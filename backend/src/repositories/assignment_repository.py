from __future__ import annotations

import uuid

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from src.db.models import UserModule, UserTrack
from src.repositories.base import AbstractAssignmentRepository

__all__ = ["AssignmentRepository"]


class AssignmentRepository(AbstractAssignmentRepository):
    async def track_ids_for_user(self, user_id: uuid.UUID) -> set[uuid.UUID]:
        result = await self._session.execute(
            select(UserTrack.track_id).where(UserTrack.user_id == user_id)
        )
        return set(result.scalars().all())

    async def module_ids_for_user(self, user_id: uuid.UUID) -> set[uuid.UUID]:
        result = await self._session.execute(
            select(UserModule.module_id).where(UserModule.user_id == user_id)
        )
        return set(result.scalars().all())

    async def all_user_tracks(self) -> list[UserTrack]:
        result = await self._session.execute(select(UserTrack))
        return list(result.scalars().all())

    async def all_user_modules(self) -> list[UserModule]:
        result = await self._session.execute(select(UserModule))
        return list(result.scalars().all())

    async def set_user_track(self, user_id: uuid.UUID, track_id: uuid.UUID, assigned: bool) -> None:
        if assigned:
            stmt = (
                pg_insert(UserTrack)
                .values(user_id=user_id, track_id=track_id)
                .on_conflict_do_nothing(index_elements=["user_id", "track_id"])
            )
            await self._session.execute(stmt)
        else:
            await self._session.execute(
                delete(UserTrack).where(
                    UserTrack.user_id == user_id, UserTrack.track_id == track_id
                )
            )
        await self._session.commit()

    async def set_user_module(
        self, user_id: uuid.UUID, module_id: uuid.UUID, assigned: bool
    ) -> None:
        if assigned:
            stmt = (
                pg_insert(UserModule)
                .values(user_id=user_id, module_id=module_id)
                .on_conflict_do_nothing(index_elements=["user_id", "module_id"])
            )
            await self._session.execute(stmt)
        else:
            await self._session.execute(
                delete(UserModule).where(
                    UserModule.user_id == user_id, UserModule.module_id == module_id
                )
            )
        await self._session.commit()
