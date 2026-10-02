# Project-scoped admins (B1) Implementation Plan

> **Status (2026-10-02): all 10 tasks done and merged in PR #152 (`9c2665d`).** The admin-panel
> follow-up (B2, #144) merged in PR #153 (`c930496`). Deviations from this plan, decided with
> Matthias: project admins *do* receive invite/reset links for their own learners (accepted risk,
> `SECURITY.md`); for project-admin callers `GET /api/admin/users` and `/learning` leave out
> power admins and project admins (#153). Deferred follow-ups: #154. Not deployed as of this note — ask the app (`/api/health`), not this file.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a project-admin tier: a `project_admins` table, plus scoped guards on every `/api/admin/*` route. Power admins keep today's powers. Drop `user+`.

**Architecture:**
- **Scope:** one request-scoped `AdminScope` (power admin, or the set of administered project ids) is resolved by a new `AdminScopeService` over `UserRepository` + a new `ProjectAdminRepository`.
- **Guards:** three FastAPI dependencies, `require_power_admin`, `require_project_in_scope` and `require_user_in_scope`, replace `require_admin`.
- **Locks:** a `bypasses_locks` dependency replaces `LOCK_BYPASS_ROLES` and `_ASSESSMENT_EXEMPT_ROLES`.
- **Tests:** the authorization matrix gains two project-admin callers (in scope / out of scope), so a forgotten guard fails a test.

**Tech Stack:** FastAPI, SQLAlchemy 2 async, Alembic, pytest (asyncio auto), React + TS (minimal).

**Spec:** `docs/superpowers/specs/2026-10-01-project-scoped-admin-design.md`

## Global Constraints

- **One-database rule:** never run `alembic upgrade` locally and never `uv run poe dev`. The migration is applied only by the Deploy migrate job. Tests run against `ai-enablement-hub-test` via `uv run poe test`.
- **Layering:** routers → services → repositories; services never call other services (see `python-be-architecture.md`).
- **Role values after this change:** exactly `'admin'` and `'user'`. `'admin'` means power admin.
- **Out-of-scope** project or user → **404**. A power-only route called by a project admin → **403** `"Admin role required"`.
- **Self/last-admin guards** → **409** (`ConflictError`).
- **AI surface toggles** (`require_ai_surface`, `require_interview_surface`) stay a hard gate for everyone. **`hidden` components** stay hidden for everyone.
- **Logs** carry UUIDs only, never emails.
- **Branch:** `feat/project-scoped-admin` from a fresh `origin/main`. Aaron ships in `interview.py` / `core/dependencies/interview.py`: `git fetch` and merge `origin/main` before each task that touches them.
- **Checks before every commit that touches backend code:**
  `cd backend && uv run poe format-check && uv run poe lint-src && uv run poe ty-src`.
  The full `uv run poe test` runs at the end of each task.

## Review Focus

1. **A project admin who also administers project B tries a learner of project B through every per-user route** → 404. Owned by Task 5's matrix (the `pa_other` caller).
2. **A bulk request that mixes one out-of-scope user id with in-scope ids** (`POST /assignments/bulk`, `GET /surveys?user_ids=`) → 404, with nothing written. Task 5 has an explicit test.
3. **A project admin invites into a project they don't administer**, or tries to promote someone with `PATCH /users/{id}` → 404 / 403. Task 5.
4. **The last power admin demotes or deletes themselves** → 409, and the row is unchanged. Task 6.
5. **A project admin whose own `users.project_id` is project A but who administers only B** → no lock bypass anywhere (lesson gate, component lock, assessment gate). Task 7.

---

### Task 1: `project_admins` table, migration, drop `user+` from the model

**Files:**
- Create: `backend/src/db/models/project_admin.py`
- Modify: `backend/src/db/models/__init__.py` (export `ProjectAdmin`)
- Modify: `backend/src/db/models/user.py` (role CHECK)
- Create: `backend/alembic/versions/a9b0c1d2e3f4_project_admins.py`
- Modify: `backend/tests/fixtures/factories.py` (add `make_project_admin`)
- Modify: `backend/tests/integration/test_models/test_fk_indexes.py` (add `project_admins.project_id`, `project_admins.granted_by` to its parametrize list, if the list is explicit)
- Test: `backend/tests/unit/test_project_admin_model.py`

**Interfaces:**
- Produces: `ProjectAdmin(user_id, project_id, granted_by, granted_at)`, and `make_project_admin(session, user, project, granted_by=None) -> ProjectAdmin`.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/unit/test_project_admin_model.py
"""project_admins exists; the users.role CHECK no longer allows 'user+'."""

from __future__ import annotations

from src.db.base import Base
from src.db.models import ProjectAdmin, User


def test_project_admins_table_shape() -> None:
    table = Base.metadata.tables["project_admins"]
    assert [c.name for c in table.primary_key.columns] == ["user_id", "project_id"]
    fks = {fk.parent.name: (fk.column.table.name, fk.ondelete) for fk in table.foreign_keys}
    assert fks == {
        "user_id": ("users", "CASCADE"),
        "project_id": ("projects", "CASCADE"),
        "granted_by": ("users", "SET NULL"),
    }
    assert ProjectAdmin.__tablename__ == "project_admins"


def test_role_check_is_admin_or_user_only() -> None:
    checks = [c for c in User.__table__.constraints if getattr(c, "name", None) == "role"]
    assert len(checks) == 1
    assert str(checks[0].sqltext) == "role IN ('admin', 'user')"
```

- [ ] **Step 2: Run it to verify it fails**

Run: `cd backend && uv run pytest tests/unit/test_project_admin_model.py -v`
Expected: FAIL. `ImportError: cannot import name 'ProjectAdmin'`.

- [ ] **Step 3: Implement the model, the CHECK change, the export and the factory**

```python
# backend/src/db/models/project_admin.py
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base

__all__ = ["ProjectAdmin"]


class ProjectAdmin(Base):
    """A user's admin rights over one project (spec 2026-10-01-project-scoped-admin).

    Users with role 'admin' are power admins and need no rows here; a 'user' with
    one or more rows is a project admin for exactly those projects."""

    __tablename__ = "project_admins"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        primary_key=True,
        index=True,
    )
    granted_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    granted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
```

- In `backend/src/db/models/user.py`, replace `CheckConstraint("role IN ('admin', 'user+', 'user')", name="role")` with `CheckConstraint("role IN ('admin', 'user')", name="role")`.
- In `backend/src/db/models/__init__.py`, add `from src.db.models.project_admin import ProjectAdmin` and put `"ProjectAdmin"` in `__all__` (alphabetical, after `"Project"`).
- In `backend/tests/fixtures/factories.py`, add the factory below (import `ProjectAdmin` alongside the existing model imports):

```python
async def make_project_admin(
    session: AsyncSession, user: User, project: Project, granted_by: User | None = None
) -> ProjectAdmin:
    """Grant `user` admin rights over `project` (a project admin, not a power admin)."""
    return await _persist(
        session,
        ProjectAdmin(
            user_id=user.id,
            project_id=project.id,
            granted_by=granted_by.id if granted_by is not None else None,
        ),
    )
```

- [ ] **Step 4: Write the migration (hand-written: autogenerate doesn't diff CHECK text)**

```python
# backend/alembic/versions/a9b0c1d2e3f4_project_admins.py
"""project admins; drop the "user+" role

Adds project_admins (user_id, project_id) — a 'user' with rows here administers
exactly those projects; role 'admin' stays the (power) admin. "user+" is dropped:
its rows become 'user' and the role CHECK narrows to ('admin', 'user').
Spec: docs/superpowers/specs/2026-10-01-project-scoped-admin-design.md.

Downgrade drops the table and widens the CHECK again; former user+ accounts are
not restored (accepted in the spec — the role only bypassed locks).

Revision ID: a9b0c1d2e3f4
Revises: e5f6a7b8c9d0
Create Date: 2026-10-01

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "a9b0c1d2e3f4"
down_revision: str | None = "e5f6a7b8c9d0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "project_admins",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("granted_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "granted_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_project_admins_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["project_id"], ["projects.id"], name=op.f("fk_project_admins_project_id_projects"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["granted_by"], ["users.id"], name=op.f("fk_project_admins_granted_by_users"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("user_id", "project_id", name=op.f("pk_project_admins")),
    )
    op.create_index(op.f("ix_project_admins_project_id"), "project_admins", ["project_id"])
    op.create_index(op.f("ix_project_admins_granted_by"), "project_admins", ["granted_by"])

    op.execute("UPDATE users SET role = 'user' WHERE role = 'user+'")
    op.drop_constraint(op.f("ck_users_role"), "users", type_="check")
    op.create_check_constraint(op.f("ck_users_role"), "users", "role IN ('admin', 'user')")


def downgrade() -> None:
    op.drop_constraint(op.f("ck_users_role"), "users", type_="check")
    op.create_check_constraint(
        op.f("ck_users_role"), "users", "role IN ('admin', 'user+', 'user')"
    )
    op.drop_index(op.f("ix_project_admins_granted_by"), table_name="project_admins")
    op.drop_index(op.f("ix_project_admins_project_id"), table_name="project_admins")
    op.drop_table("project_admins")
```

Before writing the constraint and index names, check them against the naming convention in `backend/src/db/base.py` (`MetaData(naming_convention=...)`) and against an existing migration such as `a1b2c3d4e5f6_fk_indexes.py`. CI's `alembic check` fails on any mismatch with the models.

- [ ] **Step 5: Run the tests to verify they pass**

Run: `cd backend && uv run pytest tests/unit/test_project_admin_model.py tests/integration/test_models -v`
Expected: PASS. If `test_fk_indexes.py` keeps an explicit list of FK columns, it now includes the two new ones and they pass, because the model declares `index=True`.

- [ ] **Step 6: Commit**

```bash
git add backend/src/db/models backend/alembic/versions/a9b0c1d2e3f4_project_admins.py backend/tests
git commit -m "feat(db): project_admins table, drop the user+ role (B1, #93)"
```

---

### Task 2: Repositories: project-admin rows and the user-side helpers

**Files:**
- Create: `backend/src/repositories/project_admin_repository.py`
- Modify: `backend/src/repositories/base.py` (add `AbstractProjectAdminRepository`, plus the new abstract methods on `AbstractUserRepository`)
- Modify: `backend/src/repositories/user_repository.py`
- Test: `backend/tests/integration/test_repositories/test_project_admin_repository.py`

**Interfaces:**
- Produces, on `ProjectAdminRepository(session)`:
  - `project_ids_for(user_id) -> frozenset[UUID]`
  - `is_project_admin(user_id) -> bool`
  - `list_for_project(project_id) -> list[tuple[User, datetime]]`
  - `grant(user_id, project_id, granted_by) -> None` (idempotent)
  - `revoke(user_id, project_id) -> bool` (True if a row was deleted)
  - `admin_ids_for_project(project_id) -> set[UUID]`
- Produces, on `UserRepository`:
  - `count_power_admins() -> int`
  - `project_ids_of(user_ids) -> dict[UUID, UUID | None]` (only the ids that exist are returned)

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/integration/test_repositories/test_project_admin_repository.py
from __future__ import annotations

from typing import TYPE_CHECKING

from src.repositories.project_admin_repository import ProjectAdminRepository
from src.repositories.user_repository import UserRepository
from tests.fixtures.factories import (
    create_company,
    create_project,
    create_user,
    make_project_admin,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


async def test_grant_list_revoke_roundtrip(db_session: AsyncSession) -> None:
    company = await create_company(db_session, "PA Co")
    a = await create_project(db_session, company, "A")
    b = await create_project(db_session, company, "B")
    power = await create_user(db_session, email="pa-power@example.com", role="admin")
    coach = await create_user(db_session, email="pa-coach@example.com", project_id=a.id)
    repo = ProjectAdminRepository(db_session)

    assert await repo.project_ids_for(coach.id) == frozenset()
    assert not await repo.is_project_admin(coach.id)

    await repo.grant(coach.id, a.id, power.id)
    await repo.grant(coach.id, a.id, power.id)  # idempotent
    await repo.grant(coach.id, b.id, power.id)
    assert await repo.project_ids_for(coach.id) == frozenset({a.id, b.id})
    assert await repo.is_project_admin(coach.id)
    assert await repo.admin_ids_for_project(a.id) == {coach.id}
    listed = await repo.list_for_project(a.id)
    assert [u.id for u, _ in listed] == [coach.id]

    assert await repo.revoke(coach.id, a.id) is True
    assert await repo.revoke(coach.id, a.id) is False
    assert await repo.project_ids_for(coach.id) == frozenset({b.id})


async def test_user_repo_helpers(db_session: AsyncSession) -> None:
    company = await create_company(db_session, "PA Co 2")
    a = await create_project(db_session, company, "A2")
    before = await UserRepository(db_session).count_power_admins()
    await create_user(db_session, email="pa-power2@example.com", role="admin")
    u1 = await create_user(db_session, email="pa-u1@example.com", project_id=a.id)
    u2 = await create_user(db_session, email="pa-u2@example.com")
    repo = UserRepository(db_session)
    assert await repo.count_power_admins() == before + 1
    import uuid

    missing = uuid.uuid4()
    assert await repo.project_ids_of([u1.id, u2.id, missing]) == {u1.id: a.id, u2.id: None}


async def test_factory_rows_are_visible(db_session: AsyncSession) -> None:
    company = await create_company(db_session, "PA Co 3")
    a = await create_project(db_session, company, "A3")
    coach = await create_user(db_session, email="pa-coach3@example.com")
    await make_project_admin(db_session, coach, a)
    assert await ProjectAdminRepository(db_session).project_ids_for(coach.id) == frozenset({a.id})
```

- [ ] **Step 2: Run it to verify it fails**

Run: `cd backend && uv run pytest tests/integration/test_repositories/test_project_admin_repository.py -v`
Expected: FAIL. `ModuleNotFoundError: src.repositories.project_admin_repository`.

- [ ] **Step 3: Implement**

Add the abstract class to `backend/src/repositories/base.py`, following the shape of the existing ABCs (constructor takes the `AsyncSession`; every method is `@abstractmethod async def ...: ...`, with exactly the signatures from **Interfaces** above). On `AbstractUserRepository`, add the abstract methods `count_power_admins` and `project_ids_of`.

```python
# backend/src/repositories/project_admin_repository.py
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert

from src.db.models import ProjectAdmin, User
from src.repositories.base import AbstractProjectAdminRepository

__all__ = ["ProjectAdminRepository"]


class ProjectAdminRepository(AbstractProjectAdminRepository):
    async def project_ids_for(self, user_id: uuid.UUID) -> frozenset[uuid.UUID]:
        result = await self._session.execute(
            select(ProjectAdmin.project_id).where(ProjectAdmin.user_id == user_id)
        )
        return frozenset(result.scalars().all())

    async def is_project_admin(self, user_id: uuid.UUID) -> bool:
        result = await self._session.execute(
            select(ProjectAdmin.user_id).where(ProjectAdmin.user_id == user_id).limit(1)
        )
        return result.first() is not None

    async def admin_ids_for_project(self, project_id: uuid.UUID) -> set[uuid.UUID]:
        result = await self._session.execute(
            select(ProjectAdmin.user_id).where(ProjectAdmin.project_id == project_id)
        )
        return set(result.scalars().all())

    async def list_for_project(self, project_id: uuid.UUID) -> list[tuple[User, datetime]]:
        result = await self._session.execute(
            select(User, ProjectAdmin.granted_at)
            .join(ProjectAdmin, ProjectAdmin.user_id == User.id)
            .where(ProjectAdmin.project_id == project_id)
            .order_by(User.last_name, User.first_name)
        )
        return [(user, granted_at) for user, granted_at in result.all()]

    async def grant(
        self, user_id: uuid.UUID, project_id: uuid.UUID, granted_by: uuid.UUID | None
    ) -> None:
        await self._session.execute(
            insert(ProjectAdmin)
            .values(user_id=user_id, project_id=project_id, granted_by=granted_by)
            .on_conflict_do_nothing(index_elements=["user_id", "project_id"])
        )
        await self._session.commit()

    async def revoke(self, user_id: uuid.UUID, project_id: uuid.UUID) -> bool:
        result = await self._session.execute(
            delete(ProjectAdmin).where(
                ProjectAdmin.user_id == user_id, ProjectAdmin.project_id == project_id
            )
        )
        await self._session.commit()
        return (result.rowcount or 0) > 0
```

Append to `UserRepository` (`func` and `select` are already imported there):

```python
    async def count_power_admins(self) -> int:
        result = await self._session.execute(
            select(func.count()).select_from(User).where(User.role == "admin")
        )
        return int(result.scalar_one())

    async def project_ids_of(
        self, user_ids: list[uuid.UUID]
    ) -> dict[uuid.UUID, uuid.UUID | None]:
        if not user_ids:
            return {}
        result = await self._session.execute(
            select(User.id, User.project_id).where(User.id.in_(user_ids))
        )
        return {user_id: project_id for user_id, project_id in result.all()}
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd backend && uv run pytest tests/integration/test_repositories/test_project_admin_repository.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/src/repositories backend/tests/integration/test_repositories/test_project_admin_repository.py
git commit -m "feat(repo): project-admin repository and user scope helpers (B1, #93)"
```

---

### Task 3: `AdminScope`, its service, and the guard dependencies

**Files:**
- Create: `backend/src/services/admin_scope_service.py`
- Create: `backend/src/core/dependencies/admin_scope.py`
- Modify: `backend/src/core/dependencies/domain.py` (`get_project_admin_repository`, `get_admin_scope_service`)
- Modify: `backend/src/core/dependencies/auth.py`: delete `require_admin` and remove it from `__all__`. Every caller moves in Tasks 4–5; until then they import `require_power_admin` from the new module. Do the mechanical swap **in this task**: `grep -rln "require_admin" backend/src` and replace each import and usage with `require_power_admin` from `src.core.dependencies.admin_scope`. Behaviour is identical (power admin = role `admin`).
- Test: `backend/tests/unit/test_admin_scope.py`

**Interfaces:**
- Produces in `src/services/admin_scope_service.py`:

```python
@dataclass(frozen=True)
class AdminScope:
    user: User
    is_power: bool
    project_ids: frozenset[uuid.UUID]
    def covers(self, project_id: uuid.UUID | None) -> bool: ...
    def resolve_list_project(self, project_id: uuid.UUID | None) -> uuid.UUID | None: ...

class AdminScopeService:
    def __init__(self, users: AbstractUserRepository, admins: AbstractProjectAdminRepository) -> None
    async def scope_for(self, user: User) -> AdminScope | None          # None = not an admin
    async def ensure_user_in_scope(self, scope: AdminScope, user_id: uuid.UUID) -> User
    async def ensure_users_in_scope(self, scope: AdminScope, user_ids: list[uuid.UUID]) -> None
    async def bypasses_locks(self, user: User) -> bool
```

- Produces in `src/core/dependencies/admin_scope.py`:
  - `get_admin_scope(user) -> AdminScope` (403 when not an admin)
  - `require_power_admin(user) -> User`
  - `require_project_in_scope(project_id: UUID, scope) -> AdminScope`
  - `require_user_in_scope(user_id: UUID, scope, service) -> User` (returns the **target** user)
  - `get_bypasses_locks(user, service) -> bool`
  - Aliases: `AdminScopeDep`, `PowerAdminDep`, `BypassesLocksDep`

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/unit/test_admin_scope.py
from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from src.services.admin_scope_service import AdminScope, AdminScopeService
from src.services.exceptions import InvalidRequestError, NotFoundError

A, B = uuid.uuid4(), uuid.uuid4()


def _user(role: str = "user", project_id: uuid.UUID | None = None) -> SimpleNamespace:
    return SimpleNamespace(id=uuid.uuid4(), role=role, project_id=project_id)


def _service(admin_projects: frozenset[uuid.UUID] = frozenset(), targets=None):
    users = AsyncMock()
    admins = AsyncMock()
    admins.project_ids_for.return_value = admin_projects
    admins.is_project_admin.return_value = False
    targets = targets or {}
    users.get_by_id.side_effect = lambda uid: targets.get(uid)
    users.project_ids_of.side_effect = lambda ids: {
        i: targets[i].project_id for i in ids if i in targets
    }
    return AdminScopeService(users, admins), users, admins


def test_covers_and_resolve() -> None:
    power = AdminScope(user=_user("admin"), is_power=True, project_ids=frozenset())
    pa = AdminScope(user=_user(), is_power=False, project_ids=frozenset({A}))
    multi = AdminScope(user=_user(), is_power=False, project_ids=frozenset({A, B}))
    assert power.covers(B) and power.covers(None)
    assert pa.covers(A) and not pa.covers(B) and not pa.covers(None)
    assert power.resolve_list_project(None) is None
    assert pa.resolve_list_project(None) == A
    assert pa.resolve_list_project(A) == A
    with pytest.raises(NotFoundError):
        pa.resolve_list_project(B)
    with pytest.raises(InvalidRequestError):
        multi.resolve_list_project(None)


async def test_scope_for() -> None:
    service, _, _ = _service()
    assert (await service.scope_for(_user("admin"))).is_power  # type: ignore[union-attr]
    assert await service.scope_for(_user()) is None
    service, _, _ = _service(frozenset({A}))
    scope = await service.scope_for(_user())
    assert scope is not None and scope.project_ids == frozenset({A}) and not scope.is_power


async def test_ensure_user_in_scope_rules() -> None:
    caller = _user()
    learner_a = _user(project_id=A)
    learner_b = _user(project_id=B)
    power = _user("admin", project_id=A)
    targets = {u.id: u for u in (caller, learner_a, learner_b, power)}
    service, _, admins = _service(targets=targets)
    scope = AdminScope(user=caller, is_power=False, project_ids=frozenset({A}))

    assert await service.ensure_user_in_scope(scope, learner_a.id) is learner_a
    with pytest.raises(NotFoundError):
        await service.ensure_user_in_scope(scope, learner_b.id)
    with pytest.raises(NotFoundError):
        await service.ensure_user_in_scope(scope, uuid.uuid4())
    from src.services.exceptions import AdminTargetForbiddenError

    with pytest.raises(AdminTargetForbiddenError):
        await service.ensure_user_in_scope(scope, power.id)
    caller.project_id = A
    with pytest.raises(AdminTargetForbiddenError):
        await service.ensure_user_in_scope(scope, caller.id)
    admins.is_project_admin.return_value = True
    with pytest.raises(AdminTargetForbiddenError):
        await service.ensure_user_in_scope(scope, learner_a.id)


async def test_power_admin_reaches_anyone_known() -> None:
    learner_b = _user(project_id=B)
    service, _, _ = _service(targets={learner_b.id: learner_b})
    power = AdminScope(user=_user("admin"), is_power=True, project_ids=frozenset())
    assert await service.ensure_user_in_scope(power, learner_b.id) is learner_b
    with pytest.raises(NotFoundError):
        await service.ensure_user_in_scope(power, uuid.uuid4())


async def test_ensure_users_in_scope_all_or_nothing() -> None:
    a1, a2, b1 = _user(project_id=A), _user(project_id=A), _user(project_id=B)
    service, _, _ = _service(targets={u.id: u for u in (a1, a2, b1)})
    scope = AdminScope(user=_user(), is_power=False, project_ids=frozenset({A}))
    await service.ensure_users_in_scope(scope, [a1.id, a2.id])
    with pytest.raises(NotFoundError):
        await service.ensure_users_in_scope(scope, [a1.id, b1.id])
    with pytest.raises(NotFoundError):
        await service.ensure_users_in_scope(scope, [a1.id, uuid.uuid4()])


async def test_bypasses_locks() -> None:
    service, _, _ = _service()
    assert await service.bypasses_locks(_user("admin"))
    assert not await service.bypasses_locks(_user(project_id=A))
    service, _, _ = _service(frozenset({A}))
    assert await service.bypasses_locks(_user(project_id=A))
    assert not await service.bypasses_locks(_user(project_id=B))
    assert not await service.bypasses_locks(_user(project_id=None))
```

- [ ] **Step 2: Run them to verify they fail**

Run: `cd backend && uv run pytest tests/unit/test_admin_scope.py -v`
Expected: FAIL, `ModuleNotFoundError`.

- [ ] **Step 3: Implement**

Add to `backend/src/services/exceptions.py`, and register a 403 handler in `backend/src/main.py` next to `component_locked_handler`. Use the same `_error_response(...)` helper and the `"forbidden"` code that `require_admin`'s `HTTPException(403)` produced, so the error code stays `forbidden`:

```python
class AdminTargetForbiddenError(DomainError):
    """A project admin addressed a power admin, another project admin, or
    themselves through a scoped admin route. → 403"""

    def __init__(self) -> None:
        super().__init__("Project admins can only manage learners")
```

Then the service:

```python
# backend/src/services/admin_scope_service.py
"""Who may administer what (spec 2026-10-01-project-scoped-admin-design.md).

Power admin = role 'admin' (everything). Project admin = role 'user' with
project_admins rows (only those projects). Read from the DB on every request,
like the role, so a revoke takes effect on the next call."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import TYPE_CHECKING

from src.services.exceptions import AdminTargetForbiddenError, InvalidRequestError, NotFoundError

if TYPE_CHECKING:
    from src.db.models import User
    from src.repositories.base import AbstractProjectAdminRepository, AbstractUserRepository

__all__ = ["AdminScope", "AdminScopeService"]


@dataclass(frozen=True)
class AdminScope:
    user: User
    is_power: bool
    project_ids: frozenset[uuid.UUID]

    def covers(self, project_id: uuid.UUID | None) -> bool:
        return self.is_power or (project_id is not None and project_id in self.project_ids)

    def resolve_list_project(self, project_id: uuid.UUID | None) -> uuid.UUID | None:
        """The project a list endpoint should filter on. Power admins: as given
        (None = all). Project admins: must name a covered project, or have exactly one."""
        if self.is_power:
            return project_id
        if project_id is not None:
            if project_id not in self.project_ids:
                raise NotFoundError("Project")
            return project_id
        if len(self.project_ids) == 1:
            return next(iter(self.project_ids))
        raise InvalidRequestError("project_id is required")


class AdminScopeService:
    def __init__(
        self, users: AbstractUserRepository, admins: AbstractProjectAdminRepository
    ) -> None:
        self._users = users
        self._admins = admins

    async def scope_for(self, user: User) -> AdminScope | None:
        if user.role == "admin":
            return AdminScope(user=user, is_power=True, project_ids=frozenset())
        project_ids = await self._admins.project_ids_for(user.id)
        if not project_ids:
            return None
        return AdminScope(user=user, is_power=False, project_ids=project_ids)

    async def ensure_user_in_scope(self, scope: AdminScope, user_id: uuid.UUID) -> User:
        target = await self._users.get_by_id(user_id)
        if target is None or not scope.covers(target.project_id):
            raise NotFoundError("User")
        if not scope.is_power and (
            target.role == "admin"
            or target.id == scope.user.id
            or await self._admins.is_project_admin(target.id)
        ):
            raise AdminTargetForbiddenError
        return target

    async def ensure_users_in_scope(self, scope: AdminScope, user_ids: list[uuid.UUID]) -> None:
        """All-or-nothing: one unknown or out-of-scope id rejects the whole request."""
        if scope.is_power:
            return
        found = await self._users.project_ids_of(user_ids)
        if len(found) != len(set(user_ids)) or not all(scope.covers(p) for p in found.values()):
            raise NotFoundError("User")

    async def bypasses_locks(self, user: User) -> bool:
        if user.role == "admin":
            return True
        if user.project_id is None:
            return False
        return user.project_id in await self._admins.project_ids_for(user.id)
```

The bulk check deliberately skips the "target is an admin" rule. Bulk routes only assign content or read levels, so they don't modify or delete anyone. This is documented in the method's docstring.

Wire it up in `backend/src/core/dependencies/domain.py`:

```python
def get_project_admin_repository(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ProjectAdminRepository:
    return ProjectAdminRepository(session)


def get_admin_scope_service(
    users: Annotated[UserRepository, Depends(get_user_repository)],
    admins: Annotated[ProjectAdminRepository, Depends(get_project_admin_repository)],
) -> AdminScopeService:
    return AdminScopeService(users, admins)
```

Then the dependencies:

```python
# backend/src/core/dependencies/admin_scope.py
"""Admin authorization guards (spec 2026-10-01-project-scoped-admin-design.md).
Every /api/admin/* route depends on exactly one of: require_power_admin,
require_project_in_scope, require_user_in_scope, or AdminScopeDep (lists,
which then call scope.resolve_list_project)."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import Depends, HTTPException, status

from src.core.dependencies.auth import get_current_user
from src.core.dependencies.domain import get_admin_scope_service
from src.db.models import User
from src.services.admin_scope_service import AdminScope, AdminScopeService
from src.services.exceptions import NotFoundError

__all__ = [
    "AdminScopeDep",
    "BypassesLocksDep",
    "PowerAdminDep",
    "get_admin_scope",
    "get_bypasses_locks",
    "require_power_admin",
    "require_project_in_scope",
    "require_user_in_scope",
]

_FORBIDDEN = HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin role required")

AdminScopeServiceDep = Annotated[AdminScopeService, Depends(get_admin_scope_service)]


async def get_admin_scope(
    user: Annotated[User, Depends(get_current_user)], service: AdminScopeServiceDep
) -> AdminScope:
    scope = await service.scope_for(user)
    if scope is None:
        raise _FORBIDDEN
    return scope


AdminScopeDep = Annotated[AdminScope, Depends(get_admin_scope)]


async def require_power_admin(user: Annotated[User, Depends(get_current_user)]) -> User:
    if user.role != "admin":
        raise _FORBIDDEN
    return user


PowerAdminDep = Annotated[User, Depends(require_power_admin)]


async def require_project_in_scope(project_id: uuid.UUID, scope: AdminScopeDep) -> AdminScope:
    """Binds the `{project_id}` path segment. Out of scope → 404 (no probing)."""
    if not scope.covers(project_id):
        raise NotFoundError("Project")
    return scope


async def require_user_in_scope(
    user_id: uuid.UUID, scope: AdminScopeDep, service: AdminScopeServiceDep
) -> User:
    """Binds the `{user_id}` path segment; returns the target user."""
    return await service.ensure_user_in_scope(scope, user_id)


async def get_bypasses_locks(
    user: Annotated[User, Depends(get_current_user)], service: AdminScopeServiceDep
) -> bool:
    return await service.bypasses_locks(user)


BypassesLocksDep = Annotated[bool, Depends(get_bypasses_locks)]
```

`backend/tests/unit/test_dependency_declarations.py` may enforce rules about dependency modules (for example runtime imports of annotation types). Run it, and if it fails, follow its message: it encodes the house rule.

- [ ] **Step 4: Run the tests to verify they pass, plus the full suite (the `require_admin` swap must be behaviour-neutral)**

Run: `cd backend && uv run pytest tests/unit/test_admin_scope.py -v && uv run poe test`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/src backend/tests/unit/test_admin_scope.py
git commit -m "feat(authz): AdminScope service and scoped admin guards (B1, #93)"
```

---

### Task 4: Restructure the authorization matrix, with a completeness test (no behaviour change yet)

**Files:**
- Modify: `backend/tests/integration/test_routers/test_authz.py`

**Interfaces:**
- Consumes: `make_project_admin` (Task 1).
- Produces: `_MATRIX` rows of the form `(name, method, path_of, body_of, access)`, where `access` is `Literal["any", "power", "scoped", "scoped_list"]`. The `Seed` gains `other_project`, `pa_in` (project admin of `seed.project`, whose own `project_id` is `other_project`) and `pa_out` (project admin of `other_project` only).

This task makes the matrix describe the **target** behaviour, with every row as `"power"` for now. The suite stays green, and Task 5 flips rows to `scoped` as it opens routes.

- [ ] **Step 1: Restructure**

- Replace the `admin_only: bool` column with `access`. Every current `True` becomes `"power"` and every `False` becomes `"any"`.
- Extend `Seed` and the `seed` fixture:

```python
    other_project = await create_project(db_session, company, "Matrix Other Project")
    pa_in = await create_user(
        db_session, email="matrix-pa-in@example.com", password="hunter2hunter2",
        project_id=other_project.id,
    )
    await make_project_admin(db_session, pa_in, project, granted_by=admin)
    pa_out = await create_user(
        db_session, email="matrix-pa-out@example.com", password="hunter2hunter2",
        project_id=other_project.id,
    )
    await make_project_admin(db_session, pa_out, other_project, granted_by=admin)
```

- Replace the body of `test_matrix` after the `as_user` block:

```python
    as_admin = await client.request(
        method, path, json=body, headers=auth_headers(seed.admin, test_settings)
    )
    assert as_admin.status_code not in (401, 403, 500), f"admin {method} {path}"

    if access == "any":
        return
    as_pa_in = await client.request(
        method, path, json=body, headers=auth_headers(seed.pa_in, test_settings)
    )
    as_pa_out = await client.request(
        method, path, json=body, headers=auth_headers(seed.pa_out, test_settings)
    )
    if access == "power":
        assert as_pa_in.status_code == 403, f"project admin {method} {path}"
        assert as_pa_out.status_code == 403, f"other project admin {method} {path}"
    elif access == "scoped":
        assert as_pa_in.status_code not in (401, 403, 404, 500), f"pa_in {method} {path}"
        assert as_pa_out.status_code == 404, f"pa_out {method} {path}"
    else:  # scoped_list: both reach it; filtering is asserted in test_admin_scope_routes.py
        assert as_pa_in.status_code not in (401, 403, 500), f"pa_in {method} {path}"
        assert as_pa_out.status_code not in (401, 403, 500), f"pa_out {method} {path}"
```

- The `as_user` branch now tests `access != "any"` instead of `admin_only`.
- Add rows for the endpoints missing today (all `"power"` for now): `GET /api/admin/users/{s.user.id}`, `GET`/`DELETE /api/admin/interviews/{s.user.id}`, `GET /api/admin/prompts`, `GET /api/admin/projects/{s.project.id}/ai` and `PUT .../ai/chatbot` with body `{"enabled": False}`. Bulk invite stays in its multipart class below. It gets a project-admin case in Task 5.
- **Completeness test:** walk `app.routes`. Every `APIRoute` whose path starts with `/api/admin` must match a `_MATRIX` row by `(method, templated path)`, or be in `_MATRIX_EXEMPT`, a dict from route to the reason it's exempt (multipart routes covered by their own classes).

```python
_MATRIX_EXEMPT: dict[tuple[str, str], str] = {
    ("POST", "/api/admin/media"): "multipart — TestMediaUploadAuthz",
    ("POST", "/api/admin/invites/bulk"): "multipart — TestBulkInviteAuthz",
}


def test_every_admin_route_is_in_the_matrix() -> None:
    from fastapi.routing import APIRoute

    covered = {(row[1], row[5]) for row in _MATRIX}  # (method, declared route path)
    missing = [
        (method, route.path)
        for route in app.routes
        if isinstance(route, APIRoute) and route.path.startswith("/api/admin")
        for method in route.methods
        if (method, route.path) not in covered and (method, route.path) not in _MATRIX_EXEMPT
    ]
    assert not missing, f"admin routes missing from _MATRIX: {sorted(missing)}"
```

- **Every `_MATRIX` row gets a sixth element, `route: str`:** the FastAPI route path as declared, for example `"/api/admin/users/{user_id}"`. This is what the completeness test compares against `app.routes`. Non-admin rows carry their route too, which the test ignores. Update the `parametrize` slicing to `spec[1:5]` (method, path_of, body_of, access).

- [ ] **Step 2: Run the matrix**

Run: `cd backend && uv run pytest tests/integration/test_routers/test_authz.py -v`
Expected: PASS. Every admin row is `"power"`, so both project admins get 403 (`get_admin_scope` isn't used yet; `require_power_admin` is). If the completeness test lists missing routes, add those rows (as `"power"`) until it passes; that list is the census.

- [ ] **Step 3: Commit**

```bash
git add backend/tests/integration/test_routers/test_authz.py
git commit -m "test(authz): matrix gains project-admin callers and a completeness check (B1, #93)"
```

---

### Task 5: Open the scoped routes to project admins

**Files:**
- Modify: `backend/src/routers/admin_users.py`, `admin_defaults.py`, `admin_org.py`, `admin_email_templates.py`, `admin_dashboard.py`, `interview.py` (only `admin_router`)
- Modify: `backend/src/services/org_service.py` (`companies_with_projects(project_ids: frozenset[UUID] | None = None)`)
- Modify: `backend/src/schemas/admin_users.py:162` (`RoleUpdateRequest.role: Literal["admin", "user"]`)
- Modify: `backend/tests/integration/test_routers/test_authz.py` (flip rows to `scoped` / `scoped_list`, add the bulk-invite project-admin case)
- Create: `backend/tests/integration/test_routers/test_admin_scope_routes.py`

**Interfaces:**
- Consumes: `AdminScopeDep`, `require_project_in_scope`, `require_user_in_scope`, `AdminScopeService.ensure_users_in_scope` (Task 3).

**The pattern for each router:**
- **Router-level dependency** becomes `Depends(get_admin_scope)` for `admin_users.py`, `admin_defaults.py`, `admin_email_templates.py`, `admin_dashboard.py` and `interview.admin_router`. `admin_org.py` loses its router-level dependency; each route declares its own guard.
- **Per-route:**

| Route | Add |
|---|---|
| every route with `{user_id}` (users/{id}, reset-link, reminder, maturity, DELETE, all six assignment PUTs, surveys/{id}, interviews GET/DELETE) | `dependencies=[Depends(require_user_in_scope)]` |
| `PATCH /users/{user_id}` | `dependencies=[Depends(require_power_admin)]` (stays power) |
| every route with `{project_id}` (defaults ×3, components ×2, ai ×2, email templates ×4) | `dependencies=[Depends(require_project_in_scope)]` |
| `POST /companies`, `POST /projects` | `dependencies=[Depends(require_power_admin)]` |
| `GET /users`, `GET /learning`, `GET /dashboard` | a `scope: AdminScopeDep` param; call the service with `scope.resolve_list_project(project_id)` |
| `GET /companies` | `scope: AdminScopeDep`; `org_service.companies_with_projects(None if scope.is_power else scope.project_ids)` |
| `POST /invites` | `scope: AdminScopeDep`; `if not scope.covers(body.project_id): raise NotFoundError("Project")` before the rate-limit check |
| `POST /invites/bulk` | replace `admin: Annotated[User, Depends(require_admin)]` with `scope: AdminScopeDep`; the same covers-check right after the size checks; log `scope.user.id` |
| `POST /assignments/bulk` | `scope: AdminScopeDep, scope_service: Annotated[AdminScopeService, Depends(get_admin_scope_service)]`; `await scope_service.ensure_users_in_scope(scope, body.user_ids)` first |
| `GET /surveys?user_ids=` | the same `ensure_users_in_scope(scope, parsed)` after parsing |

- Invites always create role `user` today (`admin_user_service.invite` never sets a role), so no change is needed there. Add a test pinning it.
- `companies_with_projects(project_ids)`: when `project_ids` is not None, keep only those projects and drop companies left with none.

- [ ] **Step 1: Write the failing route tests**

```python
# backend/tests/integration/test_routers/test_admin_scope_routes.py
"""Behaviour of scoped admin routes beyond the matrix's status checks."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest_asyncio
from sqlalchemy import select

from src.db.models import User, UserTrack
from tests.fixtures.auth import auth_headers
from tests.fixtures.factories import (
    create_company,
    create_project,
    create_track,
    create_user,
    make_project_admin,
)

if TYPE_CHECKING:
    from httpx import AsyncClient
    from sqlalchemy.ext.asyncio import AsyncSession

    from src.core.configs.settings import Settings


@pytest_asyncio.fixture
async def world(db_session: AsyncSession):
    company = await create_company(db_session, "Scope Co")
    a = await create_project(db_session, company, "Scope A")
    b = await create_project(db_session, company, "Scope B")
    coach = await create_user(db_session, email="scope-coach@example.com", password="x" * 12)
    await make_project_admin(db_session, coach, a)
    la = await create_user(
        db_session, email="scope-la@example.com", company_id=company.id, project_id=a.id
    )
    lb = await create_user(
        db_session, email="scope-lb@example.com", company_id=company.id, project_id=b.id
    )
    track = await create_track(db_session, "Scope Track")
    return {"a": a, "b": b, "coach": coach, "la": la, "lb": lb, "track": track}


async def test_user_list_defaults_to_the_only_project(
    client: AsyncClient, world, test_settings: Settings
) -> None:
    r = await client.get("/api/admin/users", headers=auth_headers(world["coach"], test_settings))
    assert r.status_code == 200
    ids = {u["id"] for u in r.json()["users"]}
    assert str(world["la"].id) in ids and str(world["lb"].id) not in ids


async def test_user_list_for_foreign_project_is_404(
    client: AsyncClient, world, test_settings: Settings
) -> None:
    r = await client.get(
        f"/api/admin/users?project_id={world['b'].id}",
        headers=auth_headers(world["coach"], test_settings),
    )
    assert r.status_code == 404


async def test_multi_project_admin_must_name_a_project(
    client: AsyncClient, db_session: AsyncSession, world, test_settings: Settings
) -> None:
    await make_project_admin(db_session, world["coach"], world["b"])
    r = await client.get("/api/admin/users", headers=auth_headers(world["coach"], test_settings))
    assert r.status_code == 400


async def test_bulk_assign_with_one_foreign_user_writes_nothing(
    client: AsyncClient, db_session: AsyncSession, world, test_settings: Settings
) -> None:
    r = await client.post(
        "/api/admin/assignments/bulk",
        json={
            "user_ids": [str(world["la"].id), str(world["lb"].id)],
            "track_ids": [str(world["track"].id)],
            "assigned": True,
        },
        headers=auth_headers(world["coach"], test_settings),
    )
    assert r.status_code == 404
    rows = (await db_session.execute(select(UserTrack))).scalars().all()
    assert not [t for t in rows if t.user_id in (world["la"].id, world["lb"].id)]


async def test_invite_into_foreign_project_is_404_and_own_project_is_user_role(
    client: AsyncClient, db_session: AsyncSession, world, test_settings: Settings
) -> None:
    headers = auth_headers(world["coach"], test_settings)
    body = {"first_name": "N", "last_name": "L", "send_email": False}
    r = await client.post(
        "/api/admin/invites",
        json={**body, "email": "scope-new-b@example.com", "project_id": str(world["b"].id)},
        headers=headers,
    )
    assert r.status_code == 404
    r = await client.post(
        "/api/admin/invites",
        json={**body, "email": "scope-new-a@example.com", "project_id": str(world["a"].id)},
        headers=headers,
    )
    assert r.status_code == 201
    created = (
        await db_session.execute(select(User).where(User.email == "scope-new-a@example.com"))
    ).scalar_one()
    assert created.role == "user"


async def test_role_change_is_power_only(
    client: AsyncClient, world, test_settings: Settings
) -> None:
    r = await client.patch(
        f"/api/admin/users/{world['la'].id}",
        json={"role": "admin"},
        headers=auth_headers(world["coach"], test_settings),
    )
    assert r.status_code == 403


async def test_companies_list_only_shows_scoped_projects(
    client: AsyncClient, world, test_settings: Settings
) -> None:
    r = await client.get(
        "/api/admin/companies", headers=auth_headers(world["coach"], test_settings)
    )
    assert r.status_code == 200
    project_ids = {p["id"] for c in r.json()["companies"] for p in c["projects"]}
    assert project_ids == {str(world["a"].id)}


async def test_project_admin_cannot_touch_another_project_admin(
    client: AsyncClient, db_session: AsyncSession, world, test_settings: Settings
) -> None:
    other_coach = await create_user(
        db_session, email="scope-coach2@example.com", project_id=world["a"].id
    )
    await make_project_admin(db_session, other_coach, world["b"])
    r = await client.delete(
        f"/api/admin/users/{other_coach.id}", headers=auth_headers(world["coach"], test_settings)
    )
    assert r.status_code == 403
```

If `InviteRequest`'s field names differ from `first_name`/`last_name`/`email`/`project_id`/`send_email`, read `backend/src/schemas/admin_users.py` and match them.

- [ ] **Step 2: Run them to verify they fail**

Run: `cd backend && uv run pytest tests/integration/test_routers/test_admin_scope_routes.py -v`
Expected: FAIL. The coach gets 403 everywhere, because routes are still power-only.

- [ ] **Step 3: Apply the router pattern above**

Remove `user+` from `RoleUpdateRequest`. Add the `project_ids` filter to `OrgService.companies_with_projects`.

- [ ] **Step 4: Flip the matrix rows**

In `test_authz.py`:
- every row whose route has `{user_id}` or `{project_id}` and is listed in the table above becomes `"scoped"`, except `PATCH /users/{user_id}`, which stays `"power"`;
- `GET /users`, `/learning`, `/dashboard`, `/companies` and `/surveys` (the `user_ids` form, with the path including `?user_ids={s.user.id}`) become `"scoped_list"`;
- `/invites` (body project = `s.project.id`) becomes `"scoped"`;
- `/assignments/bulk` with `user_ids=[s.user.id]` becomes `"scoped"`.
- Note that `pa_out` gets a 404 on `/surveys?user_ids={s.user.id}`. Make that row `"scoped"` too.
- In `TestBulkInviteAuthz` (or `test_admin_bulk_invite.py`), add a case where a project admin of another project posts `project_id=seed.project.id` and gets a 404.

- [ ] **Step 5: Run the full suite**

Run: `cd backend && uv run pytest tests/integration/test_routers/test_admin_scope_routes.py tests/integration/test_routers/test_authz.py -v && uv run poe test`
Expected: all PASS. Fix the `user+` tests in `test_admin_users.py` (`test_user_plus_is_denied_admin_endpoints`): delete them, because the role no longer exists. The new matrix covers "learner gets 403".

- [ ] **Step 6: Commit**

```bash
git add backend/src backend/tests
git commit -m "feat(authz): open user management to project admins, scoped (B1, #93)"
```

---

### Task 6: Grant/revoke endpoints, plus the self and last-power-admin guards

**Files:**
- Create: `backend/src/routers/admin_project_admins.py`; register it in `backend/src/main.py` next to the other admin routers.
- Create: `backend/src/schemas/admin_project_admins.py`
- Modify: `backend/src/services/admin_user_service.py` (`set_role`, `delete_user` take an `actor: User` and enforce the guards)
- Modify: `backend/src/core/dependencies/domain.py` (`get_admin_user_service` gets the project-admin repo, for list/grant)
- Modify: `backend/src/routers/admin_users.py` (pass the actor)
- Modify: `backend/tests/integration/test_routers/test_authz.py` (three new rows)
- Test: `backend/tests/integration/test_routers/test_admin_project_admins.py`

**Interfaces:**
- `GET /api/admin/projects/{project_id}/admins` → `ProjectAdminsResponse(admins: list[ProjectAdminOut])`, where `ProjectAdminOut(user_id, first_name, last_name, email, granted_at)`. Guard: `require_project_in_scope`.
- `PUT /api/admin/projects/{project_id}/admins/{user_id}` → 204. Guard: power admin. 404 for an unknown project or user. A no-op if the target is a power admin.
- `DELETE /api/admin/projects/{project_id}/admins/{user_id}` → 204. Guard: power admin. 404 when no row exists.
- `AdminUserService.set_role(actor, user_id, role)` and `delete_user(actor, user_id)` raise `LastPowerAdminError` / `SelfModificationError` (both `ConflictError`, so → 409).
- Grant/revoke log line: `project admin granted: project=%s user=%s by=%s` (UUIDs only).

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/integration/test_routers/test_admin_project_admins.py
from __future__ import annotations

from typing import TYPE_CHECKING

from tests.fixtures.auth import auth_headers
from tests.fixtures.factories import create_company, create_project, create_user

if TYPE_CHECKING:
    from httpx import AsyncClient
    from sqlalchemy.ext.asyncio import AsyncSession

    from src.core.configs.settings import Settings


async def test_grant_list_revoke(
    client: AsyncClient, db_session: AsyncSession, test_settings: Settings
) -> None:
    company = await create_company(db_session, "Grant Co")
    project = await create_project(db_session, company, "Grant P")
    power = await create_user(db_session, email="grant-power@example.com", role="admin")
    coach = await create_user(db_session, email="grant-coach@example.com")
    h = auth_headers(power, test_settings)
    base = f"/api/admin/projects/{project.id}/admins"

    assert (await client.put(f"{base}/{coach.id}", headers=h)).status_code == 204
    listed = (await client.get(base, headers=h)).json()["admins"]
    assert [a["user_id"] for a in listed] == [str(coach.id)]
    # the coach can now read the list for their own project, but not grant
    hc = auth_headers(coach, test_settings)
    assert (await client.get(base, headers=hc)).status_code == 200
    assert (await client.put(f"{base}/{power.id}", headers=hc)).status_code == 403
    assert (await client.delete(f"{base}/{coach.id}", headers=h)).status_code == 204
    assert (await client.delete(f"{base}/{coach.id}", headers=h)).status_code == 404
    # revoked → no admin access at all on the next request
    assert (await client.get(base, headers=hc)).status_code == 403


async def test_last_power_admin_cannot_demote_or_delete_self(
    client: AsyncClient, db_session: AsyncSession, test_settings: Settings
) -> None:
    from sqlalchemy import update

    from src.db.models import User

    # Isolate: demote every other admin in this test transaction.
    await db_session.execute(update(User).where(User.role == "admin").values(role="user"))
    await db_session.commit()
    power = await create_user(db_session, email="last-power@example.com", role="admin")
    h = auth_headers(power, test_settings)
    r = await client.patch(f"/api/admin/users/{power.id}", json={"role": "user"}, headers=h)
    assert r.status_code == 409
    r = await client.delete(f"/api/admin/users/{power.id}", headers=h)
    assert r.status_code == 409
    await db_session.refresh(power)
    assert power.role == "admin"


async def test_power_admin_cannot_delete_self_even_if_not_last(
    client: AsyncClient, db_session: AsyncSession, test_settings: Settings
) -> None:
    p1 = await create_user(db_session, email="self-p1@example.com", role="admin")
    await create_user(db_session, email="self-p2@example.com", role="admin")
    r = await client.delete(f"/api/admin/users/{p1.id}", headers=auth_headers(p1, test_settings))
    assert r.status_code == 409
```

`test_last_power_admin…` changes rows inside the per-test session. Check how `db_session` isolates tests (transaction rollback or truncation) in `tests/conftest.py` before relying on it. If tests share committed state, count admins with `count_power_admins` and demote only within a nested savepoint, following whatever pattern `conftest.py` documents.

- [ ] **Step 2: Run them to verify they fail**

Run: `cd backend && uv run pytest tests/integration/test_routers/test_admin_project_admins.py -v`
Expected: FAIL (404 on the new routes; 204 instead of 409 on self-delete).

- [ ] **Step 3: Implement**

Exceptions, in `backend/src/services/exceptions.py`:

```python
class SelfModificationError(ConflictError):
    def __init__(self) -> None:
        super().__init__("You can't change your own role or delete your own account")


class LastPowerAdminError(ConflictError):
    def __init__(self) -> None:
        super().__init__("At least one power admin must remain")
```

Service guards, in `AdminUserService`:

```python
    async def set_role(self, actor: User, user_id: uuid.UUID, role: str) -> None:
        user = await self._users.get_by_id(user_id)
        if user is None:
            raise NotFoundError("User")
        if user.id == actor.id:
            raise SelfModificationError
        if user.role == "admin" and role != "admin" and await self._users.count_power_admins() <= 1:
            raise LastPowerAdminError
        await self._users.update_role(user, role)

    async def delete_user(self, actor: User, user_id: uuid.UUID) -> None:
        user = await self._users.get_by_id(user_id)
        if user is None:
            raise NotFoundError("User")
        if user.id == actor.id:
            raise SelfModificationError
        if user.role == "admin" and await self._users.count_power_admins() <= 1:
            raise LastPowerAdminError
        await self._users.delete(user)
```

Routers pass the actor: `update_user_role` takes `actor: PowerAdminDep`, and `delete_user` takes `scope: AdminScopeDep` and passes `scope.user`.

Add the grant/list/revoke service methods to `AdminUserService`. It already owns users + org, and the new `ProjectAdminRepository` is injected via `get_admin_user_service`:

```python
    async def list_project_admins(self, project_id: uuid.UUID) -> list[tuple[User, datetime]]:
        await self.ensure_project(project_id)
        return await self._project_admins.list_for_project(project_id)

    async def grant_project_admin(
        self, actor: User, project_id: uuid.UUID, user_id: uuid.UUID
    ) -> None:
        await self.ensure_project(project_id)
        user = await self._users.get_by_id(user_id)
        if user is None:
            raise NotFoundError("User")
        if user.role == "admin":
            return  # power admins already cover every project
        await self._project_admins.grant(user_id, project_id, actor.id)

    async def revoke_project_admin(self, project_id: uuid.UUID, user_id: uuid.UUID) -> None:
        if not await self._project_admins.revoke(user_id, project_id):
            raise NotFoundError("Project admin")
```

The router (`admin_project_admins.py`): prefix `/api/admin`, tag `admin:project-admins`, no router-level dependency. `GET` has `dependencies=[Depends(require_project_in_scope)]`; `PUT` and `DELETE` take `actor: PowerAdminDep`. Each of the latter logs `logger.info("project admin granted: project=%s user=%s by=%s", project_id, user_id, actor.id)` (and the revoked equivalent).

Add the three rows to `_MATRIX`:
- `("project-admins-list", "GET", ..., "scoped", "/api/admin/projects/{project_id}/admins")`
- PUT and DELETE with `{s.other.id}` as `"power"`. `s.other` has no project, which is fine for a power-admin grant.

Order the matrix rows so the DELETE row's target has a row to delete: either make DELETE target `s.pa_in` on `s.project` (it exists in the seed), or accept 404 as "authz passed", since `not in (401, 403, 500)` already allows it.

- [ ] **Step 4: Run the tests**

Run: `cd backend && uv run pytest tests/integration/test_routers/test_admin_project_admins.py tests/integration/test_routers/test_authz.py -v && uv run poe test`
Expected: PASS. Existing `test_admin_users.py` tests that call the services directly need the new `actor` argument.

- [ ] **Step 5: Commit**

```bash
git add backend/src backend/tests
git commit -m "feat(admin): grant/revoke project admins, self and last-power-admin guards (B1, #93)"
```

---

### Task 7: Lock bypass for admins on their own project, plus the `/api/me` fields

**Files:**
- Modify: `backend/src/core/constants.py` (delete `LOCK_BYPASS_ROLES` and its comment)
- Modify: `backend/src/routers/learning.py` (two call sites)
- Modify: `backend/src/core/dependencies/components.py`
- Modify: `backend/src/core/dependencies/interview.py` (`require_completed_assessment`, `require_interview_assessment`; delete `_ASSESSMENT_EXEMPT_ROLES`)
- Modify: `backend/src/routers/me.py`, `backend/src/schemas/me.py`
- Modify: `backend/src/services/learning_service.py:214` (docstring: "admin / user+ (LOCK_BYPASS_ROLES)" → "callers who bypass locks (AdminScopeService.bypasses_locks)")
- Modify: `backend/src/services/exceptions.py` (the `ComponentLockedError`, `LessonNotAccessibleError` and `AssessmentRequiredError` docstrings)
- Modify: `backend/tests/integration/test_routers/test_component_lock.py` (`test_admin_is_not_exempt` → `test_admin_bypasses_locked_but_not_hidden`)
- Test: `backend/tests/integration/test_routers/test_lock_bypass.py`

**Interfaces:**
- Consumes: `BypassesLocksDep` and `get_bypasses_locks` (Task 3).
- Produces: `UserProfileResponse` gains `is_power_admin: bool`, `admin_project_ids: list[uuid.UUID]` and `bypasses_locks: bool`.

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/integration/test_routers/test_lock_bypass.py
"""Spec decision 5: power admins and project admins on their OWN project bypass
locked components, the lesson gate and the assessment gate; hidden stays hidden;
AI surface toggles stay a hard gate."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest_asyncio

from src.db.models import ProjectComponentSetting
from tests.fixtures.auth import auth_headers
from tests.fixtures.factories import (
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


@pytest_asyncio.fixture
async def world(db_session: AsyncSession):
    company = await create_company(db_session, "Bypass Co")
    a = await create_project(db_session, company, "Bypass A")  # learning locked by default
    b = await create_project(db_session, company, "Bypass B")
    own = await create_user(db_session, email="bypass-own@example.com", project_id=a.id)
    await make_project_admin(db_session, own, a)
    foreign = await create_user(db_session, email="bypass-foreign@example.com", project_id=a.id)
    await make_project_admin(db_session, foreign, b)
    track = await create_track(db_session, "Bypass Track")
    module = await create_module(db_session, track, "Bypass Module")
    lesson = await create_lesson(db_session, module, "Bypass Lesson")  # not assigned to anyone
    return {"a": a, "own": own, "foreign": foreign, "lesson": lesson}


async def test_own_project_admin_bypasses_locked_component_and_lesson_gate(
    client: AsyncClient, world, test_settings: Settings
) -> None:
    h = auth_headers(world["own"], test_settings)
    assert (await client.get("/api/learning/graph", headers=h)).status_code == 200
    assert (await client.get(f"/api/lessons/{world['lesson'].id}", headers=h)).status_code == 200
    journey = (await client.get("/api/me/journey", headers=h)).json()
    assert journey["components"]["learning"]["locked"] is False
    me = (await client.get("/api/me", headers=h)).json()
    assert me["bypasses_locks"] is True
    assert me["is_power_admin"] is False
    assert me["admin_project_ids"] == [str(world["a"].id)]


async def test_admin_of_another_project_does_not_bypass(
    client: AsyncClient, world, test_settings: Settings
) -> None:
    h = auth_headers(world["foreign"], test_settings)
    assert (await client.get("/api/learning/graph", headers=h)).status_code == 403
    assert (await client.get("/api/me", headers=h)).json()["bypasses_locks"] is False


async def test_hidden_stays_hidden_for_bypassing_admin(
    client: AsyncClient, db_session: AsyncSession, world, test_settings: Settings
) -> None:
    db_session.add(
        ProjectComponentSetting(
            project_id=world["a"].id, component="learning", hidden=True, locked=False
        )
    )
    await db_session.commit()
    h = auth_headers(world["own"], test_settings)
    assert (await client.get("/api/learning/graph", headers=h)).status_code == 403
    journey = (await client.get("/api/me/journey", headers=h)).json()
    assert journey["components"]["learning"]["hidden"] is True


async def test_own_project_admin_skips_assessment_gate_but_not_ai_toggle(
    client: AsyncClient, world, test_settings: Settings
) -> None:
    # interview component locked by default (bypassed) and the interview AI surface is
    # off by default: the response must be the AI-surface 403, not AssessmentRequired.
    h = auth_headers(world["own"], test_settings)
    r = await client.post("/api/interview/opener", headers=h)
    assert r.status_code == 403
    assert "AI feature not enabled" in r.text
```

The last test depends on the order of the interview dependencies. Read the `router = APIRouter(...)` line in `backend/src/routers/interview.py` to see which gate fires first. If the AI-surface gate fires before the assessment gate, this test passes trivially. In that case also add a unit test that calls `require_completed_assessment(user, surveys, bypasses_locks=True)` directly with an `AsyncMock` `SurveyService` returning `"not_started"`, and asserts no raise. With `bypasses_locks=False`, assert `AssessmentRequiredError`.

- [ ] **Step 2: Run them to verify they fail**

Run: `cd backend && uv run pytest tests/integration/test_routers/test_lock_bypass.py -v`
Expected: FAIL. The graph returns 403 for `own`, and `/api/me` has no `bypasses_locks`.

- [ ] **Step 3: Implement**

`components.py`: both dependencies take `bypasses_locks: BypassesLocksDep`.

```python
async def _ensure_unlocked(
    org_service: OrgService, user: User, component: str, *, bypasses_locks: bool
) -> None:
    resolved = await org_service.resolve_components(user.project_id)
    state = resolved[component]
    if state["hidden"] or (state["locked"] and not bypasses_locks):
        raise ComponentLockedError(component)
```

Update the module docstring and the factory docstring: it's no longer "not a role check". It now reads "hidden is absolute; locked is bypassed by AdminScopeService.bypasses_locks".

`learning.py`: add `bypasses_locks: BypassesLocksDep` to both handlers and pass `bypass_locks=bypasses_locks`. Remove the `LOCK_BYPASS_ROLES` import.

`interview.py` (the dependency module):

```python
async def require_completed_assessment(
    user: Annotated[User, Depends(get_current_user)],
    surveys: Annotated[SurveyService, Depends(get_survey_service)],
    bypasses_locks: BypassesLocksDep,
) -> None:
    """...Callers who bypass locks (power admins, project admins on their own
    project) are exempt, so they can test the flow (spec 2026-10-01 decision 5)..."""
    if bypasses_locks:
        return
    if await surveys.survey_status(user.id) != "complete":
        raise AssessmentRequiredError
```

`require_interview_assessment` also takes `bypasses_locks: BypassesLocksDep` and passes it through.

`me.py`:

```python
@router.get("", response_model=UserProfileResponse)
async def get_profile(
    user: CurrentUserDep,
    scope_service: Annotated[AdminScopeService, Depends(get_admin_scope_service)],
    bypasses_locks: BypassesLocksDep,
) -> UserProfileResponse:
    scope = await scope_service.scope_for(user)
    return UserProfileResponse.model_validate(user).model_copy(
        update={
            "is_power_admin": user.role == "admin",
            "admin_project_ids": sorted(scope.project_ids) if scope is not None else [],
            "bypasses_locks": bypasses_locks,
        }
    )
```

Give the new schema fields defaults (`is_power_admin: bool = False`, `admin_project_ids: list[uuid.UUID] = []`, `bypasses_locks: bool = False`) so that `model_validate(user)` works.

`get_journey`: add `bypasses_locks: BypassesLocksDep`. When it's true, return every component with `locked=False` and `hidden` unchanged:

```python
    if bypasses_locks:
        components = {c: {**s, "locked": False} for c, s in components.items()}
```

Rename `test_component_lock.py::test_admin_is_not_exempt` to `test_admin_bypasses_locked_but_not_hidden`. Assert a 200 on locked and a 403 on hidden, reusing that file's fixtures.

Remove the `user+` cases in `test_learning.py` (`grep -n "user+" tests/integration/test_routers/test_learning.py`): delete each test that exists only for `user+`. Where a test covers "bypass", switch it to a project admin on their own project via `make_project_admin`.

- [ ] **Step 4: Run the tests**

Run: `cd backend && uv run pytest tests/integration/test_routers/test_lock_bypass.py tests/integration/test_routers/test_component_lock.py tests/integration/test_routers/test_learning.py tests/integration/test_routers/test_interview.py tests/integration/test_routers/test_me.py -v && uv run poe test`
Expected: PASS. `grep -rn "user+\|LOCK_BYPASS_ROLES\|_ASSESSMENT_EXEMPT_ROLES" backend/src backend/tests` returns nothing.

- [ ] **Step 5: Commit**

```bash
git add backend/src backend/tests
git commit -m "feat(learning): admins bypass locks on their own project; /api/me admin fields (B1, #93)"
```

---

### Task 8: Dashboard excludes a project's own admins

**Files:**
- Modify: `backend/src/services/dashboard_service.py` (around line 66–74)
- Modify: `backend/src/core/dependencies/domain.py` (`get_dashboard_service` gets `ProjectAdminRepository`)
- Test: `backend/tests/integration/test_routers/test_admin_dashboard.py` (add one test)

**Interfaces:**
- Consumes: `ProjectAdminRepository.admin_ids_for_project` (Task 2). Add `all_pairs() -> set[tuple[UUID, UUID]]` to the repository (and its ABC) for the unscoped case.

- [ ] **Step 1: Write the failing test** (append to `test_admin_dashboard.py`; reuse its imports and fixtures)

```python
async def test_project_admins_are_not_counted_as_learners(
    client: AsyncClient, db_session: AsyncSession, test_settings: Settings
) -> None:
    company = await create_company(db_session, "Dash PA Co")
    project = await create_project(db_session, company, "Dash PA")
    power = await create_user(db_session, email="dash-pa-power@example.com", role="admin")
    await create_user(db_session, email="dash-pa-l1@example.com", project_id=project.id)
    coach = await create_user(db_session, email="dash-pa-coach@example.com", project_id=project.id)
    await make_project_admin(db_session, coach, project)
    r = await client.get(
        f"/api/admin/dashboard?project_id={project.id}", headers=auth_headers(power, test_settings)
    )
    assert r.status_code == 200
    funnel = next(f for f in r.json()["funnels"] if f["project_id"] == str(project.id))
    assert funnel["invited"] == 1
```

Read `backend/src/schemas/admin_dashboard.py` for the real funnel field names (`funnels`, `invited`, `project_id`) and adjust the two lookups to match.

- [ ] **Step 2: Run it to verify it fails**

Run: `cd backend && uv run pytest tests/integration/test_routers/test_admin_dashboard.py -k project_admins -v`
Expected: FAIL (`invited == 2`).

- [ ] **Step 3: Implement**

The filter in `overview()`:

```python
        staff_pairs = await self._project_admins.all_pairs()  # {(user_id, project_id)}
        rows = [
            (user, company_name, project_name)
            for user, company_name, project_name in await self._users.list_with_org_names(
                project_id
            )
            if user.role != "admin" and (user.id, user.project_id) not in staff_pairs
        ]
```

Add `all_pairs` to `ProjectAdminRepository`:

```python
    async def all_pairs(self) -> set[tuple[uuid.UUID, uuid.UUID]]:
        result = await self._session.execute(
            select(ProjectAdmin.user_id, ProjectAdmin.project_id)
        )
        return {(u, p) for u, p in result.all()}
```

Update the comment above the filter: "admins are staff, not learners — power admins everywhere, project admins in the projects they run".

- [ ] **Step 4: Run the tests**

Run: `cd backend && uv run pytest tests/integration/test_routers/test_admin_dashboard.py -v && uv run poe test`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/src backend/tests
git commit -m "feat(dashboard): exclude a project's own admins from its learner stats (B1, #93)"
```

---

### Task 9: Frontend minimum: drop `user+`, read the new `/api/me` fields

**Files:**
- Regenerate: `frontend/src/api/schema.d.ts` (`cd frontend && npm run gen:api`; it imports the app, never the DB)
- Modify: `frontend/src/contexts/AuthContext.tsx` (`Role = 'admin' | 'user'`; expose `isPowerAdmin`, `bypassesLocks`, `adminProjectIds`)
- Modify: `frontend/src/lib/learningPathLocks.ts` (+ `.test.ts`): `canBypassLocks` comes from `bypassesLocks`
- Modify: `frontend/src/lib/interviewAccess.ts` (+ `.test.ts`): replace the `role` arg with `bypassesLocks: boolean`; `if (!bypassesLocks && surveyStatus !== 'complete')`
- Modify: `frontend/src/pages/LearningPathNew.tsx:242-247`: `const canBypassLocks = bypassesLocks` (keep `isAdmin = role === 'admin'` for edit controls)
- Modify: `frontend/src/pages/JourneyHome.tsx`, `frontend/src/pages/Interview.tsx` (pass `bypassesLocks` instead of `role`)
- Modify: `frontend/src/pages/admin2/PeoplePage.tsx` (drop the `user+` bulk role button), `UserDetailPage.tsx` (drop the `user+` option), `api.ts` (role type), `frontend/src/styles/admin.css` (drop the `user+` badge rule)

**Interfaces:**
- Consumes: `UserProfileResponse.is_power_admin`, `.admin_project_ids`, `.bypasses_locks` (Task 7).

- [ ] **Step 1: Update the tests first**

In `interviewAccess.test.ts`, change every `role: 'admin'` case to `bypassesLocks: true` and every `role: 'user'` or `role: 'user+'` case to `bypassesLocks: false`. Keep the existing assertion that a non-bypassing learner without a completed survey gets `'needs_assessment'`. Add:

```ts
it('lets a lock-bypassing project admin skip the assessment', () => {
  expect(
    interviewAccess({ componentLocked: false, bypassesLocks: true, surveyStatus: 'not_started', interviewStatus: 'not_started' }),
  ).not.toBe('needs_assessment')
})
```

Use the real exported function name from `interviewAccess.ts`. In `learningPathLocks.test.ts`, delete the `user+` cases and keep the `canBypassLocks: true` ones.

- [ ] **Step 2: Run them to verify they fail**

Run: `cd frontend && npx vitest run src/lib/interviewAccess.test.ts src/lib/learningPathLocks.test.ts`
Expected: FAIL (type errors or a wrong argument).

- [ ] **Step 3: Implement the changes listed under Files.** `grep -rn "user+" frontend/src` must return nothing afterwards, except inside `schema.d.ts` if the backend still mentions it (it shouldn't).

- [ ] **Step 4: Run the frontend checks**

Run: `cd frontend && npm run gen:api && npm run typecheck && npm run lint && npm test && npm run build`
Expected: all PASS. CI's "fresh API types" check passes because `schema.d.ts` is regenerated.

- [ ] **Step 5: Commit**

```bash
git add frontend
git commit -m "feat(frontend): drop user+, read lock bypass from /api/me (B1, #93)"
```

---

### Task 10: Docs

**Files:**
- Modify: `CLAUDE.md`. In "Locking, prerequisites & preview":
  - replace the `user+`/`LOCK_BYPASS_ROLES` wording with the new rule: power admin, or a project admin on their own project, bypasses `locked`, prerequisites, the lesson gate and the assessment gate; `hidden` is absolute; AI toggles are a hard gate;
  - "Auth" line: roles are `admin` (power) / `user`, plus `project_admins` rows;
  - Rule 1 note: admin routes are scoped by `core/dependencies/admin_scope.py`;
  - update the migration head in "Current state" to `a9b0c1d2e3f4`.
- Modify: `backend/CLAUDE.md`: under conventions, "every `/api/admin/*` route declares one guard from `core/dependencies/admin_scope.py`; `test_authz.py` fails on a route missing from `_MATRIX`".
- Modify: `docs/feature-index.md`: add "Project-scoped admins → `docs/superpowers/specs/2026-10-01-project-scoped-admin-design.md`".
- Modify: `docs/superpowers/specs/2026-07-22-user-plus-role-design.md`: add a top line, "Superseded 2026-10-01: `user+` removed by `2026-10-01-project-scoped-admin-design.md`".
- Modify: `SECURITY.md`: one line under access control. Project admins can read the personal data (assessment, interview) of their projects' learners; grants are logged with UUIDs.

- [ ] **Step 1: Make the edits above.**
- [ ] **Step 2: Run the docs-drift test.** Run `cd backend && uv run pytest tests/unit/test_docs_drift.py -v`. Expected: PASS (every path named exists).
- [ ] **Step 3: Commit**

```bash
git add CLAUDE.md backend/CLAUDE.md docs SECURITY.md
git commit -m "docs: project-scoped admins in CLAUDE.md, feature index, security (B1, #93)"
```

---

## Finish

- Full checks:
  - backend: `uv run poe format-check && uv run poe lint-src && uv run poe ty-src && uv run poe test`;
  - frontend: `npm run typecheck && npm run lint && npm test && npm run build`.
- Push `feat/project-scoped-admin` and open a PR titled "feat: project-scoped admins (B1)", with `Closes #93` in the body. The body states that the PR carries **one migration** (`a9b0c1d2e3f4`, which also turns `user+` accounts into `user`), applied by the Deploy migrate job.
- After deploy, nobody is a project admin until a power admin calls `PUT /api/admin/projects/{id}/admins/{user_id}`. The UI for that arrives with #144.
- A final whole-branch review runs before handing the PR to an admin to merge.
