# Feedback-Driven Content Improvement — Plan A: AI Content Plumbing

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the two shared, provider-blind primitives the feedback-driven content-improvement feature needs — a structured-output method on the LLM seam, and a `content_blocks` structural validator — with no user-facing change.

**Architecture:** Extend the existing `LlmClient` Protocol (`backend/src/services/llm_service.py`) with a non-streaming `complete_structured()` method implemented for Anthropic via forced `tool_use`, and add a pure `validate_content_blocks()` module. Both are consumed by Plan B (triage) and Plan C (content pipeline). No DB, no router, no frontend.

**Tech Stack:** FastAPI backend (Python 3.13, uv), `anthropic` `AsyncAnthropic` SDK, pytest (async), ruff + ty via `poe`.

## Global Constraints

- Backend conventions are MANDATORY: `python-be-architecture.md` (router → service → repository → model layering; `src/` layout; DI in `core/dependencies/`).
- Backend checks after every change, run **inside `backend/`**: `uv run poe format && uv run poe lint && uv run poe test`. Coverage floor ≥ 80%.
- Branch: `feature/feedback-content-improvement` (already created off `main`). Commit only the specific files each task lists (`git add <path>`), never `git add -A`.
- Provider-blind rule: `complete_structured` lives on the `LlmClient` Protocol; the Anthropic specifics stay inside `AnthropicLlmClient`. Callers (Plans B/C) depend only on the Protocol.
- Anthropic has no native JSON mode — structured output is a **forced `tool_use`** call (`tool_choice={"type": "tool", "name": ...}`), reading the tool-call `input` from the response content blocks. Use the model already configured on the client (`self._model`); do not hardcode a model id.
- The validator is **purely structural** (mirrors `frontend/src/types/contentBlocks.ts`). It does NOT enforce media immutability — that is a service-layer diff in Plan C.

---

### Task 1: `complete_structured()` on the LLM seam

**Files:**
- Modify: `backend/src/services/llm_service.py`
- Modify: `backend/tests/fixtures/llm.py` (extend the fakes so they still satisfy the widened Protocol, and add a structured-SDK fake)
- Test: `backend/tests/unit/test_llm_service.py`

**Interfaces:**
- Consumes: nothing new (existing `LlmUsage`, `AnthropicLlmClient` in the same file).
- Produces (Plans B/C rely on these exact names/types):
  - `StructuredSchema` frozen dataclass: `name: str`, `description: str`, `input_schema: dict[str, Any]`.
  - `LlmClient.complete_structured(*, system: str, prompt: str, schema: StructuredSchema, max_tokens: int) -> tuple[dict[str, Any], LlmUsage]` (async).
  - `LlmError(RuntimeError)` — raised when the model returns no `tool_use` block.
  - `FakeLlmClient(chunks, usage=None, structured=None)` now also implements `complete_structured` (returns `(dict(structured), usage_value)`, records calls in `.structured_calls`).

- [ ] **Step 1: Write the failing test**

Add to `backend/tests/unit/test_llm_service.py`:

```python
from src.services.llm_service import AnthropicLlmClient, StructuredSchema
from tests.fixtures.llm import FakeStructuredAsyncAnthropic


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
    assert call["tools"][0]["name"] == "triage"
```

- [ ] **Step 2: Add the structured SDK fake so the test can be collected**

Add to `backend/tests/fixtures/llm.py` (and add the new names to `__all__`):

```python
class FakeToolUseBlock:
    def __init__(self, tool_input: dict[str, object]) -> None:
        self.type = "tool_use"
        self.input = tool_input


class FakeAnthropicToolMessage:
    def __init__(self, tool_input: dict[str, object], usage: tuple[int, int]) -> None:
        self.content = [FakeToolUseBlock(tool_input)]
        self.usage = type(
            "Usage", (), {"input_tokens": usage[0], "output_tokens": usage[1]}
        )()


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

    def __init__(
        self, tool_input: dict[str, object], usage: tuple[int, int] = (20, 8)
    ) -> None:
        self.messages = _FakeStructuredMessages(tool_input, usage)
```

- [ ] **Step 3: Run the test to verify it fails**

Run (inside `backend/`): `uv run pytest tests/unit/test_llm_service.py::test_anthropic_client_complete_structured_returns_tool_input_and_usage -v`
Expected: FAIL — `ImportError`/`AttributeError` (`StructuredSchema` and `complete_structured` don't exist yet).

- [ ] **Step 4: Implement the seam changes**

In `backend/src/services/llm_service.py`: add `Any` to the `typing` import, extend `__all__`, add `StructuredSchema` + `LlmError`, add `complete_structured` to the `LlmClient` Protocol, and implement it on `AnthropicLlmClient`.

```python
from typing import TYPE_CHECKING, Any, Protocol
```

```python
__all__ = [
    "AnthropicLlmClient",
    "LlmClient",
    "LlmError",
    "LlmReplyStream",
    "LlmUsage",
    "StructuredSchema",
]


class LlmError(RuntimeError):
    """Raised when the LLM response is missing an expected structured result."""


@dataclass(frozen=True)
class StructuredSchema:
    """A forced-tool_use definition: the tool name, its description, and the
    JSON Schema the model must fill. The returned dict matches input_schema."""

    name: str
    description: str
    input_schema: dict[str, Any]
```

Add to the `LlmClient` Protocol (alongside `stream_reply`):

```python
    async def complete_structured(
        self, *, system: str, prompt: str, schema: StructuredSchema, max_tokens: int
    ) -> tuple[dict[str, Any], LlmUsage]: ...
```

Add to `AnthropicLlmClient`:

```python
    async def complete_structured(
        self, *, system: str, prompt: str, schema: StructuredSchema, max_tokens: int
    ) -> tuple[dict[str, Any], LlmUsage]:
        message = await self._client.messages.create(
            model=self._model,
            max_tokens=max_tokens,
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
        usage = LlmUsage(message.usage.input_tokens, message.usage.output_tokens)
        for block in message.content:
            if block.type == "tool_use":
                return dict(block.input), usage  # ty: ignore[unresolved-attribute]
        msg = "model returned no tool_use block"
        raise LlmError(msg)
```

- [ ] **Step 5: Widen the Protocol-conforming fakes**

Because `LlmClient` is a structural `Protocol`, every object passed where an `LlmClient` is expected (e.g. `FakeLlmClient` in the existing chat tests) must now also have `complete_structured`, or `ty` will fail at those call sites. Update `backend/tests/fixtures/llm.py`:

In `FakeLlmClient.__init__`, add a `structured` param and call log:

```python
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
```

Add the method to `FakeLlmClient`:

```python
    async def complete_structured(
        self, *, system: str, prompt: str, schema: object, max_tokens: int
    ) -> tuple[dict[str, object], LlmUsage]:
        self.structured_calls.append(
            {"system": system, "prompt": prompt, "schema": schema, "max_tokens": max_tokens}
        )
        return dict(self.structured), self.usage_value
```

Add the method to `RaisingLlmClient`:

```python
    async def complete_structured(self, **_: object) -> tuple[dict[str, object], LlmUsage]:
        msg = "Anthropic API unreachable"
        raise RuntimeError(msg)
```

- [ ] **Step 6: Run the new test + the full suite**

Run (inside `backend/`):
`uv run pytest tests/unit/test_llm_service.py -v`
Expected: PASS (both the existing streaming test and the new structured test).
Then `uv run poe format && uv run poe lint && uv run poe test`
Expected: all green (the widened fakes keep the existing chat tests typechecking).

- [ ] **Step 7: Commit**

```bash
git add backend/src/services/llm_service.py backend/tests/fixtures/llm.py backend/tests/unit/test_llm_service.py
git commit -m "feat(llm): add complete_structured (forced tool_use) to the LlmClient seam"
```

---

### Task 2: `content_blocks` structural validator

**Files:**
- Create: `backend/src/services/content_blocks_validation.py`
- Test: `backend/tests/unit/test_content_blocks_validation.py`

**Interfaces:**
- Consumes: nothing.
- Produces (Plans B/C rely on these):
  - `validate_content_blocks(blocks: object) -> list[str]` — returns human-readable error strings; empty list means valid.
  - `KNOWN_BLOCK_TYPES: set[str]`.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/unit/test_content_blocks_validation.py`:

```python
from src.services.content_blocks_validation import validate_content_blocks


def test_valid_blocks_pass() -> None:
    blocks = [
        {"id": "b1", "type": "heading", "level": 2, "text": "Prompting basics"},
        {"id": "b2", "type": "paragraph", "text": "Be specific."},
        {
            "id": "b3",
            "type": "quiz",
            "questions": [
                {
                    "id": "q1",
                    "q": "What helps most?",
                    "options": ["vagueness", "specificity"],
                    "correct": 1,
                    "explanation": "Specific prompts win.",
                }
            ],
        },
    ]
    assert validate_content_blocks(blocks) == []


def test_not_a_list_is_rejected() -> None:
    assert validate_content_blocks({"id": "b1", "type": "paragraph"}) == [
        "content_blocks must be a list"
    ]


def test_unknown_type_is_rejected() -> None:
    errors = validate_content_blocks([{"id": "b1", "type": "banner", "text": "x"}])
    assert any("unknown type" in e for e in errors)


def test_missing_required_field_is_rejected() -> None:
    errors = validate_content_blocks([{"id": "b1", "type": "paragraph"}])
    assert any("text" in e for e in errors)


def test_missing_id_is_rejected() -> None:
    errors = validate_content_blocks([{"type": "paragraph", "text": "hi"}])
    assert any("id" in e for e in errors)


def test_quiz_correct_out_of_range_is_rejected() -> None:
    errors = validate_content_blocks(
        [
            {
                "id": "b1",
                "type": "quiz",
                "questions": [
                    {
                        "id": "q1",
                        "q": "Q?",
                        "options": ["a", "b"],
                        "correct": 5,
                        "explanation": "e",
                    }
                ],
            }
        ]
    )
    assert any("correct" in e for e in errors)


def test_image_missing_blob_path_is_rejected() -> None:
    errors = validate_content_blocks([{"id": "b1", "type": "image", "alt": "a chart"}])
    assert any("blob_path" in e for e in errors)


def test_interactive_bad_mode_is_rejected() -> None:
    errors = validate_content_blocks(
        [{"id": "b1", "type": "interactive", "mode": "wat", "prompt": "p"}]
    )
    assert any("mode" in e for e in errors)
```

- [ ] **Step 2: Run the test to verify it fails**

Run (inside `backend/`): `uv run pytest tests/unit/test_content_blocks_validation.py -v`
Expected: FAIL — `ModuleNotFoundError: src.services.content_blocks_validation`.

- [ ] **Step 3: Implement the validator**

Create `backend/src/services/content_blocks_validation.py`:

```python
from __future__ import annotations

from typing import Any

__all__ = ["KNOWN_BLOCK_TYPES", "validate_content_blocks"]

KNOWN_BLOCK_TYPES = {
    "heading",
    "paragraph",
    "callout",
    "kicker",
    "card_group",
    "quiz",
    "question",
    "whitespace",
    "interactive",
    "try_it_yourself",
    "image",
    "video",
}
_INTERACTIVE_MODES = {"sort", "predict", "spot_the_flaw"}
_WHITESPACE_SIZES = {"sm", "md", "lg"}


def validate_content_blocks(blocks: object) -> list[str]:
    """Structurally validate a proposed content_blocks array against the
    frontend union in frontend/src/types/contentBlocks.ts. Returns a list of
    human-readable error strings; an empty list means the array is valid.

    Purely structural. It does NOT enforce media immutability (that a proposal
    must not add or alter image/video blob_paths) — that is a service-layer
    diff against the lesson's base blocks in the content-improvement apply path.
    """
    if not isinstance(blocks, list):
        return ["content_blocks must be a list"]
    errors: list[str] = []
    for i, block in enumerate(blocks):
        errors.extend(_validate_block(i, block))
    return errors


def _validate_block(i: int, block: object) -> list[str]:
    where = f"block[{i}]"
    if not isinstance(block, dict):
        return [f"{where} must be an object"]
    errs: list[str] = []
    block_id = block.get("id")
    if not isinstance(block_id, str) or not block_id:
        errs.append(f"{where} missing non-empty string 'id'")
    btype = block.get("type")
    if btype not in KNOWN_BLOCK_TYPES:
        errs.append(f"{where} has unknown type {btype!r}")
        return errs
    errs.extend(_validate_fields(where, btype, block))
    return errs


def _require_str(where: str, block: dict[str, Any], field: str) -> list[str]:
    value = block.get(field)
    if not isinstance(value, str) or not value:
        return [f"{where}.{field} must be a non-empty string"]
    return []


def _validate_fields(where: str, btype: str, block: dict[str, Any]) -> list[str]:
    errs: list[str] = []
    if btype in ("paragraph", "callout", "kicker"):
        errs += _require_str(where, block, "text")
    elif btype == "question":
        errs += _require_str(where, block, "prompt")
    elif btype == "heading":
        errs += _require_str(where, block, "text")
        if block.get("level") not in (1, 2, 3):
            errs.append(f"{where}.level must be 1, 2, or 3")
    elif btype == "whitespace":
        if block.get("size") not in _WHITESPACE_SIZES:
            errs.append(f"{where}.size must be one of sm|md|lg")
    elif btype == "card_group":
        errs += _validate_card_group(where, block)
    elif btype == "quiz":
        errs += _validate_quiz(where, block)
    elif btype == "interactive":
        errs += _validate_interactive(where, block)
    elif btype == "try_it_yourself":
        for field in ("task", "material", "whatToNotice"):
            errs += _require_str(where, block, field)
        if not isinstance(block.get("steps"), list):
            errs.append(f"{where}.steps must be a list")
    elif btype == "image":
        errs += _require_str(where, block, "blob_path")
        errs += _require_str(where, block, "alt")
    elif btype == "video":
        source = block.get("source")
        if source == "embed":
            errs += _require_str(where, block, "url")
        elif source == "blob":
            errs += _require_str(where, block, "blob_path")
        else:
            errs.append(f"{where}.source must be 'embed' or 'blob'")
    return errs


def _validate_card_group(where: str, block: dict[str, Any]) -> list[str]:
    cards = block.get("cards")
    if not isinstance(cards, list) or not cards:
        return [f"{where}.cards must be a non-empty list"]
    errs: list[str] = []
    for j, card in enumerate(cards):
        cwhere = f"{where}.cards[{j}]"
        if not isinstance(card, dict):
            errs.append(f"{cwhere} must be an object")
            continue
        errs += _require_str(cwhere, card, "title")
        errs += _require_str(cwhere, card, "body")
    return errs


def _validate_quiz(where: str, block: dict[str, Any]) -> list[str]:
    questions = block.get("questions")
    if not isinstance(questions, list) or not questions:
        return [f"{where}.questions must be a non-empty list"]
    errs: list[str] = []
    for j, question in enumerate(questions):
        qwhere = f"{where}.questions[{j}]"
        if not isinstance(question, dict):
            errs.append(f"{qwhere} must be an object")
            continue
        errs += _require_str(qwhere, question, "q")
        errs += _require_str(qwhere, question, "explanation")
        options = question.get("options")
        if (
            not isinstance(options, list)
            or not options
            or not all(isinstance(o, str) for o in options)
        ):
            errs.append(f"{qwhere}.options must be a non-empty list of strings")
            continue
        correct = question.get("correct")
        if (
            not isinstance(correct, int)
            or isinstance(correct, bool)
            or not (0 <= correct < len(options))
        ):
            errs.append(f"{qwhere}.correct must be an index into options")
    return errs


def _validate_interactive(where: str, block: dict[str, Any]) -> list[str]:
    mode = block.get("mode")
    if mode not in _INTERACTIVE_MODES:
        return [f"{where}.mode must be one of sort|predict|spot_the_flaw"]
    errs = _require_str(where, block, "prompt")
    if mode == "sort":
        for field in ("buckets", "items"):
            if not isinstance(block.get(field), list):
                errs.append(f"{where}.{field} must be a list")
    elif mode == "predict":
        if not isinstance(block.get("options"), list):
            errs.append(f"{where}.options must be a list")
        errs += _require_str(where, block, "correctOptionId")
    elif mode == "spot_the_flaw":
        errs += _require_str(where, block, "example")
        if not isinstance(block.get("candidates"), list):
            errs.append(f"{where}.candidates must be a list")
    return errs
```

- [ ] **Step 4: Run the tests to verify they pass**

Run (inside `backend/`): `uv run pytest tests/unit/test_content_blocks_validation.py -v`
Expected: PASS (all 8 tests).

- [ ] **Step 5: Run the full backend checks**

Run (inside `backend/`): `uv run poe format && uv run poe lint && uv run poe test`
Expected: all green.

- [ ] **Step 6: Commit**

```bash
git add backend/src/services/content_blocks_validation.py backend/tests/unit/test_content_blocks_validation.py
git commit -m "feat(content): add structural content_blocks validator"
```

---

## Self-Review

**Spec coverage (this plan covers the two foundation items in the spec):**
- Spec "LLM seam extension (structured output)" → Task 1 ✅ (method signature matches the spec's `complete_structured`, forced `tool_use`, on the shared seam).
- Spec "content_blocks validation" → Task 2 ✅ (structural validator mirroring the frontend union; media-immutability explicitly deferred to Plan C, matching the spec's note that it's a service-layer diff).
- Everything else in the spec (triage columns/service/endpoint, proposals table, run/review, admin UI) is Plan B / Plan C — out of scope here by the agreed three-plan split.

**Placeholder scan:** none — every step has runnable code or an exact command.

**Type consistency:** `StructuredSchema` (name/description/input_schema), `complete_structured(*, system, prompt, schema, max_tokens) -> tuple[dict, LlmUsage]`, `validate_content_blocks(blocks) -> list[str]`, and `KNOWN_BLOCK_TYPES` are the names Plans B/C will import — used identically here. The Protocol widening + fake updates (Task 1 Step 5) keep existing chat tests typechecking.

**Scope:** self-contained; produces working, independently testable software (two commits, full suite green) with no dependency on B or C.
