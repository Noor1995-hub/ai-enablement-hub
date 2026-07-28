from __future__ import annotations

import uuid

from sqlalchemy import select

from src.db.models import CalibrationNote
from src.repositories.base import AbstractCalibrationNoteRepository

__all__ = ["CalibrationNoteRepository"]


class CalibrationNoteRepository(AbstractCalibrationNoteRepository):
    async def create_many(
        self, *, source_proposal_id: uuid.UUID, notes: list[str]
    ) -> list[CalibrationNote]:
        if not notes:
            return []
        rows = [CalibrationNote(source_proposal_id=source_proposal_id, note=note) for note in notes]
        self._session.add_all(rows)
        await self._session.commit()
        for row in rows:
            await self._session.refresh(row)
        return rows

    async def list_for_proposal(self, proposal_id: uuid.UUID) -> list[CalibrationNote]:
        query = (
            select(CalibrationNote)
            .where(CalibrationNote.source_proposal_id == proposal_id)
            .order_by(CalibrationNote.created_at)
        )
        return list((await self._session.execute(query)).scalars().all())
