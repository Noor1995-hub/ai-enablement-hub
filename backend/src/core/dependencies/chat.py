from __future__ import annotations

from typing import Annotated, Literal

from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.configs.settings import Settings
from src.core.dependencies.auth import get_current_user
from src.core.dependencies.database import get_session
from src.core.dependencies.domain import get_org_service
from src.core.dependencies.llm import get_llm_service
from src.core.dependencies.settings import get_settings
from src.db.models import User
from src.repositories.conversation_repository import ConversationRepository
from src.repositories.message_repository import MessageRepository
from src.services.chat_service import ChatService
from src.services.llm_service import AnthropicLlmClient
from src.services.org_service import OrgService

__all__ = [
    "get_chat_service",
    "get_conversation_repository",
    "get_message_repository",
    "require_ai_surface",
]

ChatKind = Literal["chatbot", "assessment", "lesson", "interview"]


def get_conversation_repository(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ConversationRepository:
    return ConversationRepository(session)


def get_message_repository(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> MessageRepository:
    return MessageRepository(session)


def get_chat_service(
    conversations: Annotated[ConversationRepository, Depends(get_conversation_repository)],
    messages: Annotated[MessageRepository, Depends(get_message_repository)],
    llm: Annotated[AnthropicLlmClient | None, Depends(get_llm_service)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> ChatService | None:
    """None when LLM__* is unconfigured — the router 404s (see get_llm_service)."""
    if llm is None or settings.llm is None:
        return None
    return ChatService(
        conversations, messages, llm, interview_hard_stop=settings.llm.interview_hard_stop
    )


async def require_ai_surface(
    kind: ChatKind,
    user: Annotated[User, Depends(get_current_user)],
    org: Annotated[OrgService, Depends(get_org_service)],
) -> None:
    """A user with no project can't be verified as paying, so it's treated as
    disabled. Mirrors require_power_admin's shape (a reusable authz-style dependency
    raising HTTPException directly)."""
    if user.project_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="AI feature not enabled for your project"
        )
    settings = await org.resolve_ai_settings(user.project_id)
    if not settings[kind]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="AI feature not enabled for your project"
        )
