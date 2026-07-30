"""DI providers for InterviewContextService/InterviewService and the
"interview" AI-surface gate.

All parameter annotations are runtime imports on purpose: FastAPI evaluates
the deferred annotations against module globals, and an unresolvable name
silently degrades the parameter to a required query param (see database.py).
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException, status

from src.core.dependencies.auth import get_current_user
from src.core.dependencies.chat import get_conversation_repository, get_message_repository
from src.core.dependencies.domain import (
    get_learning_service,
    get_maturity_service,
    get_org_service,
    get_survey_service,
)
from src.core.dependencies.llm import get_llm_service
from src.db.models import User
from src.repositories.conversation_repository import ConversationRepository
from src.repositories.message_repository import MessageRepository
from src.services.interview_context import InterviewContextService
from src.services.interview_service import InterviewService
from src.services.learning_service import LearningService
from src.services.llm_service import AnthropicLlmClient
from src.services.maturity_service import MaturityService
from src.services.org_service import OrgService
from src.services.survey_service import SurveyService

__all__ = [
    "get_interview_context_service",
    "get_interview_service",
    "require_interview_surface",
]


def get_interview_context_service(
    surveys: Annotated[SurveyService, Depends(get_survey_service)],
    maturity: Annotated[MaturityService, Depends(get_maturity_service)],
    learning: Annotated[LearningService, Depends(get_learning_service)],
) -> InterviewContextService:
    return InterviewContextService(surveys, maturity, learning)


def get_interview_service(
    conversations: Annotated[ConversationRepository, Depends(get_conversation_repository)],
    messages: Annotated[MessageRepository, Depends(get_message_repository)],
    llm: Annotated[AnthropicLlmClient | None, Depends(get_llm_service)],
    context: Annotated[InterviewContextService, Depends(get_interview_context_service)],
) -> InterviewService | None:
    """None when LLM__* is unconfigured — the router 404s (mirrors get_chat_service)."""
    if llm is None:
        return None
    return InterviewService(conversations, messages, llm, context)


async def require_interview_surface(
    user: Annotated[User, Depends(get_current_user)],
    org: Annotated[OrgService, Depends(get_org_service)],
) -> None:
    """Mirrors require_ai_surface, but for the fixed "interview" kind — these
    routes have no {kind} path segment."""
    if user.project_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="AI feature not enabled for your project"
        )
    settings = await org.resolve_ai_settings(user.project_id)
    if not settings.get("interview", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="AI feature not enabled for your project"
        )
