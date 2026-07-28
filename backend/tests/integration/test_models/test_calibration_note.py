from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from src.db.models import CalibrationNote, LessonContentProposal
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


async def test_defaults_to_suggested(db_session: AsyncSession) -> None:
    proposal = await _proposal(db_session, "Note")
    note = CalibrationNote(source_proposal_id=proposal.id, note="Prefer inline bullets.")
    db_session.add(note)
    await db_session.commit()
    await db_session.refresh(note)

    assert note.status == "suggested"
    assert note.created_at is not None
    assert note.reviewed_at is None
    assert note.reviewed_by is None


async def test_unknown_status_is_rejected(db_session: AsyncSession) -> None:
    proposal = await _proposal(db_session, "BadStatus")
    db_session.add(CalibrationNote(source_proposal_id=proposal.id, note="x", status="injected"))
    with pytest.raises(IntegrityError):
        await db_session.commit()
    await db_session.rollback()


async def test_deleting_the_proposal_keeps_the_note_and_nulls_the_link(
    db_session: AsyncSession,
) -> None:
    # An approved note must outlive the lesson it was distilled from.
    proposal = await _proposal(db_session, "Outlive")
    note = CalibrationNote(source_proposal_id=proposal.id, note="Keep me.")
    db_session.add(note)
    await db_session.commit()

    await db_session.delete(proposal)
    await db_session.commit()

    # populate_existing: the DB applies ON DELETE SET NULL as a side effect of
    # deleting `proposal`, which never goes through the ORM, so the `note`
    # instance already in this session's identity map would otherwise keep
    # returning its pre-delete (stale) source_proposal_id (see
    # org_repository.get_ai_settings for the same pattern).
    rows = (
        (
            await db_session.execute(
                select(CalibrationNote).execution_options(populate_existing=True)
            )
        )
        .scalars()
        .all()
    )
    assert len(rows) == 1
    assert rows[0].note == "Keep me."
    assert rows[0].source_proposal_id is None
