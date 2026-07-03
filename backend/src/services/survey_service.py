from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, Literal, cast

from src.services.exceptions import SurveyAlreadyCompleteError, SurveyNotInProgressError
from src.services.scoring import score_response

if TYPE_CHECKING:
    from src.db.models import SurveyResponse
    from src.repositories.base import AbstractSurveyRepository

__all__ = ["SurveyService", "SurveyStatus"]

SurveyStatus = Literal["not_started", "in_progress", "complete"]


class SurveyService:
    def __init__(self, surveys: AbstractSurveyRepository) -> None:
        self._surveys = surveys

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
        return await self._surveys.update(
            row, {**scores, "status": "complete", "completed_at": now, "scored_at": now}
        )

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
