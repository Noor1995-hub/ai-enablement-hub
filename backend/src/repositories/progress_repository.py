from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from src.db.models import LessonProgress
from src.repositories.base import AbstractProgressRepository

if TYPE_CHECKING:
    from datetime import datetime

__all__ = ["ProgressRepository"]


class ProgressRepository(AbstractProgressRepository):
    async def get(self, user_id: uuid.UUID, lesson_id: uuid.UUID) -> LessonProgress | None:
        result = await self._session.execute(
            select(LessonProgress).where(
                LessonProgress.user_id == user_id, LessonProgress.lesson_id == lesson_id
            )
        )
        return result.scalar_one_or_none()

    async def completed_lesson_ids(
        self, user_id: uuid.UUID, lesson_ids: list[uuid.UUID] | None = None
    ) -> set[uuid.UUID]:
        stmt = select(LessonProgress.lesson_id).where(LessonProgress.user_id == user_id)
        if lesson_ids is not None:
            stmt = stmt.where(LessonProgress.lesson_id.in_(lesson_ids))
        result = await self._session.execute(stmt)
        return set(result.scalars().all())

    async def latest_completion_by_user(
        self, user_ids: list[uuid.UUID]
    ) -> dict[uuid.UUID, datetime]:
        if not user_ids:
            return {}
        result = await self._session.execute(
            select(LessonProgress.user_id, func.max(LessonProgress.completed_at))
            .where(LessonProgress.user_id.in_(user_ids))
            .group_by(LessonProgress.user_id)
        )
        return {user_id: completed_at for user_id, completed_at in result.all()}

    async def completions_for_users(
        self, user_ids: list[uuid.UUID]
    ) -> dict[tuple[uuid.UUID, uuid.UUID], datetime]:
        if not user_ids:
            return {}
        result = await self._session.execute(
            select(
                LessonProgress.user_id, LessonProgress.lesson_id, LessonProgress.completed_at
            ).where(LessonProgress.user_id.in_(user_ids))
        )
        return {(user_id, lesson_id): at for user_id, lesson_id, at in result.all()}

    async def upsert(
        self, user_id: uuid.UUID, lesson_id: uuid.UUID, answers: dict[str, Any]
    ) -> None:
        # Same as the legacy PostgREST upsert: re-completing only refreshes the
        # answers; the original completed_at stands.
        stmt = pg_insert(LessonProgress).values(
            user_id=user_id, lesson_id=lesson_id, answers=answers
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=["user_id", "lesson_id"], set_={"answers": stmt.excluded.answers}
        )
        await self._session.execute(stmt)
        await self._session.commit()
