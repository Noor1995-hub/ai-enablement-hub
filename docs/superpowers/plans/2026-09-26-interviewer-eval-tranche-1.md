# AI Interviewer — Tranche 1 (make runs attributable, close the cheap gaps) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Every interview turn and playbook records which prompt version, model and settings produced it. The playbook endpoint enforces its own answer floor and handles time and size limits. The interviewer requires a completed assessment (admins exempt). The playbook prompt never guesses gender.

**Architecture:** Small changes to the existing plain-API-call design, with no new tables. Run metadata goes into the JSON columns that already exist (`messages.metadata` per turn, `conversations.summary["meta"]` per playbook). The prompt version is a short content hash of the shipped prompt file, because git is the prompt history since 2026-09-23. The assessment gate is a FastAPI dependency on the three interview write paths (opener, playbook, chat turn), mirrored by the journey tile on the frontend.

**Tech Stack:** FastAPI + Pydantic + SQLAlchemy async (backend, `uv`, pytest, ruff, ty), `anthropic` 1.x SDK, React + TypeScript + Vitest (frontend).

**Spec:** `docs/superpowers/specs/2026-09-26-interviewer-evaluation-design.md` (read Part A first; it overrides Part B).

## Global Constraints

- Live model is `claude-sonnet-5`. **Do not send `temperature`, `top_p` or `top_k`**: Sonnet 5 rejects them with a 400. Do not add `output_config.effort` in this tranche either (spec A.1).
- Prompts change only by PR. Any edit under `backend/prompts/` must regenerate golden snapshots: from `backend/`, PowerShell `$env:UPDATE_GOLDEN='1'; uv run pytest tests/golden/ai`, then commit the snapshot diff.
- Never use an em dash or en dash in new learner-facing strings (error messages included). Use a hyphen, comma or full stop.
- Assessment gate: role `admin` is exempt; every other role (`user`, `user+`) needs `survey_status == "complete"`. An `in_progress` draft does **not** count.
- `GET /api/interview/me` and the admin interview endpoints stay ungated by the assessment rule, so a learner who already has a playbook can still read it.
- The ready marker is `[[READY_TO_BUILD]]` in exactly one backend place (`src/services/interview_marker.py`) and one frontend place (`frontend/src/pages/Interview.tsx` `READY_MARKER`).
- The backend answer floor (6) must equal frontend `FALLBACK_MIN_ANSWERS` in `frontend/src/pages/Interview.tsx`.
- Work on one branch, one PR, squash merge (`CONTRIBUTING.md`). Conventional commit titles `<type>(<area>): <summary>`.

## Running tests locally (read once)

- Unit and golden tests need `backend/.env`. The active clone has none. Copy it from `..\ai-enablement-hub-rebuild\backend\.env` for the local run and **delete it before any deploy** (`deploy-legacy.ps1` uploads the folder; the normal path is the GitHub Deploy action, which builds from `main`, so this only matters for break-glass).
- Integration tests (`tests/integration/`) need the Postgres firewall to allow your IP. Aaron's preference is not to open it: **integration tests are verified by CI on the PR**. Write them locally, run the unit tests, push, and read the CI result.
- Targeted run from `backend/`: `uv run pytest tests/unit/test_interview_service.py -v`.
- Frontend from `frontend/`: `npm test`, `npm run typecheck`, `npm run lint`, `npm run build`.

## Review Focus

- A learner with an **in-progress** (draft) assessment calls the opener. Expected: 403 "Complete your assessment before starting the interview", the same as with no survey at all. Pinned in Task 5.
- A learner with **no assessment but an existing playbook** (this exists in production) opens `/interview`. Expected: the playbook still shows, because `/me` isn't gated, and the journey tile says Completed, not "Assessment first". Pinned in Tasks 5 and 6.
- A learner **types `[[READY_TO_BUILD]]` themselves** and then asks for the playbook after 2 answers. Expected: 409. Only an *assistant* turn carrying the marker counts as the model's offer. Pinned in Task 2.
- **Generation hangs** (the provider is slow). Expected: a clean error within 180 s, no summary written, the learner can retry (rate limit is 5 per 10 min). Pinned in Task 3.
- An **admin with no assessment** tests the interview. Expected: every endpoint works, and the briefing says "No completed assessment on file". Pinned in Task 5.

## Found while planning — out of scope, noted for later

- `POST /api/chat/interview` without `conversation_id` creates a *second* interview conversation (`ChatService.resolve_conversation`). `InterviewService` reads `conversations[0]`. The frontend always passes the id, so this needs a crafted request. Raise it as a GitHub issue (`security` label) and don't fix it here.
- The interviewer's closing line "sit tight while it gets put together" doesn't match the UI, which waits for a Build click. This is a prompt-tuning item for a later tranche.
- `InterviewContextService.build_briefing` treats an `in_progress` draft survey as a completed assessment. After Task 5 only admins can reach it with a draft, so leave it.

---

### Task 1: One home for the ready marker, strip it from model history, guard it in CI

**Files:**
- Create: `backend/src/services/interview_marker.py`
- Modify: `backend/src/services/interview_service.py` (remove `_READY_MARKER` / `_strip_ready_marker`, import the new module)
- Modify: `backend/src/services/chat_service.py` (`_history_for`)
- Modify: `backend/src/services/prompt_service.py` (`REQUIRED_TOKENS`)
- Test: `backend/tests/unit/test_chat_service.py`, `backend/tests/unit/test_interview_marker.py`, `backend/tests/unit/test_prompt_integrity.py` (no edit, it is parametrised from `REQUIRED_TOKENS`)

**Interfaces:**
- Produces: `READY_MARKER: str`, `has_ready_marker(text: str) -> bool`, `strip_ready_marker(text: str) -> str` in `src.services.interview_marker`. Tasks 2 and 3 use `has_ready_marker`.

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/unit/test_interview_marker.py`:

```python
from src.services.interview_marker import READY_MARKER, has_ready_marker, strip_ready_marker


def test_strip_removes_marker_and_trailing_whitespace() -> None:
    assert strip_ready_marker(f"Want me to build it?\n{READY_MARKER}") == "Want me to build it?"


def test_strip_leaves_text_without_marker_untouched() -> None:
    assert strip_ready_marker("Plain turn.  ") == "Plain turn.  "


def test_has_ready_marker() -> None:
    assert has_ready_marker(f"x\n{READY_MARKER}") is True
    assert has_ready_marker("x") is False
```

Append to `backend/tests/unit/test_chat_service.py`:

```python
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
    assert sent == [  # ty: ignore[unsupported-operator]
        {"role": "assistant", "content": "Shall I build it?"},
        {"role": "user", "content": "one more thing"},
    ]
```

- [ ] **Step 2: Run to verify they fail**

Run (from `backend/`): `uv run pytest tests/unit/test_interview_marker.py tests/unit/test_chat_service.py -v`
Expected: `test_interview_marker.py` errors with `ModuleNotFoundError: No module named 'src.services.interview_marker'`; `test_history_sent_to_the_model_has_no_ready_marker` fails because the marker is still in `sent[0]["content"]`.

- [ ] **Step 3: Implement**

Create `backend/src/services/interview_marker.py`:

```python
from __future__ import annotations

__all__ = ["READY_MARKER", "has_ready_marker", "strip_ready_marker"]

# The interviewer appends this marker to the turn where it offers to build the playbook
# (prompts/interview.md); the frontend detects it to reveal the Build button
# (frontend/src/pages/Interview.tsx READY_MARKER, keep the two in sync). It is a UI
# signal, not conversation: strip it from everything the model or an admin reads.
READY_MARKER = "[[READY_TO_BUILD]]"


def has_ready_marker(text: str) -> bool:
    return READY_MARKER in text


def strip_ready_marker(text: str) -> str:
    return text.replace(READY_MARKER, "").rstrip() if READY_MARKER in text else text
```

In `backend/src/services/interview_service.py`: delete the `_READY_MARKER` comment block, the constant, and `_strip_ready_marker`. Add `from src.services.interview_marker import strip_ready_marker` and replace both `_strip_ready_marker(` call sites with `strip_ready_marker(`.

In `backend/src/services/chat_service.py`, add `from src.services.interview_marker import strip_ready_marker` and replace `_history_for` with:

```python
    async def _history_for(self, conversation_id: uuid.UUID) -> list[dict[str, str]]:
        rows = await self._messages.list_recent(conversation_id, limit=_HISTORY_WINDOW)
        # strip_ready_marker: only the interviewer ever emits it, and the model must not
        # re-read its own UI signal on every later turn (spec 2026-09-26 A.1, §8.4).
        return [
            {
                "role": m.role,
                "content": strip_ready_marker(m.content) if m.role == "assistant" else m.content,
            }
            for m in rows
            if m.role in ("user", "assistant")
        ]
```

In `backend/src/services/prompt_service.py`, extend `REQUIRED_TOKENS` (the existing parametrised test in `test_prompt_integrity.py` picks it up):

```python
REQUIRED_TOKENS: dict[str, tuple[str, ...]] = {
    # The interviewer's only machine-read output: without it the Build button never
    # appears except through the 6-answer fallback.
    "interview": ("[[READY_TO_BUILD]]",),
    "interview_playbook": (
        "{first_name}",
        "{assessment_json}",
        "{company_context}",
        "{transcript}",
    ),
}
```

- [ ] **Step 4: Run to verify they pass**

Run: `uv run pytest tests/unit/test_interview_marker.py tests/unit/test_chat_service.py tests/unit/test_interview_service.py tests/unit/test_prompt_integrity.py -v`
Expected: all PASS (`test_required_tokens_are_present[interview-[[READY_TO_BUILD]]]` is a new passing case).

- [ ] **Step 5: Commit**

```bash
git add backend/src/services/interview_marker.py backend/src/services/interview_service.py backend/src/services/chat_service.py backend/src/services/prompt_service.py backend/tests/unit/test_interview_marker.py backend/tests/unit/test_chat_service.py
git commit -m "fix(interview): keep the ready marker out of model history; guard it in CI"
```

---

### Task 2: Server-side answer floor on the playbook endpoint

**Files:**
- Modify: `backend/src/services/interview_service.py` (`build_playbook`, new `_ensure_ready`)
- Test: `backend/tests/unit/test_interview_service.py`

**Interfaces:**
- Consumes: `has_ready_marker` (Task 1).
- Produces: `build_playbook` raises `ConflictError` (HTTP 409) when neither condition holds. Module constant `_MIN_ANSWERS_WITHOUT_OFFER = 6`.

- [ ] **Step 1: Write the failing tests, and move existing tests onto a ready transcript**

In `backend/tests/unit/test_interview_service.py`, add after `_conversation`:

```python
def _ready_rows() -> list[SimpleNamespace]:
    """A transcript the playbook endpoint accepts: the interviewer made its offer."""
    return [
        SimpleNamespace(role="assistant", content="Hi, what do you do?"),
        SimpleNamespace(role="user", content="I run the monthly close."),
        SimpleNamespace(role="assistant", content="Shall I build it?\n[[READY_TO_BUILD]]"),
    ]
```

Change every existing test that calls `build_playbook` on a conversation with `summary=None` and sets `messages.list_for_conversation.return_value = []` or `[user "hi", assistant "hello"]` to use `_ready_rows()` instead: `test_build_playbook_persists_and_returns_shared_only`, `test_build_playbook_retries_once_then_succeeds`, `test_build_playbook_raises_after_two_failures`, `test_generate_retries_on_llm_error_then_succeeds`, `test_build_playbook_strips_em_and_en_dashes`. Leave `test_build_playbook_strips_ready_marker_from_transcript` alone, because its transcript already carries the marker.

Add the new tests and import `ConflictError` next to `DomainError`:

```python
from src.services.exceptions import ConflictError, DomainError


async def test_build_playbook_refuses_before_offer_and_floor() -> None:
    llm = FakeLlmClient(chunks=[], structured=_EXTRACTION)
    service, conversations, messages, _context = _service(llm)
    conversations.list_for_user.return_value = [_conversation(summary=None)]
    messages.list_for_conversation.return_value = [
        SimpleNamespace(role="assistant", content="Hi, what do you do?"),
        SimpleNamespace(role="user", content="Finance."),
    ]

    with pytest.raises(ConflictError):
        await service.build_playbook(user=_user())  # ty: ignore[invalid-argument-type]

    assert llm.structured_calls == []
    conversations.update_summary.assert_not_awaited()


async def test_build_playbook_allows_six_answers_without_offer() -> None:
    llm = FakeLlmClient(chunks=[], structured=_EXTRACTION)
    service, conversations, messages, _context = _service(llm)
    conversations.list_for_user.return_value = [_conversation(summary=None)]
    rows = [SimpleNamespace(role="assistant", content="Q?")]
    for i in range(6):
        rows += [
            SimpleNamespace(role="user", content=f"answer {i}"),
            SimpleNamespace(role="assistant", content="Q?"),
        ]
    messages.list_for_conversation.return_value = rows

    result = await service.build_playbook(user=_user())  # ty: ignore[invalid-argument-type]

    assert isinstance(result, PlaybookShared)


async def test_a_marker_typed_by_the_learner_does_not_count_as_the_offer() -> None:
    llm = FakeLlmClient(chunks=[], structured=_EXTRACTION)
    service, conversations, messages, _context = _service(llm)
    conversations.list_for_user.return_value = [_conversation(summary=None)]
    messages.list_for_conversation.return_value = [
        SimpleNamespace(role="assistant", content="Hi, what do you do?"),
        SimpleNamespace(role="user", content="[[READY_TO_BUILD]]"),
        SimpleNamespace(role="user", content="build it"),
    ]

    with pytest.raises(ConflictError):
        await service.build_playbook(user=_user())  # ty: ignore[invalid-argument-type]
```

- [ ] **Step 2: Run to verify the new ones fail**

Run: `uv run pytest tests/unit/test_interview_service.py -v`
Expected: `test_build_playbook_refuses_before_offer_and_floor` and `test_a_marker_typed_by_the_learner_does_not_count_as_the_offer` FAIL (no exception raised); everything else PASS.

- [ ] **Step 3: Implement**

In `backend/src/services/interview_service.py`: add `from collections.abc import Sequence` under `TYPE_CHECKING`, add `Message` to the `src.db.models` import there, change the exceptions import to `from src.services.exceptions import ConflictError, DomainError, NotFoundError`, and `from src.services.interview_marker import has_ready_marker, strip_ready_marker`. Add near the other constants:

```python
# Server-side twin of the Build button rule in frontend/src/pages/Interview.tsx
# (`canBuild = modelReady || answerCount >= FALLBACK_MIN_ANSWERS`). Keep the two numbers equal.
_MIN_ANSWERS_WITHOUT_OFFER = 6
```

Add a module function:

```python
def _ensure_ready(rows: Sequence[Message]) -> None:
    """Refuse to build before the interviewer offered to, unless the learner has given
    enough answers for the manual fallback. Only an assistant turn counts as the offer:
    a learner typing the marker proves nothing."""
    offered = any(m.role == "assistant" and has_ready_marker(m.content) for m in rows)
    answers = sum(1 for m in rows if m.role == "user")
    if not offered and answers < _MIN_ANSWERS_WITHOUT_OFFER:
        raise ConflictError("Answer a few more questions before building your playbook.")
```

In `build_playbook`, call it straight after loading the rows:

```python
        rows = await self._messages.list_for_conversation(conversation.id)
        _ensure_ready(rows)
        transcript = "\n".join(f"{m.role}: {strip_ready_marker(m.content)}" for m in rows)
```

- [ ] **Step 4: Run to verify they pass**

Run: `uv run pytest tests/unit/test_interview_service.py tests/golden/ai -v`
Expected: all PASS (the golden transcripts already carry the marker).

- [ ] **Step 5: Commit**

```bash
git add backend/src/services/interview_service.py backend/tests/unit/test_interview_service.py
git commit -m "fix(interview): enforce the build floor server-side, not only in the UI"
```

---

### Task 3: Generation hardening (time budget, transcript cap, provider errors, opener logging)

**Files:**
- Modify: `backend/src/services/interview_service.py` (`build_playbook`, `_generate`, `open_interview`)
- Test: `backend/tests/unit/test_interview_service.py`

**Interfaces:**
- Consumes: `is_transient_provider_error` from `src.services.llm_service` (exists).
- Produces: `_generate(system) -> tuple[PlaybookExtraction, LlmUsage, int]` (extraction, usage of the successful call, 1-based attempt number). Task 4 relies on this return shape. Constants `_GENERATION_TIMEOUT_SECONDS = 180.0`, `_MAX_TRANSCRIPT_CHARS = 100_000`.

- [ ] **Step 1: Write the failing tests**

Add to `backend/tests/unit/test_interview_service.py` (add `import asyncio`, `import logging`, `import anthropic`, `import httpx2` at the top, and `from src.services import interview_service as interview_module`):

```python
class _SlowLlmClient:
    model = "fake-model"

    async def complete_structured(self, **_: object) -> tuple[dict[str, object], LlmUsage]:
        await asyncio.sleep(1)
        return _EXTRACTION, LlmUsage(input_tokens=1, output_tokens=1)


class _ProviderDownLlmClient:
    model = "fake-model"

    def __init__(self, exc: Exception) -> None:
        self._exc = exc

    async def complete_structured(self, **_: object) -> tuple[dict[str, object], LlmUsage]:
        raise self._exc


async def test_build_playbook_times_out_cleanly(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(interview_module, "_GENERATION_TIMEOUT_SECONDS", 0.01)
    service, conversations, messages, _context = _service(_SlowLlmClient())
    conversations.list_for_user.return_value = [_conversation(summary=None)]
    messages.list_for_conversation.return_value = _ready_rows()

    with pytest.raises(DomainError, match="took too long"):
        await service.build_playbook(user=_user())  # ty: ignore[invalid-argument-type]

    conversations.update_summary.assert_not_awaited()


async def test_build_playbook_maps_a_busy_provider_to_a_domain_error() -> None:
    exc = anthropic.APIConnectionError(
        request=httpx2.Request("POST", "https://api.anthropic.com/v1/messages")
    )
    service, conversations, messages, _context = _service(_ProviderDownLlmClient(exc))
    conversations.list_for_user.return_value = [_conversation(summary=None)]
    messages.list_for_conversation.return_value = _ready_rows()

    with pytest.raises(DomainError, match="busy"):
        await service.build_playbook(user=_user())  # ty: ignore[invalid-argument-type]


async def test_build_playbook_lets_an_unknown_error_propagate() -> None:
    service, conversations, messages, _context = _service(
        _ProviderDownLlmClient(RuntimeError("bug"))
    )
    conversations.list_for_user.return_value = [_conversation(summary=None)]
    messages.list_for_conversation.return_value = _ready_rows()

    with pytest.raises(RuntimeError, match="bug"):
        await service.build_playbook(user=_user())  # ty: ignore[invalid-argument-type]


async def test_build_playbook_refuses_an_oversized_transcript() -> None:
    llm = FakeLlmClient(chunks=[], structured=_EXTRACTION)
    service, conversations, messages, _context = _service(llm)
    conversations.list_for_user.return_value = [_conversation(summary=None)]
    messages.list_for_conversation.return_value = [
        *_ready_rows(),
        SimpleNamespace(role="user", content="x" * 100_001),
    ]

    with pytest.raises(DomainError, match="too long"):
        await service.build_playbook(user=_user())  # ty: ignore[invalid-argument-type]

    assert llm.structured_calls == []


async def test_open_interview_failure_is_logged(caplog: pytest.LogCaptureFixture) -> None:
    service, conversations, _messages, context = _service(RaisingLlmClient())
    context.build_briefing.return_value = "BRIEFING"
    conversations.list_for_user.return_value = []

    with caplog.at_level(logging.WARNING), pytest.raises(DomainError):
        await service.open_interview(user=_user())  # ty: ignore[invalid-argument-type]

    assert "interview opener failed" in caplog.text
```

Also add `model = "fake-model"` as a class attribute to `_FlakyLlmClient` and to `_FakeLlmErrorThenSuccess` in the same file (Task 4 reads `self._llm.model`; adding it now keeps the fakes stable).

- [ ] **Step 2: Run to verify they fail**

Run: `uv run pytest tests/unit/test_interview_service.py -v`
Expected: the five new tests FAIL (the timeout test hangs for about 1 s and then fails on the missing `DomainError`; the busy test gets a raw `APIConnectionError`; the oversized test calls the LLM; the log test finds no text). `test_build_playbook_lets_an_unknown_error_propagate` may already pass, which is fine.

- [ ] **Step 3: Implement**

In `backend/src/services/interview_service.py` add `import asyncio`, `import logging`, `logger = logging.getLogger(__name__)`, change the llm import to `from src.services.llm_service import LlmError, is_transient_provider_error`, and add `LlmUsage` to the `TYPE_CHECKING` import from `src.services.llm_service`. Add constants:

```python
# One budget for the whole generation (both attempts, and the SDK's own retries inside
# them). Sized under the Container Apps ingress timeout of 240 s, same reasoning as
# content_improvement_service._PER_LESSON_TIMEOUT_SECONDS.
_GENERATION_TIMEOUT_SECONDS = 180.0
# Chat messages have no length limit, so the transcript is unbounded. ~25k tokens is far
# past any real interview (the longest in production so far is ~20 answers, ~12k chars).
# Refuse rather than truncate: half a transcript makes a confidently wrong playbook.
_MAX_TRANSCRIPT_CHARS = 100_000
```

In `build_playbook`, after building `transcript`:

```python
        if len(transcript) > _MAX_TRANSCRIPT_CHARS:
            logger.warning(
                "interview %s transcript too long for a playbook (%d chars)",
                conversation.id,
                len(transcript),
            )
            raise DomainError(
                "This interview is too long to turn into a playbook. "
                "Please ask your hub admin to reset it."
            )
```

and change the generation line to `extraction, _usage, _attempts = await self._generate(system)` (Task 4 uses the two values).

Replace `_generate` with:

```python
    async def _generate(self, system: str) -> tuple[PlaybookExtraction, LlmUsage, int]:
        """Two attempts against the schema inside one time budget. Returns the extraction,
        the usage of the call that produced it, and which attempt (1 or 2) that was.

        Unusable output (schema mismatch, no tool_use block) is retried once. A timeout or
        a provider outage is not: the SDK has already retried those itself, so another
        round only burns the budget. Anything else is a bug and propagates as a 500."""
        last_error: Exception | None = None
        try:
            async with asyncio.timeout(_GENERATION_TIMEOUT_SECONDS):
                for attempt in (1, 2):
                    try:
                        result, usage = await self._llm.complete_structured(
                            system=system,
                            prompt=_GENERATE_PROMPT,
                            schema=PLAYBOOK_SCHEMA,
                            max_tokens=_MAX_TOKENS,
                        )
                        return PlaybookExtraction.model_validate(result), usage, attempt
                    except (ValidationError, LlmError) as exc:
                        logger.warning("playbook attempt %d unusable: %s", attempt, exc)
                        last_error = exc
        except TimeoutError as exc:
            logger.warning("playbook generation timed out after %ss", _GENERATION_TIMEOUT_SECONDS)
            raise DomainError("Building your playbook took too long - please try again.") from exc
        except Exception as exc:
            if not is_transient_provider_error(exc):
                raise
            logger.warning("playbook generation: provider unavailable (%s)", type(exc).__name__)
            raise DomainError(
                "The AI service is busy right now - please try again in a minute."
            ) from exc
        logger.error("playbook generation failed after 2 attempts: %s", last_error)
        raise DomainError("Could not generate the playbook - please try again.") from last_error
```

(If ruff flags `BLE001` on `except Exception`, add `# noqa: BLE001 - re-raised unless transient`.)

In `open_interview`, log before each `raise DomainError(...)`:

```python
        except Exception as exc:  # noqa: BLE001 - best-effort opener; the UI offers retry
            logger.warning("interview opener failed for user %s", user.id, exc_info=exc)
            raise DomainError("Could not start the interview - please try again.") from exc
        if not greeting:
            logger.warning("interview opener failed for user %s: empty greeting", user.id)
            raise DomainError("Could not start the interview - please try again.")
```

- [ ] **Step 4: Run to verify they pass**

Run: `uv run pytest tests/unit/test_interview_service.py tests/golden/ai -v && uv run poe lint-src && uv run poe ty-src`
Expected: all PASS, ruff and ty clean.

- [ ] **Step 5: Commit**

```bash
git add backend/src/services/interview_service.py backend/tests/unit/test_interview_service.py
git commit -m "fix(interview): bound playbook generation in time and size; handle provider outages"
```

---

### Task 4: Stamp every run with model, prompt version and settings

**Files:**
- Modify: `backend/src/services/llm_service.py` (`LlmClient.model`, `AnthropicLlmClient.model`, `THINKING_MODE`)
- Modify: `backend/src/services/prompts.py` (`prompt_version`)
- Modify: `backend/src/services/chat_service.py` (assistant metadata)
- Modify: `backend/src/services/interview_service.py` (opener metadata, `summary["meta"]`)
- Modify: `backend/tests/fixtures/llm.py`, `backend/tests/golden/ai/harness.py` (fakes get `model`)
- Test: `backend/tests/unit/test_llm_service.py`, `backend/tests/unit/test_prompts.py` (new), `backend/tests/unit/test_chat_service.py`, `backend/tests/unit/test_interview_service.py`

**Interfaces:**
- Consumes: `_generate` return shape `(extraction, usage, attempt)` (Task 3).
- Produces: `LlmClient.model: str` (property); `THINKING_MODE: str = "disabled"` in `llm_service`; `prompt_version(kind: str) -> str` (12 hex chars) in `src.services.prompts`. Stored shapes:
  - assistant `messages.metadata`: `{"truncated": bool, "model": str, "prompt_version": str, "usage"?: {...}}`
  - opener `messages.metadata`: `{"model": str, "prompt_version": str}`
  - `conversations.summary["meta"]`: `{"model", "prompt_version", "interview_prompt_version", "max_tokens", "thinking", "attempts", "usage": {"input_tokens", "output_tokens"}, "generated_at"}`

- [ ] **Step 1: Write the failing tests**

`backend/tests/unit/test_llm_service.py`, append:

```python
def test_anthropic_client_exposes_its_model() -> None:
    client = AnthropicLlmClient(
        FakeAsyncAnthropic(chunks=[]),  # ty: ignore[invalid-argument-type]
        model="claude-sonnet-5",
    )
    assert client.model == "claude-sonnet-5"
```

New `backend/tests/unit/test_prompts.py`:

```python
from src.services import prompts as P


def test_prompt_version_is_a_stable_short_hash() -> None:
    first = P.prompt_version("interview")
    assert len(first) == 12
    assert all(c in "0123456789abcdef" for c in first)
    assert P.prompt_version("interview") == first


def test_prompt_version_differs_per_prompt() -> None:
    assert P.prompt_version("interview") != P.prompt_version("interview_playbook")
```

`backend/tests/unit/test_chat_service.py`: extend `test_send_message_streams_tokens_then_done_and_persists` after its last assert, adding `from src.services.prompts import prompt_version` to the imports:

```python
    assert assistant_call.kwargs["metadata"]["model"] == "fake-model"
    assert assistant_call.kwargs["metadata"]["prompt_version"] == prompt_version("chatbot")
```

`backend/tests/unit/test_interview_service.py`: in `test_build_playbook_persists_and_returns_shared_only` replace `assert set(persisted.keys()) == {"internal", "shared"}` with:

```python
    assert set(persisted.keys()) == {"internal", "shared", "meta"}
    meta = persisted["meta"]
    assert meta["model"] == "fake-model"
    assert meta["prompt_version"] == prompt_version("interview_playbook")
    assert meta["interview_prompt_version"] == prompt_version("interview")
    assert meta["thinking"] == "disabled"
    assert meta["attempts"] == 1
    assert meta["usage"] == {"input_tokens": 10, "output_tokens": 0}
    assert meta["max_tokens"] == 8192
```

(`FakeLlmClient(chunks=[])` reports `LlmUsage(10, len(chunks))`, hence `output_tokens == 0`.) In `test_build_playbook_retries_once_then_succeeds`, add `assert conversations.update_summary.await_args.args[1]["meta"]["attempts"] == 2`. In `test_open_interview_fresh_generates_persists_and_returns_greeting`, add `assert kw["metadata"] == {"model": "fake-model", "prompt_version": prompt_version("interview")}`. Import `prompt_version` from `src.services.prompts`.

- [ ] **Step 2: Run to verify they fail**

Run: `uv run pytest tests/unit/test_llm_service.py tests/unit/test_prompts.py tests/unit/test_chat_service.py tests/unit/test_interview_service.py -v`
Expected: FAIL with `AttributeError: ... has no attribute 'model'` / `'prompt_version'`, and `KeyError: 'meta'`.

- [ ] **Step 3: Implement**

`backend/src/services/llm_service.py`: add `"THINKING_MODE"` to `__all__`, and above `AnthropicLlmClient`:

```python
# What both calls below send as `thinking`. Recorded in run metadata (spec 2026-09-26 A.1),
# so change this constant and the two `thinking=` arguments together.
THINKING_MODE = "disabled"
```

In `LlmClient(Protocol)` add, before `stream_reply`:

```python
    @property
    def model(self) -> str: ...
```

In `AnthropicLlmClient` add, after `__init__`:

```python
    @property
    def model(self) -> str:
        return self._model
```

`backend/src/services/prompts.py`: add `import hashlib`, `"prompt_version"` to `__all__`, and:

```python
def prompt_version(kind: str) -> str:
    """Which version of the prompt is active: the first 12 hex chars of the SHA-256 of the
    shipped text. Git is the prompt history (2026-09-23), so a stamped run maps back to a
    commit by hashing `backend/prompts/<kind>.md` at that commit."""
    return hashlib.sha256(load_prompt(kind).encode("utf-8")).hexdigest()[:12]
```

`backend/src/services/chat_service.py`: import `prompt_version` alongside `load_prompt`, and in `send_message`'s `finally` block build the metadata as:

```python
                metadata: dict[str, Any] = {
                    "truncated": truncated,
                    "model": self._llm.model,
                    "prompt_version": prompt_version(conversation.kind),
                }
```

(the `usage` block below it is unchanged).

`backend/src/services/interview_service.py`: add `from datetime import UTC, datetime`, import `prompt_version` alongside `load_prompt`, and `THINKING_MODE` from `llm_service`. In `open_interview`, persist the greeting with:

```python
        await self._messages.create(
            conversation.id,
            role="assistant",
            content=greeting,
            metadata={"model": self._llm.model, "prompt_version": prompt_version(_KIND)},
        )
```

In `build_playbook`, replace the generation and persist lines with:

```python
        extraction, usage, attempts = await self._generate(system)
        summary = cast("dict[str, Any]", _sanitize_dashes(extraction.model_dump(mode="json")))
        summary["meta"] = self._run_meta(usage=usage, attempts=attempts)
        await self._conversations.update_summary(conversation.id, summary)
        return PlaybookShared.model_validate(summary["shared"])
```

and add the method:

```python
    def _run_meta(self, *, usage: LlmUsage, attempts: int) -> dict[str, Any]:
        """Which prompts, model and settings produced this playbook (spec 2026-09-26 A.1).
        Stored next to the two boxes in conversations.summary. Nothing learner-facing
        reads it: get_state and get_admin_view only read "shared" and "internal"."""
        return {
            "model": self._llm.model,
            "prompt_version": prompt_version("interview_playbook"),
            "interview_prompt_version": prompt_version(_KIND),
            "max_tokens": _MAX_TOKENS,
            "thinking": THINKING_MODE,
            "attempts": attempts,
            "usage": {"input_tokens": usage.input_tokens, "output_tokens": usage.output_tokens},
            "generated_at": datetime.now(UTC).isoformat(),
        }
```

`backend/tests/fixtures/llm.py`: add `model = "fake-model"` as a class attribute on `FakeLlmClient` and `RaisingLlmClient`. `backend/tests/golden/ai/harness.py`: add `model = "fake-model"` on `RecordingLlm`.

- [ ] **Step 4: Run to verify they pass**

Run: `uv run pytest tests/unit tests/golden/ai -v && uv run poe lint-src && uv run poe ty-src`
Expected: all PASS; golden snapshots unchanged (metadata is not rendered into them).

- [ ] **Step 5: Commit**

```bash
git add backend/src/services/llm_service.py backend/src/services/prompts.py backend/src/services/chat_service.py backend/src/services/interview_service.py backend/tests/fixtures/llm.py backend/tests/golden/ai/harness.py backend/tests/unit/test_llm_service.py backend/tests/unit/test_prompts.py backend/tests/unit/test_chat_service.py backend/tests/unit/test_interview_service.py
git commit -m "feat(interview): stamp turns and playbooks with model, prompt version and settings"
```

---

### Task 5: Require a completed assessment (admins exempt)

**Files:**
- Modify: `backend/src/services/exceptions.py` (`AssessmentRequiredError`)
- Modify: `backend/src/main.py` (403 handler)
- Modify: `backend/src/core/dependencies/interview.py` (`require_completed_assessment`, `require_interview_assessment`)
- Modify: `backend/src/routers/interview.py` (opener + playbook routes)
- Modify: `backend/src/routers/chat.py` (POST `/{kind}` route dependencies)
- Test: `backend/tests/integration/test_routers/test_interview.py`

**Interfaces:**
- Produces: `AssessmentRequiredError` (message `"Complete your assessment before starting the interview"`, HTTP 403). Task 6's frontend relies on that message text only for display, not for logic.

- [ ] **Step 1: Write the failing tests**

Append to `backend/tests/integration/test_routers/test_interview.py`, adding `create_survey` to the factories import:

```python
class TestAssessmentGate:
    """Spec 2026-09-26 A.3.5: normal users need a COMPLETED assessment; admins are exempt.
    404 "not configured" (llm=None in test settings) proves every gate passed."""

    async def _open_project(self, db_session: AsyncSession, project: Project) -> None:
        await unlock_component(db_session, project, "interview")
        await _enable_interview_ai(db_session, project.id)

    async def test_no_assessment_is_403_on_opener_and_playbook(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        project: Project,
        test_settings: Settings,
    ) -> None:
        await self._open_project(db_session, project)
        user = await create_user(db_session, email="gate-none@example.com", project_id=project.id)
        headers = auth_headers(user, test_settings)

        for path in ("/api/interview/opener", "/api/interview/playbook"):
            response = await client.post(path, headers=headers)
            assert response.status_code == 403
            assert "Complete your assessment" in response.json()["error"]["message"]

    async def test_a_draft_assessment_is_not_enough(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        project: Project,
        test_settings: Settings,
    ) -> None:
        await self._open_project(db_session, project)
        user = await create_user(db_session, email="gate-draft@example.com", project_id=project.id)
        await create_survey(db_session, user, status="in_progress")

        response = await client.post(
            "/api/interview/opener", headers=auth_headers(user, test_settings)
        )
        assert response.status_code == 403

    async def test_a_completed_assessment_passes(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        project: Project,
        test_settings: Settings,
    ) -> None:
        await self._open_project(db_session, project)
        user = await create_user(db_session, email="gate-done@example.com", project_id=project.id)
        await create_survey(db_session, user, status="complete")

        response = await client.post(
            "/api/interview/opener", headers=auth_headers(user, test_settings)
        )
        assert response.status_code == 404
        assert "not configured" in response.json()["error"]["message"]

    async def test_admin_without_assessment_passes(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        project: Project,
        test_settings: Settings,
    ) -> None:
        await self._open_project(db_session, project)
        admin = await create_user(
            db_session, email="gate-admin@example.com", role="admin", project_id=project.id
        )

        response = await client.post(
            "/api/interview/opener", headers=auth_headers(admin, test_settings)
        )
        assert response.status_code == 404

    async def test_state_endpoint_is_not_gated(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        project: Project,
        test_settings: Settings,
    ) -> None:
        """A learner with an existing playbook but no assessment must still read it."""
        await self._open_project(db_session, project)
        user = await create_user(db_session, email="gate-me@example.com", project_id=project.id)

        response = await client.get("/api/interview/me", headers=auth_headers(user, test_settings))
        assert response.status_code == 404

    async def test_interview_chat_turn_is_gated(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        project: Project,
        test_settings: Settings,
    ) -> None:
        await self._open_project(db_session, project)
        user = await create_user(db_session, email="gate-chat@example.com", project_id=project.id)

        response = await client.post(
            "/api/chat/interview",
            json={"content": "hello"},
            headers=auth_headers(user, test_settings),
        )
        assert response.status_code == 403
        assert "Complete your assessment" in response.json()["error"]["message"]
```

- [ ] **Step 2: Run to verify they fail**

Integration tests need the DB (see "Running tests locally"). If the firewall is closed, skip to Step 3 and let CI run them. Otherwise run `uv run pytest tests/integration/test_routers/test_interview.py -v`.
Expected: the three 403 tests FAIL (they get 404); the three 404 tests PASS.

- [ ] **Step 3: Implement**

`backend/src/services/exceptions.py`, after `LessonNotAccessibleError`:

```python
class AssessmentRequiredError(DomainError):
    """The interview is briefed from the caller's completed assessment, so it needs one.
    A role check, unlike ComponentLockedError: admins are exempt so they can test the
    flow (spec 2026-09-26 A.3.5). user+ is NOT exempt. → 403"""

    def __init__(self) -> None:
        super().__init__("Complete your assessment before starting the interview")
```

`backend/src/main.py`: import `AssessmentRequiredError` with the other exceptions and add, next to `lesson_not_accessible_handler`:

```python
@app.exception_handler(AssessmentRequiredError)
async def assessment_required_handler(
    request: Request, exc: AssessmentRequiredError
) -> JSONResponse:
    return _error_response(403, exc.message)
```

`backend/src/core/dependencies/interview.py`: add `ChatKind` to the existing `from src.core.dependencies.chat import ...` line (that is where `chat.py` and `components.py` import it from), `from src.services.exceptions import AssessmentRequiredError`, add both names to `__all__`, and:

```python
_ASSESSMENT_EXEMPT_ROLES: tuple[str, ...] = ("admin",)


async def require_completed_assessment(
    user: Annotated[User, Depends(get_current_user)],
    surveys: Annotated[SurveyService, Depends(get_survey_service)],
) -> None:
    """The interview write paths need a COMPLETED assessment (a draft is not enough).
    Admins are exempt. Deliberately not on GET /api/interview/me, so a learner who
    already has a playbook can still read it."""
    if user.role in _ASSESSMENT_EXEMPT_ROLES:
        return
    if await surveys.survey_status(user.id) != "complete":
        raise AssessmentRequiredError


async def require_interview_assessment(
    kind: ChatKind,
    user: Annotated[User, Depends(get_current_user)],
    surveys: Annotated[SurveyService, Depends(get_survey_service)],
) -> None:
    """Chat-router twin of require_completed_assessment: applies to kind=interview only
    (same binding rule as require_chat_kind_unlocked)."""
    if kind == "interview":
        await require_completed_assessment(user, surveys)
```

`backend/src/routers/interview.py`: import `require_completed_assessment` and add `dependencies=[Depends(require_completed_assessment)]` to the `@router.post("/opener", ...)` and `@router.post("/playbook", ...)` decorators. Leave `/me` alone. Extend the "TWO gates" comment at the top to say there is a third gate on the two write routes and why `/me` is excluded.

`backend/src/routers/chat.py`: import `require_interview_assessment` from `src.core.dependencies.interview` and change the POST route's dependencies to `[Depends(require_chat_kind_unlocked), Depends(require_ai_surface), Depends(require_interview_assessment)]`.

- [ ] **Step 4: Run to verify they pass**

Run: `uv run pytest tests/unit -v && uv run poe lint-src && uv run poe ty-src` locally; the integration suite runs in CI on the PR.
Expected: unit tests PASS, lint and types clean; in CI, `TestAssessmentGate` passes and every existing `test_interview.py` / chat router test stays green.

- [ ] **Step 5: Commit**

```bash
git add backend/src/services/exceptions.py backend/src/main.py backend/src/core/dependencies/interview.py backend/src/routers/interview.py backend/src/routers/chat.py backend/tests/integration/test_routers/test_interview.py
git commit -m "feat(interview): require a completed assessment for learners; admins exempt"
```

---

### Task 6: Journey tile shows "Assessment first"

**Files:**
- Create: `frontend/src/lib/interviewAccess.ts`
- Create: `frontend/src/lib/interviewAccess.test.ts`
- Modify: `frontend/src/pages/JourneyHome.tsx` (interview branch of the state resolver, `resolveBadge`, badge constant)

**Interfaces:**
- Consumes: the 403 rule from Task 5 (mirrored, not called).
- Produces: `resolveInterviewTile(args: { componentLocked: boolean; role: Role | null; surveyStatus: SurveyStatus; interviewStatus: InterviewStatus }): InterviewTile` where `InterviewTile = 'locked' | 'needs_assessment' | 'available' | 'in_progress' | 'done'`.

- [ ] **Step 1: Write the failing test**

`frontend/src/lib/interviewAccess.test.ts`:

```ts
import { describe, expect, it } from 'vitest'
import { resolveInterviewTile } from './interviewAccess'

const base = {
  componentLocked: false,
  role: 'user' as const,
  surveyStatus: 'complete' as const,
  interviewStatus: 'not_started' as const,
}

describe('resolveInterviewTile', () => {
  it('a project-level lock wins over everything', () => {
    expect(resolveInterviewTile({ ...base, componentLocked: true, surveyStatus: 'not_started' })).toBe('locked')
  })

  it('a learner without a completed assessment must do it first', () => {
    expect(resolveInterviewTile({ ...base, surveyStatus: 'not_started' })).toBe('needs_assessment')
    expect(resolveInterviewTile({ ...base, surveyStatus: 'in_progress' })).toBe('needs_assessment')
  })

  it('user+ is not exempt, admin is', () => {
    expect(resolveInterviewTile({ ...base, role: 'user+', surveyStatus: 'not_started' })).toBe('needs_assessment')
    expect(resolveInterviewTile({ ...base, role: 'admin', surveyStatus: 'not_started' })).toBe('available')
  })

  it('an existing playbook stays reachable even without an assessment', () => {
    expect(resolveInterviewTile({ ...base, surveyStatus: 'not_started', interviewStatus: 'complete' })).toBe('done')
  })

  it('reflects interview progress once the assessment is done', () => {
    expect(resolveInterviewTile({ ...base, interviewStatus: 'in_progress' })).toBe('in_progress')
    expect(resolveInterviewTile(base)).toBe('available')
  })
})
```

- [ ] **Step 2: Run to verify it fails**

Run (from `frontend/`): `npm test -- interviewAccess`
Expected: FAIL, `Failed to resolve import "./interviewAccess"`.

- [ ] **Step 3: Implement**

`frontend/src/lib/interviewAccess.ts`:

```ts
import type { Role } from '../contexts/AuthContext'

export type SurveyStatus = 'not_started' | 'in_progress' | 'complete'
export type InterviewStatus = 'not_started' | 'in_progress' | 'complete'
export type InterviewTile = 'locked' | 'needs_assessment' | 'available' | 'in_progress' | 'done'

/** The journey tile for the interview. Mirrors the backend gates: the project-level
 *  component lock (ComponentLockedError) first, then require_completed_assessment
 *  (admins exempt, a draft assessment is not enough). A finished playbook stays
 *  reachable regardless, because GET /api/interview/me is not assessment-gated. */
export function resolveInterviewTile(args: {
  componentLocked: boolean
  role: Role | null
  surveyStatus: SurveyStatus
  interviewStatus: InterviewStatus
}): InterviewTile {
  const { componentLocked, role, surveyStatus, interviewStatus } = args
  if (componentLocked) return 'locked'
  if (interviewStatus === 'complete') return 'done'
  if (role !== 'admin' && surveyStatus !== 'complete') return 'needs_assessment'
  return interviewStatus === 'in_progress' ? 'in_progress' : 'available'
}
```

`frontend/src/pages/JourneyHome.tsx`:

1. Import: `import { resolveInterviewTile } from '../lib/interviewAccess'`, and take `role` from `useAuth()` next to `user` (`const { user, role } = useAuth()`).
2. Add a badge next to `BEING_BUILT_BADGE` (same colours as the Locked pill):

```ts
const ASSESSMENT_FIRST_BADGE: BadgeDef = { label: 'Assessment first', bg: '#F1EFEC', color: '#9A958F' }
```

3. Add state `const [interviewNeedsAssessment, setInterviewNeedsAssessment] = useState(false)`.
4. Replace the `mod.key === 'interview'` branch in the resolver with:

```ts
        } else if (mod.key === 'interview') {
          const tile = resolveInterviewTile({
            componentLocked: locked,
            role,
            surveyStatus: data.survey_status,
            interviewStatus: data.interview_status,
          })
          setInterviewNeedsAssessment(tile === 'needs_assessment')
          // every other InterviewTile value is already a ModuleState
          resolved[mod.key] = tile === 'needs_assessment' ? 'locked' : tile
```

5. Give `resolveBadge` a third parameter and return the new badge first:

```ts
function resolveBadge(
  key: ComponentKey,
  states: Record<ComponentKey, ModuleState>,
  interviewNeedsAssessment = false,
): BadgeDef {
  const state = states[key]
  if (key === 'interview' && state === 'locked' && interviewNeedsAssessment) {
    return ASSESSMENT_FIRST_BADGE
  }
  if (key === 'learning' && state === 'locked' && states['assessment'] === 'done') {
    return BEING_BUILT_BADGE
  }
  return BADGE[state] ?? BADGE.locked!
}
```

6. Pass `interviewNeedsAssessment` at **both** `resolveBadge(` call sites (`grep -n "resolveBadge(" frontend/src/pages/JourneyHome.tsx`; the doc comment says the stepper and the card both use it). If `role` is not in the effect's dependency list, add it next to `userId`.

- [ ] **Step 4: Run to verify**

Run (from `frontend/`): `npm test && npm run typecheck && npm run lint && npm run build`
Expected: all green.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/lib/interviewAccess.ts frontend/src/lib/interviewAccess.test.ts frontend/src/pages/JourneyHome.tsx
git commit -m "feat(frontend): interview tile says 'Assessment first' until the assessment is done"
```

---

### Task 7: Playbook prompt never guesses gender

**Files:**
- Modify: `backend/prompts/interview_playbook.md` (Evidence discipline section)
- Modify: `backend/tests/golden/ai/snapshots/interview_playbook.golden.txt` (regenerated, not hand-edited)

**Interfaces:** none.

- [ ] **Step 1: Edit the prompt**

In `backend/prompts/interview_playbook.md`, append this paragraph to the end of the `## Evidence discipline (both payloads)` section, straight after the sentence ending `("most of an afternoon a week", not "37%").`:

```markdown
PRONOUNS (both payloads): never guess the person's gender from their name or anything else.
Refer to {first_name} by name or as they/them. Use he/she only if the person stated their
pronouns in the transcript.
```

- [ ] **Step 2: Watch the golden test fail**

Run (from `backend/`): `uv run pytest tests/golden/ai -v`
Expected: FAIL on the playbook golden case (snapshot mismatch showing the three new lines, with `{first_name}` substituted).

- [ ] **Step 3: Regenerate and read the diff**

Run (PowerShell, from `backend/`): `$env:UPDATE_GOLDEN='1'; uv run pytest tests/golden/ai; Remove-Item Env:UPDATE_GOLDEN`
Then: `git diff backend/tests/golden/ai/snapshots/`
Expected: the only change is the new PRONOUNS paragraph in `interview_playbook.golden.txt`.

- [ ] **Step 4: Run the whole unit + golden set**

Run: `uv run pytest tests/unit tests/golden/ai -v`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/prompts/interview_playbook.md backend/tests/golden/ai/snapshots/interview_playbook.golden.txt
git commit -m "fix(prompts): the playbook never guesses a person's gender"
```

---

### Task 8: Docs, full checks, PR, deploy, prod check

**Files:**
- Modify: `CLAUDE.md` (the "Locking, prerequisites & preview (as-built)" section)
- Modify: `docs/superpowers/specs/2026-09-26-interviewer-evaluation-design.md` (status line)

- [ ] **Step 1: Document the new gate and the run stamps**

In `CLAUDE.md`, under the Component-level bullet of "Locking, prerequisites & preview (as-built)", add a sub-bullet:

```markdown
  - **Interview assessment gate (2026-09-26):** `require_completed_assessment`
    (`core/dependencies/interview.py`) on `POST /api/interview/opener`, `/playbook` and
    `POST /api/chat/interview`: learners need `survey_status == "complete"` (a draft does not
    count) ⇒ else 403 `AssessmentRequiredError`. A role check: `admin` exempt, `user+` not.
    `GET /api/interview/me` is deliberately ungated so an existing playbook stays readable.
    Frontend twin: `frontend/src/lib/interviewAccess.ts` ("Assessment first" tile).
```

and, wherever the interviewer is described (search `CLAUDE.md` and `backend/CLAUDE.md` for "interviewer"), one line: "Run stamps: assistant turns carry `model` + `prompt_version` in `messages.metadata`; playbooks carry `conversations.summary["meta"]` (model, both prompt versions, max_tokens, thinking, attempts, usage, generated_at). `prompt_version` = first 12 hex of SHA-256 of the shipped prompt file."

In the spec, change the **Status** line to: `accepted 2026-09-26; Tranche 1 shipped in PR #<n>.` (fill in the number after Step 3).

- [ ] **Step 2: Run the full CONTRIBUTING checks**

```powershell
cd .\backend;  uv run poe format-check; uv run poe lint-src; uv run poe ty-src; uv run poe test
cd ..\frontend; npm run typecheck; npm run lint; npm test; npm run build
```

Read each result separately (PowerShell 5.1 keeps going after a failure). With the firewall closed, `poe test` fails only in `tests/integration/` with connection timeouts, which isn't a code failure. Everything else must be green. Delete the copied `backend/.env` afterwards.

- [ ] **Step 3: Push and open the PR (with Aaron's go-ahead)**

```bash
git push -u origin HEAD
gh pr create --title "feat(interview): tranche 1 - run stamps, generation hardening, assessment gate" --body-file <prepared body>
```

The body covers what and why, links the spec and plan, and names the risk areas: auth gate (403 for learners without an assessment), prompt change (pronoun rule), and the learner-facing flow. Both required CI checks must be green. Read the Claude review and fix what is real. Merge with `gh pr merge --squash --delete-branch --admin`.

- [ ] **Step 4: Deploy and verify in production (with Aaron's go-ahead)**

GitHub → Actions → Deploy → Run workflow on `main`. Wait for the run to report `/api/health` on the new SHA. Then, in the browser:
1. As a learner without an assessment: the interview tile shows "Assessment first"; opening `/interview` and pressing Start shows "Complete your assessment before starting the interview".
2. As an admin (reset your own interview first via the admin panel): run a short interview to the Build offer, build the playbook, then read `GET /api/admin/interviews/<your id>` in the browser devtools. The `transcript` is unchanged, and the stored summary has a `meta` block. (The admin API doesn't expose `meta`. Checking it needs a read-only DB query, or add it to `AdminInterviewResponse` in Tranche 2 when the eval needs it.)
3. Ask for the playbook after 2 answers with no offer: expect the message "Answer a few more questions before building your playbook."

- [ ] **Step 5: Raise the out-of-scope issue**

Open one GitHub issue (label `security`) for the "second interview conversation via POST /api/chat/interview without conversation_id" finding in the "Found while planning" section above.
