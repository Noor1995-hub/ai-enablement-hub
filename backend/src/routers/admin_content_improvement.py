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
    CalibrationNoteBrief,
    ImprovementRunRequest,
    ImprovementRunResponse,
    LearnCardOut,
    ProposalDetailOut,
    ProposalListResponse,
    ProposalReviewRequest,
    ProposalReviewResponse,
    ProposalSummaryOut,
    QueueItemOut,
    QueueResponse,
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


@router.get("/queue", response_model=QueueResponse)
async def list_draft_queue(service: ImprovementServiceDep) -> QueueResponse:
    """The lessons an admin can pick to redraft: accepted feedback that no
    proposal covers yet, oldest feedback first.

    Unpaginated on purpose — this is the picker's option list, and an admin
    choosing from it needs to see the whole queue, not page one of it. It stays
    small by construction: a lesson leaves as soon as a draft or a `failed`
    proposal covers its feedback.
    """
    if service is None:
        raise _NOT_CONFIGURED
    items = await service.list_queue()
    return QueueResponse(
        items=[QueueItemOut.model_validate(item) for item in items], total=len(items)
    )


@router.post("/run", response_model=ImprovementRunResponse)
async def run_improvement_pass(
    body: ImprovementRunRequest,
    service: ImprovementServiceDep,
    admin: Annotated[User, Depends(require_admin)],
    limiter: RateLimiterDep,
) -> ImprovementRunResponse:
    """Draft revisions for the lessons the admin picked out of `GET /queue`.

    Admin-triggered, bounded and synchronous: the request caps the selection at
    MAX_LESSONS_PER_RUN and the service drafts them concurrently under a
    per-lesson timeout, so the call's wall clock is the slowest single draft
    rather than the sum — that is what keeps one click inside the ingress
    timeout. Every selected lesson is attempted, so the response accounts for
    all of them. Nothing here touches a live lesson — every draft lands as a
    `pending` proposal.

    A lesson id that is no longer queued is reported in `not_queued` rather than
    404ing the whole call: with two admins on the page, one drafting a lesson
    must not fail the other's batch.

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
    outcome = await service.run(lesson_ids=body.lesson_ids)
    return ImprovementRunResponse(
        proposed=outcome.proposed,
        skipped=outcome.skipped,
        deferred=outcome.deferred,
        not_queued=outcome.not_queued,
    )


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
        proposal_id=proposal_id,
        decision=body.decision,
        reviewer_id=admin.id,
        edited_blocks=body.edited_blocks,
    )
    return ProposalReviewResponse(status=new_status)  # ty: ignore[invalid-argument-type]


@router.post("/{proposal_id}/critique", response_model=LearnCardOut)
async def generate_learn_card(
    proposal_id: uuid.UUID,
    service: ImprovementServiceDep,
    admin: Annotated[User, Depends(require_admin)],
    limiter: RateLimiterDep,
) -> LearnCardOut:
    """Ask the agent what it can learn from the difference between its draft and
    the version the admin accepted. Only meaningful once a draft was accepted
    WITH edits; 409 otherwise, and 409 again if a learn card already exists so a
    retry can never duplicate the suggested notes."""
    if service is None:
        raise _NOT_CONFIGURED
    if limiter.is_limited(f"learn-card:{admin.id}", max_calls=20, window_seconds=600):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many learn cards — try again shortly",
            headers={"Retry-After": "60"},
        )
    proposal, notes = await service.critique(proposal_id=proposal_id)
    return LearnCardOut(
        critique_agent_wrong=proposal.critique_agent_wrong,
        critique_admin_preferred=proposal.critique_admin_preferred,
        critiqued_at=proposal.critiqued_at,
        calibration_notes=[
            CalibrationNoteBrief(id=n.id, note=n.note, status=n.status) for n in notes
        ],
    )
