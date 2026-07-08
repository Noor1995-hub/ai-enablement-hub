from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any, Literal

from src.core.constants import LEVEL_RANK
from src.services.exceptions import NotFoundError

if TYPE_CHECKING:
    from src.db.models import Lesson
    from src.repositories.base import (
        AbstractAssignmentRepository,
        AbstractContentRepository,
        AbstractProgressRepository,
    )

__all__ = ["LearningService", "LearningStatus"]

LearningStatus = Literal["not_started", "in_progress", "complete"]


class LearningService:
    """Learner-facing aggregates. Every query is hardwired to the caller's
    user id — no user identifier ever comes from the request (authz iron rule)."""

    def __init__(
        self,
        content: AbstractContentRepository,
        assignments: AbstractAssignmentRepository,
        progress: AbstractProgressRepository,
    ) -> None:
        self._content = content
        self._assignments = assignments
        self._progress = progress

    async def graph(self, user_id: uuid.UUID, effective_level: str | None = None) -> dict[str, Any]:
        """The one aggregate replacing LearningPath's legacy 7-query chain.

        lesson_count / completed_lesson_count only cover lessons ASSIGNED to
        the caller — the popup's "X of N lessons" is the learner's own
        curriculum, not the module's full inventory.

        `effective_level` is the caller's maturity (from MaturityService). Each
        track gets `unlocked_by_maturity = effective_level covers required_level`;
        modules inherit their track's flag. Maturity gates whole tracks;
        prerequisites still gate modules *within* an unlocked track (frontend)."""
        tracks = await self._content.list_tracks()
        modules = await self._content.list_modules()
        prerequisites = await self._content.list_prerequisites()
        assigned_tracks = await self._assignments.track_ids_for_user(user_id)
        assigned_modules = await self._assignments.module_ids_for_user(user_id)
        lesson_counts = await self._assignments.assigned_lesson_counts_by_module(user_id)

        caller_rank = LEVEL_RANK[effective_level] if effective_level is not None else None

        def track_unlocked(required_level: str) -> bool:
            return caller_rank is not None and LEVEL_RANK[required_level] <= caller_rank

        track_unlock = {track.id: track_unlocked(track.required_level) for track in tracks}

        return {
            "tracks": [
                {
                    "id": track.id,
                    "name": track.name,
                    "sort_order": track.sort_order,
                    "track_type": track.track_type,
                    "color": track.color,
                    "assigned": track.id in assigned_tracks,
                    "required_level": track.required_level,
                    "unlocked_by_maturity": track_unlock[track.id],
                }
                for track in tracks
            ],
            "modules": [
                {
                    "id": module.id,
                    "track_id": module.track_id,
                    "title": module.title,
                    "sort_order": module.sort_order,
                    "assigned": module.id in assigned_modules,
                    "lesson_count": lesson_counts.get(module.id, (0, 0))[0],
                    "completed_lesson_count": lesson_counts.get(module.id, (0, 0))[1],
                    "unlocked_by_maturity": track_unlock.get(module.track_id, False),
                }
                for module in modules
            ],
            "prerequisites": [
                {
                    "module_id": prereq.module_id,
                    "prerequisite_module_id": prereq.prerequisite_module_id,
                }
                for prereq in prerequisites
            ],
            "maturity_level": effective_level,
        }

    async def learning_status(self, user_id: uuid.UUID) -> LearningStatus:
        """Overall learning-path status for JourneyHome's card, over the caller's
        ASSIGNED lessons only (a completed LessonProgress row == a done lesson,
        the same definition the graph's completed_lesson_count uses):
        not_started until the first lesson is completed, complete once every
        assigned lesson is done, in_progress in between."""
        counts = await self._assignments.assigned_lesson_counts_by_module(user_id)
        total = sum(count for count, _ in counts.values())
        done = sum(completed for _, completed in counts.values())
        if total == 0 or done == 0:
            return "not_started"
        if done >= total:
            return "complete"
        return "in_progress"

    async def module_lessons(self, user_id: uuid.UUID, module_id: uuid.UUID) -> dict[str, Any]:
        """Lessons of a module with per-lesson completion and per-caller
        `assigned` flags; next = first uncompleted ASSIGNED lesson. Returns ALL
        lessons (graph pattern): learner views filter on `assigned`, the admin
        ModulePanel shows everything."""
        if await self._content.get_module(module_id) is None:
            raise NotFoundError("Module")
        lessons = await self._content.list_lessons(module_id)
        completed = await self._progress.completed_lesson_ids(user_id, [le.id for le in lessons])
        assigned = await self._assignments.lesson_ids_for_user(user_id)
        next_lesson = next(
            (le for le in lessons if le.id in assigned and le.id not in completed), None
        )
        return {
            "lessons": [
                {
                    "id": lesson.id,
                    "title": lesson.title,
                    "sort_order": lesson.sort_order,
                    "completed": lesson.id in completed,
                    "assigned": lesson.id in assigned,
                }
                for lesson in lessons
            ],
            "next_lesson_id": next_lesson.id if next_lesson is not None else None,
        }

    async def lesson_detail(self, user_id: uuid.UUID, lesson_id: uuid.UUID) -> dict[str, Any]:
        """One response for LessonPage, collapsing its sequential prefetch chain
        (fixes legacy B4). Next-destination semantics match the old page — next
        lesson in the module, else first lesson of the next module in the track —
        but only lessons ASSIGNED to the caller qualify as a destination."""
        lesson = await self._content.get_lesson(lesson_id)
        if lesson is None:
            raise NotFoundError("Lesson")
        module = await self._content.get_module(lesson.module_id)
        if module is None:  # pragma: no cover - FK guarantees the module exists
            raise NotFoundError("Module")

        progress = await self._progress.get(user_id, lesson_id)
        assigned = await self._assignments.lesson_ids_for_user(user_id)

        next_module_id: uuid.UUID | None = None
        next_lesson: Lesson | None = next(
            (
                le
                for le in await self._content.list_lessons(lesson.module_id)
                if le.sort_order > lesson.sort_order and le.id in assigned
            ),
            None,
        )
        if next_lesson is None:
            next_module = await self._content.next_module_in_track(
                module.track_id, module.sort_order
            )
            if next_module is not None:
                next_module_id = next_module.id
                next_lesson = next(
                    (
                        le
                        for le in await self._content.list_lessons(next_module.id)
                        if le.id in assigned
                    ),
                    None,
                )

        return {
            "id": lesson.id,
            "module_id": lesson.module_id,
            "title": lesson.title,
            "sort_order": lesson.sort_order,
            "content_blocks": lesson.content_blocks,
            "module": {
                "id": module.id,
                "title": module.title,
                "track_id": module.track_id,
                "sort_order": module.sort_order,
            },
            "my_answers": progress.answers if progress is not None else None,
            "next_lesson_id": next_lesson.id if next_lesson is not None else None,
            "next_module_id": next_module_id,
        }

    async def save_progress(
        self, user_id: uuid.UUID, lesson_id: uuid.UUID, answers: dict[str, Any] | None
    ) -> None:
        if await self._content.get_lesson(lesson_id) is None:
            raise NotFoundError("Lesson")
        await self._progress.upsert(user_id, lesson_id, answers or {})
