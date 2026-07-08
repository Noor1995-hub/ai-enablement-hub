from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

from src.core.constants import advance_level
from src.services.exceptions import EmailAlreadyRegisteredError, NotFoundError

if TYPE_CHECKING:
    from src.db.models import User
    from src.repositories.base import (
        AbstractAssignmentRepository,
        AbstractContentRepository,
        AbstractOrgRepository,
        AbstractSurveyRepository,
        AbstractUserRepository,
    )
    from src.services.token_service import TokenService

__all__ = ["AdminUserService"]


class AdminUserService:
    """Admin user directory: listing, invites, reset links, roles, deletion,
    and track/module assignment — everything behind require_admin."""

    def __init__(
        self,
        users: AbstractUserRepository,
        org: AbstractOrgRepository,
        assignments: AbstractAssignmentRepository,
        content: AbstractContentRepository,
        surveys: AbstractSurveyRepository,
        token_service: TokenService,
    ) -> None:
        self._users = users
        self._org = org
        self._assignments = assignments
        self._content = content
        self._surveys = surveys
        self._token_service = token_service

    async def list_users(self, project_id: uuid.UUID | None = None) -> list[dict[str, Any]]:
        rows = await self._users.list_with_org_names(project_id)
        track_map, module_map, lesson_map = await self._assignment_maps()
        effective = await self._effective_maturity_map([user for user, _, _ in rows])
        return [
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
                "assigned_track_ids": track_map.get(user.id, []),
                "assigned_module_ids": module_map.get(user.id, []),
                "assigned_lesson_ids": lesson_map.get(user.id, []),
                "maturity_override": user.maturity_override,
                "effective_maturity": effective.get(user.id),
            }
            for user, company_name, project_name in rows
        ]

    async def _effective_maturity_map(self, users: list[User]) -> dict[uuid.UUID, str | None]:
        """user_id → effective maturity, computed live via the shared ladder
        walk (no MaturityService import — services never call services). Base =
        override or a complete survey's score_level; None → no maturity."""
        complete = await self._surveys.get_complete_levels([user.id for user in users])
        bases = {user.id: user.maturity_override or complete.get(user.id) for user in users}
        if not any(bases.values()):
            return dict.fromkeys(bases, None)

        tracks = await self._content.list_tracks()
        modules = await self._content.list_modules()
        track_level = {track.id: track.required_level for track in tracks}
        module_level = {
            module.id: track_level[module.track_id]
            for module in modules
            if module.track_id in track_level
        }
        result: dict[uuid.UUID, str | None] = {}
        for user_id, base in bases.items():
            if base is None:
                result[user_id] = None
                continue
            counts = await self._assignments.assigned_lesson_counts_by_module(user_id)
            result[user_id] = advance_level(base, module_level, counts)
        return result

    async def invite(
        self, email: str, first_name: str, last_name: str, project_id: uuid.UUID
    ) -> tuple[User, str]:
        """Create the user row and a single-use invite token; returns the raw
        token (the router turns it into `{app_url}/invite/{token}`)."""
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
        raw_token = await self._token_service.issue_action_token(user, "invite")
        return user, raw_token

    async def reset_link(self, user_id: uuid.UUID) -> tuple[User, str]:
        user = await self._users.get_by_id(user_id)
        if user is None:
            raise NotFoundError("User")
        raw_token = await self._token_service.issue_action_token(user, "reset")
        return user, raw_token

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

    async def set_module_assignment(
        self, user_id: uuid.UUID, module_id: uuid.UUID, assigned: bool
    ) -> None:
        if await self._users.get_by_id(user_id) is None:
            raise NotFoundError("User")
        if await self._content.get_module(module_id) is None:
            raise NotFoundError("Module")
        await self._assignments.set_user_module(user_id, module_id, assigned)

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

    async def learning_overview(self) -> dict[str, Any]:
        """Modules + lessons + users with their assignments (admin learning panel)."""
        modules = await self._content.list_modules()
        lessons = await self._content.list_lesson_summaries()
        rows = await self._users.list_for_learning()
        track_map, module_map, lesson_map = await self._assignment_maps()
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
            "users": [
                {
                    "id": user.id,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "project_name": project_name,
                    "company_name": company_name,
                    "assigned_track_ids": track_map.get(user.id, []),
                    "assigned_module_ids": module_map.get(user.id, []),
                    "assigned_lesson_ids": lesson_map.get(user.id, []),
                }
                for user, project_name, company_name in rows
            ],
        }

    async def get_user(self, user_id: uuid.UUID) -> User:
        user = await self._users.get_by_id(user_id)
        if user is None:
            raise NotFoundError("User")
        return user

    async def _assignment_maps(
        self,
    ) -> tuple[
        dict[uuid.UUID, list[uuid.UUID]],
        dict[uuid.UUID, list[uuid.UUID]],
        dict[uuid.UUID, list[uuid.UUID]],
    ]:
        track_map: dict[uuid.UUID, list[uuid.UUID]] = {}
        for link in await self._assignments.all_user_tracks():
            track_map.setdefault(link.user_id, []).append(link.track_id)
        module_map: dict[uuid.UUID, list[uuid.UUID]] = {}
        for link in await self._assignments.all_user_modules():
            module_map.setdefault(link.user_id, []).append(link.module_id)
        lesson_map: dict[uuid.UUID, list[uuid.UUID]] = {}
        for link in await self._assignments.all_user_lessons():
            lesson_map.setdefault(link.user_id, []).append(link.lesson_id)
        return track_map, module_map, lesson_map
