from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator

__all__ = ["FeedbackCreate", "FeedbackResponse"]


class FeedbackCreate(BaseModel):
    lesson_id: uuid.UUID
    message: str

    @field_validator("message")
    @classmethod
    def _strip_non_empty(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            msg = "message must not be empty"
            raise ValueError(msg)
        if len(stripped) > 4000:
            msg = "message must be at most 4000 characters"
            raise ValueError(msg)
        return stripped


class FeedbackResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    created_at: datetime
