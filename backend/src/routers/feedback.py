from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from src.core.dependencies.auth import get_current_user
from src.core.dependencies.domain import get_feedback_service
from src.core.dependencies.ratelimit import get_rate_limiter
from src.core.ratelimit import RateLimiter
from src.db.models import User
from src.schemas.feedback import FeedbackCreate, FeedbackResponse
from src.services.feedback_service import FeedbackService

__all__ = ["router"]

router = APIRouter(prefix="/api/feedback", tags=["feedback"])

CurrentUserDep = Annotated[User, Depends(get_current_user)]
RateLimiterDep = Annotated[RateLimiter, Depends(get_rate_limiter)]

# 10 per 10 minutes per learner. A learner reading a lesson files one or two
# notes; ten is generous. The cap matters because every accepted row becomes an
# LLM call on the admin's triage run, so this endpoint is an amplification path
# into AI spend, not just a table that can be filled.
_MAX_SUBMISSIONS = 10
_WINDOW_SECONDS = 600

_RATE_LIMITED = HTTPException(
    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
    detail="Too much feedback at once — try again shortly",
    headers={"Retry-After": "600"},
)


@router.post("", response_model=FeedbackResponse, status_code=status.HTTP_201_CREATED)
async def submit_feedback(
    user: CurrentUserDep,
    body: FeedbackCreate,
    feedback_service: Annotated[FeedbackService, Depends(get_feedback_service)],
    limiter: RateLimiterDep,
) -> FeedbackResponse:
    """Keyed by user id, not IP: the caller is always authenticated here, and a
    shared office IP must not let one learner's burst silence the floor."""
    if limiter.is_limited(
        f"feedback:{user.id}", max_calls=_MAX_SUBMISSIONS, window_seconds=_WINDOW_SECONDS
    ):
        raise _RATE_LIMITED
    feedback = await feedback_service.submit(user.id, body.lesson_id, body.message)
    return FeedbackResponse.model_validate(feedback)
