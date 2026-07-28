from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel

__all__ = [
    "CalibrationNoteGraduateResponse",
    "CalibrationNoteListResponse",
    "CalibrationNoteOut",
    "CalibrationNoteReviewRequest",
    "CalibrationNoteReviewResponse",
]

CalibrationNoteStatus = Literal["suggested", "approved", "rejected", "retired"]
NoteReviewDecision = Literal["approve", "reject"]


class CalibrationNoteOut(BaseModel):
    """One note the agent suggested about its own drafting.

    `source_lesson_*` are null when the lesson it came from has since been
    deleted — the note outlives it on purpose.
    """

    id: uuid.UUID
    note: str
    status: CalibrationNoteStatus
    source_proposal_id: uuid.UUID | None
    source_lesson_id: uuid.UUID | None
    source_lesson_title: str | None
    created_at: datetime
    reviewed_at: datetime | None


class CalibrationNoteListResponse(BaseModel):
    items: list[CalibrationNoteOut]
    total: int
    limit: int
    offset: int


class CalibrationNoteReviewRequest(BaseModel):
    decision: NoteReviewDecision


class CalibrationNoteReviewResponse(BaseModel):
    status: CalibrationNoteStatus


class CalibrationNoteGraduateResponse(BaseModel):
    """`paste_ready` is the line to paste into house_style.md's calibration
    section. Graduating does not write that file — see the service docstring."""

    status: CalibrationNoteStatus
    paste_ready: str
