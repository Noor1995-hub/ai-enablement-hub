from __future__ import annotations

import asyncio
import logging
import uuid
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from src.services.exceptions import NotFoundError
from src.services.interview_marker import strip_ready_marker
from src.services.llm_service import is_provider_busy_error, is_provider_error
from src.services.prompts import load_prompt, prompt_version

if TYPE_CHECKING:
    from src.db.models import Conversation, Message
    from src.repositories.base import AbstractConversationRepository, AbstractMessageRepository
    from src.services.llm_service import LlmClient, LlmUsage

__all__ = ["ChatService", "ChatStreamEvent", "DoneEvent", "ErrorEvent", "TokenEvent"]

logger = logging.getLogger(__name__)

_HISTORY_WINDOW = 20
_MAX_TOKENS = 1024
_BUSY_MESSAGE = "The assistant is busy right now - please try again in a moment."
_GENERIC_MESSAGE = "Something went wrong generating the reply - please try again."


@dataclass(frozen=True)
class TokenEvent:
    text: str


@dataclass(frozen=True)
class DoneEvent:
    conversation_id: uuid.UUID
    truncated: bool
    usage: LlmUsage | None


@dataclass(frozen=True)
class ErrorEvent:
    """Terminal frame for a failure the HTTP layer can no longer express.

    By the time the model is streaming, a 200 and the text/event-stream headers
    are already on the wire, so a provider failure cannot become a 4xx/5xx --
    the only way to tell the learner anything is in-band. Mutually exclusive
    with DoneEvent: a `done` frame after this would claim the reply finished.
    Carries the conversation id so a client whose FIRST turn failed can
    continue this conversation instead of starting (and orphaning) another.
    """

    message: str
    conversation_id: uuid.UUID


ChatStreamEvent = TokenEvent | DoneEvent | ErrorEvent


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
        # kind must match the PATH segment, not just ownership: require_ai_surface
        # gates on the path kind while send_message below loads the system prompt
        # from conversation.kind, so a mismatch would let an enabled surface
        # continue a disabled one's conversation (and write into the interview
        # transcript admins read).
        if conversation is None or conversation.user_id != user_id or conversation.kind != kind:
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
        self, *, conversation: Conversation, content: str, system_suffix: str | None = None
    ) -> AsyncIterator[ChatStreamEvent]:
        await self._messages.create(conversation.id, role="user", content=content, metadata=None)
        system_prompt = load_prompt(conversation.kind)
        if system_suffix:
            system_prompt = f"{system_prompt}\n\n{system_suffix}"
        history = await self._history_for(conversation.id)

        chunks: list[str] = []
        truncated = False
        usage: LlmUsage | None = None
        failure: str | None = None
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
        except Exception as exc:  # noqa: BLE001 - reported in-band, see ErrorEvent
            # After the cancellation clause for readability only: GeneratorExit and
            # CancelledError derive from BaseException, so this can't shadow them.
            # It also wraps `reply.usage()`: a failure after the full text streamed
            # is still reported as an error (reply marked truncated) -- accepted.
            truncated = True
            failure = _BUSY_MESSAGE if is_provider_busy_error(exc) else _GENERIC_MESSAGE
            _log_stream_failure(exc, conversation.id)
        finally:
            accumulated = "".join(chunks)
            if accumulated:
                metadata: dict[str, Any] = {
                    "truncated": truncated,
                    "model": self._llm.model,
                    "prompt_version": prompt_version(conversation.kind),
                }
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

        if failure is not None:
            yield ErrorEvent(message=failure, conversation_id=conversation.id)
        elif not truncated:
            yield DoneEvent(conversation_id=conversation.id, truncated=False, usage=usage)

    async def _history_for(self, conversation_id: uuid.UUID) -> list[dict[str, str]]:
        rows = await self._messages.list_recent(conversation_id, limit=_HISTORY_WINDOW)
        # strip_ready_marker: only the interviewer ever emits it, and the model must not
        # re-read its own UI signal on every later turn (spec 2026-09-26 A.1, §8.4).
        return [
            {
                "role": m.role,
                "content": strip_ready_marker(m.content) if m.role == "assistant" else m.content,
            }
            for m in rows
            if m.role in ("user", "assistant")
        ]


def _log_stream_failure(exc: Exception, conversation_id: uuid.UUID) -> None:
    """Same split as interview_service: `warning` with the type name for a
    failure retrying could fix, `error` with the traceback for anything else (a
    revoked key, a bad request, a bug). Never the prompt or the learner's text.
    Keyed on the busy check (a superset of `is_transient_provider_error`) so an
    in-stream overload -- the common mid-stream case -- isn't paged as an error.
    """
    if is_provider_busy_error(exc):
        logger.warning(
            "chat stream failed (transient, %s) for conversation %s",
            type(exc).__name__,
            conversation_id,
        )
    else:
        # is_provider_error (#76) tells a provider-reported failure (a revoked key,
        # a 400) apart from a bug in our own code; both deserve the traceback.
        logger.error(
            "chat stream failed (%s, %s) for conversation %s",
            "provider" if is_provider_error(exc) else "unexpected",
            type(exc).__name__,
            conversation_id,
            exc_info=exc,
        )
