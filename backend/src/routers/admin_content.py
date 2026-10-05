from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status

from src.core.dependencies.admin_scope import require_power_admin
from src.core.dependencies.auth import get_current_user
from src.core.dependencies.domain import get_content_service
from src.core.dependencies.storage import get_media_service
from src.db.models import Lesson, Module, Track
from src.schemas.admin_content import (
    LessonCreateRequest,
    LessonOrderRequest,
    LessonOut,
    LessonSummaryOut,
    LessonUpdateRequest,
    ModuleCreateRequest,
    ModuleOut,
    TrackCreateRequest,
    TrackModuleOut,
    TrackOut,
)
from src.services.content_service import ContentService
from src.services.media_service import MediaService

__all__ = ["router"]

# Two learner-facing reads + admin-only writes; auth is declared per route.
router = APIRouter(prefix="/api", tags=["content"])

ContentServiceDep = Annotated[ContentService, Depends(get_content_service)]
MediaServiceDep = Annotated[MediaService | None, Depends(get_media_service)]


@router.get("/tracks", response_model=list[TrackOut], dependencies=[Depends(get_current_user)])
async def list_tracks(content_service: ContentServiceDep) -> list[Track]:
    """All tracks (admin panel + Add-Track/Module dropdowns). Authenticated
    read: the old public RLS read was incidental to the anon-key setup."""
    return await content_service.list_tracks()


@router.get(
    "/tracks/{track_id}/modules",
    response_model=list[TrackModuleOut],
    dependencies=[Depends(get_current_user)],
)
async def list_track_modules(
    track_id: uuid.UUID, content_service: ContentServiceDep
) -> list[Module]:
    """Modules of one track (AddModuleModal predecessor picker)."""
    return await content_service.list_track_modules(track_id)


@router.post(
    "/admin/tracks",
    response_model=TrackOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_power_admin)],
)
async def create_track(body: TrackCreateRequest, content_service: ContentServiceDep) -> Track:
    """sort_order is computed server-side (max+1) inside the transaction
    (mitigates legacy A4)."""
    return await content_service.create_track(body.name, body.track_type, body.color)


@router.post(
    "/admin/modules",
    response_model=ModuleOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_power_admin)],
)
async def create_module(body: ModuleCreateRequest, content_service: ContentServiceDep) -> Module:
    """Server computes sort_order, shifts successors and inserts prerequisite
    links in one transaction (fixes legacy DB6 duplicate sort_orders)."""
    return await content_service.create_module(
        body.track_id, body.title, body.after_module_id, body.prerequisite_ids
    )


@router.delete(
    "/admin/modules/{module_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_power_admin)],
)
async def delete_module(module_id: uuid.UUID, content_service: ContentServiceDep) -> None:
    """Lessons, prerequisite links (both directions), and assignment/progress
    rows cascade."""
    await content_service.delete_module(module_id)


@router.post(
    "/admin/lessons",
    response_model=LessonSummaryOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_power_admin)],
)
async def create_lesson(body: LessonCreateRequest, content_service: ContentServiceDep) -> Lesson:
    return await content_service.create_lesson(body.module_id, body.title)


@router.patch(
    "/admin/lessons/{lesson_id}",
    response_model=LessonOut,
    dependencies=[Depends(require_power_admin)],
)
async def update_lesson(
    lesson_id: uuid.UUID,
    body: LessonUpdateRequest,
    content_service: ContentServiceDep,
    media: MediaServiceDep,
) -> Lesson | LessonOut:
    """LessonPage editor save (title and/or content_blocks; both the
    block-editor and the MDX-editor UI save through this one endpoint).
    `module_id` (Admin → Content, B4) moves the lesson to the end of that module.

    ContentService.update_lesson always strips ephemeral SAS urls before
    persisting; when storage is configured the response is stamped so the
    editor's just-saved view has working urls (contract consistency with
    GET) — the DB write itself is unaffected."""
    lesson = await content_service.update_lesson(lesson_id, body.model_dump(exclude_unset=True))
    if media is None:
        return lesson
    return LessonOut(
        id=lesson.id,
        module_id=lesson.module_id,
        title=lesson.title,
        sort_order=lesson.sort_order,
        content_blocks=media.stamp_blocks(lesson.content_blocks),
    )


@router.delete(
    "/admin/lessons/{lesson_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_power_admin)],
)
async def delete_lesson(lesson_id: uuid.UUID, content_service: ContentServiceDep) -> None:
    """lesson_progress rows cascade."""
    await content_service.delete_lesson(lesson_id)


@router.put(
    "/admin/modules/{module_id}/lessons/order",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_power_admin)],
)
async def reorder_lessons(
    module_id: uuid.UUID, body: LessonOrderRequest, content_service: ContentServiceDep
) -> None:
    """Batch reorder in one transaction; lesson_ids must be a permutation of
    the module's lessons (replaces ModulePanel's N parallel updates, fixes B5)."""
    await content_service.reorder_lessons(module_id, body.lesson_ids)
