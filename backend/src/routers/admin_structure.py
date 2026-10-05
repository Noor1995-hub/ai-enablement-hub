"""Content structure editing (B4, spec 2026-10-05-content-structure-editing-design.md).

Edits are power-admin only (content is shared by every project). The tree is
readable by any admin; the project-scoped gap routes let a project admin assign
their own project's learners to lessons added to modules they hold."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status

from src.core.dependencies.admin_scope import (
    AdminScopeDep,
    require_power_admin,
    require_project_in_scope,
)
from src.core.dependencies.domain import get_content_service
from src.db.models import Module, Track
from src.schemas.admin_content import (
    AssignGapResponse,
    AssignmentGapResponse,
    ContentTreeResponse,
    DeleteImpactResponse,
    ModuleOrderRequest,
    ModuleOut,
    ModuleUpdateRequest,
    PrerequisitesRequest,
    TrackOrderRequest,
    TrackOut,
    TrackUpdateRequest,
)
from src.services.content_service import ContentService

__all__ = ["router"]

router = APIRouter(prefix="/api/admin", tags=["admin:content-structure"])

ContentServiceDep = Annotated[ContentService, Depends(get_content_service)]
_POWER = [Depends(require_power_admin)]
_SCOPED = [Depends(require_project_in_scope)]


@router.get("/content/tree", response_model=ContentTreeResponse)
async def content_tree(_scope: AdminScopeDep, service: ContentServiceDep) -> ContentTreeResponse:
    """Every track → module → lesson with counts; any admin (project admins
    read it to find the modules whose new lessons they assign)."""
    return ContentTreeResponse.model_validate({"tracks": await service.content_tree()})


@router.patch("/tracks/{track_id}", response_model=TrackOut, dependencies=_POWER)
async def update_track(
    track_id: uuid.UUID, body: TrackUpdateRequest, service: ContentServiceDep
) -> Track:
    return await service.update_track(track_id, body.model_dump(exclude_unset=True))


@router.delete("/tracks/{track_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=_POWER)
async def delete_track(track_id: uuid.UUID, service: ContentServiceDep) -> None:
    """Cascades to modules, lessons, assignments and progress (the UI shows
    GET …/impact first)."""
    await service.delete_track(track_id)


@router.put("/tracks/order", status_code=status.HTTP_204_NO_CONTENT, dependencies=_POWER)
async def reorder_tracks(body: TrackOrderRequest, service: ContentServiceDep) -> None:
    await service.reorder_tracks(body.track_ids)


@router.patch("/modules/{module_id}", response_model=ModuleOut, dependencies=_POWER)
async def update_module(
    module_id: uuid.UUID, body: ModuleUpdateRequest, service: ContentServiceDep
) -> Module:
    """A different track_id moves the module to the end of that track."""
    return await service.update_module(module_id, body.model_dump(exclude_unset=True))


@router.put(
    "/tracks/{track_id}/modules/order",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=_POWER,
)
async def reorder_modules(
    track_id: uuid.UUID, body: ModuleOrderRequest, service: ContentServiceDep
) -> None:
    await service.reorder_modules(track_id, body.module_ids)


@router.put(
    "/modules/{module_id}/prerequisites",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=_POWER,
)
async def set_prerequisites(
    module_id: uuid.UUID, body: PrerequisitesRequest, service: ContentServiceDep
) -> None:
    """Replaces the set; a self-loop or cycle → 400 naming the module."""
    await service.set_prerequisites(module_id, body.prerequisite_ids)


@router.get("/tracks/{track_id}/impact", response_model=DeleteImpactResponse, dependencies=_POWER)
async def track_impact(track_id: uuid.UUID, service: ContentServiceDep) -> DeleteImpactResponse:
    return DeleteImpactResponse.model_validate(await service.track_impact(track_id))


@router.get("/modules/{module_id}/impact", response_model=DeleteImpactResponse, dependencies=_POWER)
async def module_impact(module_id: uuid.UUID, service: ContentServiceDep) -> DeleteImpactResponse:
    return DeleteImpactResponse.model_validate(await service.module_impact(module_id))


@router.get(
    "/modules/{module_id}/assignment-gap",
    response_model=AssignmentGapResponse,
    dependencies=_POWER,
)
async def assignment_gap(module_id: uuid.UUID, service: ContentServiceDep) -> AssignmentGapResponse:
    return AssignmentGapResponse.model_validate(await service.assignment_gap(module_id, None))


@router.post(
    "/modules/{module_id}/assign-new-lessons",
    response_model=AssignGapResponse,
    dependencies=_POWER,
)
async def assign_gap(module_id: uuid.UUID, service: ContentServiceDep) -> AssignGapResponse:
    return AssignGapResponse(assigned_pairs=await service.assign_gap(module_id, None))


@router.get(
    "/projects/{project_id}/modules/{module_id}/assignment-gap",
    response_model=AssignmentGapResponse,
    dependencies=_SCOPED,
)
async def project_assignment_gap(
    project_id: uuid.UUID, module_id: uuid.UUID, service: ContentServiceDep
) -> AssignmentGapResponse:
    return AssignmentGapResponse.model_validate(await service.assignment_gap(module_id, project_id))


@router.post(
    "/projects/{project_id}/modules/{module_id}/assign-new-lessons",
    response_model=AssignGapResponse,
    dependencies=_SCOPED,
)
async def project_assign_gap(
    project_id: uuid.UUID, module_id: uuid.UUID, service: ContentServiceDep
) -> AssignGapResponse:
    return AssignGapResponse(assigned_pairs=await service.assign_gap(module_id, project_id))
