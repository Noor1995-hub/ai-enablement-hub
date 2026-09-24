# Prompts git-only Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `backend/prompts/*.md` is the only thing that can change a system prompt; the admin page is read-only; every AI feature has a golden snapshot of what it sends the model.

**Architecture:** Remove the DB overlay end to end (cache writers, service write path, PUT/DELETE routes, startup priming, repository) while keeping the `prompts` table and model for rollback safety. The admin page keeps its master–detail layout but shows text + GitHub links. A golden harness drives each AI service with a recording fake LLM and compares a readable `.txt` rendering of every call against a committed snapshot.

**Tech Stack:** FastAPI / Pydantic / pytest (+pytest-asyncio, xdist) in `backend/`; React 18 + TS + TanStack Query in `frontend/`; `openapi-typescript`.

**Spec:** `docs/superpowers/specs/2026-09-23-prompts-git-only-design.md`

## Global Constraints

- **No migration, no table drop.** `backend/src/db/models/prompt.py` and the `prompts` table stay; do not touch `backend/alembic/versions/`.
- **Never start the backend dev server** (`poe dev`) — its lifespan connects to the live DB and its cleanup loop deletes expired sessions. API types are regenerated from `app.openapi()` (Task 5).
- Never write to the live database; integration tests use the test DB via the existing fixtures.
- Backend checks: `uv run poe format-check`, `uv run poe lint-src`, `uv run poe test` (from `backend/`). Frontend: `npm run typecheck`, `npm run lint`, `npm run build` (from `frontend/`).
- Golden fixtures are fictional — no real learner names, emails or company data.
- FastAPI signature gotcha (CLAUDE.md #4): types used in router/DI parameter annotations are runtime imports.
- Branch `feat/prompts-git-only`; one PR at the end; `--title "feat: prompts are git-only; read-only System Prompts page; golden cases per AI feature"`.

## Review Focus

1. **A stale in-process cache after the change.** Nothing may write `_CACHE` except `load_prompt`'s own first read. Expected: `set_cache`/`reset_cache` no longer exist; grep proves no caller. Pinned by Task 1's seam test (`hasattr` checks).
2. **Old clients calling PUT/DELETE** (a browser tab open on the old page across the deploy). Expected: 405, not 500, not a silent write. Pinned by Task 1's integration test.
3. **Non-deterministic golden output** (dates, UUIDs, dict order, `now()` in a briefing). Expected: two consecutive runs are byte-identical. Pinned by Task 2's `test_golden_is_deterministic` pattern applied in every golden task (run the render twice, compare).
4. **A snapshot silently regenerated in CI.** Expected: `UPDATE_GOLDEN` is only honoured locally; with it unset a missing/different snapshot fails. Pinned by Task 2's harness test.
5. **`build_sha` absent or `dev` on the page.** Expected: the "View live version" link falls back to `main`, never renders `undefined`. Pinned by Task 5's stubbed-fetch render check.

---

### Task 1: Backend — file-only prompts, read-only API

**Files:**
- Modify: `backend/src/services/prompts.py`, `backend/src/services/prompt_service.py`, `backend/src/schemas/prompt.py`, `backend/src/routers/admin_prompts.py`, `backend/src/core/dependencies/prompt.py`, `backend/src/main.py`, `backend/src/db/models/prompt.py` (docstring only)
- Delete: `backend/src/repositories/prompt_repository.py`
- Tests: `backend/tests/unit/test_prompt_seam.py`, `backend/tests/unit/test_prompt_service.py` (rewrite), `backend/tests/unit/test_prompt_integrity.py` (new), `backend/tests/integration/test_routers/test_admin_prompts.py` (rewrite)

**Interfaces:**
- Produces: `PromptService()` (no args) with sync `list_all() -> list[PromptSummary]`, `get(kind: str) -> PromptDetail`; `prompt_path(kind: str) -> str` returning `backend/prompts/<kind>.md`; `PromptSummary{kind,label,group,path}`, `PromptDetail{kind,label,content,path}`; `prompts.load_prompt`, `prompts.read_file`, `prompts.clear_cache` only.

- [x] **Step 1: Write the failing tests**

`backend/tests/unit/test_prompt_seam.py` — replace the file:

```python
import pytest

from src.services import prompts as P


@pytest.fixture(autouse=True)
def _clear():
    P.clear_cache()
    yield
    P.clear_cache()


def test_load_prompt_reads_file_by_default():
    assert P.load_prompt("interview").startswith("You are the AI Opportunity Interviewer")


def test_load_prompt_equals_the_shipped_file():
    assert P.load_prompt("chatbot") == P.read_file("chatbot")


def test_the_cache_cannot_be_written_from_outside():
    # Git is the only source of truth (2026-09-23): no override path may exist.
    assert not hasattr(P, "set_cache")
    assert not hasattr(P, "reset_cache")
```

`backend/tests/unit/test_prompt_service.py` — replace the file:

```python
from pathlib import Path

import pytest

from src.services.exceptions import NotFoundError
from src.services.prompt_service import KNOWN_PROMPTS, PromptService, prompt_path

REPO_ROOT = Path(__file__).resolve().parents[3]


def test_list_all_returns_every_known_kind_with_its_path():
    summaries = PromptService().list_all()
    assert [s.kind for s in summaries] == [m.kind for m in KNOWN_PROMPTS]
    for s in summaries:
        assert s.path == f"backend/prompts/{s.kind}.md"
        assert (REPO_ROOT / s.path).is_file()


def test_get_returns_the_file_content():
    detail = PromptService().get("interview")
    assert detail.content == (REPO_ROOT / "backend/prompts/interview.md").read_text(
        encoding="utf-8"
    ).strip()
    assert detail.path == prompt_path("interview")
    assert detail.label == "Interview — conversation"


def test_get_unknown_kind_is_not_found():
    with pytest.raises(NotFoundError):
        PromptService().get("does_not_exist")


def test_the_service_has_no_write_path():
    for name in ("update", "reset", "refresh_cache"):
        assert not hasattr(PromptService, name)
```

`backend/tests/unit/test_prompt_integrity.py` — new:

```python
"""What the admin editor used to check on save now runs in CI on every PR."""

import pytest

from src.services import prompts as P
from src.services.prompt_service import KNOWN_PROMPTS, REQUIRED_TOKENS


@pytest.mark.parametrize("kind", [m.kind for m in KNOWN_PROMPTS])
def test_every_known_prompt_has_a_non_empty_file(kind: str) -> None:
    assert P.read_file(kind)


@pytest.mark.parametrize(
    ("kind", "token"), [(k, t) for k, tokens in REQUIRED_TOKENS.items() for t in tokens]
)
def test_required_tokens_are_present(kind: str, token: str) -> None:
    assert token in P.read_file(kind), f"{kind}.md lost required placeholder {token}"
```

`backend/tests/integration/test_routers/test_admin_prompts.py` — rewrite keeping the file's existing imports/fixtures for `client`, `admin_headers`, `auth_headers`, `create_user`, `test_settings` (read the current file first and keep its fixture definitions; delete the `_clear_prompt_cache` autouse fixture's DB/cache-override parts if any, keeping only `P.clear_cache()`). The test classes become:

```python
class TestList:
    async def test_list_as_admin_contains_all_nine_kinds(self, client, admin_headers):
        response = await client.get("/api/admin/prompts", headers=admin_headers)
        assert response.status_code == 200
        prompts = response.json()["prompts"]
        assert len(prompts) == 9
        assert {p["path"] for p in prompts} == {f"backend/prompts/{p['kind']}.md" for p in prompts}
        assert "source" not in prompts[0]

    async def test_non_admin_is_403(self, client, db_session, test_settings):
        user = await create_user(db_session)
        response = await client.get("/api/admin/prompts", headers=auth_headers(user, test_settings))
        assert response.status_code == 403


class TestDetail:
    async def test_detail_returns_file_content(self, client, admin_headers):
        response = await client.get("/api/admin/prompts/interview", headers=admin_headers)
        assert response.status_code == 200
        body = response.json()
        assert body["content"].startswith("You are the AI Opportunity Interviewer")
        assert body["path"] == "backend/prompts/interview.md"

    async def test_unknown_kind_is_404(self, client, admin_headers):
        response = await client.get("/api/admin/prompts/does_not_exist", headers=admin_headers)
        assert response.status_code == 404


class TestNoWritePath:
    async def test_put_is_405(self, client, admin_headers):
        response = await client.put(
            "/api/admin/prompts/interview", json={"content": "x"}, headers=admin_headers
        )
        assert response.status_code == 405

    async def test_delete_is_405(self, client, admin_headers):
        response = await client.delete("/api/admin/prompts/interview", headers=admin_headers)
        assert response.status_code == 405
```

(Use the fixture names the current file actually uses — e.g. if the session fixture is not `db_session`, use its real name. Adapt, don't invent.)

- [x] **Step 2: Run them to verify they fail**

Run (from `backend/`): `uv run pytest tests/unit/test_prompt_seam.py tests/unit/test_prompt_service.py tests/unit/test_prompt_integrity.py tests/integration/test_routers/test_admin_prompts.py -q -p no:randomly`
Expected: FAIL — `ImportError: cannot import name 'prompt_path'`, `hasattr` asserts, PUT returns 200 not 405. (`test_prompt_integrity.py` may already pass: it tests files, not code — that is fine; note it.)

- [x] **Step 3: Implement**

`backend/src/services/prompts.py`:

```python
from __future__ import annotations

from pathlib import Path

__all__ = ["load_prompt", "read_file", "clear_cache"]

_PROMPTS_DIR = Path(__file__).resolve().parents[2] / "prompts"
_CACHE: dict[str, str] = {}


def read_file(kind: str) -> str:
    """The shipped prompt for `kind` — `backend/prompts/<kind>.md`."""
    return (_PROMPTS_DIR / f"{kind}.md").read_text(encoding="utf-8").strip()


def load_prompt(kind: str) -> str:
    """The active prompt. Git is the only source of truth (2026-09-23): this is always the
    shipped file, read once per process and cached."""
    cached = _CACHE.get(kind)
    if cached is not None:
        return cached
    text = read_file(kind)
    _CACHE[kind] = text
    return text


def clear_cache() -> None:
    _CACHE.clear()
```

`backend/src/services/prompt_service.py` — keep `PromptMeta`, `KNOWN_PROMPTS`, `REQUIRED_TOKENS`, `_META_BY_KIND` exactly as they are; replace the rest:

```python
from __future__ import annotations

from dataclasses import dataclass

from src.schemas.prompt import PromptDetail, PromptSummary
from src.services import prompts as P
from src.services.exceptions import NotFoundError

__all__ = ["KNOWN_PROMPTS", "REQUIRED_TOKENS", "PromptMeta", "PromptService", "prompt_path"]

# ... PromptMeta, KNOWN_PROMPTS, REQUIRED_TOKENS, _META_BY_KIND unchanged ...


def prompt_path(kind: str) -> str:
    """Repo-relative path of the file that is the prompt's only source of truth."""
    return f"backend/prompts/{kind}.md"


class PromptService:
    """Read-only view of the shipped prompt files for the admin System Prompts page.
    Git is the only source of truth (2026-09-23, spec 2026-09-23-prompts-git-only):
    a prompt changes by pull request and ships with the next deploy."""

    def list_all(self) -> list[PromptSummary]:
        return [
            PromptSummary(kind=m.kind, label=m.label, group=m.group, path=prompt_path(m.kind))
            for m in KNOWN_PROMPTS
        ]

    def get(self, kind: str) -> PromptDetail:
        meta = _META_BY_KIND.get(kind)
        if meta is None:
            raise NotFoundError("Prompt")
        return PromptDetail(
            kind=meta.kind, label=meta.label, content=P.read_file(kind), path=prompt_path(kind)
        )
```

`backend/src/schemas/prompt.py`:

```python
from __future__ import annotations

from pydantic import BaseModel

__all__ = ["PromptDetail", "PromptListResponse", "PromptSummary"]


class PromptSummary(BaseModel):
    kind: str
    label: str
    group: str
    path: str  # repo-relative, e.g. backend/prompts/interview.md


class PromptDetail(BaseModel):
    kind: str
    label: str
    content: str
    path: str


class PromptListResponse(BaseModel):
    prompts: list[PromptSummary]
```

`backend/src/routers/admin_prompts.py`:

```python
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from src.core.dependencies.auth import require_admin
from src.core.dependencies.prompt import get_prompt_service
from src.schemas.prompt import PromptDetail, PromptListResponse
from src.services.prompt_service import PromptService

__all__ = ["router"]

router = APIRouter(
    prefix="/api/admin/prompts", tags=["admin-prompts"], dependencies=[Depends(require_admin)]
)

PromptServiceDep = Annotated[PromptService, Depends(get_prompt_service)]


@router.get("", response_model=PromptListResponse)
async def list_prompts(service: PromptServiceDep) -> PromptListResponse:
    """Every known prompt kind with the repo path of its file (the only source of truth)."""
    return PromptListResponse(prompts=service.list_all())


@router.get("/{kind}", response_model=PromptDetail)
async def get_prompt(kind: str, service: PromptServiceDep) -> PromptDetail:
    """Unknown kind -> global 404 handler (NotFoundError). There is no write route:
    prompts change by pull request (2026-09-23)."""
    return service.get(kind)
```

`backend/src/core/dependencies/prompt.py`:

```python
"""DI provider for PromptService (read-only admin System Prompts page)."""

from __future__ import annotations

from src.services.prompt_service import PromptService

__all__ = ["get_prompt_service"]


def get_prompt_service() -> PromptService:
    return PromptService()
```

`backend/src/main.py`: delete the two lines

```python
    async with AsyncSession(engine, expire_on_commit=False) as session:
        await PromptService(PromptRepository(session)).refresh_cache()
```

and the now-unused imports `from src.repositories.prompt_repository import PromptRepository` and `from src.services.prompt_service import PromptService` (keep `AsyncSession` — it is used elsewhere in the file).

`backend/src/db/models/prompt.py`: add to the class docstring (or a module comment if none):
`Retired 2026-09-23 (prompts are git-only; nothing reads or writes this table). Kept for rollback safety; dropped by a July phase-C migration.`

Delete `backend/src/repositories/prompt_repository.py`. Then `grep -rn "prompt_repository\|PromptRepository\|set_cache\|reset_cache\|refresh_cache\|PromptUpdateRequest" backend/src backend/tests` must return nothing (fix any stragglers, e.g. a repositories `__init__` export).

- [x] **Step 4: Run the tests — expect PASS**

Run: the Step 2 command. Expected: all pass.

- [x] **Step 5: Full backend checks**

Run (from `backend/`): `uv run poe format` then `uv run poe format-check; uv run poe lint-src; uv run poe test > /tmp/t1.log 2>&1; tail -5 /tmp/t1.log`
Expected: format clean, lint "All checks passed!", tests all pass (rerun once if the shared test DB flakes). Coverage must not drop below the current level noticeably.

- [x] **Step 6: Commit**

```bash
git add -A backend/src backend/tests
git commit -m "feat(prompts): git is the only source of truth; read-only admin API"
```

### Task 2: Golden harness + the feedback-triage snapshot

**Files:**
- Create: `backend/tests/golden/ai/__init__.py` (empty), `backend/tests/golden/ai/harness.py`, `backend/tests/golden/ai/test_harness.py`, `backend/tests/golden/ai/test_feedback_triage_golden.py`, `backend/tests/golden/ai/snapshots/feedback_triage.golden.txt` (generated)
- Check: `backend/tests/golden/` has no `__init__.py` today — if the other golden tests import as a package, mirror whatever makes pytest collect them (look at `tests/golden/test_*.py` headers); do not break their collection.

**Interfaces:**
- Produces: `RecordingLlm(structured_results: list[dict] | None = None, chunks: list[str] | None = None)` implementing `LlmClient`, with `.calls: list[dict]`; `render_calls(calls: list[dict]) -> str`; `assert_golden(name: str, calls: list[dict]) -> None`. Tasks 3–4 use exactly these.

- [x] **Step 1: Write the harness test (failing)**

`backend/tests/golden/ai/test_harness.py`:

```python
import pytest

from src.services.llm_service import StructuredSchema
from tests.golden.ai import harness
from tests.golden.ai.harness import RecordingLlm, assert_golden, render_calls


async def test_recording_llm_records_both_call_shapes():
    llm = RecordingLlm(structured_results=[{"a": 1}], chunks=["hi"])
    async with llm.stream_reply(system="S", messages=[{"role": "user", "content": "u"}], max_tokens=5) as s:
        assert [c async for c in s] == ["hi"]
    schema = StructuredSchema(name="tool", description="d", input_schema={"type": "object"})
    out, _ = await llm.complete_structured(system="S2", prompt="P", schema=schema, max_tokens=7)
    assert out == {"a": 1}
    assert [c["method"] for c in llm.calls] == ["stream_reply", "complete_structured"]


def test_render_is_readable_and_stable():
    calls = [
        {"method": "stream_reply", "system": "line1\nline2", "messages": [{"role": "user", "content": "hello"}], "max_tokens": 5},
    ]
    text = render_calls(calls)
    assert "=== call 1: stream_reply (max_tokens=5) ===" in text
    assert "--- system ---\nline1\nline2\n" in text
    assert "--- message 1 (user) ---\nhello\n" in text
    assert render_calls(calls) == text


def test_missing_snapshot_fails_with_instructions(tmp_path, monkeypatch):
    monkeypatch.setattr(harness, "SNAPSHOT_DIR", tmp_path)
    monkeypatch.delenv("UPDATE_GOLDEN", raising=False)
    with pytest.raises(AssertionError, match="UPDATE_GOLDEN=1"):
        assert_golden("nope", [])


def test_update_golden_writes_then_plain_run_passes(tmp_path, monkeypatch):
    monkeypatch.setattr(harness, "SNAPSHOT_DIR", tmp_path)
    calls = [{"method": "stream_reply", "system": "S", "messages": [], "max_tokens": 1}]
    monkeypatch.setenv("UPDATE_GOLDEN", "1")
    assert_golden("x", calls)
    monkeypatch.delenv("UPDATE_GOLDEN")
    assert_golden("x", calls)
    calls[0]["system"] = "changed"
    with pytest.raises(AssertionError):
        assert_golden("x", calls)


def test_update_golden_is_ignored_in_ci(tmp_path, monkeypatch):
    monkeypatch.setattr(harness, "SNAPSHOT_DIR", tmp_path)
    monkeypatch.setenv("UPDATE_GOLDEN", "1")
    monkeypatch.setenv("CI", "true")
    with pytest.raises(AssertionError):
        assert_golden("never-written", [])
```

- [x] **Step 2: Run — expect FAIL** (`ModuleNotFoundError: tests.golden.ai.harness`).

Run: `uv run pytest tests/golden/ai -q -p no:randomly`

- [x] **Step 3: Implement `harness.py`**

```python
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
            {"method": "stream_reply", "system": system,
             "messages": [dict(m) for m in messages], "max_tokens": max_tokens}
        )
        return FakeLlmReplyStream(self._chunks, _USAGE)

    async def complete_structured(
        self, *, system: str, prompt: str, schema: StructuredSchema, max_tokens: int
    ) -> tuple[dict[str, Any], LlmUsage]:
        self.calls.append(
            {"method": "complete_structured", "system": system, "prompt": prompt,
             "schema": {"name": schema.name, "description": schema.description,
                        "input_schema": schema.input_schema},
             "max_tokens": max_tokens}
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
            f"UPDATE_GOLDEN=1 uv run pytest {Path(__file__).parent.name} and read it before committing."
        )
    expected = path.read_text(encoding="utf-8")
    if actual != expected:
        diff = "".join(difflib.unified_diff(
            expected.splitlines(keepends=True), actual.splitlines(keepends=True),
            fromfile=f"{path.name} (committed)", tofile=f"{path.name} (now)"))
        raise AssertionError(
            f"What the {name!r} feature sends the model changed:\n{diff}\n"
            "If intended, regenerate with UPDATE_GOLDEN=1 and commit the snapshot with the change."
        )
```

- [x] **Step 4: Run the harness tests — expect PASS.**

- [x] **Step 5: Feedback-triage golden (failing first)**

`test_feedback_triage_golden.py`: build the service exactly as `tests/unit/test_feedback_triage_service.py::test_prompt_carries_the_lesson_and_the_feedback` does (its `_row` / `_repo` helpers — copy them, don't import from another test module), with **fictional fixed values**: lesson title `"Prompting basics"`, feedback message `"Please add a worked example"`, fixed UUIDs (`uuid.UUID(int=1)` style) and any timestamps fixed. Use `RecordingLlm(structured_results=[{"suggested_status": "accepted", "rationale": "Actionable."}])`. Call `await service.suggest(limit=5)`, then:

```python
    assert_golden("feedback_triage", llm.calls)
    # determinism (Review Focus 3): a second identical run renders identically
    assert render_calls(llm.calls) == render_calls(second_run_llm.calls)
```

Run without the snapshot → FAIL with "No golden snapshot … UPDATE_GOLDEN=1". Then `UPDATE_GOLDEN=1 uv run pytest tests/golden/ai/test_feedback_triage_golden.py -q`, **open the `.golden.txt` and read it** (it must show the real `feedback_triage.md` system prompt, the lesson and the feedback), then run plainly → PASS.

- [x] **Step 6: Commit** — `git add backend/tests/golden/ai && git commit -m "test(golden): harness for AI-feature golden cases + feedback triage"`

### Task 3: Golden cases — chat surfaces and interviewer

**Files:** Create `backend/tests/golden/ai/test_chat_golden.py`, `backend/tests/golden/ai/test_interview_golden.py`, snapshots `chatbot`, `assessment`, `lesson`, `interview`, `interview_playbook`.

**Interfaces:** Consumes Task 2's `RecordingLlm`, `assert_golden`, `render_calls`.

- [x] **Step 1: Chat (3 snapshots).** Construct `ChatService` as `tests/unit/test_chat_service.py` does (reuse its fake repositories by copying the minimal helpers). For each conversation kind `chatbot`, `assessment`, `lesson`: a fixed fictional conversation with one prior assistant turn and one new user message; drive the service method that streams a reply; consume the stream; `assert_golden(kind, llm.calls)` with `RecordingLlm(chunks=["ok"])`. If a kind injects context (e.g. lesson content), feed a fixed fictional lesson.
- [x] **Step 2: Interview (2 snapshots).** Construct `InterviewService` as `tests/unit/test_interview_service.py` does. `interview`: one conversation turn — the system must include the briefing (`build_briefing`) built from a fixed fictional user (first name `"Alex"`), fixed assessment results and fixed company context. `interview_playbook`: the playbook generation call — all four tokens (`{first_name}`, `{assessment_json}`, `{company_context}`, `{transcript}`) substituted with fixed values; assert in the test that none of the four literal tokens remain in the recorded system/prompt.
- [x] **Step 3:** Each test: run → FAIL (no snapshot); `UPDATE_GOLDEN=1` → generate; **read each snapshot**; plain run → PASS; determinism check as in Task 2 (freeze any clock with the same technique the unit tests use, or pass fixed datetimes).
- [x] **Step 4:** `uv run poe format; uv run poe lint-src; uv run pytest tests/golden -q` → pass. Commit `test(golden): chat surfaces + interviewer golden cases`.

### Task 4: Golden cases — content improvement

**Files:** Create `backend/tests/golden/ai/test_content_improvement_golden.py`, snapshots `content_improvement`, `content_improvement_critique`.

**Interfaces:** Consumes Task 2's harness.

- [x] **Step 1:** Construct `ContentImprovementService` as `tests/unit/test_content_improvement_service.py` / `test_content_improvement_critique.py` do. `content_improvement`: the drafting call for one fixed fictional lesson (a few `content_blocks` with nested ids) + one accepted feedback item + two fixed calibration notes; the recorded system must contain the house style, the drafting prompt and both notes. `content_improvement_critique`: the critique call over a fixed draft.
- [x] **Step 2:** fail → `UPDATE_GOLDEN=1` → read → pass; determinism check.
- [x] **Step 3:** checks as Task 3 Step 4. Commit `test(golden): content-improvement golden cases`.

### Task 5: Frontend — read-only System Prompts page

**Files:** Modify `frontend/src/pages/admin2/PromptsPage.tsx`, `frontend/src/pages/admin2/api.ts`, `frontend/src/types/domain.ts` (prompt types), `frontend/src/api/schema.d.ts` (regenerated), `frontend/src/styles/admin.css` only if a class is needed for the text block.

**Interfaces:** Consumes Task 1's `PromptSummary{kind,label,group,path}`, `PromptDetail{kind,label,content,path}`.

- [x] **Step 1: Regenerate API types without a server.** From `backend/`:
  `uv run python -c "import json; from src.main import app; open('../frontend/openapi.tmp.json','w',encoding='utf-8').write(json.dumps(app.openapi()))"` then from `frontend/`: `npx openapi-typescript openapi.tmp.json -o src/api/schema.d.ts` and delete `openapi.tmp.json`. `git diff --stat src/api/schema.d.ts` must show only prompt-related changes (if unrelated drift appears, that is pre-existing drift — keep it, and note it in the PR).
- [x] **Step 2: Types + hooks.** `domain.ts`: `PromptSummary`/`PromptDetail` follow the schema (drop `source`, `updated_at`, `required_tokens`; add `path`). `api.ts`: delete `useUpdatePrompt` and `useResetPrompt` and their fetchers; keep `usePrompts`/`usePrompt`.
- [x] **Step 3: Page.** In `PromptsPage.tsx`: remove the Edited/Default chip, `sourceTone`/`sourceLabel`, the editor state, textarea, Save/Reset, `window.confirm`, required-token hint. The right pane shows the label, then a read-only block `<pre className="adm-prompt-text">{data.content}</pre>` (monospace, `white-space: pre-wrap`, scrollable, max-height ~70vh), then:

  ```tsx
  <p className="adm-muted">
    Source of truth: <code>{data.path}</code> in git. Change it with a pull request, then deploy.{' '}
    <a href={liveUrl} target="_blank" rel="noreferrer">View live version</a>{' · '}
    <a href={`${REPO}/edit/main/${data.path}`} target="_blank" rel="noreferrer">Edit on GitHub</a>
  </p>
  ```

  with `const REPO = 'https://github.com/DLW-INT-BTA-BELUX/ai-enablement-hub'` and
  `liveUrl = sha && sha !== 'dev' ? \`${REPO}/blob/${sha}/${data.path}\` : \`${REPO}/blob/main/${data.path}\``, where `sha` comes from the same health query hook `SetupPage.tsx` uses (import it; do not add a new fetch). Update the file's doc comment: read-only since 2026-09-23, git is the source of truth.
- [x] **Step 4: Checks.** `npm run typecheck; npm run lint; npm run build` → all green.
- [x] **Step 5: Render check (Review Focus 5)** per CLAUDE.md "Verifying without touching live data": Playwright with `addInitScript` stubbing `window.fetch` for `/api/admin/prompts`, `/api/admin/prompts/interview`, `/api/health` (two variants: `build_sha` = a 40-char sha, and `"dev"`) and whatever auth/me endpoint the admin shell needs, against the Vite dev server (`npm run dev`, frontend only — **no backend**). Assert: no `textarea`, no Save/Reset buttons; the `pre` contains the stubbed text; "View live version" href is `…/blob/<sha>/backend/prompts/interview.md`, and `…/blob/main/…` in the `dev` variant; "Edit on GitHub" href is `…/edit/main/backend/prompts/interview.md`. If driving the authenticated admin shell with stubs proves impractical, record that as a ruling and rely on typecheck + a unit-level reading of `liveUrl`.
- [x] **Step 6: Commit** `feat(admin): read-only System Prompts page with links to git`.

### Task 6: Hooks and docs

**Files:** Modify `.claude/hooks/prod_asset_nudge.py`, `backend/tests/unit/test_claude_hooks.py`, `CLAUDE.md`, `docs/README.md`, `CONTRIBUTING.md`.

- [x] **Step 1 (failing test):** in `test_claude_hooks.py`, change the prompts case's expected fragment from `"production asset"` to `"UPDATE_GOLDEN=1"`, and add a test asserting `"DB override" not in` the prompts message. Run → FAIL.
- [x] **Step 2:** `prod_asset_nudge.py` prompts rule text becomes:
  `"is a production asset baked into the Docker image, and git is its only source of truth: it ships with the next deploy. Regenerate the golden snapshots (UPDATE_GOLDEN=1 uv run pytest tests/golden/ai) and read their diff before calling this done."` Run → PASS.
- [x] **Step 3: CLAUDE.md** — replace each DB-overridable/admin-editable prompt mention:
  - Repo map `backend/prompts/` line: "…loaded by `services/prompts.py`; git is the only source of truth (read-only System Prompts page since 2026-09-23). Treat edits as production changes. Never move/rename."
  - Feature index "System prompts, DB-overridable + admin-editable" → "**System prompts — git-only** (2026-09-23): `backend/prompts/*.md`, read-only admin page `admin2/PromptsPage.tsx`, golden cases in `backend/tests/golden/ai/` — `2026-09-23-prompts-git-only-design.md` (supersedes the editor half of `2026-07-29-prompt-editor-design.md`). The `prompts` table is retired, dropped in phase C."
  - Admin panel feature list "System Prompts" stays as a page name.
  - Grep afterwards: `grep -n -i "overrid" CLAUDE.md` — no prompt-override claims remain.
- [x] **Step 4: docs/README.md** "Not docs" paragraph: replace "(DB-overridable via the admin System Prompts page)" with "(git is their only source of truth; the admin System Prompts page is read-only)".
- [x] **Step 5: CONTRIBUTING.md** — under "Claude review", add a bullet: "**Prompt changes** (`backend/prompts/`) are ordinary PRs: regenerate the golden snapshots with `UPDATE_GOLDEN=1 uv run pytest tests/golden/ai`, read the diff, commit it with the change. They go live with the next deploy."
- [x] **Step 6:** `uv run pytest tests/unit/test_claude_hooks.py -q` → pass. Commit `docs: prompts are git-only; nudge hook + CLAUDE.md follow`.

### Task 7: PR, review, merge

- [x] **Step 1:** Push; `gh pr create --title "feat: prompts are git-only; read-only System Prompts page; golden cases per AI feature" --body-file <body>` — body: what & why, the census result (0 overrides), "no migration; `prompts` table retired, dropped in phase C", **deploy note: re-check /admin/prompts shows no Edited chip immediately before pressing Deploy**, checklist, attribution line.
- [x] **Step 2:** Wait for `backend`, `frontend` (required) and `claude-review`. Read every Claude finding; fix real ones (TDD) or reply why not.
- [x] **Step 3:** `gh pr merge --squash --delete-branch --admin`; `git fetch && git reset --hard origin/main`.
- [x] **Step 4:** Execution record appended to this plan in a small docs PR (ticked boxes, rulings, the Claude review outcome).

## Execution record (2026-09-23/24)

Subagent-driven: 6 build tasks, each implemented by a fresh Sonnet agent and reviewed by a fresh
reviewer (all approved); final whole-branch review on Opus; one fix wave, re-reviewed. Merged as
**PR #16, squash `f84fded`** (2026-09-24). **Not deployed yet** — see CLAUDE.md "Current state".

- **Live census before building:** production `prompts` table had **0 rows** (read-only `SELECT`), so
  step 1 of the spec (fold overrides into files) was skipped.
- **Final review Critical, fixed (`c672661`):** `test_update_golden_writes_then_plain_run_passes`
  failed under GitHub's `CI=true` (the harness correctly ignores `UPDATE_GOLDEN` in CI, but its own
  self-test never cleared `CI`). Reproduced with `CI=true`, fixed with `monkeypatch.delenv("CI")`.
- **Claude PR review ($5.85, 26 turns):** one valid finding — the July phase-C task C8 still hardened
  the `prompts` table and the master plan assumed the override. Fixed in `425ab06`: C8 now drops the
  table; the master's notes are marked superseded/resolved.
- **Rulings:** the `lesson` snapshot drives `kind="lesson"` with no lesson context (no injection path
  exists in code; `lesson.md` is a placeholder) — regenerate it when lesson context ships.
  `{company_context}` is hardcoded `""` in `InterviewService.build_playbook` today; the snapshot
  reflects that. `types/domain.ts` needed only a comment change (types alias the generated schema).
- **Deferred minors:** `get_prompt` is `async` doing a sync file read; the harness CI guard is
  presence-based; duplicated transcript rows in the playbook golden; the three chat goldens could be
  one parametrized test; "from `backend/`" regenerate hint lives in three places.
- Suite at merge: 1555 backend tests passed; frontend typecheck/lint/build green.

