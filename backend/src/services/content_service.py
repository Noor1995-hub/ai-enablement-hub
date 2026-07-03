from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

from src.services.exceptions import (
    InvalidRequestError,
    LessonSetMismatchError,
    NotFoundError,
)

if TYPE_CHECKING:
    from src.db.models import Lesson, Module, Track
    from src.repositories.base import AbstractContentRepository

__all__ = ["ContentService"]


class ContentService:
    """Admin content management. All sort_order arithmetic happens here, inside
    one transaction per mutation (fixes legacy A4/DB6 races and B5's N updates)."""

    def __init__(self, content: AbstractContentRepository) -> None:
        self._content = content

    # -- reads shared with learners (auth level U) ---------------------------

    async def list_tracks(self) -> list[Track]:
        return await self._content.list_tracks()

    async def list_track_modules(self, track_id: uuid.UUID) -> list[Module]:
        if await self._content.get_track(track_id) is None:
            raise NotFoundError("Track")
        return await self._content.list_modules(track_id)

    # -- admin writes --------------------------------------------------------

    async def create_track(self, name: str, track_type: str, color: str | None) -> Track:
        max_sort = await self._content.max_track_sort_order()
        sort_order = (max_sort if max_sort is not None else -1) + 1
        return await self._content.create_track(name.strip(), track_type, color, sort_order)

    async def create_module(
        self,
        track_id: uuid.UUID,
        title: str,
        after_module_id: uuid.UUID | None,
        prerequisite_ids: list[uuid.UUID],
    ) -> Module:
        """Insert after a chosen predecessor (shifting successors +1) or append.

        Shift + insert + prerequisite links commit together.
        """
        if await self._content.get_track(track_id) is None:
            raise NotFoundError("Track")
        deduped: list[uuid.UUID] = []
        for prereq_id in prerequisite_ids:
            if prereq_id not in deduped:
                deduped.append(prereq_id)
        for prereq_id in deduped:
            if await self._content.get_module(prereq_id) is None:
                raise NotFoundError("Prerequisite module")

        if after_module_id is not None:
            after = await self._content.get_module(after_module_id)
            if after is None:
                raise NotFoundError("Module")
            if after.track_id != track_id:
                msg = "after_module_id must belong to the same track"
                raise InvalidRequestError(msg)
            sort_order = after.sort_order + 1
            await self._content.shift_module_sort_orders(track_id, sort_order)
        else:
            max_sort = await self._content.max_module_sort_order(track_id)
            sort_order = (max_sort if max_sort is not None else -1) + 1

        return await self._content.create_module(track_id, title.strip(), sort_order, deduped)

    async def create_lesson(self, module_id: uuid.UUID, title: str) -> Lesson:
        if await self._content.get_module(module_id) is None:
            raise NotFoundError("Module")
        max_sort = await self._content.max_lesson_sort_order(module_id)
        sort_order = (max_sort if max_sort is not None else -1) + 1
        return await self._content.create_lesson(module_id, title.strip(), sort_order)

    async def update_lesson(self, lesson_id: uuid.UUID, values: dict[str, Any]) -> Lesson:
        lesson = await self._content.get_lesson(lesson_id)
        if lesson is None:
            raise NotFoundError("Lesson")
        return await self._content.update_lesson(lesson, values)

    async def delete_lesson(self, lesson_id: uuid.UUID) -> None:
        lesson = await self._content.get_lesson(lesson_id)
        if lesson is None:
            raise NotFoundError("Lesson")
        await self._content.delete_lesson(lesson)

    async def reorder_lessons(self, module_id: uuid.UUID, lesson_ids: list[uuid.UUID]) -> None:
        """Assign index positions in one transaction (replaces ModulePanel's N
        parallel updates — fixes legacy B5). The id list must be a permutation
        of the module's lessons."""
        if await self._content.get_module(module_id) is None:
            raise NotFoundError("Module")
        current = await self._content.list_lessons(module_id)
        if len(lesson_ids) != len(current) or set(lesson_ids) != {le.id for le in current}:
            raise LessonSetMismatchError
        await self._content.set_lesson_orders(
            [(lesson_id, index) for index, lesson_id in enumerate(lesson_ids)]
        )
