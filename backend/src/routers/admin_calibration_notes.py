from __future__ import annotations

import uuid
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query

from src.core.dependencies.auth import require_admin
from src.core.dependencies.content_ai import get_calibration_note_service
from src.db.models import User
from src.schemas.admin_calibration_notes import (
    CalibrationNoteGraduateResponse,
    CalibrationNoteListResponse,
    CalibrationNoteOut,
    CalibrationNoteReviewRequest,
    CalibrationNoteReviewResponse,
)
from src.services.calibration_note_service import CalibrationNoteService

__all__ = ["router"]

router = APIRouter(
    prefix="/api/admin/calibration-notes",
    tags=["admin:calibration-notes"],
    dependencies=[Depends(require_admin)],
)

NoteServiceDep = Annotated[CalibrationNoteService, Depends(get_calibration_note_service)]


@router.get("", response_model=CalibrationNoteListResponse)
async def list_calibration_notes(
    service: NoteServiceDep,
    status_filter: Annotated[
        Literal["suggested", "approved", "rejected", "retired"] | None, Query(alias="status")
    ] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> CalibrationNoteListResponse:
    items, total = await service.list_notes(status=status_filter, limit=limit, offset=offset)
    return CalibrationNoteListResponse(
        items=[CalibrationNoteOut.model_validate(item) for item in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post("/{note_id}/review", response_model=CalibrationNoteReviewResponse)
async def review_calibration_note(
    note_id: uuid.UUID,
    body: CalibrationNoteReviewRequest,
    service: NoteServiceDep,
    admin: Annotated[User, Depends(require_admin)],
) -> CalibrationNoteReviewResponse:
    """The human gate. Approving is what lets a note start influencing future
    drafts; rejecting takes it out of consideration for good."""
    new_status = await service.review(note_id=note_id, decision=body.decision, reviewer_id=admin.id)
    return CalibrationNoteReviewResponse(status=new_status)  # ty: ignore[invalid-argument-type]


@router.post("/{note_id}/graduate", response_model=CalibrationNoteGraduateResponse)
async def graduate_calibration_note(
    note_id: uuid.UUID,
    service: NoteServiceDep,
    admin: Annotated[User, Depends(require_admin)],
) -> CalibrationNoteGraduateResponse:
    """Retire an approved note and hand back the line to paste into
    house_style.md. Retiring frees one of the capped runtime slots and stops the
    note being injected twice once it is in the file."""
    paste_ready = await service.graduate(note_id=note_id, reviewer_id=admin.id)
    return CalibrationNoteGraduateResponse(status="retired", paste_ready=paste_ready)
