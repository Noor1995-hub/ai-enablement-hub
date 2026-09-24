from __future__ import annotations

from pydantic import BaseModel

__all__ = ["PromptDetail", "PromptListResponse", "PromptSummary"]


class PromptSummary(BaseModel):
    kind: str
    label: str
    group: str
    path: str  # repo-relative, e.g. backend/prompts/interview.md


class PromptDetail(BaseModel):
    kind: str
    label: str
    content: str
    path: str


class PromptListResponse(BaseModel):
    prompts: list[PromptSummary]
