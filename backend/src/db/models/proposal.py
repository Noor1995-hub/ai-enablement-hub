from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Text, func, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base

__all__ = ["LessonContentProposal"]

# 'failed' is not in the design doc's list. It exists so a lesson the agent
# cannot draft for (oversized, or output that never passes validation) stops
# re-consuming the oldest-first slot of every future run — the same starvation
# fix Plan B's final review forced on triage. A failed row records WHY in
# `summary`, keeps its source feedback out of later runs, and an admin can
# reject it to make that feedback eligible again.
_STATUSES = "'pending','approved','rejected','superseded','failed'"


class LessonContentProposal(Base):
    """A drafted revision of one lesson's content_blocks, awaiting an admin.

    Deliberately NOT a general content-versioning system: it holds a proposed
    array plus the snapshot it was drafted against (`base_blocks`), just long
    enough for a human to approve or discard it. Nothing here ever reaches a
    live lesson without an explicit approve.
    """

    __tablename__ = "lesson_content_proposals"
    __table_args__ = (CheckConstraint(f"status IN ({_STATUSES})", name="status"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    lesson_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("lessons.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # Same shape as Lesson.content_blocks (opaque list on the backend; the
    # union lives in frontend/src/types/contentBlocks.ts and is enforced by
    # services/content_blocks_validation.py).
    proposed_blocks: Mapped[list[Any]] = mapped_column(JSONB, nullable=False)
    # The lesson's blocks at generation time: makes the review diff stable
    # even if the lesson is edited meanwhile, and lets approve detect that the
    # lesson moved under the proposal (-> superseded, refuse).
    base_blocks: Mapped[list[Any]] = mapped_column(JSONB, nullable=False)
    # Provenance: the accepted feedback rows that drove this draft. A feedback
    # id appearing here (on a pending/approved/failed proposal) is what makes
    # it "already incorporated" and keeps runs idempotent.
    source_feedback_ids: Mapped[list[Any]] = mapped_column(JSONB, nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'pending'"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
