from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status

from src.core.constants import LOCK_BYPASS_ROLES
from src.core.dependencies.auth import get_current_user
from src.core.dependencies.components import require_component_unlocked
from src.core.dependencies.domain import get_learning_service, get_maturity_service
from src.core.dependencies.storage import get_media_service
from src.db.models import User
from src.schemas.learning import (
    LearningGraphResponse,
    LessonDetailResponse,
    LessonProgressRequest,
    ModuleLessonsResponse,
)
from src.services.learning_service import LearningService
from src.services.maturity_service import MaturityService
from src.services.media_service import MediaService

__all__ = ["router"]

router = APIRouter(
    prefix="/api",
    tags=["learning"],
    dependencies=[Depends(require_component_unlocked("learning"))],
)

CurrentUserDep = Annotated[User, Depends(get_current_user)]
LearningServiceDep = Annotated[LearningService, Depends(get_learning_service)]
MaturityServiceDep = Annotated[MaturityService, Depends(get_maturity_service)]
MediaServiceDep = Annotated[MediaService | None, Depends(get_media_service)]


@router.get("/learning/graph", response_model=LearningGraphResponse)
async def get_learning_graph(
    user: CurrentUserDep,
    learning_service: LearningServiceDep,
) -> LearningGraphResponse:
    """One aggregate replacing LearningPath's legacy 7-query chain; `assigned`
    flags are computed for the caller only. Per-track maturity locks come from
    the caller's effective level (override + live progression), which the
    service derives from the rows it already reads."""
    return LearningGraphResponse(**await learning_service.graph(user))


@router.get("/modules/{module_id}/lessons", response_model=ModuleLessonsResponse)
async def get_module_lessons(
    module_id: uuid.UUID, user: CurrentUserDep, learning_service: LearningServiceDep
) -> ModuleLessonsResponse:
    """Lessons + caller's completion per lesson; next_lesson_id is the first
    uncompleted one (ModulePopup + LessonPage sidebar in one call)."""
    return ModuleLessonsResponse(**await learning_service.module_lessons(user.id, module_id))


@router.get("/lessons/{lesson_id}", response_model=LessonDetailResponse)
async def get_lesson(
    lesson_id: uuid.UUID,
    user: CurrentUserDep,
    learning_service: LearningServiceDep,
    maturity_service: MaturityServiceDep,
    media: MediaServiceDep,
) -> LessonDetailResponse:
    """Lesson + module + caller's answers + next destination in one response
    (collapses LessonPage's sequential prefetch chain, fixes legacy B4).

    Effective maturity and the role bypass are resolved HERE and passed down:
    services never call other services, so the router composes MaturityService
    and LearningService exactly as get_learning_graph above does. A lesson that
    is neither assigned nor maturity-unlocked is a 403 (see
    LearningService._is_accessible).

    content_blocks gets fresh SAS urls stamped onto image/blob-video blocks
    when storage is configured. Response-only: `media.stamp_blocks` returns a
    new list, so rebinding the aggregate dict's key never assigns back onto
    the lesson ORM object/JSONB attribute."""
    payload = await learning_service.lesson_detail(
        user.id,
        lesson_id,
        effective_level=await maturity_service.effective_level(user),
        bypass_locks=user.role in LOCK_BYPASS_ROLES,
    )
    if media is not None:
        payload["content_blocks"] = media.stamp_blocks(payload["content_blocks"])
    return LessonDetailResponse(**payload)


@router.put("/lessons/{lesson_id}/progress", status_code=status.HTTP_204_NO_CONTENT)
async def save_lesson_progress(
    lesson_id: uuid.UUID,
    body: LessonProgressRequest,
    user: CurrentUserDep,
    learning_service: LearningServiceDep,
    maturity_service: MaturityServiceDep,
) -> None:
    """Mark the lesson complete for the caller (idempotent upsert). lesson_id
    is the only client-supplied identifier — ownership comes from the token,
    and the same access gate as GET applies."""
    await learning_service.save_progress(
        user.id,
        lesson_id,
        body.answers,
        effective_level=await maturity_service.effective_level(user),
        bypass_locks=user.role in LOCK_BYPASS_ROLES,
    )
