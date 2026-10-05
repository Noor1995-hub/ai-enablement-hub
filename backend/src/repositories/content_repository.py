from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import delete, func, select, tuple_, update
from sqlalchemy.orm import load_only

from src.db.models import Lesson, LessonProgress, Module, ModulePrerequisite, Track, UserLesson
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
        self, name: str, track_type: str, color: str | None, sort_order: int, required_level: str
    ) -> Track:
        track = Track(
            name=name,
            track_type=track_type,
            color=color,
            sort_order=sort_order,
            required_level=required_level,
        )
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

    async def next_module_in_track(
        self, track_id: uuid.UUID, sort_order: int, module_id: uuid.UUID
    ) -> Module | None:
        # `sort_order` alone is not a total order: live data holds tracks with
        # two modules sharing a sort_order. Comparing the full (sort_order, id)
        # tuple against the current module's own tuple makes "next" well
        # defined even for a tie, instead of skipping whichever tied module
        # happens to sort first.
        result = await self._session.execute(
            select(Module)
            .where(
                Module.track_id == track_id,
                tuple_(Module.sort_order, Module.id) > (sort_order, module_id),
            )
            .order_by(Module.sort_order, Module.id)
            .limit(1)
        )
        return result.scalars().first()

    async def list_prerequisites(self) -> list[ModulePrerequisite]:
        result = await self._session.execute(select(ModulePrerequisite))
        return list(result.scalars().all())

    async def delete_module(self, module: Module) -> None:
        track_id = module.track_id
        await self._session.delete(module)
        await self._session.flush()
        siblings = (
            (
                await self._session.execute(
                    select(Module.id)
                    .where(Module.track_id == track_id)
                    .order_by(Module.sort_order, Module.id)
                )
            )
            .scalars()
            .all()
        )
        await self._write_orders(Module, list(siblings))
        await self._session.commit()

    # -- lessons -----------------------------------------------------------

    async def list_lessons(self, module_id: uuid.UUID) -> list[Lesson]:
        result = await self._session.execute(
            select(Lesson)
            .where(Lesson.module_id == module_id)
            .order_by(Lesson.sort_order, Lesson.id)
        )
        return list(result.scalars().all())

    async def list_lesson_summaries(self) -> list[Lesson]:
        result = await self._session.execute(
            select(Lesson)
            .options(load_only(Lesson.id, Lesson.module_id, Lesson.title, Lesson.sort_order))
            .order_by(Lesson.sort_order, Lesson.id)
        )
        return list(result.scalars().all())

    async def count_tracks_by_ids(self, track_ids: list[uuid.UUID]) -> int:
        result = await self._session.execute(
            select(func.count()).select_from(Track).where(Track.id.in_(track_ids))
        )
        return result.scalar_one()

    async def count_modules_by_ids(self, module_ids: list[uuid.UUID]) -> int:
        result = await self._session.execute(
            select(func.count()).select_from(Module).where(Module.id.in_(module_ids))
        )
        return result.scalar_one()

    async def count_lessons_by_ids(self, lesson_ids: list[uuid.UUID]) -> int:
        result = await self._session.execute(
            select(func.count()).select_from(Lesson).where(Lesson.id.in_(lesson_ids))
        )
        return result.scalar_one()

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

    async def stage_lesson_update(self, lesson: Lesson, values: dict[str, Any]) -> Lesson:
        for field, value in values.items():
            setattr(lesson, field, value)
        await self._session.flush()
        return lesson

    async def update_lesson(self, lesson: Lesson, values: dict[str, Any]) -> Lesson:
        await self.stage_lesson_update(lesson, values)
        await self._session.commit()
        await self._session.refresh(lesson)
        return lesson

    async def delete_lesson(self, lesson: Lesson) -> None:
        await self._session.delete(lesson)
        await self._session.commit()

    async def set_lesson_orders(self, orders: list[tuple[uuid.UUID, int]]) -> None:
        if not orders:
            return
        # One executemany round-trip, not M sequential UPDATEs: SQLAlchemy's ORM
        # bulk-update-by-primary-key takes a list of dicts that each carry the pk
        # plus the columns to set. asyncpg's executemany runs one UPDATE per row, so a
        # permutation passes through duplicate sort_orders; that is safe only because
        # uq_lessons_module_id_sort_order is DEFERRABLE INITIALLY DEFERRED (checked at commit).
        await self._session.execute(
            update(Lesson),
            [{"id": lesson_id, "sort_order": sort_order} for lesson_id, sort_order in orders],
        )
        await self._session.commit()

    # -- B4 structure operations (spec 2026-10-05). Each is one commit; the
    # deferred unique constraints let a renumber pass through duplicates.

    async def update_track(self, track: Track, values: dict[str, Any]) -> Track:
        for field, value in values.items():
            setattr(track, field, value)
        await self._session.commit()
        await self._session.refresh(track)
        return track

    async def delete_track(self, track: Track) -> None:
        await self._session.delete(track)
        await self._session.flush()
        remaining = (
            (await self._session.execute(select(Track.id).order_by(Track.sort_order, Track.id)))
            .scalars()
            .all()
        )
        await self._write_orders(Track, list(remaining))
        await self._session.commit()

    async def set_track_orders(self, orders: list[tuple[uuid.UUID, int]]) -> None:
        if orders:
            await self._session.execute(
                update(Track), [{"id": i, "sort_order": o} for i, o in orders]
            )
        await self._session.commit()

    async def update_module(self, module: Module, values: dict[str, Any]) -> Module:
        for field, value in values.items():
            setattr(module, field, value)
        await self._session.commit()
        await self._session.refresh(module)
        return module

    async def move_module(self, module: Module, track_id: uuid.UUID) -> Module:
        source = module.track_id
        top = (
            await self._session.execute(
                select(func.max(Module.sort_order)).where(Module.track_id == track_id)
            )
        ).scalar_one()
        module.track_id = track_id
        module.sort_order = 0 if top is None else top + 1
        await self._session.flush()
        siblings = (
            (
                await self._session.execute(
                    select(Module.id)
                    .where(Module.track_id == source)
                    .order_by(Module.sort_order, Module.id)
                )
            )
            .scalars()
            .all()
        )
        await self._write_orders(Module, list(siblings))
        await self._session.commit()
        await self._session.refresh(module)
        return module

    async def set_module_orders(self, orders: list[tuple[uuid.UUID, int]]) -> None:
        if orders:
            await self._session.execute(
                update(Module), [{"id": i, "sort_order": o} for i, o in orders]
            )
        await self._session.commit()

    async def set_prerequisites(
        self, module_id: uuid.UUID, prerequisite_ids: list[uuid.UUID]
    ) -> None:
        await self._session.execute(
            delete(ModulePrerequisite).where(ModulePrerequisite.module_id == module_id)
        )
        self._session.add_all(
            ModulePrerequisite(module_id=module_id, prerequisite_module_id=prereq_id)
            for prereq_id in prerequisite_ids
        )
        await self._session.commit()

    async def move_lesson(self, lesson: Lesson, module_id: uuid.UUID) -> Lesson:
        source = lesson.module_id
        top = (
            await self._session.execute(
                select(func.max(Lesson.sort_order)).where(Lesson.module_id == module_id)
            )
        ).scalar_one()
        lesson.module_id = module_id
        lesson.sort_order = 0 if top is None else top + 1
        await self._session.flush()
        siblings = (
            (
                await self._session.execute(
                    select(Lesson.id)
                    .where(Lesson.module_id == source)
                    .order_by(Lesson.sort_order, Lesson.id)
                )
            )
            .scalars()
            .all()
        )
        await self._write_orders(Lesson, list(siblings))
        await self._session.commit()
        await self._session.refresh(lesson)
        return lesson

    async def learner_counts_for_lessons(self, lesson_ids: list[uuid.UUID]) -> tuple[int, int]:
        if not lesson_ids:
            return (0, 0)
        assigned = (
            await self._session.execute(
                select(func.count(func.distinct(UserLesson.user_id))).where(
                    UserLesson.lesson_id.in_(lesson_ids)
                )
            )
        ).scalar_one()
        with_progress = (
            await self._session.execute(
                select(func.count(func.distinct(LessonProgress.user_id))).where(
                    LessonProgress.lesson_id.in_(lesson_ids)
                )
            )
        ).scalar_one()
        return (int(assigned), int(with_progress))

    async def _write_orders(
        self, model: type[Track | Module | Lesson], ids: list[uuid.UUID]
    ) -> None:
        """0..n-1 in the given order; no commit (callers commit once)."""
        if ids:
            await self._session.execute(
                update(model), [{"id": i, "sort_order": o} for o, i in enumerate(ids)]
            )

    async def lesson_context(
        self, lesson_ids: list[uuid.UUID]
    ) -> dict[uuid.UUID, tuple[str, uuid.UUID, str, str]]:
        if not lesson_ids:
            return {}
        query = (
            select(
                Lesson.id,
                Module.title,
                Track.id,
                Track.name,
                Track.required_level,
            )
            .join(Module, Module.id == Lesson.module_id)
            .join(Track, Track.id == Module.track_id)
            .where(Lesson.id.in_(lesson_ids))
        )
        rows = (await self._session.execute(query)).all()
        return {row[0]: (row[1], row[2], row[3], row[4]) for row in rows}
