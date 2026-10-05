from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert

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

    async def stage_update(self, row: SurveyResponse, values: dict[str, Any]) -> SurveyResponse:
        for field, value in values.items():
            setattr(row, field, value)
        await self._session.flush()
        return row

    async def update(self, row: SurveyResponse, values: dict[str, Any]) -> SurveyResponse:
        await self.stage_update(row, values)
        await self._session.commit()
        await self._session.refresh(row)
        return row

    async def create_or_update(
        self, user_id: uuid.UUID, values: dict[str, Any]
    ) -> SurveyResponse | None:
        stmt = pg_insert(SurveyResponse).values(user_id=user_id, **values)
        stmt = stmt.on_conflict_do_update(
            index_elements=["user_id"],
            set_={
                **{column: stmt.excluded[column] for column in values},
                "updated_at": func.now(),
            },
            where=SurveyResponse.status != "complete",
        ).returning(SurveyResponse.id)
        row_id = (await self._session.execute(stmt)).scalar_one_or_none()
        await self._session.commit()
        if row_id is None:
            # The row exists and is already complete: the WHERE guard blocked
            # the update, so nothing was written. The caller (save_draft's
            # pre-check normally catches this first, but a concurrent
            # complete() can land between that check and this statement).
            return None
        # Re-read through the ORM: the Core upsert bypasses the identity map,
        # so an instance loaded earlier in this session (e.g. save_draft's
        # pre-check) would otherwise keep its stale values (same reason
        # OrgRepository.get_ai_settings uses populate_existing).
        result = await self._session.execute(
            select(SurveyResponse)
            .where(SurveyResponse.id == row_id)
            .execution_options(populate_existing=True)
        )
        return result.scalar_one()

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

    async def list_for_users(self, user_ids: list[uuid.UUID]) -> list[SurveyResponse]:
        if not user_ids:
            return []
        result = await self._session.execute(
            select(SurveyResponse).where(SurveyResponse.user_id.in_(user_ids))
        )
        return list(result.scalars().all())
