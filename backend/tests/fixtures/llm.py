"""LLM test doubles: a FakeLlmClient mirroring tests/fixtures/email.py's
RecordingSender/RaisingSender pattern, plus a fake shaped like AsyncAnthropic's
`messages.stream(...)` for testing the adapter itself."""

from __future__ import annotations

from collections.abc import AsyncIterator
from types import TracebackType

from src.services.llm_service import LlmUsage

__all__ = [
    "FakeAnthropicMessage",
    "FakeAnthropicStream",
    "FakeAnthropicStreamManager",
    "FakeAnthropicToolMessage",
    "FakeLlmClient",
    "FakeStructuredAsyncAnthropic",
    "FakeToolUseBlock",
    "RaisingLlmClient",
]


class FakeAnthropicMessage:
    def __init__(self, input_tokens: int, output_tokens: int) -> None:
        self.usage = type(
            "Usage", (), {"input_tokens": input_tokens, "output_tokens": output_tokens}
        )()


class FakeAnthropicStream:
    """Shaped like anthropic's MessageStream: `.text_stream` + `.get_final_message()`."""

    def __init__(self, chunks: list[str], usage: tuple[int, int]) -> None:
        self._chunks = chunks
        self._usage = usage

    @property
    async def text_stream(self) -> AsyncIterator[str]:
        for chunk in self._chunks:
            yield chunk

    async def get_final_message(self) -> FakeAnthropicMessage:
        return FakeAnthropicMessage(*self._usage)


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

    def stream(self, **_: object) -> FakeAnthropicStreamManager:
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

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        return None

    async def __aiter__(self) -> AsyncIterator[str]:
        for chunk in self._chunks:
            yield chunk

    async def usage(self) -> LlmUsage:
        return self._usage


class FakeLlmClient:
    """Stubs LlmClient: streams canned chunks, reports canned usage."""

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


class RaisingLlmClient:
    """Every call blows up (dead Anthropic endpoint, bad key, ...)."""

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
    def __init__(self, tool_input: dict[str, object], usage: tuple[int, int]) -> None:
        self.content = [FakeToolUseBlock(tool_input)]
        self.usage = type("Usage", (), {"input_tokens": usage[0], "output_tokens": usage[1]})()


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
