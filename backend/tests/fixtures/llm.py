"""LLM test doubles: a FakeLlmClient mirroring tests/fixtures/email.py's
RecordingSender/RaisingSender pattern, plus a fake shaped like AsyncAnthropic's
`messages.stream(...)` for testing the adapter itself."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

import anthropic
import httpx2

from src.services.llm_service import LlmUsage

__all__ = [
    "FakeAnthropicMessage",
    "FakeAnthropicStream",
    "FakeAnthropicStreamManager",
    "FakeAnthropicToolMessage",
    "FailingLlmClient",
    "FakeLlmClient",
    "FakeStructuredAsyncAnthropic",
    "FakeToolUseBlock",
    "RaisingLlmClient",
    "connection_error",
    "in_stream_error",
    "overloaded_error",
    "status_error",
]


def status_error(cls: Any, status: int) -> Exception:
    """A real anthropic status error, built the way the SDK builds one
    (anthropic 1.8.0 is on httpx2, not httpx — see `llm_service.py`'s
    `_TRANSIENT_PROVIDER_ERRORS` and `test_llm_service.py`)."""
    request = httpx2.Request("POST", "https://api.anthropic.com/v1/messages")
    return cls("boom", response=httpx2.Response(status, request=request), body=None)


def overloaded_error() -> Exception:
    """The 529 a run actually hits when Anthropic is at capacity."""
    return status_error(anthropic.OverloadedError, 529)


def in_stream_error(error_type: str = "overloaded_error") -> Exception:
    """What the SDK raises when the provider fails AFTER the stream started:
    anthropic 1.8 `_streaming.py` turns an in-stream `event: error` into
    `_make_status_error(response=self.response)`, and that response is the 200
    that opened the stream -- so it is a plain `APIStatusError` (not
    `OverloadedError`) whose only busy signal is `.type`."""
    request = httpx2.Request("POST", "https://api.anthropic.com/v1/messages")
    body = {"type": "error", "error": {"type": error_type, "message": "Overloaded"}}
    return anthropic.APIStatusError(
        str(body), response=httpx2.Response(200, request=request), body=body
    )


def connection_error() -> Exception:
    """A transport failure that never reached the API (dropped connection,
    DNS, TLS, ...)."""
    request = httpx2.Request("POST", "https://api.anthropic.com/v1/messages")
    return anthropic.APIConnectionError(request=request)


class FakeAnthropicMessage:
    def __init__(
        self,
        input_tokens: int,
        output_tokens: int,
        *,
        model: str = "fake-served-model",
        stop_reason: str = "end_turn",
    ) -> None:
        self.usage = type(
            "Usage", (), {"input_tokens": input_tokens, "output_tokens": output_tokens}
        )()
        self.model = model
        self.stop_reason = stop_reason


class FakeAnthropicStream:
    """Shaped like anthropic's MessageStream: `.text_stream` + `.get_final_message()`."""

    def __init__(
        self,
        chunks: list[str],
        usage: tuple[int, int],
        *,
        model: str = "fake-served-model",
        stop_reason: str = "end_turn",
    ) -> None:
        self._chunks = chunks
        self._usage = usage
        self._model = model
        self._stop_reason = stop_reason

    @property
    async def text_stream(self) -> AsyncIterator[str]:
        for chunk in self._chunks:
            yield chunk

    async def get_final_message(self) -> FakeAnthropicMessage:
        return FakeAnthropicMessage(*self._usage, model=self._model, stop_reason=self._stop_reason)


class FakeAnthropicStreamManager:
    """Shaped like `client.messages.stream(...)`'s return value: an async context
    manager that yields a FakeAnthropicStream."""

    def __init__(self, chunks: list[str], usage: tuple[int, int]) -> None:
        self._stream = FakeAnthropicStream(chunks, usage)

    async def __aenter__(self) -> FakeAnthropicStream:
        return self._stream

    async def __aexit__(self, *exc: object) -> None:
        return None


class _FakeMessages:
    def __init__(self, chunks: list[str], usage: tuple[int, int]) -> None:
        self._chunks = chunks
        self._usage = usage
        self.calls: list[dict[str, object]] = []

    def stream(self, **kwargs: object) -> FakeAnthropicStreamManager:
        self.calls.append(kwargs)
        return FakeAnthropicStreamManager(self._chunks, self._usage)


class FakeAsyncAnthropic:
    """A fake shaped exactly like `AsyncAnthropic` for `AnthropicLlmClient` tests."""

    def __init__(self, chunks: list[str], usage: tuple[int, int] = (10, 5)) -> None:
        self.messages = _FakeMessages(chunks, usage)


class FakeLlmReplyStream:
    def __init__(self, chunks: list[str], usage: LlmUsage) -> None:
        self._chunks = chunks
        self._usage = usage

    async def __aenter__(self) -> FakeLlmReplyStream:
        return self

    async def __aexit__(self, *exc: object) -> None:
        return None

    async def __aiter__(self) -> AsyncIterator[str]:
        for chunk in self._chunks:
            yield chunk

    async def usage(self) -> LlmUsage:
        return self._usage


class FakeLlmClient:
    """Stubs LlmClient: streams canned chunks, reports canned usage."""

    model = "fake-model"

    def __init__(
        self,
        chunks: list[str],
        usage: LlmUsage | None = None,
        structured: dict[str, object] | None = None,
    ) -> None:
        self.chunks = chunks
        self.usage_value = usage or LlmUsage(input_tokens=10, output_tokens=len(chunks))
        self.calls: list[dict[str, object]] = []
        self.structured = structured or {}
        self.structured_calls: list[dict[str, object]] = []

    def stream_reply(
        self, *, system: str, messages: list[dict[str, str]], max_tokens: int
    ) -> FakeLlmReplyStream:
        self.calls.append({"system": system, "messages": messages, "max_tokens": max_tokens})
        return FakeLlmReplyStream(self.chunks, self.usage_value)

    async def complete_structured(
        self, *, system: str, prompt: str, schema: object, max_tokens: int
    ) -> tuple[dict[str, object], LlmUsage]:
        self.structured_calls.append(
            {"system": system, "prompt": prompt, "schema": schema, "max_tokens": max_tokens}
        )
        return dict(self.structured), self.usage_value


class FailingLlmReplyStream(FakeLlmReplyStream):
    """Streams `chunks`, then raises `exc` -- or raises it on `__aenter__`
    (before any token) when `on_enter` is set, which is where a 529 lands."""

    def __init__(self, chunks: list[str], exc: BaseException, *, on_enter: bool) -> None:
        super().__init__(chunks, LlmUsage(input_tokens=0, output_tokens=0))
        self._exc = exc
        self._on_enter = on_enter

    async def __aenter__(self) -> FailingLlmReplyStream:
        if self._on_enter:
            raise self._exc
        return self

    async def __aiter__(self) -> AsyncIterator[str]:
        for chunk in self._chunks:
            yield chunk
        raise self._exc


class FailingLlmClient(FakeLlmClient):
    """A FakeLlmClient whose stream falls over: after `chunks` (mid-stream), or
    before the first token with `on_enter=True`. Subclasses FakeLlmClient so it
    drops into every helper typed for one."""

    def __init__(
        self, exc: BaseException, chunks: list[str] | None = None, *, on_enter: bool = False
    ) -> None:
        super().__init__(chunks=chunks or [])
        self.exc = exc
        self.on_enter = on_enter

    def stream_reply(
        self, *, system: str, messages: list[dict[str, str]], max_tokens: int
    ) -> FailingLlmReplyStream:
        self.calls.append({"system": system, "messages": messages, "max_tokens": max_tokens})
        return FailingLlmReplyStream(self.chunks, self.exc, on_enter=self.on_enter)


class RaisingLlmClient:
    """Every call blows up (dead Anthropic endpoint, bad key, ...)."""

    model = "fake-model"

    def stream_reply(self, **_: object) -> FakeLlmReplyStream:
        msg = "Anthropic API unreachable"
        raise RuntimeError(msg)

    async def complete_structured(self, **_: object) -> tuple[dict[str, object], LlmUsage]:
        msg = "Anthropic API unreachable"
        raise RuntimeError(msg)


class FakeToolUseBlock:
    def __init__(self, tool_input: dict[str, object]) -> None:
        self.type = "tool_use"
        self.input = tool_input


class FakeAnthropicToolMessage:
    def __init__(
        self,
        tool_input: dict[str, object],
        usage: tuple[int, int],
        *,
        model: str = "fake-served-model",
        stop_reason: str = "end_turn",
    ) -> None:
        self.content = [FakeToolUseBlock(tool_input)]
        self.usage = type("Usage", (), {"input_tokens": usage[0], "output_tokens": usage[1]})()
        self.model = model
        self.stop_reason = stop_reason


class _FakeStructuredMessages:
    def __init__(self, tool_input: dict[str, object], usage: tuple[int, int]) -> None:
        self._tool_input = tool_input
        self._usage = usage
        self.calls: list[dict[str, object]] = []

    async def create(self, **kwargs: object) -> FakeAnthropicToolMessage:
        self.calls.append(kwargs)
        return FakeAnthropicToolMessage(self._tool_input, self._usage)


class FakeStructuredAsyncAnthropic:
    """Shaped like `AsyncAnthropic` for `AnthropicLlmClient.complete_structured`."""

    def __init__(self, tool_input: dict[str, object], usage: tuple[int, int] = (20, 8)) -> None:
        self.messages = _FakeStructuredMessages(tool_input, usage)
