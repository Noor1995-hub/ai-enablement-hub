"""Who may administer what (spec 2026-10-01-project-scoped-admin-design.md).

Power admin = role 'admin' (everything). Project admin = role 'user' with
project_admins rows (only those projects). Read from the DB on every request,
like the role, so a revoke takes effect on the next call."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import TYPE_CHECKING

from src.services.exceptions import AdminTargetForbiddenError, InvalidRequestError, NotFoundError

if TYPE_CHECKING:
    from src.db.models import User
    from src.repositories.base import AbstractProjectAdminRepository, AbstractUserRepository

__all__ = ["AdminScope", "AdminScopeService"]


@dataclass(frozen=True)
class AdminScope:
    user: User
    is_power: bool
    project_ids: frozenset[uuid.UUID]

    def covers(self, project_id: uuid.UUID | None) -> bool:
        return self.is_power or (project_id is not None and project_id in self.project_ids)

    def resolve_list_project(self, project_id: uuid.UUID | None) -> uuid.UUID | None:
        """The project a list endpoint filters on. Power admins: as given (None =
        all). Project admins: a covered project, or their only one when omitted."""
        if self.is_power:
            return project_id
        if project_id is not None:
            if project_id not in self.project_ids:
                raise NotFoundError("Project")
            return project_id
        if len(self.project_ids) == 1:
            return next(iter(self.project_ids))
        raise InvalidRequestError("project_id is required")


class AdminScopeService:
    def __init__(
        self, users: AbstractUserRepository, admins: AbstractProjectAdminRepository
    ) -> None:
        self._users = users
        self._admins = admins

    async def scope_for(self, user: User) -> AdminScope | None:
        """None when the user is neither a power admin nor a project admin."""
        if user.role == "admin":
            return AdminScope(user=user, is_power=True, project_ids=frozenset())
        project_ids = await self._admins.project_ids_for(user.id)
        if not project_ids:
            return None
        return AdminScope(user=user, is_power=False, project_ids=project_ids)

    async def ensure_user_in_scope(self, scope: AdminScope, user_id: uuid.UUID) -> User:
        """The target of a per-user admin route. Unknown or out of scope → 404.
        A project admin may only manage learners: never a power admin, another
        project admin, or themselves (→ 403)."""
        target = await self._users.get_by_id(user_id)
        if target is None or not scope.covers(target.project_id):
            raise NotFoundError("User")
        if not scope.is_power and (
            target.role == "admin"
            or target.id == scope.user.id
            or await self._admins.is_project_admin(target.id)
        ):
            raise AdminTargetForbiddenError
        return target

    async def ensure_users_in_scope(self, scope: AdminScope, user_ids: list[uuid.UUID]) -> None:
        """All-or-nothing for bulk routes: one unknown or out-of-scope id rejects
        the whole request. Bulk routes only assign content or read levels, so
        the learners-only rule of ensure_user_in_scope is not applied here."""
        if scope.is_power:
            return
        found = await self._users.project_ids_of(user_ids)
        if len(found) != len(set(user_ids)) or not all(scope.covers(p) for p in found.values()):
            raise NotFoundError("User")

    async def bypasses_locks(self, user: User) -> bool:
        """Power admins everywhere; project admins on their own project only."""
        if user.role == "admin":
            return True
        if user.project_id is None:
            return False
        return user.project_id in await self._admins.project_ids_for(user.id)
