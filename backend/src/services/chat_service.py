from __future__ import annotations

import asyncio
import uuid
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from src.services.exceptions import NotFoundError
from src.services.prompts import load_prompt

if TYPE_CHECKING:
    from src.db.models import Conversation, Message
    from src.repositories.base import AbstractConversationRepository, AbstractMessageRepository
    from src.services.llm_service import LlmClient, LlmUsage

__all__ = ["ChatService", "ChatStreamEvent", "DoneEvent", "TokenEvent"]

_HISTORY_WINDOW = 20
_MAX_TOKENS = 1024


@dataclass(frozen=True)
class TokenEvent:
    text: str


@dataclass(frozen=True)
class DoneEvent:
    conversation_id: uuid.UUID
    truncated: bool
    usage: LlmUsage | None


ChatStreamEvent = TokenEvent | DoneEvent


class ChatService:
    """Owns the completion loop: persist the user turn -> call the model ->
    stream the assistant turn -> persist it on completion (or on client
    disconnect, marked truncated)."""

    def __init__(
        self,
        conversations: AbstractConversationRepository,
        messages: AbstractMessageRepository,
        llm: LlmClient,
    ) -> None:
        self._conversations = conversations
        self._messages = messages
        self._llm = llm

    async def resolve_conversation(
        self, *, user_id: uuid.UUID, kind: str, conversation_id: uuid.UUID | None
    ) -> Conversation:
        """Runs BEFORE any streaming starts (never inside the generator) so a
        NotFoundError becomes a plain 404 through the existing exception
        handler, not a mid-stream error event."""
        if conversation_id is None:
            return await self._conversations.create(user_id=user_id, kind=kind)
        conversation = await self._conversations.get_by_id(conversation_id)
        if conversation is None or conversation.user_id != user_id:
            raise NotFoundError("Conversation")
        return conversation

    async def list_conversations(self, *, user_id: uuid.UUID, kind: str) -> list[Conversation]:
        return await self._conversations.list_for_user(user_id, kind)

    async def get_conversation_detail(
        self, *, user_id: uuid.UUID, conversation_id: uuid.UUID
    ) -> tuple[Conversation, list[Message]]:
        conversation = await self._conversations.get_by_id(conversation_id)
        if conversation is None or conversation.user_id != user_id:
            raise NotFoundError("Conversation")
        messages = await self._messages.list_for_conversation(conversation_id)
        return conversation, messages

    async def send_message(
        self, *, conversation: Conversation, content: str
    ) -> AsyncIterator[ChatStreamEvent]:
        await self._messages.create(conversation.id, role="user", content=content, metadata=None)
        system_prompt = load_prompt(conversation.kind)
        history = await self._history_for(conversation.id)

        chunks: list[str] = []
        truncated = False
        usage: LlmUsage | None = None
        try:
            async with self._llm.stream_reply(
                system=system_prompt, messages=history, max_tokens=_MAX_TOKENS
            ) as reply:
                async for text in reply:
                    chunks.append(text)
                    yield TokenEvent(text)
                usage = await reply.usage()
        except (GeneratorExit, asyncio.CancelledError):
            # Both a client disconnect (GeneratorExit, injected by aclose()) and an
            # ASGI-level task cancellation (asyncio.CancelledError) mid-stream mean
            # the reply is incomplete -> mark it truncated before persisting.
            truncated = True
            raise
        finally:
            accumulated = "".join(chunks)
            if accumulated:
                metadata: dict[str, Any] = {"truncated": truncated}
                if usage is not None:
                    metadata["usage"] = {
                        "input_tokens": usage.input_tokens,
                        "output_tokens": usage.output_tokens,
                    }
                await asyncio.shield(
                    self._messages.create(
                        conversation.id, role="assistant", content=accumulated, metadata=metadata
                    )
                )
                await asyncio.shield(self._conversations.touch(conversation.id))

        if not truncated:
            yield DoneEvent(conversation_id=conversation.id, truncated=False, usage=usage)

    async def _history_for(self, conversation_id: uuid.UUID) -> list[dict[str, str]]:
        rows = await self._messages.list_recent(conversation_id, limit=_HISTORY_WINDOW)
        return [
            {"role": m.role, "content": m.content} for m in rows if m.role in ("user", "assistant")
        ]
