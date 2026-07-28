# Feedback-Driven Content Improvement — Plan E: Curate and Inject Learn Cards

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the loop. The agent already suggests calibration notes when an admin edits its draft; this plan lets an admin approve the good ones and injects approved notes into the drafting prompt so future drafts improve.

**Architecture:** No migration — Plan D's `calibration_notes` table already carries the full `suggested|approved|rejected|retired` lifecycle. This is repository reads plus a service, a router, a pure prompt-composition module, and one admin screen. The injected block is bounded (8 notes, 1500 chars) and ordered by recency of approval; with nothing approved the composed system prompt is **byte-identical to today**.

**Tech Stack:** FastAPI (Python 3.13, uv, async SQLAlchemy 2.0), React 18 + TypeScript (Vite, TanStack Query), pytest, ruff + ty via `poe`.

## Global Constraints

- Backend conventions are MANDATORY: `python-be-architecture.md` (router → service → repository → model; services take ABSTRACT repositories; **services never call other services**; DI in `core/dependencies/`; `from __future__ import annotations`; `__all__`; full type annotations).
- **FastAPI signature gotcha (CLAUDE.md, load-bearing):** any type in a *parameter* annotation FastAPI inspects — routers and `core/dependencies/` providers — must be imported at RUNTIME, never under `if TYPE_CHECKING`. An unresolvable name silently degrades the parameter into a required query param, surfacing as uniform 422s.
- Backend checks, run **inside `backend/`**: `uv run poe format && uv run poe lint && uv run poe test`, plus `uv run poe ty`. Pre-existing baseline: **~48 ruff findings in `backend/scripts/` and exactly 23 ty diagnostics.** `poe lint` is red before you start. Confirm you added none (`ruff check <file>` per touched file) and that ty ends at exactly 23.
- Frontend checks, run **inside `frontend/`**: `npm run typecheck && npm run lint && npm run build`. A single `react-refresh/only-export-components` warning on `ProposalDiff.tsx` is the known baseline.
- **Everything in the FOREGROUND.** No `run_in_background`, no Monitor. `uv run poe test` takes ~3 min; pass `timeout: 600000` and wait. Several implementers on the previous plan stalled by backgrounding it.
- Focused pytest runs use `-n0`. **Never `-p no:xdist`** — this repo's `tests/conftest.py` defines a `pytest_xdist_auto_num_workers` hookimpl, so unloading the plugin raises `PluginValidationError`.
- `poe test` hits the shared `ai-enablement-hub-test` Azure PG database and is occasionally flaky under load; failures in the media/org/reminder/users routers on a first run are the known flake — **re-run once**.
- **STOP AND ASK before any Azure-mutating command.** No `alembic upgrade`/`downgrade`, no `poe upgrade`, no `deploy.ps1`, no `npm run gen:api` (it starts a dev server whose startup fires a cleanup DELETE against the real Azure dev DB), no real Anthropic call.
- Branch: `feature/feedback-content-improvement-e`, cut from `main` @ `ac2eda3`. Commit only the files each task lists (`git add <path>`), **never `git add -A`** — the tree carries an untracked `.claude/` and `scratch_review/`.
- **There is NO migration in this plan.** The `calibration_notes` table, its four statuses and its `reviewed_at`/`reviewed_by` columns all shipped with Plan D. If you find yourself writing one, stop — something has been misunderstood.

## The two properties that define this plan

1. **With zero approved notes, the composed system prompt must be byte-identical to today's.** Every existing test that asserts on the drafting prompt keeps passing verbatim, and the drafting behaviour cannot drift just because this plan landed. This is the regression guard.
2. **An approved note is guidance, never a gate.** `check_house_style` enforces a fixed set of rules in code; a free-text note cannot be enforced that way and must never be presented as if it could. The injected block says so every time, and the review UI repeats it.

## Primitives already on `main`

- `backend/src/db/models/calibration_note.py` — `CalibrationNote` with `id`, `source_proposal_id` (nullable, ON DELETE SET NULL), `note`, `status` (CHECK `suggested|approved|rejected|retired`), `created_at`, `reviewed_at`, `reviewed_by`.
- `backend/src/repositories/calibration_note_repository.py` — `create_many`, `list_for_proposal`. You are appending to this and to its ABC.
- `backend/src/services/content_improvement_service.py` — `run(*, max_lessons)`, `_draft`, and the module-level `_system_prompt()` returning `f"{load_prompt('house_style')}\n\n---\n\n{load_prompt('content_improvement')}"`.
- `backend/src/services/prompts.py` — `load_prompt(kind)`, `@lru_cache`d **by filename**. **Do not make it dynamic.** A value that varies per run cannot go through it.
- `backend/src/routers/admin_content_improvement.py` and `backend/src/schemas/admin_proposals.py` — the house patterns for an admin router and its DTOs.
- `frontend/src/pages/admin2/ContentImprovementPage.tsx` — gains a local tab switch; `api.ts` and `kit/ConfirmButton` are the frontend patterns.

## File structure

| File | Responsibility |
|---|---|
| `backend/src/repositories/{base.py,calibration_note_repository.py}` (modify) | the four new reads/writes |
| `backend/src/services/calibration_prompt.py` (new) | the pure, bounded block renderer |
| `backend/src/services/content_improvement_service.py` (modify) | inject the block; fetch notes once per run |
| `backend/prompts/house_style.md` (modify) | one sentence telling a reader runtime notes may follow |
| `backend/src/services/calibration_note_service.py` (new) | list / review / graduate |
| `backend/src/schemas/admin_calibration_notes.py` (new) | the wire DTOs |
| `backend/src/routers/admin_calibration_notes.py` (new) | the three endpoints |
| `frontend/src/pages/admin2/CalibrationNotesQueue.tsx` (new) | the review screen |

---

### Task 1: repository reads and writes

**Files:**
- Modify: `backend/src/repositories/base.py`
- Modify: `backend/src/repositories/calibration_note_repository.py`
- Test: `backend/tests/integration/test_repositories/test_calibration_note_repository.py` (extend)

**Interfaces:**
- Consumes: the `CalibrationNote` model (already on `main`).
- Produces (Tasks 2 and 3 call exactly these):
  - `get_by_id(note_id: uuid.UUID) -> CalibrationNote | None`
  - `list_admin(*, status: str | None = None, limit: int, offset: int) -> list[Any]`
  - `count_admin(*, status: str | None = None) -> int`
  - `set_status(note: CalibrationNote, status: str, reviewed_by: uuid.UUID | None) -> None`
  - `list_for_injection(*, limit: int) -> list[str]`

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/integration/test_repositories/test_calibration_note_repository.py` (it already has a `_proposal` helper and imports `CalibrationNoteRepository`):

```python
async def test_get_by_id_and_set_status(db_session: AsyncSession) -> None:
    proposal = await _proposal(db_session, "SetStatus")
    reviewer = await create_user(db_session, email="cal-review@x.test", role="admin")
    repo = CalibrationNoteRepository(db_session)
    created = await repo.create_many(source_proposal_id=proposal.id, notes=["Prefer bullets."])
    note = created[0]

    fetched = await repo.get_by_id(note.id)
    assert fetched is not None

    await repo.set_status(fetched, "approved", reviewer.id)
    await db_session.refresh(fetched)
    assert fetched.status == "approved"
    assert fetched.reviewed_by == reviewer.id
    assert fetched.reviewed_at is not None

    assert await repo.get_by_id(uuid.uuid4()) is None


async def test_set_status_with_no_reviewer_clears_the_stamp(db_session: AsyncSession) -> None:
    # Mirrors the sibling repositories: reviewed_by=None clears reviewed_at too.
    proposal = await _proposal(db_session, "ClearStamp")
    reviewer = await create_user(db_session, email="cal-clear@x.test", role="admin")
    repo = CalibrationNoteRepository(db_session)
    note = (await repo.create_many(source_proposal_id=proposal.id, notes=["x"]))[0]

    await repo.set_status(note, "approved", reviewer.id)
    await repo.set_status(note, "suggested", None)
    await db_session.refresh(note)

    assert note.status == "suggested"
    assert note.reviewed_by is None
    assert note.reviewed_at is None


async def test_list_admin_filters_by_status_and_joins_the_source_lesson(
    db_session: AsyncSession,
) -> None:
    proposal = await _proposal(db_session, "ListAdmin")
    reviewer = await create_user(db_session, email="cal-list@x.test", role="admin")
    repo = CalibrationNoteRepository(db_session)
    created = await repo.create_many(
        source_proposal_id=proposal.id, notes=["first", "second"]
    )
    await repo.set_status(created[0], "approved", reviewer.id)

    rows = await repo.list_admin(limit=10, offset=0)
    assert len(rows) == 2
    # (note, source_lesson_id, source_lesson_title)
    note, lesson_id, lesson_title = rows[0]
    assert lesson_id is not None
    assert lesson_title == "ListAdmin Lesson"

    assert await repo.count_admin() == 2
    assert await repo.count_admin(status="approved") == 1
    approved = await repo.list_admin(status="approved", limit=10, offset=0)
    assert [r[0].note for r in approved] == ["first"]


async def test_list_admin_survives_a_deleted_source(db_session: AsyncSession) -> None:
    # source_proposal_id is ON DELETE SET NULL, so an approved note outlives its
    # lesson. The outer joins must not hide it.
    proposal = await _proposal(db_session, "Orphan")
    repo = CalibrationNoteRepository(db_session)
    await repo.create_many(source_proposal_id=proposal.id, notes=["survivor"])
    await db_session.delete(proposal)
    await db_session.commit()

    rows = await repo.list_admin(limit=10, offset=0)

    assert len(rows) == 1
    note, lesson_id, lesson_title = rows[0]
    assert note.note == "survivor"
    assert lesson_id is None
    assert lesson_title is None


async def test_list_for_injection_returns_approved_text_newest_first(
    db_session: AsyncSession,
) -> None:
    proposal = await _proposal(db_session, "Injection")
    reviewer = await create_user(db_session, email="cal-inject@x.test", role="admin")
    repo = CalibrationNoteRepository(db_session)
    created = await repo.create_many(
        source_proposal_id=proposal.id, notes=["older", "newer", "never approved"]
    )
    await repo.set_status(created[0], "approved", reviewer.id)
    await repo.set_status(created[1], "approved", reviewer.id)
    await repo.set_status(created[2], "rejected", reviewer.id)

    notes = await repo.list_for_injection(limit=10)

    assert "never approved" not in notes
    assert set(notes) == {"older", "newer"}
    assert await repo.list_for_injection(limit=1) == notes[:1]


async def test_only_approved_notes_are_injected(db_session: AsyncSession) -> None:
    proposal = await _proposal(db_session, "OnlyApproved")
    reviewer = await create_user(db_session, email="cal-only@x.test", role="admin")
    repo = CalibrationNoteRepository(db_session)
    created = await repo.create_many(
        source_proposal_id=proposal.id, notes=["a", "b", "c"]
    )
    await repo.set_status(created[1], "retired", reviewer.id)
    await repo.set_status(created[2], "rejected", reviewer.id)

    # created[0] is still `suggested` — never approved, so never injected.
    assert await repo.list_for_injection(limit=10) == []
```

Add `create_user` to that file's `tests.fixtures.factories` import and `import uuid` if not already present.

- [ ] **Step 2: Run the tests to verify they fail**

Run (inside `backend/`): `uv run pytest tests/integration/test_repositories/test_calibration_note_repository.py -v -n0`
Expected: FAIL — `AttributeError: 'CalibrationNoteRepository' object has no attribute 'get_by_id'`.

- [ ] **Step 3: Extend the abstract contract**

In `backend/src/repositories/base.py`, add to `AbstractCalibrationNoteRepository` after `list_for_proposal`:

```python
    @abstractmethod
    async def get_by_id(self, note_id: uuid.UUID) -> CalibrationNote | None: ...

    @abstractmethod
    async def list_admin(
        self, *, status: str | None = None, limit: int, offset: int
    ) -> list[Any]:
        """Newest-first review rows: (note, source_lesson_id, source_lesson_title).
        BOTH joins are outer — `source_proposal_id` is ON DELETE SET NULL, so an
        approved note outlives the lesson it came from and must not disappear
        from the queue when that lesson is deleted."""

    @abstractmethod
    async def count_admin(self, *, status: str | None = None) -> int:
        """Total rows matching the same filter as list_admin (pagination total)."""

    @abstractmethod
    async def set_status(
        self, note: CalibrationNote, status: str, reviewed_by: uuid.UUID | None
    ) -> None:
        """Update status + reviewer stamp; reviewed_by=None clears reviewed_at too
        (same contract as the sibling repositories)."""

    @abstractmethod
    async def list_for_injection(self, *, limit: int) -> list[str]:
        """Approved note TEXT ONLY, most-recently-approved first, capped at
        `limit`. Only `approved` — a `suggested` note has not been through the
        human gate, and `rejected`/`retired` are deliberately out (retired means
        it was hand-copied into house_style.md and injecting it too would
        duplicate it). The caller applies the character budget on top, via
        services/calibration_prompt.py::render_calibration_block."""
```

- [ ] **Step 4: Implement**

In `backend/src/repositories/calibration_note_repository.py`, extend the imports and append the methods:

```python
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import Select, func, select

from src.db.models import CalibrationNote, Lesson, LessonContentProposal
```

```python
    async def get_by_id(self, note_id: uuid.UUID) -> CalibrationNote | None:
        result = await self._session.execute(
            select(CalibrationNote).where(CalibrationNote.id == note_id)
        )
        return result.scalar_one_or_none()

    def _admin_query(self, status: str | None) -> Select[Any]:
        query = (
            select(
                CalibrationNote,
                LessonContentProposal.lesson_id.label("source_lesson_id"),
                Lesson.title.label("source_lesson_title"),
            )
            # Both OUTER: the source proposal may have been deleted (SET NULL),
            # and an approved note must still appear in the queue without it.
            .outerjoin(
                LessonContentProposal,
                LessonContentProposal.id == CalibrationNote.source_proposal_id,
            )
            .outerjoin(Lesson, Lesson.id == LessonContentProposal.lesson_id)
        )
        if status is not None:
            query = query.where(CalibrationNote.status == status)
        return query

    async def list_admin(
        self, *, status: str | None = None, limit: int, offset: int
    ) -> list[Any]:
        query = (
            self._admin_query(status)
            .order_by(CalibrationNote.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list((await self._session.execute(query)).all())

    async def count_admin(self, *, status: str | None = None) -> int:
        query = select(func.count()).select_from(self._admin_query(status).subquery())
        return int((await self._session.execute(query)).scalar_one())

    async def set_status(
        self, note: CalibrationNote, status: str, reviewed_by: uuid.UUID | None
    ) -> None:
        note.status = status
        note.reviewed_by = reviewed_by
        note.reviewed_at = None if reviewed_by is None else datetime.now(UTC)
        await self._session.commit()

    async def list_for_injection(self, *, limit: int) -> list[str]:
        query = (
            select(CalibrationNote.note)
            .where(CalibrationNote.status == "approved")
            .order_by(CalibrationNote.reviewed_at.desc())
            .limit(limit)
        )
        return [row[0] for row in (await self._session.execute(query)).all()]
```

- [ ] **Step 5: Run the tests**

Run (inside `backend/`): `uv run pytest tests/integration/test_repositories/test_calibration_note_repository.py -v -n0`
Expected: PASS (the 2 pre-existing plus the 6 new).

- [ ] **Step 6: Full backend checks**

Run (inside `backend/`): `uv run poe format && uv run poe lint && uv run poe test && uv run poe ty`
Expected: green; no new findings in the touched files; ty at exactly 23.

- [ ] **Step 7: Commit**

```bash
git add backend/src/repositories/base.py backend/src/repositories/calibration_note_repository.py backend/tests/integration/test_repositories/test_calibration_note_repository.py
git commit -m "feat(content): calibration-note reads and status writes"
```

---

### Task 2: the bounded injected block

**Files:**
- Create: `backend/src/services/calibration_prompt.py`
- Modify: `backend/src/services/content_improvement_service.py`
- Modify: `backend/prompts/house_style.md`
- Test: `backend/tests/unit/test_calibration_prompt.py` (new)
- Test: `backend/tests/unit/test_content_improvement_service.py` (extend)

**Interfaces:**
- Consumes: `list_for_injection` (Task 1).
- Produces: `render_calibration_block(notes, *, max_notes, max_chars) -> str`, `MAX_INJECTED_NOTES = 8`, `MAX_INJECTED_CHARS = 1500`; `_system_prompt(calibration_notes: list[str]) -> str`.

**⚠️ Constructor churn:** `ContentImprovementService` gains a SIXTH positional dependency (`calibration_notes: AbstractCalibrationNoteRepository`)... **NO — it already has one.** Plan D added `calibration_notes` as the fifth argument for the learn card. You are reusing that same dependency, not adding another. Read the constructor before you touch it.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/unit/test_calibration_prompt.py`:

```python
from __future__ import annotations

from src.services.calibration_prompt import (
    MAX_INJECTED_CHARS,
    MAX_INJECTED_NOTES,
    render_calibration_block,
)


def test_no_notes_renders_nothing() -> None:
    # "" is the signal for the caller to skip the section entirely rather than
    # inject a header with nothing under it.
    assert render_calibration_block([]) == ""


def test_notes_are_numbered_in_the_order_given() -> None:
    block = render_calibration_block(["first note", "second note"])

    assert "1. first note" in block
    assert "2. second note" in block
    assert block.index("first note") < block.index("second note")


def test_the_header_says_the_notes_are_not_enforced() -> None:
    block = render_calibration_block(["a note"])

    lowered = block.lower()
    assert "not" in lowered and "enforced" in lowered


def test_the_note_count_is_capped() -> None:
    block = render_calibration_block([f"note {i}" for i in range(20)], max_notes=3)

    assert "note 2" in block
    assert "note 3" not in block


def test_the_character_budget_drops_from_the_end() -> None:
    notes = ["x" * 200, "y" * 200, "z" * 200]

    block = render_calibration_block(notes, max_chars=len(render_calibration_block(notes[:2])))

    assert "y" * 200 in block
    assert "z" * 200 not in block


def test_one_oversized_note_is_still_kept() -> None:
    # Dropping everything would silently lose a legitimate long note.
    block = render_calibration_block(["q" * 5000], max_chars=100)

    assert "q" * 5000 in block


def test_the_defaults_are_the_documented_bounds() -> None:
    assert MAX_INJECTED_NOTES == 8
    assert MAX_INJECTED_CHARS == 1500
```

Add to `backend/tests/unit/test_content_improvement_service.py`:

```python
async def test_zero_approved_notes_leaves_the_prompt_byte_identical() -> None:
    # THE regression guard for this plan: nothing about drafting may change
    # just because the injection mechanism exists.
    from src.services.content_improvement_service import _system_prompt
    from src.services.prompts import load_prompt

    expected = f"{load_prompt('house_style')}\n\n---\n\n{load_prompt('content_improvement')}"

    assert _system_prompt([]) == expected


async def test_approved_notes_are_injected_between_house_style_and_the_task() -> None:
    from src.services.content_improvement_service import _system_prompt

    composed = _system_prompt(["Prefer inline bullets over a card group."])

    assert "Prefer inline bullets over a card group." in composed
    # House style first, notes in the middle, the task prompt last.
    assert composed.index("Artefact") < composed.index("Prefer inline bullets")
    assert composed.index("Prefer inline bullets") < composed.index("block by block diff")


async def test_the_notes_repository_is_read_once_per_run_not_once_per_lesson() -> None:
    first, lesson_a = _row("first"), _lesson("First")
    second, lesson_b = _row("second"), _lesson("Second")
    llm = _ScriptedLlm(
        [
            {"proposed_blocks": _GOOD_BLOCKS, "summary": "s"},
            {"proposed_blocks": _GOOD_BLOCKS, "summary": "s"},
        ]
    )
    service, _proposals, _content = _service(
        [(first, lesson_a), (second, lesson_b)], llm=llm
    )

    await service.run(max_lessons=3)

    assert len(llm.prompts) == 2
    service._calibration_notes.list_for_injection.assert_awaited_once()
```

Adapt that last test's helpers to whatever `_row`/`_lesson`/`_service` actually look like in that file — read them first. The point is two lessons in one run, two model calls, **one** notes read.

- [ ] **Step 2: Run the tests to verify they fail**

Run (inside `backend/`): `uv run pytest tests/unit/test_calibration_prompt.py tests/unit/test_content_improvement_service.py -v`
Expected: FAIL — `ModuleNotFoundError: src.services.calibration_prompt`, and `_system_prompt()` takes no argument.

- [ ] **Step 3: Write the pure renderer**

Create `backend/src/services/calibration_prompt.py`:

```python
"""Renders the admin-approved calibration notes injected into the content
agent's system prompt.

Pure: no I/O, no DB, no LLM, so the bounding rules are unit-testable on their
own. The caller fetches the notes; this decides how many of them fit and how
they are framed.
"""

from __future__ import annotations

__all__ = ["MAX_INJECTED_CHARS", "MAX_INJECTED_NOTES", "render_calibration_block"]

MAX_INJECTED_NOTES = 8
MAX_INJECTED_CHARS = 1500

_HEADER = (
    "## Calibration notes from past admin edits\n\n"
    "An admin approved each note below after comparing one of your earlier "
    "drafts with the version they actually accepted. They extend the house "
    "style above. They are NOT validator-enforced the way the [enforced] rules "
    "there are, so treat them as guidance — and if a note ever contradicts the "
    "house style above, the house style wins."
)


def render_calibration_block(
    notes: list[str],
    *,
    max_notes: int = MAX_INJECTED_NOTES,
    max_chars: int = MAX_INJECTED_CHARS,
) -> str:
    """A bounded markdown block of approved notes, or "" when there are none.

    Returns "" rather than a bare header so the caller can skip the section
    entirely — an empty header would spend tokens telling the model about
    guidance that does not exist.

    `notes` is assumed already ordered by priority (the repository orders by
    most-recently-approved). This drops from the END, the lowest priority, until
    the rendered block fits `max_chars` — but always keeps at least one note
    even if that one alone exceeds the budget, because silently dropping a
    legitimate long note is worse than overshooting slightly.
    """
    if not notes:
        return ""
    kept: list[str] = []
    for note in notes[:max_notes]:
        candidate = [*kept, note]
        if kept and len(_render(candidate)) > max_chars:
            break
        kept = candidate
    return _render(kept)


def _render(notes: list[str]) -> str:
    lines = "\n".join(f"{index}. {note}" for index, note in enumerate(notes, start=1))
    return f"{_HEADER}\n\n{lines}"
```

- [ ] **Step 4: Inject it**

In `backend/src/services/content_improvement_service.py`:

(a) import the renderer:

```python
from src.services.calibration_prompt import MAX_INJECTED_NOTES, render_calibration_block
```

(b) replace `_system_prompt`:

```python
def _system_prompt(calibration_notes: list[str]) -> str:
    """House style, then any admin-approved calibration notes, then the task
    prompt. `content_improvement.md` reads as a continuation of the house style
    ("The house style above is not background reading"), and the notes sit
    between them because they extend it — they are literally more entries for
    its calibration section.

    With no approved notes the block renders as "" and is skipped, so the
    composed prompt is byte-identical to what it was before injection existed.

    NOT cached, and load_prompt must not be made dynamic: load_prompt is
    @lru_cache'd by filename because it reads static files, whereas this value
    depends on whatever is currently approved in the database.
    """
    parts = [load_prompt("house_style")]
    block = render_calibration_block(calibration_notes)
    if block:
        parts.append(block)
    parts.append(load_prompt("content_improvement"))
    return "\n\n---\n\n".join(parts)
```

(c) in `run`, fetch the approved set **once**, before the loop, and thread it through:

```python
        pending = await self._lessons_awaiting_draft()
        calibration_notes = await self._calibration_notes.list_for_injection(
            limit=MAX_INJECTED_NOTES
        )
```

then pass it to `_draft(lesson, feedback_items, calibration_notes)`; `_draft` takes it as a third parameter and passes it to `_system_prompt(calibration_notes)`.

Fetching once per run rather than once per lesson matters: a three-lesson run must not issue three identical queries, and every lesson in one run should be drafted against the same guidance.

- [ ] **Step 5: Tell a reader of the file that runtime notes exist**

In `backend/prompts/house_style.md`, in the "Calibration: real edits made to drafts" section, immediately after its intro paragraph and before the `was … became` list, add:

```markdown
Admin-approved notes distilled from more recent edits may be appended below
this section at runtime. They extend this list. They are guidance, never an
`[enforced]` rule, even when they read like one.
```

Someone reading this file on disk cannot see the database, and without this line the runtime prompt has a section the file never mentions. **Write it without em dashes, en dashes or ellipsis** — this file's own `[enforced]` punctuation rule applies to it.

- [ ] **Step 6: Run the tests**

Run (inside `backend/`): `uv run pytest tests/unit/test_calibration_prompt.py tests/unit/test_content_improvement_service.py -v`
Expected: PASS, including every pre-existing prompt assertion in the second file — unchanged, because zero notes composes byte-identically.

- [ ] **Step 7: Full backend checks**

Run (inside `backend/`): `uv run poe format && uv run poe lint && uv run poe test && uv run poe ty`
Expected: green; ty at exactly 23.

- [ ] **Step 8: Commit**

```bash
git add backend/src/services/calibration_prompt.py backend/src/services/content_improvement_service.py backend/prompts/house_style.md backend/tests/unit/test_calibration_prompt.py backend/tests/unit/test_content_improvement_service.py
git commit -m "feat(content): inject admin-approved calibration notes into the drafting prompt"
```

---

### Task 3: the curation service and its endpoints

**Files:**
- Create: `backend/src/services/calibration_note_service.py`
- Create: `backend/src/schemas/admin_calibration_notes.py`
- Create: `backend/src/routers/admin_calibration_notes.py`
- Modify: `backend/src/core/dependencies/content_ai.py`
- Modify: `backend/src/main.py`
- Test: `backend/tests/unit/test_calibration_note_service.py` (new)
- Test: `backend/tests/integration/test_routers/test_admin_calibration_notes.py` (new)
- Test: `backend/tests/integration/test_routers/test_authz.py` (three rows)

**Interfaces:**
- Consumes: Task 1's repository methods.
- Produces (Task 4 consumes over HTTP):
  - `GET /api/admin/calibration-notes?status=&limit=<1..100>&offset=` → `CalibrationNoteListResponse`
  - `POST /api/admin/calibration-notes/{note_id}/review` body `{decision: "approve"|"reject"}` → `CalibrationNoteReviewResponse {status}`
  - `POST /api/admin/calibration-notes/{note_id}/graduate` → `CalibrationNoteGraduateResponse {status, paste_ready}`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/unit/test_calibration_note_service.py`:

```python
from __future__ import annotations

import uuid
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock

import pytest

from src.repositories.base import AbstractCalibrationNoteRepository
from src.services.calibration_note_service import CalibrationNoteService
from src.services.exceptions import ConflictError, InvalidRequestError, NotFoundError


def _note(**overrides: Any) -> Any:
    defaults: dict[str, Any] = {
        "id": uuid.uuid4(),
        "note": "Prefer inline bullets over a card group.",
        "status": "suggested",
        "source_proposal_id": uuid.uuid4(),
        "created_at": None,
        "reviewed_at": None,
    }
    return SimpleNamespace(**{**defaults, **overrides})


def _service(note: Any | None) -> tuple[CalibrationNoteService, AsyncMock]:
    notes = AsyncMock(spec=AbstractCalibrationNoteRepository)
    notes.get_by_id.return_value = note
    return CalibrationNoteService(notes), notes


async def test_approve_moves_a_suggested_note_to_approved() -> None:
    note = _note()
    service, notes = _service(note)
    reviewer_id = uuid.uuid4()

    assert (
        await service.review(note_id=note.id, decision="approve", reviewer_id=reviewer_id)
        == "approved"
    )
    notes.set_status.assert_awaited_once_with(note, "approved", reviewer_id)


async def test_reject_moves_a_suggested_note_to_rejected() -> None:
    note = _note()
    service, notes = _service(note)
    reviewer_id = uuid.uuid4()

    assert (
        await service.review(note_id=note.id, decision="reject", reviewer_id=reviewer_id)
        == "rejected"
    )
    notes.set_status.assert_awaited_once_with(note, "rejected", reviewer_id)


@pytest.mark.parametrize("status", ["approved", "rejected", "retired"])
async def test_an_already_decided_note_is_refused(status: str) -> None:
    note = _note(status=status)
    service, notes = _service(note)

    with pytest.raises(ConflictError):
        await service.review(
            note_id=note.id, decision="approve", reviewer_id=uuid.uuid4()
        )
    notes.set_status.assert_not_awaited()


async def test_an_unknown_decision_never_changes_anything() -> None:
    note = _note()
    service, notes = _service(note)

    for decision in ("", "APPROVE", "inject"):
        with pytest.raises(InvalidRequestError):
            await service.review(
                note_id=note.id, decision=decision, reviewer_id=uuid.uuid4()
            )
    notes.set_status.assert_not_awaited()


async def test_review_of_an_unknown_note_raises_not_found() -> None:
    service, _notes = _service(None)

    with pytest.raises(NotFoundError):
        await service.review(
            note_id=uuid.uuid4(), decision="approve", reviewer_id=uuid.uuid4()
        )


async def test_graduate_retires_an_approved_note_and_returns_paste_ready_text() -> None:
    note = _note(status="approved")
    service, notes = _service(note)
    reviewer_id = uuid.uuid4()

    paste_ready = await service.graduate(note_id=note.id, reviewer_id=reviewer_id)

    notes.set_status.assert_awaited_once_with(note, "retired", reviewer_id)
    # Paste-ready for house_style.md's calibration list.
    assert paste_ready == "- Prefer inline bullets over a card group."


@pytest.mark.parametrize("status", ["suggested", "rejected", "retired"])
async def test_only_an_approved_note_can_graduate(status: str) -> None:
    note = _note(status=status)
    service, notes = _service(note)

    with pytest.raises(ConflictError):
        await service.graduate(note_id=note.id, reviewer_id=uuid.uuid4())
    notes.set_status.assert_not_awaited()


async def test_list_notes_shapes_the_rows_and_returns_the_total() -> None:
    note = _note()
    notes = AsyncMock(spec=AbstractCalibrationNoteRepository)
    lesson_id = uuid.uuid4()
    notes.list_admin.return_value = [(note, lesson_id, "Prompting basics")]
    notes.count_admin.return_value = 1
    service = CalibrationNoteService(notes)

    items, total = await service.list_notes(status=None, limit=25, offset=0)

    assert total == 1
    assert items[0]["id"] == note.id
    assert items[0]["note"] == note.note
    assert items[0]["source_lesson_id"] == lesson_id
    assert items[0]["source_lesson_title"] == "Prompting basics"
```

- [ ] **Step 2: Run the test to verify it fails**

Run (inside `backend/`): `uv run pytest tests/unit/test_calibration_note_service.py -v`
Expected: FAIL — `ModuleNotFoundError: src.services.calibration_note_service`.

- [ ] **Step 3: Write the service**

Create `backend/src/services/calibration_note_service.py`:

```python
"""Admin curation of the calibration notes the content agent suggested.

The human gate between the learn-card feature and the drafting prompt: a note
influences nothing until an admin approves it.

Has NO LLM dependency, unlike ContentImprovementService and
FeedbackTriageService, so it is never None-gated — reviewing notes that already
exist must keep working even if Settings.llm is later unconfigured.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

from src.services.exceptions import ConflictError, InvalidRequestError, NotFoundError

if TYPE_CHECKING:
    from src.repositories.base import AbstractCalibrationNoteRepository

__all__ = ["CalibrationNoteService"]

# Only a note nobody has decided on yet can be approved or rejected.
_REVIEWABLE_STATUSES = ("suggested",)


class CalibrationNoteService:
    def __init__(self, notes: AbstractCalibrationNoteRepository) -> None:
        self._notes = notes

    async def list_notes(
        self, *, status: str | None = None, limit: int, offset: int
    ) -> tuple[list[dict[str, Any]], int]:
        rows = await self._notes.list_admin(status=status, limit=limit, offset=offset)
        total = await self._notes.count_admin(status=status)
        items = [
            {
                "id": note.id,
                "note": note.note,
                "status": note.status,
                "source_proposal_id": note.source_proposal_id,
                "source_lesson_id": source_lesson_id,
                "source_lesson_title": source_lesson_title,
                "created_at": note.created_at,
                "reviewed_at": note.reviewed_at,
            }
            for (note, source_lesson_id, source_lesson_title) in rows
        ]
        return items, total

    async def review(self, *, note_id: uuid.UUID, decision: str, reviewer_id: uuid.UUID) -> str:
        """Approve a note into the drafting prompt, or reject it. Approving is
        the ONLY way a note starts influencing future drafts."""
        note = await self._notes.get_by_id(note_id)
        if note is None:
            raise NotFoundError("Calibration note")
        if note.status not in _REVIEWABLE_STATUSES:
            msg = f"this note is already {note.status}"
            raise ConflictError(msg)
        if decision == "approve":
            await self._notes.set_status(note, "approved", reviewer_id)
            return "approved"
        if decision == "reject":
            await self._notes.set_status(note, "rejected", reviewer_id)
            return "rejected"
        msg = f"unknown review decision {decision!r}"
        raise InvalidRequestError(msg)

    async def graduate(self, *, note_id: uuid.UUID, reviewer_id: uuid.UUID) -> str:
        """Mark an approved note `retired` and hand back the line to paste into
        backend/prompts/house_style.md.

        `retired` is not `rejected`: retired means the note proved itself and a
        human copied it into the house style, so it should stop occupying one of
        the capped runtime slots — and retiring is what stops it being injected
        TWICE, once from the database and once from the file.

        This deliberately does NOT write house_style.md. That file is baked into
        the container image at build time, so a runtime write lands on an
        ephemeral filesystem and disappears on the next revision, and git would
        overwrite it on the next deploy regardless. The file edit is a reviewed
        commit; this is the bookkeeping that a human made it.
        """
        note = await self._notes.get_by_id(note_id)
        if note is None:
            raise NotFoundError("Calibration note")
        if note.status != "approved":
            msg = f"only an approved note can graduate; this one is {note.status}"
            raise ConflictError(msg)
        await self._notes.set_status(note, "retired", reviewer_id)
        return f"- {note.note}"
```

- [ ] **Step 4: Write the schemas**

Create `backend/src/schemas/admin_calibration_notes.py`:

```python
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel

__all__ = [
    "CalibrationNoteGraduateResponse",
    "CalibrationNoteListResponse",
    "CalibrationNoteOut",
    "CalibrationNoteReviewRequest",
    "CalibrationNoteReviewResponse",
]

CalibrationNoteStatus = Literal["suggested", "approved", "rejected", "retired"]
NoteReviewDecision = Literal["approve", "reject"]


class CalibrationNoteOut(BaseModel):
    """One note the agent suggested about its own drafting. `source_lesson_*`
    are null when the lesson it came from has since been deleted — the note
    outlives it on purpose."""

    id: uuid.UUID
    note: str
    status: CalibrationNoteStatus
    source_proposal_id: uuid.UUID | None
    source_lesson_id: uuid.UUID | None
    source_lesson_title: str | None
    created_at: datetime
    reviewed_at: datetime | None


class CalibrationNoteListResponse(BaseModel):
    items: list[CalibrationNoteOut]
    total: int
    limit: int
    offset: int


class CalibrationNoteReviewRequest(BaseModel):
    decision: NoteReviewDecision


class CalibrationNoteReviewResponse(BaseModel):
    status: CalibrationNoteStatus


class CalibrationNoteGraduateResponse(BaseModel):
    """`paste_ready` is the line to paste into house_style.md's calibration
    section. Graduating does not write that file — see the service docstring."""

    status: CalibrationNoteStatus
    paste_ready: str
```

- [ ] **Step 5: Wire the DI**

In `backend/src/core/dependencies/content_ai.py`, add (runtime imports, per the FastAPI gotcha — `CalibrationNoteRepository` is already imported there for the content-improvement service):

```python
def get_calibration_note_service(
    notes: Annotated[CalibrationNoteRepository, Depends(get_calibration_note_repository)],
) -> CalibrationNoteService:
    """Unconditional, unlike the two agent services: curating notes needs no
    model, so it must keep working even when LLM__* is unconfigured."""
    return CalibrationNoteService(notes)
```

and add `"get_calibration_note_service"` to `__all__` in alphabetical position.

- [ ] **Step 6: Write the router**

Create `backend/src/routers/admin_calibration_notes.py`:

```python
from __future__ import annotations

import uuid
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query

from src.core.dependencies.auth import require_admin
from src.core.dependencies.content_ai import get_calibration_note_service
from src.db.models import User
from src.schemas.admin_calibration_notes import (
    CalibrationNoteGraduateResponse,
    CalibrationNoteListResponse,
    CalibrationNoteOut,
    CalibrationNoteReviewRequest,
    CalibrationNoteReviewResponse,
)
from src.services.calibration_note_service import CalibrationNoteService

__all__ = ["router"]

router = APIRouter(
    prefix="/api/admin/calibration-notes",
    tags=["admin:calibration-notes"],
    dependencies=[Depends(require_admin)],
)

NoteServiceDep = Annotated[CalibrationNoteService, Depends(get_calibration_note_service)]


@router.get("", response_model=CalibrationNoteListResponse)
async def list_calibration_notes(
    service: NoteServiceDep,
    status_filter: Annotated[
        Literal["suggested", "approved", "rejected", "retired"] | None, Query(alias="status")
    ] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> CalibrationNoteListResponse:
    items, total = await service.list_notes(status=status_filter, limit=limit, offset=offset)
    return CalibrationNoteListResponse(
        items=[CalibrationNoteOut.model_validate(item) for item in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post("/{note_id}/review", response_model=CalibrationNoteReviewResponse)
async def review_calibration_note(
    note_id: uuid.UUID,
    body: CalibrationNoteReviewRequest,
    service: NoteServiceDep,
    admin: Annotated[User, Depends(require_admin)],
) -> CalibrationNoteReviewResponse:
    """The human gate. Approving is what lets a note start influencing future
    drafts; rejecting takes it out of consideration for good."""
    new_status = await service.review(
        note_id=note_id, decision=body.decision, reviewer_id=admin.id
    )
    return CalibrationNoteReviewResponse(status=new_status)  # ty: ignore[invalid-argument-type]


@router.post("/{note_id}/graduate", response_model=CalibrationNoteGraduateResponse)
async def graduate_calibration_note(
    note_id: uuid.UUID,
    service: NoteServiceDep,
    admin: Annotated[User, Depends(require_admin)],
) -> CalibrationNoteGraduateResponse:
    """Retire an approved note and hand back the line to paste into
    house_style.md. Retiring frees one of the capped runtime slots and stops the
    note being injected twice once it is in the file."""
    paste_ready = await service.graduate(note_id=note_id, reviewer_id=admin.id)
    return CalibrationNoteGraduateResponse(status="retired", paste_ready=paste_ready)
```

If `ty` reports the `# ty: ignore` on the review response as UNUSED, delete it — a `str` return into a `Literal` field may or may not need it depending on inference. Match what ty actually says; the count must end at exactly 23.

- [ ] **Step 7: Register the router**

In `backend/src/main.py`, add `admin_calibration_notes` to the `from src.routers import (...)` block (alphabetically, before `admin_content`) and add `app.include_router(admin_calibration_notes.router)` next to the other admin routers.

- [ ] **Step 8: Add the authz rows**

In `backend/tests/integration/test_routers/test_authz.py`, after the content-improvement rows:

```python
    # Unlike the content-improvement rows, this router is NOT LLM-gated —
    # curating notes needs no model. So the admin case here hits the real
    # handler: a 200 for the list, and a genuine 404 (NotFoundError) for a
    # random note id on review/graduate, rather than "not configured". That
    # difference is deliberate, not a copy-paste slip.
    (
        "calibration-notes-list",
        "GET",
        lambda s: "/api/admin/calibration-notes",
        lambda s: None,
        True,
    ),
    (
        "calibration-notes-review",
        "POST",
        lambda s: f"/api/admin/calibration-notes/{uuid.uuid4()}/review",
        lambda s: {"decision": "approve"},
        True,
    ),
    (
        "calibration-notes-graduate",
        "POST",
        lambda s: f"/api/admin/calibration-notes/{uuid.uuid4()}/graduate",
        lambda s: None,
        True,
    ),
```

- [ ] **Step 9: Write the integration tests**

Create `backend/tests/integration/test_routers/test_admin_calibration_notes.py`. Unlike the content-improvement tests this needs **no DI override and no fake LLM** — the router is not LLM-gated, so the plain conftest `client` fixture works. Seed notes with `CalibrationNoteRepository(db_session).create_many(...)` against a proposal built the same way `test_calibration_note_repository.py` does.

Cover: the list returns seeded notes with lesson context and filters by status; approve then a second approve 409s; reject works; an unknown decision is 422 (the `Literal` catches it at the schema); an unknown note id is 404; graduate on an approved note returns `{"status": "retired", "paste_ready": "- <text>"}`; graduate on a `suggested` note 409s; and **the whole router works with `test_settings.llm = None`**, which is what proves it is not LLM-gated.

- [ ] **Step 10: Run everything**

Run (inside `backend/`):
`uv run pytest tests/unit/test_calibration_note_service.py tests/integration/test_routers/test_admin_calibration_notes.py tests/integration/test_routers/test_authz.py -v -n0`
then `uv run poe format && uv run poe lint && uv run poe test && uv run poe ty`
Expected: all green; ty at exactly 23.

- [ ] **Step 11: Commit**

```bash
git add backend/src/services/calibration_note_service.py backend/src/schemas/admin_calibration_notes.py backend/src/routers/admin_calibration_notes.py backend/src/core/dependencies/content_ai.py backend/src/main.py backend/tests/unit/test_calibration_note_service.py backend/tests/integration/test_routers/test_admin_calibration_notes.py backend/tests/integration/test_routers/test_authz.py
git commit -m "feat(content): admin curation of calibration notes"
```

---

### Task 4: the learn-cards review screen

**Files:**
- Modify: `frontend/src/api/schema.d.ts` (regenerated, committed)
- Modify: `frontend/src/types/domain.ts`
- Modify: `frontend/src/pages/admin2/api.ts`
- Create: `frontend/src/pages/admin2/CalibrationNotesQueue.tsx`
- Modify: `frontend/src/pages/admin2/ContentImprovementPage.tsx`
- Modify: `frontend/src/styles/admin.css`

**Interfaces:**
- Consumes: Task 3's three endpoints.
- Produces: the finished curation screen.

- [ ] **Step 1: Regenerate the API types (side-effect-free)**

Never `npm run gen:api` — it points `openapi-typescript` at a *running* dev server whose startup fires a cleanup DELETE against the real Azure dev database.

```bash
# inside backend/
uv run python -c "import json, pathlib; from src.main import app; pathlib.Path('openapi.json').write_text(json.dumps(app.openapi()), encoding='utf-8')"
# inside frontend/
npx openapi-typescript ../backend/openapi.json -o src/api/schema.d.ts
rm ../backend/openapi.json
```

Expected diff: the three `/api/admin/calibration-notes*` paths and their operations, plus `CalibrationNoteOut`, `CalibrationNoteListResponse`, `CalibrationNoteReviewRequest/Response` and `CalibrationNoteGraduateResponse`. **Inspect it before committing.** If unrelated paths churn, stop and report. Confirm `backend/openapi.json` is gone from `git status --short`.

- [ ] **Step 2: Domain aliases**

Append to `frontend/src/types/domain.ts`:

```typescript
export type CalibrationNoteOut = components['schemas']['CalibrationNoteOut']
export type CalibrationNoteListResponse = components['schemas']['CalibrationNoteListResponse']
export type CalibrationNoteStatus = CalibrationNoteOut['status']
export type CalibrationNoteGraduateResponse = components['schemas']['CalibrationNoteGraduateResponse']
```

- [ ] **Step 3: Data-layer hooks**

Append to `frontend/src/pages/admin2/api.ts` (add the new types to the `import type` list):

```typescript
// ── Calibration notes (the agent's suggested guidance, pending an admin) ────────────────────
// Not project-scoped, for the same reason proposals are not: the guidance is about how the
// agent writes, not about any one project's content.

export const CALIBRATION_NOTE_PAGE_SIZE = 25

export interface CalibrationNotesParams {
  status?: CalibrationNoteStatus
  page?: number
  /** Defaults to CALIBRATION_NOTE_PAGE_SIZE. The tab badge overrides this to 1 — carried in
   * the query key below so that call never collides with a paginated list entry. */
  limit?: number
}

async function fetchCalibrationNotes(params: CalibrationNotesParams): Promise<CalibrationNoteListResponse> {
  const limit = params.limit ?? CALIBRATION_NOTE_PAGE_SIZE
  const offset = ((params.page ?? 1) - 1) * limit
  const { data, error } = await rawRequest<CalibrationNoteListResponse>('GET', '/api/admin/calibration-notes', {
    params: { query: { status: params.status, limit, offset } },
  })
  if (!data) throw new Error(errorMessage(error, 'Failed to load calibration notes.'))
  return data
}

export function useCalibrationNotes(params: CalibrationNotesParams) {
  return useQuery({
    queryKey: ['admin', 'calibration-notes', { status: params.status, page: params.page, limit: params.limit }] as const,
    queryFn: () => fetchCalibrationNotes(params),
  })
}

export interface ReviewCalibrationNoteInput {
  noteId: string
  decision: 'approve' | 'reject'
}

async function reviewCalibrationNote({ noteId, decision }: ReviewCalibrationNoteInput): Promise<void> {
  const { error } = await rawRequest<unknown>('POST', `/api/admin/calibration-notes/${noteId}/review`, {
    body: { decision },
  })
  if (error) throw new Error(errorMessage(error, 'Failed to review the note.'))
}

/** Approving is what lets a note start influencing future drafts, so this invalidates the
 * whole `['admin','calibration-notes']` prefix — the list, and the tab badge that shares it. */
export function useReviewCalibrationNote() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: reviewCalibrationNote,
    onSettled: () => {
      void queryClient.invalidateQueries({ queryKey: ['admin', 'calibration-notes'] })
    },
  })
}

async function graduateCalibrationNote(noteId: string): Promise<CalibrationNoteGraduateResponse> {
  const { data, error } = await rawRequest<CalibrationNoteGraduateResponse>(
    'POST',
    `/api/admin/calibration-notes/${noteId}/graduate`,
  )
  if (!data) throw new Error(errorMessage(error, 'Failed to graduate the note.'))
  return data
}

/** Retires an approved note and returns the line to paste into house_style.md. The server
 * deliberately does not write that file — it is baked into the container image, so a runtime
 * write would vanish on the next revision. */
export function useGraduateCalibrationNote() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: graduateCalibrationNote,
    onSettled: () => {
      void queryClient.invalidateQueries({ queryKey: ['admin', 'calibration-notes'] })
    },
  })
}
```

- [ ] **Step 4: The queue screen**

Create `frontend/src/pages/admin2/CalibrationNotesQueue.tsx`:

```tsx
import { useEffect, useState } from 'react'
import { formatDate } from '../admin/adminHelpers'
import type { CalibrationNoteOut, CalibrationNoteStatus } from '../../types/domain'
import {
  CALIBRATION_NOTE_PAGE_SIZE,
  useCalibrationNotes,
  useGraduateCalibrationNote,
  useReviewCalibrationNote,
} from './api'
import { Chip, ConfirmButton, EmptyState, ErrorState, Spinner } from './kit'
import type { ChipTone } from './kit'

type StatusFilter = CalibrationNoteStatus | undefined

const STATUS_PILLS: { value: StatusFilter; label: string }[] = [
  { value: 'suggested', label: 'Suggested' },
  { value: 'approved', label: 'Approved' },
  { value: 'retired', label: 'Graduated' },
  { value: 'rejected', label: 'Rejected' },
  { value: undefined, label: 'All' },
]

/** The human gate between the agent's self-critique and its own prompt. The
 * agent suggests a note after an admin edits one of its drafts; nothing here
 * influences a future draft until it is approved. */
export default function CalibrationNotesQueue() {
  const [status, setStatus] = useState<StatusFilter>('suggested')
  const [page, setPage] = useState(1)
  const review = useReviewCalibrationNote()
  const graduate = useGraduateCalibrationNote()

  useEffect(() => setPage(1), [status])

  const { data, isLoading, error, refetch } = useCalibrationNotes({ status, page })
  const totalPages = data ? Math.max(1, Math.ceil(data.total / CALIBRATION_NOTE_PAGE_SIZE)) : 1

  useEffect(() => {
    if (page > totalPages) setPage(totalPages)
  }, [page, totalPages])

  if (isLoading) {
    return (
      <div className="adm-loading">
        <Spinner />
      </div>
    )
  }

  if (error || !data) {
    return <ErrorState message={error?.message ?? 'Failed to load calibration notes.'} onRetry={() => void refetch()} />
  }

  return (
    <div>
      <p className="adm-page-sub">
        Guidance the agent suggested about its own drafting, after comparing a draft with the
        version you accepted. A note changes nothing until you approve it, and an approved note
        is guidance for the agent, never a rule the validator enforces.
      </p>

      <div className="adm-toolbar">
        <div className="adm-pills">
          {STATUS_PILLS.map(pill => (
            <button
              key={pill.label}
              type="button"
              className={status === pill.value ? 'adm-pill active' : 'adm-pill'}
              onClick={() => setStatus(pill.value)}
            >
              {pill.label}
            </button>
          ))}
        </div>
      </div>

      {graduate.isSuccess && (
        <p className="adm-subtext">
          Retired. Paste this into the calibration section of <code>backend/prompts/house_style.md</code> and commit it:
          <br />
          <code>{graduate.data.paste_ready}</code>
        </p>
      )}
      {(review.isError || graduate.isError) && (
        <p className="adm-form-msg adm-form-msg-err">
          {(review.error ?? graduate.error) instanceof Error
            ? ((review.error ?? graduate.error) as Error).message
            : 'Failed to update the note.'}
        </p>
      )}

      {data.items.length === 0 ? (
        <EmptyState
          title="No notes here."
          hint="Notes appear after you accept a draft you edited."
        />
      ) : (
        data.items.map(item => (
          <NoteRow
            key={item.id}
            item={item}
            onReview={decision => review.mutate({ noteId: item.id, decision })}
            onGraduate={() => graduate.mutate(item.id)}
            busy={review.isPending || graduate.isPending}
          />
        ))
      )}

      <div className="adm-pager">
        <span className="adm-pager-info">
          Page {page} of {totalPages} · {data.total} total
        </span>
        <div className="adm-pager-actions">
          <button type="button" className="adm-btn adm-btn-ghost adm-btn-sm" disabled={page <= 1} onClick={() => setPage(p => p - 1)}>
            Previous
          </button>
          <button type="button" className="adm-btn adm-btn-ghost adm-btn-sm" disabled={page >= totalPages} onClick={() => setPage(p => p + 1)}>
            Next
          </button>
        </div>
      </div>
    </div>
  )
}

interface NoteRowProps {
  item: CalibrationNoteOut
  onReview: (decision: 'approve' | 'reject') => void
  onGraduate: () => void
  busy: boolean
}

function NoteRow({ item, onReview, onGraduate, busy }: NoteRowProps) {
  const done = item.status !== 'suggested'

  return (
    <div className={`adm-ci-card${done ? ' adm-ci-card-done' : ''}`}>
      <div className="adm-ci-head">
        <Chip tone={statusTone(item.status)}>{statusLabel(item.status)}</Chip>
        <span className="adm-ci-when">{formatDate(item.created_at)}</span>
      </div>

      {/* Agent output — plain text, never HTML or markdown. */}
      <p className="adm-ci-summary">{item.note}</p>

      <div className="adm-ci-loc">
        <span className="adm-loc-chip">
          <span className="adm-loc-label">From</span>
          {item.source_lesson_title ?? '(lesson since deleted)'}
        </span>
      </div>

      <div className="adm-ci-foot">
        {item.status === 'suggested' && (
          <div className="adm-ci-actions">
            <button type="button" className="adm-btn adm-btn-ghost adm-btn-sm" disabled={busy} onClick={() => onReview('reject')}>
              Reject
            </button>
            <ConfirmButton
              label="Approve"
              confirmLabel="Yes, approve"
              tone="neutral"
              busy={busy}
              onConfirm={() => onReview('approve')}
            />
          </div>
        )}
        {item.status === 'approved' && (
          <div className="adm-ci-actions">
            <ConfirmButton
              label="Mark as graduated"
              confirmLabel="Yes, retire it"
              tone="neutral"
              busy={busy}
              onConfirm={onGraduate}
            />
          </div>
        )}
      </div>
    </div>
  )
}

function statusTone(status: CalibrationNoteStatus): ChipTone {
  if (status === 'approved') return 'good'
  if (status === 'retired') return 'warn'
  return 'default'
}

function statusLabel(status: CalibrationNoteStatus): string {
  const labels: Record<CalibrationNoteStatus, string> = {
    suggested: 'Awaiting review',
    approved: 'In the prompt',
    rejected: 'Rejected',
    retired: 'Graduated to house style',
  }
  return labels[status]
}
```

`ConfirmButton` gained a `tone` prop earlier in this feature (default `'danger'`); `'neutral'` is right here because approving a note is reversible-ish and nothing is published. Check the prop still exists and drop it if not.

- [ ] **Step 5: Add the tab switch**

In `frontend/src/pages/admin2/ContentImprovementPage.tsx`, add a local view switch. **The structural point:** the page's existing early returns for the proposals query's loading and error states must NOT block the notes tab. Keep every hook unconditional at the top, then choose a body rather than returning early:

```tsx
  const [tab, setTab] = useState<'proposals' | 'notes'>('proposals')
  const suggestedNotes = useCalibrationNotes({ status: 'suggested', limit: 1 })
```

```tsx
  const body =
    tab === 'notes' ? (
      <CalibrationNotesQueue />
    ) : isLoading ? (
      <div className="adm-loading">
        <Spinner />
      </div>
    ) : error || !data ? (
      <ErrorState message={error?.message ?? 'Failed to load content proposals.'} onRetry={() => void refetch()} />
    ) : (
      <>{/* the existing proposals body, unchanged */}</>
    )

  return (
    <div>
      <h1 className="adm-page-title">Content AI</h1>
      <div className="adm-tabs">
        <button type="button" className={tab === 'proposals' ? 'adm-pill active' : 'adm-pill'} onClick={() => setTab('proposals')}>
          Proposals
        </button>
        <button type="button" className={tab === 'notes' ? 'adm-pill active' : 'adm-pill'} onClick={() => setTab('notes')}>
          Learn cards
          {(suggestedNotes.data?.total ?? 0) > 0 && <span className="adm-pill-n">{suggestedNotes.data?.total}</span>}
        </button>
      </div>
      {body}
    </div>
  )
```

Move the existing page subtitle into the proposals branch, since `CalibrationNotesQueue` renders its own. No `nav.ts` or `App.tsx` change — this is a sub-view of Content AI, not a new section.

- [ ] **Step 6: Styles**

Append to `frontend/src/styles/admin.css` if `.adm-tabs` does not already exist:

```css
.adm-tabs { display: flex; gap: 6px; margin: 0 0 14px; }
```

Check first — the file may already have something equivalent, in which case reuse it.

- [ ] **Step 7: Run the frontend checks**

Run (inside `frontend/`): `npm run typecheck && npm run lint && npm run build`
Expected: all green, with the single known `ProposalDiff.tsx` warning.

- [ ] **Step 8: Commit**

```bash
git add frontend/src/api/schema.d.ts frontend/src/types/domain.ts frontend/src/pages/admin2/api.ts frontend/src/pages/admin2/CalibrationNotesQueue.tsx frontend/src/pages/admin2/ContentImprovementPage.tsx frontend/src/styles/admin.css
git commit -m "feat(admin): review and graduate the agent's calibration notes"
```

- [ ] **Step 9: Confirm no stray dump file**

Run: `git status --short` — `backend/openapi.json` must NOT be listed.

---

## Self-Review

**Plan-mode coverage (the approved Phase 2):**

| Requirement | Task |
|---|---|
| A store with a review lifecycle, traceable to its source proposal | already on `main` (Plan D) ✅ |
| `CalibrationNoteService` with `list_notes` / `review` / `graduate`, no LLM dependency | Task 3 ✅ |
| `retired` distinct from `rejected`, graduation as bookkeeping only | Task 3 ✅ |
| `graduate()` does NOT write `house_style.md`, returns paste-ready text | Task 3 ✅ |
| Router at `/api/admin/calibration-notes` (list / review / graduate) | Task 3 ✅ |
| Pure `render_calibration_block` with a count cap and a char cap, keeping ≥1 | Task 2 ✅ |
| `_system_prompt` joins house style → notes → task prompt | Task 2 ✅ |
| `load_prompt` untouched and still `@lru_cache`d by filename | Task 2 ✅ |
| Notes fetched once per run, not once per lesson | Task 2 ✅ |
| Ordering by `reviewed_at DESC`, no admin pinning | Tasks 1 + 2 ✅ |
| No per-note "enforced" flag; the header and the UI both say so | Tasks 2 + 4 ✅ |
| One sentence in `house_style.md` pointing at the runtime block | Task 2 ✅ |
| A tab switch on the existing page, no new nav entry or route | Task 4 ✅ |
| Zero approved notes → byte-identical prompt | Task 2 ✅ (its own test) |
| Authz rows for every new endpoint | Task 3 ✅ |

**Deliberate deviations, flag at review:**
1. **No migration.** The plan-mode doc assumed one; Plan D already shipped the table with all four statuses and both reviewer columns, so there is nothing to migrate. If a reviewer expects a migration, this is why there is none.
2. **No `sync()` step.** The plan-mode doc had the notes materialised from critiques by a sweep. Plan D writes the rows directly at critique time, so the sweep would have nothing to do.
3. **The tab badge counts `suggested` notes.** Not in the plan; it mirrors the Feedback nav badge and costs one `limit=1` query that shares a cache entry with nothing else.

**Placeholder scan:** none. Two steps deliberately tell the implementer to check something before writing (`ConfirmButton`'s `tone` prop, whether `.adm-tabs` already exists) rather than assert a fact this plan has not verified.

**Type consistency:** `list_admin` returns `(note, source_lesson_id, source_lesson_title)` in Task 1 and is unpacked in that order in Task 3's `list_notes`; the dict keys it builds match `CalibrationNoteOut`'s fields exactly. `render_calibration_block(notes, *, max_notes, max_chars)` is defined in Task 2 and called with the same keywords by `_system_prompt`. `list_for_injection(*, limit)` is defined in Task 1 and called with `MAX_INJECTED_NOTES` in Task 2. The three endpoint shapes in Task 3 match the hooks in Task 4.

**The risk a reviewer should probe hardest:** whether zero approved notes really does compose byte-identically. Every existing assertion about the drafting prompt depends on it, and the failure mode is silent — a stray separator or an empty header would change every future draft's system prompt without any test necessarily noticing.
