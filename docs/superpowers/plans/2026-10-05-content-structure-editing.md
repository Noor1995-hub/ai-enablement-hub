# Content structure editing (B4) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** An admin **Content** page (`/admin/content`) where power admins edit the whole content structure (tracks, modules, lessons: edit, reorder, move, delete, prerequisites) without SQL, and where project admins assign their own project's learners to lessons added to modules they already hold.

**Architecture:** One migration normalises `sort_order` and adds deferred unique constraints. A pure cycle check lives in `core/prerequisites.py`. Atomic repository operations (move, delete-and-renumber, reorder) sit in `ContentRepository`. `ContentService` gains the assignment, user and project-admin repositories (repositories, not services) for the assignment gap. A new router, `routers/admin_structure.py`, holds the new endpoints; the lesson move rides on the existing `PATCH /api/admin/lessons/{id}`. The frontend gets an admin-kit page with a tree (left) and a detail panel (right), and pure helpers in `lib/contentTree.ts`.

**Tech Stack:** FastAPI, SQLAlchemy 2 async, Alembic, Postgres; React 18 + TypeScript, TanStack Query, openapi-fetch, Vitest + Testing Library.

**Spec:** `docs/superpowers/specs/2026-10-05-content-structure-editing-design.md`. Read it first; this plan argues from it.

## Global Constraints

- Read `CLAUDE.md`, `backend/CLAUDE.md` and `frontend/CLAUDE.md` before starting.
- **One database:** never run `uv run poe dev` or `alembic upgrade`. The migration is executed only by CI's `migrations` job and the Deploy workflow.
- Integration tests hit the shared remote test DB. Check `Test-NetConnection imaginemore-playground-pg.postgres.database.azure.com -Port 5432` first; if it fails, rely on CI. Never run two pytest sessions at once against it.
- Router → service → repository. **Services never call services.** `ContentService` takes repositories only.
- Every `/api/admin/*` route declares exactly one guard from `core/dependencies/admin_scope.py` and has a `_MATRIX` row in `backend/tests/integration/test_routers/test_authz.py`.
- FastAPI parameter annotations are runtime imports, never under `TYPE_CHECKING`.
- Error envelope: domain errors only (`NotFoundError` 404, `InvalidRequestError` 400). The reorder set mismatch is 400.
- Only power admins edit content. Project admins see the page read-only plus the project-scoped assign action.
- New and moved lessons are **never** auto-assigned; the Assign button inserts the gap with `assigned_via="manual"`.
- Deletes cascade after an impact warning; there is no undo. No `window.confirm`: use the kit `ConfirmButton`.
- `is_introduction` stays non-editable.
- Checks before every commit that touches the side: backend `uv run poe format-check && uv run poe lint-src && uv run poe ty-src` plus focused tests; frontend `npm run typecheck && npm run lint` plus focused tests. Full suites at checkpoints (end of Task 6, end of Task 9).
- Commit messages end with `Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>`.

## Review Focus

1. **A moved module or lesson leaves a hole or a duplicate position.** Expect source and destination both to read `0..n-1` afterwards. Tested in Task 3 (`test_move_module_renumbers_both_tracks`, `test_move_lesson_renumbers_both_modules`).
2. **Moving an item to where it already is** (same track or module). Expect a no-op that keeps its position, not "append at the end". Tested in Task 4 (`test_move_module_to_its_own_track_is_a_noop`).
3. **A project admin's assign touching another project's learner or a staff member.** Expect only the project's learners (no power admins, no project admins of that project). Tested in Task 5 (`test_project_gap_excludes_other_projects_and_staff`) and Task 6 (`test_project_assign_never_touches_another_project`).
4. **A prerequisite set that names an unknown module, repeats an id, or crosses tracks without a cycle.** Expect 404, dedupe, and success respectively. Tested in Task 2 and Task 4.
5. **The tree after deleting the last module of a track, or a track with zero modules.** Expect the track to stay with `0 · 0` counts, and the empty track to delete with a zero impact. Tested in Task 4 (`test_impact_of_an_empty_track_is_zero`) and Task 8 (`renders an empty track`).

---

## File structure

**Backend**

| File | Responsibility |
|---|---|
| Create `backend/alembic/versions/b0c1d2e3f4a5_unique_track_module_sort_order.py` | renumber + deferred unique constraints |
| Modify `backend/src/db/models/learning.py` | declare the two constraints on `Track` and `Module` |
| Modify `backend/tests/fixtures/factories.py` | `create_track`/`create_module` default to next free `sort_order` |
| Create `backend/src/core/prerequisites.py` | pure `would_create_cycle` |
| Modify `backend/src/repositories/base.py`, `content_repository.py`, `assignment_repository.py` | atomic structure ops, gap reads, pair insert, impact counts |
| Modify `backend/src/services/content_service.py` | structure use cases, impact, tree, gap, assign |
| Modify `backend/src/core/dependencies/domain.py` | `get_content_service` wiring |
| Modify `backend/src/schemas/admin_content.py` | request/response models |
| Create `backend/src/routers/admin_structure.py` | the new endpoints |
| Modify `backend/src/routers/admin_content.py` | lesson move via `module_id` |
| Modify `backend/src/main.py` | include the router |

**Frontend**

| File | Responsibility |
|---|---|
| Create `frontend/src/lib/contentTree.ts` (+ `.test.ts`) | filter, ↑/↓ permutation, labels |
| Modify `frontend/src/pages/admin2/api.ts` | content hooks |
| Create `frontend/src/pages/admin2/ContentPage.tsx` (+ `.test.tsx`) | page: tree + detail panel |
| Create `frontend/src/pages/admin2/ContentDetail.tsx` | track / module / lesson panels |
| Modify `frontend/src/pages/admin2/nav.ts`, `frontend/src/App.tsx` | sidebar item + route |
| Modify `frontend/src/styles/` (the admin stylesheet that defines `.adm-assign-layout`) | `.adm-content-*` classes |

---

### Task 1: Migration, model constraints, factory defaults

**Files:**
- Create: `backend/alembic/versions/b0c1d2e3f4a5_unique_track_module_sort_order.py`
- Modify: `backend/src/db/models/learning.py` (`Track.__table_args__`, `Module` table args)
- Modify: `backend/tests/fixtures/factories.py:116-142`
- Test: `backend/tests/integration/test_models/test_track_module_sort_order_uniqueness.py`

**Interfaces:**
- Produces: constraints `uq_tracks_sort_order` and `uq_modules_track_id_sort_order` (both `DEFERRABLE INITIALLY DEFERRED`); module-level constants `RENUMBER_TRACKS_SQL`, `RENUMBER_MODULES_SQL` in the migration file; factories `create_track(..., sort_order: int | None = None)` and `create_module(..., sort_order: int | None = None)` that pick `max + 1` when `None`.

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/integration/test_models/test_track_module_sort_order_uniqueness.py
"""Tracks and modules get the deferred sort_order uniqueness lessons already
have (migration b0c1d2e3f4a5, spec 2026-10-05). Deferred: a permutation may
pass through duplicates mid-transaction; the check runs at commit."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from src.db.models import Module, Track
from tests.fixtures.factories import create_module, create_track

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

_MIGRATION = (
    Path(__file__).resolve().parents[3]
    / "alembic"
    / "versions"
    / "b0c1d2e3f4a5_unique_track_module_sort_order.py"
)


def _migration():  # noqa: ANN202 - a loaded module
    spec = importlib.util.spec_from_file_location("b0c1d2e3f4a5", _MIGRATION)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


async def test_two_tracks_cannot_share_a_sort_order(db_session: AsyncSession) -> None:
    await create_track(db_session, "A", sort_order=7)
    db_session.add(Track(name="B", track_type="general", required_level="explore", sort_order=7))
    with pytest.raises(IntegrityError):
        await db_session.commit()
    await db_session.rollback()


async def test_two_modules_in_one_track_cannot_share_a_sort_order(
    db_session: AsyncSession,
) -> None:
    track = await create_track(db_session, "T")
    await create_module(db_session, track, "M1", sort_order=3)
    db_session.add(Module(track_id=track.id, title="M2", sort_order=3))
    with pytest.raises(IntegrityError):
        await db_session.commit()
    await db_session.rollback()


async def test_factories_pick_the_next_free_sort_order(db_session: AsyncSession) -> None:
    first = await create_track(db_session, "First")
    second = await create_track(db_session, "Second")
    assert second.sort_order == first.sort_order + 1
    m1 = await create_module(db_session, first, "M1")
    m2 = await create_module(db_session, first, "M2")
    assert (m1.sort_order, m2.sort_order) == (0, 1)


async def test_renumbering_keeps_the_sort_order_then_id_order(db_session: AsyncSession) -> None:
    """The migration's data step on tied rows: inside one transaction the
    deferred constraint lets us create the live-data shape (a tie), then the
    renumber must produce 0..n-1 in (sort_order, id) order."""
    migration = _migration()
    rows = [
        Track(name=name, track_type="general", required_level="explore", sort_order=order)
        for name, order in (("tie-a", 5), ("tie-b", 5), ("low", 2))
    ]
    db_session.add_all(rows)
    await db_session.flush()
    expected = [t.id for t in sorted(rows, key=lambda t: (t.sort_order, str(t.id)))]

    await db_session.execute(text(migration.RENUMBER_TRACKS_SQL))
    await db_session.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))
    result = await db_session.execute(
        text("SELECT id FROM tracks WHERE name IN ('tie-a','tie-b','low') ORDER BY sort_order")
    )
    assert [row[0] for row in result.all()] == expected
```

Note on the tie order: Postgres orders `uuid` by its bytes, and that matches the order of `str(uuid)`, because both compare the same 32 hex digits left to right.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd backend && uv run pytest tests/integration/test_models/test_track_module_sort_order_uniqueness.py -v -p no:randomly`
Expected: FAIL. The first two don't raise (no constraint yet); the factory test fails (both 0); the renumber test fails on the missing migration file.

- [ ] **Step 3: Write the migration**

```python
# backend/alembic/versions/b0c1d2e3f4a5_unique_track_module_sort_order.py
"""unique sort_order on tracks and on modules per track: DEFERRABLE (B4)

Spec: docs/superpowers/specs/2026-10-05-content-structure-editing-design.md.
Live data has duplicate sort_order values on tracks and on (track_id,
sort_order) for modules (see d4e5f6a7b8c9, which constrained lessons only).

1. Renumber both to 0..n-1 in (sort_order, id) order: the order every query
   already uses (content_repository.py: order_by(sort_order, id)), so
   learners see nothing move.
2. Add deferrable, initially deferred unique constraints, like lessons'.

Expand-first: the running image keeps working. create_track appends max+1;
create_module's "shift successors +1, then insert" only collides
mid-transaction, which a deferred constraint allows.

Downgrade drops the constraints; the renumbering is not undone (harmless:
relative order is unchanged).

Revision ID: b0c1d2e3f4a5
Revises: a9b0c1d2e3f4
Create Date: 2026-10-05
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "b0c1d2e3f4a5"
down_revision: str | None = "a9b0c1d2e3f4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

RENUMBER_TRACKS_SQL = """
UPDATE tracks AS t SET sort_order = r.rn
FROM (SELECT id, ROW_NUMBER() OVER (ORDER BY sort_order, id) - 1 AS rn FROM tracks) AS r
WHERE t.id = r.id AND t.sort_order IS DISTINCT FROM r.rn
"""

RENUMBER_MODULES_SQL = """
UPDATE modules AS m SET sort_order = r.rn
FROM (
    SELECT id, ROW_NUMBER() OVER (PARTITION BY track_id ORDER BY sort_order, id) - 1 AS rn
    FROM modules
) AS r
WHERE m.id = r.id AND m.sort_order IS DISTINCT FROM r.rn
"""


def upgrade() -> None:
    op.execute(RENUMBER_TRACKS_SQL)
    op.execute(RENUMBER_MODULES_SQL)
    op.create_unique_constraint(
        op.f("uq_tracks_sort_order"),
        "tracks",
        ["sort_order"],
        deferrable=True,
        initially="DEFERRED",
    )
    op.create_unique_constraint(
        op.f("uq_modules_track_id_sort_order"),
        "modules",
        ["track_id", "sort_order"],
        deferrable=True,
        initially="DEFERRED",
    )


def downgrade() -> None:
    op.drop_constraint(op.f("uq_modules_track_id_sort_order"), "modules", type_="unique")
    op.drop_constraint(op.f("uq_tracks_sort_order"), "tracks", type_="unique")
```

- [ ] **Step 4: Declare the constraints on the models**

In `backend/src/db/models/learning.py`, add `UniqueConstraint` to the `Track` table args:

```python
class Track(Base):
    __tablename__ = "tracks"
    __table_args__ = (
        CheckConstraint("track_type IN ('general', 'tool')", name="track_type"),
        CheckConstraint(
            "required_level IN ('explore', 'practitioner', 'integrator', 'multiplier')",
            name="required_level",
        ),
        # Deferred for the same reason as lessons' (reorders pass through
        # duplicates mid-transaction). Migration b0c1d2e3f4a5 renumbered the
        # live duplicates before adding it.
        UniqueConstraint("sort_order", deferrable=True, initially="DEFERRED"),
    )
```

Give `Module` table args (it has none today):

```python
class Module(Base):
    __tablename__ = "modules"
    __table_args__ = (
        UniqueConstraint("track_id", "sort_order", deferrable=True, initially="DEFERRED"),
    )
```

Then update the `Lesson` comment, which says "Lessons only, not modules or tracks". Replace that sentence with: `Tracks and modules got the same deferred constraint in migration b0c1d2e3f4a5 (B4).`

- [ ] **Step 5: Make the factories pick the next free position**

In `backend/tests/fixtures/factories.py`, change `create_track` and `create_module`:

```python
async def create_track(
    session: AsyncSession,
    name: str = "Core Track",
    *,
    track_type: str = "general",
    color: str | None = None,
    sort_order: int | None = None,
    required_level: str = "explore",
    is_introduction: bool = False,
) -> Track:
    """sort_order=None → the next free position (tracks.sort_order is unique)."""
    if sort_order is None:
        current = (await session.execute(select(func.max(Track.sort_order)))).scalar_one()
        sort_order = 0 if current is None else current + 1
    return await _persist(
        session,
        Track(
            name=name,
            track_type=track_type,
            color=color,
            sort_order=sort_order,
            required_level=required_level,
            is_introduction=is_introduction,
        ),
    )


async def create_module(
    session: AsyncSession, track: Track, title: str = "Module", *, sort_order: int | None = None
) -> Module:
    """sort_order=None → the next free position in the track."""
    if sort_order is None:
        current = (
            await session.execute(
                select(func.max(Module.sort_order)).where(Module.track_id == track.id)
            )
        ).scalar_one()
        sort_order = 0 if current is None else current + 1
    return await _persist(session, Module(track_id=track.id, title=title, sort_order=sort_order))
```

Add `from sqlalchemy import func, select` to the factories' imports if it's missing.

- [ ] **Step 6: Run the new tests, then the whole integration suite**

Run: `cd backend && uv run pytest tests/integration/test_models/test_track_module_sort_order_uniqueness.py -v -p no:randomly`
Expected: PASS (4).

Run: `cd backend && uv run pytest tests/integration -q -n auto`
Expected: PASS. Any failure is a test that passes **explicit** tied `sort_order=` values for two tracks, or for two modules of one track (36 call sites pass one). Fix each by giving distinct values or dropping the argument; don't touch production code for it.

Run: `cd backend && uv run alembic heads`
Expected: `b0c1d2e3f4a5 (head)` (reads files only).

- [ ] **Step 7: Commit**

```bash
git add backend/alembic/versions/b0c1d2e3f4a5_unique_track_module_sort_order.py backend/src/db/models/learning.py backend/tests
git commit -m "feat(content): unique deferred sort_order on tracks and modules (B4, #145)"
```

---

### Task 2: Pure prerequisite cycle check

**Files:**
- Create: `backend/src/core/prerequisites.py`
- Test: `backend/tests/unit/test_prerequisites.py`

**Interfaces:**
- Produces: `would_create_cycle(edges: Iterable[tuple[uuid.UUID, uuid.UUID]], module_id: uuid.UUID, prerequisite_ids: Iterable[uuid.UUID]) -> bool`. `edges` are `(module_id, prerequisite_module_id)` pairs of the whole graph today; the module's own current edges are replaced by the new set.

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/unit/test_prerequisites.py
from __future__ import annotations

import uuid

from src.core.prerequisites import would_create_cycle

A, B, C, D = (uuid.uuid4() for _ in range(4))


def test_self_is_a_cycle() -> None:
    assert would_create_cycle([], A, [A])


def test_two_step_cycle() -> None:
    # B requires A today; now A would require B.
    assert would_create_cycle([(B, A)], A, [B])


def test_three_step_cycle() -> None:
    # C requires B, B requires A; A would require C.
    assert would_create_cycle([(C, B), (B, A)], A, [C])


def test_a_chain_without_a_loop_is_fine() -> None:
    # C requires B; A would require C. Nothing leads back to A.
    assert not would_create_cycle([(C, B)], A, [C])


def test_the_modules_own_old_edges_are_replaced() -> None:
    # A requires B today (A, B); the new set drops B and adds C. B → A does
    # not exist, so no cycle, and the old A → B edge must not count.
    assert not would_create_cycle([(A, B), (C, D)], A, [C])


def test_an_empty_set_never_cycles() -> None:
    assert not would_create_cycle([(B, A), (A, B)], A, [])
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd backend && uv run pytest tests/unit/test_prerequisites.py -v`
Expected: FAIL with `ModuleNotFoundError: src.core.prerequisites`.

- [ ] **Step 3: Implement**

```python
# backend/src/core/prerequisites.py
"""Module prerequisite graph rules (spec 2026-10-05, B4). Pure."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import uuid
    from collections.abc import Iterable

__all__ = ["would_create_cycle"]


def would_create_cycle(
    edges: Iterable[tuple[uuid.UUID, uuid.UUID]],
    module_id: uuid.UUID,
    prerequisite_ids: Iterable[uuid.UUID],
) -> bool:
    """True when giving `module_id` exactly `prerequisite_ids` would make it
    depend on itself, directly or through a chain. `edges` are the graph's
    (module, prerequisite) pairs today; the module's own edges are replaced.

    A cycle locks every module on it forever (each waits for the next)."""
    requires: dict[uuid.UUID, set[uuid.UUID]] = {}
    for module, prerequisite in edges:
        if module != module_id:
            requires.setdefault(module, set()).add(prerequisite)
    stack = list(prerequisite_ids)
    seen: set[uuid.UUID] = set()
    while stack:
        current = stack.pop()
        if current == module_id:
            return True
        if current in seen:
            continue
        seen.add(current)
        stack.extend(requires.get(current, ()))
    return False
```

- [ ] **Step 4: Run to verify it passes**

Run: `cd backend && uv run pytest tests/unit/test_prerequisites.py -v`
Expected: PASS (6).

- [ ] **Step 5: Commit**

```bash
git add backend/src/core/prerequisites.py backend/tests/unit/test_prerequisites.py
git commit -m "feat(content): prerequisite cycle check (B4, #145)"
```

---

### Task 3: Repository operations

**Files:**
- Modify: `backend/src/repositories/base.py` (`AbstractContentRepository`, `AbstractAssignmentRepository`)
- Modify: `backend/src/repositories/content_repository.py`
- Modify: `backend/src/repositories/assignment_repository.py`
- Test: `backend/tests/integration/test_repositories/test_content_structure_repository.py`

**Interfaces:**
- Produces on `AbstractContentRepository`:
  - `update_track(track: Track, values: dict[str, Any]) -> Track`;
  - `delete_track(track: Track) -> None` (deletes, then renumbers the remaining tracks `0..n-1`, one commit);
  - `set_track_orders(orders: list[tuple[uuid.UUID, int]]) -> None`;
  - `update_module(module: Module, values: dict[str, Any]) -> Module` (title and description only);
  - `move_module(module: Module, track_id: uuid.UUID) -> Module` (append to the destination, renumber the source, one commit);
  - `set_module_orders(orders: list[tuple[uuid.UUID, int]]) -> None`;
  - `set_prerequisites(module_id: uuid.UUID, prerequisite_ids: list[uuid.UUID]) -> None` (replace the set, one commit);
  - `move_lesson(lesson: Lesson, module_id: uuid.UUID) -> Lesson` (append, renumber the source, one commit);
  - `learner_counts_for_lessons(lesson_ids: list[uuid.UUID]) -> tuple[int, int]` (distinct users with a `user_lessons` row, distinct users with a `lesson_progress` row);
  - **changed:** `delete_module(module)` now also renumbers the remaining modules of its track in the same commit.
- Produces on `AbstractAssignmentRepository`:
  - `user_ids_with_module(module_id: uuid.UUID) -> set[uuid.UUID]`;
  - `add_user_lesson_pairs(pairs: list[tuple[uuid.UUID, uuid.UUID]], *, assigned_via: str = "manual") -> int` (insert, skipping existing pairs; returns rows inserted; one commit).

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/integration/test_repositories/test_content_structure_repository.py
"""B4 structure operations: each is one commit and leaves dense 0..n-1 order."""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.repositories.assignment_repository import AssignmentRepository
from src.repositories.content_repository import ContentRepository
from tests.fixtures.factories import (
    assign_lesson,
    assign_module,
    complete_lesson,
    create_lesson,
    create_module,
    create_track,
    create_user,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


async def _orders(repo: ContentRepository, track_id) -> list[tuple[str, int]]:  # noqa: ANN001
    return [(m.title, m.sort_order) for m in await repo.list_modules(track_id)]


async def test_move_module_renumbers_both_tracks(db_session: AsyncSession) -> None:
    repo = ContentRepository(db_session)
    source = await create_track(db_session, "Source")
    dest = await create_track(db_session, "Dest")
    a = await create_module(db_session, source, "A")
    await create_module(db_session, source, "B")
    await create_module(db_session, dest, "X")

    moved = await repo.move_module(a, dest.id)

    assert moved.track_id == dest.id
    assert await _orders(repo, source.id) == [("B", 0)]
    assert await _orders(repo, dest.id) == [("X", 0), ("A", 1)]


async def test_move_lesson_renumbers_both_modules(db_session: AsyncSession) -> None:
    repo = ContentRepository(db_session)
    track = await create_track(db_session)
    m1 = await create_module(db_session, track, "M1")
    m2 = await create_module(db_session, track, "M2")
    l1 = await create_lesson(db_session, m1, "L1", sort_order=0)
    await create_lesson(db_session, m1, "L2", sort_order=1)
    await create_lesson(db_session, m2, "K1", sort_order=0)

    await repo.move_lesson(l1, m2.id)

    assert [(le.title, le.sort_order) for le in await repo.list_lessons(m1.id)] == [("L2", 0)]
    assert [(le.title, le.sort_order) for le in await repo.list_lessons(m2.id)] == [
        ("K1", 0),
        ("L1", 1),
    ]


async def test_delete_track_cascades_and_renumbers(db_session: AsyncSession) -> None:
    repo = ContentRepository(db_session)
    first = await create_track(db_session, "First")
    doomed = await create_track(db_session, "Doomed")
    last = await create_track(db_session, "Last")
    module = await create_module(db_session, doomed, "M")
    await create_lesson(db_session, module, "L")

    await repo.delete_track(doomed)

    ours = [t for t in await repo.list_tracks() if t.id in {first.id, last.id}]
    assert [t.sort_order for t in ours] == sorted(t.sort_order for t in ours)
    assert all(t.sort_order in range(len(await repo.list_tracks())) for t in ours)
    assert await repo.get_module(module.id) is None


async def test_delete_module_renumbers_its_track(db_session: AsyncSession) -> None:
    repo = ContentRepository(db_session)
    track = await create_track(db_session)
    await create_module(db_session, track, "A")
    b = await create_module(db_session, track, "B")
    await create_module(db_session, track, "C")

    await repo.delete_module(b)

    assert await _orders(repo, track.id) == [("A", 0), ("C", 1)]


async def test_set_prerequisites_replaces_the_set(db_session: AsyncSession) -> None:
    repo = ContentRepository(db_session)
    track = await create_track(db_session)
    a = await create_module(db_session, track, "A")
    b = await create_module(db_session, track, "B")
    c = await create_module(db_session, track, "C")
    await repo.set_prerequisites(c.id, [a.id])

    await repo.set_prerequisites(c.id, [b.id])

    pairs = {(p.module_id, p.prerequisite_module_id) for p in await repo.list_prerequisites()}
    assert (c.id, b.id) in pairs
    assert (c.id, a.id) not in pairs


async def test_learner_counts_for_lessons(db_session: AsyncSession) -> None:
    repo = ContentRepository(db_session)
    track = await create_track(db_session)
    module = await create_module(db_session, track)
    lesson = await create_lesson(db_session, module)
    ann = await create_user(db_session, email="b4-count-ann@example.com")
    bob = await create_user(db_session, email="b4-count-bob@example.com")
    await assign_lesson(db_session, ann, lesson)
    await assign_lesson(db_session, bob, lesson)
    await complete_lesson(db_session, ann, lesson)

    assert await repo.learner_counts_for_lessons([lesson.id]) == (2, 1)
    assert await repo.learner_counts_for_lessons([]) == (0, 0)


async def test_gap_reads_and_pair_insert(db_session: AsyncSession) -> None:
    repo = AssignmentRepository(db_session)
    track = await create_track(db_session)
    module = await create_module(db_session, track)
    old = await create_lesson(db_session, module, "Old", sort_order=0)
    new = await create_lesson(db_session, module, "New", sort_order=1)
    ann = await create_user(db_session, email="b4-gap-ann@example.com")
    await assign_module(db_session, ann, module)
    await assign_lesson(db_session, ann, old)

    assert await repo.user_ids_with_module(module.id) == {ann.id}
    inserted = await repo.add_user_lesson_pairs([(ann.id, new.id), (ann.id, old.id)])
    assert inserted == 1
    assert await repo.lesson_ids_for_user(ann.id) == {old.id, new.id}
    assert await repo.add_user_lesson_pairs([]) == 0
```

- [ ] **Step 2: Run to verify they fail**

Run: `cd backend && uv run pytest tests/integration/test_repositories/test_content_structure_repository.py -v -p no:randomly`
Expected: FAIL with `AttributeError` on the missing methods.

- [ ] **Step 3: Add the abstract methods**

In `backend/src/repositories/base.py`, inside `AbstractContentRepository` (after `set_lesson_orders`):

```python
    @abstractmethod
    async def update_track(self, track: Track, values: dict[str, Any]) -> Track:
        """Set name/color/track_type/required_level and commit."""

    @abstractmethod
    async def delete_track(self, track: Track) -> None:
        """Delete (modules, lessons, assignments, progress cascade), then
        renumber the remaining tracks 0..n-1, in one commit."""

    @abstractmethod
    async def set_track_orders(self, orders: list[tuple[uuid.UUID, int]]) -> None:
        """Write the given positions in one commit (deferred uniqueness)."""

    @abstractmethod
    async def update_module(self, module: Module, values: dict[str, Any]) -> Module:
        """Set title/description and commit. Moving is move_module."""

    @abstractmethod
    async def move_module(self, module: Module, track_id: uuid.UUID) -> Module:
        """Append to the destination track and renumber the source, one commit."""

    @abstractmethod
    async def set_module_orders(self, orders: list[tuple[uuid.UUID, int]]) -> None:
        """Write the given positions in one commit (deferred uniqueness)."""

    @abstractmethod
    async def set_prerequisites(
        self, module_id: uuid.UUID, prerequisite_ids: list[uuid.UUID]
    ) -> None:
        """Replace the module's prerequisite set, one commit."""

    @abstractmethod
    async def move_lesson(self, lesson: Lesson, module_id: uuid.UUID) -> Lesson:
        """Append to the destination module and renumber the source, one commit."""

    @abstractmethod
    async def learner_counts_for_lessons(self, lesson_ids: list[uuid.UUID]) -> tuple[int, int]:
        """(distinct users assigned any of them, distinct users with progress
        on any of them): the delete warning's counts."""
```

Also change the docstring of `AbstractContentRepository.delete_module` (or add one) to: `"""Delete (cascades) and renumber the track's remaining modules, one commit."""`

Inside `AbstractAssignmentRepository`:

```python
    @abstractmethod
    async def user_ids_with_module(self, module_id: uuid.UUID) -> set[uuid.UUID]:
        """Users with a user_modules row for the module."""

    @abstractmethod
    async def add_user_lesson_pairs(
        self, pairs: list[tuple[uuid.UUID, uuid.UUID]], *, assigned_via: str = "manual"
    ) -> int:
        """Insert (user_id, lesson_id) rows, skipping existing ones; one commit.
        Returns how many were inserted."""
```

- [ ] **Step 4: Implement in `ContentRepository`**

Add `delete` to the `sqlalchemy` import (`from sqlalchemy import delete, func, select, tuple_, update`), plus `from src.db.models import LessonProgress, UserLesson` alongside the existing model import. Then add:

```python
    # -- B4 structure operations (spec 2026-10-05). Each is one commit; the
    # deferred unique constraints let a renumber pass through duplicates.

    async def update_track(self, track: Track, values: dict[str, Any]) -> Track:
        for field, value in values.items():
            setattr(track, field, value)
        await self._session.commit()
        await self._session.refresh(track)
        return track

    async def delete_track(self, track: Track) -> None:
        await self._session.delete(track)
        await self._session.flush()
        remaining = (await self._session.execute(
            select(Track.id).order_by(Track.sort_order, Track.id)
        )).scalars().all()
        await self._write_orders(Track, list(remaining))
        await self._session.commit()

    async def set_track_orders(self, orders: list[tuple[uuid.UUID, int]]) -> None:
        if orders:
            await self._session.execute(
                update(Track), [{"id": i, "sort_order": o} for i, o in orders]
            )
        await self._session.commit()

    async def update_module(self, module: Module, values: dict[str, Any]) -> Module:
        for field, value in values.items():
            setattr(module, field, value)
        await self._session.commit()
        await self._session.refresh(module)
        return module

    async def move_module(self, module: Module, track_id: uuid.UUID) -> Module:
        source = module.track_id
        top = (await self._session.execute(
            select(func.max(Module.sort_order)).where(Module.track_id == track_id)
        )).scalar_one()
        module.track_id = track_id
        module.sort_order = 0 if top is None else top + 1
        await self._session.flush()
        siblings = (await self._session.execute(
            select(Module.id)
            .where(Module.track_id == source)
            .order_by(Module.sort_order, Module.id)
        )).scalars().all()
        await self._write_orders(Module, list(siblings))
        await self._session.commit()
        await self._session.refresh(module)
        return module

    async def set_module_orders(self, orders: list[tuple[uuid.UUID, int]]) -> None:
        if orders:
            await self._session.execute(
                update(Module), [{"id": i, "sort_order": o} for i, o in orders]
            )
        await self._session.commit()

    async def set_prerequisites(
        self, module_id: uuid.UUID, prerequisite_ids: list[uuid.UUID]
    ) -> None:
        await self._session.execute(
            delete(ModulePrerequisite).where(ModulePrerequisite.module_id == module_id)
        )
        self._session.add_all(
            ModulePrerequisite(module_id=module_id, prerequisite_module_id=prereq_id)
            for prereq_id in prerequisite_ids
        )
        await self._session.commit()

    async def move_lesson(self, lesson: Lesson, module_id: uuid.UUID) -> Lesson:
        source = lesson.module_id
        top = (await self._session.execute(
            select(func.max(Lesson.sort_order)).where(Lesson.module_id == module_id)
        )).scalar_one()
        lesson.module_id = module_id
        lesson.sort_order = 0 if top is None else top + 1
        await self._session.flush()
        siblings = (await self._session.execute(
            select(Lesson.id)
            .where(Lesson.module_id == source)
            .order_by(Lesson.sort_order, Lesson.id)
        )).scalars().all()
        await self._write_orders(Lesson, list(siblings))
        await self._session.commit()
        await self._session.refresh(lesson)
        return lesson

    async def learner_counts_for_lessons(self, lesson_ids: list[uuid.UUID]) -> tuple[int, int]:
        if not lesson_ids:
            return (0, 0)
        assigned = (await self._session.execute(
            select(func.count(func.distinct(UserLesson.user_id))).where(
                UserLesson.lesson_id.in_(lesson_ids)
            )
        )).scalar_one()
        with_progress = (await self._session.execute(
            select(func.count(func.distinct(LessonProgress.user_id))).where(
                LessonProgress.lesson_id.in_(lesson_ids)
            )
        )).scalar_one()
        return (int(assigned), int(with_progress))

    async def _write_orders(self, model: type[Track | Module | Lesson], ids: list[uuid.UUID]) -> None:
        """0..n-1 in the given order; no commit (callers commit once)."""
        if ids:
            await self._session.execute(
                update(model), [{"id": i, "sort_order": o} for o, i in enumerate(ids)]
            )
```

Replace the existing `delete_module` with:

```python
    async def delete_module(self, module: Module) -> None:
        track_id = module.track_id
        await self._session.delete(module)
        await self._session.flush()
        siblings = (await self._session.execute(
            select(Module.id)
            .where(Module.track_id == track_id)
            .order_by(Module.sort_order, Module.id)
        )).scalars().all()
        await self._write_orders(Module, list(siblings))
        await self._session.commit()
```

Run `uv run poe format` afterwards; the parenthesised `(await …).scalars()` lines will be reflowed.

- [ ] **Step 5: Implement in `AssignmentRepository`**

```python
    async def user_ids_with_module(self, module_id: uuid.UUID) -> set[uuid.UUID]:
        result = await self._session.execute(
            select(UserModule.user_id).where(UserModule.module_id == module_id)
        )
        return set(result.scalars().all())

    async def add_user_lesson_pairs(
        self, pairs: list[tuple[uuid.UUID, uuid.UUID]], *, assigned_via: str = "manual"
    ) -> int:
        if not pairs:
            return 0
        result = await self._session.execute(
            pg_insert(UserLesson)
            .values(
                [
                    {"user_id": user_id, "lesson_id": lesson_id, "assigned_via": assigned_via}
                    for user_id, lesson_id in pairs
                ]
            )
            .on_conflict_do_nothing(index_elements=["user_id", "lesson_id"])
            .returning(UserLesson.id)
        )
        inserted = len(result.scalars().all())
        await self._session.commit()
        return inserted
```

- [ ] **Step 6: Patch the in-memory fakes**

`grep -rn "AbstractContentRepository)\|AbstractAssignmentRepository)" backend/src backend/tests backend/evals` lists every concrete subclass. Each one must implement the new abstract methods, or `ty` and the eval tests fail (this happened in B3). Give a fake's unused methods a `raise NotImplementedError` body.

- [ ] **Step 7: Run the tests**

Run: `cd backend && uv run pytest tests/integration/test_repositories/test_content_structure_repository.py tests/integration/test_routers/test_admin_content.py -v -p no:randomly`
Expected: PASS. `test_admin_content.py` still passing proves the `delete_module` change kept its behaviour.

Run: `cd backend && uv run poe format && uv run poe lint-src && uv run poe ty-src`
Expected: clean.

- [ ] **Step 8: Commit**

```bash
git add backend/src/repositories backend/tests/integration/test_repositories/test_content_structure_repository.py backend/evals
git commit -m "feat(content): atomic structure operations in the repositories (B4, #145)"
```

---

### Task 4: ContentService structure use cases (edit, move, reorder, prerequisites, impact, tree)

**Files:**
- Modify: `backend/src/services/content_service.py`
- Modify: `backend/src/core/dependencies/domain.py:137-140`
- Modify: `backend/tests/unit/test_content_service_size.py:25` (constructor)
- Test: `backend/tests/unit/test_content_structure_service.py`

**Interfaces:**
- Consumes: Task 2 `would_create_cycle`; Task 3 repository methods.
- Produces:
  - Constructor: `ContentService(content, *, assignments: AbstractAssignmentRepository, users: AbstractUserRepository, project_admins: AbstractProjectAdminRepository)`.
  - `update_track(track_id, values: dict[str, Any]) -> Track`;
  - `delete_track(track_id) -> None`;
  - `reorder_tracks(track_ids: list[UUID]) -> None`;
  - `update_module(module_id, values: dict[str, Any]) -> Module` (`values` may carry `title`, `description`, `track_id`; a different `track_id` moves);
  - `reorder_modules(track_id, module_ids: list[UUID]) -> None`;
  - `set_prerequisites(module_id, prerequisite_ids: list[UUID]) -> None`;
  - `update_lesson(lesson_id, values)`, which now accepts `module_id`;
  - `track_impact(track_id) -> DeleteImpact` and `module_impact(module_id) -> DeleteImpact`;
  - `content_tree() -> list[dict[str, Any]]` (the tree shape of the spec).
- Produces dataclass `DeleteImpact(modules: int, lessons: int, learners_assigned: int, learners_with_progress: int)` in `content_service.py`.

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/unit/test_content_structure_service.py
"""ContentService B4 rules on fake repositories (spec 2026-10-05)."""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from src.repositories.base import (
    AbstractAssignmentRepository,
    AbstractContentRepository,
    AbstractProjectAdminRepository,
    AbstractUserRepository,
)
from src.services.content_service import ContentService, DeleteImpact
from src.services.exceptions import InvalidRequestError, NotFoundError


def _ids(n: int) -> list[uuid.UUID]:
    return [uuid.uuid4() for _ in range(n)]


def _service() -> tuple[ContentService, AsyncMock]:
    content = AsyncMock(spec=AbstractContentRepository)
    service = ContentService(
        content,
        assignments=AsyncMock(spec=AbstractAssignmentRepository),
        users=AsyncMock(spec=AbstractUserRepository),
        project_admins=AsyncMock(spec=AbstractProjectAdminRepository),
    )
    return service, content


async def test_update_track_keeps_type_and_level_independent() -> None:
    service, content = _service()
    track = SimpleNamespace(id=uuid.uuid4(), track_type="general", required_level="explore")
    content.get_track.return_value = track

    await service.update_track(track.id, {"track_type": "tool"})

    content.update_track.assert_awaited_once_with(track, {"track_type": "tool"})


async def test_update_unknown_track_is_404() -> None:
    service, content = _service()
    content.get_track.return_value = None
    with pytest.raises(NotFoundError):
        await service.update_track(uuid.uuid4(), {"name": "x"})


async def test_reorder_tracks_needs_the_exact_set() -> None:
    service, content = _service()
    a, b = _ids(2)
    content.list_tracks.return_value = [SimpleNamespace(id=a), SimpleNamespace(id=b)]

    with pytest.raises(InvalidRequestError):
        await service.reorder_tracks([a])
    await service.reorder_tracks([b, a])

    content.set_track_orders.assert_awaited_once_with([(b, 0), (a, 1)])


async def test_update_module_moves_when_the_track_changes() -> None:
    service, content = _service()
    old_track, new_track = _ids(2)
    module = SimpleNamespace(id=uuid.uuid4(), track_id=old_track)
    content.get_module.return_value = module
    content.get_track.return_value = SimpleNamespace(id=new_track)
    content.move_module.return_value = module

    await service.update_module(module.id, {"title": "New", "track_id": new_track})

    content.move_module.assert_awaited_once_with(module, new_track)
    content.update_module.assert_awaited_once_with(module, {"title": "New"})


async def test_move_module_to_its_own_track_is_a_noop() -> None:
    service, content = _service()
    track_id = uuid.uuid4()
    module = SimpleNamespace(id=uuid.uuid4(), track_id=track_id)
    content.get_module.return_value = module

    await service.update_module(module.id, {"track_id": track_id})

    content.move_module.assert_not_awaited()
    content.update_module.assert_not_awaited()


async def test_reorder_modules_needs_the_tracks_exact_set() -> None:
    service, content = _service()
    track_id = uuid.uuid4()
    a, b = _ids(2)
    content.get_track.return_value = SimpleNamespace(id=track_id)
    content.list_modules.return_value = [SimpleNamespace(id=a), SimpleNamespace(id=b)]

    with pytest.raises(InvalidRequestError):
        await service.reorder_modules(track_id, [a, a])
    await service.reorder_modules(track_id, [b, a])

    content.list_modules.assert_awaited_with(track_id)
    content.set_module_orders.assert_awaited_once_with([(b, 0), (a, 1)])


async def test_prerequisites_refuse_a_cycle_naming_the_module() -> None:
    service, content = _service()
    a, b = _ids(2)
    content.get_module.return_value = SimpleNamespace(id=a, title="Prompting basics")
    content.count_modules_by_ids.return_value = 1
    content.list_prerequisites.return_value = [
        SimpleNamespace(module_id=b, prerequisite_module_id=a)
    ]

    with pytest.raises(InvalidRequestError, match="Prompting basics"):
        await service.set_prerequisites(a, [b])
    content.set_prerequisites.assert_not_awaited()


async def test_prerequisites_dedupe_and_allow_cross_track_chains() -> None:
    service, content = _service()
    a, b = _ids(2)
    content.get_module.return_value = SimpleNamespace(id=a, title="A")
    content.count_modules_by_ids.return_value = 1
    content.list_prerequisites.return_value = []

    await service.set_prerequisites(a, [b, b])

    content.set_prerequisites.assert_awaited_once_with(a, [b])


async def test_prerequisites_with_an_unknown_id_are_404() -> None:
    service, content = _service()
    a, b = _ids(2)
    content.get_module.return_value = SimpleNamespace(id=a, title="A")
    content.count_modules_by_ids.return_value = 0
    with pytest.raises(NotFoundError):
        await service.set_prerequisites(a, [b])


async def test_update_lesson_with_module_id_moves_it() -> None:
    service, content = _service()
    old, new = _ids(2)
    lesson = SimpleNamespace(id=uuid.uuid4(), module_id=old)
    content.get_lesson.return_value = lesson
    content.get_module.return_value = SimpleNamespace(id=new)
    content.move_lesson.return_value = lesson

    await service.update_lesson(lesson.id, {"module_id": new})

    content.move_lesson.assert_awaited_once_with(lesson, new)
    content.update_lesson.assert_not_awaited()


async def test_track_impact_counts_everything_below_it() -> None:
    service, content = _service()
    track_id, m1, m2 = _ids(3)
    content.get_track.return_value = SimpleNamespace(id=track_id)
    content.list_modules.return_value = [SimpleNamespace(id=m1), SimpleNamespace(id=m2)]
    lessons = [SimpleNamespace(id=uuid.uuid4(), module_id=m) for m in (m1, m1, m2)]
    content.list_lesson_summaries.return_value = [
        *lessons,
        SimpleNamespace(id=uuid.uuid4(), module_id=uuid.uuid4()),
    ]
    content.learner_counts_for_lessons.return_value = (14, 9)

    impact = await service.track_impact(track_id)

    assert impact == DeleteImpact(modules=2, lessons=3, learners_assigned=14, learners_with_progress=9)
    content.learner_counts_for_lessons.assert_awaited_once_with([le.id for le in lessons])


async def test_impact_of_an_empty_track_is_zero() -> None:
    service, content = _service()
    content.get_track.return_value = SimpleNamespace(id=uuid.uuid4())
    content.list_modules.return_value = []
    content.list_lesson_summaries.return_value = []
    content.learner_counts_for_lessons.return_value = (0, 0)

    assert await service.track_impact(uuid.uuid4()) == DeleteImpact(0, 0, 0, 0)


async def test_content_tree_nests_counts_and_prerequisites() -> None:
    service, content = _service()
    t, m1, m2 = _ids(3)
    content.list_tracks.return_value = [
        SimpleNamespace(
            id=t, name="General I", color=None, track_type="general",
            required_level="explore", is_introduction=False, sort_order=0,
        )
    ]
    content.list_modules.return_value = [
        SimpleNamespace(id=m1, track_id=t, title="M1", description=None, sort_order=0),
        SimpleNamespace(id=m2, track_id=t, title="M2", description="d", sort_order=1),
    ]
    content.list_prerequisites.return_value = [
        SimpleNamespace(module_id=m2, prerequisite_module_id=m1)
    ]
    content.list_lesson_summaries.return_value = [
        SimpleNamespace(id=uuid.uuid4(), module_id=m2, title="L", sort_order=0)
    ]

    tree = await service.content_tree()

    assert [m["title"] for m in tree[0]["modules"]] == ["M1", "M2"]
    assert tree[0]["modules"][1]["prerequisite_ids"] == [m1]
    assert tree[0]["modules"][1]["lesson_count"] == 1
    assert tree[0]["modules"][0]["lessons"] == []
```

- [ ] **Step 2: Run to verify they fail**

Run: `cd backend && uv run pytest tests/unit/test_content_structure_service.py -v`
Expected: FAIL (`TypeError` on the constructor keywords / `ImportError: DeleteImpact`).

- [ ] **Step 3: Implement**

In `backend/src/services/content_service.py`:

- add `from dataclasses import dataclass`;
- add `from src.core.prerequisites import would_create_cycle`;
- under `TYPE_CHECKING`, import `AbstractAssignmentRepository`, `AbstractProjectAdminRepository` and `AbstractUserRepository`, plus `Module` and `Track` from `src.db.models`;
- add `"DeleteImpact"` to `__all__`.

```python
@dataclass(frozen=True)
class DeleteImpact:
    """What a delete takes with it: the warning's counts (spec 2026-10-05)."""

    modules: int
    lessons: int
    learners_assigned: int
    learners_with_progress: int
```

Replace `__init__`:

```python
    def __init__(
        self,
        content: AbstractContentRepository,
        *,
        assignments: AbstractAssignmentRepository,
        users: AbstractUserRepository,
        project_admins: AbstractProjectAdminRepository,
    ) -> None:
        self._content = content
        # B4: the assignment gap (assign new lessons to learners who hold the
        # module) needs these. Repositories, not services: no service calls.
        self._assignments = assignments
        self._users = users
        self._project_admins = project_admins
```

Add the methods (after `reorder_lessons`):

```python
    # -- B4 structure editing (spec 2026-10-05) ------------------------------

    async def update_track(self, track_id: uuid.UUID, values: dict[str, Any]) -> Track:
        """Type and required level are independent after creation: editing one
        never changes the other."""
        track = await self._content.get_track(track_id)
        if track is None:
            raise NotFoundError("Track")
        if "name" in values:
            values = {**values, "name": values["name"].strip()}
        return await self._content.update_track(track, values)

    async def delete_track(self, track_id: uuid.UUID) -> None:
        track = await self._content.get_track(track_id)
        if track is None:
            raise NotFoundError("Track")
        await self._content.delete_track(track)

    async def reorder_tracks(self, track_ids: list[uuid.UUID]) -> None:
        current = {track.id for track in await self._content.list_tracks()}
        if len(track_ids) != len(current) or set(track_ids) != current:
            raise InvalidRequestError("track_ids must contain exactly every track id once")
        await self._content.set_track_orders([(tid, i) for i, tid in enumerate(track_ids)])

    async def update_module(self, module_id: uuid.UUID, values: dict[str, Any]) -> Module:
        """title/description edit in place; a different track_id moves the
        module to the end of that track. Moving to its own track is a no-op."""
        module = await self._content.get_module(module_id)
        if module is None:
            raise NotFoundError("Module")
        values = dict(values)
        track_id = values.pop("track_id", None)
        if track_id is not None and track_id != module.track_id:
            if await self._content.get_track(track_id) is None:
                raise NotFoundError("Track")
            module = await self._content.move_module(module, track_id)
        if "title" in values:
            values["title"] = values["title"].strip()
        if values:
            module = await self._content.update_module(module, values)
        return module

    async def reorder_modules(self, track_id: uuid.UUID, module_ids: list[uuid.UUID]) -> None:
        if await self._content.get_track(track_id) is None:
            raise NotFoundError("Track")
        current = {module.id for module in await self._content.list_modules(track_id)}
        if len(module_ids) != len(current) or set(module_ids) != current:
            raise InvalidRequestError("module_ids must contain exactly the track's module ids once")
        await self._content.set_module_orders([(mid, i) for i, mid in enumerate(module_ids)])

    async def set_prerequisites(
        self, module_id: uuid.UUID, prerequisite_ids: list[uuid.UUID]
    ) -> None:
        """Replace the set. Unknown ids → 404; a self-loop or a cycle → 400
        naming the module. Cross-track prerequisites stay allowed."""
        module = await self._content.get_module(module_id)
        if module is None:
            raise NotFoundError("Module")
        deduped = list(dict.fromkeys(prerequisite_ids))
        if deduped and await self._content.count_modules_by_ids(deduped) != len(deduped):
            raise NotFoundError("Prerequisite module")
        edges = [
            (p.module_id, p.prerequisite_module_id)
            for p in await self._content.list_prerequisites()
        ]
        if would_create_cycle(edges, module_id, deduped):
            msg = f'This would make "{module.title}" depend on itself.'
            raise InvalidRequestError(msg)
        await self._content.set_prerequisites(module_id, deduped)

    async def track_impact(self, track_id: uuid.UUID) -> DeleteImpact:
        if await self._content.get_track(track_id) is None:
            raise NotFoundError("Track")
        module_ids = {m.id for m in await self._content.list_modules(track_id)}
        return await self._impact(len(module_ids), module_ids)

    async def module_impact(self, module_id: uuid.UUID) -> DeleteImpact:
        if await self._content.get_module(module_id) is None:
            raise NotFoundError("Module")
        return await self._impact(0, {module_id})

    async def _impact(self, modules: int, module_ids: set[uuid.UUID]) -> DeleteImpact:
        lesson_ids = [
            le.id
            for le in await self._content.list_lesson_summaries()
            if le.module_id in module_ids
        ]
        assigned, with_progress = await self._content.learner_counts_for_lessons(lesson_ids)
        return DeleteImpact(modules, len(lesson_ids), assigned, with_progress)

    async def content_tree(self) -> list[dict[str, Any]]:
        """Tracks → modules → lessons in display order, for the admin Content
        page. Four reads, whatever the size of the tree."""
        modules = await self._content.list_modules()
        lessons = await self._content.list_lesson_summaries()
        prerequisites: dict[uuid.UUID, list[uuid.UUID]] = {}
        for link in await self._content.list_prerequisites():
            prerequisites.setdefault(link.module_id, []).append(link.prerequisite_module_id)
        lessons_by_module: dict[uuid.UUID, list[dict[str, Any]]] = {}
        for lesson in lessons:
            lessons_by_module.setdefault(lesson.module_id, []).append(
                {"id": lesson.id, "title": lesson.title, "sort_order": lesson.sort_order}
            )
        modules_by_track: dict[uuid.UUID, list[dict[str, Any]]] = {}
        for module in modules:
            module_lessons = lessons_by_module.get(module.id, [])
            modules_by_track.setdefault(module.track_id, []).append(
                {
                    "id": module.id,
                    "title": module.title,
                    "description": module.description,
                    "sort_order": module.sort_order,
                    "prerequisite_ids": prerequisites.get(module.id, []),
                    "lesson_count": len(module_lessons),
                    "lessons": module_lessons,
                }
            )
        return [
            {
                "id": track.id,
                "name": track.name,
                "color": track.color,
                "track_type": track.track_type,
                "required_level": track.required_level,
                "is_introduction": track.is_introduction,
                "sort_order": track.sort_order,
                "modules": modules_by_track.get(track.id, []),
            }
            for track in await self._content.list_tracks()
        ]
```

At the top of the existing `update_lesson`, right after the `lesson is None` check, add the move:

```python
        values = dict(values)
        module_id = values.pop("module_id", None)
        if module_id is not None and module_id != lesson.module_id:
            if await self._content.get_module(module_id) is None:
                raise NotFoundError("Module")
            lesson = await self._content.move_lesson(lesson, module_id)
        if not values:
            return lesson
```

`list_lesson_summaries()` and `list_modules()` already return items in `(sort_order, id)` order, so the dicts built above come out in display order.

- [ ] **Step 4: Rewire DI and the existing test**

`backend/src/core/dependencies/domain.py`:

```python
def get_content_service(
    content: Annotated[ContentRepository, Depends(get_content_repository)],
    assignments: Annotated[AssignmentRepository, Depends(get_assignment_repository)],
    users: Annotated[UserRepository, Depends(get_user_repository)],
    project_admins: Annotated[ProjectAdminRepository, Depends(get_project_admin_repository)],
) -> ContentService:
    return ContentService(
        content, assignments=assignments, users=users, project_admins=project_admins
    )
```

`get_content_service` is defined *above* `get_assignment_repository` and `get_project_admin_repository` in that file. FastAPI resolves `Depends(...)` names at definition time, so move `get_content_service` below both providers.

`backend/tests/unit/test_content_service_size.py:25`: construct with the three keyword fakes (`AsyncMock(spec=AbstractAssignmentRepository)`, `AsyncMock(spec=AbstractUserRepository)`, `AsyncMock(spec=AbstractProjectAdminRepository)`).

- [ ] **Step 5: Run the tests**

Run: `cd backend && uv run pytest tests/unit/test_content_structure_service.py tests/unit/test_content_service_size.py -v`
Expected: PASS.

Run: `cd backend && uv run poe format && uv run poe lint-src && uv run poe ty-src`
Expected: clean.

- [ ] **Step 6: Commit**

```bash
git add backend/src/services/content_service.py backend/src/core/dependencies/domain.py backend/tests/unit
git commit -m "feat(content): track/module edit, move, reorder, prerequisites, impact, tree (B4, #145)"
```

---

### Task 5: The assignment gap and the Assign action

**Files:**
- Modify: `backend/src/services/content_service.py`
- Test: `backend/tests/unit/test_assignment_gap.py`

**Interfaces:**
- Consumes: Task 3 `user_ids_with_module`, `add_user_lesson_pairs`; existing `AbstractAssignmentRepository.user_lessons_for_users`, `AbstractUserRepository.list_with_org_names`, `AbstractProjectAdminRepository.admin_ids_for_project`, `AbstractContentRepository.list_lesson_summaries`.
- Produces:
  - `ContentService.assignment_gap(module_id: UUID, project_id: UUID | None) -> AssignmentGap`;
  - `ContentService.assign_gap(module_id: UUID, project_id: UUID | None) -> int` (pairs inserted);
  - dataclass `AssignmentGap(lesson_ids: list[UUID], learner_count: int, missing_pairs: int)`.

  `project_id=None` means every learner who holds the module; a project id means that project's learners only (no power admins, none of its own project admins).

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/unit/test_assignment_gap.py
"""The assignment gap: lessons of a module that learners who HOLD the module
don't have yet (new or moved lessons). Spec 2026-10-05, decision 4."""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from src.repositories.base import (
    AbstractAssignmentRepository,
    AbstractContentRepository,
    AbstractProjectAdminRepository,
    AbstractUserRepository,
)
from src.services.content_service import AssignmentGap, ContentService
from src.services.exceptions import NotFoundError

MODULE = uuid.uuid4()
PROJECT = uuid.uuid4()
OLD, NEW, ELSEWHERE = (uuid.uuid4() for _ in range(3))


def _user(role: str = "user") -> SimpleNamespace:
    return SimpleNamespace(id=uuid.uuid4(), role=role, project_id=PROJECT)


class _World:
    def __init__(self) -> None:
        self.ann, self.bob, self.coach, self.power = _user(), _user(), _user(), _user("admin")
        self.outsider = _user()  # holds the module, other project
        self.content = AsyncMock(spec=AbstractContentRepository)
        self.content.get_module.return_value = SimpleNamespace(id=MODULE)
        self.content.list_lesson_summaries.return_value = [
            SimpleNamespace(id=OLD, module_id=MODULE),
            SimpleNamespace(id=NEW, module_id=MODULE),
            SimpleNamespace(id=ELSEWHERE, module_id=uuid.uuid4()),
        ]
        self.assignments = AsyncMock(spec=AbstractAssignmentRepository)
        holders = [self.ann, self.bob, self.coach, self.power, self.outsider]
        self.assignments.user_ids_with_module.return_value = {u.id for u in holders}
        self.assignments.user_lessons_for_users.return_value = [
            SimpleNamespace(user_id=u.id, lesson_id=OLD) for u in holders
        ] + [SimpleNamespace(user_id=self.bob.id, lesson_id=NEW)]
        self.assignments.add_user_lesson_pairs.side_effect = lambda pairs, **_: len(pairs)
        self.users = AsyncMock(spec=AbstractUserRepository)
        self.users.list_with_org_names.return_value = [
            (u, "Acme", "Rollout") for u in (self.ann, self.bob, self.coach, self.power)
        ]
        self.project_admins = AsyncMock(spec=AbstractProjectAdminRepository)
        self.project_admins.admin_ids_for_project.return_value = {self.coach.id}

    def service(self) -> ContentService:
        return ContentService(
            self.content,
            assignments=self.assignments,
            users=self.users,
            project_admins=self.project_admins,
        )


async def test_gap_for_everyone_who_holds_the_module() -> None:
    world = _World()

    gap = await world.service().assignment_gap(MODULE, None)

    # ann, coach, power, outsider miss NEW; bob has it.
    assert gap == AssignmentGap(lesson_ids=[NEW], learner_count=4, missing_pairs=4)


async def test_project_gap_excludes_other_projects_and_staff() -> None:
    world = _World()

    gap = await world.service().assignment_gap(MODULE, PROJECT)

    assert gap == AssignmentGap(lesson_ids=[NEW], learner_count=1, missing_pairs=1)  # ann only
    world.users.list_with_org_names.assert_awaited_once_with(PROJECT)


async def test_assign_inserts_exactly_the_missing_pairs_as_manual() -> None:
    world = _World()

    inserted = await world.service().assign_gap(MODULE, PROJECT)

    assert inserted == 1
    world.assignments.add_user_lesson_pairs.assert_awaited_once_with(
        [(world.ann.id, NEW)], assigned_via="manual"
    )


async def test_an_empty_gap_inserts_nothing() -> None:
    world = _World()
    world.assignments.user_ids_with_module.return_value = {world.bob.id}

    gap = await world.service().assignment_gap(MODULE, None)

    assert gap == AssignmentGap(lesson_ids=[], learner_count=0, missing_pairs=0)
    assert await world.service().assign_gap(MODULE, None) == 0


async def test_unknown_module_is_404() -> None:
    world = _World()
    world.content.get_module.return_value = None
    with pytest.raises(NotFoundError):
        await world.service().assignment_gap(MODULE, None)
```

- [ ] **Step 2: Run to verify they fail**

Run: `cd backend && uv run pytest tests/unit/test_assignment_gap.py -v`
Expected: FAIL with `ImportError: AssignmentGap`.

- [ ] **Step 3: Implement**

In `content_service.py`, add `"AssignmentGap"` to `__all__` and:

```python
@dataclass(frozen=True)
class AssignmentGap:
    """Lessons of a module that some learner holding the module lacks."""

    lesson_ids: list[uuid.UUID]
    learner_count: int
    missing_pairs: int
```

Methods on `ContentService`:

```python
    async def assignment_gap(
        self, module_id: uuid.UUID, project_id: uuid.UUID | None
    ) -> AssignmentGap:
        missing, lesson_order = await self._missing_pairs(module_id, project_id)
        lessons = {lesson_id for _, lesson_id in missing}
        return AssignmentGap(
            lesson_ids=[lid for lid in lesson_order if lid in lessons],
            learner_count=len({user_id for user_id, _ in missing}),
            missing_pairs=len(missing),
        )

    async def assign_gap(self, module_id: uuid.UUID, project_id: uuid.UUID | None) -> int:
        """Insert exactly the missing pairs, stamped like the Assignments page.
        Never removes a row."""
        missing, _ = await self._missing_pairs(module_id, project_id)
        return await self._assignments.add_user_lesson_pairs(missing, assigned_via="manual")

    async def _missing_pairs(
        self, module_id: uuid.UUID, project_id: uuid.UUID | None
    ) -> tuple[list[tuple[uuid.UUID, uuid.UUID]], list[uuid.UUID]]:
        if await self._content.get_module(module_id) is None:
            raise NotFoundError("Module")
        lesson_order = [
            le.id for le in await self._content.list_lesson_summaries() if le.module_id == module_id
        ]
        holders = await self._assignments.user_ids_with_module(module_id)
        if project_id is not None:
            # The B1 rule: a project's learners are its members minus power
            # admins and the project's own admins.
            staff = await self._project_admins.admin_ids_for_project(project_id)
            members = {
                user.id
                for user, _, _ in await self._users.list_with_org_names(project_id)
                if user.role != "admin" and user.id not in staff
            }
            holders &= members
        if not holders or not lesson_order:
            return [], lesson_order
        have = {
            (link.user_id, link.lesson_id)
            for link in await self._assignments.user_lessons_for_users(sorted(holders))
        }
        missing = [
            (user_id, lesson_id)
            for user_id in sorted(holders)
            for lesson_id in lesson_order
            if (user_id, lesson_id) not in have
        ]
        return missing, lesson_order
```

- [ ] **Step 4: Run to verify they pass**

Run: `cd backend && uv run pytest tests/unit/test_assignment_gap.py tests/unit/test_content_structure_service.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/src/services/content_service.py backend/tests/unit/test_assignment_gap.py
git commit -m "feat(content): assignment gap + assign for new and moved lessons (B4, #145)"
```

---

### Task 6: Schemas, routers, authz rows, integration tests

**Files:**
- Modify: `backend/src/schemas/admin_content.py`
- Create: `backend/src/routers/admin_structure.py`
- Modify: `backend/src/routers/admin_content.py` (`update_lesson` passes `module_id`)
- Modify: `backend/src/main.py`
- Modify: `backend/tests/integration/test_routers/test_authz.py` (`_MATRIX`)
- Test: `backend/tests/integration/test_routers/test_admin_structure.py`

**Interfaces:**
- Consumes: Tasks 4–5 service methods; guards `require_power_admin`, `require_project_in_scope`, `AdminScopeDep`.
- Produces HTTP (the frontend relies on these exact paths and shapes):
  - `GET /api/admin/content/tree` → `ContentTreeResponse{tracks: TreeTrack[]}`.
  - `PATCH /api/admin/tracks/{track_id}` body `TrackUpdateRequest{name?, color?, track_type?, required_level?}` → `TrackOut`.
  - `DELETE /api/admin/tracks/{track_id}` → 204.
  - `PUT /api/admin/tracks/order` body `{track_ids}` → 204.
  - `PATCH /api/admin/modules/{module_id}` body `ModuleUpdateRequest{title?, description?, track_id?}` → `ModuleOut` (now with `description`).
  - `PUT /api/admin/tracks/{track_id}/modules/order` body `{module_ids}` → 204.
  - `PUT /api/admin/modules/{module_id}/prerequisites` body `{prerequisite_ids}` → 204.
  - `GET /api/admin/tracks/{track_id}/impact` and `GET /api/admin/modules/{module_id}/impact` → `DeleteImpactResponse{modules, lessons, learners_assigned, learners_with_progress}`.
  - `GET /api/admin/modules/{module_id}/assignment-gap` → `AssignmentGapResponse{lesson_ids, learner_count, missing_pairs}`.
  - `POST /api/admin/modules/{module_id}/assign-new-lessons` → `AssignGapResponse{assigned_pairs}`.
  - The same two under `/api/admin/projects/{project_id}/modules/{module_id}/…`.
  - `PATCH /api/admin/lessons/{lesson_id}` accepts `module_id`.

- [ ] **Step 1: Add the schemas**

Append to `backend/src/schemas/admin_content.py` and add each new name to `__all__`:

```python
Level = Literal["explore", "practitioner", "integrator", "multiplier"]


class TrackUpdateRequest(BaseModel):
    name: str | None = None
    color: str | None = None
    track_type: Literal["tool", "general"] | None = None
    required_level: Level | None = None

    _non_blank = field_validator("name")(require_non_blank)


class TrackOrderRequest(BaseModel):
    track_ids: list[uuid.UUID]


class ModuleUpdateRequest(BaseModel):
    title: str | None = None
    description: str | None = None
    track_id: uuid.UUID | None = None

    _non_blank = field_validator("title")(require_non_blank)


class ModuleOrderRequest(BaseModel):
    module_ids: list[uuid.UUID]


class PrerequisitesRequest(BaseModel):
    prerequisite_ids: list[uuid.UUID]


class TreeLesson(BaseModel):
    id: uuid.UUID
    title: str
    sort_order: int


class TreeModule(BaseModel):
    id: uuid.UUID
    title: str
    description: str | None
    sort_order: int
    prerequisite_ids: list[uuid.UUID]
    lesson_count: int
    lessons: list[TreeLesson]


class TreeTrack(BaseModel):
    id: uuid.UUID
    name: str
    color: str | None
    track_type: str
    required_level: str
    is_introduction: bool
    sort_order: int
    modules: list[TreeModule]


class ContentTreeResponse(BaseModel):
    tracks: list[TreeTrack]


class DeleteImpactResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    modules: int
    lessons: int
    learners_assigned: int
    learners_with_progress: int


class AssignmentGapResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    lesson_ids: list[uuid.UUID]
    learner_count: int
    missing_pairs: int


class AssignGapResponse(BaseModel):
    assigned_pairs: int
```

Give `ModuleOut` a `description: str | None = None` field. Give `LessonUpdateRequest` a `module_id: uuid.UUID | None = None` field.

`model_dump(exclude_unset=True)` keeps an explicit `"color": null`, so setting a track's colour to none works. An explicit `"name": null` reaches `require_non_blank`; check that validator rejects `None`, or add `if v is None: raise ValueError("must not be null")` to the request's own validator.

- [ ] **Step 2: Write the router**

```python
# backend/src/routers/admin_structure.py
"""Content structure editing (B4, spec 2026-10-05-content-structure-editing-design.md).

Edits are power-admin only (content is shared by every project). The tree is
readable by any admin; the project-scoped gap routes let a project admin assign
their own project's learners to lessons added to modules they hold."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status

from src.core.dependencies.admin_scope import (
    AdminScopeDep,
    require_power_admin,
    require_project_in_scope,
)
from src.core.dependencies.domain import get_content_service
from src.db.models import Module, Track
from src.schemas.admin_content import (
    AssignGapResponse,
    AssignmentGapResponse,
    ContentTreeResponse,
    DeleteImpactResponse,
    ModuleOrderRequest,
    ModuleOut,
    ModuleUpdateRequest,
    PrerequisitesRequest,
    TrackOrderRequest,
    TrackOut,
    TrackUpdateRequest,
)
from src.services.content_service import ContentService

__all__ = ["router"]

router = APIRouter(prefix="/api/admin", tags=["admin:content-structure"])

ContentServiceDep = Annotated[ContentService, Depends(get_content_service)]
_POWER = [Depends(require_power_admin)]
_SCOPED = [Depends(require_project_in_scope)]


@router.get("/content/tree", response_model=ContentTreeResponse)
async def content_tree(_scope: AdminScopeDep, service: ContentServiceDep) -> ContentTreeResponse:
    """Every track → module → lesson with counts; any admin (project admins
    read it to find the modules whose new lessons they assign)."""
    return ContentTreeResponse.model_validate({"tracks": await service.content_tree()})


@router.patch("/tracks/{track_id}", response_model=TrackOut, dependencies=_POWER)
async def update_track(
    track_id: uuid.UUID, body: TrackUpdateRequest, service: ContentServiceDep
) -> Track:
    return await service.update_track(track_id, body.model_dump(exclude_unset=True))


@router.delete(
    "/tracks/{track_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=_POWER
)
async def delete_track(track_id: uuid.UUID, service: ContentServiceDep) -> None:
    """Cascades to modules, lessons, assignments and progress (the UI shows
    GET …/impact first)."""
    await service.delete_track(track_id)


@router.put("/tracks/order", status_code=status.HTTP_204_NO_CONTENT, dependencies=_POWER)
async def reorder_tracks(body: TrackOrderRequest, service: ContentServiceDep) -> None:
    await service.reorder_tracks(body.track_ids)


@router.patch("/modules/{module_id}", response_model=ModuleOut, dependencies=_POWER)
async def update_module(
    module_id: uuid.UUID, body: ModuleUpdateRequest, service: ContentServiceDep
) -> Module:
    """A different track_id moves the module to the end of that track."""
    return await service.update_module(module_id, body.model_dump(exclude_unset=True))


@router.put(
    "/tracks/{track_id}/modules/order",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=_POWER,
)
async def reorder_modules(
    track_id: uuid.UUID, body: ModuleOrderRequest, service: ContentServiceDep
) -> None:
    await service.reorder_modules(track_id, body.module_ids)


@router.put(
    "/modules/{module_id}/prerequisites",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=_POWER,
)
async def set_prerequisites(
    module_id: uuid.UUID, body: PrerequisitesRequest, service: ContentServiceDep
) -> None:
    """Replaces the set; a self-loop or cycle → 400 naming the module."""
    await service.set_prerequisites(module_id, body.prerequisite_ids)


@router.get(
    "/tracks/{track_id}/impact", response_model=DeleteImpactResponse, dependencies=_POWER
)
async def track_impact(track_id: uuid.UUID, service: ContentServiceDep) -> DeleteImpactResponse:
    return DeleteImpactResponse.model_validate(await service.track_impact(track_id))


@router.get(
    "/modules/{module_id}/impact", response_model=DeleteImpactResponse, dependencies=_POWER
)
async def module_impact(module_id: uuid.UUID, service: ContentServiceDep) -> DeleteImpactResponse:
    return DeleteImpactResponse.model_validate(await service.module_impact(module_id))


@router.get(
    "/modules/{module_id}/assignment-gap",
    response_model=AssignmentGapResponse,
    dependencies=_POWER,
)
async def assignment_gap(
    module_id: uuid.UUID, service: ContentServiceDep
) -> AssignmentGapResponse:
    return AssignmentGapResponse.model_validate(await service.assignment_gap(module_id, None))


@router.post(
    "/modules/{module_id}/assign-new-lessons",
    response_model=AssignGapResponse,
    dependencies=_POWER,
)
async def assign_gap(module_id: uuid.UUID, service: ContentServiceDep) -> AssignGapResponse:
    return AssignGapResponse(assigned_pairs=await service.assign_gap(module_id, None))


@router.get(
    "/projects/{project_id}/modules/{module_id}/assignment-gap",
    response_model=AssignmentGapResponse,
    dependencies=_SCOPED,
)
async def project_assignment_gap(
    project_id: uuid.UUID, module_id: uuid.UUID, service: ContentServiceDep
) -> AssignmentGapResponse:
    return AssignmentGapResponse.model_validate(
        await service.assignment_gap(module_id, project_id)
    )


@router.post(
    "/projects/{project_id}/modules/{module_id}/assign-new-lessons",
    response_model=AssignGapResponse,
    dependencies=_SCOPED,
)
async def project_assign_gap(
    project_id: uuid.UUID, module_id: uuid.UUID, service: ContentServiceDep
) -> AssignGapResponse:
    return AssignGapResponse(assigned_pairs=await service.assign_gap(module_id, project_id))
```

**Route-order trap:** `PUT /tracks/order` and `PATCH /tracks/{track_id}` use different methods, so they can't collide. But don't add a `PUT /tracks/{track_id}` later without checking.

Register it in `backend/src/main.py`: import `admin_structure` in the alphabetical router import block, and add `app.include_router(admin_structure.router)` after `admin_content`'s include.

In `backend/src/routers/admin_content.py`, `update_lesson` already passes `body.model_dump(exclude_unset=True)`. Nothing changes there beyond the schema field, but its docstring should mention: "`module_id` moves the lesson to the end of that module".

- [ ] **Step 3: Add the authz matrix rows**

In `test_authz.py` `_MATRIX`, in a `# --- content structure (B4) ---` block:

```python
    ("content-tree", "GET", "/api/admin/content/tree",
     lambda s: "/api/admin/content/tree", lambda s: None, "scoped_list"),
    ("track-patch", "PATCH", "/api/admin/tracks/{track_id}",
     lambda s: f"/api/admin/tracks/{s.track.id}", lambda s: {"name": "Renamed"}, "power"),
    ("track-impact", "GET", "/api/admin/tracks/{track_id}/impact",
     lambda s: f"/api/admin/tracks/{s.track.id}/impact", lambda s: None, "power"),
    ("tracks-order", "PUT", "/api/admin/tracks/order",
     lambda s: "/api/admin/tracks/order", lambda s: {"track_ids": [str(s.track.id)]}, "power"),
    ("modules-order", "PUT", "/api/admin/tracks/{track_id}/modules/order",
     lambda s: f"/api/admin/tracks/{s.track.id}/modules/order",
     lambda s: {"module_ids": [str(s.module.id)]}, "power"),
    ("module-patch", "PATCH", "/api/admin/modules/{module_id}",
     lambda s: f"/api/admin/modules/{s.module.id}", lambda s: {"title": "Renamed"}, "power"),
    ("module-prerequisites", "PUT", "/api/admin/modules/{module_id}/prerequisites",
     lambda s: f"/api/admin/modules/{s.module.id}/prerequisites",
     lambda s: {"prerequisite_ids": []}, "power"),
    ("module-impact", "GET", "/api/admin/modules/{module_id}/impact",
     lambda s: f"/api/admin/modules/{s.module.id}/impact", lambda s: None, "power"),
    ("module-gap", "GET", "/api/admin/modules/{module_id}/assignment-gap",
     lambda s: f"/api/admin/modules/{s.module.id}/assignment-gap", lambda s: None, "power"),
    ("module-assign-gap", "POST", "/api/admin/modules/{module_id}/assign-new-lessons",
     lambda s: f"/api/admin/modules/{s.module.id}/assign-new-lessons", lambda s: None, "power"),
    ("project-module-gap", "GET",
     "/api/admin/projects/{project_id}/modules/{module_id}/assignment-gap",
     lambda s: f"/api/admin/projects/{s.project.id}/modules/{s.module.id}/assignment-gap",
     lambda s: None, "scoped"),
    ("project-module-assign-gap", "POST",
     "/api/admin/projects/{project_id}/modules/{module_id}/assign-new-lessons",
     lambda s: f"/api/admin/projects/{s.project.id}/modules/{s.module.id}/assign-new-lessons",
     lambda s: None, "scoped"),
    # Last: deletes the seed track (each row gets a fresh seed, but keep
    # destructive rows at the end of the block for readability).
    ("track-delete", "DELETE", "/api/admin/tracks/{track_id}",
     lambda s: f"/api/admin/tracks/{s.track.id}", lambda s: None, "power"),
```

The `tracks-order` row's body names only the seed track. If the test DB holds other tracks, the admin gets a 400; the matrix accepts that (it rejects only 401/403/500). The same goes for `modules-order`. `uv run poe format` reflows these rows into the file's style.

- [ ] **Step 4: Write the router integration tests**

```python
# backend/tests/integration/test_routers/test_admin_structure.py
"""B4 endpoints end to end (spec 2026-10-05). Rules are pinned in
tests/unit/test_content_structure_service.py and test_assignment_gap.py; here:
wiring, status codes, the cascade, and project isolation."""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.repositories.assignment_repository import AssignmentRepository
from tests.fixtures.auth import auth_headers
from tests.fixtures.factories import (
    assign_lesson,
    assign_module,
    complete_lesson,
    create_company,
    create_lesson,
    create_module,
    create_project,
    create_track,
    create_user,
    make_project_admin,
)

if TYPE_CHECKING:
    from httpx import AsyncClient
    from sqlalchemy.ext.asyncio import AsyncSession

    from src.core.configs.settings import Settings


async def test_tree_lists_modules_with_prerequisites_and_lessons(
    client: AsyncClient, db_session: AsyncSession, test_settings: Settings
) -> None:
    power = await create_user(db_session, email="b4-tree-power@example.com", role="admin")
    track = await create_track(db_session, "B4 Tree")
    first = await create_module(db_session, track, "First")
    second = await create_module(db_session, track, "Second")
    await create_lesson(db_session, second, "Only")
    headers = auth_headers(power, test_settings)
    await client.put(
        f"/api/admin/modules/{second.id}/prerequisites",
        json={"prerequisite_ids": [str(first.id)]},
        headers=headers,
    )

    response = await client.get("/api/admin/content/tree", headers=headers)

    assert response.status_code == 200
    ours = next(t for t in response.json()["tracks"] if t["id"] == str(track.id))
    assert [m["title"] for m in ours["modules"]] == ["First", "Second"]
    assert ours["modules"][1]["prerequisite_ids"] == [str(first.id)]
    assert [le["title"] for le in ours["modules"][1]["lessons"]] == ["Only"]


async def test_a_prerequisite_cycle_is_400(
    client: AsyncClient, db_session: AsyncSession, test_settings: Settings
) -> None:
    power = await create_user(db_session, email="b4-cycle-power@example.com", role="admin")
    track = await create_track(db_session)
    a = await create_module(db_session, track, "Alpha")
    b = await create_module(db_session, track, "Beta")
    headers = auth_headers(power, test_settings)
    ok = await client.put(
        f"/api/admin/modules/{b.id}/prerequisites",
        json={"prerequisite_ids": [str(a.id)]},
        headers=headers,
    )
    assert ok.status_code == 204

    loop = await client.put(
        f"/api/admin/modules/{a.id}/prerequisites",
        json={"prerequisite_ids": [str(b.id)]},
        headers=headers,
    )

    assert loop.status_code == 400
    assert "Alpha" in loop.json()["error"]["message"]


async def test_track_delete_impact_then_cascade(
    client: AsyncClient, db_session: AsyncSession, test_settings: Settings
) -> None:
    power = await create_user(db_session, email="b4-del-power@example.com", role="admin")
    learner = await create_user(db_session, email="b4-del-learner@example.com")
    track = await create_track(db_session, "Doomed")
    module = await create_module(db_session, track)
    lesson = await create_lesson(db_session, module)
    await assign_lesson(db_session, learner, lesson)
    await complete_lesson(db_session, learner, lesson)
    headers = auth_headers(power, test_settings)

    impact = await client.get(f"/api/admin/tracks/{track.id}/impact", headers=headers)
    assert impact.json() == {
        "modules": 1,
        "lessons": 1,
        "learners_assigned": 1,
        "learners_with_progress": 1,
    }

    deleted = await client.delete(f"/api/admin/tracks/{track.id}", headers=headers)
    assert deleted.status_code == 204
    gone = await client.get(f"/api/modules/{module.id}/lessons", headers=headers)
    assert gone.status_code == 404


async def test_move_module_and_lesson(
    client: AsyncClient, db_session: AsyncSession, test_settings: Settings
) -> None:
    power = await create_user(db_session, email="b4-move-power@example.com", role="admin")
    source = await create_track(db_session, "Src")
    dest = await create_track(db_session, "Dst")
    module = await create_module(db_session, source, "Mover")
    target = await create_module(db_session, dest, "Target")
    lesson = await create_lesson(db_session, module, "Traveller")
    headers = auth_headers(power, test_settings)

    moved = await client.patch(
        f"/api/admin/modules/{module.id}", json={"track_id": str(dest.id)}, headers=headers
    )
    assert moved.status_code == 200
    assert moved.json()["track_id"] == str(dest.id)
    assert moved.json()["sort_order"] == 1

    lesson_moved = await client.patch(
        f"/api/admin/lessons/{lesson.id}", json={"module_id": str(target.id)}, headers=headers
    )
    assert lesson_moved.status_code == 200
    assert lesson_moved.json()["module_id"] == str(target.id)


async def test_reorder_with_a_wrong_set_is_400(
    client: AsyncClient, db_session: AsyncSession, test_settings: Settings
) -> None:
    power = await create_user(db_session, email="b4-order-power@example.com", role="admin")
    track = await create_track(db_session)
    a = await create_module(db_session, track, "A")
    await create_module(db_session, track, "B")

    response = await client.put(
        f"/api/admin/tracks/{track.id}/modules/order",
        json={"module_ids": [str(a.id)]},
        headers=auth_headers(power, test_settings),
    )

    assert response.status_code == 400


async def test_project_assign_never_touches_another_project(
    client: AsyncClient, db_session: AsyncSession, test_settings: Settings
) -> None:
    company = await create_company(db_session, "B4 Co")
    ours = await create_project(db_session, company, "B4 Ours")
    theirs = await create_project(db_session, company, "B4 Theirs")
    coach = await create_user(
        db_session, email="b4-coach@example.com", password="hunter2hunter2", project_id=theirs.id
    )
    await make_project_admin(db_session, coach, ours)
    mine = await create_user(db_session, email="b4-mine@example.com", project_id=ours.id)
    other = await create_user(db_session, email="b4-other@example.com", project_id=theirs.id)
    track = await create_track(db_session)
    module = await create_module(db_session, track)
    old = await create_lesson(db_session, module, "Old", sort_order=0)
    for user in (mine, other):
        await assign_module(db_session, user, module)
        await assign_lesson(db_session, user, old)
    new = await create_lesson(db_session, module, "New", sort_order=1)
    headers = auth_headers(coach, test_settings)
    base = f"/api/admin/projects/{ours.id}/modules/{module.id}"

    gap = await client.get(f"{base}/assignment-gap", headers=headers)
    assert gap.json() == {"lesson_ids": [str(new.id)], "learner_count": 1, "missing_pairs": 1}

    assigned = await client.post(f"{base}/assign-new-lessons", headers=headers)
    assert assigned.json() == {"assigned_pairs": 1}
    repo = AssignmentRepository(db_session)
    assert new.id in await repo.lesson_ids_for_user(mine.id)
    assert new.id not in await repo.lesson_ids_for_user(other.id)

    foreign = await client.get(
        f"/api/admin/projects/{theirs.id}/modules/{module.id}/assignment-gap", headers=headers
    )
    assert foreign.status_code == 404
```

- [ ] **Step 5: Run focused, then the full backend suite (checkpoint)**

Run: `cd backend && uv run pytest tests/integration/test_routers/test_admin_structure.py "tests/integration/test_routers/test_authz.py" -v -p no:randomly`
Expected: PASS, including `test_every_admin_route_is_in_the_matrix`.

Run: `cd backend && uv run poe format-check && uv run poe lint-src && uv run poe ty-src && uv run poe test`
Expected: all green; coverage ≥ 90%.

- [ ] **Step 6: Commit**

```bash
git add backend/src backend/tests
git commit -m "feat(content): structure editing endpoints + authz rows (B4, #145)"
```

---

### Task 7: Frontend data layer: API types, hooks, pure tree helpers

**Files:**
- Modify: `frontend/src/api/schema.d.ts` (generated)
- Modify: `frontend/src/pages/admin2/api.ts`
- Create: `frontend/src/lib/contentTree.ts`
- Test: `frontend/src/lib/contentTree.test.ts`

**Interfaces:**
- Consumes: Task 6 HTTP contract.
- Produces from `lib/contentTree.ts`:
  - `type TreeTrack = components['schemas']['TreeTrack']`, `TreeModule`, `TreeLesson`;
  - `filterTree(tracks: TreeTrack[], query: string): TreeTrack[]` (keeps a track when it or any descendant matches, case-insensitively; keeps the matching descendants and their ancestors);
  - `moveInList(ids: string[], id: string, direction: -1 | 1): string[] | null` (`null` at an edge);
  - `impactLabel(impact: DeleteImpact): string`;
  - `gapLabel(gap: AssignmentGap): string | null` (`null` when nothing is missing).
- Produces from `admin2/api.ts`:
  - `useContentTree()`;
  - `useTrackImpact(trackId | null)`, `useModuleImpact(moduleId | null)`;
  - `useAssignmentGap(moduleId | null, projectId: string | null)`;
  - `useContentMutation()`: one mutation over a tagged union of actions, invalidating `['admin','content']`, `['admin','tracks']` and `['admin','learning']` on settle.

- [ ] **Step 1: Regenerate the API types**

Run: `cd frontend && npm run gen:api`
Expected: `schema.d.ts` gains the B4 paths and `TreeTrack`/`TreeModule`/`TreeLesson`/`DeleteImpactResponse`/`AssignmentGapResponse`/`AssignGapResponse`.

- [ ] **Step 2: Write the failing helper tests**

```ts
// frontend/src/lib/contentTree.test.ts
import { describe, expect, it } from 'vitest'
import { filterTree, gapLabel, impactLabel, moveInList, type TreeTrack } from './contentTree'

const tree: TreeTrack[] = [
  {
    id: 't1', name: 'General I', color: null, track_type: 'general', required_level: 'explore',
    is_introduction: false, sort_order: 0,
    modules: [
      { id: 'm1', title: 'Prompting basics', description: null, sort_order: 0, prerequisite_ids: [], lesson_count: 1,
        lessons: [{ id: 'l1', title: 'Ask clearly', sort_order: 0 }] },
      { id: 'm2', title: 'Checking output', description: null, sort_order: 1, prerequisite_ids: [], lesson_count: 0, lessons: [] },
    ],
  },
  {
    id: 't2', name: 'Copilot I', color: null, track_type: 'tool', required_level: 'integrator',
    is_introduction: false, sort_order: 1, modules: [],
  },
]

describe('filterTree', () => {
  it('returns everything for an empty query', () => {
    expect(filterTree(tree, '  ')).toBe(tree)
  })
  it('keeps a matching lesson with its module and track only', () => {
    const result = filterTree(tree, 'ASK')
    expect(result.map(t => t.id)).toEqual(['t1'])
    expect(result[0].modules.map(m => m.id)).toEqual(['m1'])
    expect(result[0].modules[0].lessons.map(l => l.id)).toEqual(['l1'])
  })
  it('keeps a matching track whole', () => {
    expect(filterTree(tree, 'copilot').map(t => t.id)).toEqual(['t2'])
  })
})

describe('moveInList', () => {
  it('swaps with the neighbour', () => {
    expect(moveInList(['a', 'b', 'c'], 'b', -1)).toEqual(['b', 'a', 'c'])
    expect(moveInList(['a', 'b', 'c'], 'b', 1)).toEqual(['a', 'c', 'b'])
  })
  it('returns null at an edge or for an unknown id', () => {
    expect(moveInList(['a', 'b'], 'a', -1)).toBeNull()
    expect(moveInList(['a', 'b'], 'b', 1)).toBeNull()
    expect(moveInList(['a'], 'x', 1)).toBeNull()
  })
})

describe('labels', () => {
  it('spells out a delete impact', () => {
    expect(impactLabel({ modules: 3, lessons: 21, learners_assigned: 20, learners_with_progress: 14 }))
      .toBe('Deletes 3 modules, 21 lessons and the progress of 14 learners.')
    expect(impactLabel({ modules: 0, lessons: 1, learners_assigned: 0, learners_with_progress: 0 }))
      .toBe('Deletes 1 lesson. No learner has progress on it.')
  })
  it('describes the assignment gap, or nothing when there is none', () => {
    expect(gapLabel({ lesson_ids: ['l9'], learner_count: 14, missing_pairs: 14 }))
      .toBe('1 lesson not yet assigned to the 14 learners who have this module.')
    expect(gapLabel({ lesson_ids: [], learner_count: 0, missing_pairs: 0 })).toBeNull()
  })
})
```

- [ ] **Step 3: Run to verify they fail**

Run: `cd frontend && npx vitest run src/lib/contentTree.test.ts`
Expected: FAIL (module not found).

- [ ] **Step 4: Implement the helpers**

```ts
// frontend/src/lib/contentTree.ts
// Pure helpers for the admin Content page (spec 2026-10-05, B4).
import type { components } from '../api/schema'

export type TreeTrack = components['schemas']['TreeTrack']
export type TreeModule = components['schemas']['TreeModule']
export type TreeLesson = components['schemas']['TreeLesson']
export type DeleteImpact = components['schemas']['DeleteImpactResponse']
export type AssignmentGap = components['schemas']['AssignmentGapResponse']

const plural = (n: number, word: string) => `${n} ${word}${n === 1 ? '' : 's'}`

/** Case-insensitive name filter. A matching track or module is kept whole;
 * otherwise only matching descendants and their ancestors remain. */
export function filterTree(tracks: TreeTrack[], query: string): TreeTrack[] {
  const q = query.trim().toLowerCase()
  if (!q) return tracks
  const hit = (text: string) => text.toLowerCase().includes(q)
  return tracks.flatMap(track => {
    if (hit(track.name)) return [track]
    const modules = track.modules.flatMap(module => {
      if (hit(module.title)) return [module]
      const lessons = module.lessons.filter(lesson => hit(lesson.title))
      return lessons.length ? [{ ...module, lessons }] : []
    })
    return modules.length ? [{ ...track, modules }] : []
  })
}

/** The id list with `id` swapped one step up (-1) or down (+1); null when it
 * can't move (an edge, or not in the list). */
export function moveInList(ids: string[], id: string, direction: -1 | 1): string[] | null {
  const from = ids.indexOf(id)
  const to = from + direction
  if (from < 0 || to < 0 || to >= ids.length) return null
  const next = [...ids]
  ;[next[from], next[to]] = [next[to], next[from]]
  return next
}

export function impactLabel(impact: DeleteImpact): string {
  const parts = [
    ...(impact.modules ? [plural(impact.modules, 'module')] : []),
    plural(impact.lessons, 'lesson'),
  ]
  const what = parts.length === 2 ? `${parts[0]}, ${parts[1]}` : parts[0]
  if (impact.learners_with_progress === 0) {
    return `Deletes ${what}. No learner has progress on ${impact.lessons === 1 ? 'it' : 'them'}.`
  }
  return `Deletes ${what} and the progress of ${plural(impact.learners_with_progress, 'learner')}.`
}

export function gapLabel(gap: AssignmentGap): string | null {
  if (gap.missing_pairs === 0) return null
  return `${plural(gap.lesson_ids.length, 'lesson')} not yet assigned to the ${plural(gap.learner_count, 'learner')} who have this module.`
}
```

`impactLabel` for `{modules: 3, lessons: 21, …}` gives "Deletes 3 modules, 21 lessons and the progress of 14 learners.", which matches the test. Keep the comma form exactly.

- [ ] **Step 5: Add the hooks to `admin2/api.ts`**

```ts
// ── Content structure (B4, spec 2026-10-05) ─────────────────────────────────

export type ContentAction =
  | { kind: 'updateTrack'; trackId: string; body: components['schemas']['TrackUpdateRequest'] }
  | { kind: 'deleteTrack'; trackId: string }
  | { kind: 'reorderTracks'; trackIds: string[] }
  | { kind: 'createTrack'; body: components['schemas']['TrackCreateRequest'] }
  | { kind: 'updateModule'; moduleId: string; body: components['schemas']['ModuleUpdateRequest'] }
  | { kind: 'deleteModule'; moduleId: string }
  | { kind: 'reorderModules'; trackId: string; moduleIds: string[] }
  | { kind: 'setPrerequisites'; moduleId: string; prerequisiteIds: string[] }
  | { kind: 'createModule'; body: components['schemas']['ModuleCreateRequest'] }
  | { kind: 'updateLesson'; lessonId: string; body: { title?: string; module_id?: string } }
  | { kind: 'deleteLesson'; lessonId: string }
  | { kind: 'reorderLessons'; moduleId: string; lessonIds: string[] }
  | { kind: 'createLesson'; moduleId: string; title: string }
  | { kind: 'assignGap'; moduleId: string; projectId: string | null }

async function runContentAction(action: ContentAction): Promise<void> {
  const call = (() => {
    switch (action.kind) {
      case 'updateTrack':
        return client.PATCH('/api/admin/tracks/{track_id}', { params: { path: { track_id: action.trackId } }, body: action.body })
      case 'deleteTrack':
        return client.DELETE('/api/admin/tracks/{track_id}', { params: { path: { track_id: action.trackId } } })
      case 'reorderTracks':
        return client.PUT('/api/admin/tracks/order', { body: { track_ids: action.trackIds } })
      case 'createTrack':
        return client.POST('/api/admin/tracks', { body: action.body })
      case 'updateModule':
        return client.PATCH('/api/admin/modules/{module_id}', { params: { path: { module_id: action.moduleId } }, body: action.body })
      case 'deleteModule':
        return client.DELETE('/api/admin/modules/{module_id}', { params: { path: { module_id: action.moduleId } } })
      case 'reorderModules':
        return client.PUT('/api/admin/tracks/{track_id}/modules/order', {
          params: { path: { track_id: action.trackId } },
          body: { module_ids: action.moduleIds },
        })
      case 'setPrerequisites':
        return client.PUT('/api/admin/modules/{module_id}/prerequisites', {
          params: { path: { module_id: action.moduleId } },
          body: { prerequisite_ids: action.prerequisiteIds },
        })
      case 'createModule':
        return client.POST('/api/admin/modules', { body: action.body })
      case 'updateLesson':
        return client.PATCH('/api/admin/lessons/{lesson_id}', { params: { path: { lesson_id: action.lessonId } }, body: action.body })
      case 'deleteLesson':
        return client.DELETE('/api/admin/lessons/{lesson_id}', { params: { path: { lesson_id: action.lessonId } } })
      case 'reorderLessons':
        return client.PUT('/api/admin/modules/{module_id}/lessons/order', {
          params: { path: { module_id: action.moduleId } },
          body: { lesson_ids: action.lessonIds },
        })
      case 'createLesson':
        return client.POST('/api/admin/lessons', { body: { module_id: action.moduleId, title: action.title } })
      case 'assignGap':
        return action.projectId
          ? client.POST('/api/admin/projects/{project_id}/modules/{module_id}/assign-new-lessons', {
              params: { path: { project_id: action.projectId, module_id: action.moduleId } },
            })
          : client.POST('/api/admin/modules/{module_id}/assign-new-lessons', {
              params: { path: { module_id: action.moduleId } },
            })
    }
  })()
  const { error } = await call
  if (error !== undefined) throw new Error(errorMessage(error, 'The change could not be saved.'))
}

export function useContentMutation() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: runContentAction,
    onSettled: () => {
      for (const key of [['admin', 'content'], ['admin', 'tracks'], ['admin', 'learning']]) {
        void queryClient.invalidateQueries({ queryKey: key })
      }
    },
  })
}

export function useContentTree() {
  return useQuery({
    queryKey: ['admin', 'content', 'tree'] as const,
    queryFn: async () => {
      const { data, error } = await client.GET('/api/admin/content/tree')
      if (!data) throw new Error(errorMessage(error, 'Failed to load the content.'))
      return data.tracks
    },
  })
}

export function useTrackImpact(trackId: string | null) {
  return useQuery({
    queryKey: ['admin', 'content', 'impact', 'track', trackId] as const,
    enabled: trackId !== null,
    queryFn: async () => {
      const { data, error } = await client.GET('/api/admin/tracks/{track_id}/impact', {
        params: { path: { track_id: trackId! } },
      })
      if (!data) throw new Error(errorMessage(error, 'Failed to load the impact.'))
      return data
    },
  })
}

export function useModuleImpact(moduleId: string | null) {
  return useQuery({
    queryKey: ['admin', 'content', 'impact', 'module', moduleId] as const,
    enabled: moduleId !== null,
    queryFn: async () => {
      const { data, error } = await client.GET('/api/admin/modules/{module_id}/impact', {
        params: { path: { module_id: moduleId! } },
      })
      if (!data) throw new Error(errorMessage(error, 'Failed to load the impact.'))
      return data
    },
  })
}

/** projectId null → every learner (power admins in the all-projects scope). */
export function useAssignmentGap(moduleId: string | null, projectId: string | null) {
  return useQuery({
    queryKey: ['admin', 'content', 'gap', moduleId, projectId] as const,
    enabled: moduleId !== null,
    queryFn: async () => {
      const { data, error } = projectId
        ? await client.GET('/api/admin/projects/{project_id}/modules/{module_id}/assignment-gap', {
            params: { path: { project_id: projectId, module_id: moduleId! } },
          })
        : await client.GET('/api/admin/modules/{module_id}/assignment-gap', {
            params: { path: { module_id: moduleId! } },
          })
      if (!data) throw new Error(errorMessage(error, 'Failed to load the assignment gap.'))
      return data
    },
  })
}
```

If `npm run typecheck` rejects the `client.PATCH/PUT/DELETE` calls with path-literal unions, check `schema.d.ts` for the exact path strings. A TypeScript complaint about the `call` union is fixed by awaiting inside each `case` and returning `{ error }`.

- [ ] **Step 6: Run the tests**

Run: `cd frontend && npx vitest run src/lib/contentTree.test.ts && npm run typecheck && npm run lint`
Expected: PASS and clean.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/api/schema.d.ts frontend/src/pages/admin2/api.ts frontend/src/lib/contentTree.ts frontend/src/lib/contentTree.test.ts
git commit -m "feat(admin): content-structure hooks and tree helpers (B4, #145)"
```

---

### Task 8: The Content page

**Files:**
- Create: `frontend/src/pages/admin2/ContentPage.tsx`
- Create: `frontend/src/pages/admin2/ContentDetail.tsx`
- Modify: `frontend/src/pages/admin2/nav.ts` (`NAV_ITEMS`)
- Modify: `frontend/src/App.tsx` (lazy import + `<Route path="content" …>`)
- Modify: the admin stylesheet that defines `.adm-assign-layout` (find it with `grep -rn "adm-assign-layout" frontend/src/styles`)
- Test: `frontend/src/pages/admin2/ContentPage.test.tsx`

**Interfaces:**
- Consumes: Task 7 hooks and helpers; `useAuth().isPowerAdmin`; `useScope().projectId`; kit `Card`, `ConfirmButton`, `EmptyState`, `ErrorState`, `Spinner`.
- Produces: default export `ContentPage`; `ContentDetail` with props `{ selection: Selection; tree: TreeTrack[]; canEdit: boolean; projectId: string | null; onSelect: (s: Selection | null) => void }`, where `type Selection = { kind: 'track'; id: string } | { kind: 'module'; id: string } | { kind: 'lesson'; id: string }` is exported from `ContentDetail.tsx`.

- [ ] **Step 1: Write the failing page tests**

```tsx
// frontend/src/pages/admin2/ContentPage.test.tsx
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import ContentPage from './ContentPage'

const h = vi.hoisted(() => ({ auth: { isPowerAdmin: true } }))
vi.mock('../../contexts/AuthContext', () => ({ useAuth: () => h.auth }))

const clientMock = vi.hoisted(() => ({ GET: vi.fn(), POST: vi.fn(), PUT: vi.fn(), PATCH: vi.fn(), DELETE: vi.fn() }))
vi.mock('../../api/client', async importOriginal => {
  const actual = await importOriginal<typeof import('../../api/client')>()
  return { ...actual, client: clientMock }
})

const TREE = [
  {
    id: 't1', name: 'General I', color: null, track_type: 'general', required_level: 'explore',
    is_introduction: false, sort_order: 0,
    modules: [
      { id: 'm1', title: 'Why AI now', description: null, sort_order: 0, prerequisite_ids: [], lesson_count: 0, lessons: [] },
      { id: 'm2', title: 'Prompting basics', description: null, sort_order: 1, prerequisite_ids: ['m1'], lesson_count: 1,
        lessons: [{ id: 'l1', title: 'Ask clearly', sort_order: 0 }] },
    ],
  },
  { id: 't2', name: 'Empty track', color: null, track_type: 'tool', required_level: 'integrator', is_introduction: false, sort_order: 1, modules: [] },
]

function renderPage(search = '') {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[`/admin/content${search}`]}>
        <ContentPage />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('ContentPage', () => {
  beforeEach(() => {
    h.auth = { isPowerAdmin: true }
    for (const fn of Object.values(clientMock)) fn.mockReset()
    clientMock.GET.mockImplementation((path: string) => {
      if (path === '/api/admin/content/tree') return Promise.resolve({ data: { tracks: structuredClone(TREE) } })
      if (path.endsWith('/assignment-gap')) return Promise.resolve({ data: { lesson_ids: ['l1'], learner_count: 14, missing_pairs: 14 } })
      if (path.endsWith('/impact')) return Promise.resolve({ data: { modules: 0, lessons: 1, learners_assigned: 3, learners_with_progress: 2 } })
      return Promise.resolve({ data: undefined, error: { error: { code: 'x', message: 'unexpected' } } })
    })
    for (const fn of [clientMock.POST, clientMock.PUT, clientMock.PATCH, clientMock.DELETE]) {
      fn.mockResolvedValue({ data: {}, error: undefined })
    }
  })

  it('renders an empty track', async () => {
    renderPage()
    expect(await screen.findByText('Empty track')).toBeInTheDocument()
    expect(screen.getByText('0 · 0')).toBeInTheDocument()
  })

  it('moves a module down with one reorder call', async () => {
    renderPage()
    fireEvent.click(await screen.findByText('General I'))
    fireEvent.click(screen.getByRole('button', { name: 'Move Why AI now down' }))
    await waitFor(() =>
      expect(clientMock.PUT).toHaveBeenCalledWith('/api/admin/tracks/{track_id}/modules/order', {
        params: { path: { track_id: 't1' } },
        body: { module_ids: ['m2', 'm1'] },
      }),
    )
  })

  it('renames a module from the detail panel', async () => {
    renderPage()
    fireEvent.click(await screen.findByText('General I'))
    fireEvent.click(screen.getByText('Prompting basics'))
    const title = await screen.findByLabelText('Title')
    fireEvent.change(title, { target: { value: 'Prompting 101' } })
    fireEvent.click(screen.getByRole('button', { name: 'Save' }))
    await waitFor(() =>
      expect(clientMock.PATCH).toHaveBeenCalledWith('/api/admin/modules/{module_id}', {
        params: { path: { module_id: 'm2' } },
        body: { title: 'Prompting 101', description: null },
      }),
    )
  })

  it('shows the impact before a two-step delete', async () => {
    renderPage()
    fireEvent.click(await screen.findByText('General I'))
    fireEvent.click(screen.getByText('Prompting basics'))
    expect(await screen.findByText('Deletes 1 lesson and the progress of 2 learners.')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Delete module' }))
    expect(clientMock.DELETE).not.toHaveBeenCalled()
    fireEvent.click(screen.getByRole('button', { name: 'Yes, delete' }))
    await waitFor(() =>
      expect(clientMock.DELETE).toHaveBeenCalledWith('/api/admin/modules/{module_id}', { params: { path: { module_id: 'm2' } } }),
    )
  })

  it('gives a project admin a read-only tree plus the project-scoped assign button', async () => {
    h.auth = { isPowerAdmin: false }
    renderPage('?project=p1')
    fireEvent.click(await screen.findByText('General I'))
    fireEvent.click(screen.getByText('Prompting basics'))
    const panel = await screen.findByRole('region', { name: 'Prompting basics' })
    expect(within(panel).queryByLabelText('Title')).toBeNull()
    expect(screen.queryByRole('button', { name: /^Move / })).toBeNull()
    expect(screen.queryByRole('button', { name: '+ Track' })).toBeNull()
    fireEvent.click(within(panel).getByRole('button', { name: 'Assign to the 14 learners' }))
    await waitFor(() =>
      expect(clientMock.POST).toHaveBeenCalledWith(
        '/api/admin/projects/{project_id}/modules/{module_id}/assign-new-lessons',
        { params: { path: { project_id: 'p1', module_id: 'm2' } } },
      ),
    )
  })
})
```

`useScope` reads `?project=` from the URL, which is why the project-admin test renders with `?project=p1`. Check `useScope.ts` for any other dependency (e.g. on `useAuth`) and extend the `h.auth` mock with `adminProjectIds: ['p1']` if it needs one. Per the B2 lesson, every `useAuth()` field the page reads must be in this mock.

- [ ] **Step 2: Run to verify it fails**

Run: `cd frontend && npx vitest run src/pages/admin2/ContentPage.test.tsx`
Expected: FAIL (module not found).

- [ ] **Step 3: Implement `ContentPage.tsx`**

```tsx
// frontend/src/pages/admin2/ContentPage.tsx
import { useMemo, useState } from 'react'
import { useAuth } from '../../contexts/AuthContext'
import { filterTree, moveInList, type TreeTrack } from '../../lib/contentTree'
import { useContentMutation, useContentTree } from './api'
import ContentDetail, { type Selection } from './ContentDetail'
import { Card, EmptyState, ErrorState, Spinner } from './kit'
import { useScope } from './useScope'

/** Admin → Content (spec 2026-10-05, B4): tree of tracks → modules → lessons
 * on the left, the selected item's settings on the right. Power admins edit;
 * project admins read, plus "assign new lessons" for their project. */
export default function ContentPage() {
  const { isPowerAdmin } = useAuth()
  const { projectId } = useScope()
  const tree = useContentTree()
  const mutate = useContentMutation()
  const [query, setQuery] = useState('')
  const [open, setOpen] = useState<Set<string>>(new Set())
  const [selection, setSelection] = useState<Selection | null>(null)
  const [newTrack, setNewTrack] = useState('')
  const visible = useMemo(() => filterTree(tree.data ?? [], query), [tree.data, query])

  if (tree.isLoading) return <div className="adm-loading"><Spinner /></div>
  if (tree.error || !tree.data) {
    return <ErrorState message={tree.error?.message ?? 'Failed to load the content.'} onRetry={() => void tree.refetch()} />
  }
  const tracks = tree.data
  const filtering = query.trim() !== ''
  const isOpen = (id: string) => filtering || open.has(id)
  const toggle = (id: string) =>
    setOpen(prev => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  const selected = (kind: Selection['kind'], id: string) => selection?.kind === kind && selection.id === id

  function moveTrack(track: TreeTrack, direction: -1 | 1) {
    const order = moveInList(tracks.map(t => t.id), track.id, direction)
    if (order) mutate.mutate({ kind: 'reorderTracks', trackIds: order })
  }

  return (
    <div>
      <div className="adm-page-head">
        <div>
          <h1 className="adm-page-title">Content</h1>
          <p className="adm-page-sub">
            {isPowerAdmin ? 'Tracks, modules and lessons, shared by every project.' : 'Read-only. You can assign new lessons to your project’s learners.'}
          </p>
        </div>
      </div>

      {mutate.error && <p className="adm-form-msg adm-form-msg-err" role="alert">{mutate.error.message}</p>}

      <div className="adm-content-layout">
        <Card>
          <div className="adm-content-tree-head">
            <input className="adm-field-input" placeholder="Filter by name…" aria-label="Filter by name" value={query} onChange={e => setQuery(e.target.value)} />
          </div>
          {visible.length === 0 ? (
            <EmptyState title="Nothing matches" hint="Try another name." />
          ) : (
            <ul className="adm-content-outline">
              {visible.map(track => (
                <li key={track.id}>
                  <div className={`adm-content-row${selected('track', track.id) ? ' active' : ''}`}>
                    <button type="button" className="adm-content-name" aria-expanded={isOpen(track.id)} onClick={() => { toggle(track.id); setSelection({ kind: 'track', id: track.id }) }}>
                      {isOpen(track.id) ? '▾' : '▸'} {track.name}
                    </button>
                    <span className="adm-subtext">{track.modules.length} · {track.modules.reduce((n, m) => n + m.lesson_count, 0)}</span>
                    {isPowerAdmin && !filtering && (
                      <MoveButtons label={track.name} onMove={d => moveTrack(track, d)} />
                    )}
                  </div>
                  {isOpen(track.id) && (
                    <ul>
                      {track.modules.map(module => (
                        <li key={module.id}>
                          <div className={`adm-content-row adm-content-depth-1${selected('module', module.id) ? ' active' : ''}`}>
                            <button type="button" className="adm-content-name" aria-expanded={isOpen(module.id)} onClick={() => { toggle(module.id); setSelection({ kind: 'module', id: module.id }) }}>
                              {module.title}
                            </button>
                            <span className="adm-subtext">{module.lesson_count}</span>
                            {isPowerAdmin && !filtering && (
                              <MoveButtons
                                label={module.title}
                                onMove={d => {
                                  const order = moveInList(track.modules.map(m => m.id), module.id, d)
                                  if (order) mutate.mutate({ kind: 'reorderModules', trackId: track.id, moduleIds: order })
                                }}
                              />
                            )}
                          </div>
                          {isOpen(module.id) && (
                            <ul>
                              {module.lessons.map(lesson => (
                                <li key={lesson.id}>
                                  <div className={`adm-content-row adm-content-depth-2${selected('lesson', lesson.id) ? ' active' : ''}`}>
                                    <button type="button" className="adm-content-name" onClick={() => setSelection({ kind: 'lesson', id: lesson.id })}>
                                      {lesson.title}
                                    </button>
                                    {isPowerAdmin && !filtering && (
                                      <MoveButtons
                                        label={lesson.title}
                                        onMove={d => {
                                          const order = moveInList(module.lessons.map(l => l.id), lesson.id, d)
                                          if (order) mutate.mutate({ kind: 'reorderLessons', moduleId: module.id, lessonIds: order })
                                        }}
                                      />
                                    )}
                                  </div>
                                </li>
                              ))}
                              {isPowerAdmin && (
                                <li><AddInline label="+ Lesson" onAdd={title => mutate.mutate({ kind: 'createLesson', moduleId: module.id, title })} /></li>
                              )}
                            </ul>
                          )}
                        </li>
                      ))}
                      {isPowerAdmin && (
                        <li><AddInline label="+ Module" onAdd={title => mutate.mutate({ kind: 'createModule', body: { track_id: track.id, title, prerequisite_ids: [] } })} /></li>
                      )}
                    </ul>
                  )}
                </li>
              ))}
            </ul>
          )}
          {isPowerAdmin && (
            <div className="adm-content-add-track">
              <input className="adm-field-input" placeholder="New track name" aria-label="New track name" value={newTrack} onChange={e => setNewTrack(e.target.value)} />
              <button
                type="button"
                className="adm-btn adm-btn-ghost adm-btn-sm"
                disabled={newTrack.trim() === ''}
                onClick={() => { mutate.mutate({ kind: 'createTrack', body: { name: newTrack.trim(), track_type: 'general' } }); setNewTrack('') }}
              >
                + Track
              </button>
            </div>
          )}
        </Card>

        <Card>
          {selection ? (
            <ContentDetail selection={selection} tree={tracks} canEdit={isPowerAdmin} projectId={projectId} onSelect={setSelection} />
          ) : (
            <EmptyState title="Pick something on the left" hint="A track, module or lesson." />
          )}
        </Card>
      </div>
    </div>
  )
}

function MoveButtons({ label, onMove }: { label: string; onMove: (direction: -1 | 1) => void }) {
  return (
    <span className="adm-content-move">
      <button type="button" className="adm-btn adm-btn-subtle adm-btn-sm" aria-label={`Move ${label} up`} onClick={() => onMove(-1)}>↑</button>
      <button type="button" className="adm-btn adm-btn-subtle adm-btn-sm" aria-label={`Move ${label} down`} onClick={() => onMove(1)}>↓</button>
    </span>
  )
}

function AddInline({ label, onAdd }: { label: string; onAdd: (title: string) => void }) {
  const [title, setTitle] = useState('')
  const [adding, setAdding] = useState(false)
  if (!adding) {
    return <button type="button" className="adm-btn adm-btn-subtle adm-btn-sm adm-content-depth-1" onClick={() => setAdding(true)}>{label}</button>
  }
  return (
    <form
      className="adm-content-add"
      onSubmit={e => {
        e.preventDefault()
        if (!title.trim()) return
        onAdd(title.trim())
        setTitle('')
        setAdding(false)
      }}
    >
      <input className="adm-field-input" autoFocus aria-label={`${label} title`} value={title} onChange={e => setTitle(e.target.value)} />
      <button type="submit" className="adm-btn adm-btn-ghost adm-btn-sm">Add</button>
      <button type="button" className="adm-btn adm-btn-subtle adm-btn-sm" onClick={() => setAdding(false)}>Cancel</button>
    </form>
  )
}
```

The ↑/↓ buttons are hidden while filtering, because a filtered list isn't the real sibling order. A new track starts as `general`; its type and level are changed in the detail panel.

- [ ] **Step 4: Implement `ContentDetail.tsx`**

```tsx
// frontend/src/pages/admin2/ContentDetail.tsx
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { gapLabel, impactLabel, type TreeModule, type TreeTrack } from '../../lib/contentTree'
import { useAssignmentGap, useContentMutation, useModuleImpact, useTrackImpact } from './api'
import { ConfirmButton } from './kit'

export type Selection = { kind: 'track'; id: string } | { kind: 'module'; id: string } | { kind: 'lesson'; id: string }

interface Props {
  selection: Selection
  tree: TreeTrack[]
  canEdit: boolean
  projectId: string | null
  onSelect: (selection: Selection | null) => void
}

const LEVELS = ['explore', 'practitioner', 'integrator', 'multiplier'] as const

/** The right-hand panel of Admin → Content: the selected track, module or lesson. */
export default function ContentDetail({ selection, tree, canEdit, projectId, onSelect }: Props) {
  const modules = tree.flatMap(t => t.modules.map(m => ({ ...m, trackId: t.id, trackName: t.name })))
  if (selection.kind === 'track') {
    const track = tree.find(t => t.id === selection.id)
    return track ? <TrackPanel key={track.id} track={track} canEdit={canEdit} onDeleted={() => onSelect(null)} /> : null
  }
  if (selection.kind === 'module') {
    const module = modules.find(m => m.id === selection.id)
    return module ? (
      <ModulePanel key={module.id} module={module} trackId={module.trackId} tree={tree} canEdit={canEdit} projectId={projectId} onDeleted={() => onSelect(null)} />
    ) : null
  }
  const owner = modules.find(m => m.lessons.some(l => l.id === selection.id))
  const lesson = owner?.lessons.find(l => l.id === selection.id)
  return owner && lesson ? (
    <LessonPanel key={lesson.id} lesson={lesson} moduleId={owner.id} modules={modules} canEdit={canEdit} onDeleted={() => onSelect(null)} />
  ) : null
}

function TrackPanel({ track, canEdit, onDeleted }: { track: TreeTrack; canEdit: boolean; onDeleted: () => void }) {
  const mutate = useContentMutation()
  const impact = useTrackImpact(canEdit ? track.id : null)
  const [name, setName] = useState(track.name)
  const [color, setColor] = useState(track.color ?? '')
  const [type, setType] = useState(track.track_type)
  const [level, setLevel] = useState(track.required_level)
  useEffect(() => {
    setName(track.name); setColor(track.color ?? ''); setType(track.track_type); setLevel(track.required_level)
  }, [track])

  return (
    <section aria-label={track.name} className="adm-content-detail">
      <h2 className="adm-card-title">Track: {track.name}</h2>
      {canEdit ? (
        <>
          <Field id="track-name" label="Name"><input id="track-name" className="adm-field-input" value={name} onChange={e => setName(e.target.value)} /></Field>
          <Field id="track-color" label="Colour"><input id="track-color" className="adm-field-input" value={color} placeholder="#3BC9BC" onChange={e => setColor(e.target.value)} /></Field>
          <Field id="track-type" label="Type">
            <select id="track-type" className="adm-field-input" value={type} onChange={e => setType(e.target.value)}>
              <option value="general">General</option>
              <option value="tool">Tool</option>
            </select>
          </Field>
          <Field id="track-level" label="Required level">
            <select id="track-level" className="adm-field-input" value={level} onChange={e => setLevel(e.target.value)}>
              {LEVELS.map(l => <option key={l} value={l}>{l}</option>)}
            </select>
          </Field>
          <p className="adm-hint">Changing the level changes who can open this track, in every project, straight away.</p>
          <div className="adm-content-actions">
            <button
              type="button"
              className="adm-btn adm-btn-red"
              disabled={!name.trim() || mutate.isPending}
              onClick={() => mutate.mutate({
                kind: 'updateTrack',
                trackId: track.id,
                body: { name: name.trim(), color: color.trim() || null, track_type: type as 'general' | 'tool', required_level: level as (typeof LEVELS)[number] },
              })}
            >
              Save
            </button>
          </div>
          <DangerZone label="Delete track" impact={impact.data ? impactLabel(impact.data) : null} busy={mutate.isPending}
            onConfirm={() => mutate.mutate({ kind: 'deleteTrack', trackId: track.id }, { onSuccess: onDeleted })} />
        </>
      ) : (
        <p className="adm-hint">{track.track_type} · {track.required_level} · {track.modules.length} modules</p>
      )}
    </section>
  )
}

function ModulePanel({ module, trackId, tree, canEdit, projectId, onDeleted }: {
  module: TreeModule; trackId: string; tree: TreeTrack[]; canEdit: boolean; projectId: string | null; onDeleted: () => void
}) {
  const mutate = useContentMutation()
  const impact = useModuleImpact(canEdit ? module.id : null)
  const gap = useAssignmentGap(module.id, projectId)
  const [title, setTitle] = useState(module.title)
  const [description, setDescription] = useState(module.description ?? '')
  const [prereqs, setPrereqs] = useState<Set<string>>(new Set(module.prerequisite_ids))
  useEffect(() => {
    setTitle(module.title); setDescription(module.description ?? ''); setPrereqs(new Set(module.prerequisite_ids))
  }, [module])
  const gapText = gap.data ? gapLabel(gap.data) : null

  return (
    <section aria-label={module.title} className="adm-content-detail">
      <h2 className="adm-card-title">Module: {module.title}</h2>

      {gapText && gap.data && (
        <div className="adm-note-banner">
          <p>{gapText}</p>
          <button
            type="button"
            className="adm-btn adm-btn-red adm-btn-sm"
            disabled={mutate.isPending}
            onClick={() => mutate.mutate({ kind: 'assignGap', moduleId: module.id, projectId })}
          >
            Assign to the {gap.data.learner_count} learner{gap.data.learner_count === 1 ? '' : 's'}
          </button>
        </div>
      )}

      {canEdit ? (
        <>
          <Field id="module-title" label="Title"><input id="module-title" className="adm-field-input" value={title} onChange={e => setTitle(e.target.value)} /></Field>
          <Field id="module-description" label="Description">
            <textarea id="module-description" className="adm-field-input" rows={3} value={description} onChange={e => setDescription(e.target.value)} />
          </Field>
          <Field id="module-track" label="Track">
            <select
              id="module-track"
              className="adm-field-input"
              value={trackId}
              onChange={e => mutate.mutate({ kind: 'updateModule', moduleId: module.id, body: { track_id: e.target.value } })}
            >
              {tree.map(t => <option key={t.id} value={t.id}>{t.name}</option>)}
            </select>
          </Field>
          <div className="adm-content-actions">
            <button
              type="button"
              className="adm-btn adm-btn-red"
              disabled={!title.trim() || mutate.isPending}
              onClick={() => mutate.mutate({ kind: 'updateModule', moduleId: module.id, body: { title: title.trim(), description: description.trim() || null } })}
            >
              Save
            </button>
          </div>

          <fieldset className="adm-content-prereqs">
            <legend>Unlocks after</legend>
            {tree.map(t => (
              <div key={t.id}>
                <div className="adm-subtext">{t.name}</div>
                {t.modules.filter(m => m.id !== module.id).map(m => (
                  <label key={m.id} className="adm-check-row">
                    <input
                      type="checkbox"
                      checked={prereqs.has(m.id)}
                      onChange={() => setPrereqs(prev => {
                        const next = new Set(prev)
                        if (next.has(m.id)) next.delete(m.id)
                        else next.add(m.id)
                        return next
                      })}
                    />
                    {m.title}
                  </label>
                ))}
              </div>
            ))}
            <button
              type="button"
              className="adm-btn adm-btn-ghost adm-btn-sm"
              disabled={mutate.isPending}
              onClick={() => mutate.mutate({ kind: 'setPrerequisites', moduleId: module.id, prerequisiteIds: [...prereqs] })}
            >
              Save prerequisites
            </button>
          </fieldset>

          <DangerZone label="Delete module" impact={impact.data ? impactLabel(impact.data) : null} busy={mutate.isPending}
            onConfirm={() => mutate.mutate({ kind: 'deleteModule', moduleId: module.id }, { onSuccess: onDeleted })} />
        </>
      ) : (
        <p className="adm-hint">{module.lesson_count} lessons</p>
      )}
    </section>
  )
}

function LessonPanel({ lesson, moduleId, modules, canEdit, onDeleted }: {
  lesson: { id: string; title: string }
  moduleId: string
  modules: (TreeModule & { trackName: string })[]
  canEdit: boolean
  onDeleted: () => void
}) {
  const mutate = useContentMutation()
  const [title, setTitle] = useState(lesson.title)
  useEffect(() => setTitle(lesson.title), [lesson])

  return (
    <section aria-label={lesson.title} className="adm-content-detail">
      <h2 className="adm-card-title">Lesson: {lesson.title}</h2>
      <Link className="adm-btn adm-btn-ghost adm-btn-sm" to={`/learning/lesson/${lesson.id}?edit=true`}>Edit content</Link>
      {canEdit && (
        <>
          <Field id="lesson-title" label="Title"><input id="lesson-title" className="adm-field-input" value={title} onChange={e => setTitle(e.target.value)} /></Field>
          <Field id="lesson-module" label="Module">
            <select
              id="lesson-module"
              className="adm-field-input"
              value={moduleId}
              onChange={e => mutate.mutate({ kind: 'updateLesson', lessonId: lesson.id, body: { module_id: e.target.value } })}
            >
              {modules.map(m => <option key={m.id} value={m.id}>{m.trackName} · {m.title}</option>)}
            </select>
          </Field>
          <p className="adm-hint">Moving keeps its learners. Learners of the new module get it when you press Assign there.</p>
          <div className="adm-content-actions">
            <button type="button" className="adm-btn adm-btn-red" disabled={!title.trim() || mutate.isPending}
              onClick={() => mutate.mutate({ kind: 'updateLesson', lessonId: lesson.id, body: { title: title.trim() } })}>
              Save
            </button>
          </div>
          <DangerZone label="Delete lesson" impact={null} busy={mutate.isPending}
            onConfirm={() => mutate.mutate({ kind: 'deleteLesson', lessonId: lesson.id }, { onSuccess: onDeleted })} />
        </>
      )}
    </section>
  )
}

function Field({ id, label, children }: { id: string; label: string; children: React.ReactNode }) {
  return (
    <div className="adm-field">
      <label className="adm-field-label" htmlFor={id}>{label}</label>
      {children}
    </div>
  )
}

function DangerZone({ label, impact, busy, onConfirm }: { label: string; impact: string | null; busy: boolean; onConfirm: () => void }) {
  return (
    <div className="adm-content-danger">
      {impact && <p className="adm-form-msg adm-form-msg-err">{impact}</p>}
      <ConfirmButton label={label} confirmLabel="Yes, delete" onConfirm={onConfirm} busy={busy} />
    </div>
  )
}
```

The rename test expects the PATCH body `{ title: 'Prompting 101', description: null }`, which matches the Save handler above when the description is empty. If `ConfirmButton`'s armed buttons use different accessible names than `confirmLabel` and "Cancel", adjust the test to match (read `kit/ConfirmButton.tsx`).

- [ ] **Step 5: Add the nav item, the route and the styles**

`nav.ts`, after `assignments`:

```ts
  { key: 'content',     label: 'Content',         icon: 'folder',   path: 'content' },
```

`App.tsx`: add `const ContentPage = lazy(() => import('./pages/admin2/ContentPage'))` next to the other admin2 lazies, and `<Route path="content" element={<ContentPage />} />` after the `assignments` route. It's not `powerOnly`: project admins see it read-only.

Stylesheet (next to `.adm-assign-layout`):

```css
.adm-content-layout { display: grid; grid-template-columns: minmax(320px, 2fr) 3fr; gap: 16px; align-items: start; }
.adm-content-tree-head { margin-bottom: 8px; }
.adm-content-outline, .adm-content-outline ul { list-style: none; margin: 0; padding: 0; }
.adm-content-row { display: flex; align-items: center; gap: 8px; padding: 4px 6px; border-radius: 6px; }
.adm-content-row.active { background: var(--adm-surface-2, #f3f4f6); }
.adm-content-depth-1 { padding-left: 20px; }
.adm-content-depth-2 { padding-left: 40px; }
.adm-content-name { flex: 1; text-align: left; background: none; border: 0; padding: 0; cursor: pointer; font: inherit; }
.adm-content-move { display: inline-flex; gap: 2px; }
.adm-content-add, .adm-content-add-track { display: flex; gap: 6px; padding: 6px 0 0 20px; }
.adm-content-add-track { padding-left: 0; margin-top: 12px; }
.adm-content-detail { display: flex; flex-direction: column; gap: 12px; }
.adm-content-actions { display: flex; gap: 8px; }
.adm-content-prereqs { border: 0; padding: 0; display: flex; flex-direction: column; gap: 6px; }
.adm-content-danger { border-top: 1px solid var(--adm-border, #e5e7eb); padding-top: 12px; display: flex; flex-direction: column; gap: 8px; }
```

Use the CSS variables the stylesheet already defines; grep it for `--adm-` and replace the fallback names if they differ.

- [ ] **Step 6: Run the tests**

Run: `cd frontend && npx vitest run src/pages/admin2/ContentPage.test.tsx src/pages/admin2/AdminShell.test.tsx`
Expected: PASS. `AdminShell.test.tsx` may count nav items; update its expectation for the new "Content" entry if it does.

Run: `cd frontend && npm run typecheck && npm run lint`
Expected: clean (the 2 existing `ProposalDiff.tsx` warnings only).

- [ ] **Step 7: Commit**

```bash
git add frontend/src
git commit -m "feat(admin): Content page with tree and detail panel (B4, #145)"
```

---

### Task 9: Docs, full checks, review, PR

**Files:**
- Modify: `docs/content/authoring-guide.md` §11 (the "Assignment" bullet)
- Modify: `docs/feature-index.md`
- Modify: `CLAUDE.md` (the "Lesson content" rule and the Locking section's note on editing)

- [ ] **Step 1: Update the docs**

Replace the §11 "Assignment" bullet with:

```markdown
- **Assignment**: `user_lessons` (a row = assigned); learners see only assigned lessons. A lesson
  added to (or moved into) a module is **not** assigned automatically. When it's ready, open the
  module in **Admin → Content** and press **Assign to the N learners who have this module**
  (`POST /api/admin/modules/{id}/assign-new-lessons`; project admins get the same button for their
  own project). Structure changes (rename, reorder, move, delete, prerequisites) are on the same
  page; none needs SQL.
```

`docs/feature-index.md`, after the project-export entry:

```markdown
- **Content structure editing** (#145, B4) — Admin → Content: tracks/modules/lessons edit,
  reorder, move, delete with impact warning, prerequisites (cycles refused), "assign new lessons";
  `2026-10-05-content-structure-editing-design.md`; `routers/admin_structure.py`,
  `frontend/src/pages/admin2/ContentPage.tsx`.
```

`CLAUDE.md` → "Rules that span the whole repo" rule 5: add "Structure (tracks, modules, order, prerequisites, assigning new lessons) is edited in Admin → Content." In "Locking": the module-prerequisite bullet gains "Admin → Content refuses prerequisite cycles (server-side, `core/prerequisites.py`)."

- [ ] **Step 2: Full checks (checkpoint)**

Run: `cd backend && uv run poe format-check && uv run poe lint-src && uv run poe ty-src && uv run poe test`
Expected: green, coverage ≥ 90%, docs-drift passes (every path named above exists).

Run: `cd frontend && npm run typecheck && npm run lint && npm test && npm run build`
Expected: green.

- [ ] **Step 3: Commit the docs**

```bash
git add docs CLAUDE.md
git commit -m "docs: Admin → Content replaces the SQL structure steps (B4, #145)"
```

- [ ] **Step 4: One strong-model review of the whole branch**

Dispatch one reviewer (most capable model) over `git diff origin/main...HEAD`. Give it the spec and this plan. Its focus:
- the migration's safety on live data;
- authz on every new route, especially project isolation in the gap routes;
- atomicity of moves and deletes;
- the cascade warning's accuracy;
- the Review Focus list above.

Fix real findings and note the nits in the PR.

- [ ] **Step 5: Open the PR**

```bash
git push -u origin feat/content-structure
gh pr create --base main --title "feat(admin): content structure editing — B4" --body "Closes #145 …"
```

The PR body should cover:
- what's on the page and who can do what;
- the migration (renumbers live `sort_order` on tracks and modules without changing visible order; deferred uniqueness);
- tests run, plus what ran only in CI;
- the deploy note: the migration ships with the next Deploy and is expand-first.

End the body with the `🤖 Generated with [Claude Code](https://claude.com/claude-code)` line.
