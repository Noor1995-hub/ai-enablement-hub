from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Final, Protocol

import anthropic

if TYPE_CHECKING:
    from anthropic import AsyncAnthropic

__all__ = [
    "THINKING_MODE",
    "AnthropicLlmClient",
    "LlmClient",
    "LlmError",
    "LlmReplyStream",
    "LlmUsage",
    "StructuredSchema",
    "is_transient_provider_error",
]

# The provider saying "not now" -- capacity, throttling, or a network blip.
# Every one of these has the same right answer: try the same request again
# later. Kept next to AnthropicLlmClient rather than in a caller because these
# are provider-specific types, and LlmClient exists so a second provider can be
# adapted here without callers learning its exception hierarchy.
_TRANSIENT_PROVIDER_ERRORS = (
    anthropic.OverloadedError,  # 529
    anthropic.RateLimitError,  # 429
    anthropic.InternalServerError,  # 5xx
    anthropic.APIConnectionError,  # never reached the API
)


class LlmError(RuntimeError):
    """Raised when the LLM response is missing an expected structured result."""


def is_transient_provider_error(exc: BaseException) -> bool:
    """True when retrying the identical request could plausibly succeed.

    Deliberately narrow. `LlmError` is ours and always means the request itself
    is unusable (over the char ceiling, no tool_use block, an empty summary), a
    `TimeoutError` usually means this particular input is too slow rather than
    the provider being busy, and an unrecognised exception is not something to
    retry on optimistically -- a caller that re-queues work on every unknown
    failure re-consumes every future run forever.
    """
    return isinstance(exc, _TRANSIENT_PROVIDER_ERRORS)


@dataclass(frozen=True)
class LlmUsage:
    input_tokens: int
    output_tokens: int
    # Filled by AnthropicLlmClient from the API response (both calls). Additive: every
    # existing caller and stored metadata shape is unchanged (spec 2026-09-27 §4.3).
    model: str | None = None
    stop_reason: str | None = None


@dataclass(frozen=True)
class StructuredSchema:
    """A forced-tool_use definition: the tool name, its description, and the
    JSON Schema the model must fill. The returned dict matches input_schema."""

    name: str
    description: str
    input_schema: dict[str, Any]


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

    @property
    def model(self) -> str: ...

    def stream_reply(
        self, *, system: str, messages: list[dict[str, str]], max_tokens: int
    ) -> LlmReplyStream: ...

    async def complete_structured(
        self, *, system: str, prompt: str, schema: StructuredSchema, max_tokens: int
    ) -> tuple[dict[str, Any], LlmUsage]: ...


class _AnthropicReplyStream:
    """Adapts anthropic's `client.messages.stream(...)` async-context-manager
    (`.text_stream` / `.get_final_message()`) to the `LlmReplyStream` shape."""

    def __init__(self, manager: object) -> None:
        self._manager = manager
        self._stream: object | None = None

    async def __aenter__(self) -> _AnthropicReplyStream:
        self._stream = await self._manager.__aenter__()  # ty: ignore[unresolved-attribute]
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self._manager.__aexit__(*exc)  # ty: ignore[unresolved-attribute]

    async def __aiter__(self) -> AsyncIterator[str]:
        assert self._stream is not None
        async for chunk in self._stream.text_stream:  # ty: ignore[unresolved-attribute]
            yield chunk

    async def usage(self) -> LlmUsage:
        assert self._stream is not None
        final = await self._stream.get_final_message()  # ty: ignore[unresolved-attribute]
        return LlmUsage(
            final.usage.input_tokens,
            final.usage.output_tokens,
            model=final.model,
            stop_reason=final.stop_reason,
        )


# What both calls below send as `thinking`. Recorded in run metadata (spec 2026-09-26 A.1).
THINKING_MODE: Final = "disabled"


class AnthropicLlmClient:
    """Thin wrapper over `AsyncAnthropic` — mirrors how EmailService wraps ACS.

    Both calls disable thinking explicitly. From Sonnet 5 onward a request that
    omits the field thinks by default, and `max_tokens` caps thinking *plus*
    visible output — which the callers' budgets (300 for feedback triage, 1024
    for chat) cannot absorb. Raise the caller's budget before turning it back on.
    """

    def __init__(self, client: AsyncAnthropic, *, model: str) -> None:
        self._client = client
        self._model = model

    @property
    def model(self) -> str:
        return self._model

    def stream_reply(
        self, *, system: str, messages: list[dict[str, str]], max_tokens: int
    ) -> _AnthropicReplyStream:
        manager = self._client.messages.stream(
            model=self._model,
            max_tokens=max_tokens,
            thinking={"type": THINKING_MODE},
            system=system,
            messages=messages,  # ty: ignore[invalid-argument-type]
        )
        return _AnthropicReplyStream(manager)

    async def complete_structured(
        self, *, system: str, prompt: str, schema: StructuredSchema, max_tokens: int
    ) -> tuple[dict[str, Any], LlmUsage]:
        message = await self._client.messages.create(
            model=self._model,
            max_tokens=max_tokens,
            thinking={"type": THINKING_MODE},
            system=system,
            messages=[{"role": "user", "content": prompt}],
            tools=[
                {
                    "name": schema.name,
                    "description": schema.description,
                    "input_schema": schema.input_schema,
                }
            ],
            tool_choice={"type": "tool", "name": schema.name},
        )
        usage = LlmUsage(
            message.usage.input_tokens,
            message.usage.output_tokens,
            model=message.model,
            stop_reason=message.stop_reason,
        )
        for block in message.content:
            if block.type == "tool_use":
                return dict(block.input), usage
        msg = "model returned no tool_use block"
        raise LlmError(msg)
