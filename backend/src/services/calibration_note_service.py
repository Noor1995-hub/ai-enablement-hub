"""Admin curation of the calibration notes the content agent suggested.

The human gate between the learn-card feature and the drafting prompt: a note
influences nothing until an admin approves it.

Has NO LLM dependency, unlike ContentImprovementService and
FeedbackTriageService, so it is never None-gated — reviewing notes that already
exist must keep working even if Settings.llm is later unconfigured.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from src.services.exceptions import ConflictError, InvalidRequestError, NotFoundError

if TYPE_CHECKING:
    import uuid

    from src.db.models import CalibrationNote
    from src.repositories.base import AbstractCalibrationNoteRepository

__all__ = ["CalibrationNoteService"]

# Only a note nobody has decided on yet can be approved or rejected.
_REVIEWABLE_STATUSES = ("suggested",)


def _paste_ready(note: CalibrationNote) -> str:
    """The line a human copies into backend/prompts/house_style.md's calibration
    section.

    ONE renderer, two callers (`graduate` and `list_notes`), so the text an
    admin reads before graduating and the text the graduate response hands back
    can never drift apart. Deliberately not reimplemented in TypeScript for the
    same reason. Derived from `note.note`, which is NOT NULL, so it is always
    available whatever the note's status.
    """
    return f"- {note.note}"


class CalibrationNoteService:
    def __init__(self, notes: AbstractCalibrationNoteRepository) -> None:
        self._notes = notes

    async def list_notes(
        self, *, status: str | None = None, limit: int, offset: int
    ) -> tuple[list[dict[str, Any]], int]:
        rows = await self._notes.list_admin(status=status, limit=limit, offset=offset)
        total = await self._notes.count_admin(status=status)
        items = [
            {
                "id": note.id,
                "note": note.note,
                "status": note.status,
                "source_proposal_id": note.source_proposal_id,
                "source_lesson_id": source_lesson_id,
                "source_lesson_title": source_lesson_title,
                "created_at": note.created_at,
                "reviewed_at": note.reviewed_at,
                # On EVERY row, not just retired ones: the admin needs the line
                # before they graduate, and graduating is a one-way door that
                # otherwise hands it back exactly once.
                "paste_ready": _paste_ready(note),
            }
            for (note, source_lesson_id, source_lesson_title) in rows
        ]
        return items, total

    async def review(self, *, note_id: uuid.UUID, decision: str, reviewer_id: uuid.UUID) -> str:
        """Approve a note into the drafting prompt, or reject it.

        Approving is the ONLY way a note starts influencing future drafts.
        """
        note = await self._notes.get_by_id(note_id)
        if note is None:
            raise NotFoundError("Calibration note")
        if note.status not in _REVIEWABLE_STATUSES:
            msg = f"this note is already {note.status}"
            raise ConflictError(msg)
        if decision == "approve":
            await self._notes.set_status(note, "approved", reviewer_id)
            return "approved"
        if decision == "reject":
            await self._notes.set_status(note, "rejected", reviewer_id)
            return "rejected"
        msg = f"unknown review decision {decision!r}"
        raise InvalidRequestError(msg)

    async def graduate(self, *, note_id: uuid.UUID, reviewer_id: uuid.UUID) -> str:
        """Mark an approved note `retired` and hand back the line to paste into
        backend/prompts/house_style.md.

        `retired` is not `rejected`: retired means the note proved itself and a
        human copied it into the house style, so it should stop occupying one of
        the capped runtime slots — and retiring is what stops it being injected
        TWICE, once from the database and once from the file.

        This deliberately does NOT write house_style.md. That file is baked into
        the container image at build time, so a runtime write lands on an
        ephemeral filesystem and disappears on the next revision, and git would
        overwrite it on the next deploy regardless. The file edit is a reviewed
        commit; this is the bookkeeping that a human made it.

        The same line is on every list row (see `_paste_ready`), so this
        response is a convenience, not the only way to obtain it.
        """
        note = await self._notes.get_by_id(note_id)
        if note is None:
            raise NotFoundError("Calibration note")
        if note.status != "approved":
            msg = f"only an approved note can graduate; this one is {note.status}"
            raise ConflictError(msg)
        await self._notes.set_status(note, "retired", reviewer_id)
        return _paste_ready(note)
