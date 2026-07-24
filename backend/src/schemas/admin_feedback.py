from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel

__all__ = ["AdminFeedbackListResponse", "AdminFeedbackOut", "FeedbackStatusUpdateRequest"]

FeedbackStatus = Literal["new", "accepted", "dismissed"]


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


class AdminFeedbackListResponse(BaseModel):
    items: list[AdminFeedbackOut]
    total: int
    limit: int
    offset: int


class FeedbackStatusUpdateRequest(BaseModel):
    status: FeedbackStatus
