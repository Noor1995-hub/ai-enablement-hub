from __future__ import annotations

import uuid

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
