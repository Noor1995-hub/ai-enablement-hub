from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel

__all__ = [
    "AdminFeedbackListResponse",
    "AdminFeedbackOut",
    "FeedbackStatusUpdateRequest",
    "SuggestTriageResponse",
]

FeedbackStatus = Literal["new", "accepted", "dismissed"]
# An AI triage suggestion is one of the two *terminal* dispositions — never
# 'new', and never written to the real `status` column.
FeedbackSuggestion = Literal["accepted", "dismissed"]


class AdminFeedbackOut(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    user_name: str
    company_name: str | None
    project_name: str | None
    lesson_id: uuid.UUID
    lesson_title: str
    module_id: uuid.UUID
    module_title: str
    track_id: uuid.UUID
    track_name: str
    track_level: str
    message: str
    status: FeedbackStatus
    created_at: datetime
    reviewed_at: datetime | None
    # AI-assisted triage (Plan B) — a suggestion for the admin, not a decision.
    # All three are null until a suggest-triage run covers the row.
    ai_suggested_status: FeedbackSuggestion | None = None
    ai_rationale: str | None = None
    ai_suggested_at: datetime | None = None


class AdminFeedbackListResponse(BaseModel):
    items: list[AdminFeedbackOut]
    total: int
    limit: int
    offset: int


class FeedbackStatusUpdateRequest(BaseModel):
    status: FeedbackStatus


class SuggestTriageResponse(BaseModel):
    """`suggested` = suggestions written by this (bounded) run; `remaining` =
    rows that still lack one, so a truncated run is never silent."""

    suggested: int
    remaining: int
