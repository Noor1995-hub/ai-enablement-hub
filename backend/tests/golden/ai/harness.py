"""Golden cases for the AI features: pin exactly what each feature sends the model.

Drive the real service with RecordingLlm, then assert_golden(name, llm.calls). The snapshot is
a readable text rendering (a prompt edit shows up as a line diff in the PR). Regenerate locally
with UPDATE_GOLDEN=1 and READ THE DIFF; CI never regenerates.
"""

from __future__ import annotations

import difflib
import json
import os
from pathlib import Path
from typing import Any

from src.services.llm_service import LlmUsage, StructuredSchema
from tests.fixtures.llm import FakeLlmReplyStream

__all__ = ["RecordingLlm", "SNAPSHOT_DIR", "assert_golden", "render_calls"]

SNAPSHOT_DIR = Path(__file__).resolve().parent / "snapshots"
_USAGE = LlmUsage(input_tokens=10, output_tokens=5)


class RecordingLlm:
    """An LlmClient that records every call and returns canned output."""

    model = "fake-model"

    def __init__(
        self,
        structured_results: list[dict[str, Any]] | None = None,
        chunks: list[str] | None = None,
    ) -> None:
        self._structured = list(structured_results or [])
        self._chunks = chunks if chunks is not None else ["ok"]
        self.calls: list[dict[str, Any]] = []

    def stream_reply(
        self, *, system: str, messages: list[dict[str, str]], max_tokens: int
    ) -> FakeLlmReplyStream:
        self.calls.append(
            {
                "method": "stream_reply",
                "system": system,
                "messages": [dict(m) for m in messages],
                "max_tokens": max_tokens,
            }
        )
        return FakeLlmReplyStream(self._chunks, _USAGE)

    async def complete_structured(
        self, *, system: str, prompt: str, schema: StructuredSchema, max_tokens: int
    ) -> tuple[dict[str, Any], LlmUsage]:
        self.calls.append(
            {
                "method": "complete_structured",
                "system": system,
                "prompt": prompt,
                "schema": {
                    "name": schema.name,
                    "description": schema.description,
                    "input_schema": schema.input_schema,
                },
                "max_tokens": max_tokens,
            }
        )
        result = self._structured.pop(0) if self._structured else {}
        return dict(result), _USAGE


def render_calls(calls: list[dict[str, Any]]) -> str:
    out: list[str] = []
    for i, call in enumerate(calls, start=1):
        out.append(f"=== call {i}: {call['method']} (max_tokens={call['max_tokens']}) ===")
        out.append("--- system ---")
        out.append(call["system"])
        if call["method"] == "stream_reply":
            for j, m in enumerate(call["messages"], start=1):
                out.append(f"--- message {j} ({m['role']}) ---")
                out.append(m["content"])
        else:
            out.append("--- prompt ---")
            out.append(call["prompt"])
            s = call["schema"]
            out.append(f"--- schema {s['name']}: {s['description']} ---")
            out.append(json.dumps(s["input_schema"], indent=2, sort_keys=True, ensure_ascii=False))
        out.append("")
    return "\n".join(out) + "\n"


def assert_golden(name: str, calls: list[dict[str, Any]]) -> None:
    path = SNAPSHOT_DIR / f"{name}.golden.txt"
    actual = render_calls(calls)
    if os.environ.get("UPDATE_GOLDEN") == "1" and not os.environ.get("CI"):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(actual, encoding="utf-8", newline="\n")
        return
    if not path.exists():
        raise AssertionError(
            f"No golden snapshot {path.name}. Generate it locally with "
            "UPDATE_GOLDEN=1 uv run pytest tests/golden/ai (run from backend/) and read it "
            "before committing."
        )
    expected = path.read_text(encoding="utf-8")
    if actual != expected:
        diff = "".join(
            difflib.unified_diff(
                expected.splitlines(keepends=True),
                actual.splitlines(keepends=True),
                fromfile=f"{path.name} (committed)",
                tofile=f"{path.name} (now)",
            )
        )
        raise AssertionError(
            f"What the {name!r} feature sends the model changed:\n{diff}\n"
            "If intended, regenerate with UPDATE_GOLDEN=1 and commit the snapshot with the change."
        )
