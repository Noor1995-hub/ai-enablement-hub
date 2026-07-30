from __future__ import annotations

from dataclasses import dataclass


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
