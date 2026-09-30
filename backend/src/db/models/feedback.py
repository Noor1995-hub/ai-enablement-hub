from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Text, func, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base

__all__ = ["Feedback"]


class Feedback(Base):
    __tablename__ = "feedback"
    __table_args__ = (
        CheckConstraint("status IN ('new','accepted','dismissed')", name="status"),
        CheckConstraint(
            "ai_suggested_status IS NULL OR ai_suggested_status IN ('accepted','dismissed')",
            name="ai_suggested_status",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    lesson_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("lessons.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    message: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'new'"))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    # AI-assisted triage (feedback-driven content improvement, Plan B). These
    # are a SUGGESTION only: nothing here ever writes `status` — the admin
    # still clicks Accept/Dismiss. `ai_suggested_at IS NULL` means "not yet
    # suggested" and is what drives lazy, bounded generation.
    ai_suggested_status: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_rationale: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_suggested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
