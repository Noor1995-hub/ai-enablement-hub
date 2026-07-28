"""DI for the feedback-driven content-improvement agents.

All parameter annotations are runtime imports on purpose: FastAPI evaluates the
deferred annotations against module globals, and an unresolvable name silently
degrades the parameter to a required query param (see database.py).
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from src.core.dependencies.domain import get_feedback_repository
from src.core.dependencies.llm import get_llm_service
from src.repositories.feedback_repository import FeedbackRepository
from src.services.feedback_triage_service import FeedbackTriageService
from src.services.llm_service import AnthropicLlmClient

__all__ = ["get_feedback_triage_service"]


def get_feedback_triage_service(
    feedback: Annotated[FeedbackRepository, Depends(get_feedback_repository)],
    llm: Annotated[AnthropicLlmClient | None, Depends(get_llm_service)],
) -> FeedbackTriageService | None:
    """None when LLM__* is unconfigured — the endpoint 404s (mirrors
    get_chat_service; the feature has no meaning without a model)."""
    if llm is None:
        return None
    return FeedbackTriageService(feedback, llm)
