from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

__all__ = [
    "PromptDetail",
    "PromptListResponse",
    "PromptSummary",
    "PromptUpdateRequest",
]


class PromptSummary(BaseModel):
    kind: str
    label: str
    group: str
    source: str  # "file" | "db"
    updated_at: datetime | None = None


class PromptDetail(BaseModel):
    kind: str
    label: str
    content: str
    source: str
    required_tokens: list[str]
    updated_at: datetime | None = None


class PromptListResponse(BaseModel):
    prompts: list[PromptSummary]


class PromptUpdateRequest(BaseModel):
    content: str = Field(..., min_length=1)
