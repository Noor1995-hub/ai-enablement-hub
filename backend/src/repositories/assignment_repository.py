from __future__ import annotations

import uuid

from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from src.db.models import Lesson, LessonProgress, UserLesson, UserModule, UserTrack
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

    async def lesson_ids_for_user(self, user_id: uuid.UUID) -> set[uuid.UUID]:
        result = await self._session.execute(
            select(UserLesson.lesson_id).where(UserLesson.user_id == user_id)
        )
        return set(result.scalars().all())

    async def all_user_tracks(self) -> list[UserTrack]:
        result = await self._session.execute(select(UserTrack))
        return list(result.scalars().all())

    async def all_user_modules(self) -> list[UserModule]:
        result = await self._session.execute(select(UserModule))
        return list(result.scalars().all())

    async def all_user_lessons(self) -> list[UserLesson]:
        result = await self._session.execute(select(UserLesson))
        return list(result.scalars().all())

    async def assigned_lesson_counts_by_module(
        self, user_id: uuid.UUID
    ) -> dict[uuid.UUID, tuple[int, int]]:
        result = await self._session.execute(
            select(Lesson.module_id, func.count(), func.count(LessonProgress.id))
            .select_from(UserLesson)
            .join(Lesson, Lesson.id == UserLesson.lesson_id)
            .outerjoin(
                LessonProgress,
                (LessonProgress.user_id == UserLesson.user_id)
                & (LessonProgress.lesson_id == UserLesson.lesson_id),
            )
            .where(UserLesson.user_id == user_id)
            .group_by(Lesson.module_id)
        )
        return {row[0]: (row[1], row[2]) for row in result.all()}

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

    async def set_user_lesson(
        self, user_id: uuid.UUID, lesson_id: uuid.UUID, assigned: bool
    ) -> None:
        if assigned:
            stmt = (
                pg_insert(UserLesson)
                .values(user_id=user_id, lesson_id=lesson_id)
                .on_conflict_do_nothing(index_elements=["user_id", "lesson_id"])
            )
            await self._session.execute(stmt)
        else:
            await self._session.execute(
                delete(UserLesson).where(
                    UserLesson.user_id == user_id, UserLesson.lesson_id == lesson_id
                )
            )
        await self._session.commit()

    async def set_user_tracks(
        self, user_id: uuid.UUID, track_ids: list[uuid.UUID], assigned: bool
    ) -> None:
        if assigned:
            stmt = (
                pg_insert(UserTrack)
                .values([{"user_id": user_id, "track_id": tid} for tid in track_ids])
                .on_conflict_do_nothing(index_elements=["user_id", "track_id"])
            )
            await self._session.execute(stmt)
        else:
            await self._session.execute(
                delete(UserTrack).where(
                    UserTrack.user_id == user_id, UserTrack.track_id.in_(track_ids)
                )
            )
        await self._session.commit()

    async def set_user_modules(
        self, user_id: uuid.UUID, module_ids: list[uuid.UUID], assigned: bool
    ) -> None:
        if assigned:
            stmt = (
                pg_insert(UserModule)
                .values([{"user_id": user_id, "module_id": mid} for mid in module_ids])
                .on_conflict_do_nothing(index_elements=["user_id", "module_id"])
            )
            await self._session.execute(stmt)
        else:
            await self._session.execute(
                delete(UserModule).where(
                    UserModule.user_id == user_id, UserModule.module_id.in_(module_ids)
                )
            )
        await self._session.commit()

    async def set_user_lessons(
        self, user_id: uuid.UUID, lesson_ids: list[uuid.UUID], assigned: bool
    ) -> None:
        if assigned:
            stmt = (
                pg_insert(UserLesson)
                .values([{"user_id": user_id, "lesson_id": lid} for lid in lesson_ids])
                .on_conflict_do_nothing(index_elements=["user_id", "lesson_id"])
            )
            await self._session.execute(stmt)
        else:
            await self._session.execute(
                delete(UserLesson).where(
                    UserLesson.user_id == user_id, UserLesson.lesson_id.in_(lesson_ids)
                )
            )
        await self._session.commit()
