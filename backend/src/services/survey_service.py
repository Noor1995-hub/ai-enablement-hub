from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, Literal, cast

from src.core.constants import LEVEL_RANK
from src.services.exceptions import SurveyAlreadyCompleteError, SurveyNotInProgressError
from src.services.scoring import score_response

if TYPE_CHECKING:
    from src.db.models import SurveyResponse
    from src.repositories.base import (
        AbstractAssignmentRepository,
        AbstractContentRepository,
        AbstractSurveyRepository,
    )

__all__ = ["SurveyService", "SurveyStatus"]

SurveyStatus = Literal["not_started", "in_progress", "complete"]


class SurveyService:
    def __init__(
        self,
        surveys: AbstractSurveyRepository,
        content: AbstractContentRepository,
        assignments: AbstractAssignmentRepository,
    ) -> None:
        self._surveys = surveys
        self._content = content
        self._assignments = assignments

    async def get_own(self, user_id: uuid.UUID) -> SurveyResponse | None:
        return await self._surveys.get_by_user_id(user_id)

    async def save_draft(self, user_id: uuid.UUID, values: dict[str, Any]) -> SurveyResponse:
        """Upsert the caller's draft; a completed survey can no longer be edited."""
        row = await self._surveys.get_by_user_id(user_id)
        if row is not None and row.status == "complete":
            raise SurveyAlreadyCompleteError
        values = {**values, "status": "in_progress"}
        if row is None:
            return await self._surveys.create(user_id, values)
        return await self._surveys.update(row, values)

    async def complete(self, user_id: uuid.UUID) -> SurveyResponse:
        """Score the caller's in-progress draft and persist every scored field.

        Raises SurveyNotInProgressError (→ 409) with a clear message when there
        is no draft (fixes legacy B3) and ScoringError (→ 422) when answers are
        missing or unrecognised.
        """
        row = await self._surveys.get_by_user_id(user_id)
        if row is None or row.status != "in_progress":
            raise SurveyNotInProgressError
        scores = score_response(
            {
                "c1_code": row.c1_code,
                "c2_code": row.c2_code,
                "c3_code": row.c3_code,
                "c4_code": row.c4_code,
                "c5_codes": row.c5_codes,
                "c6_code": row.c6_code,
                "b_freq": row.b_freq,
                "b_breadth": row.b_breadth,
            }
        )
        now = datetime.now(UTC)
        completed = await self._surveys.update(
            row, {**scores, "status": "complete", "completed_at": now, "scored_at": now}
        )
        await self._seed_assignments(user_id, completed.score_level)
        return completed

    async def _seed_assignments(self, user_id: uuid.UUID, score_level: str | None) -> None:
        """One-time auto-assignment on first completion: assign every track whose
        `required_level` is at or below the scored level, cascading to all of
        their modules and lessons so the learner sees content immediately.

        Seeds ONLY when the user has no track assignments yet — an admin who has
        already tweaked assignments is never clobbered, and re-scoring (which
        cannot happen via the API today, but may via a backfill) never re-seeds.
        Maturity still gates *visibility* of this content; assignment just grants
        it. The admin can add or remove tracks afterwards."""
        level_rank = LEVEL_RANK.get(score_level or "")
        if level_rank is None:
            return
        if await self._assignments.track_ids_for_user(user_id):
            return

        # The scoring engine tops out at 'integrator'; 'multiplier' is aspirational
        # (reached only by progression from integrator, never scored). Extend the
        # seed ceiling to the top of the ladder for integrator scorers so a
        # multiplier-gated track (e.g. "For Developers") is seeded alongside the
        # integrator tool tracks — assignment just grants the content, maturity
        # still gates its visibility until the learner closes out integrator.
        seed_rank = (
            LEVEL_RANK["multiplier"] if level_rank >= LEVEL_RANK["integrator"] else level_rank
        )

        tracks = await self._content.list_tracks()
        track_ids = [
            track.id
            for track in tracks
            if (rank := LEVEL_RANK.get(track.required_level)) is not None and rank <= seed_rank
        ]
        if not track_ids:
            return

        eligible = set(track_ids)
        modules = [m for m in await self._content.list_modules() if m.track_id in eligible]
        module_ids = [module.id for module in modules]
        eligible_modules = set(module_ids)
        lesson_ids = [
            lesson.id
            for lesson in await self._content.list_lesson_summaries()
            if lesson.module_id in eligible_modules
        ]

        await self._assignments.set_user_tracks(user_id, track_ids, assigned=True)
        if module_ids:
            await self._assignments.set_user_modules(user_id, module_ids, assigned=True)
        if lesson_ids:
            await self._assignments.set_user_lessons(user_id, lesson_ids, assigned=True)

    async def survey_status(self, user_id: uuid.UUID) -> SurveyStatus:
        row = await self._surveys.get_by_user_id(user_id)
        if row is None:
            return "not_started"
        # The DB CHECK constraint restricts status to in_progress|complete.
        return cast("SurveyStatus", row.status)

    async def complete_levels(self, user_ids: list[uuid.UUID]) -> dict[uuid.UUID, str]:
        return await self._surveys.get_complete_levels(user_ids)

    async def complete_survey_for(self, user_id: uuid.UUID) -> SurveyResponse | None:
        """The user's completed survey, or None (admin results view)."""
        row = await self._surveys.get_by_user_id(user_id)
        if row is None or row.status != "complete":
            return None
        return row
