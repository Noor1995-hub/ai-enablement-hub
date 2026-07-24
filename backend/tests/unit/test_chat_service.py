from __future__ import annotations

import asyncio
import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from src.repositories.base import AbstractConversationRepository, AbstractMessageRepository
from src.services.chat_service import ChatService, DoneEvent, TokenEvent
from src.services.exceptions import NotFoundError
from tests.fixtures.llm import FakeLlmClient


def _service(llm: FakeLlmClient) -> tuple[ChatService, AsyncMock, AsyncMock]:
    conversations = AsyncMock(spec=AbstractConversationRepository)
    messages = AsyncMock(spec=AbstractMessageRepository)
    messages.list_recent.return_value = []
    return ChatService(conversations, messages, llm), conversations, messages  # ty: ignore[invalid-argument-type]


async def test_resolve_conversation_creates_new_when_no_id() -> None:
    service, conversations, _ = _service(FakeLlmClient(chunks=[]))
    conversations.create.return_value = SimpleNamespace(id=uuid.uuid4(), user_id=uuid.uuid4())
    user_id = uuid.uuid4()

    conversation = await service.resolve_conversation(
        user_id=user_id, kind="chatbot", conversation_id=None
    )

    conversations.create.assert_awaited_once_with(user_id=user_id, kind="chatbot")
    assert conversation is conversations.create.return_value


async def test_resolve_conversation_rejects_someone_elses() -> None:
    service, conversations, _ = _service(FakeLlmClient(chunks=[]))
    other_user_id = uuid.uuid4()
    conversations.get_by_id.return_value = SimpleNamespace(id=uuid.uuid4(), user_id=other_user_id)

    with pytest.raises(NotFoundError):
        await service.resolve_conversation(
            user_id=uuid.uuid4(), kind="chatbot", conversation_id=uuid.uuid4()
        )


async def test_send_message_streams_tokens_then_done_and_persists() -> None:
    llm = FakeLlmClient(chunks=["Hel", "lo!"])
    service, _, messages = _service(llm)
    conversation = SimpleNamespace(id=uuid.uuid4(), user_id=uuid.uuid4(), kind="chatbot")

    events = [
        e
        async for e in service.send_message(
            conversation=conversation,  # ty: ignore[invalid-argument-type]
            content="hi",
        )
    ]

    assert [type(e).__name__ for e in events] == ["TokenEvent", "TokenEvent", "DoneEvent"]
    assert events[0] == TokenEvent("Hel")
    assert events[1] == TokenEvent("lo!")
    done = events[2]
    assert isinstance(done, DoneEvent)
    assert done.conversation_id == conversation.id
    assert done.truncated is False

    # user turn + assistant turn persisted; assistant content is the full accumulation
    assert messages.create.await_count == 2
    user_call, assistant_call = messages.create.await_args_list
    assert user_call.kwargs == {"role": "user", "content": "hi", "metadata": None}
    assert assistant_call.kwargs["role"] == "assistant"
    assert assistant_call.kwargs["content"] == "Hello!"
    assert assistant_call.kwargs["metadata"]["truncated"] is False


async def test_send_message_persists_partial_on_disconnect() -> None:
    llm = FakeLlmClient(chunks=["Hel", "lo!"])
    service, _, messages = _service(llm)
    conversation = SimpleNamespace(id=uuid.uuid4(), user_id=uuid.uuid4(), kind="chatbot")

    agen = service.send_message(
        conversation=conversation,  # ty: ignore[invalid-argument-type]
        content="hi",
    )
    first = await agen.__anext__()  # consume one TokenEvent
    assert first == TokenEvent("Hel")
    # aclose/athrow aren't part of the declared AsyncIterator return type, but the
    # object returned by an async-generator function has them at runtime.
    await agen.aclose()  # ty: ignore[unresolved-attribute]  # -> GeneratorExit -> disconnect

    # user turn + partial assistant turn both persisted; assistant marked truncated
    assert messages.create.await_count == 2
    _user_call, assistant_call = messages.create.await_args_list
    assert assistant_call.kwargs["role"] == "assistant"
    assert assistant_call.kwargs["metadata"]["truncated"] is True
    # partial content = only the chunk that was appended before the yield that got
    # interrupted (chunks.append happens before the yield, so only "Hel" made it in;
    # "lo!" was never appended because the for-loop never resumed after the close).
    assert assistant_call.kwargs["content"] == "Hel"


async def test_send_message_persists_partial_on_cancellation() -> None:
    llm = FakeLlmClient(chunks=["Hel", "lo!"])
    service, _, messages = _service(llm)
    conversation = SimpleNamespace(id=uuid.uuid4(), user_id=uuid.uuid4(), kind="chatbot")

    agen = service.send_message(
        conversation=conversation,  # ty: ignore[invalid-argument-type]
        content="hi",
    )
    first = await agen.__anext__()  # consume one TokenEvent
    assert first == TokenEvent("Hel")

    # simulate ASGI-level task cancellation mid-stream (distinct from a client
    # disconnect / GeneratorExit): athrow propagates CancelledError back out since
    # the generator re-raises the same exception it was thrown.
    with pytest.raises(asyncio.CancelledError):
        await agen.athrow(asyncio.CancelledError)  # ty: ignore[unresolved-attribute]

    assert messages.create.await_count == 2
    _user_call, assistant_call = messages.create.await_args_list
    assert assistant_call.kwargs["role"] == "assistant"
    assert assistant_call.kwargs["metadata"]["truncated"] is True
    assert assistant_call.kwargs["content"] == "Hel"
