from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import TYPE_CHECKING, Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.sse import EventSourceResponse, ServerSentEvent

from src.core.dependencies.auth import get_current_user
from src.core.dependencies.chat import ChatKind, get_chat_service, require_ai_surface
from src.core.dependencies.interview import get_interview_context_service
from src.core.dependencies.ratelimit import get_rate_limiter
from src.core.ratelimit import RateLimiter
from src.db.models import User
from src.schemas.chat import (
    ChatMessageCreate,
    ConversationDetailResponse,
    ConversationListResponse,
    ConversationSummary,
    MessageResponse,
)
from src.services.chat_service import ChatService, DoneEvent, TokenEvent
from src.services.exceptions import NotFoundError
from src.services.interview_context import InterviewContextService

if TYPE_CHECKING:
    from src.db.models import Conversation

__all__ = ["router"]

router = APIRouter(prefix="/api/chat", tags=["chat"])

CurrentUserDep = Annotated[User, Depends(get_current_user)]
ChatServiceDep = Annotated[ChatService | None, Depends(get_chat_service)]
RateLimiterDep = Annotated[RateLimiter, Depends(get_rate_limiter)]

_RATE_LIMITED_SHORT = HTTPException(
    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
    detail="Too many messages — try again shortly",
    headers={"Retry-After": "60"},
)
_RATE_LIMITED_DAILY = HTTPException(
    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
    detail="Daily chat limit reached",
    headers={"Retry-After": "3600"},
)


@dataclass
class _PreparedChat:
    """Everything the streaming generator needs, already resolved.

    NOTE ON STRUCTURE (deviation from the plan's sketch): the plan wrote
    `send_chat_message` as a plain `async def` that does the 404/429/404
    pre-flight checks and then `return`s an inner `_events()` async generator.
    Verified (via a standalone experiment against this repo's installed
    fastapi==0.139.0) that this shape is actually broken: FastAPI's SSE
    routing only treats a path operation as streamable when the operation
    function ITSELF is an async-generator function (`inspect.isasyncgenfunction`
    — i.e. contains a `yield` directly in its own body); otherwise it calls
    `iterate_in_threadpool()` on the un-awaited coroutine the outer function
    returns, which blows up with an unhandled ExceptionGroup and a "coroutine
    was never awaited" warning.

    A real async-generator endpoint only starts executing its body on the
    first `__anext__()` — which FastAPI's SSE plumbing pulls from a background
    producer task AFTER it has already committed to a 200 response with
    text/event-stream headers. Any HTTPException/NotFoundError raised from
    inside that body arrives too late to change the status code (confirmed by
    the same experiment: raising inside the generator surfaces as an
    unhandled ExceptionGroup, never a clean 4xx).

    So the fix is to do all pre-flight work (chat_service configured?,
    rate limits, ChatService.resolve_conversation) in a plain `Depends()`
    callable — those run eagerly during normal dependency solving, well
    before the SSE branch, so a raised HTTPException/NotFoundError becomes a
    normal response through the existing exception handlers (also confirmed
    by the experiment). `send_chat_message` below is then a genuine
    async-generator function doing only the streaming.
    """

    chat_service: ChatService
    conversation: Conversation
    content: str
    system_suffix: str | None = None


async def _prepare_chat_message(
    kind: ChatKind,
    body: ChatMessageCreate,
    user: CurrentUserDep,
    chat_service: ChatServiceDep,
    limiter: RateLimiterDep,
    interview_context: Annotated[InterviewContextService, Depends(get_interview_context_service)],
) -> _PreparedChat:
    if chat_service is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat is not configured")
    if limiter.is_limited(f"chat:{user.id}", max_calls=20, window_seconds=300):
        raise _RATE_LIMITED_SHORT
    if limiter.is_limited(f"chat-daily:{user.id}", max_calls=200, window_seconds=86400):
        raise _RATE_LIMITED_DAILY
    conversation = await chat_service.resolve_conversation(
        user_id=user.id, kind=kind, conversation_id=body.conversation_id
    )
    system_suffix = await interview_context.build_briefing(user) if kind == "interview" else None
    return _PreparedChat(
        chat_service=chat_service,
        conversation=conversation,
        content=body.content,
        system_suffix=system_suffix,
    )


ChatRequestDep = Annotated[_PreparedChat, Depends(_prepare_chat_message)]


@router.post(
    "/{kind}",
    response_class=EventSourceResponse,
    dependencies=[Depends(require_ai_surface)],
)
async def send_chat_message(chat_request: ChatRequestDep) -> AsyncIterator[ServerSentEvent]:
    async for event in chat_request.chat_service.send_message(
        conversation=chat_request.conversation,
        content=chat_request.content,
        system_suffix=chat_request.system_suffix,
    ):
        if isinstance(event, TokenEvent):
            yield ServerSentEvent(data={"text": event.text}, event="token")
        elif isinstance(event, DoneEvent):
            usage = (
                {
                    "input_tokens": event.usage.input_tokens,
                    "output_tokens": event.usage.output_tokens,
                }
                if event.usage is not None
                else None
            )
            yield ServerSentEvent(
                data={
                    "conversation_id": str(event.conversation_id),
                    "truncated": event.truncated,
                    "usage": usage,
                },
                event="done",
            )


@router.get("/conversations", response_model=ConversationListResponse)
async def list_conversations(
    user: CurrentUserDep,
    chat_service: ChatServiceDep,
    kind: Annotated[ChatKind, Query()],
) -> ConversationListResponse:
    if chat_service is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat is not configured")
    conversations = await chat_service.list_conversations(user_id=user.id, kind=kind)
    return ConversationListResponse(
        conversations=[ConversationSummary.model_validate(c) for c in conversations]
    )


@router.get("/conversations/{conversation_id}", response_model=ConversationDetailResponse)
async def get_conversation(
    conversation_id: uuid.UUID,
    user: CurrentUserDep,
    chat_service: ChatServiceDep,
) -> ConversationDetailResponse:
    if chat_service is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat is not configured")
    try:
        conversation, messages = await chat_service.get_conversation_detail(
            user_id=user.id, conversation_id=conversation_id
        )
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return ConversationDetailResponse(
        conversation=ConversationSummary.model_validate(conversation),
        messages=[MessageResponse.model_validate(m) for m in messages],
    )
