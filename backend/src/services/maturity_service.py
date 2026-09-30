from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from src.core.constants import advance_level, module_level_map
from src.services.exceptions import NotFoundError

if TYPE_CHECKING:
    from src.db.models import User
    from src.repositories.base import (
        AbstractAssignmentRepository,
        AbstractContentRepository,
        AbstractSurveyRepository,
        AbstractUserRepository,
    )

__all__ = ["MaturityService"]


class MaturityService:
    """Effective maturity as a live progression loop over the learning path.

    Base level = the admin override if pinned, else the score_level of a
    *complete* survey, else None. From that base the level self-propels upward:
    each time every module the user has *assigned lessons for* at the current
    level is complete, maturity steps up a rung (General I → Practitioner →
    General II → Integrator → tool tracks). Nothing is stored — recomputed on
    every read, so a changed override never drifts and never demotes below what
    the user has already earned. Maturity gates *visibility* only; it never
    assigns or unassigns content.
    """

    def __init__(
        self,
        users: AbstractUserRepository,
        surveys: AbstractSurveyRepository,
        content: AbstractContentRepository,
        assignments: AbstractAssignmentRepository,
    ) -> None:
        self._users = users
        self._surveys = surveys
        self._content = content
        self._assignments = assignments

    async def effective_level(self, user: User) -> str | None:
        base = user.maturity_override or (await self._surveys.get_complete_levels([user.id])).get(
            user.id
        )
        if base is None:
            return None

        tracks = await self._content.list_tracks()
        modules = await self._content.list_modules()
        counts = await self._assignments.assigned_lesson_counts_by_module(user.id)

        return advance_level(base, module_level_map(tracks, modules), counts)

    async def set_override(self, user_id: uuid.UUID, level: str | None) -> None:
        """Pin (or clear) the admin maturity override. No assignment side
        effects — maturity never touches what content a user has."""
        user = await self._users.get_by_id(user_id)
        if user is None:
            raise NotFoundError("User")
        await self._users.set_maturity_override(user, level)
