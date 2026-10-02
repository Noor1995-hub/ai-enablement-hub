from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status

from src.core.dependencies.admin_scope import require_project_in_scope
from src.core.dependencies.domain import get_admin_user_service
from src.schemas.admin_defaults import (
    ApplyDefaultsResponse,
    DefaultsResponse,
    DefaultsUpdateRequest,
)
from src.services.admin_user_service import AdminUserService

__all__ = ["router"]

router = APIRouter(
    prefix="/api/admin", tags=["admin:defaults"], dependencies=[Depends(require_project_in_scope)]
)

AdminUserServiceDep = Annotated[AdminUserService, Depends(get_admin_user_service)]


@router.get("/projects/{project_id}/defaults", response_model=DefaultsResponse)
async def get_defaults(
    project_id: uuid.UUID, admin_user_service: AdminUserServiceDep
) -> DefaultsResponse:
    return DefaultsResponse(track_ids=await admin_user_service.get_project_defaults(project_id))


@router.put("/projects/{project_id}/defaults", status_code=status.HTTP_204_NO_CONTENT)
async def put_defaults(
    project_id: uuid.UUID, body: DefaultsUpdateRequest, admin_user_service: AdminUserServiceDep
) -> None:
    await admin_user_service.set_project_defaults(project_id, body.track_ids)


@router.post("/projects/{project_id}/defaults/apply", response_model=ApplyDefaultsResponse)
async def apply_defaults(
    project_id: uuid.UUID, admin_user_service: AdminUserServiceDep
) -> ApplyDefaultsResponse:
    return ApplyDefaultsResponse(
        users_updated=await admin_user_service.apply_project_defaults(project_id)
    )
