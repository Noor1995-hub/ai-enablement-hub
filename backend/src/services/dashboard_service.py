from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any

from src.core.attention import ACTIVE_DAYS, attention_for
from src.core.constants import LEVEL_ORDER, advance_level
from src.services.exceptions import NotFoundError

if TYPE_CHECKING:
    from src.db.models import Project
    from src.repositories.base import (
        AbstractAssignmentRepository,
        AbstractAuthSessionRepository,
        AbstractContentRepository,
        AbstractFeedbackRepository,
        AbstractOrgRepository,
        AbstractProgressRepository,
        AbstractSurveyRepository,
        AbstractUserRepository,
    )

__all__ = ["DashboardService"]

_FUNNEL_KEYS = ("invited", "activated", "assessed", "started", "completed_track")


class DashboardService:
    """Admin dashboard aggregates (spec §4.4): tiles, per-project funnels, the
    attention list and the maturity distribution — one call for the whole screen.

    Reuses the SAME pure rules the People directory uses: `attention_for`
    (core/attention.py) for the attention list and the `advance_level` ladder
    walk (core/constants.py) for maturity. It never calls AdminUserService or
    any other service — the small duplication of fetch lines is the accepted
    price of "services never call services"."""

    def __init__(
        self,
        users: AbstractUserRepository,
        org: AbstractOrgRepository,
        assignments: AbstractAssignmentRepository,
        content: AbstractContentRepository,
        surveys: AbstractSurveyRepository,
        sessions: AbstractAuthSessionRepository,
        progress: AbstractProgressRepository,
        feedback: AbstractFeedbackRepository,
    ) -> None:
        self._users = users
        self._org = org
        self._assignments = assignments
        self._content = content
        self._surveys = surveys
        self._sessions = sessions
        self._progress = progress
        self._feedback = feedback

    async def overview(self, project_id: uuid.UUID | None) -> dict[str, Any]:
        scope: Project | None = None
        if project_id is not None:
            scope = await self._org.get_project(project_id)
            if scope is None:
                raise NotFoundError("Project")

        # Learners in scope (admins are staff, not learners). list_with_org_names
        # filters by project when scoped; None returns everyone.
        rows = [
            (user, company_name, project_name)
            for user, company_name, project_name in await self._users.list_with_org_names(
                project_id
            )
            if user.role != "admin"
        ]
        users = [user for user, _, _ in rows]
        user_ids = [user.id for user in users]

        # One batched read each — same reads the People directory uses.
        counts = await self._assignments.assigned_lesson_counts_by_module_for_users(user_ids)
        last_active = await self._sessions.last_used_by_user(user_ids)
        latest = await self._progress.latest_completion_by_user(user_ids)
        surveyed = await self._surveys.user_ids_with_survey(user_ids)
        complete = await self._surveys.get_complete_levels(user_ids)
        track_map: dict[uuid.UUID, list[uuid.UUID]] = {}
        for track_link in await self._assignments.user_tracks_for_users(user_ids):
            track_map.setdefault(track_link.user_id, []).append(track_link.track_id)

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
        modules_by_track: dict[uuid.UUID, list[uuid.UUID]] = {}
        for module in modules:
            modules_by_track.setdefault(module.track_id, []).append(module.id)

        now = datetime.now(UTC)
        active_cutoff = timedelta(days=ACTIVE_DAYS)
        attention_items: list[dict[str, Any]] = []
        active_week = 0
        maturity = dict.fromkeys(LEVEL_ORDER, 0)
        funnels: dict[uuid.UUID, dict[str, int]] = {}

        for user, company_name, project_name in rows:
            user_counts = counts.get(user.id, {})
            assigned_total = sum(assigned for assigned, _ in user_counts.values())
            completed_total = sum(completed for _, completed in user_counts.values())
            activated = user.password_set or user.external_id is not None
            has_survey = user.id in surveyed
            latest_completion = latest.get(user.id)
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
            last_active_at = last_active.get(user.id)
            activated_known_since = max(user.created_at, last_active_at or user.created_at)

            if last_active_at is not None and now - last_active_at <= active_cutoff:
                active_week += 1

            attention = attention_for(
                now=now,
                created_at=user.created_at,
                activated=activated,
                activated_known_since=activated_known_since,
                has_survey=has_survey,
                latest_completion=latest_completion,
                assigned_total=assigned_total,
                completed_total=completed_total,
                track_names_in_progress=track_names_in_progress,
            )
            if attention is not None:
                kind, reason = attention
                attention_items.append(
                    {
                        "user_id": user.id,
                        "name": f"{user.first_name} {user.last_name}",
                        "email": user.email,
                        "project_id": user.project_id,
                        "project_name": project_name,
                        "company_name": company_name,
                        "kind": kind,
                        "reason": reason,
                    }
                )

            base = user.maturity_override or complete.get(user.id)
            if base is not None:
                effective = advance_level(base, module_level, user_counts)
                if effective in maturity:
                    maturity[effective] += 1

            if user.project_id is not None:
                funnel = funnels.setdefault(user.project_id, dict.fromkeys(_FUNNEL_KEYS, 0))
                funnel["invited"] += 1
                if activated:
                    funnel["activated"] += 1
                # Locked spec §4.4: "assessed" is a COMPLETED survey
                # (status='complete'), i.e. the `complete` map. This is
                # deliberately stricter than the attention module's `has_survey`
                # (any row, incl. drafts) — that stays the not_assessed contract.
                if user.id in complete:
                    funnel["assessed"] += 1
                if latest_completion is not None:
                    funnel["started"] += 1
                if self._completed_a_track(assigned_tracks, modules_by_track, user_counts):
                    funnel["completed_track"] += 1

        projects = [scope] if scope is not None else await self._org.list_projects()
        company_name_by_id = {
            company.id: company.name for company in await self._org.list_companies()
        }
        funnel_list = [
            {
                "project_id": project.id,
                "project_name": project.name,
                "company_name": company_name_by_id.get(project.company_id, ""),
                **funnels.get(project.id, dict.fromkeys(_FUNNEL_KEYS, 0)),
            }
            for project in projects
        ]

        return {
            "tiles": {
                "learners": len(users),
                "active_week": active_week,
                "attention": len(attention_items),
                "new_feedback": await self._feedback.count_new(project_id),
            },
            "attention": attention_items,
            "funnels": funnel_list,
            "maturity": maturity,
        }

    @staticmethod
    def _completed_a_track(
        assigned_track_ids: list[uuid.UUID],
        modules_by_track: dict[uuid.UUID, list[uuid.UUID]],
        user_counts: dict[uuid.UUID, tuple[int, int]],
    ) -> bool:
        """Locked spec: a track counts as completed for a user when, grouping the
        user's assigned-lesson counts by the track's modules, every module with
        assigned lessons has total > 0 and completed == total (and at least one
        such module exists)."""
        for track_id in assigned_track_ids:
            assigned_modules = [
                mid
                for mid in modules_by_track.get(track_id, [])
                if user_counts.get(mid, (0, 0))[0] > 0
            ]
            if assigned_modules and all(
                user_counts[mid][1] == user_counts[mid][0] for mid in assigned_modules
            ):
                return True
        return False
