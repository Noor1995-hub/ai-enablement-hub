from __future__ import annotations

import uuid
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock

import pytest

from src.repositories.base import AbstractCalibrationNoteRepository
from src.services.calibration_note_service import CalibrationNoteService
from src.services.exceptions import ConflictError, InvalidRequestError, NotFoundError


def _note(**overrides: Any) -> Any:
    defaults: dict[str, Any] = {
        "id": uuid.uuid4(),
        "note": "Prefer inline bullets over a card group.",
        "status": "suggested",
        "source_proposal_id": uuid.uuid4(),
        "created_at": None,
        "reviewed_at": None,
    }
    return SimpleNamespace(**{**defaults, **overrides})


def _service(note: Any | None) -> tuple[CalibrationNoteService, AsyncMock]:
    notes = AsyncMock(spec=AbstractCalibrationNoteRepository)
    notes.get_by_id.return_value = note
    return CalibrationNoteService(notes), notes


async def test_approve_moves_a_suggested_note_to_approved() -> None:
    note = _note()
    service, notes = _service(note)
    reviewer_id = uuid.uuid4()

    assert (
        await service.review(note_id=note.id, decision="approve", reviewer_id=reviewer_id)
        == "approved"
    )
    notes.set_status.assert_awaited_once_with(note, "approved", reviewer_id)


async def test_reject_moves_a_suggested_note_to_rejected() -> None:
    note = _note()
    service, notes = _service(note)
    reviewer_id = uuid.uuid4()

    assert (
        await service.review(note_id=note.id, decision="reject", reviewer_id=reviewer_id)
        == "rejected"
    )
    notes.set_status.assert_awaited_once_with(note, "rejected", reviewer_id)


@pytest.mark.parametrize("status", ["approved", "rejected", "retired"])
async def test_an_already_decided_note_is_refused(status: str) -> None:
    note = _note(status=status)
    service, notes = _service(note)

    with pytest.raises(ConflictError):
        await service.review(note_id=note.id, decision="approve", reviewer_id=uuid.uuid4())
    notes.set_status.assert_not_awaited()


async def test_an_unknown_decision_never_changes_anything() -> None:
    note = _note()
    service, notes = _service(note)

    for decision in ("", "APPROVE", "inject"):
        with pytest.raises(InvalidRequestError):
            await service.review(note_id=note.id, decision=decision, reviewer_id=uuid.uuid4())
    notes.set_status.assert_not_awaited()


async def test_review_of_an_unknown_note_raises_not_found() -> None:
    service, _notes = _service(None)

    with pytest.raises(NotFoundError):
        await service.review(note_id=uuid.uuid4(), decision="approve", reviewer_id=uuid.uuid4())


async def test_graduate_retires_an_approved_note_and_returns_paste_ready_text() -> None:
    note = _note(status="approved")
    service, notes = _service(note)
    reviewer_id = uuid.uuid4()

    paste_ready = await service.graduate(note_id=note.id, reviewer_id=reviewer_id)

    notes.set_status.assert_awaited_once_with(note, "retired", reviewer_id)
    # Paste-ready for house_style.md's calibration list.
    assert paste_ready == "- Prefer inline bullets over a card group."


@pytest.mark.parametrize("status", ["suggested", "rejected", "retired"])
async def test_only_an_approved_note_can_graduate(status: str) -> None:
    note = _note(status=status)
    service, notes = _service(note)

    with pytest.raises(ConflictError):
        await service.graduate(note_id=note.id, reviewer_id=uuid.uuid4())
    notes.set_status.assert_not_awaited()


async def test_list_notes_shapes_the_rows_and_returns_the_total() -> None:
    note = _note()
    notes = AsyncMock(spec=AbstractCalibrationNoteRepository)
    lesson_id = uuid.uuid4()
    notes.list_admin.return_value = [(note, lesson_id, "Prompting basics")]
    notes.count_admin.return_value = 1
    service = CalibrationNoteService(notes)

    items, total = await service.list_notes(status=None, limit=25, offset=0)

    assert total == 1
    assert items[0]["id"] == note.id
    assert items[0]["note"] == note.note
    assert items[0]["source_lesson_id"] == lesson_id
    assert items[0]["source_lesson_title"] == "Prompting basics"
