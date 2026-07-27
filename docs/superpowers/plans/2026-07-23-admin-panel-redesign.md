# Admin Panel Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the MVP admin panel with the approved function-first redesign: routed admin shell (Dashboard · People · Assignments · Feedback · Projects · Email templates · Setup), project-level default assignments materialized on invite, a multi-user bulk assignment endpoint, a feedback triage queue, dashboard aggregates, and the N+1/pagination hygiene — shipped as one cutover release.

**Architecture:** Backend lands first as independently shippable slices behind the existing `/api/admin/*` surface (old panel keeps working untouched until cutover — every contract change is additive). Frontend is "middle + reskin": a new routed shell under `/admin/*` with TanStack Query and a small admin-scoped component kit, reusing `SurveyResults`, `BulkInviteModal`, `EmailTemplatesCard` internals and the Setup forms. The cutover commit deletes `Admin.tsx`, `ProjectsView`, `ProjectDetailView`, `ParticipantDetail` (the inline detail that replaced `UserPanel` on main, 2026-07-24).

**Tech Stack:** FastAPI (Python 3.13, uv, SQLAlchemy 2.0 async, Alembic, Pydantic v2, pytest), React 18 + TypeScript (Vite, react-router-dom v6, openapi-fetch, @tanstack/react-query — new dep), Azure PostgreSQL.

**Spec (single source of truth):** `docs/superpowers/specs/2026-07-23-admin-panel-redesign-design.md`
**Visual contract:** `docs/design-prototypes/admin-redesign/option-b.html` (+ `styles.css` tokens)
**Builds on (MUST be merged first):** branch `worktree-cascading-track-module-assignment` — cascading assignment (spec `2026-07-23-cascading-track-module-assignment-design.md`)

## Global Constraints

- Backend layering is mandatory (`python-be-architecture.md`): router → service → repository → model; DI providers in `core/dependencies/domain.py` with **runtime** (not TYPE_CHECKING) param annotations; services never call services; repositories are the only layer touching the session.
- **Iron rule:** no endpoint outside `/admin/*` accepts a user identifier from the request. All new endpoints here live under `/api/admin/*` and are admin-gated.
- **Every new `/admin` endpoint gets an authz-matrix entry** in `backend/tests/integration/test_routers/test_authz.py::_MATRIX` (anonymous→401, user→403, admin→2xx/4xx-not-authz).
- All contract changes to existing endpoints are **additive** (new optional params, new response fields) — the old admin panel must keep compiling and working until the cutover commit.
- Locked definitions (spec §4.4): *stalled* = last lesson completion > 14 days ago with unfinished assigned lessons; *active this week* = last activity ≤ 7 days; *completed a track* = all assigned lessons of that track completed; *activated* = `password_set` OR `external_id`; *assessed* = `surveys.status='complete'`.
- Provenance values: `assigned_via IN ('manual','default')`, default `'manual'`. Provenance records how a row was **first** created (`ON CONFLICT DO NOTHING` everywhere — the defaults *apply* action is additive-only and never overwrites or removes).
- Feedback stays message-only; **no `type` column, no `ai_*` columns** (AI triage is parked, spec §8).
- Backend gate after each task: `cd backend && uv run poe format && uv run poe lint && uv run poe test` — all green, coverage ≥80%.
- Frontend gate: `cd frontend && npm run typecheck && npm run lint && npm run build` — all green.
- `asyncio_mode = "auto"` — async tests need no marker. Integration tests run against the `ai-enablement-hub-test` Azure PG DB (normal dev loop, no approval needed).
- **Approval gates (never unattended):** applying migrations to the dev Azure DB (`poe upgrade`), running the dev backend for `npm run gen:api` (startup fires a real cleanup DELETE), any `git push`, and `deploy.ps1`.
- Every git commit message ends with the trailer:
  `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`

## Before you start — Task 0: preconditions

- [ ] **Verify the cascading-assignment branch has merged into `main`.** This plan's Phase A modifies `admin_user_service.py` as it exists on that branch (cascade helpers `_cascade_to_modules_and_lessons` / `_cascade_to_lessons`). Do not start otherwise.

```powershell
git fetch origin
git merge-base --is-ancestor origin/worktree-cascading-track-module-assignment origin/main; if ($?) { "OK - merged" } else { "STOP - not merged" }
```

Expected: `OK - merged`. If `STOP`: halt and ask Aaron.

- [ ] **Create the feature branch** (never work on `main`; never push without Aaron's explicit approval):

```powershell
git checkout main; git pull --ff-only origin main
git checkout -b feature/admin-panel-redesign
```

- [ ] **Parallel-work awareness (checked 2026-07-24):** Matthias works on his own branches and merges to `main` (cascading-assignment and participant-inline-detail both landed this way); his next project is **ai-chat-foundation** (spec + plan on `main`, implementation pending). Two coordination rules for this plan's execution:
  1. **Alembic single-chain policy.** The chat plan adds a migration chaining off the same head this plan's migrations chain off. Before committing ANY migration here, pull `main` and run `cd backend && uv run alembic heads` — exactly one head must exist. If a chat-foundation migration has landed, re-parent this plan's migration (`down_revision` → the new head). Whoever merges second re-parents; never leave two heads.
  2. **Old-panel collision.** The chat plan's final frontend tasks modify `Admin.tsx`/`ProjectDetailView.tsx` (project AI settings), which this plan deletes at cutover (Task 20 has the check). Rebase `main` into the feature branch regularly (`git fetch origin && git rebase origin/main` while unpushed) so conflicts surface small; the merge-conflict hotspots are all additive (`main.py` router registrations, `test_authz.py::_MATRIX`, `repositories/base.py`, `db/models/__init__.py`, `core/dependencies/domain.py`).

---

## Phase A — Backend (defaults → bulk → feedback → reminder → hygiene → dashboard). No Azure DB mutation without approval.

### Task 1: Models + migration — `project_track_defaults` and `assigned_via` provenance

**Files:**
- Create: `backend/src/db/models/defaults.py`
- Modify: `backend/src/db/models/assignment.py` (3 columns + 3 CHECKs)
- Modify: `backend/src/db/models/__init__.py` (export `ProjectTrackDefault`)
- Create: `backend/alembic/versions/b5c6d7e8f9a0_project_defaults_and_provenance.py`
- Test: `backend/tests/integration/test_repositories/test_defaults_schema.py`

**Interfaces:**
- Produces: model `ProjectTrackDefault(project_id, track_id, created_at)` (composite PK, both FKs CASCADE); `UserTrack.assigned_via` / `UserModule.assigned_via` / `UserLesson.assigned_via` (`Mapped[str]`, NOT NULL, server_default `'manual'`, CHECK `IN ('manual','default')`).
- Alembic: new head `b5c6d7e8f9a0`, `down_revision = "e2f3a4b5c6d7"`.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/integration/test_repositories/test_defaults_schema.py
from __future__ import annotations

import uuid

from sqlalchemy import select

from src.db.models import ProjectTrackDefault, UserTrack
from tests.fixtures.factories import create_company, create_project, create_track, create_user


async def test_project_track_default_roundtrip(db_session) -> None:
    company = await create_company(db_session)
    project = await create_project(db_session, company_id=company.id)
    track = await create_track(db_session)
    db_session.add(ProjectTrackDefault(project_id=project.id, track_id=track.id))
    await db_session.commit()
    row = (await db_session.execute(select(ProjectTrackDefault))).scalar_one()
    assert (row.project_id, row.track_id) == (project.id, track.id)


async def test_assigned_via_defaults_to_manual(db_session) -> None:
    user = await create_user(db_session, email=f"{uuid.uuid4()}@x.test")
    track = await create_track(db_session)
    db_session.add(UserTrack(user_id=user.id, track_id=track.id))
    await db_session.commit()
    row = (await db_session.execute(select(UserTrack))).scalar_one()
    assert row.assigned_via == "manual"
```

(Match `create_*` factory signatures in `tests/fixtures/factories.py` exactly — e.g. if `create_user` requires `first_name`/`last_name`, pass them.)

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/integration/test_repositories/test_defaults_schema.py -v`
Expected: FAIL — `ImportError: cannot import name 'ProjectTrackDefault'`

- [ ] **Step 3: Write the model + column changes**

```python
# backend/src/db/models/defaults.py
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base

__all__ = ["ProjectTrackDefault"]


class ProjectTrackDefault(Base):
    """A track every new participant of the project receives at invite time.

    Track-level only by design (spec §4.1): a default track implies all of its
    modules and lessons via the cascade; per-user tweaks handle exceptions.
    """

    __tablename__ = "project_track_defaults"

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        primary_key=True,
    )
    track_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tracks.id", ondelete="CASCADE"),
        primary_key=True,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
```

In `backend/src/db/models/assignment.py`: add `CheckConstraint` and `Text` to the imports, then to **each** of `UserTrack`, `UserModule`, `UserLesson` add the column and extend `__table_args__`, e.g. for `UserTrack`:

```python
    __table_args__ = (
        UniqueConstraint("user_id", "track_id"),
        CheckConstraint("assigned_via IN ('manual','default')", name="assigned_via"),
    )
    ...
    assigned_via: Mapped[str] = mapped_column(
        Text, nullable=False, server_default=text("'manual'")
    )
```

(Repeat identically for `UserModule` and `UserLesson`; keep their existing `UniqueConstraint` first. `LessonProgress` is untouched.) Add `ProjectTrackDefault` to `backend/src/db/models/__init__.py` mirroring how the other models are imported/exported there.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && uv run pytest tests/integration/test_repositories/test_defaults_schema.py -v`
Expected: PASS (integration schema is created from `Base.metadata`, so model changes are live without the migration)

- [ ] **Step 5: Write the migration by hand** (hand-authored like every migration in this repo — do NOT autogenerate)

```python
# backend/alembic/versions/b5c6d7e8f9a0_project_defaults_and_provenance.py
"""project defaults and assignment provenance

Revision ID: b5c6d7e8f9a0
Revises: e2f3a4b5c6d7
Create Date: 2026-07-23
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "b5c6d7e8f9a0"
down_revision: str | None = "e2f3a4b5c6d7"
branch_labels = None
depends_on = None

_ASSIGNMENT_TABLES = ("user_tracks", "user_modules", "user_lessons")


def upgrade() -> None:
    op.create_table(
        "project_track_defaults",
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("track_id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            name=op.f("fk_project_track_defaults_project_id_projects"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["track_id"],
            ["tracks.id"],
            name=op.f("fk_project_track_defaults_track_id_tracks"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("project_id", "track_id", name=op.f("pk_project_track_defaults")),
    )
    op.create_index(
        op.f("ix_project_track_defaults_track_id"),
        "project_track_defaults",
        ["track_id"],
        unique=False,
    )
    for table in _ASSIGNMENT_TABLES:
        op.add_column(
            table,
            sa.Column(
                "assigned_via", sa.Text(), server_default=sa.text("'manual'"), nullable=False
            ),
        )
        op.create_check_constraint(
            op.f(f"ck_{table}_assigned_via"), table, "assigned_via IN ('manual','default')"
        )


def downgrade() -> None:
    for table in _ASSIGNMENT_TABLES:
        op.drop_constraint(op.f(f"ck_{table}_assigned_via"), table, type_="check")
        op.drop_column(table, "assigned_via")
    op.drop_index(op.f("ix_project_track_defaults_track_id"), table_name="project_track_defaults")
    op.drop_table("project_track_defaults")
```

Compare constraint-name style against the previous migration (`e2f3a4b5c6d7_user_plus_role.py`) before committing — if that file passes bare names to `create_check_constraint` (letting the naming convention prefix them), do the same here. **Also verify the chain base:** `cd backend && uv run alembic heads` must show exactly `e2f3a4b5c6d7` — if another migration (e.g. ai-chat-foundation's) has landed on `main` since, re-parent this file's `down_revision` to the actual head (see Task 0's single-chain policy).

**Do NOT run `poe upgrade` against the dev Azure DB in this task** — migrations are applied once, with Aaron's approval, at the Phase A checkpoint.

- [ ] **Step 6: Run the full backend gate**

Run: `cd backend && uv run poe format && uv run poe lint && uv run poe test`
Expected: all green

- [ ] **Step 7: Commit**

```bash
git add backend/src/db/models/ backend/alembic/versions/b5c6d7e8f9a0_project_defaults_and_provenance.py backend/tests/integration/test_repositories/test_defaults_schema.py
git commit -m "feat(admin): project_track_defaults table + assigned_via provenance columns"
```

### Task 2: Thread `assigned_via` through the assignment repository

**Files:**
- Modify: `backend/src/repositories/base.py` (6 abstract `set_user_*` signatures)
- Modify: `backend/src/repositories/assignment_repository.py`
- Test: `backend/tests/integration/test_repositories/test_assignment_provenance.py`

**Interfaces:**
- Consumes: `UserTrack/UserModule/UserLesson.assigned_via` (Task 1).
- Produces: every `set_user_*` method gains keyword-only `assigned_via: str = "manual"`:
  `set_user_track(user_id, track_id, assigned, *, assigned_via="manual")`, `set_user_module(...)`, `set_user_lesson(...)`, `set_user_tracks(user_id, track_ids, assigned, *, assigned_via="manual")`, `set_user_modules(...)`, `set_user_lessons(...)`. Semantics: inserts carry the value; `ON CONFLICT DO NOTHING` is kept, so an existing row's provenance is never rewritten (spec: apply is additive-only). Unassign (`assigned=False`) ignores `assigned_via` and deletes regardless of provenance.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/integration/test_repositories/test_assignment_provenance.py
from __future__ import annotations

import uuid

from sqlalchemy import select

from src.db.models import UserTrack
from src.repositories.assignment_repository import AssignmentRepository
from tests.fixtures.factories import create_track, create_user


async def _provenance(db_session, user_id) -> str:
    row = (
        await db_session.execute(select(UserTrack).where(UserTrack.user_id == user_id))
    ).scalar_one()
    return row.assigned_via


async def test_bulk_insert_carries_assigned_via(db_session) -> None:
    repo = AssignmentRepository(db_session)
    user = await create_user(db_session, email=f"{uuid.uuid4()}@x.test")
    track = await create_track(db_session)
    await repo.set_user_tracks(user.id, [track.id], True, assigned_via="default")
    assert await _provenance(db_session, user.id) == "default"


async def test_conflict_keeps_first_writer_provenance(db_session) -> None:
    repo = AssignmentRepository(db_session)
    user = await create_user(db_session, email=f"{uuid.uuid4()}@x.test")
    track = await create_track(db_session)
    await repo.set_user_track(user.id, track.id, True)  # manual first
    await repo.set_user_tracks(user.id, [track.id], True, assigned_via="default")  # apply later
    assert await _provenance(db_session, user.id) == "manual"


async def test_unassign_deletes_regardless_of_provenance(db_session) -> None:
    repo = AssignmentRepository(db_session)
    user = await create_user(db_session, email=f"{uuid.uuid4()}@x.test")
    track = await create_track(db_session)
    await repo.set_user_track(user.id, track.id, True, assigned_via="default")
    await repo.set_user_track(user.id, track.id, False)
    assert await repo.track_ids_for_user(user.id) == set()
```

(Write the same three cases for modules and lessons in the same file — identical shape with `create_module`/`create_lesson` factories and `set_user_module(s)`/`set_user_lesson(s)`.)

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/integration/test_repositories/test_assignment_provenance.py -v`
Expected: FAIL — `TypeError: ... got an unexpected keyword argument 'assigned_via'`

- [ ] **Step 3: Implement**

In `repositories/base.py`, change the six abstract signatures (keyword-only param), e.g.:

```python
    @abstractmethod
    async def set_user_track(
        self, user_id: uuid.UUID, track_id: uuid.UUID, assigned: bool, *, assigned_via: str = "manual"
    ) -> None: ...
```

In `assignment_repository.py`, add `"assigned_via": assigned_via` to every insert's values dict — single-item and bulk, e.g. the bulk-track insert becomes:

```python
            stmt = (
                pg_insert(UserTrack)
                .values(
                    [
                        {"user_id": user_id, "track_id": tid, "assigned_via": assigned_via}
                        for tid in track_ids
                    ]
                )
                .on_conflict_do_nothing(index_elements=["user_id", "track_id"])
            )
```

The delete branches are untouched. Mirror for modules/lessons and the three single-item methods.

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && uv run pytest tests/integration/test_repositories/test_assignment_provenance.py -v`
Expected: PASS. Then the full gate: `uv run poe format && uv run poe lint && uv run poe test` (the cascading-assignment suite from the merged branch must stay green — the default value keeps all existing callers `'manual'`).

- [ ] **Step 5: Commit**

```bash
git add backend/src/repositories/ backend/tests/integration/test_repositories/test_assignment_provenance.py
git commit -m "feat(admin): assigned_via provenance threaded through assignment writes"
```

### Task 3: Defaults storage + `GET/PUT /api/admin/projects/{id}/defaults`

**Files:**
- Modify: `backend/src/repositories/base.py` (`AbstractOrgRepository` + 2 methods)
- Modify: `backend/src/repositories/org_repository.py`
- Modify: `backend/src/services/admin_user_service.py` (2 methods)
- Create: `backend/src/schemas/admin_defaults.py`
- Create: `backend/src/routers/admin_defaults.py`
- Modify: `backend/src/main.py` (register router)
- Modify: `backend/tests/integration/test_routers/test_authz.py` (2 matrix entries)
- Test: `backend/tests/integration/test_routers/test_admin_defaults.py`

**Interfaces:**
- Consumes: `ProjectTrackDefault` model (Task 1); `AbstractContentRepository.count_tracks_by_ids`; `AbstractOrgRepository.get_project`.
- Produces:
  - `AbstractOrgRepository.default_track_ids(project_id: uuid.UUID) -> list[uuid.UUID]`
  - `AbstractOrgRepository.set_default_tracks(project_id: uuid.UUID, track_ids: list[uuid.UUID]) -> None` (full replace)
  - `AdminUserService.get_project_defaults(project_id) -> list[uuid.UUID]` (404 unknown project)
  - `AdminUserService.set_project_defaults(project_id, track_ids) -> None` (404 unknown project/track; deduplicates; **empty list allowed** = clear defaults — deliberately different from the bulk-assign 422 convention because PUT is a full replace)
  - Endpoints `GET /api/admin/projects/{project_id}/defaults` → `DefaultsResponse{track_ids}` and `PUT` (204) with `DefaultsUpdateRequest{track_ids}`.

- [ ] **Step 1: Write the failing router test**

```python
# backend/tests/integration/test_routers/test_admin_defaults.py
from __future__ import annotations

import uuid

from tests.fixtures.auth import auth_headers
from tests.fixtures.factories import create_company, create_project, create_track, create_user


class TestDefaultsEndpoints:
    async def test_get_empty_defaults(self, client, db_session, test_settings) -> None:
        admin = await create_user(db_session, email="a1@x.test", role="admin")
        company = await create_company(db_session)
        project = await create_project(db_session, company_id=company.id)
        resp = await client.get(
            f"/api/admin/projects/{project.id}/defaults",
            headers=auth_headers(admin, test_settings),
        )
        assert resp.status_code == 200
        assert resp.json() == {"track_ids": []}

    async def test_put_then_get_roundtrip(self, client, db_session, test_settings) -> None:
        admin = await create_user(db_session, email="a2@x.test", role="admin")
        company = await create_company(db_session)
        project = await create_project(db_session, company_id=company.id)
        track = await create_track(db_session)
        headers = auth_headers(admin, test_settings)
        put = await client.put(
            f"/api/admin/projects/{project.id}/defaults",
            json={"track_ids": [str(track.id)]},
            headers=headers,
        )
        assert put.status_code == 204
        got = await client.get(f"/api/admin/projects/{project.id}/defaults", headers=headers)
        assert got.json() == {"track_ids": [str(track.id)]}

    async def test_put_empty_clears(self, client, db_session, test_settings) -> None:
        admin = await create_user(db_session, email="a3@x.test", role="admin")
        company = await create_company(db_session)
        project = await create_project(db_session, company_id=company.id)
        track = await create_track(db_session)
        headers = auth_headers(admin, test_settings)
        await client.put(
            f"/api/admin/projects/{project.id}/defaults",
            json={"track_ids": [str(track.id)]},
            headers=headers,
        )
        cleared = await client.put(
            f"/api/admin/projects/{project.id}/defaults", json={"track_ids": []}, headers=headers
        )
        assert cleared.status_code == 204
        got = await client.get(f"/api/admin/projects/{project.id}/defaults", headers=headers)
        assert got.json() == {"track_ids": []}

    async def test_unknown_project_404(self, client, db_session, test_settings) -> None:
        admin = await create_user(db_session, email="a4@x.test", role="admin")
        resp = await client.get(
            f"/api/admin/projects/{uuid.uuid4()}/defaults",
            headers=auth_headers(admin, test_settings),
        )
        assert resp.status_code == 404

    async def test_unknown_track_404_writes_nothing(self, client, db_session, test_settings) -> None:
        admin = await create_user(db_session, email="a5@x.test", role="admin")
        company = await create_company(db_session)
        project = await create_project(db_session, company_id=company.id)
        headers = auth_headers(admin, test_settings)
        resp = await client.put(
            f"/api/admin/projects/{project.id}/defaults",
            json={"track_ids": [str(uuid.uuid4())]},
            headers=headers,
        )
        assert resp.status_code == 404
        got = await client.get(f"/api/admin/projects/{project.id}/defaults", headers=headers)
        assert got.json() == {"track_ids": []}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/integration/test_routers/test_admin_defaults.py -v`
Expected: FAIL — 404 `Not Found` on every request (route doesn't exist)

- [ ] **Step 3: Implement repository → service → schema → router**

`repositories/base.py`, inside `AbstractOrgRepository`:

```python
    @abstractmethod
    async def default_track_ids(self, project_id: uuid.UUID) -> list[uuid.UUID]: ...

    @abstractmethod
    async def set_default_tracks(
        self, project_id: uuid.UUID, track_ids: list[uuid.UUID]
    ) -> None: ...
```

`repositories/org_repository.py` (add `delete`, `select` and `ProjectTrackDefault` imports):

```python
    async def default_track_ids(self, project_id: uuid.UUID) -> list[uuid.UUID]:
        result = await self._session.execute(
            select(ProjectTrackDefault.track_id).where(
                ProjectTrackDefault.project_id == project_id
            )
        )
        return list(result.scalars().all())

    async def set_default_tracks(
        self, project_id: uuid.UUID, track_ids: list[uuid.UUID]
    ) -> None:
        await self._session.execute(
            delete(ProjectTrackDefault).where(ProjectTrackDefault.project_id == project_id)
        )
        self._session.add_all(
            ProjectTrackDefault(project_id=project_id, track_id=track_id)
            for track_id in track_ids
        )
        await self._session.commit()
```

`services/admin_user_service.py`:

```python
    async def get_project_defaults(self, project_id: uuid.UUID) -> list[uuid.UUID]:
        if await self._org.get_project(project_id) is None:
            raise NotFoundError("Project")
        return await self._org.default_track_ids(project_id)

    async def set_project_defaults(
        self, project_id: uuid.UUID, track_ids: list[uuid.UUID]
    ) -> None:
        if await self._org.get_project(project_id) is None:
            raise NotFoundError("Project")
        unique_ids = list(set(track_ids))
        if await self._content.count_tracks_by_ids(unique_ids) != len(unique_ids):
            raise NotFoundError("Track")
        await self._org.set_default_tracks(project_id, unique_ids)
```

`schemas/admin_defaults.py`:

```python
from __future__ import annotations

import uuid

from pydantic import BaseModel

__all__ = ["ApplyDefaultsResponse", "DefaultsResponse", "DefaultsUpdateRequest"]


class DefaultsResponse(BaseModel):
    track_ids: list[uuid.UUID]


class DefaultsUpdateRequest(BaseModel):
    """Full replace; an empty list clears the project's defaults."""

    track_ids: list[uuid.UUID]


class ApplyDefaultsResponse(BaseModel):
    users_updated: int
```

`routers/admin_defaults.py` (mirror `admin_users.py`'s `AdminUserServiceDep` alias style — copy the exact `Annotated[...]` alias it uses):

```python
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, status

from src.core.dependencies.auth import require_admin
from src.core.dependencies.domain import get_admin_user_service  # same provider admin_users.py uses
from src.schemas.admin_defaults import DefaultsResponse, DefaultsUpdateRequest

__all__ = ["router"]

router = APIRouter(
    prefix="/api/admin", tags=["admin:defaults"], dependencies=[Depends(require_admin)]
)


@router.get("/projects/{project_id}/defaults", response_model=DefaultsResponse)
async def get_defaults(
    project_id: uuid.UUID, admin_user_service: AdminUserServiceDep
) -> DefaultsResponse:
    return DefaultsResponse(track_ids=await admin_user_service.get_project_defaults(project_id))


@router.put("/projects/{project_id}/defaults", status_code=status.HTTP_204_NO_CONTENT)
async def put_defaults(
    project_id: uuid.UUID, body: DefaultsUpdateRequest, admin_user_service: AdminUserServiceDep
) -> None:
    await admin_user_service.set_project_defaults(project_id, body.track_ids)
```

(Use the real `AdminUserServiceDep` type alias — check how `routers/admin_users.py` declares it and import/replicate exactly.) Register in `main.py` next to the other routers: `app.include_router(admin_defaults.router)`.

Add two authz-matrix entries in `test_authz.py::_MATRIX` (the `s` fixture already carries a project — check its attribute name, e.g. `s.project`):

```python
("defaults-get", "GET", lambda s: f"/api/admin/projects/{s.project.id}/defaults", lambda s: None, True),
("defaults-put", "PUT", lambda s: f"/api/admin/projects/{s.project.id}/defaults",
    lambda s: {"track_ids": [str(s.track.id)]}, True),
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && uv run pytest tests/integration/test_routers/test_admin_defaults.py tests/integration/test_routers/test_authz.py -v`
Expected: PASS. Then the full gate.

- [ ] **Step 5: Commit**

```bash
git add backend/src/ backend/tests/
git commit -m "feat(admin): project defaults endpoints (GET/PUT)"
```

### Task 4: Materialize defaults on invite + `POST .../defaults/apply`

**Files:**
- Modify: `backend/src/services/admin_user_service.py` (cascade helpers gain `assigned_via`; `invite`/`create_invited_users` materialize; new `_materialize_defaults` + `apply_project_defaults`)
- Modify: `backend/src/repositories/base.py` + `backend/src/repositories/user_repository.py` (`ids_for_project`)
- Modify: `backend/src/routers/admin_defaults.py` (apply route)
- Modify: `backend/tests/integration/test_routers/test_authz.py` (1 entry)
- Test: `backend/tests/integration/test_routers/test_admin_defaults.py` (extend), `backend/tests/integration/test_routers/test_admin_users.py` (invite materialization), `backend/tests/integration/test_routers/test_admin_bulk_invite.py` (CSV materialization)

**Interfaces:**
- Consumes: Task 2's `assigned_via` kwargs; Task 3's `default_track_ids`; the merged branch's `_cascade_to_modules_and_lessons(user_id, track_ids, assigned)` / `_cascade_to_lessons(user_id, module_ids, assigned)`.
- Produces:
  - `AbstractUserRepository.ids_for_project(project_id: uuid.UUID) -> list[uuid.UUID]`
  - Cascade helpers gain keyword-only `assigned_via: str = "manual"` (existing callers unchanged).
  - `AdminUserService._materialize_defaults(user_id, project_id) -> None` — reads defaults, then `set_user_tracks(..., assigned_via="default")` + cascade with `assigned_via="default"`.
  - `AdminUserService.apply_project_defaults(project_id) -> int` — additive backfill over every user of the project, returns user count touched; 404 unknown project.
  - `POST /api/admin/projects/{project_id}/defaults/apply` → `ApplyDefaultsResponse{users_updated}`.
  - `invite()` and `create_invited_users()` call `_materialize_defaults` after each user row is created — this covers **all four invite paths** (single × email/link — `send_email` only affects mail, and bulk CSV) with zero extra work.

- [ ] **Step 1: Write the failing tests**

Add to `test_admin_defaults.py`:

```python
class TestMaterializeOnInvite:
    async def _project_with_default(self, db_session):
        company = await create_company(db_session)
        project = await create_project(db_session, company_id=company.id)
        track = await create_track(db_session)
        module = await create_module(db_session, track_id=track.id)
        lesson = await create_lesson(db_session, module_id=module.id)
        db_session.add(ProjectTrackDefault(project_id=project.id, track_id=track.id))
        await db_session.commit()
        return project, track, module, lesson

    async def test_invite_materializes_defaults_with_provenance(
        self, client, db_session, test_settings
    ) -> None:
        admin = await create_user(db_session, email="m1@x.test", role="admin")
        project, track, module, lesson = await self._project_with_default(db_session)
        resp = await client.post(
            "/api/admin/invites",
            json={
                "email": "newbie@x.test",
                "first_name": "New",
                "last_name": "Bie",
                "project_id": str(project.id),
                "send_email": False,
            },
            headers=auth_headers(admin, test_settings),
        )
        assert resp.status_code == 201
        rows = (await db_session.execute(select(UserTrack))).scalars().all()
        assert [(r.track_id, r.assigned_via) for r in rows if r.track_id == track.id] == [
            (track.id, "default")
        ]
        module_rows = (await db_session.execute(select(UserModule))).scalars().all()
        lesson_rows = (await db_session.execute(select(UserLesson))).scalars().all()
        assert {r.assigned_via for r in module_rows} == {"default"}
        assert {r.lesson_id for r in lesson_rows} == {lesson.id}

    async def test_invite_without_defaults_assigns_nothing(
        self, client, db_session, test_settings
    ) -> None:
        admin = await create_user(db_session, email="m2@x.test", role="admin")
        company = await create_company(db_session)
        project = await create_project(db_session, company_id=company.id)
        resp = await client.post(
            "/api/admin/invites",
            json={
                "email": "plain@x.test",
                "first_name": "Pl",
                "last_name": "Ain",
                "project_id": str(project.id),
                "send_email": False,
            },
            headers=auth_headers(admin, test_settings),
        )
        assert resp.status_code == 201
        assert (await db_session.execute(select(UserTrack))).scalars().all() == []


class TestApplyDefaults:
    async def test_apply_is_additive_and_keeps_manual_provenance(
        self, client, db_session, test_settings
    ) -> None:
        admin = await create_user(db_session, email="ap1@x.test", role="admin")
        company = await create_company(db_session)
        project = await create_project(db_session, company_id=company.id)
        track = await create_track(db_session)
        extra_track = await create_track(db_session)
        existing = await create_user(
            db_session, email="old@x.test", project_id=project.id, company_id=company.id
        )
        await assign_track(db_session, existing.id, extra_track.id)  # manual, pre-existing
        db_session.add(ProjectTrackDefault(project_id=project.id, track_id=track.id))
        await db_session.commit()
        resp = await client.post(
            f"/api/admin/projects/{project.id}/defaults/apply",
            headers=auth_headers(admin, test_settings),
        )
        assert resp.status_code == 200
        assert resp.json() == {"users_updated": 1}
        rows = (await db_session.execute(select(UserTrack))).scalars().all()
        by_track = {r.track_id: r.assigned_via for r in rows}
        assert by_track[track.id] == "default"      # backfilled
        assert by_track[extra_track.id] == "manual"  # untouched, never removed/rewritten
```

(Imports at top of file: `select` from sqlalchemy, `ProjectTrackDefault`, `UserTrack`, `UserModule`, `UserLesson` from `src.db.models`, plus `create_module`, `create_lesson`, `assign_track` factories.) Also add one bulk-CSV case to `test_admin_bulk_invite.py`: commit a valid 1-row CSV into a project with a default track, assert the created user has `UserTrack/UserModule/UserLesson` rows all `assigned_via == "default"` — copy the CSV-upload mechanics from the existing tests in that file.

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && uv run pytest tests/integration/test_routers/test_admin_defaults.py -v`
Expected: `TestMaterializeOnInvite` FAILs on the row asserts (no materialization yet); `TestApplyDefaults` FAILs with 404/405 (route missing)

- [ ] **Step 3: Implement**

`repositories/base.py` (`AbstractUserRepository`) + `user_repository.py`:

```python
    @abstractmethod
    async def ids_for_project(self, project_id: uuid.UUID) -> list[uuid.UUID]: ...
```

```python
    async def ids_for_project(self, project_id: uuid.UUID) -> list[uuid.UUID]:
        result = await self._session.execute(
            select(User.id).where(User.project_id == project_id)
        )
        return list(result.scalars().all())
```

`services/admin_user_service.py` — thread `assigned_via` through the two cascade helpers (signature only; bodies pass it to the repo calls):

```python
    async def _cascade_to_modules_and_lessons(
        self, user_id: uuid.UUID, track_ids: list[uuid.UUID], assigned: bool,
        *, assigned_via: str = "manual",
    ) -> None:
        module_ids, lesson_ids = await self._cascade_module_and_lesson_ids(track_ids)
        if module_ids:
            await self._assignments.set_user_modules(
                user_id, module_ids, assigned, assigned_via=assigned_via
            )
        if lesson_ids:
            await self._assignments.set_user_lessons(
                user_id, lesson_ids, assigned, assigned_via=assigned_via
            )
```

(same pattern for `_cascade_to_lessons`), then:

```python
    async def _materialize_defaults(self, user_id: uuid.UUID, project_id: uuid.UUID) -> None:
        """Copy the project's default tracks (plus cascade) onto a user, additively."""
        track_ids = await self._org.default_track_ids(project_id)
        if not track_ids:
            return
        await self._assignments.set_user_tracks(user_id, track_ids, True, assigned_via="default")
        await self._cascade_to_modules_and_lessons(
            user_id, track_ids, True, assigned_via="default"
        )

    async def apply_project_defaults(self, project_id: uuid.UUID) -> int:
        """Backfill defaults onto every existing participant. Additive only —
        ON CONFLICT DO NOTHING means manual rows keep their provenance and
        nothing is ever removed."""
        if await self._org.get_project(project_id) is None:
            raise NotFoundError("Project")
        user_ids = await self._users.ids_for_project(project_id)
        for user_id in user_ids:
            await self._materialize_defaults(user_id, project_id)
        return len(user_ids)
```

In `invite()`: after `self._users.create(...)` returns `user`, add `await self._materialize_defaults(user.id, project.id)` and return the user. In `create_invited_users()`: same call inside the loop after each successful `create`.

`routers/admin_defaults.py`:

```python
@router.post("/projects/{project_id}/defaults/apply", response_model=ApplyDefaultsResponse)
async def apply_defaults(
    project_id: uuid.UUID, admin_user_service: AdminUserServiceDep
) -> ApplyDefaultsResponse:
    return ApplyDefaultsResponse(
        users_updated=await admin_user_service.apply_project_defaults(project_id)
    )
```

Authz entry:

```python
("defaults-apply", "POST", lambda s: f"/api/admin/projects/{s.project.id}/defaults/apply",
    lambda s: None, True),
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && uv run pytest tests/integration/test_routers/test_admin_defaults.py tests/integration/test_routers/test_admin_bulk_invite.py tests/integration/test_routers/test_authz.py -v`
Expected: PASS. Then the full gate (existing invite tests must stay green — projects without defaults are a no-op).

- [ ] **Step 5: Commit**

```bash
git add backend/src/ backend/tests/
git commit -m "feat(admin): materialize project defaults on invite + explicit apply action"
```

### Task 5: Multi-user bulk assignment — `POST /api/admin/assignments/bulk`

**Files:**
- Modify: `backend/src/repositories/base.py` + `backend/src/repositories/user_repository.py` (`count_by_ids`)
- Modify: `backend/src/schemas/admin_users.py` (`BulkAssignmentRequest`)
- Modify: `backend/src/services/admin_user_service.py` (`bulk_assign`)
- Modify: `backend/src/routers/admin_users.py` (route)
- Modify: `backend/tests/integration/test_routers/test_authz.py` (1 entry)
- Test: `backend/tests/integration/test_routers/test_admin_users.py` (new `TestMultiUserBulk` class)

**Interfaces:**
- Consumes: Task 2 repo kwargs; cascade helpers (Task 4 signatures).
- Produces:
  - `AbstractUserRepository.count_by_ids(user_ids: list[uuid.UUID]) -> int`
  - `AdminUserService.bulk_assign(user_ids, *, track_ids=None, module_ids=None, lesson_ids=None, assigned: bool) -> None` — validates ALL ids up front (404 before any write, matching the existing bulk atomicity convention), then per user writes + cascades with `assigned_via="manual"`.
  - `POST /api/admin/assignments/bulk` (204) with `BulkAssignmentRequest{user_ids[], exactly-one-of track_ids|module_ids|lesson_ids, assigned}` — 422 when zero or more than one content list is present, or any list is empty.

- [ ] **Step 1: Write the failing test**

```python
# append to backend/tests/integration/test_routers/test_admin_users.py
class TestMultiUserBulk:
    async def test_bulk_assign_tracks_cascades_for_every_user(
        self, client, db_session, test_settings
    ) -> None:
        admin = await create_user(db_session, email="mb1@x.test", role="admin")
        u1 = await create_user(db_session, email="mb-u1@x.test")
        u2 = await create_user(db_session, email="mb-u2@x.test")
        track = await create_track(db_session)
        module = await create_module(db_session, track_id=track.id)
        lesson = await create_lesson(db_session, module_id=module.id)
        resp = await client.post(
            "/api/admin/assignments/bulk",
            json={
                "user_ids": [str(u1.id), str(u2.id)],
                "track_ids": [str(track.id)],
                "assigned": True,
            },
            headers=auth_headers(admin, test_settings),
        )
        assert resp.status_code == 204
        for uid in (u1.id, u2.id):
            tracks = (
                await db_session.execute(select(UserTrack).where(UserTrack.user_id == uid))
            ).scalars().all()
            lessons = (
                await db_session.execute(select(UserLesson).where(UserLesson.user_id == uid))
            ).scalars().all()
            assert [t.track_id for t in tracks] == [track.id]
            assert [t.assigned_via for t in tracks] == ["manual"]
            assert [le.lesson_id for le in lessons] == [lesson.id]

    async def test_unknown_user_404_writes_nothing(self, client, db_session, test_settings) -> None:
        admin = await create_user(db_session, email="mb2@x.test", role="admin")
        u1 = await create_user(db_session, email="mb-u3@x.test")
        track = await create_track(db_session)
        resp = await client.post(
            "/api/admin/assignments/bulk",
            json={
                "user_ids": [str(u1.id), str(uuid.uuid4())],
                "track_ids": [str(track.id)],
                "assigned": True,
            },
            headers=auth_headers(admin, test_settings),
        )
        assert resp.status_code == 404
        assert (await db_session.execute(select(UserTrack))).scalars().all() == []

    async def test_two_content_kinds_422(self, client, db_session, test_settings) -> None:
        admin = await create_user(db_session, email="mb3@x.test", role="admin")
        u1 = await create_user(db_session, email="mb-u4@x.test")
        track = await create_track(db_session)
        module = await create_module(db_session, track_id=track.id)
        resp = await client.post(
            "/api/admin/assignments/bulk",
            json={
                "user_ids": [str(u1.id)],
                "track_ids": [str(track.id)],
                "module_ids": [str(module.id)],
                "assigned": True,
            },
            headers=auth_headers(admin, test_settings),
        )
        assert resp.status_code == 422

    async def test_no_content_kind_422(self, client, db_session, test_settings) -> None:
        admin = await create_user(db_session, email="mb4@x.test", role="admin")
        u1 = await create_user(db_session, email="mb-u5@x.test")
        resp = await client.post(
            "/api/admin/assignments/bulk",
            json={"user_ids": [str(u1.id)], "assigned": True},
            headers=auth_headers(admin, test_settings),
        )
        assert resp.status_code == 422

    async def test_bulk_unassign_removes_cascaded_rows(
        self, client, db_session, test_settings
    ) -> None:
        admin = await create_user(db_session, email="mb5@x.test", role="admin")
        u1 = await create_user(db_session, email="mb-u6@x.test")
        track = await create_track(db_session)
        module = await create_module(db_session, track_id=track.id)
        await create_lesson(db_session, module_id=module.id)
        headers = auth_headers(admin, test_settings)
        body = {"user_ids": [str(u1.id)], "track_ids": [str(track.id)]}
        await client.post("/api/admin/assignments/bulk", json={**body, "assigned": True}, headers=headers)
        resp = await client.post(
            "/api/admin/assignments/bulk", json={**body, "assigned": False}, headers=headers
        )
        assert resp.status_code == 204
        assert (await db_session.execute(select(UserLesson))).scalars().all() == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/integration/test_routers/test_admin_users.py::TestMultiUserBulk -v`
Expected: FAIL — 404/405 (route missing)

- [ ] **Step 3: Implement**

`repositories/base.py` (`AbstractUserRepository`) + `user_repository.py`:

```python
    @abstractmethod
    async def count_by_ids(self, user_ids: list[uuid.UUID]) -> int: ...
```

```python
    async def count_by_ids(self, user_ids: list[uuid.UUID]) -> int:
        result = await self._session.execute(
            select(func.count()).select_from(User).where(User.id.in_(user_ids))
        )
        return int(result.scalar_one())
```

`schemas/admin_users.py`:

```python
class BulkAssignmentRequest(BaseModel):
    """Many-users × one content kind (spec §4.2). Exactly one of the three id
    lists must be provided; all provided lists must be non-empty."""

    user_ids: list[uuid.UUID] = Field(min_length=1)
    track_ids: list[uuid.UUID] | None = Field(default=None, min_length=1)
    module_ids: list[uuid.UUID] | None = Field(default=None, min_length=1)
    lesson_ids: list[uuid.UUID] | None = Field(default=None, min_length=1)
    assigned: bool

    @model_validator(mode="after")
    def _exactly_one_kind(self) -> BulkAssignmentRequest:
        provided = [x for x in (self.track_ids, self.module_ids, self.lesson_ids) if x is not None]
        if len(provided) != 1:
            msg = "provide exactly one of track_ids, module_ids or lesson_ids"
            raise ValueError(msg)
        return self
```

(`model_validator` joins the existing pydantic imports.) `services/admin_user_service.py`:

```python
    async def bulk_assign(
        self,
        user_ids: list[uuid.UUID],
        *,
        track_ids: list[uuid.UUID] | None = None,
        module_ids: list[uuid.UUID] | None = None,
        lesson_ids: list[uuid.UUID] | None = None,
        assigned: bool,
    ) -> None:
        """Many-users bulk (spec §4.2): validate everything, then write per user.
        404 if ANY user or content id is unknown — before any write."""
        unique_users = list(set(user_ids))
        if await self._users.count_by_ids(unique_users) != len(unique_users):
            raise NotFoundError("User")
        if track_ids is not None:
            unique_ids = list(set(track_ids))
            if await self._content.count_tracks_by_ids(unique_ids) != len(unique_ids):
                raise NotFoundError("Track")
            for user_id in unique_users:
                await self._assignments.set_user_tracks(user_id, unique_ids, assigned)
                await self._cascade_to_modules_and_lessons(user_id, unique_ids, assigned)
        elif module_ids is not None:
            unique_ids = list(set(module_ids))
            if await self._content.count_modules_by_ids(unique_ids) != len(unique_ids):
                raise NotFoundError("Module")
            for user_id in unique_users:
                await self._assignments.set_user_modules(user_id, unique_ids, assigned)
                await self._cascade_to_lessons(user_id, unique_ids, assigned)
        elif lesson_ids is not None:
            unique_ids = list(set(lesson_ids))
            if await self._content.count_lessons_by_ids(unique_ids) != len(unique_ids):
                raise NotFoundError("Lesson")
            for user_id in unique_users:
                await self._assignments.set_user_lessons(user_id, unique_ids, assigned)
```

`routers/admin_users.py`:

```python
@router.post("/assignments/bulk", status_code=status.HTTP_204_NO_CONTENT)
async def bulk_assign(
    body: BulkAssignmentRequest, admin_user_service: AdminUserServiceDep
) -> None:
    await admin_user_service.bulk_assign(
        body.user_ids,
        track_ids=body.track_ids,
        module_ids=body.module_ids,
        lesson_ids=body.lesson_ids,
        assigned=body.assigned,
    )
```

Authz entry:

```python
("assignments-bulk", "POST", lambda s: "/api/admin/assignments/bulk",
    lambda s: {"user_ids": [str(s.other.id)], "track_ids": [str(s.track.id)], "assigned": True}, True),
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && uv run pytest tests/integration/test_routers/test_admin_users.py tests/integration/test_routers/test_authz.py -v`
Expected: PASS. Then the full gate.

- [ ] **Step 5: Commit**

```bash
git add backend/src/ backend/tests/
git commit -m "feat(admin): multi-user bulk assignment endpoint"
```

### Task 6: Feedback triage — status columns + admin queue endpoints

**Files:**
- Modify: `backend/src/db/models/feedback.py` (status/reviewed_at/reviewed_by)
- Create: `backend/alembic/versions/c6d7e8f9a0b1_feedback_triage.py`
- Modify: `backend/src/repositories/base.py` (`AbstractFeedbackRepository` + 5 methods)
- Modify: `backend/src/repositories/feedback_repository.py`
- Modify: `backend/src/services/feedback_service.py` (admin list + set_status)
- Create: `backend/src/schemas/admin_feedback.py`
- Create: `backend/src/routers/admin_feedback.py`
- Modify: `backend/src/main.py` (register), `backend/src/core/dependencies/domain.py` (only if `get_feedback_service` needs no change — it already composes feedback+content repos; verify)
- Modify: `backend/tests/integration/test_routers/test_authz.py` (2 entries)
- Test: `backend/tests/integration/test_routers/test_admin_feedback.py`

**Interfaces:**
- Produces:
  - `Feedback.status: Mapped[str]` (NOT NULL, server_default `'new'`, CHECK `IN ('new','accepted','dismissed')`), `reviewed_at: Mapped[datetime | None]`, `reviewed_by: Mapped[uuid.UUID | None]` (FK users.id ON DELETE SET NULL).
  - Repo: `list_admin(*, status=None, track_id=None, project_id=None, limit, offset) -> list[Row]` (joined: Feedback + user first/last + company/project names + lesson title + module id/title + track id/name/required_level), `count_admin(*, status=None, track_id=None, project_id=None) -> int`, `count_new(project_id=None) -> int`, `get_by_id(feedback_id) -> Feedback | None`, `set_status(feedback, status, reviewed_by) -> None`.
  - Service: `FeedbackService.list_admin(...) -> tuple[list[dict], int]`, `FeedbackService.set_status(feedback_id, status, reviewed_by) -> None` (404 unknown id; `status='new'` clears `reviewed_*`, else stamps `reviewed_at=now`, `reviewed_by=admin id`).
  - Endpoints: `GET /api/admin/feedback?status=&track_id=&project_id=&limit=&offset=` → `AdminFeedbackListResponse{items, total, limit, offset}` (limit default 50, max 200 — **paginated from day one**, spec §4.6); `PATCH /api/admin/feedback/{feedback_id}` (204) with `FeedbackStatusUpdateRequest{status}`.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/integration/test_routers/test_admin_feedback.py
from __future__ import annotations

import uuid

from sqlalchemy import select

from src.db.models import Feedback
from tests.fixtures.auth import auth_headers
from tests.fixtures.factories import (
    create_company,
    create_lesson,
    create_module,
    create_project,
    create_track,
    create_user,
)


async def _seed(db_session):
    company = await create_company(db_session)
    project = await create_project(db_session, company_id=company.id)
    learner = await create_user(
        db_session, email=f"{uuid.uuid4()}@x.test", project_id=project.id, company_id=company.id
    )
    track = await create_track(db_session)
    module = await create_module(db_session, track_id=track.id)
    lesson = await create_lesson(db_session, module_id=module.id)
    fb = Feedback(user_id=learner.id, lesson_id=lesson.id, message="More examples please")
    db_session.add(fb)
    await db_session.commit()
    await db_session.refresh(fb)
    return project, track, module, lesson, learner, fb


class TestAdminFeedbackList:
    async def test_list_joins_names_and_defaults_to_new(
        self, client, db_session, test_settings
    ) -> None:
        admin = await create_user(db_session, email="fb1@x.test", role="admin")
        project, track, module, lesson, learner, fb = await _seed(db_session)
        resp = await client.get(
            "/api/admin/feedback", headers=auth_headers(admin, test_settings)
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 1
        item = body["items"][0]
        assert item["id"] == str(fb.id)
        assert item["status"] == "new"
        assert item["message"] == "More examples please"
        assert item["lesson_title"] == lesson.title
        assert item["module_id"] == str(module.id)
        assert item["track_id"] == str(track.id)
        assert item["project_name"] == project.name

    async def test_status_and_track_filters(self, client, db_session, test_settings) -> None:
        admin = await create_user(db_session, email="fb2@x.test", role="admin")
        _, track, _, _, _, fb = await _seed(db_session)
        headers = auth_headers(admin, test_settings)
        assert (
            await client.get("/api/admin/feedback?status=accepted", headers=headers)
        ).json()["total"] == 0
        assert (
            await client.get(f"/api/admin/feedback?track_id={track.id}", headers=headers)
        ).json()["total"] == 1
        assert (
            await client.get(f"/api/admin/feedback?track_id={uuid.uuid4()}", headers=headers)
        ).json()["total"] == 0

    async def test_pagination_contract(self, client, db_session, test_settings) -> None:
        admin = await create_user(db_session, email="fb3@x.test", role="admin")
        project, track, module, lesson, learner, _ = await _seed(db_session)
        for i in range(3):
            db_session.add(
                Feedback(user_id=learner.id, lesson_id=lesson.id, message=f"note {i}")
            )
        await db_session.commit()
        resp = await client.get(
            "/api/admin/feedback?limit=2&offset=2", headers=auth_headers(admin, test_settings)
        )
        body = resp.json()
        assert body["total"] == 4
        assert body["limit"] == 2 and body["offset"] == 2
        assert len(body["items"]) == 2


class TestFeedbackTriage:
    async def test_accept_stamps_reviewer(self, client, db_session, test_settings) -> None:
        admin = await create_user(db_session, email="fb4@x.test", role="admin")
        *_, fb = await _seed(db_session)
        resp = await client.patch(
            f"/api/admin/feedback/{fb.id}",
            json={"status": "accepted"},
            headers=auth_headers(admin, test_settings),
        )
        assert resp.status_code == 204
        row = (await db_session.execute(select(Feedback))).scalar_one()
        assert row.status == "accepted"
        assert row.reviewed_by == admin.id
        assert row.reviewed_at is not None

    async def test_back_to_new_clears_review_stamp(
        self, client, db_session, test_settings
    ) -> None:
        admin = await create_user(db_session, email="fb5@x.test", role="admin")
        *_, fb = await _seed(db_session)
        headers = auth_headers(admin, test_settings)
        await client.patch(f"/api/admin/feedback/{fb.id}", json={"status": "dismissed"}, headers=headers)
        resp = await client.patch(f"/api/admin/feedback/{fb.id}", json={"status": "new"}, headers=headers)
        assert resp.status_code == 204
        row = (await db_session.execute(select(Feedback))).scalar_one()
        assert row.status == "new"
        assert row.reviewed_by is None and row.reviewed_at is None

    async def test_unknown_id_404_and_bad_status_422(
        self, client, db_session, test_settings
    ) -> None:
        admin = await create_user(db_session, email="fb6@x.test", role="admin")
        *_, fb = await _seed(db_session)
        headers = auth_headers(admin, test_settings)
        assert (
            await client.patch(
                f"/api/admin/feedback/{uuid.uuid4()}", json={"status": "accepted"}, headers=headers
            )
        ).status_code == 404
        assert (
            await client.patch(
                f"/api/admin/feedback/{fb.id}", json={"status": "resolved"}, headers=headers
            )
        ).status_code == 422
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/integration/test_routers/test_admin_feedback.py -v`
Expected: FAIL — 404 (routes missing)

- [ ] **Step 3: Implement model + migration**

`db/models/feedback.py` — add imports (`CheckConstraint`, `text`) and:

```python
    __table_args__ = (
        CheckConstraint("status IN ('new','accepted','dismissed')", name="status"),
    )
    ...
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'new'"))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
```

Migration `c6d7e8f9a0b1_feedback_triage.py` (`down_revision = "b5c6d7e8f9a0"` — chains after Task 1; re-run the `alembic heads` single-head check from Task 0 before committing):

```python
def upgrade() -> None:
    op.add_column(
        "feedback",
        sa.Column("status", sa.Text(), server_default=sa.text("'new'"), nullable=False),
    )
    op.add_column("feedback", sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("feedback", sa.Column("reviewed_by", sa.UUID(), nullable=True))
    op.create_check_constraint(
        op.f("ck_feedback_status"), "feedback", "status IN ('new','accepted','dismissed')"
    )
    op.create_foreign_key(
        op.f("fk_feedback_reviewed_by_users"),
        "feedback",
        "users",
        ["reviewed_by"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(op.f("fk_feedback_reviewed_by_users"), "feedback", type_="foreignkey")
    op.drop_constraint(op.f("ck_feedback_status"), "feedback", type_="check")
    op.drop_column("feedback", "reviewed_by")
    op.drop_column("feedback", "reviewed_at")
    op.drop_column("feedback", "status")
```

- [ ] **Step 4: Implement repository → service → schema → router**

`repositories/base.py` (`AbstractFeedbackRepository`):

```python
    @abstractmethod
    async def get_by_id(self, feedback_id: uuid.UUID) -> Feedback | None: ...

    @abstractmethod
    async def set_status(
        self, feedback: Feedback, status: str, reviewed_by: uuid.UUID | None
    ) -> None: ...

    @abstractmethod
    async def list_admin(
        self,
        *,
        status: str | None = None,
        track_id: uuid.UUID | None = None,
        project_id: uuid.UUID | None = None,
        limit: int,
        offset: int,
    ) -> list[Any]: ...

    @abstractmethod
    async def count_admin(
        self,
        *,
        status: str | None = None,
        track_id: uuid.UUID | None = None,
        project_id: uuid.UUID | None = None,
    ) -> int: ...

    @abstractmethod
    async def count_new(self, project_id: uuid.UUID | None = None) -> int: ...
```

`feedback_repository.py` — one join spine shared by list/count:

```python
    def _admin_query(self, status: str | None, track_id: uuid.UUID | None, project_id: uuid.UUID | None):
        query = (
            select(
                Feedback,
                User.first_name,
                User.last_name,
                Company.name.label("company_name"),
                Project.name.label("project_name"),
                Lesson.title.label("lesson_title"),
                Module.id.label("module_id"),
                Module.title.label("module_title"),
                Track.id.label("track_id"),
                Track.name.label("track_name"),
                Track.required_level.label("track_level"),
            )
            .join(User, User.id == Feedback.user_id)
            .outerjoin(Company, Company.id == User.company_id)
            .outerjoin(Project, Project.id == User.project_id)
            .join(Lesson, Lesson.id == Feedback.lesson_id)
            .join(Module, Module.id == Lesson.module_id)
            .join(Track, Track.id == Module.track_id)
        )
        if status is not None:
            query = query.where(Feedback.status == status)
        if track_id is not None:
            query = query.where(Track.id == track_id)
        if project_id is not None:
            query = query.where(User.project_id == project_id)
        return query

    async def list_admin(self, *, status=None, track_id=None, project_id=None, limit, offset):
        query = (
            self._admin_query(status, track_id, project_id)
            .order_by(Feedback.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list((await self._session.execute(query)).all())

    async def count_admin(self, *, status=None, track_id=None, project_id=None) -> int:
        query = select(func.count()).select_from(
            self._admin_query(status, track_id, project_id).subquery()
        )
        return int((await self._session.execute(query)).scalar_one())

    async def count_new(self, project_id: uuid.UUID | None = None) -> int:
        return await self.count_admin(status="new", project_id=project_id)

    async def get_by_id(self, feedback_id: uuid.UUID) -> Feedback | None:
        result = await self._session.execute(select(Feedback).where(Feedback.id == feedback_id))
        return result.scalar_one_or_none()

    async def set_status(
        self, feedback: Feedback, status: str, reviewed_by: uuid.UUID | None
    ) -> None:
        feedback.status = status
        feedback.reviewed_by = reviewed_by
        feedback.reviewed_at = None if reviewed_by is None else datetime.now(UTC)
        await self._session.commit()
```

(Full type annotations per house rules; imports: `datetime`/`UTC`, `func`, and the joined models.) `services/feedback_service.py`:

```python
    async def list_admin(
        self,
        *,
        status: str | None = None,
        track_id: uuid.UUID | None = None,
        project_id: uuid.UUID | None = None,
        limit: int,
        offset: int,
    ) -> tuple[list[dict[str, Any]], int]:
        rows = await self._feedback.list_admin(
            status=status, track_id=track_id, project_id=project_id, limit=limit, offset=offset
        )
        total = await self._feedback.count_admin(
            status=status, track_id=track_id, project_id=project_id
        )
        items = [
            {
                "id": fb.id,
                "user_id": fb.user_id,
                "user_name": f"{first_name} {last_name}",
                "company_name": company_name,
                "project_name": project_name,
                "lesson_id": fb.lesson_id,
                "lesson_title": lesson_title,
                "module_id": module_id,
                "module_title": module_title,
                "track_id": track_id_,
                "track_name": track_name,
                "track_level": track_level,
                "message": fb.message,
                "status": fb.status,
                "created_at": fb.created_at,
                "reviewed_at": fb.reviewed_at,
            }
            for (
                fb, first_name, last_name, company_name, project_name, lesson_title,
                module_id, module_title, track_id_, track_name, track_level,
            ) in rows
        ]
        return items, total

    async def set_status(
        self, feedback_id: uuid.UUID, status: str, reviewed_by: uuid.UUID
    ) -> None:
        feedback = await self._feedback.get_by_id(feedback_id)
        if feedback is None:
            raise NotFoundError("Feedback")
        reviewer = None if status == "new" else reviewed_by
        await self._feedback.set_status(feedback, status, reviewer)
```

`schemas/admin_feedback.py`:

```python
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel

__all__ = ["AdminFeedbackListResponse", "AdminFeedbackOut", "FeedbackStatusUpdateRequest"]

FeedbackStatus = Literal["new", "accepted", "dismissed"]


class AdminFeedbackOut(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    user_name: str
    company_name: str | None
    project_name: str | None
    lesson_id: uuid.UUID
    lesson_title: str
    module_id: uuid.UUID
    module_title: str
    track_id: uuid.UUID
    track_name: str
    track_level: str
    message: str
    status: FeedbackStatus
    created_at: datetime
    reviewed_at: datetime | None


class AdminFeedbackListResponse(BaseModel):
    items: list[AdminFeedbackOut]
    total: int
    limit: int
    offset: int


class FeedbackStatusUpdateRequest(BaseModel):
    status: FeedbackStatus
```

`routers/admin_feedback.py` — note the reviewer comes from `require_admin`'s returned `User` (same pattern as `admin_users.py`'s rate-limit keys); alias `status` because it shadows the `fastapi.status` module:

```python
router = APIRouter(prefix="/api/admin", tags=["admin:feedback"])


@router.get("/feedback", response_model=AdminFeedbackListResponse)
async def list_feedback(
    feedback_service: FeedbackServiceDep,
    _admin: Annotated[User, Depends(require_admin)],
    status_filter: Annotated[
        Literal["new", "accepted", "dismissed"] | None, Query(alias="status")
    ] = None,
    track_id: uuid.UUID | None = None,
    project_id: uuid.UUID | None = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> AdminFeedbackListResponse:
    items, total = await feedback_service.list_admin(
        status=status_filter, track_id=track_id, project_id=project_id, limit=limit, offset=offset
    )
    return AdminFeedbackListResponse(
        items=[AdminFeedbackOut.model_validate(item) for item in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.patch("/feedback/{feedback_id}", status_code=status.HTTP_204_NO_CONTENT)
async def set_feedback_status(
    feedback_id: uuid.UUID,
    body: FeedbackStatusUpdateRequest,
    feedback_service: FeedbackServiceDep,
    admin: Annotated[User, Depends(require_admin)],
) -> None:
    await feedback_service.set_status(feedback_id, body.status, admin.id)
```

(`AdminFeedbackOut.model_validate(item)` needs `model_config = ConfigDict(from_attributes=False)` default — items are dicts, which `model_validate` accepts natively. `FeedbackServiceDep` = the existing DI alias for `get_feedback_service`; verify its name in `routers/feedback.py` and reuse.) Register in `main.py`. Authz entries (`s` scenario needs a feedback row — check whether the authz scenario fixture already creates one; if not, extend the fixture the same way it creates `s.lesson`):

```python
("feedback-admin-list", "GET", lambda s: "/api/admin/feedback", lambda s: None, True),
("feedback-admin-patch", "PATCH", lambda s: f"/api/admin/feedback/{s.feedback.id}",
    lambda s: {"status": "accepted"}, True),
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd backend && uv run pytest tests/integration/test_routers/test_admin_feedback.py tests/integration/test_routers/test_authz.py tests/integration/test_routers/test_feedback.py -v`
Expected: PASS (learner-facing POST untouched). Then the full gate.

- [ ] **Step 6: Commit**

```bash
git add backend/src/ backend/alembic/versions/c6d7e8f9a0b1_feedback_triage.py backend/tests/
git commit -m "feat(admin): feedback triage - status columns + admin queue endpoints"
```

### Task 7: Reminder email — `POST /api/admin/users/{id}/reminder`

**Files:**
- Modify: `backend/src/services/email_templates.py` (reminder template + token builder)
- Modify: `backend/src/services/admin_user_service.py` (`reminder_context`)
- Modify: `backend/src/schemas/admin_users.py` (`ReminderResponse`)
- Modify: `backend/src/routers/admin_users.py` (route)
- Modify: `backend/tests/integration/test_routers/test_authz.py` (1 entry)
- Test: `backend/tests/integration/test_routers/test_admin_reminder.py`, `backend/tests/unit/test_email_templates.py` (extend)

**Interfaces:**
- Consumes: `EmailService.send(to, content) -> bool`, `render_email(subject, body_markdown, *, tokens)`, `EmailTemplate` NamedTuple, the router-level email pattern from `create_reset_link` (feature-flagged: DI yields `None` when `EMAIL__*` unset), the existing rate limiter (`reset:{email}` pattern).
- Produces:
  - `REMINDER_TEMPLATE: EmailTemplate` module constant + `build_reminder_tokens(*, first_name, last_name, project_name, login_url) -> dict[str, str]` in `email_templates.py`. **Not per-project-customizable** (spec §3.6 lists only Invitation/Password reset pills) — rendered from the constant, never from `project_email_templates`.
  - `AdminUserService.reminder_context(user_id) -> tuple[User, str]` (user + project name, `""` when the user has no project; 404 unknown user).
  - `POST /api/admin/users/{user_id}/reminder` → 200 `ReminderResponse{email_status: EmailStatus}` — reuses the existing `"sent"/"failed"/"disabled"` semantics (never `"skipped"`); a failed send never fails the endpoint. Rate-limit key `reminder:{email}`, same budget as `reset`.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/integration/test_routers/test_admin_reminder.py
from __future__ import annotations

import uuid

from tests.fixtures.auth import auth_headers
from tests.fixtures.factories import create_company, create_project, create_user


class TestReminder:
    async def test_disabled_when_email_unconfigured(
        self, client, db_session, test_settings
    ) -> None:
        admin = await create_user(db_session, email="r1@x.test", role="admin")
        learner = await create_user(db_session, email="r-l1@x.test")
        resp = await client.post(
            f"/api/admin/users/{learner.id}/reminder",
            headers=auth_headers(admin, test_settings),
        )
        assert resp.status_code == 200
        assert resp.json() == {"email_status": "disabled"}

    async def test_unknown_user_404(self, client, db_session, test_settings) -> None:
        admin = await create_user(db_session, email="r2@x.test", role="admin")
        resp = await client.post(
            f"/api/admin/users/{uuid.uuid4()}/reminder",
            headers=auth_headers(admin, test_settings),
        )
        assert resp.status_code == 404
```

Plus a `"sent"`/`"failed"` pair using the stub email fixture — copy the exact client/fixture wiring from `test_admin_email.py` (it overrides the email DI with `tests/fixtures/email.py`'s stub sender; assert the stub captured a message whose plain text contains the learner's first name and `/login`, and that a raising stub yields `{"email_status": "failed"}` with HTTP 200).

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/integration/test_routers/test_admin_reminder.py -v`
Expected: FAIL — 404/405 (route missing)

- [ ] **Step 3: Implement**

`services/email_templates.py`:

```python
REMINDER_TEMPLATE = EmailTemplate(
    subject="Continue your AI learning journey",
    body_markdown=(
        "Hi {{first_name}},\n\n"
        "You have learning content waiting for you on the AI Enablement Hub"
        "{{project_suffix}}.\n\n"
        "[Continue learning]({{login_url}})\n\n"
        "See you there!"
    ),
)


def build_reminder_tokens(
    *, first_name: str, last_name: str, project_name: str, login_url: str
) -> dict[str, str]:
    return {
        "first_name": first_name,
        "last_name": last_name,
        "project_name": project_name,
        "project_suffix": f" for {project_name}" if project_name else "",
        "login_url": login_url,
    }
```

(Match the exact link-rendering mechanics of `DEFAULT_TEMPLATES` — if the existing templates render links via a raw URL token rather than markdown link syntax, mirror that instead.)

`services/admin_user_service.py`:

```python
    async def reminder_context(self, user_id: uuid.UUID) -> tuple[User, str]:
        user = await self._users.get_by_id(user_id)
        if user is None:
            raise NotFoundError("User")
        project_name = ""
        if user.project_id is not None:
            project = await self._org.get_project(user.project_id)
            if project is not None:
                project_name = project.name
        return user, project_name
```

`schemas/admin_users.py`: `class ReminderResponse(BaseModel): email_status: EmailStatus`.

`routers/admin_users.py` — copy the shape of `create_reset_link`'s email branch (rate limiter, settings, optional `EmailService`):

```python
@router.post("/users/{user_id}/reminder", response_model=ReminderResponse)
async def send_reminder(
    user_id: uuid.UUID,
    admin_user_service: AdminUserServiceDep,
    email_service: EmailServiceDep,  # same optional DI the invite/reset routes use
    settings: SettingsDep,
) -> ReminderResponse:
    user, project_name = await admin_user_service.reminder_context(user_id)
    check_rate_limit(f"reminder:{user.email}")  # exact helper/name as used by the reset route
    if email_service is None:
        return ReminderResponse(email_status="disabled")
    content = render_email(
        REMINDER_TEMPLATE.subject,
        REMINDER_TEMPLATE.body_markdown,
        tokens=build_reminder_tokens(
            first_name=user.first_name,
            last_name=user.last_name,
            project_name=project_name,
            login_url=f"{settings.app.url}/login",
        ),
    )
    sent = await email_service.send(user.email, content)
    return ReminderResponse(email_status="sent" if sent else "failed")
```

(The dep aliases, rate-limit helper name, and `settings.app.url` attribute must be copied verbatim from the existing invite/reset handlers in this file — do not guess; open the file and mirror.) Authz entry:

```python
("reminder", "POST", lambda s: f"/api/admin/users/{s.other.id}/reminder", lambda s: None, True),
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && uv run pytest tests/integration/test_routers/test_admin_reminder.py tests/unit/test_email_templates.py tests/integration/test_routers/test_authz.py -v`
Expected: PASS. Then the full gate.

- [ ] **Step 5: Commit**

```bash
git add backend/src/ backend/tests/
git commit -m "feat(admin): reminder email endpoint"
```

### Task 8: Kill the full-table scans + enrich the admin user payload (status/progress/attention/provenance)

**Files:**
- Create: `backend/src/core/attention.py` (pure helpers + thresholds)
- Modify: `backend/src/repositories/base.py` (scoped assignment reads; `last_used_by_user`; `latest_completion_by_user`; `user_ids_with_survey`)
- Modify: `backend/src/repositories/assignment_repository.py`, `auth_session_repository.py` (or wherever `AuthSessionRepository` lives), `progress_repository.py`, `survey_repository.py`
- Modify: `backend/src/services/admin_user_service.py` (ctor + `list_users` + `learning_overview`)
- Modify: `backend/src/core/dependencies/domain.py` (provider gains the two new repo args)
- Modify: `backend/src/schemas/admin_users.py` (`AdminUserOut` + `AdminLearningUserOut` additive fields)
- Test: `backend/tests/unit/test_attention.py`, extend `backend/tests/integration/test_routers/test_admin_users.py`

**Interfaces:**
- Produces (repo):
  - `AbstractAssignmentRepository.user_tracks_for_users(user_ids) -> list[UserTrack]` (+ `user_modules_for_users`, `user_lessons_for_users`) — `select(X).where(X.user_id.in_(user_ids))`; ORM rows carry `assigned_via`. The unfiltered `all_user_tracks/all_user_modules/all_user_lessons` are then **deleted** (grep first: `list_users` and `learning_overview` are the only callers).
  - `AbstractAuthSessionRepository.last_used_by_user(user_ids) -> dict[uuid.UUID, datetime]` — `select(user_id, func.max(last_used_at)).group_by(user_id)`, absent key = never active.
  - `AbstractProgressRepository.latest_completion_by_user(user_ids) -> dict[uuid.UUID, datetime]` — max `completed_at` per user.
  - `AbstractSurveyRepository.user_ids_with_survey(user_ids) -> set[uuid.UUID]` — any survey row (draft counts as "started").
- Produces (`core/attention.py`) — **pure, no I/O**, the single home of the attention rules shared by People and Dashboard (services must not duplicate each other's logic and never call each other):

```python
STALLED_DAYS = 14      # locked, spec §4.4
ACTIVE_DAYS = 7        # locked, spec §4.4
NUDGE_DAYS = 7         # chosen default for "invited, never activated" / "activated, not assessed" — Aaron may tune

def attention_for(
    *, now: datetime, created_at: datetime, activated: bool, activated_known_since: datetime,
    has_survey: bool, latest_completion: datetime | None,
    assigned_total: int, completed_total: int, track_names_in_progress: list[str],
) -> tuple[str, str] | None:
    """Returns (kind, human reason) or None.
    kinds: 'never_activated' | 'not_assessed' | 'stalled'."""
```

  with the three rules: not activated and invited ≥ `NUDGE_DAYS` ago → `("never_activated", "Invited, never activated")`; activated, no survey row, ≥ `NUDGE_DAYS` since `activated_known_since` → `("not_assessed", f"Activated {days} days ago, assessment not started")`; `completed_total < assigned_total` and `latest_completion` older than `STALLED_DAYS` → `("stalled", f"Stalled in {track_names_in_progress[0]} for {days} days")` (fallback reason without a track name when the list is empty). NOTE: `users` has no "activated_at" column — use `max(created_at, first session's last_used_at)` as `activated_known_since` (approximation; document in the docstring).
- Produces (schema, all **additive**): `AdminUserOut` gains `last_active_at: datetime | None`, `activated: bool`, `assigned_lesson_count: int`, `completed_lesson_count: int`, `needs_attention: bool`, `attention_reason: str | None`, `default_track_ids/default_module_ids/default_lesson_ids: list[uuid.UUID]`; `AdminLearningUserOut` gains the three `default_*_ids` lists (the matrix's "via default" tint).
- `AdminUserService.__init__` gains `sessions: AbstractAuthSessionRepository` and `progress: AbstractProgressRepository` (update DI provider + every unit-test constructor call).

- [ ] **Step 1: Write failing unit tests for the pure rules**

```python
# backend/tests/unit/test_attention.py
from __future__ import annotations

from datetime import UTC, datetime, timedelta

from src.core.attention import attention_for

NOW = datetime(2026, 7, 23, 12, 0, tzinfo=UTC)


def _base(**overrides):
    kwargs = {
        "now": NOW,
        "created_at": NOW - timedelta(days=30),
        "activated": True,
        "activated_known_since": NOW - timedelta(days=30),
        "has_survey": True,
        "latest_completion": NOW - timedelta(days=1),
        "assigned_total": 10,
        "completed_total": 3,
        "track_names_in_progress": ["Copilot"],
    }
    kwargs.update(overrides)
    return kwargs


def test_healthy_learner_is_none() -> None:
    assert attention_for(**_base()) is None


def test_never_activated_after_nudge_window() -> None:
    kind, reason = attention_for(**_base(activated=False, has_survey=False))
    assert kind == "never_activated"


def test_fresh_invite_not_flagged() -> None:
    assert (
        attention_for(
            **_base(
                activated=False, has_survey=False, created_at=NOW - timedelta(days=2)
            )
        )
        is None
    )


def test_not_assessed() -> None:
    kind, reason = attention_for(**_base(has_survey=False, latest_completion=None,
                                         assigned_total=0, completed_total=0))
    assert kind == "not_assessed"
    assert "assessment not started" in reason


def test_stalled_with_track_name() -> None:
    kind, reason = attention_for(**_base(latest_completion=NOW - timedelta(days=16)))
    assert kind == "stalled"
    assert "Copilot" in reason and "16 days" in reason


def test_completed_everything_never_stalls() -> None:
    assert (
        attention_for(**_base(completed_total=10, latest_completion=NOW - timedelta(days=60)))
        is None
    )
```

- [ ] **Step 2: Run, verify fail, implement `core/attention.py`, verify pass**

Run: `cd backend && uv run pytest tests/unit/test_attention.py -v` (FAIL: no module → implement → PASS). Implementation is a direct transcription of the three rules above; days rendered with `(now - x).days`.

- [ ] **Step 3: Write the failing integration assertions**

Extend `test_admin_users.py` (new class `TestAdminUserEnrichment`): seed one project with an activated learner (factory `password_set=True` — check the factory's kwarg, else set the column directly) who completed 1 of 2 assigned lessons 20 days ago → assert their `AdminUserOut` row has `activated is True`, `assigned_lesson_count == 2`, `completed_lesson_count == 1`, `needs_attention is True`, `"Stalled" in attention_reason`; a second user assigned a track via `assigned_via='default'` rows → assert the track id appears in both `assigned_track_ids` and `default_track_ids`. Assert `GET /api/admin/learning` users carry `default_track_ids` too.

- [ ] **Step 4: Implement repos + service enrichment**

Repo methods per the Interfaces block (each is one grouped/filtered `select`; follow the exact style of `assigned_lesson_counts_by_module_for_users` in `assignment_repository.py`). Then in `AdminUserService.list_users`:

1. `rows = await self._users.list_with_org_names(project_id)`; `user_ids = [u.id for u, _, _ in rows]`.
2. Replace `_assignment_maps()` with `_assignment_maps_for(user_ids)` — same dict-building loops over the three `*_for_users` queries, but ALSO build `default_track_map/default_module_map/default_lesson_map` from rows where `link.assigned_via == "default"`.
3. Fetch once for all users: `counts = await self._assignments.assigned_lesson_counts_by_module_for_users(user_ids)`, `last_active = await self._sessions.last_used_by_user(user_ids)`, `latest = await self._progress.latest_completion_by_user(user_ids)`, `surveyed = await self._surveys.user_ids_with_survey(user_ids)`. Pass `counts` into `_effective_maturity_map` (add a parameter; it currently re-fetches internally for scored users only).
4. Per user compute: `assigned_total/completed_total = sums over counts[user.id]`; `activated = user.password_set or user.external_id is not None`; `track_names_in_progress` = names of assigned tracks whose module counts show `completed < assigned` (build from `track_map` + `self._content.list_tracks()` already fetched for maturity); call `attention_for(...)`; emit the new dict fields.
5. `learning_overview()` switches to the same scoped `_assignment_maps_for` (it lists all users today — pass their ids) and emits `default_*_ids`.

Update `get_admin_user_service` in `core/dependencies/domain.py` (add the two `Depends` args — runtime imports) and every unit test constructing `AdminUserService` directly.

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd backend && uv run pytest tests/unit/test_attention.py tests/integration/test_routers/test_admin_users.py -v`
Expected: PASS. Then the full gate — **the whole existing suite must stay green** (additive response fields; removed repo methods had exactly two callers, both migrated).

- [ ] **Step 6: Commit**

```bash
git add backend/src/ backend/tests/
git commit -m "feat(admin): scoped assignment reads + status/progress/attention enrichment"
```

### Task 9: Pagination + search/status filters on `/admin/users` and `/admin/learning`

**Files:**
- Modify: `backend/src/repositories/base.py` + `user_repository.py` (`list_with_org_names` gains `q`)
- Modify: `backend/src/services/admin_user_service.py` (`list_users` / `learning_overview` signatures)
- Modify: `backend/src/schemas/admin_users.py` (`total` on both envelopes)
- Modify: `backend/src/routers/admin_users.py` (query params)
- Test: extend `backend/tests/integration/test_routers/test_admin_users.py`

**Interfaces:**
- **Back-compat is the design constraint:** `limit`/`offset` are optional; omitted → full list exactly as today (the live old panel sends no params). `total` is an additive response field.
- Produces:
  - `list_with_org_names(project_id=None, q: str | None = None)` — `q` adds `ILIKE %q%` over `first_name`, `last_name`, `email` (`sa.or_`).
  - `AdminUserService.list_users(project_id=None, *, q=None, status=None, limit=None, offset=0) -> tuple[list[dict], int]` — `status: Literal['active','invited','attention'] | None` filters **after** enrichment (attention is computed, not stored; at our scale — tens to low hundreds of users — Python filtering after set-based queries is fine and documented); returns `(page, total_after_filters)`.
  - `AdminUserService.learning_overview(*, project_id=None, limit=None, offset=0) -> dict` — paginates the `users` array only; also gains the `project_id` filter (the matrix is always project-scoped per the spec — today it lists everyone); `modules`/`lessons` stay complete.
  - Router: `GET /api/admin/users?project_id=&q=&status=&limit=&offset=` (limit `ge=1 le=200`), `GET /api/admin/learning?project_id=&limit=&offset=`. Envelopes: `AdminUsersResponse{users, total}`, `AdminLearningResponse{modules, lessons, users, total}`.

- [ ] **Step 1: Write the failing tests** — new class `TestAdminUsersPagination` in `test_admin_users.py`: seed 5 learners; assert (a) no params → 5 users, `total == 5` (back-compat); (b) `limit=2&offset=2` → 2 users, `total == 5`; (c) `q=` matching one email → 1/1; (d) `status=invited` returns only non-activated users; (e) `/api/admin/learning?limit=2` pages users and keeps full `modules`. Follow the existing test style in the file (real code, seeded via factories, exact status-code + body asserts).

- [ ] **Step 2: Run to verify failure** (`total` missing / params ignored), **then implement** per the Interfaces block: repo `q` filter; service slices `page = enriched[offset : offset + limit] if limit is not None else enriched[offset:]` after the status filter; `total = len(enriched)` post-filter pre-slice; router forwards params and builds the envelope with `total`.

- [ ] **Step 3: Full gate** — existing `test_admin_users.py` tests (no params) must pass unchanged apart from mechanically adding the new envelope field where a test asserts the exact body.

- [ ] **Step 4: Commit**

```bash
git add backend/src/ backend/tests/
git commit -m "feat(admin): pagination + q/status filters on admin users and learning"
```

### Task 10: Dashboard aggregates — `GET /api/admin/dashboard`

**Files:**
- Create: `backend/src/services/dashboard_service.py`
- Create: `backend/src/schemas/admin_dashboard.py`
- Create: `backend/src/routers/admin_dashboard.py`
- Modify: `backend/src/core/dependencies/domain.py` (`get_dashboard_service`), `backend/src/main.py` (register)
- Modify: `backend/tests/integration/test_routers/test_authz.py` (1 entry)
- Test: `backend/tests/integration/test_routers/test_admin_dashboard.py`

**Interfaces:**
- Consumes: Task 8's repo methods (`last_used_by_user`, `latest_completion_by_user`, `user_ids_with_survey`, `assigned_lesson_counts_by_module_for_users`, `user_tracks_for_users`), Task 6's `count_new`, `core/attention.py`, `core/constants.advance_level`, `SurveyRepository.get_complete_levels`.
- Produces `DashboardService(users, assignments, content, surveys, sessions, progress, feedback: Abstract*Repository)` with one public method `overview(project_id: uuid.UUID | None) -> dict[str, Any]`, and:

```python
# schemas/admin_dashboard.py
class DashboardTiles(BaseModel):
    learners: int          # non-admin users in scope
    active_week: int       # last activity <= 7 days (locked)
    attention: int
    new_feedback: int

class AttentionItemOut(BaseModel):
    user_id: uuid.UUID
    name: str
    email: str
    project_id: uuid.UUID | None
    project_name: str | None
    company_name: str | None
    kind: Literal["never_activated", "not_assessed", "stalled"]
    reason: str

class FunnelOut(BaseModel):
    project_id: uuid.UUID
    project_name: str
    company_name: str
    invited: int           # all learners of the project
    activated: int
    assessed: int
    started: int           # >= 1 lesson completed
    completed_track: int   # >= 1 assigned track fully completed (locked definition)

class MaturityDistributionOut(BaseModel):
    explore: int
    practitioner: int
    integrator: int
    multiplier: int

class DashboardResponse(BaseModel):
    tiles: DashboardTiles
    attention: list[AttentionItemOut]
    funnels: list[FunnelOut]
    maturity: MaturityDistributionOut
```

  - Endpoint: `GET /api/admin/dashboard?project_id=` → `DashboardResponse`, one call for the whole screen (spec §4.4). Unknown `project_id` → 404 (use `OrgRepository.get_project`; add the org repo to the ctor if cleaner — decide when writing, either is convention-clean).
  - "Completed a track" per user: group `assigned_lesson_counts_by_module_for_users` by each assigned track's modules (module→track map from `content.list_modules()`); a track counts when its per-module sums have `total > 0` and `completed == total` for every module with assigned lessons.
  - Maturity distribution: effective level per assessed/pinned user via the same base + `advance_level` walk `_effective_maturity_map` uses (fetch data in the service, feed the **pure** `advance_level` — the small duplication of fetch lines is the accepted price of "services never call services"; the rules themselves live in pure functions).
  - `active_week` counts learners with `last_used_by_user` value within `ACTIVE_DAYS` of now.

- [ ] **Step 1: Write the failing test** — `test_admin_dashboard.py`, one rich seeded scenario (single test class, shared `_seed` helper): project A with (u1) invited-only 10 days ago, (u2) activated + no survey + activated ≥7 days, (u3) assessed + 1of2 lessons done 20 days ago (stalled), (u4) assessed + all lessons of its one assigned track done yesterday (completed_track, active); project B with 1 healthy learner; 1 `status='new'` feedback row in project A. Assertions:
  - unscoped: `tiles == {learners: 5, active_week: <computed>, attention: 3, new_feedback: 1}`; funnels has 2 entries; project A funnel `{invited: 4, activated: 3, assessed: 2, started: 2, completed_track: 1}`; attention list has u1 (`never_activated`), u2 (`not_assessed`), u3 (`stalled`, reason mentions the track name and day count).
  - scoped `?project_id=<B>`: 1 learner, empty attention, 1 funnel.
  - unknown project → 404.
  - Setting `completed_at` 20 days back: update the `LessonProgress` row directly in the test (`row.completed_at = NOW - timedelta(days=20)` + commit) — the factory stamps `now()`.

- [ ] **Step 2: Run to verify 404-failure, then implement** service + schemas + router + DI per the Interfaces block. Router is three lines (validate scope, call `overview`, `DashboardResponse.model_validate`). Authz entry:

```python
("dashboard", "GET", lambda s: "/api/admin/dashboard", lambda s: None, True),
```

- [ ] **Step 3: Full gate, then commit**

```bash
git add backend/src/ backend/tests/
git commit -m "feat(admin): dashboard aggregates endpoint"
```

### Task 11: Phase A checkpoint — migrations to dev DB + regenerate the API types ⚠️ APPROVAL GATES

- [ ] **Ask Aaron, then apply migrations to the dev Azure DB:** `cd backend && uv run poe upgrade` (applies `b5c6d7e8f9a0` + `c6d7e8f9a0b1`; prod applies automatically on next deploy via `startup.py`).
- [ ] **Ask Aaron, then regenerate frontend types:** start the dev backend (`uv run poe dev` — its startup runs a real auth-cleanup DELETE against the dev DB, hence the gate), run `cd frontend && npm run gen:api`, stop the backend. Commit `frontend/src/api/schema.d.ts`:

```bash
git add frontend/src/api/schema.d.ts
git commit -m "chore: regenerate API types after admin backend changes"
```

- [ ] **Verify the old panel still works against the new backend** (additive-only claim): `npm run typecheck && npm run lint && npm run build` on the untouched frontend + a quick manual smoke of `/admin` against the local backend (list users, open a user panel, toggle an assignment).

---

## Phase B — Frontend foundation (shell, data layer, kit). The old panel keeps running untouched until Phase D.

**Working principles for all frontend tasks (from the visual contract + code map):**
- Visual contract: `docs/design-prototypes/admin-redesign/option-b.html` + `styles.css` + `common.js`. Open them in a browser next to the implementation; class names below refer to that prototype.
- Styling: new admin styles live in one new global stylesheet `frontend/src/styles/admin.css` (imported by the shell only), defining `--adm-*` aliases that map prototype tokens onto the existing brand tokens from `index.css` (`--adm-red: var(--dlw-dot-red)`, `--adm-red-deep: var(--dlw-primary-red)`, `--adm-red-dark: var(--dlw-sub-red-2)`, `--adm-ink: var(--dlw-black)`, `--adm-surface: var(--dlw-surface)`, `--adm-warm: var(--dlw-warm-grey)`, `--adm-border: var(--dlw-border)`, `--adm-muted: var(--dlw-muted)`, plus the semantic pairs the prototype adds as literals: `--adm-good-bg:#EDFAF4; --adm-good-text:#1D7A52; --adm-warn-bg:#FFF8EC; --adm-warn-text:#B45309; --adm-info-bg:#EEF2FF; --adm-info-text:#4B5CC4; --adm-red-tint:#FFF0EF; --adm-red-border:#FBCFCC`). Copy the prototype's `styles.css` rules for kit components into `admin.css`, swapping raw hex for the tokens. Kit components use `className`s (real CSS, hover states for free) — NOT inline `CSSProperties`; this is the "reskin" half of "middle + reskin". The learner pages and `index.css` are untouched.
- Data layer: TanStack Query for **all** admin data. Query keys: `['admin','users',{project,q,status,page}]`, `['admin','learning',{project}]`, `['admin','defaults',project]`, `['admin','dashboard',project]`, `['admin','feedback',{status,track,project,page}]`, `['admin','companies']`, `['admin','tracks']`, `['admin','components',project]`, `['admin','survey',userId]`. Mutations invalidate the affected keys; matrix toggles and feedback triage use optimistic `onMutate`/`onError` rollback (spec §5).
- Scope: `?project=<id>` query param via `useSearchParams`, wrapped in one `useScope()` hook — the sole source of truth for the global scope switcher.
- Types: extend `frontend/src/types/domain.ts` with aliases for the new schemas (`AdminFeedbackItem`, `AdminFeedbackList`, `Dashboard`, `DefaultsOut`, etc.). Pages never index `components['schemas']` directly.

### Task 12: Query client + admin shell (routes, sidebar, topbar, scope switcher)

**Files:**
- Modify: `frontend/package.json` (`npm install @tanstack/react-query@^5`)
- Create: `frontend/src/styles/admin.css` (tokens + shell layout; extend per-component in later tasks)
- Create: `frontend/src/pages/admin2/AdminShell.tsx` (layout route: topbar + sidebar + `<Outlet/>`)
- Create: `frontend/src/pages/admin2/useScope.ts`
- Create: `frontend/src/pages/admin2/ScopeSwitcher.tsx`
- Create: `frontend/src/pages/admin2/nav.ts` (section registry: key/label/icon/path)
- Modify: `frontend/src/App.tsx` (nested `/admin/*` routes **behind the same guard ternary**, old `Admin.tsx` stays reachable at `/admin-old` until cutover)
- Create: `frontend/src/pages/admin2/Placeholder.tsx` (temporary per-section stub so the shell is walkable)

**Why `admin2/`:** the new panel is built in a parallel directory so the old one stays deployable; Phase D renames nothing — it deletes the old files and flips the routes (the directory name is internal; the URL stays `/admin`).

**Interfaces:**
- Produces:
  - `useScope() -> { projectId: string | null, setProject(id: string | null): void }` (reads/writes `?project=`, preserved across navigation by writing through `useSearchParams`).
  - `AdminShell` — renders: topbar (brand + "Admin" tag, `<ScopeSwitcher/>`, "Open learner app" link → `/`, user chip reusing the AppNav dropdown pattern) + fixed 216px sidebar from `nav.ts` (`NavLink` per section, active state, feedback badge count added in Task 17) + scrollable `<main><div className="adm-container"><Outlet/></div></main>`. One `QueryClientProvider` wraps the shell (`staleTime: 30_000`, `retry: 1`).
  - Routes in `App.tsx` (inside the existing `<Routes>`; guard copied verbatim from the current `/admin` route):

```tsx
<Route path="/admin" element={!session ? <Navigate to="/login"/> : role !== 'admin' ? <Navigate to="/"/> : <AdminShell/>}>
  <Route index element={<DashboardPage/>} />
  <Route path="people" element={<PeoplePage/>} />
  <Route path="people/:userId" element={<UserDetailPage/>} />
  <Route path="assignments" element={<AssignmentsPage/>} />
  <Route path="feedback" element={<FeedbackPage/>} />
  <Route path="projects" element={<ProjectsPage/>} />
  <Route path="templates" element={<TemplatesPage/>} />
  <Route path="setup" element={<SetupPage/>} />
</Route>
<Route path="/admin-old" element={/* same guard */ <Admin/>} />
```

  (During Phase B/C the eight elements are `<Placeholder/>` swapped out one task at a time.)
- Steps: install dep → write `useScope` + failing-then-passing smoke via typecheck → shell + CSS (copy `.topbar/.shell/.sidebar/.scope-*` rules from the prototype into `admin.css` with tokens) → routes → gate (`npm run typecheck && npm run lint && npm run build`) → manual walk: every sidebar item navigates, scope pill sets/clears `?project=`, deep-link + back-button work, `/admin-old` still renders the old panel.

- [ ] **Step 1:** `cd frontend && npm install @tanstack/react-query@^5` (verify react 18 peer OK)
- [ ] **Step 2:** implement `useScope.ts` + `nav.ts` + `ScopeSwitcher.tsx` + `AdminShell.tsx` + `admin.css` + `Placeholder.tsx` + route changes
- [ ] **Step 3:** gate + manual walk (list above)
- [ ] **Step 4:** Commit

```bash
git add frontend/
git commit -m "feat(admin-ui): routed admin shell with sidebar, scope switcher, react-query"
```

### Task 13: Component kit

**Files:**
- Create: `frontend/src/pages/admin2/kit/{Tile,Card,Chip,Table,Toolbar,ProgressBar,BulkBar,Modal,ConfirmButton,EmptyState,ErrorState,Spinner}.tsx` (one file per component, named exports)
- Create: `frontend/src/pages/admin2/kit/index.ts` (barrel)
- Modify: `frontend/src/styles/admin.css` (kit rules copied/tokenized from the prototype)
- Create: `frontend/src/pages/admin2/api.ts` — thin typed hooks over `client` + react-query (`useAdminUsers(params)`, `useLearning(project)`, `useCompanies()`, `useTracks()`, `useDashboard(project)`, `useFeedback(params)`, `useDefaults(project)`, `useComponents(project)`, `useSurvey(userId)` + the mutation hooks each screen task lists)

**Interfaces (exact props consumed by Phase C):**

```tsx
Tile({ label, value, alert?: boolean })                      // dashboard stat tile; alert → red value
Card({ title?, actions?: ReactNode, children, className? })
Chip({ children, tone?: 'default'|'good'|'warn'|'info'|'red', dot?: string /* css color */ })
Table<T>({ columns: { key, header, width?, render: (row: T) => ReactNode }[], rows: T[],
          rowKey: (r: T) => string, onRowClick?, selectable?: boolean,
          selected?: Set<string>, onSelect?: (next: Set<string>) => void, empty?: ReactNode })
Toolbar({ children })                                        // search + filter pills row
ProgressBar({ completed, total })                            // text label + bar, no color-only encoding
BulkBar({ count, children, onClear })                        // sticky bottom bar, hidden when count===0
Modal({ title, onClose, children, footer? })
ConfirmButton({ label, confirmLabel, onConfirm, busy? })     // two-step in-place confirm — never window.confirm
EmptyState({ title, hint? }) / ErrorState({ message, onRetry? }) / Spinner()
```

- All loading/error/empty rendering in Phase C goes through `Spinner`/`ErrorState`/`EmptyState` — **no literal loading strings** (spec §5).
- Reuse, don't rebuild: `LevelBadge`/`BandBadge`/`RungPill` from `adminHelpers.tsx` keep working inside the new screens (token-level restyle only if needed).
- Steps: build components against the prototype's CSS (copy rule blocks per component into `admin.css`); `api.ts` hooks typed via `types/domain.ts` aliases (add the new aliases now); gate; commit `feat(admin-ui): admin component kit + typed query hooks`.

- [ ] Implement kit components + `admin.css` rules
- [ ] Implement `api.ts` query/mutation hooks + `types/domain.ts` aliases
- [ ] Gate (`typecheck/lint/build`) then commit

---

## Phase C — Screens (one task per sidebar section; each replaces its `<Placeholder/>`)

Every screen task follows the same loop: build against the prototype screen → wire the Task 13 hooks → gate (`npm run typecheck && npm run lint && npm run build`) → manual browser check against the local backend → commit. Behavior contracts below are from spec §3; visuals from `option-b.html`.

### Task 14: Dashboard (`/admin`)

**Files:** Create `frontend/src/pages/admin2/DashboardPage.tsx`; modify `admin.css` (tiles/funnel/attention rules from prototype), `App.tsx` (swap placeholder).

**Contract (spec §3.1):**
- `useDashboard(scope.projectId)` → single call.
- Four `<Tile>`s: Learners · Active this week · Need attention (`alert` when > 0) · New feedback.
- Needs-attention `<Card>`: one row per `attention[]` item — name, `Chip` with company (unscoped only), the `reason` verbatim from the API, actions **Remind** (`useSendReminder()` mutation → `POST /users/{id}/reminder`, button shows sent/failed feedback via the returned `email_status`) and **View** (→ `/admin/people/{user_id}?project=…`). Empty → `EmptyState("All learners on track")`.
- One funnel `<Card>` per `funnels[]` entry (company-first title `Company · Project`): five steps Invited → Activated → Assessed → Learning started → Completed a track, each step = count + label + step-conversion % as **text** (single-hue ramp per the prototype; no color-only encoding).
- Maturity distribution: one labeled bar row per level (`LEVELS` from `lib/levels.ts` for names/colors), value as text — **never a stacked bar** (spec §3.1).
- Loading/error via `Spinner`/`ErrorState`.

- [ ] Implement, gate, manual check (scoped + unscoped), commit `feat(admin-ui): dashboard screen`

### Task 15: People (`/admin/people`)

**Files:** Create `frontend/src/pages/admin2/PeoplePage.tsx`, `frontend/src/pages/admin2/InviteModal.tsx`; modify `admin.css`, `App.tsx`.

**Contract (spec §3.2):**
- `useAdminUsers({ project: scope.projectId, q, status, page })` — server-driven: `q` debounced 300 ms, status pills All/Active/Invited/Needs attention map to `status=`&nbsp;`undefined|'active'|'invited'|'attention'`, pager sends `limit=50&offset=` and renders from `total`.
- `<Table>` columns: [select] · Participant (avatar initials, name, email) · Project (company `Chip`, **only when unscoped**) · Status (`Chip` tone good/default/warn from `activated`/`needs_attention`) · Maturity (`LevelBadge` on `effective_maturity`, 📌 when `maturity_override`) · Progress (`ProgressBar completed={completed_lesson_count} total={assigned_lesson_count}`) · Last active (`formatDate(last_active_at)`) · Role chip. Row click → `/admin/people/{id}` (keep `?project=`).
- `<BulkBar>` on selection: **Assign content** (modal: pick tracks OR modules OR lessons from `useTracks()`/`useLearning()`, then ONE `useBulkAssign()` → `POST /api/admin/assignments/bulk`) · **Send reminder** (client-side fan-out over `useSendReminder` per selected id — spec §4.2 allows this at our scale) · **Change role** (fan-out over the existing `PATCH /users/{id}`).
- **Invite modal** (button disabled with hint until scoped): first/last/email + the two submit paths (`send_email: true` / `false` → link shown with copy button, reusing the `LinkResponse.email_status` handling conventions from `ProjectDetailView`), plus a banner naming the project's default tracks (`useDefaults(scope.projectId)` → "Will automatically receive: Track A, Track B" or "No project defaults configured"). **Bulk invite (CSV)** button mounts the existing `BulkInviteModal` unchanged (`projectId`/`projectName`/`onClose`/`onCommitted` props; `onCommitted` invalidates `['admin','users']`).
- Mutations invalidate `['admin','users']` (+ `['admin','learning']` for assigns).

- [ ] Implement, gate, manual check (search, pills, paging, bulk assign 2 users × 1 track, invite with defaults banner), commit `feat(admin-ui): people screen with bulk bar and invite modal`

### Task 16: User detail (`/admin/people/:userId`)

**Files:** Create `frontend/src/pages/admin2/UserDetailPage.tsx`; modify `admin.css`, `App.tsx`.

**Contract (spec §3.3) — full-width page replacing the inline `ParticipantDetail` (which itself replaced the UserPanel slide-over via the participant-inline-detail feature, merged 2026-07-24). Reuse `ParticipantDetail`'s internals where they fit — spec §5 anticipated exactly this:**
- Data: the user row from `useAdminUsers` cache (or refetch), `useSurvey(userId)` → `GET /api/admin/surveys/{user_id}`.
- Header: avatar initials, name, email, company `Chip`, status `Chip`, last active; breadcrumb "People / {name}"; shortcut button → `/admin/assignments?project=…`.
- **Assessment card:** completed → render the existing `<SurveyResults survey={…}/>` unchanged (it is pure-presentational). Not assessed → the *why* (from `activated`/`attention_reason`: "invite not redeemed" vs "activated but not started") + Send-reminder button.
- **Account card:** Role select (user/user+/admin → existing `PATCH /users/{id}`, reuse `roleBadgeColor` conventions); Maturity pin (port the `ParticipantDetail` select verbatim: value `maturity_override ?? ''`, options "From assessment" + `PIN_LEVELS`, effective level via `LevelBadge`, → `PUT /users/{id}/maturity`); Send reset link (`POST /users/{id}/reset-link` → emailed/failed indicator + copyable link fallback — port `ResetLinkEntry` handling); Remove participant (`ConfirmButton` two-step → `DELETE /users/{id}`, then navigate back to People).
- **Learning progress card:** per assigned track (`assigned_track_ids` × `useTracks()`): track name + `ProgressBar` from the track's module counts in `useLearning` data.
- All mutations invalidate `['admin','users']` (+ `['admin','survey',userId]` where relevant).

- [ ] Implement, gate, manual check (assessed + not-assessed users, pin, reset link, role change; delete a disposable user), commit `feat(admin-ui): user detail page`

### Task 17: Assignments matrix (`/admin/assignments`) — the headline redesign

**Files:** Create `frontend/src/pages/admin2/AssignmentsPage.tsx`, `frontend/src/pages/admin2/ContentTree.tsx`, `frontend/src/pages/admin2/Matrix.tsx`; modify `admin.css` (`.assign-layout/.content-tree/.matrix*` rules from the prototype), `App.tsx`.

**Contract (spec §3.4; prototype `mountMatrix` in `common.js` is the DOM reference):**
- Unscoped → company/project picker cards (reuse the Projects-card pattern; clicking sets scope).
- Scope state: `{level:'tracks'} | {level:'modules', trackId} | {level:'lessons', trackId, moduleId}` in component state; breadcrumb mirrors it.
- `<ContentTree>`: "All tracks" root + per-track items (`resolveTrackColor` dots, `is_introduction` tracks excluded — same `assignableTracks` filter as `ParticipantDetail`), selected track expands its modules as sub-items. Data: `useTracks()` + `useLearning(project)`.
- `<Matrix>` rows: **Project defaults row first** (`useDefaults(project)`; only meaningful at track level — at module/lesson scope render the defaults cells read-only/tinted when the parent track is a default, tooltip "defaults are track-level"), then one row per participant (from `useLearning(project).users`, paged with the Task 9 params when > 50).
- Cell state per user × column, computed from the enriched arrays: explicit = id in `assigned_*_ids` and NOT in `default_*_ids` → `yes` (✓ solid); via default = id in both → `def` (✓ tinted); partial = **derived client-side**: not assigned itself but some (not all) child ids assigned — tracks check their modules, modules their lessons → `part` (◐); else empty. Legend always visible (four swatches + "Click a cell to toggle").
- Toggling:
  - user cell → single-item `PUT /users/{id}/tracks|modules|lessons/{itemId} {assigned: !current}` via `useToggleAssignment()`; **optimistic**: `onMutate` patches the cached `['admin','learning']` arrays (add/remove the id + cascade locally: toggling a track patches its module/lesson ids too — mirror the server cascade so the UI matches what refetch will return), `onError` rolls back, `onSettled` invalidates.
  - defaults cell (track level) → `PUT /api/admin/projects/{id}/defaults` with the updated full list via `useSetDefaults()`; after success show a one-line toast/hint "Applies to new participants — Apply to existing…" with an **Apply now** action → `POST …/defaults/apply` (`useApplyDefaults()`), then invalidate `['admin','learning']`.
- Column sets: tracks level → all non-intro tracks; modules level → selected track's modules; lessons level → selected module's lessons (from `useLearning` `modules`/`lessons` arrays, sorted by `sort_order`).

- [ ] Implement `ContentTree` → `Matrix` (static render first) → cell toggles + optimistic cache math → defaults row → gate → manual check (assign/unassign at all 3 levels, partial glyphs, defaults toggle + apply, legend, unscoped picker) → commit `feat(admin-ui): assignments matrix with project-defaults row`

### Task 18: Feedback queue (`/admin/feedback`)

**Files:** Create `frontend/src/pages/admin2/FeedbackPage.tsx`; modify `admin.css`, `App.tsx`, `AdminShell.tsx` (sidebar badge).

**Contract (spec §3.5 — no type chip, no AI box):**
- `useFeedback({ status, track, project: scope.projectId, page })`. Status pills New (count from `total` of a `status=new` query) · Accepted · Dismissed · All; separate Filter row: track dropdown (`useTracks()`) + item count.
- Card per item: avatar+name (company beneath when unscoped) · `formatDate(created_at)` · location chips **Track:** (with level dot via `resolveTrackColor`; click filters the queue) / **Module:** / **Lesson:** · *open lesson* link → `/learning/lesson/{lesson_id}` (new tab) · quoted message · Dismiss / Accept buttons (`usePatchFeedback()` → `PATCH {status}`; **optimistic** status flip with rollback). Accepted/dismissed cards render dimmed with a status `Chip` + "Mark as new" undo action.
- Sidebar "Feedback" item shows the new-count badge (`useFeedback({status:'new', limit:1})` → `total`; refreshed by invalidation after any patch).
- Pagination over `total/limit/offset`.

- [ ] Implement, gate, manual check (triage a real row both ways, filters, badge updates), commit `feat(admin-ui): feedback triage queue`

### Task 19: Projects, Email templates, Setup (`/admin/projects`, `/admin/templates`, `/admin/setup`)

**Files:** Create `frontend/src/pages/admin2/{ProjectsPage,TemplatesPage,SetupPage}.tsx`; modify `admin.css`, `App.tsx`.

**Contract (spec §3.6):**
- **Projects:** one `<Card>` per project from `useCompanies()` (company-first title). Inside: component-access toggles (port the `COMPONENT_KEYS` table from `ProjectDetailView` — `useComponents(projectId)` + `PUT …/components/{component}`, same visible/unlocked toggle semantics) + three buttons People / Assignments / Email templates that navigate **pre-scoped** (`?project={id}`).
- **Email templates:** requires scope (unscoped → picker, like Assignments). Renders the existing `<EmailTemplatesCard projectId={scope.projectId}/>` **unchanged** (it owns its own data; token-level restyle only — wrap in a kit `<Card>` and neutralize clashing inline styles minimally).
- **Setup:** port `SetupView`'s two forms into kit components (`useCompanies()` + `useCreateCompany()`/`useCreateProject()` mutations invalidating `['admin','companies']`); keep the existing-list rendering.

- [ ] Implement all three, gate, manual check, commit `feat(admin-ui): projects, email templates, setup screens`

---

## Phase D — Cutover (one release, spec §6)

### Task 20: The cutover commit

**Files:**
- Modify: `frontend/src/App.tsx` — delete the `/admin-old` route and the `Admin` import.
- Delete: `frontend/src/pages/Admin.tsx`, `frontend/src/pages/admin/ProjectsView.tsx`, `frontend/src/pages/admin/ProjectDetailView.tsx`, `frontend/src/pages/admin/ParticipantDetail.tsx` (replaced `UserPanel.tsx`, which is already gone from main).
- Modify: `frontend/src/pages/admin/adminStyles.ts` — remove the style keys only the deleted files used (nav*, panel*, projectView*, etc.); **keep** `LEVEL_STYLE`/`BAND_STYLE`/`RUNG_*` and whatever `s.*` keys the reused components (`SurveyResults`, `BulkInviteModal`, `EmailTemplatesCard`, `SetupView`-ported forms) still reference — let the TypeScript compiler drive the deletion list.
- Move-or-keep: `ResetLinkEntry` type (currently exported from `Admin.tsx`, imported by `BulkInviteModal`) → relocate to `frontend/src/types/domain.ts` first, update imports.

**Steps:**
- [ ] Relocate `ResetLinkEntry`; typecheck.
- [ ] Delete the four files + the `/admin-old` route; run `npm run typecheck` and chase every dangling import until clean (the compiler is the feature-inventory verification — anything still importing the dead files is a missed port).
- [ ] Full gate + `cd backend && uv run poe test` (nothing backend changed, but the cutover claim is "all suites green").
- [ ] Grep sweep: `rg "admin-old|ProjectsView|ProjectDetailView|ParticipantDetail" frontend/src` → zero hits.
- [ ] **ai-chat-foundation collision check:** that plan's final tasks modify `Admin.tsx`/`ProjectDetailView.tsx` (project AI settings UI). If that work landed before this cutover, port the AI-settings card into the new Projects screen (Task 19's card) before deleting; if it hasn't landed, tell Matthias his remaining frontend tasks must target the new panel (`admin2/ProjectsPage.tsx`).
- [ ] Commit:

```bash
# targeted add only — the working tree may hold unrelated untracked files (repo deploy discipline: never blanket-add)
git add frontend/src/App.tsx frontend/src/pages/Admin.tsx frontend/src/pages/admin/ frontend/src/types/domain.ts
git commit -m "feat(admin-ui)!: cutover - new admin panel replaces Admin.tsx shell"
```

### Task 21: Pre-cutover verification checklist (spec §7) + docs

- [ ] **Browser pass against the local dev stack** (backend `uv run poe dev` — ask Aaron first, dev-DB writes; frontend `npm run dev`), executing the five mockup tasks for real: morning check (dashboard scan) · project health (funnel + attention) · bulk assign (People multi-select) · change defaults (matrix defaults row + apply) · triage feedback (accept + dismiss + undo).
- [ ] Plus: user detail assessed AND not-assessed; invite modal shows the defaults banner and both submit paths; deep-link every route + back-button through a full navigation chain; a below-1280px width pass (sidebar + matrix horizontal scroll behavior).
- [ ] Update `CLAUDE.md` (feature index entry + appendix entry for the redesign, note the retired components) and `docs/design/design-frontend.md` if it documents the admin shell.
- [ ] Commit docs: `git commit -m "docs: admin panel redesign feature entry"`.
- [ ] **STOP — Aaron's gates:** push the branch, merge to `main`, and `deploy.ps1` are all explicit approval gates. Deploy per the documented discipline (build from a clean worktree of the pushed commit, never the live working dir).

---

## Self-review notes (spec-coverage check done while writing)

- Spec §2 URL routing → Task 12. §3.1 → Task 14. §3.2 → Task 15. §3.3 → Task 16. §3.4 → Task 17. §3.5 → Task 18. §3.6 → Task 19. §4.1 → Tasks 1–4. §4.2 → Task 5. §4.3 → Task 6. §4.4 → Tasks 8+10. §4.5 → Task 7. §4.6 → Tasks 6+9. §5 → Tasks 12–13. §6 → Task 20. §7 → per-task tests + Task 21. §8 honored (no AI columns anywhere). §9 → Task 0.
- Deliberate decisions surfaced for Aaron's review: `NUDGE_DAYS = 7` for the two non-locked attention rules (Task 8); status-filter pagination happens in the service layer post-enrichment (Task 9, scale-justified); provenance is first-writer-wins under `ON CONFLICT DO NOTHING` (Task 2 — this is what makes *apply* additive-only); defaults PUT accepts an empty list (Task 3); reminder template is fixed, not per-project (Task 7).
- Type-consistency: `assigned_via` kwarg name is identical across repo/service layers; `default_*_ids` naming matches between `AdminUserOut`, `AdminLearningUserOut`, and the matrix's cell math; `EmailStatus` reused (never extended) for reminders.

## Execution

Two options once Aaron approves the plan:
1. **Subagent-Driven** (recommended): fresh subagent per task, review between tasks — use `superpowers:subagent-driven-development`.
2. **Inline**: execute task-by-task in one session with checkpoints — use `superpowers:executing-plans`.
