from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Text, func, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base

__all__ = ["Conversation", "Message"]

_KINDS = "'chatbot', 'assessment', 'lesson', 'interview'"


class Conversation(Base):
    __tablename__ = "conversations"
    __table_args__ = (
        CheckConstraint(f"kind IN ({_KINDS})", name="kind"),
        # A learner has exactly one interview (InterviewService._interview_
        # conversation takes conversations[0]), but chat kinds are many-per-user,
        # hence a PARTIAL unique index rather than a unique constraint. Not
        # deferrable: a duplicate fails at flush. Declared here as well as in
        # migration c3d4e5f6a7b8 so the metadata-built test schema matches prod.
        Index(
            "uq_conversations_interview_user_id",
            "user_id",
            unique=True,
            postgresql_where=text("kind = 'interview'"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    kind: Mapped[str] = mapped_column(Text, nullable=False)
    # lesson_id or survey question id; text because it's polymorphic across
    # kinds, not a single-target FK.
    context_ref: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Interviewer's structured extraction (Batch C) — unused by this batch.
    summary: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class Message(Base):
    __tablename__ = "messages"
    __table_args__ = (
        CheckConstraint("role IN ('user', 'assistant', 'system', 'tool')", name="role"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role: Mapped[str] = mapped_column(Text, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    # Token counts, model id, truncated flag.
    metadata_: Mapped[dict[str, Any] | None] = mapped_column("metadata", JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
