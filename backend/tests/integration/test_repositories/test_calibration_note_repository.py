from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from src.db.models import LessonContentProposal
from src.repositories.calibration_note_repository import CalibrationNoteRepository
from tests.fixtures.factories import create_lesson, create_module, create_track, create_user

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


async def test_get_by_id_and_set_status(db_session: AsyncSession) -> None:
    proposal = await _proposal(db_session, "SetStatus")
    reviewer = await create_user(db_session, email="cal-review@x.test", role="admin")
    repo = CalibrationNoteRepository(db_session)
    created = await repo.create_many(source_proposal_id=proposal.id, notes=["Prefer bullets."])
    note = created[0]

    fetched = await repo.get_by_id(note.id)
    assert fetched is not None

    await repo.set_status(fetched, "approved", reviewer.id)
    await db_session.refresh(fetched)
    assert fetched.status == "approved"
    assert fetched.reviewed_by == reviewer.id
    assert fetched.reviewed_at is not None

    assert await repo.get_by_id(uuid.uuid4()) is None


async def test_set_status_with_no_reviewer_clears_the_stamp(db_session: AsyncSession) -> None:
    # Mirrors the sibling repositories: reviewed_by=None clears reviewed_at too.
    proposal = await _proposal(db_session, "ClearStamp")
    reviewer = await create_user(db_session, email="cal-clear@x.test", role="admin")
    repo = CalibrationNoteRepository(db_session)
    note = (await repo.create_many(source_proposal_id=proposal.id, notes=["x"]))[0]

    await repo.set_status(note, "approved", reviewer.id)
    await repo.set_status(note, "suggested", None)
    await db_session.refresh(note)

    assert note.status == "suggested"
    assert note.reviewed_by is None
    assert note.reviewed_at is None


async def test_list_admin_filters_by_status_and_joins_the_source_lesson(
    db_session: AsyncSession,
) -> None:
    proposal = await _proposal(db_session, "ListAdmin")
    reviewer = await create_user(db_session, email="cal-list@x.test", role="admin")
    repo = CalibrationNoteRepository(db_session)
    created = await repo.create_many(source_proposal_id=proposal.id, notes=["first", "second"])
    await repo.set_status(created[0], "approved", reviewer.id)

    rows = await repo.list_admin(limit=10, offset=0)
    assert len(rows) == 2
    # (note, source_lesson_id, source_lesson_title)
    note, lesson_id, lesson_title = rows[0]
    assert lesson_id is not None
    assert lesson_title == "ListAdmin Lesson"

    assert await repo.count_admin() == 2
    assert await repo.count_admin(status="approved") == 1
    approved = await repo.list_admin(status="approved", limit=10, offset=0)
    assert [r[0].note for r in approved] == ["first"]


async def test_list_admin_survives_a_deleted_source(db_session: AsyncSession) -> None:
    # source_proposal_id is ON DELETE SET NULL, so an approved note outlives its
    # lesson. The outer joins must not hide it.
    proposal = await _proposal(db_session, "Orphan")
    repo = CalibrationNoteRepository(db_session)
    await repo.create_many(source_proposal_id=proposal.id, notes=["survivor"])
    await db_session.delete(proposal)
    await db_session.commit()

    rows = await repo.list_admin(limit=10, offset=0)

    assert len(rows) == 1
    note, lesson_id, lesson_title = rows[0]
    assert note.note == "survivor"
    assert lesson_id is None
    assert lesson_title is None


async def test_list_for_injection_returns_approved_text_newest_first(
    db_session: AsyncSession,
) -> None:
    proposal = await _proposal(db_session, "Injection")
    reviewer = await create_user(db_session, email="cal-inject@x.test", role="admin")
    repo = CalibrationNoteRepository(db_session)
    created = await repo.create_many(
        source_proposal_id=proposal.id, notes=["older", "newer", "never approved"]
    )
    await repo.set_status(created[0], "approved", reviewer.id)
    await repo.set_status(created[1], "approved", reviewer.id)
    await repo.set_status(created[2], "rejected", reviewer.id)

    notes = await repo.list_for_injection(limit=10)

    assert "never approved" not in notes
    assert set(notes) == {"older", "newer"}
    assert await repo.list_for_injection(limit=1) == notes[:1]


async def test_only_approved_notes_are_injected(db_session: AsyncSession) -> None:
    proposal = await _proposal(db_session, "OnlyApproved")
    reviewer = await create_user(db_session, email="cal-only@x.test", role="admin")
    repo = CalibrationNoteRepository(db_session)
    created = await repo.create_many(source_proposal_id=proposal.id, notes=["a", "b", "c"])
    await repo.set_status(created[1], "retired", reviewer.id)
    await repo.set_status(created[2], "rejected", reviewer.id)

    # created[0] is still `suggested` — never approved, so never injected.
    assert await repo.list_for_injection(limit=10) == []
