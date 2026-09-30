from __future__ import annotations

import asyncio
import logging
import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock

import anthropic
import pytest

from src.repositories.base import AbstractConversationRepository, AbstractMessageRepository
from src.services.chat_service import (
    ChatService,
    ChatStreamEvent,
    DoneEvent,
    ErrorEvent,
    TokenEvent,
)
from src.services.exceptions import NotFoundError
from src.services.prompts import load_prompt, prompt_version
from tests.fixtures.llm import (
    FailingLlmClient,
    FakeLlmClient,
    connection_error,
    in_stream_error,
    overloaded_error,
    status_error,
)


def _service(llm: FakeLlmClient) -> tuple[ChatService, AsyncMock, AsyncMock]:
    conversations = AsyncMock(spec=AbstractConversationRepository)
    messages = AsyncMock(spec=AbstractMessageRepository)
    messages.list_recent.return_value = []
    return ChatService(conversations, messages, llm), conversations, messages


async def test_resolve_conversation_creates_new_when_no_id() -> None:
    service, conversations, _ = _service(FakeLlmClient(chunks=[]))
    conversations.create.return_value = SimpleNamespace(id=uuid.uuid4(), user_id=uuid.uuid4())
    user_id = uuid.uuid4()

    conversation = await service.resolve_conversation(
        user_id=user_id, kind="chatbot", conversation_id=None
    )

    conversations.create.assert_awaited_once_with(user_id=user_id, kind="chatbot")
    assert conversation is conversations.create.return_value


async def test_resolve_conversation_creates_the_first_interview_race_safely() -> None:
    service, conversations, _ = _service(FakeLlmClient(chunks=[]))
    created = SimpleNamespace(id=uuid.uuid4(), user_id=uuid.uuid4(), kind="interview")
    conversations.create_interview_if_absent.return_value = created
    user_id = uuid.uuid4()

    conversation = await service.resolve_conversation(
        user_id=user_id, kind="interview", conversation_id=None
    )

    conversations.create_interview_if_absent.assert_awaited_once_with(user_id)
    conversations.create.assert_not_awaited()
    assert conversation is created


async def test_resolve_conversation_reuses_the_existing_interview() -> None:
    """One interview per user (uq_conversations_interview_user_id): no id means
    "my interview", never a second row (which the index would turn into a 500)."""
    service, conversations, _ = _service(FakeLlmClient(chunks=[]))
    user_id = uuid.uuid4()
    existing = SimpleNamespace(id=uuid.uuid4(), user_id=user_id, kind="interview")
    conversations.create_interview_if_absent.return_value = None
    conversations.list_for_user.return_value = [existing]

    conversation = await service.resolve_conversation(
        user_id=user_id, kind="interview", conversation_id=None
    )

    assert conversation is existing
    conversations.list_for_user.assert_awaited_once_with(user_id, "interview")
    conversations.create.assert_not_awaited()


async def test_resolve_conversation_404s_if_the_interview_vanishes_mid_race() -> None:
    """Lost the insert race, then the winner was reset before the re-read."""
    service, conversations, _ = _service(FakeLlmClient(chunks=[]))
    conversations.create_interview_if_absent.return_value = None
    conversations.list_for_user.return_value = []

    with pytest.raises(NotFoundError):
        await service.resolve_conversation(
            user_id=uuid.uuid4(), kind="interview", conversation_id=None
        )
    conversations.create.assert_not_awaited()


async def test_resolve_conversation_rejects_someone_elses() -> None:
    service, conversations, _ = _service(FakeLlmClient(chunks=[]))
    other_user_id = uuid.uuid4()
    conversations.get_by_id.return_value = SimpleNamespace(id=uuid.uuid4(), user_id=other_user_id)

    with pytest.raises(NotFoundError):
        await service.resolve_conversation(
            user_id=uuid.uuid4(), kind="chatbot", conversation_id=uuid.uuid4()
        )


async def test_resolve_conversation_rejects_a_different_kind() -> None:
    """The AI-surface gate is keyed on the PATH kind while send_message loads the
    system prompt from the STORED row, so accepting a mismatched conversation
    would let an enabled surface drive a disabled one's conversation."""
    service, conversations, _ = _service(FakeLlmClient(chunks=[]))
    user_id = uuid.uuid4()
    conversations.get_by_id.return_value = SimpleNamespace(
        id=uuid.uuid4(), user_id=user_id, kind="interview"
    )

    with pytest.raises(NotFoundError):
        await service.resolve_conversation(
            user_id=user_id, kind="chatbot", conversation_id=uuid.uuid4()
        )


async def test_list_conversations_caps_the_repository_read_at_fifty() -> None:
    """Decision 5.11: cap the dialogue-history read now; the retention window
    (deleting old rows) is a separate, still-open decision."""
    service, conversations, _ = _service(FakeLlmClient(chunks=[]))
    conversations.list_for_user.return_value = []
    user_id = uuid.uuid4()

    await service.list_conversations(user_id=user_id, kind="chatbot")

    conversations.list_for_user.assert_awaited_once_with(user_id, "chatbot", limit=50)


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
    assert assistant_call.kwargs["metadata"]["model"] == "fake-model"
    assert assistant_call.kwargs["metadata"]["prompt_version"] == prompt_version("chatbot")


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


async def test_send_message_without_system_suffix_is_unchanged() -> None:
    llm = FakeLlmClient(chunks=["Hi"])
    service, _, _ = _service(llm)
    conversation = SimpleNamespace(id=uuid.uuid4(), user_id=uuid.uuid4(), kind="chatbot")

    events = [
        e
        async for e in service.send_message(
            conversation=conversation,  # ty: ignore[invalid-argument-type]
            content="hi",
        )
    ]

    assert [type(e).__name__ for e in events] == ["TokenEvent", "DoneEvent"]
    assert llm.calls[0]["system"] == load_prompt("chatbot")


async def test_send_message_appends_system_suffix() -> None:
    llm = FakeLlmClient(chunks=["Hi"])
    service, _, _ = _service(llm)
    conversation = SimpleNamespace(id=uuid.uuid4(), user_id=uuid.uuid4(), kind="chatbot")

    events = [
        e
        async for e in service.send_message(
            conversation=conversation,  # ty: ignore[invalid-argument-type]
            content="hi",
            system_suffix="BRIEFING-XYZ",
        )
    ]

    assert [type(e).__name__ for e in events] == ["TokenEvent", "DoneEvent"]
    system = llm.calls[0]["system"]
    assert system.endswith("BRIEFING-XYZ")  # ty: ignore[unresolved-attribute]
    assert system.startswith(load_prompt("chatbot"))  # ty: ignore[unresolved-attribute]


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


async def test_history_sent_to_the_model_has_no_ready_marker() -> None:
    """Once emitted, the marker must not be re-read by the model on every later turn."""
    llm = FakeLlmClient(chunks=["ok"])
    service, _, messages = _service(llm)
    messages.list_recent.return_value = [
        SimpleNamespace(role="assistant", content="Shall I build it?\n[[READY_TO_BUILD]]"),
        SimpleNamespace(role="user", content="one more thing"),
    ]
    conversation = SimpleNamespace(id=uuid.uuid4(), user_id=uuid.uuid4(), kind="interview")

    _ = [
        e
        async for e in service.send_message(
            conversation=conversation,  # ty: ignore[invalid-argument-type]
            content="one more thing",
        )
    ]

    sent = llm.calls[0]["messages"]
    assert sent == [
        {"role": "assistant", "content": "Shall I build it?"},
        {"role": "user", "content": "one more thing"},
    ]


# --- provider failures: a terminal ErrorEvent instead of a dead stream ------------

_BUSY = "The assistant is busy right now - please try again in a moment."
_GENERIC = "Something went wrong generating the reply - please try again."


async def _collect(
    llm: FakeLlmClient,
) -> tuple[list[ChatStreamEvent], AsyncMock, AsyncMock, SimpleNamespace]:
    service, conversations, messages = _service(llm)
    conversation = SimpleNamespace(id=uuid.uuid4(), user_id=uuid.uuid4(), kind="chatbot")
    events = [
        e
        async for e in service.send_message(
            conversation=conversation,  # ty: ignore[invalid-argument-type]
            content="my secret question",
        )
    ]
    return events, messages, conversations, conversation


async def test_provider_failure_mid_stream_yields_a_terminal_error_event() -> None:
    events, messages, _conversations, conversation = await _collect(
        FailingLlmClient(overloaded_error(), chunks=["Par"])
    )

    assert [type(e).__name__ for e in events] == ["TokenEvent", "ErrorEvent"]
    error = events[1]
    assert error == ErrorEvent(message=_BUSY, conversation_id=conversation.id)
    # The partial reply is still persisted and still marked truncated -- a failed
    # stream persists exactly like a disconnect does.
    assert messages.create.await_count == 2
    _user_call, assistant_call = messages.create.await_args_list
    assert assistant_call.kwargs["content"] == "Par"
    # #81's provenance rides on the partial reply too, so a failed turn is as
    # attributable (model, prompt version) as a completed one.
    assert assistant_call.kwargs["metadata"] == {
        "truncated": True,
        "model": "fake-model",
        "prompt_version": prompt_version("chatbot"),
    }


async def test_in_stream_overload_on_the_200_gets_the_busy_wording() -> None:
    """The realistic mid-stream overload: the SDK raises a plain APIStatusError
    carrying the 200 that opened the stream, recognisable only by its `type`."""
    events, _, _, _ = await _collect(FailingLlmClient(in_stream_error(), chunks=["Par"]))

    assert isinstance(events[-1], ErrorEvent)
    assert events[-1].message == _BUSY


async def test_a_non_busy_in_stream_error_gets_the_generic_wording() -> None:
    events, _, _, _ = await _collect(
        FailingLlmClient(in_stream_error("invalid_request_error"), chunks=["Par"])
    )

    assert isinstance(events[-1], ErrorEvent)
    assert events[-1].message == _GENERIC


async def test_no_done_event_follows_a_failure() -> None:
    """A `done` frame after an `error` frame would tell the client the reply
    finished cleanly."""
    events, _, _, _ = await _collect(FailingLlmClient(RuntimeError("boom"), chunks=["Par"]))

    assert not any(isinstance(e, DoneEvent) for e in events)
    assert isinstance(events[-1], ErrorEvent)
    assert events[-1].message == _GENERIC


async def test_provider_failure_before_the_first_token_persists_no_assistant_turn() -> None:
    """The commonest real case: a 529 when the stream opens. Only the learner's
    turn is on record -- no empty or half assistant message."""
    events, messages, conversations, conversation = await _collect(
        FailingLlmClient(overloaded_error(), on_enter=True)
    )

    assert events == [ErrorEvent(message=_BUSY, conversation_id=conversation.id)]
    assert messages.create.await_count == 1
    assert messages.create.await_args.kwargs["role"] == "user"
    conversations.touch.assert_not_awaited()


async def test_a_connection_error_before_the_first_token_is_busy() -> None:
    events, _, _, _ = await _collect(FailingLlmClient(connection_error(), on_enter=True))

    assert [type(e).__name__ for e in events] == ["ErrorEvent"]
    assert isinstance(events[0], ErrorEvent)
    assert events[0].message == _BUSY


async def test_a_transient_failure_logs_a_warning_with_the_type_only(
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.WARNING, logger="src.services.chat_service"):
        await _collect(FailingLlmClient(in_stream_error(), chunks=["Par"]))

    [record] = caplog.records
    assert record.levelno == logging.WARNING
    assert "APIStatusError" in record.getMessage()
    assert record.exc_info is None
    assert "my secret question" not in caplog.text
    assert "Par" not in caplog.text


async def test_a_non_transient_failure_logs_an_error_with_the_traceback(
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.WARNING, logger="src.services.chat_service"):
        await _collect(
            FailingLlmClient(status_error(anthropic.AuthenticationError, 401), on_enter=True)
        )

    [record] = caplog.records
    assert record.levelno == logging.ERROR
    assert "provider, AuthenticationError" in record.getMessage()
    assert record.exc_info is not None
    assert "my secret question" not in caplog.text


async def test_a_bug_in_our_own_code_is_logged_as_unexpected(
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.WARNING, logger="src.services.chat_service"):
        await _collect(FailingLlmClient(RuntimeError("boom"), chunks=["Par"]))

    [record] = caplog.records
    assert record.levelno == logging.ERROR
    assert "unexpected, RuntimeError" in record.getMessage()
    assert record.exc_info is not None
