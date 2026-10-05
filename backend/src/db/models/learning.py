from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base

__all__ = ["Curriculum", "Lesson", "Module", "ModulePrerequisite", "Track"]


class Track(Base):
    __tablename__ = "tracks"
    __table_args__ = (
        CheckConstraint("track_type IN ('general', 'tool')", name="track_type"),
        CheckConstraint(
            "required_level IN ('explore', 'practitioner', 'integrator', 'multiplier')",
            name="required_level",
        ),
        # Deferred for the same reason as lessons' (reorders pass through
        # duplicates mid-transaction). Migration b0c1d2e3f4a5 renumbered the
        # live duplicates before adding it.
        UniqueConstraint("sort_order", deferrable=True, initially="DEFERRED"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    track_type: Mapped[str] = mapped_column(Text, nullable=False)
    color: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Maturity gate: a track is unlocked iff the user's effective maturity is at
    # least this level. General I → explore, General II → practitioner, tool
    # tracks → integrator, except "For Developers" → multiplier, the aspirational
    # top rung reached only by progression (see the maturity-ladder migration and
    # the For-Developers promotion migration).
    required_level: Mapped[str] = mapped_column(Text, nullable=False)
    # Introduction "level": a mandatory, always-unlocked, implicitly-assigned
    # pre-Explorer track whose completion gates every other track (client-side).
    # NOT a maturity level — required_level stays 'explore'; this boolean is the
    # only marker. Set once by migration; never admin-editable.
    is_introduction: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class Curriculum(Base):
    """Kept 1:1 from Supabase (data-only; no endpoints reference it)."""

    __tablename__ = "curricula"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    track_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tracks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'default'"))
    created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, server_default=func.now()
    )


class Module(Base):
    __tablename__ = "modules"
    __table_args__ = (
        UniqueConstraint("track_id", "sort_order", deferrable=True, initially="DEFERRED"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    track_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tracks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class ModulePrerequisite(Base):
    __tablename__ = "module_prerequisites"
    __table_args__ = (CheckConstraint("module_id <> prerequisite_module_id", name="not_self"),)

    module_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("modules.id", ondelete="CASCADE"),
        primary_key=True,
    )
    prerequisite_module_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("modules.id", ondelete="CASCADE"),
        primary_key=True,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class Lesson(Base):
    __tablename__ = "lessons"
    __table_args__ = (
        # DEFERRABLE INITIALLY DEFERRED, not a plain unique index: reordering a
        # module's lessons (ContentRepository.set_lesson_orders) writes each
        # lesson's new sort_order in its own statement, so a permutation
        # passes through intermediate states where two lessons briefly share a
        # value. Deferring the check to end-of-transaction (or an explicit
        # `SET CONSTRAINTS ... IMMEDIATE`) makes that safe. Tracks and
        # modules got the same deferred constraint in migration b0c1d2e3f4a5 (B4).
        UniqueConstraint("module_id", "sort_order", deferrable=True, initially="DEFERRED"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    module_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("modules.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(Text, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    content_blocks: Mapped[list[Any]] = mapped_column(
        JSONB, nullable=False, server_default=text("'[]'::jsonb")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
