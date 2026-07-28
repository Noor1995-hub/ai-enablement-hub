from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from src.db.models import LessonContentProposal
from tests.fixtures.factories import create_lesson, create_module, create_track

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


async def _lesson(db_session: AsyncSession, name: str):
    track = await create_track(db_session, f"{name} Track")
    module = await create_module(db_session, track, f"{name} Module")
    return await create_lesson(
        db_session,
        module,
        f"{name} Lesson",
        content_blocks=[{"id": "b1", "type": "paragraph", "text": "Before."}],
    )


async def test_defaults_to_pending_and_round_trips_jsonb(db_session: AsyncSession) -> None:
    lesson = await _lesson(db_session, "Proposal")
    proposal = LessonContentProposal(
        lesson_id=lesson.id,
        proposed_blocks=[{"id": "b1", "type": "paragraph", "text": "After."}],
        base_blocks=lesson.content_blocks,
        source_feedback_ids=["6f0c1d2e-3a4b-5c6d-7e8f-9a0b1c2d3e4f"],
        summary="Reworded the opening for clarity.",
    )
    db_session.add(proposal)
    await db_session.commit()
    await db_session.refresh(proposal)

    assert proposal.status == "pending"
    assert proposal.created_at is not None
    assert proposal.reviewed_at is None
    assert proposal.reviewed_by is None
    assert proposal.proposed_blocks == [{"id": "b1", "type": "paragraph", "text": "After."}]
    assert proposal.base_blocks == [{"id": "b1", "type": "paragraph", "text": "Before."}]
    assert proposal.source_feedback_ids == ["6f0c1d2e-3a4b-5c6d-7e8f-9a0b1c2d3e4f"]


async def test_unknown_status_is_rejected(db_session: AsyncSession) -> None:
    lesson = await _lesson(db_session, "BadStatus")
    proposal = LessonContentProposal(
        lesson_id=lesson.id,
        proposed_blocks=[],
        base_blocks=[],
        source_feedback_ids=[],
        summary="x",
        status="published",
    )
    db_session.add(proposal)
    with pytest.raises(IntegrityError):
        await db_session.commit()
    await db_session.rollback()


async def test_deleting_the_lesson_cascades(db_session: AsyncSession) -> None:
    lesson = await _lesson(db_session, "Cascade")
    proposal = LessonContentProposal(
        lesson_id=lesson.id,
        proposed_blocks=[],
        base_blocks=[],
        source_feedback_ids=[],
        summary="x",
    )
    db_session.add(proposal)
    await db_session.commit()

    await db_session.delete(lesson)
    await db_session.commit()

    rows = (await db_session.execute(select(LessonContentProposal))).scalars().all()
    assert rows == []
