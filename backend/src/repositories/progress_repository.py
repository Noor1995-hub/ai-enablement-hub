from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from src.db.models import Lesson, LessonProgress
from src.repositories.base import AbstractProgressRepository

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

    async def completed_counts_by_module(self, user_id: uuid.UUID) -> dict[uuid.UUID, int]:
        result = await self._session.execute(
            select(Lesson.module_id, func.count())
            .join(LessonProgress, LessonProgress.lesson_id == Lesson.id)
            .where(LessonProgress.user_id == user_id)
            .group_by(Lesson.module_id)
        )
        return {row[0]: row[1] for row in result.all()}

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
