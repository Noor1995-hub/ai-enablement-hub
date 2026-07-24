from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator

__all__ = [
    "ChatMessageCreate",
    "ConversationDetailResponse",
    "ConversationListResponse",
    "ConversationSummary",
    "MessageResponse",
]


class ChatMessageCreate(BaseModel):
    content: str
    conversation_id: uuid.UUID | None = None

    @field_validator("content")
    @classmethod
    def _strip_non_empty(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            msg = "content must not be empty"
            raise ValueError(msg)
        if len(stripped) > 4000:
            msg = "content must be at most 4000 characters"
            raise ValueError(msg)
        return stripped


class ConversationSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    kind: str
    context_ref: str | None
    created_at: datetime
    updated_at: datetime


class MessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    role: str
    content: str
    created_at: datetime


class ConversationListResponse(BaseModel):
    conversations: list[ConversationSummary]


class ConversationDetailResponse(BaseModel):
    conversation: ConversationSummary
    messages: list[MessageResponse]
