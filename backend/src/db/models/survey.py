from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    SmallInteger,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base

__all__ = ["SurveyResponse"]


class SurveyResponse(Base):
    __tablename__ = "survey_responses"
    __table_args__ = (
        UniqueConstraint("user_id"),
        CheckConstraint("status IN ('in_progress', 'complete')", name="status"),
        CheckConstraint(
            "score_level IN ('explore', 'practitioner', 'integrator')", name="score_level"
        ),
        CheckConstraint(
            "usage_band IN ('dormant', 'occasional', 'regular', 'embedded')", name="usage_band"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'in_progress'"))
    instrument_version: Mapped[str] = mapped_column(
        Text, nullable=False, server_default=text("'1.0'")
    )
    current_step: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    job_title: Mapped[str | None] = mapped_column(Text, nullable=True)
    department: Mapped[str | None] = mapped_column(Text, nullable=True)
    consent: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    c1_code: Mapped[str | None] = mapped_column(Text, nullable=True)
    c2_code: Mapped[str | None] = mapped_column(Text, nullable=True)
    c3_code: Mapped[str | None] = mapped_column(Text, nullable=True)
    c4_code: Mapped[str | None] = mapped_column(Text, nullable=True)
    c5_codes: Mapped[list[str] | None] = mapped_column(ARRAY(Text), nullable=True)
    c6_code: Mapped[str | None] = mapped_column(Text, nullable=True)
    b_freq: Mapped[str | None] = mapped_column(Text, nullable=True)
    b_breadth: Mapped[str | None] = mapped_column(Text, nullable=True)
    b_setup: Mapped[list[str] | None] = mapped_column(ARRAY(Text), nullable=True)
    b_tools: Mapped[list[str] | None] = mapped_column(ARRAY(Text), nullable=True)
    b_barriers: Mapped[list[str] | None] = mapped_column(ARRAY(Text), nullable=True)
    b_attitude: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    b_readiness: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    q_excitement: Mapped[str | None] = mapped_column(Text, nullable=True)
    q_timesink: Mapped[str | None] = mapped_column(Text, nullable=True)
    score_level: Mapped[str | None] = mapped_column(Text, nullable=True)
    c1_rung: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    c2_rung: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    c3_rung: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    c4_rung: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    c5_rung: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    c6_rung: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    have_count: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    adv_count: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    safety_flag: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    mandatory_modules: Mapped[list[str] | None] = mapped_column(ARRAY(Text), nullable=True)
    usage_band: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    scored_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
