from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status

from src.core.dependencies.auth import get_current_user
from src.core.dependencies.domain import get_learning_service
from src.db.models import User
from src.schemas.learning import (
    LearningGraphResponse,
    LessonDetailResponse,
    LessonProgressRequest,
    ModuleLessonsResponse,
)
from src.services.learning_service import LearningService

__all__ = ["router"]

router = APIRouter(prefix="/api", tags=["learning"])

CurrentUserDep = Annotated[User, Depends(get_current_user)]
LearningServiceDep = Annotated[LearningService, Depends(get_learning_service)]


@router.get("/learning/graph", response_model=LearningGraphResponse)
async def get_learning_graph(
    user: CurrentUserDep, learning_service: LearningServiceDep
) -> LearningGraphResponse:
    """One aggregate replacing LearningPath's legacy 7-query chain; `assigned`
    flags are computed for the caller only."""
    return LearningGraphResponse(**await learning_service.graph(user.id))


@router.get("/modules/{module_id}/lessons", response_model=ModuleLessonsResponse)
async def get_module_lessons(
    module_id: uuid.UUID, user: CurrentUserDep, learning_service: LearningServiceDep
) -> ModuleLessonsResponse:
    """Lessons + caller's completion per lesson; next_lesson_id is the first
    uncompleted one (ModulePopup + LessonPage sidebar in one call)."""
    return ModuleLessonsResponse(**await learning_service.module_lessons(user.id, module_id))


@router.get("/lessons/{lesson_id}", response_model=LessonDetailResponse)
async def get_lesson(
    lesson_id: uuid.UUID, user: CurrentUserDep, learning_service: LearningServiceDep
) -> LessonDetailResponse:
    """Lesson + module + caller's answers + next destination in one response
    (collapses LessonPage's sequential prefetch chain, fixes legacy B4)."""
    return LessonDetailResponse(**await learning_service.lesson_detail(user.id, lesson_id))


@router.put("/lessons/{lesson_id}/progress", status_code=status.HTTP_204_NO_CONTENT)
async def save_lesson_progress(
    lesson_id: uuid.UUID,
    body: LessonProgressRequest,
    user: CurrentUserDep,
    learning_service: LearningServiceDep,
) -> None:
    """Mark the lesson complete for the caller (idempotent upsert). lesson_id
    is the only client-supplied identifier — ownership comes from the token."""
    await learning_service.save_progress(user.id, lesson_id, body.answers)
