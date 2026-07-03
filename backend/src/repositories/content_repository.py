from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import func, select, update

from src.db.models import Lesson, Module, ModulePrerequisite, Track
from src.repositories.base import AbstractContentRepository

__all__ = ["ContentRepository"]


class ContentRepository(AbstractContentRepository):
    # -- tracks ------------------------------------------------------------

    async def list_tracks(self) -> list[Track]:
        result = await self._session.execute(select(Track).order_by(Track.sort_order, Track.id))
        return list(result.scalars().all())

    async def get_track(self, track_id: uuid.UUID) -> Track | None:
        result = await self._session.execute(select(Track).where(Track.id == track_id))
        return result.scalar_one_or_none()

    async def create_track(
        self, name: str, track_type: str, color: str | None, sort_order: int
    ) -> Track:
        track = Track(name=name, track_type=track_type, color=color, sort_order=sort_order)
        self._session.add(track)
        await self._session.commit()
        await self._session.refresh(track)
        return track

    async def max_track_sort_order(self) -> int | None:
        result = await self._session.execute(select(func.max(Track.sort_order)))
        return result.scalar_one()

    # -- modules -----------------------------------------------------------

    async def list_modules(self, track_id: uuid.UUID | None = None) -> list[Module]:
        stmt = select(Module).order_by(Module.sort_order, Module.id)
        if track_id is not None:
            stmt = stmt.where(Module.track_id == track_id)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_module(self, module_id: uuid.UUID) -> Module | None:
        result = await self._session.execute(select(Module).where(Module.id == module_id))
        return result.scalar_one_or_none()

    async def max_module_sort_order(self, track_id: uuid.UUID) -> int | None:
        result = await self._session.execute(
            select(func.max(Module.sort_order)).where(Module.track_id == track_id)
        )
        return result.scalar_one()

    async def shift_module_sort_orders(self, track_id: uuid.UUID, from_sort_order: int) -> None:
        # No commit here: create_module commits the shift + insert atomically (fixes DB6).
        await self._session.execute(
            update(Module)
            .where(Module.track_id == track_id, Module.sort_order >= from_sort_order)
            .values(sort_order=Module.sort_order + 1)
        )

    async def create_module(
        self,
        track_id: uuid.UUID,
        title: str,
        sort_order: int,
        prerequisite_ids: list[uuid.UUID],
    ) -> Module:
        module = Module(track_id=track_id, title=title, sort_order=sort_order)
        self._session.add(module)
        await self._session.flush()
        self._session.add_all(
            ModulePrerequisite(module_id=module.id, prerequisite_module_id=prereq_id)
            for prereq_id in prerequisite_ids
        )
        await self._session.commit()
        await self._session.refresh(module)
        return module

    async def next_module_in_track(self, track_id: uuid.UUID, sort_order: int) -> Module | None:
        result = await self._session.execute(
            select(Module)
            .where(Module.track_id == track_id, Module.sort_order > sort_order)
            .order_by(Module.sort_order, Module.id)
            .limit(1)
        )
        return result.scalars().first()

    async def list_prerequisites(self) -> list[ModulePrerequisite]:
        result = await self._session.execute(select(ModulePrerequisite))
        return list(result.scalars().all())

    # -- lessons -----------------------------------------------------------

    async def list_lessons(self, module_id: uuid.UUID) -> list[Lesson]:
        result = await self._session.execute(
            select(Lesson)
            .where(Lesson.module_id == module_id)
            .order_by(Lesson.sort_order, Lesson.id)
        )
        return list(result.scalars().all())

    async def lesson_counts_by_module(self) -> dict[uuid.UUID, int]:
        result = await self._session.execute(
            select(Lesson.module_id, func.count()).group_by(Lesson.module_id)
        )
        return {row[0]: row[1] for row in result.all()}

    async def get_lesson(self, lesson_id: uuid.UUID) -> Lesson | None:
        result = await self._session.execute(select(Lesson).where(Lesson.id == lesson_id))
        return result.scalar_one_or_none()

    async def max_lesson_sort_order(self, module_id: uuid.UUID) -> int | None:
        result = await self._session.execute(
            select(func.max(Lesson.sort_order)).where(Lesson.module_id == module_id)
        )
        return result.scalar_one()

    async def create_lesson(self, module_id: uuid.UUID, title: str, sort_order: int) -> Lesson:
        lesson = Lesson(module_id=module_id, title=title, sort_order=sort_order)
        self._session.add(lesson)
        await self._session.commit()
        await self._session.refresh(lesson)
        return lesson

    async def update_lesson(self, lesson: Lesson, values: dict[str, Any]) -> Lesson:
        for field, value in values.items():
            setattr(lesson, field, value)
        await self._session.commit()
        await self._session.refresh(lesson)
        return lesson

    async def delete_lesson(self, lesson: Lesson) -> None:
        await self._session.delete(lesson)
        await self._session.commit()

    async def next_lesson_in_module(self, module_id: uuid.UUID, sort_order: int) -> Lesson | None:
        result = await self._session.execute(
            select(Lesson)
            .where(Lesson.module_id == module_id, Lesson.sort_order > sort_order)
            .order_by(Lesson.sort_order, Lesson.id)
            .limit(1)
        )
        return result.scalars().first()

    async def first_lesson(self, module_id: uuid.UUID) -> Lesson | None:
        result = await self._session.execute(
            select(Lesson)
            .where(Lesson.module_id == module_id)
            .order_by(Lesson.sort_order, Lesson.id)
            .limit(1)
        )
        return result.scalars().first()

    async def set_lesson_orders(self, orders: list[tuple[uuid.UUID, int]]) -> None:
        for lesson_id, sort_order in orders:
            await self._session.execute(
                update(Lesson).where(Lesson.id == lesson_id).values(sort_order=sort_order)
            )
        await self._session.commit()
