"""Who administers a project (spec 2026-10-01-project-scoped-admin-design.md).
Reading the list is open to that project's admins; granting and revoking is
power-admin only."""

from __future__ import annotations

import logging
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status

from src.core.dependencies.admin_scope import PowerAdminDep, require_project_in_scope
from src.core.dependencies.domain import get_admin_user_service
from src.schemas.admin_project_admins import ProjectAdminOut, ProjectAdminsResponse
from src.services.admin_user_service import AdminUserService

__all__ = ["router"]

router = APIRouter(prefix="/api/admin", tags=["admin:project-admins"])

logger = logging.getLogger(__name__)

AdminUserServiceDep = Annotated[AdminUserService, Depends(get_admin_user_service)]


@router.get(
    "/projects/{project_id}/admins",
    response_model=ProjectAdminsResponse,
    dependencies=[Depends(require_project_in_scope)],
)
async def list_project_admins(
    project_id: uuid.UUID, admin_user_service: AdminUserServiceDep
) -> ProjectAdminsResponse:
    rows = await admin_user_service.list_project_admins(project_id)
    return ProjectAdminsResponse(
        admins=[
            ProjectAdminOut(
                user_id=user.id,
                first_name=user.first_name,
                last_name=user.last_name,
                email=user.email,
                granted_at=granted_at,
            )
            for user, granted_at in rows
        ]
    )


@router.put("/projects/{project_id}/admins/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def grant_project_admin(
    project_id: uuid.UUID,
    user_id: uuid.UUID,
    actor: PowerAdminDep,
    admin_user_service: AdminUserServiceDep,
) -> None:
    """Idempotent; a no-op for a power admin (they already cover every project)."""
    await admin_user_service.grant_project_admin(actor, project_id, user_id)
    logger.info("project admin granted: project=%s user=%s by=%s", project_id, user_id, actor.id)


@router.delete("/projects/{project_id}/admins/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_project_admin(
    project_id: uuid.UUID,
    user_id: uuid.UUID,
    actor: PowerAdminDep,
    admin_user_service: AdminUserServiceDep,
) -> None:
    """404 when the user is not an admin of this project. Takes effect on the
    user's next request (scope is read from the DB every time)."""
    await admin_user_service.revoke_project_admin(project_id, user_id)
    logger.info("project admin revoked: project=%s user=%s by=%s", project_id, user_id, actor.id)
