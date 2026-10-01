from __future__ import annotations

from typing import Final, Literal

__all__ = [
    "DEFAULT_LANGUAGE",
    "INTERVIEW_LANGUAGES",
    "InterviewLanguage",
    "language_directive",
    "resolve_language",
]

# The language the learner picks on the interview's welcome screen (#83). Stored on the
# interview conversation; NULL (a conversation from before the picker) counts as English.
InterviewLanguage = Literal["en", "nl"]
INTERVIEW_LANGUAGES: Final[tuple[InterviewLanguage, ...]] = ("en", "nl")
DEFAULT_LANGUAGE: Final[InterviewLanguage] = "en"


def resolve_language(value: str | None) -> InterviewLanguage:
    """The stored value as a known language: anything else (NULL, a stray value) is English,
    so free text can never reach a prompt."""
    if value in INTERVIEW_LANGUAGES:
        return value
    return DEFAULT_LANGUAGE


def language_directive(value: str | None) -> str:
    """The line appended to both interviewer prompts (opener, every chat turn, the playbook):
    a fixed tag the prompts refer to (`backend/prompts/interview.md`, Language), never
    learner text."""
    return f"<interview_language>{resolve_language(value)}</interview_language>"
