from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from src.core.prerequisites import would_create_cycle
from src.services.content_blocks_validation import check_link_schemes
from src.services.exceptions import (
    InvalidRequestError,
    LessonChangedError,
    LessonSetMismatchError,
    NotFoundError,
    PayloadTooLargeError,
)
from src.services.lesson_qa import Finding, check_lesson
from src.services.media_blocks import strip_ephemeral

if TYPE_CHECKING:
    from src.db.models import Lesson, Module, Track
    from src.repositories.base import (
        AbstractAssignmentRepository,
        AbstractContentRepository,
        AbstractProjectAdminRepository,
        AbstractUserRepository,
    )

__all__ = ["AssignmentGap", "ContentService", "DeleteImpact"]

# Decision 5.2 option A (2026-09-25): 66/91 live lessons predate
# `validate_content_blocks`'s nested-id rule, so a structural gate would make
# them unsavable. Human saves get a size ceiling only, not structural
# validation; option B (reject only regressions) follows the nested-id
# backfill as a separate future task.
MAX_LESSON_BLOCKS_BYTES = 1_048_576


@dataclass(frozen=True)
class DeleteImpact:
    """What a delete takes with it: the warning's counts (spec 2026-10-05)."""

    modules: int
    lessons: int
    learners_assigned: int
    learners_with_progress: int


@dataclass(frozen=True)
class AssignmentGap:
    """Lessons of a module that some learner holding the module lacks."""

    lesson_ids: list[uuid.UUID]
    learner_count: int
    missing_pairs: int


class ContentService:
    """Admin content management. All sort_order arithmetic happens here, inside
    one transaction per mutation (fixes legacy A4/DB6 races and B5's N updates)."""

    def __init__(
        self,
        content: AbstractContentRepository,
        *,
        assignments: AbstractAssignmentRepository,
        users: AbstractUserRepository,
        project_admins: AbstractProjectAdminRepository,
    ) -> None:
        self._content = content
        # B4: the assignment gap (assign new lessons to learners who hold the
        # module) needs these. Repositories, not services: no service calls.
        self._assignments = assignments
        self._users = users
        self._project_admins = project_admins

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
        # Maturity gate for a new track: tool tracks require Integrator, general
        # tracks Explorer (same rule the migration/seed apply to existing tracks).
        required_level = "integrator" if track_type == "tool" else "explore"
        return await self._content.create_track(
            name.strip(), track_type, color, sort_order, required_level
        )

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

    async def delete_module(self, module_id: uuid.UUID) -> None:
        module = await self._content.get_module(module_id)
        if module is None:
            raise NotFoundError("Module")
        await self._content.delete_module(module)

    async def create_lesson(self, module_id: uuid.UUID, title: str) -> Lesson:
        if await self._content.get_module(module_id) is None:
            raise NotFoundError("Module")
        max_sort = await self._content.max_lesson_sort_order(module_id)
        sort_order = (max_sort if max_sort is not None else -1) + 1
        return await self._content.create_lesson(module_id, title.strip(), sort_order)

    async def update_lesson(
        self, lesson_id: uuid.UUID, values: dict[str, Any], *, actor_id: uuid.UUID | None = None
    ) -> Lesson:
        """The editor save (and B4's move). `expected_updated_at`, when sent, must
        match the stored one, or LessonChangedError (409) names who changed it and
        when (B5). Every write stamps updated_at/updated_by. A checked save reads
        the row FOR UPDATE, so a concurrent save waits and then sees the change."""
        checked = values.get("expected_updated_at") is not None
        lesson = await (
            self._content.get_lesson_for_update(lesson_id)
            if checked
            else self._content.get_lesson(lesson_id)
        )
        if lesson is None:
            raise NotFoundError("Lesson")
        values = dict(values)
        expected = values.pop("expected_updated_at", None)
        if expected is not None and expected != lesson.updated_at:
            editor = await self._users.get_by_id(lesson.updated_by) if lesson.updated_by else None
            name = f"{editor.first_name} {editor.last_name}".strip() if editor else None
            raise LessonChangedError(lesson.updated_at, name or None)
        stamp = {"updated_at": datetime.now(UTC), "updated_by": actor_id}
        module_id = values.pop("module_id", None)
        if module_id is not None and module_id != lesson.module_id:
            if await self._content.get_module(module_id) is None:
                raise NotFoundError("Module")
            lesson = await self._content.move_lesson(lesson, module_id)
        if not values:
            return await self._content.update_lesson(lesson, stamp) if module_id else lesson
        if "content_blocks" in values:
            # Scheme-only validation, NOT the full structural validator: most of
            # the live corpus predates that validator (see review 6.8), so
            # applying it here would block ordinary saves. The scheme allowlist
            # is narrow enough to be safe and is the only guard on this path --
            # an admin pasting MDX produced by the AI would otherwise bypass the
            # proposal pipeline's check entirely.
            scheme_errors = check_link_schemes(values["content_blocks"])
            if scheme_errors:
                raise InvalidRequestError("; ".join(scheme_errors[:5]))
            # Ephemeral SAS urls (stamped on read) must never persist, even
            # when storage is unconfigured — the editor may echo a stale one
            # back verbatim, and stale urls in the JSONB would go stale forever.
            blocks = strip_ephemeral(values["content_blocks"])
            values = {**values, "content_blocks": blocks}
            # Size ceiling only, not structural validation (see
            # MAX_LESSON_BLOCKS_BYTES above) — measured on what will actually
            # be persisted, after the scheme check and the SAS strip so an
            # echoed url never counts against the caller.
            size = len(json.dumps(blocks, ensure_ascii=False, separators=(",", ":")).encode())
            if size > MAX_LESSON_BLOCKS_BYTES:
                raise PayloadTooLargeError(MAX_LESSON_BLOCKS_BYTES, what="Lesson content")
        return await self._content.update_lesson(lesson, {**values, **stamp})

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

    # -- B4 structure editing (spec 2026-10-05) ------------------------------

    async def update_track(self, track_id: uuid.UUID, values: dict[str, Any]) -> Track:
        """Type and required level are independent after creation: editing one
        never changes the other."""
        track = await self._content.get_track(track_id)
        if track is None:
            raise NotFoundError("Track")
        if "name" in values:
            values = {**values, "name": values["name"].strip()}
        return await self._content.update_track(track, values)

    async def delete_track(self, track_id: uuid.UUID) -> None:
        track = await self._content.get_track(track_id)
        if track is None:
            raise NotFoundError("Track")
        await self._content.delete_track(track)

    async def reorder_tracks(self, track_ids: list[uuid.UUID]) -> None:
        current = {track.id for track in await self._content.list_tracks()}
        if len(track_ids) != len(current) or set(track_ids) != current:
            raise InvalidRequestError("track_ids must contain exactly every track id once")
        await self._content.set_track_orders([(tid, i) for i, tid in enumerate(track_ids)])

    async def update_module(self, module_id: uuid.UUID, values: dict[str, Any]) -> Module:
        """title/description edit in place; a different track_id moves the
        module to the end of that track. Moving to its own track is a no-op."""
        module = await self._content.get_module(module_id)
        if module is None:
            raise NotFoundError("Module")
        values = dict(values)
        track_id = values.pop("track_id", None)
        if track_id is not None and track_id != module.track_id:
            if await self._content.get_track(track_id) is None:
                raise NotFoundError("Track")
            module = await self._content.move_module(module, track_id)
        if "title" in values:
            values["title"] = values["title"].strip()
        if values:
            module = await self._content.update_module(module, values)
        return module

    async def reorder_modules(self, track_id: uuid.UUID, module_ids: list[uuid.UUID]) -> None:
        if await self._content.get_track(track_id) is None:
            raise NotFoundError("Track")
        current = {module.id for module in await self._content.list_modules(track_id)}
        if len(module_ids) != len(current) or set(module_ids) != current:
            raise InvalidRequestError("module_ids must contain exactly the track's module ids once")
        await self._content.set_module_orders([(mid, i) for i, mid in enumerate(module_ids)])

    async def set_prerequisites(
        self, module_id: uuid.UUID, prerequisite_ids: list[uuid.UUID]
    ) -> None:
        """Replace the set. Unknown ids → 404; a self-loop or a cycle → 400
        naming the module. Cross-track prerequisites stay allowed."""
        module = await self._content.get_module(module_id)
        if module is None:
            raise NotFoundError("Module")
        deduped = list(dict.fromkeys(prerequisite_ids))
        if deduped and await self._content.count_modules_by_ids(deduped) != len(deduped):
            raise NotFoundError("Prerequisite module")
        edges = [
            (p.module_id, p.prerequisite_module_id)
            for p in await self._content.list_prerequisites()
        ]
        if would_create_cycle(edges, module_id, deduped):
            msg = f'This would make "{module.title}" depend on itself.'
            raise InvalidRequestError(msg)
        await self._content.set_prerequisites(module_id, deduped)

    async def track_impact(self, track_id: uuid.UUID) -> DeleteImpact:
        if await self._content.get_track(track_id) is None:
            raise NotFoundError("Track")
        module_ids = {m.id for m in await self._content.list_modules(track_id)}
        return await self._impact(len(module_ids), module_ids)

    async def module_impact(self, module_id: uuid.UUID) -> DeleteImpact:
        if await self._content.get_module(module_id) is None:
            raise NotFoundError("Module")
        return await self._impact(0, {module_id})

    async def _impact(self, modules: int, module_ids: set[uuid.UUID]) -> DeleteImpact:
        lesson_ids = [
            le.id
            for le in await self._content.list_lesson_summaries()
            if le.module_id in module_ids
        ]
        assigned, with_progress = await self._content.learner_counts_for_lessons(lesson_ids)
        return DeleteImpact(modules, len(lesson_ids), assigned, with_progress)

    async def content_tree(self) -> list[dict[str, Any]]:
        """Tracks → modules → lessons in display order, for the admin Content
        page. Four reads, whatever the size of the tree."""
        modules = await self._content.list_modules()
        lessons = await self._content.list_lesson_summaries()
        prerequisites: dict[uuid.UUID, list[uuid.UUID]] = {}
        for link in await self._content.list_prerequisites():
            prerequisites.setdefault(link.module_id, []).append(link.prerequisite_module_id)
        lessons_by_module: dict[uuid.UUID, list[dict[str, Any]]] = {}
        for lesson in lessons:
            lessons_by_module.setdefault(lesson.module_id, []).append(
                {"id": lesson.id, "title": lesson.title, "sort_order": lesson.sort_order}
            )
        modules_by_track: dict[uuid.UUID, list[dict[str, Any]]] = {}
        for module in modules:
            module_lessons = lessons_by_module.get(module.id, [])
            modules_by_track.setdefault(module.track_id, []).append(
                {
                    "id": module.id,
                    "title": module.title,
                    "description": module.description,
                    "sort_order": module.sort_order,
                    "prerequisite_ids": prerequisites.get(module.id, []),
                    "lesson_count": len(module_lessons),
                    "lessons": module_lessons,
                }
            )
        return [
            {
                "id": track.id,
                "name": track.name,
                "color": track.color,
                "track_type": track.track_type,
                "required_level": track.required_level,
                "is_introduction": track.is_introduction,
                "sort_order": track.sort_order,
                "modules": modules_by_track.get(track.id, []),
            }
            for track in await self._content.list_tracks()
        ]

    async def assignment_gap(
        self, module_id: uuid.UUID, project_id: uuid.UUID | None
    ) -> AssignmentGap:
        missing, lesson_order = await self._missing_pairs(module_id, project_id)
        lessons = {lesson_id for _, lesson_id in missing}
        return AssignmentGap(
            lesson_ids=[lid for lid in lesson_order if lid in lessons],
            learner_count=len({user_id for user_id, _ in missing}),
            missing_pairs=len(missing),
        )

    async def assign_gap(self, module_id: uuid.UUID, project_id: uuid.UUID | None) -> int:
        """Insert exactly the missing pairs, stamped like the Assignments page.
        Never removes a row."""
        missing, _ = await self._missing_pairs(module_id, project_id)
        return await self._assignments.add_user_lesson_pairs(missing, assigned_via="manual")

    async def _missing_pairs(
        self, module_id: uuid.UUID, project_id: uuid.UUID | None
    ) -> tuple[list[tuple[uuid.UUID, uuid.UUID]], list[uuid.UUID]]:
        if await self._content.get_module(module_id) is None:
            raise NotFoundError("Module")
        lesson_order = [
            le.id for le in await self._content.list_lesson_summaries() if le.module_id == module_id
        ]
        holders = await self._assignments.user_ids_with_module(module_id)
        if project_id is not None:
            # The B1 rule: a project's learners are its members minus power
            # admins and the project's own admins.
            staff = await self._project_admins.admin_ids_for_project(project_id)
            members = {
                user.id
                for user, _, _ in await self._users.list_with_org_names(project_id)
                if user.role != "admin" and user.id not in staff
            }
            holders &= members
        if not holders or not lesson_order:
            return [], lesson_order
        have = {
            (link.user_id, link.lesson_id)
            for link in await self._assignments.user_lessons_for_users(sorted(holders))
        }
        missing = [
            (user_id, lesson_id)
            for user_id in sorted(holders)
            for lesson_id in lesson_order
            if (user_id, lesson_id) not in have
        ]
        return missing, lesson_order

    async def check_lesson(self, lesson_id: uuid.UUID, blocks: list[Any]) -> list[Finding]:
        """The house-style checks on unsaved blocks (B5). Read-only."""
        if await self._content.get_lesson(lesson_id) is None:
            raise NotFoundError("Lesson")
        return check_lesson(blocks)
