from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, Literal

from src.core.attention import attention_for
from src.core.constants import advance_level
from src.services.exceptions import EmailAlreadyRegisteredError, NotFoundError

if TYPE_CHECKING:
    from src.db.models import User
    from src.repositories.base import (
        AbstractAssignmentRepository,
        AbstractAuthSessionRepository,
        AbstractContentRepository,
        AbstractOrgRepository,
        AbstractProgressRepository,
        AbstractSurveyRepository,
        AbstractUserRepository,
    )

__all__ = ["AdminUserService"]


class AdminUserService:
    """Admin user directory: listing, invites, reset links, roles, deletion,
    and track/module assignment — everything behind require_admin.

    Token issuance (invite/reset) is deliberately NOT done here: this service
    only creates/looks up the user, and the router mints the action token via
    TokenService — services never call other services."""

    def __init__(
        self,
        users: AbstractUserRepository,
        org: AbstractOrgRepository,
        assignments: AbstractAssignmentRepository,
        content: AbstractContentRepository,
        surveys: AbstractSurveyRepository,
        sessions: AbstractAuthSessionRepository,
        progress: AbstractProgressRepository,
    ) -> None:
        self._users = users
        self._org = org
        self._assignments = assignments
        self._content = content
        self._surveys = surveys
        self._sessions = sessions
        self._progress = progress

    async def list_users(
        self,
        project_id: uuid.UUID | None = None,
        *,
        q: str | None = None,
        status: Literal["active", "invited", "attention"] | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> tuple[list[dict[str, Any]], int]:
        rows = await self._users.list_with_org_names(project_id, q)
        result = await self._enrich_rows(rows)

        # Task 9: status is computed (not a column), so it's filtered here in
        # Python after the enrichment, rather than pushed into SQL — at our
        # scale (tens to low hundreds of users per project) this is a
        # deliberate, documented tradeoff over adding a second query shape.
        if status is not None:
            if status == "active":
                result = [u for u in result if u["activated"]]
            elif status == "invited":
                result = [u for u in result if not u["activated"]]
            else:  # "attention"
                result = [u for u in result if u["needs_attention"]]

        total = len(result)
        page = result[offset : offset + limit] if limit is not None else result[offset:]
        return page, total

    async def get_user_enriched(self, user_id: uuid.UUID) -> dict[str, Any]:
        """One user in the same enriched shape `list_users` yields — the People
        detail screen's read. Before this existed the frontend dug its user out
        of a cached page of the list, so anyone past the first page of a project
        was unreachable; going by id keeps it correct at any project size."""
        row = await self._users.get_with_org_names(user_id)
        if row is None:
            raise NotFoundError("User")
        return (await self._enrich_rows([row]))[0]

    async def _enrich_rows(
        self, rows: list[tuple[User, str | None, str | None]]
    ) -> list[dict[str, Any]]:
        """Directory-grade enrichment (assignments, progress, attention,
        effective maturity) for a set of (user, company_name, project_name)
        rows. Every read below is batched over the row set, so it costs the
        same handful of queries whether `rows` holds one user or all of them."""
        users = [user for user, _, _ in rows]
        user_ids = [user.id for user in users]
        (
            track_map,
            module_map,
            lesson_map,
            default_track_map,
            default_module_map,
            default_lesson_map,
        ) = await self._assignment_maps_for(user_ids)
        # One batched read each — the N+1 per-user scans are gone.
        counts = await self._assignments.assigned_lesson_counts_by_module_for_users(user_ids)
        last_active = await self._sessions.last_used_by_user(user_ids)
        latest = await self._progress.latest_completion_by_user(user_ids)
        surveyed = await self._surveys.user_ids_with_survey(user_ids)
        tracks = await self._content.list_tracks()
        modules = await self._content.list_modules()
        track_name = {track.id: track.name for track in tracks}
        track_level = {track.id: track.required_level for track in tracks}
        module_track = {module.id: module.track_id for module in modules}
        module_level = {
            module.id: track_level[module.track_id]
            for module in modules
            if module.track_id in track_level
        }
        effective = await self._effective_maturity_map(users, counts, module_level)

        now = datetime.now(UTC)
        result: list[dict[str, Any]] = []
        for user, company_name, project_name in rows:
            user_counts = counts.get(user.id, {})
            assigned_total = sum(assigned for assigned, _ in user_counts.values())
            completed_total = sum(completed for _, completed in user_counts.values())
            track_progress: dict[uuid.UUID, tuple[int, int]] = {}
            for mid, (assigned, completed) in user_counts.items():
                tid = module_track.get(mid)
                if tid is None:
                    continue
                prev_assigned, prev_completed = track_progress.get(tid, (0, 0))
                track_progress[tid] = (prev_assigned + assigned, prev_completed + completed)
            activated = user.password_set or user.external_id is not None
            assigned_tracks = track_map.get(user.id, [])
            in_progress = {
                module_track[mid]
                for mid, (assigned, completed) in user_counts.items()
                if assigned > 0 and completed < assigned and mid in module_track
            }
            track_names_in_progress = [
                track_name[tid]
                for tid in assigned_tracks
                if tid in in_progress and tid in track_name
            ]
            # No activated_at column exists — approximate the moment we can prove
            # the account was live as max(created_at, first session's last use).
            last_active_at = last_active.get(user.id)
            activated_known_since = max(user.created_at, last_active_at or user.created_at)
            attention = attention_for(
                now=now,
                created_at=user.created_at,
                activated=activated,
                activated_known_since=activated_known_since,
                has_survey=user.id in surveyed,
                latest_completion=latest.get(user.id),
                assigned_total=assigned_total,
                completed_total=completed_total,
                track_names_in_progress=track_names_in_progress,
            )
            result.append(
                {
                    "id": user.id,
                    "email": user.email,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "role": user.role,
                    "is_active": user.is_active,
                    "password_set": user.password_set,
                    "created_at": user.created_at,
                    "company_id": user.company_id,
                    "project_id": user.project_id,
                    "company_name": company_name,
                    "project_name": project_name,
                    "assigned_track_ids": assigned_tracks,
                    "assigned_module_ids": module_map.get(user.id, []),
                    "assigned_lesson_ids": lesson_map.get(user.id, []),
                    "track_progress": {
                        tid: {"assigned": a, "completed": c}
                        for tid, (a, c) in track_progress.items()
                    },
                    "maturity_override": user.maturity_override,
                    "effective_maturity": effective.get(user.id),
                    "last_active_at": last_active_at,
                    "activated": activated,
                    "assigned_lesson_count": assigned_total,
                    "completed_lesson_count": completed_total,
                    "needs_attention": attention is not None,
                    "attention_reason": attention[1] if attention is not None else None,
                    "default_track_ids": default_track_map.get(user.id, []),
                    "default_module_ids": default_module_map.get(user.id, []),
                    "default_lesson_ids": default_lesson_map.get(user.id, []),
                }
            )

        return result

    async def _effective_maturity_map(
        self,
        users: list[User],
        counts: dict[uuid.UUID, dict[uuid.UUID, tuple[int, int]]],
        module_level: dict[uuid.UUID, str],
    ) -> dict[uuid.UUID, str | None]:
        """user_id → effective maturity, computed live via the shared ladder
        walk (no MaturityService import — services never call services). Base =
        override or a complete survey's score_level; None → no maturity. The
        per-user assigned-lesson `counts` and the module→required_level map are
        passed in (both already fetched once by the caller) so this stays a
        single query."""
        complete = await self._surveys.get_complete_levels([user.id for user in users])
        result: dict[uuid.UUID, str | None] = {}
        for user in users:
            base = user.maturity_override or complete.get(user.id)
            result[user.id] = (
                advance_level(base, module_level, counts.get(user.id, {}))
                if base is not None
                else None
            )
        return result

    async def invite(
        self, email: str, first_name: str, last_name: str, project_id: uuid.UUID
    ) -> User:
        """Create the invited user row; the router mints the invite token."""
        normalised = email.strip().lower()
        if await self._users.get_by_email(normalised) is not None:
            raise EmailAlreadyRegisteredError
        project = await self._org.get_project(project_id)
        if project is None:
            raise NotFoundError("Project")
        user = await self._users.create(
            email=normalised,
            first_name=first_name.strip(),
            last_name=last_name.strip(),
            company_id=project.company_id,
            project_id=project.id,
        )
        await self._materialize_defaults(user.id, project.id)
        return user

    async def existing_emails(self, emails: list[str]) -> set[str]:
        """Subset of the given (normalized) emails that already have a user row."""
        return await self._users.emails_in(emails)

    async def ensure_project(self, project_id: uuid.UUID) -> None:
        """Raise NotFoundError if the project does not exist (bulk-invite preflight)."""
        if await self._org.get_project(project_id) is None:
            raise NotFoundError("Project")

    async def create_invited_users(
        self, project_id: uuid.UUID, rows: list[tuple[str, str, str]]
    ) -> list[User]:
        """Create one invited user per (first_name, last_name, email) row, all
        bound to the project (404 if unknown). Emails already taken — e.g.
        created between the admin's preview and confirm — are skipped. Returns
        the users actually created, in input order; the router mints each one an
        invite token (services never call services)."""
        project = await self._org.get_project(project_id)
        if project is None:
            raise NotFoundError("Project")
        created: list[User] = []
        for first_name, last_name, email in rows:
            if await self._users.get_by_email(email) is not None:
                continue
            user = await self._users.create(
                email=email,
                first_name=first_name,
                last_name=last_name,
                company_id=project.company_id,
                project_id=project.id,
            )
            await self._materialize_defaults(user.id, project.id)
            created.append(user)
        return created

    async def set_role(self, user_id: uuid.UUID, role: str) -> None:
        user = await self._users.get_by_id(user_id)
        if user is None:
            raise NotFoundError("User")
        await self._users.update_role(user, role)

    async def delete_user(self, user_id: uuid.UUID) -> None:
        """Single DELETE; FK cascades wipe tokens, sessions, survey, progress
        and assignments atomically (fixes legacy B2 by construction)."""
        user = await self._users.get_by_id(user_id)
        if user is None:
            raise NotFoundError("User")
        await self._users.delete(user)

    async def set_track_assignment(
        self, user_id: uuid.UUID, track_id: uuid.UUID, assigned: bool
    ) -> None:
        if await self._users.get_by_id(user_id) is None:
            raise NotFoundError("User")
        if await self._content.get_track(track_id) is None:
            raise NotFoundError("Track")
        await self._assignments.set_user_track(user_id, track_id, assigned)
        await self._cascade_to_modules_and_lessons(user_id, [track_id], assigned)

    async def _cascade_module_and_lesson_ids(
        self, track_ids: list[uuid.UUID]
    ) -> tuple[list[uuid.UUID], list[uuid.UUID]]:
        """All module ids under the given tracks, and all lesson ids under those modules."""
        track_id_set = set(track_ids)
        modules = [m for m in await self._content.list_modules() if m.track_id in track_id_set]
        module_ids = [m.id for m in modules]
        return module_ids, await self._cascade_lesson_ids(module_ids)

    async def _cascade_to_modules_and_lessons(
        self,
        user_id: uuid.UUID,
        track_ids: list[uuid.UUID],
        assigned: bool,
        *,
        assigned_via: str = "manual",
    ) -> None:
        module_ids, lesson_ids = await self._cascade_module_and_lesson_ids(track_ids)
        if module_ids:
            await self._assignments.set_user_modules(
                user_id, module_ids, assigned, assigned_via=assigned_via
            )
        if lesson_ids:
            await self._assignments.set_user_lessons(
                user_id, lesson_ids, assigned, assigned_via=assigned_via
            )

    async def set_module_assignment(
        self, user_id: uuid.UUID, module_id: uuid.UUID, assigned: bool
    ) -> None:
        if await self._users.get_by_id(user_id) is None:
            raise NotFoundError("User")
        if await self._content.get_module(module_id) is None:
            raise NotFoundError("Module")
        await self._assignments.set_user_module(user_id, module_id, assigned)
        await self._cascade_to_lessons(user_id, [module_id], assigned)

    async def _cascade_lesson_ids(self, module_ids: list[uuid.UUID]) -> list[uuid.UUID]:
        """All lesson ids under the given modules."""
        module_id_set = set(module_ids)
        lessons = [
            le
            for le in await self._content.list_lesson_summaries()
            if le.module_id in module_id_set
        ]
        return [le.id for le in lessons]

    async def _cascade_to_lessons(
        self,
        user_id: uuid.UUID,
        module_ids: list[uuid.UUID],
        assigned: bool,
        *,
        assigned_via: str = "manual",
    ) -> None:
        lesson_ids = await self._cascade_lesson_ids(module_ids)
        if lesson_ids:
            await self._assignments.set_user_lessons(
                user_id, lesson_ids, assigned, assigned_via=assigned_via
            )

    async def set_lesson_assignment(
        self, user_id: uuid.UUID, lesson_id: uuid.UUID, assigned: bool
    ) -> None:
        if await self._users.get_by_id(user_id) is None:
            raise NotFoundError("User")
        if await self._content.get_lesson(lesson_id) is None:
            raise NotFoundError("Lesson")
        await self._assignments.set_user_lesson(user_id, lesson_id, assigned)

    async def set_track_assignments(
        self, user_id: uuid.UUID, track_ids: list[uuid.UUID], assigned: bool
    ) -> None:
        """Bulk assign/unassign ("Add/unassign all tracks"); 404 if ANY id is unknown."""
        if await self._users.get_by_id(user_id) is None:
            raise NotFoundError("User")
        unique_ids = list(set(track_ids))
        if await self._content.count_tracks_by_ids(unique_ids) != len(unique_ids):
            raise NotFoundError("Track")
        await self._assignments.set_user_tracks(user_id, unique_ids, assigned)
        await self._cascade_to_modules_and_lessons(user_id, unique_ids, assigned)

    async def set_module_assignments(
        self, user_id: uuid.UUID, module_ids: list[uuid.UUID], assigned: bool
    ) -> None:
        """Bulk assign/unassign ("Add all modules"); 404 if ANY id is unknown."""
        if await self._users.get_by_id(user_id) is None:
            raise NotFoundError("User")
        unique_ids = list(set(module_ids))
        if await self._content.count_modules_by_ids(unique_ids) != len(unique_ids):
            raise NotFoundError("Module")
        await self._assignments.set_user_modules(user_id, unique_ids, assigned)
        await self._cascade_to_lessons(user_id, unique_ids, assigned)

    async def set_lesson_assignments(
        self, user_id: uuid.UUID, lesson_ids: list[uuid.UUID], assigned: bool
    ) -> None:
        """Bulk assign/unassign ("Add all lessons"); 404 if ANY id is unknown."""
        if await self._users.get_by_id(user_id) is None:
            raise NotFoundError("User")
        unique_ids = list(set(lesson_ids))
        if await self._content.count_lessons_by_ids(unique_ids) != len(unique_ids):
            raise NotFoundError("Lesson")
        await self._assignments.set_user_lessons(user_id, unique_ids, assigned)

    async def bulk_assign(
        self,
        user_ids: list[uuid.UUID],
        *,
        track_ids: list[uuid.UUID] | None = None,
        module_ids: list[uuid.UUID] | None = None,
        lesson_ids: list[uuid.UUID] | None = None,
        assigned: bool,
    ) -> None:
        """Many-users bulk (spec §4.2): validate everything, then write per user.
        404 if ANY user or content id is unknown — before any write."""
        unique_users = list(set(user_ids))
        if await self._users.count_by_ids(unique_users) != len(unique_users):
            raise NotFoundError("User")
        if track_ids is not None:
            unique_ids = list(set(track_ids))
            if await self._content.count_tracks_by_ids(unique_ids) != len(unique_ids):
                raise NotFoundError("Track")
            for user_id in unique_users:
                await self._assignments.set_user_tracks(user_id, unique_ids, assigned)
                await self._cascade_to_modules_and_lessons(user_id, unique_ids, assigned)
        elif module_ids is not None:
            unique_ids = list(set(module_ids))
            if await self._content.count_modules_by_ids(unique_ids) != len(unique_ids):
                raise NotFoundError("Module")
            for user_id in unique_users:
                await self._assignments.set_user_modules(user_id, unique_ids, assigned)
                await self._cascade_to_lessons(user_id, unique_ids, assigned)
        elif lesson_ids is not None:
            unique_ids = list(set(lesson_ids))
            if await self._content.count_lessons_by_ids(unique_ids) != len(unique_ids):
                raise NotFoundError("Lesson")
            for user_id in unique_users:
                await self._assignments.set_user_lessons(user_id, unique_ids, assigned)

    async def learning_overview(
        self,
        *,
        project_id: uuid.UUID | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> dict[str, Any]:
        """Modules + lessons + users with their assignments (admin learning
        panel). Only the `users` array is paginated/filtered — modules/lessons
        are always returned complete. project_id scopes the matrix to one
        project (the spec's intent — the matrix lists everyone today); it is
        applied here in Python since list_for_learning() has no project
        parameter (Task 9 keeps the repository change scoped to
        list_with_org_names's `q`)."""
        modules = await self._content.list_modules()
        lessons = await self._content.list_lesson_summaries()
        rows = await self._users.list_for_learning()
        if project_id is not None:
            rows = [row for row in rows if row[0].project_id == project_id]
        (
            track_map,
            module_map,
            lesson_map,
            default_track_map,
            default_module_map,
            default_lesson_map,
        ) = await self._assignment_maps_for([user.id for user, _, _ in rows])
        users = [
            {
                "id": user.id,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "project_name": project_name,
                "company_name": company_name,
                "assigned_track_ids": track_map.get(user.id, []),
                "assigned_module_ids": module_map.get(user.id, []),
                "assigned_lesson_ids": lesson_map.get(user.id, []),
                "default_track_ids": default_track_map.get(user.id, []),
                "default_module_ids": default_module_map.get(user.id, []),
                "default_lesson_ids": default_lesson_map.get(user.id, []),
            }
            for user, project_name, company_name in rows
        ]
        total = len(users)
        page = users[offset : offset + limit] if limit is not None else users[offset:]
        return {
            "modules": [
                {
                    "id": module.id,
                    "track_id": module.track_id,
                    "title": module.title,
                    "sort_order": module.sort_order,
                }
                for module in modules
            ],
            "lessons": [
                {
                    "id": lesson.id,
                    "module_id": lesson.module_id,
                    "title": lesson.title,
                    "sort_order": lesson.sort_order,
                }
                for lesson in lessons
            ],
            "users": page,
            "total": total,
        }

    async def get_project_defaults(self, project_id: uuid.UUID) -> list[uuid.UUID]:
        if await self._org.get_project(project_id) is None:
            raise NotFoundError("Project")
        return await self._org.default_track_ids(project_id)

    async def set_project_defaults(self, project_id: uuid.UUID, track_ids: list[uuid.UUID]) -> None:
        """Full replace; an empty list clears the project's defaults (deliberately
        different from the bulk-assign 422-on-empty convention — PUT here is a
        full replace, not an add/remove-many operation)."""
        if await self._org.get_project(project_id) is None:
            raise NotFoundError("Project")
        unique_ids = list(set(track_ids))
        if await self._content.count_tracks_by_ids(unique_ids) != len(unique_ids):
            raise NotFoundError("Track")
        await self._org.set_default_tracks(project_id, unique_ids)

    async def _materialize_defaults(self, user_id: uuid.UUID, project_id: uuid.UUID) -> None:
        """Copy the project's default tracks (plus cascade) onto a user, additively."""
        track_ids = await self._org.default_track_ids(project_id)
        if not track_ids:
            return
        await self._assignments.set_user_tracks(user_id, track_ids, True, assigned_via="default")
        await self._cascade_to_modules_and_lessons(user_id, track_ids, True, assigned_via="default")

    async def apply_project_defaults(self, project_id: uuid.UUID) -> int:
        """Backfill defaults onto every existing participant. Additive only —
        ON CONFLICT DO NOTHING means manual rows keep their provenance and
        nothing is ever removed."""
        if await self._org.get_project(project_id) is None:
            raise NotFoundError("Project")
        user_ids = await self._users.ids_for_project(project_id)
        for user_id in user_ids:
            await self._materialize_defaults(user_id, project_id)
        return len(user_ids)

    async def get_user(self, user_id: uuid.UUID) -> User:
        user = await self._users.get_by_id(user_id)
        if user is None:
            raise NotFoundError("User")
        return user

    async def reminder_context(self, user_id: uuid.UUID) -> tuple[User, str]:
        """The user + their project name ("" when unassigned) for the
        reminder email — 404 for an unknown user."""
        user = await self._users.get_by_id(user_id)
        if user is None:
            raise NotFoundError("User")
        project_name = ""
        if user.project_id is not None:
            project = await self._org.get_project(user.project_id)
            if project is not None:
                project_name = project.name
        return user, project_name

    async def _assignment_maps_for(
        self, user_ids: list[uuid.UUID]
    ) -> tuple[
        dict[uuid.UUID, list[uuid.UUID]],
        dict[uuid.UUID, list[uuid.UUID]],
        dict[uuid.UUID, list[uuid.UUID]],
        dict[uuid.UUID, list[uuid.UUID]],
        dict[uuid.UUID, list[uuid.UUID]],
        dict[uuid.UUID, list[uuid.UUID]],
    ]:
        """Scoped assignment maps for the given users: the three assigned-id
        maps plus the three "assigned via project default" (provenance) maps,
        built from the same rows in one pass each. Replaces the old unfiltered
        full-table reads."""
        track_map: dict[uuid.UUID, list[uuid.UUID]] = {}
        default_track_map: dict[uuid.UUID, list[uuid.UUID]] = {}
        for track_link in await self._assignments.user_tracks_for_users(user_ids):
            track_map.setdefault(track_link.user_id, []).append(track_link.track_id)
            if track_link.assigned_via == "default":
                default_track_map.setdefault(track_link.user_id, []).append(track_link.track_id)
        module_map: dict[uuid.UUID, list[uuid.UUID]] = {}
        default_module_map: dict[uuid.UUID, list[uuid.UUID]] = {}
        for module_link in await self._assignments.user_modules_for_users(user_ids):
            module_map.setdefault(module_link.user_id, []).append(module_link.module_id)
            if module_link.assigned_via == "default":
                default_module_map.setdefault(module_link.user_id, []).append(module_link.module_id)
        lesson_map: dict[uuid.UUID, list[uuid.UUID]] = {}
        default_lesson_map: dict[uuid.UUID, list[uuid.UUID]] = {}
        for lesson_link in await self._assignments.user_lessons_for_users(user_ids):
            lesson_map.setdefault(lesson_link.user_id, []).append(lesson_link.lesson_id)
            if lesson_link.assigned_via == "default":
                default_lesson_map.setdefault(lesson_link.user_id, []).append(lesson_link.lesson_id)
        return (
            track_map,
            module_map,
            lesson_map,
            default_track_map,
            default_module_map,
            default_lesson_map,
        )
