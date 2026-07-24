from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from anthropic import AsyncAnthropic

__all__ = ["AnthropicLlmClient", "LlmClient", "LlmReplyStream", "LlmUsage"]


@dataclass(frozen=True)
class LlmUsage:
    input_tokens: int
    output_tokens: int


class LlmReplyStream(Protocol):
    """Async-iterate for text deltas; call `usage()` only after the iterator is
    fully exhausted (mirrors AsyncAnthropic's `stream.get_final_message()`)."""

    async def __aenter__(self) -> LlmReplyStream: ...
    async def __aexit__(self, *exc: object) -> None: ...
    def __aiter__(self) -> AsyncIterator[str]: ...
    async def usage(self) -> LlmUsage: ...


class LlmClient(Protocol):
    """The seam: tests stub this, `AnthropicLlmClient` is the only real
    implementation for now (see docs/ai-agents-plan.md §7 for the provider
    decision and the Foundry-adapter option kept open by this Protocol)."""

    def stream_reply(
        self, *, system: str, messages: list[dict[str, str]], max_tokens: int
    ) -> LlmReplyStream: ...


class _AnthropicReplyStream:
    """Adapts anthropic's `client.messages.stream(...)` async-context-manager
    (`.text_stream` / `.get_final_message()`) to the `LlmReplyStream` shape."""

    def __init__(self, manager: object) -> None:
        self._manager = manager
        self._stream: object | None = None

    async def __aenter__(self) -> _AnthropicReplyStream:
        self._stream = await self._manager.__aenter__()  # type: ignore[attr-defined]
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self._manager.__aexit__(*exc)  # type: ignore[attr-defined]

    async def __aiter__(self) -> AsyncIterator[str]:
        assert self._stream is not None
        async for chunk in self._stream.text_stream:  # type: ignore[attr-defined]
            yield chunk

    async def usage(self) -> LlmUsage:
        assert self._stream is not None
        final = await self._stream.get_final_message()  # type: ignore[attr-defined]
        return LlmUsage(final.usage.input_tokens, final.usage.output_tokens)


class AnthropicLlmClient:
    """Thin wrapper over `AsyncAnthropic` — mirrors how EmailService wraps ACS."""

    def __init__(self, client: AsyncAnthropic, *, model: str) -> None:
        self._client = client
        self._model = model

    def stream_reply(
        self, *, system: str, messages: list[dict[str, str]], max_tokens: int
    ) -> _AnthropicReplyStream:
        manager = self._client.messages.stream(
            model=self._model, max_tokens=max_tokens, system=system, messages=messages
        )
        return _AnthropicReplyStream(manager)
