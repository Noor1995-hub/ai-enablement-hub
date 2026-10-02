"""Admin authorization guards (spec 2026-10-01-project-scoped-admin-design.md).

Every /api/admin/* route depends on exactly one of: require_power_admin,
require_project_in_scope, require_user_in_scope, or AdminScopeDep (lists and
bodies, which then call scope.resolve_list_project / scope.covers).
tests/integration/test_routers/test_authz.py fails on an admin route that is
missing from its matrix.

All parameter annotations are runtime imports on purpose (see database.py)."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import Depends, HTTPException, status

from src.core.dependencies.auth import get_current_user
from src.core.dependencies.domain import get_admin_scope_service
from src.db.models import User
from src.services.admin_scope_service import AdminScope, AdminScopeService
from src.services.exceptions import NotFoundError

__all__ = [
    "AdminScopeDep",
    "AdminScopeServiceDep",
    "BypassesLocksDep",
    "PowerAdminDep",
    "get_admin_scope",
    "get_bypasses_locks",
    "require_power_admin",
    "require_project_in_scope",
    "require_user_in_scope",
]

AdminScopeServiceDep = Annotated[AdminScopeService, Depends(get_admin_scope_service)]


def _forbidden() -> HTTPException:
    return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin role required")


async def get_admin_scope(
    user: Annotated[User, Depends(get_current_user)], service: AdminScopeServiceDep
) -> AdminScope:
    """Power admin or project admin; anyone else → 403."""
    scope = await service.scope_for(user)
    if scope is None:
        raise _forbidden()
    return scope


AdminScopeDep = Annotated[AdminScope, Depends(get_admin_scope)]


async def require_power_admin(user: Annotated[User, Depends(get_current_user)]) -> User:
    if user.role != "admin":
        raise _forbidden()
    return user


PowerAdminDep = Annotated[User, Depends(require_power_admin)]


async def require_project_in_scope(project_id: uuid.UUID, scope: AdminScopeDep) -> AdminScope:
    """Binds the `{project_id}` path segment. Out of scope → 404 (no probing)."""
    if not scope.covers(project_id):
        raise NotFoundError("Project")
    return scope


async def require_user_in_scope(
    user_id: uuid.UUID, scope: AdminScopeDep, service: AdminScopeServiceDep
) -> User:
    """Binds the `{user_id}` path segment; returns the target user."""
    return await service.ensure_user_in_scope(scope, user_id)


async def get_bypasses_locks(
    user: Annotated[User, Depends(get_current_user)], service: AdminScopeServiceDep
) -> bool:
    return await service.bypasses_locks(user)


BypassesLocksDep = Annotated[bool, Depends(get_bypasses_locks)]
