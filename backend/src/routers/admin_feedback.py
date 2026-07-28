from __future__ import annotations

import uuid
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status

from src.core.dependencies.auth import require_admin
from src.core.dependencies.content_ai import get_feedback_triage_service
from src.core.dependencies.domain import get_feedback_service
from src.core.dependencies.ratelimit import get_rate_limiter
from src.core.ratelimit import RateLimiter
from src.db.models import User
from src.schemas.admin_feedback import (
    AdminFeedbackListResponse,
    AdminFeedbackOut,
    FeedbackStatusUpdateRequest,
    SuggestTriageResponse,
)
from src.services.feedback_service import FeedbackService
from src.services.feedback_triage_service import FeedbackTriageService

__all__ = ["router"]

router = APIRouter(
    prefix="/api/admin", tags=["admin:feedback"], dependencies=[Depends(require_admin)]
)

FeedbackServiceDep = Annotated[FeedbackService, Depends(get_feedback_service)]
TriageServiceDep = Annotated[FeedbackTriageService | None, Depends(get_feedback_triage_service)]
RateLimiterDep = Annotated[RateLimiter, Depends(get_rate_limiter)]


@router.get("/feedback", response_model=AdminFeedbackListResponse)
async def list_feedback(
    feedback_service: FeedbackServiceDep,
    status_filter: Annotated[
        Literal["new", "accepted", "dismissed"] | None, Query(alias="status")
    ] = None,
    track_id: Annotated[uuid.UUID | None, Query()] = None,
    project_id: Annotated[uuid.UUID | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> AdminFeedbackListResponse:
    items, total = await feedback_service.list_admin(
        status=status_filter, track_id=track_id, project_id=project_id, limit=limit, offset=offset
    )
    return AdminFeedbackListResponse(
        items=[AdminFeedbackOut.model_validate(item) for item in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post("/feedback/suggest-triage", response_model=SuggestTriageResponse)
async def suggest_feedback_triage(
    triage_service: TriageServiceDep,
    admin: Annotated[User, Depends(require_admin)],
    limiter: RateLimiterDep,
    project_id: Annotated[uuid.UUID | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=25)] = 10,
) -> SuggestTriageResponse:
    """Generate AI triage suggestions for `new` feedback that has none yet.

    Lazy + admin-triggered on purpose: the learner's POST /api/feedback stays
    free of LLM latency and cost. Bounded by `limit`; the response reports what
    is still outstanding so a truncated run is visible, never silent. This only
    ever writes the ai_* columns — the real `status` is the admin's call.
    """
    if triage_service is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="AI triage is not configured"
        )
    if limiter.is_limited(f"triage:{admin.id}", max_calls=6, window_seconds=300):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many triage runs — try again shortly",
            headers={"Retry-After": "60"},
        )
    suggested, failed, remaining = await triage_service.suggest(project_id=project_id, limit=limit)
    return SuggestTriageResponse(suggested=suggested, failed=failed, remaining=remaining)


@router.patch("/feedback/{feedback_id}", status_code=status.HTTP_204_NO_CONTENT)
async def set_feedback_status(
    feedback_id: uuid.UUID,
    body: FeedbackStatusUpdateRequest,
    feedback_service: FeedbackServiceDep,
    admin: Annotated[User, Depends(require_admin)],
) -> None:
    await feedback_service.set_status(feedback_id, body.status, admin.id)
