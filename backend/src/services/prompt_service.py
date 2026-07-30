from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import TYPE_CHECKING

from src.schemas.prompt import PromptDetail, PromptSummary
from src.services import prompts as P
from src.services.exceptions import DomainError, NotFoundError

if TYPE_CHECKING:
    from src.repositories.prompt_repository import PromptRepository

__all__ = [
    "KNOWN_PROMPTS",
    "REQUIRED_TOKENS",
    "PromptMeta",
    "PromptService",
    "missing_tokens",
]


@dataclass(frozen=True)
class PromptMeta:
    kind: str
    label: str
    group: str


KNOWN_PROMPTS: list[PromptMeta] = [
    PromptMeta("interview", "Interview — conversation", "Interviewer"),
    PromptMeta("interview_playbook", "Interview — playbook generation", "Interviewer"),
    PromptMeta("chatbot", "Chatbot", "Chat"),
    PromptMeta("assessment", "Assessment chat", "Chat"),
    PromptMeta("lesson", "Lesson helper", "Chat"),
    PromptMeta("content_improvement", "Content improvement — draft", "Content (Plan C/D/E)"),
    PromptMeta(
        "content_improvement_critique", "Content improvement — critique", "Content (Plan C/D/E)"
    ),
    PromptMeta("house_style", "House style", "Content (Plan C/D/E)"),
    PromptMeta("feedback_triage", "Feedback triage", "Content (Plan C/D/E)"),
]

REQUIRED_TOKENS: dict[str, tuple[str, ...]] = {
    "interview_playbook": (
        "{first_name}",
        "{assessment_json}",
        "{company_context}",
        "{transcript}",
    ),
}


def missing_tokens(kind: str, content: str) -> list[str]:
    return [t for t in REQUIRED_TOKENS.get(kind, ()) if t not in content]


_KNOWN_KINDS: set[str] = {p.kind for p in KNOWN_PROMPTS}
_META_BY_KIND: dict[str, PromptMeta] = {p.kind: p for p in KNOWN_PROMPTS}


class PromptService:
    """Overlays DB overrides (per `PromptRepository`) on top of the shipped
    prompt files for the admin editor: list/detail views, validated save,
    reset-to-default, and priming the in-process cache (`src.services.prompts`)
    that request-time code actually reads from."""

    def __init__(self, repo: PromptRepository) -> None:
        self._repo = repo

    async def list_all(self) -> list[PromptSummary]:
        rows_by_kind = {row.kind: row for row in await self._repo.list_all()}
        summaries: list[PromptSummary] = []
        for meta in KNOWN_PROMPTS:
            row = rows_by_kind.get(meta.kind)
            summaries.append(
                PromptSummary(
                    kind=meta.kind,
                    label=meta.label,
                    group=meta.group,
                    source="db" if row is not None else "file",
                    updated_at=row.updated_at if row is not None else None,
                )
            )
        return summaries

    async def get(self, kind: str) -> PromptDetail:
        meta = _META_BY_KIND.get(kind)
        if meta is None:
            raise NotFoundError("Prompt")
        row = await self._repo.get(kind)
        content = row.content if row is not None else P.read_file(kind)
        return PromptDetail(
            kind=meta.kind,
            label=meta.label,
            content=content,
            source="db" if row is not None else "file",
            required_tokens=list(REQUIRED_TOKENS.get(kind, ())),
            updated_at=row.updated_at if row is not None else None,
        )

    async def update(self, kind: str, content: str, user_id: uuid.UUID | None) -> None:
        if kind not in _KNOWN_KINDS:
            raise NotFoundError("Prompt")
        missing = missing_tokens(kind, content)
        if missing:
            raise DomainError(f"Prompt is missing required placeholders: {', '.join(missing)}")
        await self._repo.upsert(kind, content, user_id)
        P.set_cache(kind, content)

    async def reset(self, kind: str) -> None:
        if kind not in _KNOWN_KINDS:
            raise NotFoundError("Prompt")
        await self._repo.delete(kind)
        P.reset_cache(kind)

    async def refresh_cache(self) -> None:
        for row in await self._repo.list_all():
            P.set_cache(row.kind, row.content)
