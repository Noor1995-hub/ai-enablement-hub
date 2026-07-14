from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status

from src.core.dependencies.auth import get_current_user
from src.core.dependencies.domain import get_feedback_service
from src.db.models import User
from src.schemas.feedback import FeedbackCreate, FeedbackResponse
from src.services.feedback_service import FeedbackService

__all__ = ["router"]

router = APIRouter(prefix="/api/feedback", tags=["feedback"])

CurrentUserDep = Annotated[User, Depends(get_current_user)]


@router.post("", response_model=FeedbackResponse, status_code=status.HTTP_201_CREATED)
async def submit_feedback(
    user: CurrentUserDep,
    body: FeedbackCreate,
    feedback_service: Annotated[FeedbackService, Depends(get_feedback_service)],
) -> FeedbackResponse:
    feedback = await feedback_service.submit(user.id, body.lesson_id, body.message)
    return FeedbackResponse.model_validate(feedback)
