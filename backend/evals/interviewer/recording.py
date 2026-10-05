"""Wraps one real LlmClient for a single (case, rep) attempt: keeps every call's inputs, raw
output (before the dash sanitiser) and usage, in call order, so the runner (Task 4) can bill
the attempt and write a full trace even across a retried attempt. Since #149 the playbook is a
streamed tagged document, so streamed calls are recorded too, with the text as raw_output."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from src.services.llm_service import LlmClient, LlmReplyStream, LlmUsage

__all__ = ["RawTextRecordingLlmClient", "RecordingLlmClient", "UsageCapturingLlmClient"]


class RecordingLlmClient:
    def __init__(self, inner: LlmClient) -> None:
        self._inner = inner
        self.calls: list[dict[str, Any]] = []

    @property
    def model(self) -> str:
        return self._inner.model

    def stream_reply(
        self, *, system: str, messages: list[dict[str, str]], max_tokens: int
    ) -> LlmReplyStream:
        # The playbook is a streamed tagged document since #149: record it like a structured
        # call, with the full text as raw_output.
        inner = self._inner.stream_reply(system=system, messages=messages, max_tokens=max_tokens)
        prompt = messages[-1]["content"] if messages else ""
        return _RecordingReplyStream(inner, self.calls, system=system, prompt=prompt)

    async def complete_structured(
        self, *, system: str, prompt: str, schema: Any, max_tokens: int
    ) -> tuple[dict[str, Any], LlmUsage]:
        result, usage = await self._inner.complete_structured(
            system=system, prompt=prompt, schema=schema, max_tokens=max_tokens
        )
        self.calls.append(
            {"system": system, "prompt": prompt, "raw_output": result, "usage": usage}
        )
        return result, usage


class _RecordingReplyStream:
    """Wraps one stream so the call lands in `calls` once its text is fully read: the text
    as raw_output, and the usage (read from the inner stream at the end of the iterator)."""

    def __init__(
        self, inner: LlmReplyStream, calls: list[dict[str, Any]], *, system: str, prompt: str
    ) -> None:
        self._inner = inner
        self._calls = calls
        self._system = system
        self._prompt = prompt
        self._usage: LlmUsage | None = None

    async def __aenter__(self) -> _RecordingReplyStream:
        await self._inner.__aenter__()
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self._inner.__aexit__(*exc)

    async def __aiter__(self) -> AsyncIterator[str]:
        chunks: list[str] = []
        async for chunk in self._inner:
            chunks.append(chunk)
            yield chunk
        self._usage = await self._inner.usage()
        self._calls.append(
            {
                "system": self._system,
                "prompt": self._prompt,
                "raw_output": "".join(chunks),
                "usage": self._usage,
            }
        )

    async def usage(self) -> LlmUsage:
        if self._usage is None:
            self._usage = await self._inner.usage()
        return self._usage


class _UsageCapturingReplyStream:
    """Wraps one `stream_reply` call's `LlmReplyStream` so its usage lands in `sink`
    exactly once, whether or not the caller itself calls `.usage()` - `InterviewService.
    open_interview` never does (it only reads the streamed text), while `ChatService.
    send_message` and this package's own `_learner_reply` both do. Reads usage as soon as
    the iterator is fully exhausted, matching the `LlmReplyStream` contract ("call usage()
    only after the iterator is fully exhausted")."""

    def __init__(self, inner: LlmReplyStream, sink: list[LlmUsage]) -> None:
        self._inner = inner
        self._sink = sink
        self._captured: LlmUsage | None = None

    async def __aenter__(self) -> _UsageCapturingReplyStream:
        await self._inner.__aenter__()
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self._inner.__aexit__(*exc)

    async def __aiter__(self) -> AsyncIterator[str]:
        async for chunk in self._inner:
            yield chunk
        await self._ensure_captured()

    async def usage(self) -> LlmUsage:
        return await self._ensure_captured()

    async def _ensure_captured(self) -> LlmUsage:
        if self._captured is None:
            self._captured = await self._inner.usage()
            self._sink.append(self._captured)
        return self._captured


class UsageCapturingLlmClient:
    """Wraps a real LlmClient so every `stream_reply` call's usage lands in `usages`, in
    call order - used by `simulate --variant` to cost a simulation (spec 2026-09-28): both
    the interviewer's calls (InterviewService.open_interview, ChatService.send_message)
    and the persona's own calls (`simulate._learner_reply`) go through this, so a single
    shared `usages` list on both wrappers captures the full cost of one simulation."""

    def __init__(self, inner: LlmClient, usages: list[LlmUsage]) -> None:
        self._inner = inner
        self.usages = usages

    @property
    def model(self) -> str:
        return self._inner.model

    def stream_reply(self, **kwargs: Any) -> _UsageCapturingReplyStream:
        return _UsageCapturingReplyStream(self._inner.stream_reply(**kwargs), self.usages)

    async def complete_structured(
        self, *, system: str, prompt: str, schema: Any, max_tokens: int
    ) -> tuple[dict[str, Any], LlmUsage]:
        return await self._inner.complete_structured(
            system=system, prompt=prompt, schema=schema, max_tokens=max_tokens
        )


class _RawTextReplyStream:
    """Passes every chunk through untouched and, once the stream is exhausted, appends
    the whole raw reply to `sink`."""

    def __init__(self, inner: LlmReplyStream, sink: list[str]) -> None:
        self._inner = inner
        self._sink = sink

    async def __aenter__(self) -> _RawTextReplyStream:
        await self._inner.__aenter__()
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self._inner.__aexit__(*exc)

    async def __aiter__(self) -> AsyncIterator[str]:
        chunks: list[str] = []
        async for chunk in self._inner:
            chunks.append(chunk)
            yield chunk
        self._sink.append("".join(chunks))

    async def usage(self) -> LlmUsage:
        return await self._inner.usage()


class RawTextRecordingLlmClient:
    """Keeps the interviewer's raw reply for every `stream_reply` call, in call order,
    before the hub's hard stop (#96) cuts anything, so `simulate` can show a reviewer
    exactly what each cut removed."""

    def __init__(self, inner: LlmClient) -> None:
        self._inner = inner
        self.texts: list[str] = []

    @property
    def model(self) -> str:
        return self._inner.model

    def stream_reply(self, **kwargs: Any) -> _RawTextReplyStream:
        return _RawTextReplyStream(self._inner.stream_reply(**kwargs), self.texts)

    async def complete_structured(
        self, *, system: str, prompt: str, schema: Any, max_tokens: int
    ) -> tuple[dict[str, Any], LlmUsage]:
        return await self._inner.complete_structured(
            system=system, prompt=prompt, schema=schema, max_tokens=max_tokens
        )
