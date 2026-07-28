from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import Select, func, select

from src.db.models import CalibrationNote, Lesson, LessonContentProposal
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

    async def get_by_id(self, note_id: uuid.UUID) -> CalibrationNote | None:
        result = await self._session.execute(
            select(CalibrationNote).where(CalibrationNote.id == note_id)
        )
        return result.scalar_one_or_none()

    def _admin_query(self, status: str | None) -> Select[Any]:
        query = (
            select(
                CalibrationNote,
                LessonContentProposal.lesson_id.label("source_lesson_id"),
                Lesson.title.label("source_lesson_title"),
            )
            # Both OUTER: the source proposal may have been deleted (SET NULL),
            # and an approved note must still appear in the queue without it.
            .outerjoin(
                LessonContentProposal,
                LessonContentProposal.id == CalibrationNote.source_proposal_id,
            )
            .outerjoin(Lesson, Lesson.id == LessonContentProposal.lesson_id)
        )
        if status is not None:
            query = query.where(CalibrationNote.status == status)
        return query

    async def list_admin(self, *, status: str | None = None, limit: int, offset: int) -> list[Any]:
        # `id DESC` is the tiebreaker, and it is load-bearing: create_many
        # inserts every note of one critique in a single transaction, and
        # `created_at`'s server default is transaction_timestamp(), so a whole
        # batch shares ONE timestamp. Without a total order, a tied batch
        # straddling a page boundary can hand back a row twice or never, and a
        # `suggested` note nobody ever sees is never decided on.
        query = (
            self._admin_query(status)
            .order_by(CalibrationNote.created_at.desc(), CalibrationNote.id.desc())
            .limit(limit)
            .offset(offset)
        )
        return list((await self._session.execute(query)).all())

    async def count_admin(self, *, status: str | None = None) -> int:
        query = select(func.count()).select_from(self._admin_query(status).subquery())
        return int((await self._session.execute(query)).scalar_one())

    async def set_status(
        self, note: CalibrationNote, status: str, reviewed_by: uuid.UUID | None
    ) -> None:
        note.status = status
        note.reviewed_by = reviewed_by
        note.reviewed_at = None if reviewed_by is None else datetime.now(UTC)
        await self._session.commit()

    async def list_for_injection(self, *, limit: int) -> list[str]:
        # NULLS LAST because Postgres DESC defaults to NULLS FIRST, and
        # `set_status(note, status, None)` is an implemented contract with no
        # guard against status="approved": such a row would carry
        # reviewed_at = NULL, sort to the HEAD of the injection list, and
        # displace the newest real guidance. `id DESC` makes the rest a total
        # order so the capped slice is deterministic.
        query = (
            select(CalibrationNote.note)
            .where(CalibrationNote.status == "approved")
            .order_by(CalibrationNote.reviewed_at.desc().nullslast(), CalibrationNote.id.desc())
            .limit(limit)
        )
        return [row[0] for row in (await self._session.execute(query)).all()]
