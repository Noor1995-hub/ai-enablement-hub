from __future__ import annotations

import uuid
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status

from src.core.dependencies.auth import require_admin
from src.core.dependencies.content_ai import get_content_improvement_service
from src.core.dependencies.ratelimit import get_rate_limiter
from src.core.ratelimit import RateLimiter
from src.db.models import User
from src.schemas.admin_proposals import (
    ImprovementRunResponse,
    ProposalDetailOut,
    ProposalListResponse,
    ProposalReviewRequest,
    ProposalReviewResponse,
    ProposalSummaryOut,
)
from src.services.content_improvement_service import ContentImprovementService

__all__ = ["router"]

router = APIRouter(
    prefix="/api/admin/content-improvement",
    tags=["admin:content-improvement"],
    dependencies=[Depends(require_admin)],
)

ImprovementServiceDep = Annotated[
    ContentImprovementService | None, Depends(get_content_improvement_service)
]
RateLimiterDep = Annotated[RateLimiter, Depends(get_rate_limiter)]

_NOT_CONFIGURED = HTTPException(
    status_code=status.HTTP_404_NOT_FOUND, detail="AI content improvement is not configured"
)


@router.post("/run", response_model=ImprovementRunResponse)
async def run_improvement_pass(
    service: ImprovementServiceDep,
    admin: Annotated[User, Depends(require_admin)],
    limiter: RateLimiterDep,
    max_lessons: Annotated[int, Query(ge=1, le=3)] = 3,
) -> ImprovementRunResponse:
    """Draft revisions for lessons with accepted, not-yet-incorporated feedback.

    Admin-triggered, bounded and synchronous: `max_lessons` caps the fan-out and
    the service carries a per-lesson timeout plus an overall budget, so one
    click can never hold the request past the ingress timeout. Nothing here
    touches a live lesson — every draft lands as a `pending` proposal.

    Not project-scoped on purpose: lessons are shared catalogue content, not
    per-project, so a "run for project X" would be a category error.
    """
    if service is None:
        raise _NOT_CONFIGURED
    if limiter.is_limited(f"content-improvement:{admin.id}", max_calls=6, window_seconds=600):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many improvement passes — try again shortly",
            headers={"Retry-After": "120"},
        )
    proposed, skipped, remaining = await service.run(max_lessons=max_lessons)
    return ImprovementRunResponse(proposed=proposed, skipped=skipped, remaining=remaining)


@router.get("", response_model=ProposalListResponse)
async def list_proposals(
    service: ImprovementServiceDep,
    status_filter: Annotated[
        Literal["pending", "approved", "rejected", "superseded", "failed"] | None,
        Query(alias="status"),
    ] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> ProposalListResponse:
    if service is None:
        raise _NOT_CONFIGURED
    items, total = await service.list_proposals(status=status_filter, limit=limit, offset=offset)
    return ProposalListResponse(
        items=[ProposalSummaryOut.model_validate(item) for item in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{proposal_id}", response_model=ProposalDetailOut)
async def get_proposal(proposal_id: uuid.UUID, service: ImprovementServiceDep) -> ProposalDetailOut:
    if service is None:
        raise _NOT_CONFIGURED
    return ProposalDetailOut.model_validate(await service.proposal_detail(proposal_id))


@router.post("/{proposal_id}/review", response_model=ProposalReviewResponse)
async def review_proposal(
    proposal_id: uuid.UUID,
    body: ProposalReviewRequest,
    service: ImprovementServiceDep,
    admin: Annotated[User, Depends(require_admin)],
) -> ProposalReviewResponse:
    """The human gate. `approve` writes the revision to the live lesson;
    `reject` discards it and frees its feedback for a future run. A 409 means
    the lesson moved under the proposal (now `superseded`) or the draft was
    already decided."""
    if service is None:
        raise _NOT_CONFIGURED
    new_status = await service.review(
        proposal_id=proposal_id, decision=body.decision, reviewer_id=admin.id
    )
    return ProposalReviewResponse(status=new_status)  # ty: ignore[invalid-argument-type]
