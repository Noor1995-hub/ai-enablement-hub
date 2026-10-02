from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any, cast

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert

from src.db.models import ProjectAdmin, User
from src.repositories.base import AbstractProjectAdminRepository

if TYPE_CHECKING:
    from datetime import datetime

    from sqlalchemy import CursorResult

__all__ = ["ProjectAdminRepository"]


class ProjectAdminRepository(AbstractProjectAdminRepository):
    async def project_ids_for(self, user_id: uuid.UUID) -> frozenset[uuid.UUID]:
        result = await self._session.execute(
            select(ProjectAdmin.project_id).where(ProjectAdmin.user_id == user_id)
        )
        return frozenset(result.scalars().all())

    async def is_project_admin(self, user_id: uuid.UUID) -> bool:
        result = await self._session.execute(
            select(ProjectAdmin.user_id).where(ProjectAdmin.user_id == user_id).limit(1)
        )
        return result.first() is not None

    async def admin_ids_for_project(self, project_id: uuid.UUID) -> set[uuid.UUID]:
        result = await self._session.execute(
            select(ProjectAdmin.user_id).where(ProjectAdmin.project_id == project_id)
        )
        return set(result.scalars().all())

    async def all_pairs(self) -> set[tuple[uuid.UUID, uuid.UUID]]:
        result = await self._session.execute(select(ProjectAdmin.user_id, ProjectAdmin.project_id))
        return {(user_id, project_id) for user_id, project_id in result.all()}

    async def list_for_project(self, project_id: uuid.UUID) -> list[tuple[User, datetime]]:
        result = await self._session.execute(
            select(User, ProjectAdmin.granted_at)
            .join(ProjectAdmin, ProjectAdmin.user_id == User.id)
            .where(ProjectAdmin.project_id == project_id)
            .order_by(User.last_name, User.first_name)
        )
        return [(user, granted_at) for user, granted_at in result.all()]

    async def grant(
        self, user_id: uuid.UUID, project_id: uuid.UUID, granted_by: uuid.UUID | None
    ) -> None:
        await self._session.execute(
            insert(ProjectAdmin)
            .values(user_id=user_id, project_id=project_id, granted_by=granted_by)
            .on_conflict_do_nothing(index_elements=["user_id", "project_id"])
        )
        await self._session.commit()

    async def revoke(self, user_id: uuid.UUID, project_id: uuid.UUID) -> bool:
        result = await self._session.execute(
            delete(ProjectAdmin).where(
                ProjectAdmin.user_id == user_id, ProjectAdmin.project_id == project_id
            )
        )
        await self._session.commit()
        return cast("CursorResult[Any]", result).rowcount > 0
