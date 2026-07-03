from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

__all__ = ["SurveyCompleteResponse", "SurveyDraftRequest", "SurveyResponseOut"]


class SurveyDraftRequest(BaseModel):
    """Partial draft: only fields the client sends are written (exclude_unset).

    q_* answers are capped at 2000 chars (fixes legacy S5: unbounded text).
    """

    job_title: str | None = None
    department: str | None = None
    consent: bool | None = None
    c1_code: str | None = None
    c2_code: str | None = None
    c3_code: str | None = None
    c4_code: str | None = None
    c5_codes: list[str] | None = None
    c6_code: str | None = None
    b_freq: str | None = None
    b_breadth: str | None = None
    b_setup: list[str] | None = None
    b_tools: list[str] | None = None
    b_barriers: list[str] | None = None
    b_attitude: int | None = None
    b_readiness: int | None = None
    q_excitement: str | None = Field(default=None, max_length=2000)
    q_timesink: str | None = Field(default=None, max_length=2000)
    current_step: int | None = Field(default=None, ge=0)


class SurveyResponseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    status: str
    instrument_version: str
    current_step: int
    job_title: str | None
    department: str | None
    consent: bool | None
    c1_code: str | None
    c2_code: str | None
    c3_code: str | None
    c4_code: str | None
    c5_codes: list[str] | None
    c6_code: str | None
    b_freq: str | None
    b_breadth: str | None
    b_setup: list[str] | None
    b_tools: list[str] | None
    b_barriers: list[str] | None
    b_attitude: int | None
    b_readiness: int | None
    q_excitement: str | None
    q_timesink: str | None
    score_level: str | None
    c1_rung: int | None
    c2_rung: int | None
    c3_rung: int | None
    c4_rung: int | None
    c5_rung: int | None
    c6_rung: int | None
    have_count: int | None
    adv_count: int | None
    safety_flag: bool | None
    mandatory_modules: list[str] | None
    usage_band: str | None
    started_at: datetime
    completed_at: datetime | None
    scored_at: datetime | None
    updated_at: datetime


class SurveyCompleteResponse(BaseModel):
    score_level: str
    usage_band: str | None
    mandatory_modules: list[str]
