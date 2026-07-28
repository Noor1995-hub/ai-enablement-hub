from __future__ import annotations

from typing import TYPE_CHECKING

from src.db.models import LessonContentProposal
from src.repositories.calibration_note_repository import CalibrationNoteRepository
from tests.fixtures.factories import create_lesson, create_module, create_track

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


async def _proposal(db_session: AsyncSession, name: str) -> LessonContentProposal:
    track = await create_track(db_session, f"{name} Track")
    module = await create_module(db_session, track, f"{name} Module")
    lesson = await create_lesson(db_session, module, f"{name} Lesson")
    proposal = LessonContentProposal(
        lesson_id=lesson.id,
        proposed_blocks=[],
        base_blocks=[],
        source_feedback_ids=[],
        summary="s",
    )
    db_session.add(proposal)
    await db_session.commit()
    await db_session.refresh(proposal)
    return proposal


async def test_create_many_inserts_one_suggested_row_per_note(
    db_session: AsyncSession,
) -> None:
    proposal = await _proposal(db_session, "CreateMany")
    repo = CalibrationNoteRepository(db_session)

    rows = await repo.create_many(
        source_proposal_id=proposal.id,
        notes=["Prefer inline bullets.", "Do not add a card group by default."],
    )

    assert [r.note for r in rows] == [
        "Prefer inline bullets.",
        "Do not add a card group by default.",
    ]
    assert all(r.status == "suggested" for r in rows)
    assert all(r.source_proposal_id == proposal.id for r in rows)
    assert all(r.id is not None for r in rows)


async def test_create_many_with_no_notes_inserts_nothing(db_session: AsyncSession) -> None:
    proposal = await _proposal(db_session, "CreateNone")
    repo = CalibrationNoteRepository(db_session)

    assert await repo.create_many(source_proposal_id=proposal.id, notes=[]) == []
