from __future__ import annotations

from dataclasses import dataclass

from src.schemas.prompt import PromptDetail, PromptSummary
from src.services import prompts as P
from src.services.exceptions import NotFoundError
from src.services.interview_marker import READY_MARKER

__all__ = ["KNOWN_PROMPTS", "REQUIRED_TOKENS", "PromptMeta", "PromptService", "prompt_path"]


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
    # The interviewer's only machine-read output: without it the Build button never
    # appears except through the 6-answer fallback.
    "interview": (READY_MARKER,),
    "interview_playbook": (
        "{first_name}",
        "{assessment_json}",
        "{company_context}",
        "{transcript}",
    ),
}


_META_BY_KIND: dict[str, PromptMeta] = {p.kind: p for p in KNOWN_PROMPTS}


def prompt_path(kind: str) -> str:
    """Repo-relative path of the file that is the prompt's only source of truth."""
    return f"backend/prompts/{kind}.md"


class PromptService:
    """Read-only view of the shipped prompt files for the admin System Prompts page.
    Git is the only source of truth (2026-09-23, spec 2026-09-23-prompts-git-only):
    a prompt changes by pull request and ships with the next deploy."""

    def list_all(self) -> list[PromptSummary]:
        return [
            PromptSummary(kind=m.kind, label=m.label, group=m.group, path=prompt_path(m.kind))
            for m in KNOWN_PROMPTS
        ]

    def get(self, kind: str) -> PromptDetail:
        meta = _META_BY_KIND.get(kind)
        if meta is None:
            raise NotFoundError("Prompt")
        return PromptDetail(
            kind=meta.kind, label=meta.label, content=P.read_file(kind), path=prompt_path(kind)
        )
