from __future__ import annotations

import anthropic
import httpx2

from src.services.llm_service import (
    THINKING_MODE,
    AnthropicLlmClient,
    LlmError,
    StructuredSchema,
    is_provider_error,
    is_transient_provider_error,
)
from tests.fixtures.llm import (
    FakeAsyncAnthropic,
    FakeStructuredAsyncAnthropic,
    overloaded_error,
    status_error,
)


async def test_anthropic_client_streams_chunks_and_reports_usage() -> None:
    fake_sdk = FakeAsyncAnthropic(chunks=["Hel", "lo!"], usage=(12, 3))
    client = AnthropicLlmClient(
        fake_sdk,  # ty: ignore[invalid-argument-type]
        model="claude-haiku-4-5",
    )

    collected: list[str] = []
    async with client.stream_reply(
        system="You are helpful.", messages=[{"role": "user", "content": "hi"}], max_tokens=1024
    ) as reply:
        async for chunk in reply:
            collected.append(chunk)
        usage = await reply.usage()

    assert collected == ["Hel", "lo!"]
    assert usage.input_tokens == 12
    assert usage.output_tokens == 3


async def test_anthropic_client_complete_structured_returns_tool_input_and_usage() -> None:
    fake_sdk = FakeStructuredAsyncAnthropic(
        tool_input={"suggested_status": "accepted", "rationale": "actionable"},
        usage=(20, 8),
    )
    client = AnthropicLlmClient(
        fake_sdk,  # ty: ignore[invalid-argument-type]
        model="claude-haiku-4-5",
    )
    schema = StructuredSchema(
        name="triage",
        description="Suggest a triage disposition.",
        input_schema={
            "type": "object",
            "properties": {
                "suggested_status": {"type": "string", "enum": ["accepted", "dismissed"]},
                "rationale": {"type": "string"},
            },
            "required": ["suggested_status", "rationale"],
            "additionalProperties": False,
        },
    )

    result, usage = await client.complete_structured(
        system="You triage feedback.",
        prompt="Feedback: the examples were unclear.",
        schema=schema,
        max_tokens=512,
    )

    assert result == {"suggested_status": "accepted", "rationale": "actionable"}
    assert usage.input_tokens == 20
    assert usage.output_tokens == 8
    # forced tool_use wired with the schema's tool name + the client's model
    call = fake_sdk.messages.calls[0]
    assert call["tool_choice"] == {"type": "tool", "name": "triage"}
    assert call["model"] == "claude-haiku-4-5"
    assert call["tools"][0]["name"] == "triage"  # ty: ignore[not-subscriptable]


class TestTransientProviderErrors:
    """`is_transient_provider_error` decides whether a failed drafting call gets
    a `failed` proposal (terminal) or stays queued for the next run (transient).
    Getting it wrong is expensive in both directions: a transient error recorded
    as terminal makes the admin dismiss cards by hand, and a terminal error
    treated as transient re-consumes every future run forever."""

    def test_an_overloaded_error_is_transient(self) -> None:
        assert is_transient_provider_error(overloaded_error()) is True

    def test_a_rate_limit_error_is_transient(self) -> None:
        assert is_transient_provider_error(status_error(anthropic.RateLimitError, 429)) is True

    def test_a_server_error_is_transient(self) -> None:
        assert is_transient_provider_error(status_error(anthropic.InternalServerError, 500)) is True

    def test_a_connection_error_is_transient(self) -> None:
        exc = anthropic.APIConnectionError(request=httpx2.Request("POST", "https://x/y"))
        assert is_transient_provider_error(exc) is True

    def test_our_own_llm_error_is_terminal(self) -> None:
        # Raised for the char ceiling, an empty summary, and validator rejection
        # -- re-running cannot change any of those.
        assert is_transient_provider_error(LlmError("lesson content is 60000 characters")) is False

    def test_a_timeout_is_terminal(self) -> None:
        # A lesson that consistently exceeds the per-lesson timeout would eat the
        # whole run budget on every future run if it stayed queued.
        assert is_transient_provider_error(TimeoutError()) is False

    def test_a_bad_request_is_terminal(self) -> None:
        assert is_transient_provider_error(status_error(anthropic.BadRequestError, 400)) is False

    def test_an_unknown_error_is_terminal(self) -> None:
        assert is_transient_provider_error(RuntimeError("something else")) is False


class TestProviderErrors:
    """`is_provider_error` separates "the provider call failed" (a 502 for the caller)
    from a bug in our own code (a 500)."""

    def test_transient_and_terminal_sdk_errors_are_provider_errors(self) -> None:
        assert is_provider_error(overloaded_error()) is True
        assert is_provider_error(status_error(anthropic.AuthenticationError, 401)) is True
        assert is_provider_error(status_error(anthropic.BadRequestError, 400)) is True
        exc = anthropic.APIConnectionError(request=httpx2.Request("POST", "https://x/y"))
        assert is_provider_error(exc) is True

    def test_our_own_errors_and_bugs_are_not(self) -> None:
        assert is_provider_error(LlmError("no tool_use block")) is False
        assert is_provider_error(TimeoutError()) is False
        assert is_provider_error(RuntimeError("bug")) is False


def test_anthropic_client_exposes_its_model() -> None:
    client = AnthropicLlmClient(
        FakeAsyncAnthropic(chunks=[]),  # ty: ignore[invalid-argument-type]
        model="claude-sonnet-5",
    )
    assert client.model == "claude-sonnet-5"


async def test_stream_reply_sends_the_recorded_thinking_mode() -> None:
    """Guards THINKING_MODE against drifting from what's actually sent: if a future edit
    changes one without the other, this catches it (see llm_service.THINKING_MODE)."""
    fake_sdk = FakeAsyncAnthropic(chunks=[])
    client = AnthropicLlmClient(
        fake_sdk,  # ty: ignore[invalid-argument-type]
        model="claude-sonnet-5",
    )

    async with client.stream_reply(
        system="You are helpful.", messages=[{"role": "user", "content": "hi"}], max_tokens=1024
    ) as reply:
        async for _ in reply:
            pass

    call = fake_sdk.messages.calls[0]
    assert call["thinking"] == {"type": THINKING_MODE}


async def test_anthropic_client_records_the_served_model_and_stop_reason_from_streaming() -> None:
    fake_sdk = FakeAsyncAnthropic(chunks=["hi"], usage=(1, 1))
    client = AnthropicLlmClient(fake_sdk, model="claude-sonnet-5")  # ty: ignore[invalid-argument-type]

    async with client.stream_reply(
        system="s", messages=[{"role": "user", "content": "hi"}], max_tokens=10
    ) as reply:
        async for _ in reply:
            pass
        usage = await reply.usage()

    assert usage.model == "fake-served-model"
    assert usage.stop_reason == "end_turn"


async def test_anthropic_client_records_the_served_model_and_stop_reason_from_structured() -> None:
    fake_sdk = FakeStructuredAsyncAnthropic(tool_input={"a": "b"})
    client = AnthropicLlmClient(
        fake_sdk,  # ty: ignore[invalid-argument-type]
        model="claude-sonnet-5",
    )
    schema = StructuredSchema(
        name="t", description="d", input_schema={"type": "object", "properties": {}}
    )

    _, usage = await client.complete_structured(
        system="s", prompt="p", schema=schema, max_tokens=10
    )

    assert usage.model == "fake-served-model"
    assert usage.stop_reason == "end_turn"


async def test_complete_structured_sends_the_recorded_thinking_mode() -> None:
    fake_sdk = FakeStructuredAsyncAnthropic(tool_input={"a": "b"})
    client = AnthropicLlmClient(
        fake_sdk,  # ty: ignore[invalid-argument-type]
        model="claude-sonnet-5",
    )
    schema = StructuredSchema(
        name="triage",
        description="Suggest a triage disposition.",
        input_schema={"type": "object", "properties": {}},
    )

    await client.complete_structured(
        system="You triage feedback.", prompt="Feedback: unclear.", schema=schema, max_tokens=512
    )

    call = fake_sdk.messages.calls[0]
    assert call["thinking"] == {"type": THINKING_MODE}
