from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select

from src.db.models import SurveyResponse
from src.repositories.base import AbstractSurveyRepository

__all__ = ["SurveyRepository"]


class SurveyRepository(AbstractSurveyRepository):
    async def get_by_user_id(self, user_id: uuid.UUID) -> SurveyResponse | None:
        result = await self._session.execute(
            select(SurveyResponse).where(SurveyResponse.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def create(self, user_id: uuid.UUID, values: dict[str, Any]) -> SurveyResponse:
        row = SurveyResponse(user_id=user_id, **values)
        self._session.add(row)
        await self._session.commit()
        await self._session.refresh(row)
        return row

    async def update(self, row: SurveyResponse, values: dict[str, Any]) -> SurveyResponse:
        for field, value in values.items():
            setattr(row, field, value)
        await self._session.commit()
        await self._session.refresh(row)
        return row

    async def get_complete_levels(self, user_ids: list[uuid.UUID]) -> dict[uuid.UUID, str]:
        if not user_ids:
            return {}
        result = await self._session.execute(
            select(SurveyResponse.user_id, SurveyResponse.score_level).where(
                SurveyResponse.user_id.in_(user_ids),
                SurveyResponse.status == "complete",
                SurveyResponse.score_level.is_not(None),
            )
        )
        return {row[0]: row[1] for row in result.all()}

    async def user_ids_with_survey(self, user_ids: list[uuid.UUID]) -> set[uuid.UUID]:
        if not user_ids:
            return set()
        result = await self._session.execute(
            select(SurveyResponse.user_id).where(SurveyResponse.user_id.in_(user_ids))
        )
        return set(result.scalars().all())
