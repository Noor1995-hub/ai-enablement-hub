"""Wraps one real LlmClient for a single (case, rep) attempt: keeps every
complete_structured call's inputs, raw tool output (before the dash sanitiser) and
usage, in call order, so the runner (Task 4) can bill the attempt and write a full
trace even across a retried attempt."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from src.services.llm_service import LlmClient, LlmReplyStream, LlmUsage

__all__ = ["RecordingLlmClient"]


class RecordingLlmClient:
    def __init__(self, inner: LlmClient) -> None:
        self._inner = inner
        self.calls: list[dict[str, Any]] = []

    @property
    def model(self) -> str:
        return self._inner.model

    def stream_reply(self, **kwargs: Any) -> LlmReplyStream:
        # Unused by `run` (the frozen transcript already ends at the offer); kept so this
        # class satisfies LlmClient for simulate.py, which does use it.
        return self._inner.stream_reply(**kwargs)

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
