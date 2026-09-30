from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Text, func, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base

__all__ = ["CalibrationNote"]

# `retired` is not `rejected`: retired means the note proved itself and a human
# copied it into backend/prompts/house_style.md, so it should stop occupying one
# of the capped runtime slots — and retiring is what stops it being injected
# twice, once from here and once from the file. `rejected` means it was never
# good guidance.
_STATUSES = "'suggested','approved','rejected','retired'"


class CalibrationNote(Base):
    """Guidance the content agent suggested about its own drafting, distilled
    from comparing its draft against the version an admin actually accepted.

    Never reaches the agent's prompt until an admin approves it. Plan D only
    writes these rows; the curation UI and the prompt injection are Plan E,
    so in this plan an approved note still influences nothing.
    """

    __tablename__ = "calibration_notes"
    __table_args__ = (CheckConstraint(f"status IN ({_STATUSES})", name="status"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    # Nullable with ON DELETE SET NULL on purpose: deleting a lesson cascades
    # through its proposals, and an approved note must outlive the specific
    # lesson it came from. Losing the provenance link is a better trade than
    # silently deleting curated guidance. The application always sets it at
    # creation time.
    source_proposal_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("lesson_content_proposals.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    note: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'suggested'"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
