# Admin housekeeping (B6) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Power admins can:
- move a user to another project;
- rename and delete projects and companies, where a delete takes its users with it (power admins excepted);
- see every uploaded media file, with where it's used, and delete unused ones.

**Architecture:**
- **Backend:**
  - pure helpers: `core/media_paths.py` (path validation) and `core/media_usage.py` (block scanning);
  - new repository methods, including flush-only `stage_*` writes for the atomic flows;
  - `AdminUserService.move_user` (it gains the unit of work);
  - `OrgService` gets renames;
  - a new `OrgDeletionService` (impact + delete);
  - `MediaService` gets storage list and delete;
  - a new `MediaUsageService` (lessons + live proposals).
  - Routers orchestrate media (usage service, then storage), as `backend/CLAUDE.md` allows.
- **Frontend:**
  - a Move dialog on the user detail page;
  - rename/delete on the Projects page plus a Companies section;
  - a new Media page.

**Tech Stack:** FastAPI, SQLAlchemy 2 async, azure-storage-blob (sync SDK via `run_in_threadpool`), Postgres; React 18 + TypeScript, TanStack Query, Vitest.

**Spec:** `docs/superpowers/specs/2026-10-06-admin-housekeeping-design.md`.

## Global Constraints

- Read `CLAUDE.md`, `backend/CLAUDE.md`, `frontend/CLAUDE.md`.
- **One database:** never `uv run poe dev`, never `alembic upgrade`. No migration in this plan. Integration tests use the remote test DB: check `Test-NetConnection … -Port 5432`, and never run two pytest sessions at once.
- **The test harness never commits** (savepoints). Tests assert on rows, not on commit side effects.
- **Every B6 route is power admin only** (`require_power_admin`, `_MATRIX` access `"power"`).
- **Services never call services.** New services take repositories (and the unit of work) only.
- **Power admins are never deleted** by a project or company delete; they become project- and company-less.
- Deletes and moves commit once (stage + `uow.commit()`).
- Log lines carry ids and counts only, never names or emails.
- No `window.confirm`; use `ConfirmButton`. No `as unknown as` casts (lint rule).
- Media names must match `^[0-9a-f]{32}\.[a-z0-9]{2,5}$` under `images/` or `videos/`; anything else is 404.
- A FK census is done (2026-10-06): all 15 FKs into `users.id` are `CASCADE` or `SET NULL`. `users.company_id → companies` is `RESTRICT`, which is why users are deleted or detached before a company is.
- Commit messages end with `Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>`.

## Review Focus

1. **Deleting the project that holds the caller's own home membership, or one holding the only other power admin.** Expect power admins kept and made project-less, never deleted. Test in Task 3 (`test_delete_project_keeps_power_admins_project_less`).
2. **A project admin of another project whose home membership is the deleted project.** Expect that user deleted (they are a member), and their grants elsewhere to cascade with them. Test in Task 3 (`test_delete_project_deletes_members_even_if_they_run_another_project`).
3. **Moving a user into a project they administer.** Expect the grant on that project removed, and grants on other projects kept. Test in Task 2 (`test_move_into_a_project_you_run_drops_only_that_grant`).
4. **A media file referenced only by a rejected or superseded proposal, or by an embed video URL.** Expect "Unused". Test in Task 4 (`test_usage_ignores_dead_proposals_and_embed_videos`).
5. **Deleting the project currently picked in the scope switcher.** Expect the scope to reset to All projects, not a page full of 404s. Test in Task 6 (`resets the scope when the scoped project is deleted`).

---

## File structure

| File | Responsibility |
|---|---|
| Create `backend/src/core/media_paths.py`, `backend/src/core/media_usage.py` | pure: path validation, blob paths in blocks |
| Modify `backend/src/repositories/{base,user_repository,project_admin_repository,org_repository,content_repository,proposal_repository}.py` | new reads + stage writes |
| Modify `backend/src/services/admin_user_service.py` | `move_user` |
| Modify `backend/src/services/org_service.py` | renames |
| Create `backend/src/services/org_deletion_service.py` | impact + delete |
| Modify `backend/src/services/media_service.py` | `list_files`, `delete_file` |
| Create `backend/src/services/media_usage_service.py` | usage map, unused guard |
| Modify `backend/src/core/dependencies/domain.py`, `backend/src/core/dependencies/storage.py` | DI |
| Modify `backend/src/routers/admin_users.py`, `admin_org.py`, `admin_media.py`; `backend/src/schemas/{admin_users,admin_org,admin_media}.py` | routes |
| Modify `backend/tests/fixtures/media.py` | fake listing + delete |
| Create `frontend/src/lib/orgImpact.ts`, `frontend/src/lib/mediaLibrary.ts` (+ tests) | sentences, filters, totals |
| Create `frontend/src/pages/admin2/MoveUserDialog.tsx`, `OrgDeleteDialog.tsx`, `MediaPage.tsx` (+ tests) | UI |
| Modify `frontend/src/pages/admin2/{UserDetailPage,ProjectsPage,api,nav}.tsx/ts`, `frontend/src/App.tsx` | wiring |

---

### Task 1: Pure helpers and repository methods

**Files:**
- Create: `backend/src/core/media_paths.py`, `backend/src/core/media_usage.py`
- Modify: the repositories listed above
- Test: `backend/tests/unit/test_media_helpers.py`, `backend/tests/integration/test_repositories/test_housekeeping_repository.py`

**Interfaces (produced):**
- `media_paths.media_path(kind: str, name: str) -> str | None`: `"images/<hex>.png"`, or None when invalid.
- `media_usage.blob_paths(blocks: Any) -> set[str]`: image `blob_path`s, plus video `blob_path`s where `source == "blob"`; empty strings are ignored; tolerant of any shape.
- `AbstractUserRepository`:
  - `members_of(project_ids: list[UUID], company_id: UUID | None) -> list[User]`: users whose `project_id` is in `project_ids`, or whose `company_id == company_id`;
  - `stage_set_org(user_ids: list[UUID], project_id: UUID | None, company_id: UUID | None) -> None`;
  - `stage_delete_many(user_ids: list[UUID]) -> None` (flush only).
- `AbstractProjectAdminRepository.stage_revoke(user_id, project_id) -> None`.
- `AbstractOrgRepository`:
  - `rename_company(company, name) -> Company` and `rename_project(project, name) -> Project` (commit);
  - `stage_delete_project(project)` and `stage_delete_company(company)` (flush).
- `AbstractContentRepository.lessons_with_module_titles() -> list[tuple[Lesson, str]]` (full rows).
- `AbstractProposalRepository.live_block_sets() -> list[list[Any]]`: for each `pending`/`approved` proposal, its `base_blocks`, `proposed_blocks` and `edited_blocks` (when not null) as separate entries.

- [ ] **Step 1: Failing unit tests for the pure helpers**

```python
# backend/tests/unit/test_media_helpers.py
from __future__ import annotations

import pytest

from src.core.media_paths import media_path
from src.core.media_usage import blob_paths

HEX = "0123456789abcdef0123456789abcdef"


@pytest.mark.parametrize(
    ("kind", "name", "expected"),
    [
        ("images", f"{HEX}.png", f"images/{HEX}.png"),
        ("videos", f"{HEX}.mp4", f"videos/{HEX}.mp4"),
        ("docs", f"{HEX}.png", None),
        ("images", "../secret.png", None),
        ("images", f"{HEX}.PNG", None),
        ("images", f"{HEX[:-1]}.png", None),
        ("images", f"{HEX}.png/x", None),
    ],
)
def test_media_path_accepts_only_upload_shaped_names(kind: str, name: str, expected: str | None) -> None:
    assert media_path(kind, name) == expected


def test_blob_paths_finds_images_and_blob_videos_only() -> None:
    blocks = [
        {"id": "i", "type": "image", "blob_path": "images/a.png", "alt": "x"},
        {"id": "e", "type": "image", "blob_path": "", "alt": "placeholder"},
        {"id": "v", "type": "video", "source": "blob", "blob_path": "videos/b.mp4"},
        {"id": "y", "type": "video", "source": "embed", "url": "https://youtube.com/embed/x"},
        {"id": "p", "type": "paragraph", "text": "images/c.png in prose is not a reference"},
        "garbage",
    ]
    assert blob_paths(blocks) == {"images/a.png", "videos/b.mp4"}
    assert blob_paths(None) == set()
```

Run: `cd backend && uv run pytest tests/unit/test_media_helpers.py -v`. Expected: FAIL (modules missing).

- [ ] **Step 2: Implement the pure helpers**

```python
# backend/src/core/media_paths.py
"""Valid media blob paths (B6). Uploads are named `<kind>s/<uuid4 hex><ext>`
(services/media_service.py), so the library only ever touches that shape —
anything else (traversal, other prefixes) is rejected before storage sees it."""

from __future__ import annotations

import re

__all__ = ["media_path"]

_KINDS = frozenset({"images", "videos"})
_NAME = re.compile(r"^[0-9a-f]{32}\.[a-z0-9]{2,5}$")


def media_path(kind: str, name: str) -> str | None:
    if kind not in _KINDS or not _NAME.fullmatch(name):
        return None
    return f"{kind}/{name}"
```

```python
# backend/src/core/media_usage.py
"""Which media blobs a content_blocks array references (B6 media library).
Pure and shape-tolerant: lessons and AI proposals are opaque JSONB."""

from __future__ import annotations

from typing import Any

__all__ = ["blob_paths"]


def blob_paths(blocks: Any) -> set[str]:
    """Image blob_paths and stored-video blob_paths (source == "blob"). Embed
    videos point outside our storage; empty paths are upload placeholders."""
    found: set[str] = set()
    if not isinstance(blocks, list):
        return found
    for block in blocks:
        if not isinstance(block, dict):
            continue
        kind = block.get("type")
        path = block.get("blob_path")
        if not isinstance(path, str) or not path:
            continue
        if kind == "image" or (kind == "video" and block.get("source") == "blob"):
            found.add(path)
    return found
```

Run the unit tests. Expected: PASS.

- [ ] **Step 3: Failing repository integration tests**

```python
# backend/tests/integration/test_repositories/test_housekeeping_repository.py
from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import select

from src.db.models import LessonContentProposal, Project, User
from src.repositories.content_repository import ContentRepository
from src.repositories.org_repository import OrgRepository
from src.repositories.project_admin_repository import ProjectAdminRepository
from src.repositories.proposal_repository import ProposalRepository
from src.repositories.unit_of_work import UnitOfWork
from src.repositories.user_repository import UserRepository
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
    from sqlalchemy.ext.asyncio import AsyncSession


async def test_members_of_projects_and_company(db_session: AsyncSession) -> None:
    company = await create_company(db_session, "B6 Repo Co")
    p1 = await create_project(db_session, company, "B6 P1")
    other = await create_project(db_session, await create_company(db_session, "B6 Other Co"), "B6 P2")
    in_p1 = await create_user(db_session, email="b6-in-p1@example.com", company_id=company.id, project_id=p1.id)
    company_only = await create_user(db_session, email="b6-co@example.com", company_id=company.id)
    await create_user(db_session, email="b6-out@example.com", project_id=other.id)
    repo = UserRepository(db_session)

    assert {u.id for u in await repo.members_of([p1.id], None)} == {in_p1.id}
    assert {u.id for u in await repo.members_of([p1.id], company.id)} == {in_p1.id, company_only.id}


async def test_stage_set_org_and_delete_many(db_session: AsyncSession) -> None:
    company = await create_company(db_session, "B6 Stage Co")
    project = await create_project(db_session, company, "B6 Stage P")
    a = await create_user(db_session, email="b6-a@example.com", project_id=project.id)
    b = await create_user(db_session, email="b6-b@example.com", project_id=project.id)
    repo = UserRepository(db_session)

    await repo.stage_set_org([a.id], None, None)
    await repo.stage_delete_many([b.id])
    await UnitOfWork(db_session).commit()

    rows = {u.id: u for u in (await db_session.execute(select(User).where(User.id.in_([a.id, b.id])))).scalars()}
    await db_session.refresh(rows[a.id])
    assert rows[a.id].project_id is None
    assert b.id not in rows


async def test_org_rename_and_stage_delete(db_session: AsyncSession) -> None:
    company = await create_company(db_session, "B6 Rename Co")
    project = await create_project(db_session, company, "Old name")
    repo = OrgRepository(db_session)

    renamed = await repo.rename_project(project, "New name")
    assert renamed.name == "New name"
    await repo.stage_delete_company(company)
    await UnitOfWork(db_session).commit()

    assert (await db_session.execute(select(Project).where(Project.id == project.id))).scalar_one_or_none() is None


async def test_stage_revoke(db_session: AsyncSession) -> None:
    company = await create_company(db_session, "B6 Grant Co")
    project = await create_project(db_session, company, "B6 Grant P")
    coach = await create_user(db_session, email="b6-coach@example.com")
    await make_project_admin(db_session, coach, project)
    repo = ProjectAdminRepository(db_session)

    await repo.stage_revoke(coach.id, project.id)
    await UnitOfWork(db_session).commit()

    assert not await repo.is_project_admin(coach.id)


async def test_lessons_with_module_titles_and_live_proposal_blocks(db_session: AsyncSession) -> None:
    module = await create_module(db_session, await create_track(db_session), "B6 Module")
    lesson = await create_lesson(db_session, module, "B6 Lesson")
    blocks = [{"id": "i", "type": "image", "blob_path": "images/x.png", "alt": "a"}]
    for status in ("pending", "rejected"):
        db_session.add(LessonContentProposal(
            lesson_id=lesson.id, proposed_blocks=blocks, base_blocks=[], status=status,
            source_feedback_ids=[], summary="s",
        ))
    await db_session.commit()

    rows = await ContentRepository(db_session).lessons_with_module_titles()
    assert any(le.id == lesson.id and title == "B6 Module" for le, title in rows)
    sets = await ProposalRepository(db_session).live_block_sets()
    assert blocks in sets
    assert sets.count(blocks) == 1  # the rejected proposal is not live
```

Before running, check `LessonContentProposal`'s required columns in `src/db/models/proposal.py` (e.g. `source_feedback_ids`, `summary`) and adjust the constructor call to what the model requires.

Run: `cd backend && uv run pytest tests/integration/test_repositories/test_housekeeping_repository.py -v -p no:randomly`. Expected: FAIL (`AttributeError`s).

- [ ] **Step 4: Implement the repository methods**

ABCs in `base.py` (with docstrings as in the Interfaces block). Implementations:

```python
# UserRepository
    async def members_of(
        self, project_ids: list[uuid.UUID], company_id: uuid.UUID | None
    ) -> list[User]:
        conditions = []
        if project_ids:
            conditions.append(User.project_id.in_(project_ids))
        if company_id is not None:
            conditions.append(User.company_id == company_id)
        if not conditions:
            return []
        result = await self._session.execute(select(User).where(or_(*conditions)))
        return list(result.scalars().all())

    async def stage_set_org(
        self, user_ids: list[uuid.UUID], project_id: uuid.UUID | None, company_id: uuid.UUID | None
    ) -> None:
        if user_ids:
            await self._session.execute(
                update(User).where(User.id.in_(user_ids)).values(project_id=project_id, company_id=company_id)
            )

    async def stage_delete_many(self, user_ids: list[uuid.UUID]) -> None:
        # One DELETE; every FK into users.id is CASCADE or SET NULL (census 2026-10-06).
        if user_ids:
            await self._session.execute(delete(User).where(User.id.in_(user_ids)))
```

(Import `delete`, `update`, `or_` from sqlalchemy where missing.)

```python
# ProjectAdminRepository
    async def stage_revoke(self, user_id: uuid.UUID, project_id: uuid.UUID) -> None:
        await self._session.execute(
            delete(ProjectAdmin).where(ProjectAdmin.user_id == user_id, ProjectAdmin.project_id == project_id)
        )
```

```python
# OrgRepository
    async def rename_company(self, company: Company, name: str) -> Company:
        company.name = name
        await self._session.commit()
        await self._session.refresh(company)
        return company

    async def rename_project(self, project: Project, name: str) -> Project:
        project.name = name
        await self._session.commit()
        await self._session.refresh(project)
        return project

    async def stage_delete_project(self, project: Project) -> None:
        await self._session.delete(project)
        await self._session.flush()

    async def stage_delete_company(self, company: Company) -> None:
        # projects.company_id is ON DELETE CASCADE; users pointing at the
        # company (RESTRICT) must be gone or detached first (OrgDeletionService).
        await self._session.delete(company)
        await self._session.flush()
```

```python
# ContentRepository
    async def lessons_with_module_titles(self) -> list[tuple[Lesson, str]]:
        result = await self._session.execute(
            select(Lesson, Module.title).join(Module, Module.id == Lesson.module_id)
        )
        return [(lesson, title) for lesson, title in result.all()]
```

```python
# ProposalRepository
    async def live_block_sets(self) -> list[list[Any]]:
        result = await self._session.execute(
            select(
                LessonContentProposal.base_blocks,
                LessonContentProposal.proposed_blocks,
                LessonContentProposal.edited_blocks,
            ).where(LessonContentProposal.status.in_(("pending", "approved")))
        )
        sets: list[list[Any]] = []
        for base, proposed, edited in result.all():
            sets.extend(blocks for blocks in (base, proposed, edited) if blocks is not None)
        return sets
```

If a concrete or in-memory subclass of these ABCs exists outside `src/repositories/` (`grep -rn "AbstractUserRepository)\|AbstractOrgRepository)\|AbstractProjectAdminRepository)\|AbstractContentRepository)\|AbstractProposalRepository)" backend/src backend/tests backend/evals`), implement the new methods there too.

- [ ] **Step 5: Run, check, commit**

Run the unit test and the integration test file. Expected: PASS. Then `uv run poe format && uv run poe lint-src && uv run poe ty-src` (clean).

```bash
git add backend/src backend/tests
git commit -m "feat(admin): media path/usage helpers and housekeeping repository methods (B6, #147)"
```

---

### Task 2: Move a user to another project

**Files:**
- Modify: `backend/src/services/admin_user_service.py` (constructor gains `uow`; `move_user`)
- Modify: `backend/src/core/dependencies/domain.py` (`get_admin_user_service` passes `uow`)
- Modify: `backend/tests/integration/test_routers/test_admin_bulk_invite.py:51`, `backend/tests/unit/test_admin_user_guards.py:28` (constructor)
- Modify: `backend/src/schemas/admin_users.py`, `backend/src/routers/admin_users.py`, `backend/tests/integration/test_routers/test_authz.py`
- Test: `backend/tests/unit/test_move_user.py`, `backend/tests/integration/test_routers/test_move_user.py`

**Interfaces:**
- Produces:
  - `AdminUserService(..., *, project_admins, uow: AbstractUnitOfWork)`;
  - `move_user(user_id: UUID, project_id: UUID) -> User`;
  - `PUT /api/admin/users/{user_id}/project` body `MoveUserRequest{project_id}` → 204.

- [ ] **Step 1: Failing unit tests**

```python
# backend/tests/unit/test_move_user.py
from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from src.repositories.base import (
    AbstractAssignmentRepository,
    AbstractAuthSessionRepository,
    AbstractContentRepository,
    AbstractOrgRepository,
    AbstractProgressRepository,
    AbstractProjectAdminRepository,
    AbstractSurveyRepository,
    AbstractUnitOfWork,
    AbstractUserRepository,
)
from src.services.admin_user_service import AdminUserService
from src.services.exceptions import NotFoundError

OLD, NEW, COMPANY = (uuid.uuid4() for _ in range(3))


def _service(user: SimpleNamespace | None, project: SimpleNamespace | None):  # noqa: ANN202
    users = AsyncMock(spec=AbstractUserRepository)
    users.get_by_id.return_value = user
    org = AsyncMock(spec=AbstractOrgRepository)
    org.get_project.return_value = project
    admins = AsyncMock(spec=AbstractProjectAdminRepository)
    admins.project_ids_for.return_value = frozenset()
    uow = AsyncMock(spec=AbstractUnitOfWork)
    service = AdminUserService(
        users, org,
        AsyncMock(spec=AbstractAssignmentRepository), AsyncMock(spec=AbstractContentRepository),
        AsyncMock(spec=AbstractSurveyRepository), AsyncMock(spec=AbstractAuthSessionRepository),
        AsyncMock(spec=AbstractProgressRepository),
        project_admins=admins, uow=uow,
    )
    return service, users, admins, uow


def _user() -> SimpleNamespace:
    return SimpleNamespace(id=uuid.uuid4(), project_id=OLD, company_id=uuid.uuid4(), role="user")


async def test_move_sets_project_and_its_company_in_one_commit() -> None:
    user = _user()
    service, users, admins, uow = _service(user, SimpleNamespace(id=NEW, company_id=COMPANY))

    await service.move_user(user.id, NEW)

    users.stage_set_org.assert_awaited_once_with([user.id], NEW, COMPANY)
    admins.stage_revoke.assert_not_awaited()
    uow.commit.assert_awaited_once()


async def test_move_into_a_project_you_run_drops_only_that_grant() -> None:
    user = _user()
    service, _, admins, _ = _service(user, SimpleNamespace(id=NEW, company_id=COMPANY))
    admins.project_ids_for.return_value = frozenset({NEW, uuid.uuid4()})

    await service.move_user(user.id, NEW)

    admins.stage_revoke.assert_awaited_once_with(user.id, NEW)


async def test_moving_to_the_current_project_changes_nothing() -> None:
    user = _user()
    service, users, _, uow = _service(user, SimpleNamespace(id=OLD, company_id=COMPANY))
    await service.move_user(user.id, OLD)
    users.stage_set_org.assert_not_awaited()
    uow.commit.assert_not_awaited()


@pytest.mark.parametrize("missing", ["user", "project"])
async def test_unknown_user_or_project_is_404(missing: str) -> None:
    user = _user()
    service, _, _, _ = _service(
        None if missing == "user" else user,
        None if missing == "project" else SimpleNamespace(id=NEW, company_id=COMPANY),
    )
    with pytest.raises(NotFoundError):
        await service.move_user(uuid.uuid4(), NEW)
```

Run: expected FAIL (`TypeError` on `uow`, then `AttributeError`).

- [ ] **Step 2: Implement**

Constructor: add `uow: AbstractUnitOfWork` after `project_admins` (keyword-only), store it as `self._uow`, and import the ABC under `TYPE_CHECKING`.

```python
    async def move_user(self, user_id: uuid.UUID, project_id: uuid.UUID) -> User:
        """B6 / #111: change a user's home project (and its company). Assignments,
        progress, survey and interview stay: they belong to the user. A grant to
        administer the DESTINATION project is dropped — staff aren't learners of
        the project they run (B1). One commit."""
        user = await self._users.get_by_id(user_id)
        if user is None:
            raise NotFoundError("User")
        project = await self._org.get_project(project_id)
        if project is None:
            raise NotFoundError("Project")
        if user.project_id == project.id:
            return user
        if project.id in await self._project_admins.project_ids_for(user.id):
            await self._project_admins.stage_revoke(user.id, project.id)
        await self._users.stage_set_org([user.id], project.id, project.company_id)
        await self._uow.commit()
        return user
```

DI: in `get_admin_user_service`, add `uow: Annotated[UnitOfWork, Depends(get_unit_of_work)]` and pass `uow=uow`; `get_unit_of_work` must be defined above it. Update the two test construction sites (`uow=AsyncMock()` in the unit guard test; in `test_admin_bulk_invite.py`, `uow=UnitOfWork(db_session)`).

Schema `MoveUserRequest(BaseModel): project_id: uuid.UUID` (in `__all__`). Route in `admin_users.py`:

```python
@router.put(
    "/users/{user_id}/project",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_power_admin)],
)
async def move_user(
    user_id: uuid.UUID, body: MoveUserRequest, admin_user_service: AdminUserServiceDep
) -> None:
    """Move a user to another project (B6 / #111); assignments and progress stay."""
    await admin_user_service.move_user(user_id, body.project_id)
    logger.info("user moved: user=%s project=%s", user_id, body.project_id)
```

`_MATRIX` row: `("user-move", "PUT", "/api/admin/users/{user_id}/project", lambda s: f"/api/admin/users/{s.user.id}/project", lambda s: {"project_id": str(s.other_project.id)}, "power")`.

- [ ] **Step 3: Integration test**

```python
# backend/tests/integration/test_routers/test_move_user.py
from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import select

from src.db.models import User
from src.repositories.assignment_repository import AssignmentRepository
from tests.fixtures.auth import auth_headers
from tests.fixtures.factories import (
    assign_lesson, create_company, create_lesson, create_module, create_project, create_track, create_user,
)

if TYPE_CHECKING:
    from httpx import AsyncClient
    from sqlalchemy.ext.asyncio import AsyncSession

    from src.core.configs.settings import Settings


async def test_move_keeps_assignments_and_updates_company(
    client: AsyncClient, db_session: AsyncSession, test_settings: Settings
) -> None:
    power = await create_user(db_session, email="b6-move-power@example.com", role="admin")
    old_co = await create_company(db_session, "B6 Old Co")
    new_co = await create_company(db_session, "B6 New Co")
    old = await create_project(db_session, old_co, "B6 Old")
    new = await create_project(db_session, new_co, "B6 New")
    learner = await create_user(db_session, email="b6-mover@example.com", company_id=old_co.id, project_id=old.id)
    lesson = await create_lesson(db_session, await create_module(db_session, await create_track(db_session)))
    await assign_lesson(db_session, learner, lesson)

    response = await client.put(
        f"/api/admin/users/{learner.id}/project",
        json={"project_id": str(new.id)},
        headers=auth_headers(power, test_settings),
    )

    assert response.status_code == 204
    moved = (await db_session.execute(select(User).where(User.id == learner.id))).scalar_one()
    await db_session.refresh(moved)
    assert (moved.project_id, moved.company_id) == (new.id, new_co.id)
    assert lesson.id in await AssignmentRepository(db_session).lesson_ids_for_user(learner.id)
```

- [ ] **Step 4: Run, check, commit**

Run the unit test, the integration test, `test_admin_users.py`, `test_admin_bulk_invite.py` and `test_authz.py`. Then format/lint/ty.

```bash
git commit -am "feat(admin): move a user to another project (B6, #111)"
```

(`git add` any new test files first.)

---

### Task 3: Rename and delete projects and companies

**Files:**
- Modify: `backend/src/services/org_service.py` (renames)
- Create: `backend/src/services/org_deletion_service.py`
- Modify: `backend/src/core/dependencies/domain.py` (`get_org_deletion_service`), `backend/src/schemas/admin_org.py`, `backend/src/routers/admin_org.py`, `test_authz.py`
- Test: `backend/tests/unit/test_org_deletion_service.py`, `backend/tests/unit/test_org_service.py` (renames), `backend/tests/integration/test_routers/test_org_housekeeping.py`

**Interfaces:**
- Produces:
  - `OrgService.rename_company(company_id, name) -> Company`: strips the name; 404 when unknown; `DuplicateCompanyNameError` when another company has the name case-insensitively;
  - `OrgService.rename_project(project_id, name) -> Project`;
  - `OrgImpact` (frozen dataclass: `projects: int, users_deleted: int, power_admins_kept: int, project_admin_grants: int, users_with_progress: int`);
  - `OrgDeletionService(org, users, project_admins, progress, uow)` with `project_impact(id)`, `company_impact(id)`, `delete_project(id) -> OrgImpact` and `delete_company(id) -> OrgImpact`.
  - Routes, all power:
    - `PATCH /api/admin/projects/{project_id}` and `PATCH /api/admin/companies/{company_id}`, `{name}` → `ProjectOut` / `CompanyOut`;
    - `GET …/impact` → `OrgImpactResponse`;
    - `DELETE …` → 204.

- [ ] **Step 1: Failing unit tests**

```python
# backend/tests/unit/test_org_deletion_service.py
from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock

from src.repositories.base import (
    AbstractOrgRepository,
    AbstractProgressRepository,
    AbstractProjectAdminRepository,
    AbstractUnitOfWork,
    AbstractUserRepository,
)
from src.services.org_deletion_service import OrgDeletionService, OrgImpact

CO = uuid.uuid4()
P1, P2 = uuid.uuid4(), uuid.uuid4()


def _u(role: str = "user", project_id: uuid.UUID | None = P1) -> SimpleNamespace:
    return SimpleNamespace(id=uuid.uuid4(), role=role, project_id=project_id, company_id=CO)


def _service(members: list[SimpleNamespace]):  # noqa: ANN202
    org = AsyncMock(spec=AbstractOrgRepository)
    org.get_project.return_value = SimpleNamespace(id=P1, company_id=CO)
    org.get_company.return_value = SimpleNamespace(id=CO)
    org.list_projects.return_value = [SimpleNamespace(id=P1, company_id=CO), SimpleNamespace(id=P2, company_id=CO),
                                      SimpleNamespace(id=uuid.uuid4(), company_id=uuid.uuid4())]
    users = AsyncMock(spec=AbstractUserRepository)
    users.members_of.return_value = members
    admins = AsyncMock(spec=AbstractProjectAdminRepository)
    admins.admin_ids_for_project.return_value = {uuid.uuid4(), uuid.uuid4()}
    progress = AsyncMock(spec=AbstractProgressRepository)
    progress.latest_completion_by_user.side_effect = lambda ids: dict.fromkeys(ids[:1], object())
    uow = AsyncMock(spec=AbstractUnitOfWork)
    return OrgDeletionService(org, users, admins, progress, uow), org, users, uow


async def test_project_impact_counts_members_power_admins_grants_progress() -> None:
    learner, other, power = _u(), _u(), _u("admin")
    service, _, users, _ = _service([learner, other, power])

    impact = await service.project_impact(P1)

    users.members_of.assert_awaited_once_with([P1], None)
    assert impact == OrgImpact(projects=0, users_deleted=2, power_admins_kept=1, project_admin_grants=2, users_with_progress=1)


async def test_delete_project_keeps_power_admins_project_less() -> None:
    learner, power = _u(), _u("admin")
    service, org, users, uow = _service([learner, power])

    await service.delete_project(P1)

    users.stage_set_org.assert_awaited_once_with([power.id], None, power.company_id)
    users.stage_delete_many.assert_awaited_once_with([learner.id])
    org.stage_delete_project.assert_awaited_once()
    uow.commit.assert_awaited_once()


async def test_delete_project_deletes_members_even_if_they_run_another_project() -> None:
    coach = _u()  # a member of P1 who administers some other project
    service, _, users, _ = _service([coach])
    await service.delete_project(P1)
    users.stage_delete_many.assert_awaited_once_with([coach.id])


async def test_delete_company_covers_its_projects_and_detaches_power_admins_fully() -> None:
    learner, power = _u(project_id=P2), _u("admin")
    service, org, users, _ = _service([learner, power])

    impact = await service.delete_company(CO)

    users.members_of.assert_awaited_once_with([P1, P2], CO)
    users.stage_set_org.assert_awaited_once_with([power.id], None, None)
    users.stage_delete_many.assert_awaited_once_with([learner.id])
    org.stage_delete_company.assert_awaited_once()
    assert impact.projects == 2
```

The project-admin grants count is the sum of `admin_ids_for_project` over the affected projects: 2 for one project, 4 for the company's two. Add a renames test to `test_org_service.py`: unknown company → `NotFoundError`; a name taken by *another* company → `DuplicateCompanyNameError`; renaming a company to its own name in different case is allowed.

Run: expected FAIL.

- [ ] **Step 2: Implement `OrgDeletionService`**

```python
# backend/src/services/org_deletion_service.py
"""Delete a project or a company with its users (B6, spec 2026-10-06 decisions
2-3). Members are deleted — their progress, survey, interview, sessions and
grants cascade (every FK into users.id is CASCADE or SET NULL) — except power
admins, who are kept and detached. One commit; repositories only."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from src.services.exceptions import NotFoundError

if TYPE_CHECKING:
    import uuid

    from src.db.models import User
    from src.repositories.base import (
        AbstractOrgRepository,
        AbstractProgressRepository,
        AbstractProjectAdminRepository,
        AbstractUnitOfWork,
        AbstractUserRepository,
    )

__all__ = ["OrgDeletionService", "OrgImpact"]


@dataclass(frozen=True)
class OrgImpact:
    projects: int
    users_deleted: int
    power_admins_kept: int
    project_admin_grants: int
    users_with_progress: int


class OrgDeletionService:
    def __init__(
        self,
        org: AbstractOrgRepository,
        users: AbstractUserRepository,
        project_admins: AbstractProjectAdminRepository,
        progress: AbstractProgressRepository,
        uow: AbstractUnitOfWork,
    ) -> None:
        self._org = org
        self._users = users
        self._project_admins = project_admins
        self._progress = progress
        self._uow = uow

    async def project_impact(self, project_id: uuid.UUID) -> OrgImpact:
        await self._project(project_id)
        return await self._impact([project_id], None, projects=0)

    async def company_impact(self, company_id: uuid.UUID) -> OrgImpact:
        project_ids = await self._company_project_ids(company_id)
        return await self._impact(project_ids, company_id, projects=len(project_ids))

    async def delete_project(self, project_id: uuid.UUID) -> OrgImpact:
        project = await self._project(project_id)
        impact = await self._impact([project_id], None, projects=0)
        members = await self._users.members_of([project_id], None)
        kept = [u for u in members if u.role == "admin"]
        for user in kept:
            await self._users.stage_set_org([user.id], None, user.company_id)
        await self._users.stage_delete_many([u.id for u in members if u.role != "admin"])
        await self._org.stage_delete_project(project)
        await self._uow.commit()
        return impact

    async def delete_company(self, company_id: uuid.UUID) -> OrgImpact:
        company = await self._org.get_company(company_id)
        if company is None:
            raise NotFoundError("Company")
        project_ids = await self._company_project_ids(company_id)
        impact = await self._impact(project_ids, company_id, projects=len(project_ids))
        members = await self._users.members_of(project_ids, company_id)
        kept = [u.id for u in members if u.role == "admin"]
        if kept:
            await self._users.stage_set_org(kept, None, None)
        await self._users.stage_delete_many([u.id for u in members if u.role != "admin"])
        await self._org.stage_delete_company(company)
        await self._uow.commit()
        return impact

    async def _project(self, project_id: uuid.UUID):  # noqa: ANN202
        project = await self._org.get_project(project_id)
        if project is None:
            raise NotFoundError("Project")
        return project

    async def _company_project_ids(self, company_id: uuid.UUID) -> list[uuid.UUID]:
        if await self._org.get_company(company_id) is None:
            raise NotFoundError("Company")
        return [p.id for p in await self._org.list_projects() if p.company_id == company_id]

    async def _impact(
        self, project_ids: list[uuid.UUID], company_id: uuid.UUID | None, *, projects: int
    ) -> OrgImpact:
        members: list[User] = await self._users.members_of(project_ids, company_id)
        deleted = [u.id for u in members if u.role != "admin"]
        grants = 0
        for project_id in project_ids:
            grants += len(await self._project_admins.admin_ids_for_project(project_id))
        with_progress = await self._progress.latest_completion_by_user(deleted) if deleted else {}
        return OrgImpact(
            projects=projects,
            users_deleted=len(deleted),
            power_admins_kept=len(members) - len(deleted),
            project_admin_grants=grants,
            users_with_progress=len(with_progress),
        )
```

`delete_project` detaches each kept power admin with its own `stage_set_org([id], None, user.company_id)` call, because they keep their company; `delete_company` clears both in one call. Annotate `_project`'s return as `Project` (imported under `TYPE_CHECKING`) instead of the `noqa`.

**Renames** in `OrgService`:

```python
    async def rename_company(self, company_id: uuid.UUID, name: str) -> Company:
        company = await self._org.get_company(company_id)
        if company is None:
            raise NotFoundError("Company")
        name = name.strip()
        clash = await self._org.get_company_by_name_ci(name)
        if clash is not None and clash.id != company.id:
            raise DuplicateCompanyNameError
        return await self._org.rename_company(company, name)

    async def rename_project(self, project_id: uuid.UUID, name: str) -> Project:
        project = await self._org.get_project(project_id)
        if project is None:
            raise NotFoundError("Project")
        return await self._org.rename_project(project, name.strip())
```

DI:

```python
def get_org_deletion_service(
    org: Annotated[OrgRepository, Depends(get_org_repository)],
    users: Annotated[UserRepository, Depends(get_user_repository)],
    project_admins: Annotated[ProjectAdminRepository, Depends(get_project_admin_repository)],
    progress: Annotated[ProgressRepository, Depends(get_progress_repository)],
    uow: Annotated[UnitOfWork, Depends(get_unit_of_work)],
) -> OrgDeletionService:
    return OrgDeletionService(org, users, project_admins, progress, uow)
```

Place it at the end of the file (after every provider it depends on), and add it to `__all__`.

**Schemas** (`admin_org.py`): `RenameRequest{name: str}` with `require_non_blank` and a null refusal (like B4's `_not_null`); `OrgImpactResponse` with the five ints (`from_attributes=True`).

**Routes** (`admin_org.py`, each `dependencies=[Depends(require_power_admin)]`):
- `PATCH /projects/{project_id}` → `ProjectOut`
- `PATCH /companies/{company_id}` → `CompanyOut`
- `GET /projects/{project_id}/impact` and `GET /companies/{company_id}/impact` → `OrgImpactResponse`
- `DELETE /projects/{project_id}` and `DELETE /companies/{company_id}` → 204, logging `"project deleted: project=%s users_deleted=%d power_admins_kept=%d"` (company: `"company deleted: company=%s projects=%d users_deleted=%d power_admins_kept=%d"`).

`_MATRIX` rows (all `power`):
- the two renames: body `{"name": "Renamed"}`, targets `s.project` / `s.company`;
- the two impacts;
- the two deletes, targeting `s.other_project`, then `s.company`, at the END of the matrix list.

The company delete removes the seed company. Each row gets a fresh seed, so that's fine, but keep destructive rows last for readability.

- [ ] **Step 3: Integration tests**

```python
# backend/tests/integration/test_routers/test_org_housekeeping.py
from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import select

from src.db.models import Company, Project, User
from tests.fixtures.auth import auth_headers
from tests.fixtures.factories import (
    complete_lesson, create_company, create_lesson, create_module, create_project, create_track, create_user,
    make_project_admin,
)

if TYPE_CHECKING:
    from httpx import AsyncClient
    from sqlalchemy.ext.asyncio import AsyncSession

    from src.core.configs.settings import Settings


async def _exists(db_session: AsyncSession, model, id_) -> bool:  # noqa: ANN001
    return (await db_session.execute(select(model).where(model.id == id_))).scalar_one_or_none() is not None


async def test_delete_project_impact_then_delete(
    client: AsyncClient, db_session: AsyncSession, test_settings: Settings
) -> None:
    caller = await create_user(db_session, email="b6-del-caller@example.com", role="admin")
    company = await create_company(db_session, "B6 Del Co")
    project = await create_project(db_session, company, "B6 Del P")
    elsewhere = await create_project(db_session, company, "B6 Elsewhere")
    learner = await create_user(db_session, email="b6-del-l@example.com", company_id=company.id, project_id=project.id)
    power = await create_user(db_session, email="b6-del-power@example.com", role="admin",
                              company_id=company.id, project_id=project.id)
    coach = await create_user(db_session, email="b6-del-coach@example.com", company_id=company.id, project_id=elsewhere.id)
    await make_project_admin(db_session, coach, project)
    lesson = await create_lesson(db_session, await create_module(db_session, await create_track(db_session)))
    await complete_lesson(db_session, learner, lesson)
    headers = auth_headers(caller, test_settings)

    impact = await client.get(f"/api/admin/projects/{project.id}/impact", headers=headers)
    assert impact.json() == {"projects": 0, "users_deleted": 1, "power_admins_kept": 1,
                             "project_admin_grants": 1, "users_with_progress": 1}

    assert (await client.delete(f"/api/admin/projects/{project.id}", headers=headers)).status_code == 204
    assert not await _exists(db_session, Project, project.id)
    assert not await _exists(db_session, User, learner.id)
    assert await _exists(db_session, User, coach.id)  # member of another project, only lost the grant
    kept = (await db_session.execute(select(User).where(User.id == power.id))).scalar_one()
    await db_session.refresh(kept)
    assert kept.project_id is None


async def test_delete_company_takes_projects_and_company_only_users(
    client: AsyncClient, db_session: AsyncSession, test_settings: Settings
) -> None:
    caller = await create_user(db_session, email="b6-delco-caller@example.com", role="admin")
    company = await create_company(db_session, "B6 DelCo")
    project = await create_project(db_session, company, "B6 DelCo P")
    member = await create_user(db_session, email="b6-delco-m@example.com", company_id=company.id, project_id=project.id)
    loose = await create_user(db_session, email="b6-delco-loose@example.com", company_id=company.id)

    response = await client.delete(f"/api/admin/companies/{company.id}", headers=auth_headers(caller, test_settings))

    assert response.status_code == 204
    for model, id_ in ((Company, company.id), (Project, project.id), (User, member.id), (User, loose.id)):
        assert not await _exists(db_session, model, id_)


async def test_rename_project_and_duplicate_company_name(
    client: AsyncClient, db_session: AsyncSession, test_settings: Settings
) -> None:
    caller = await create_user(db_session, email="b6-ren@example.com", role="admin")
    a = await create_company(db_session, "B6 Alpha")
    await create_company(db_session, "B6 Beta")
    project = await create_project(db_session, a, "B6 Old")
    headers = auth_headers(caller, test_settings)

    renamed = await client.patch(f"/api/admin/projects/{project.id}", json={"name": " B6 New "}, headers=headers)
    assert renamed.json()["name"] == "B6 New"
    clash = await client.patch(f"/api/admin/companies/{a.id}", json={"name": "b6 beta"}, headers=headers)
    assert clash.status_code == 409
    blank = await client.patch(f"/api/admin/companies/{a.id}", json={"name": "  "}, headers=headers)
    assert blank.status_code == 422
```

- [ ] **Step 4: Run, check, commit**

Run the unit tests, `test_org_housekeeping.py`, `test_admin_org.py`, `test_authz.py`, then format/lint/ty.

```bash
git add backend && git commit -m "feat(admin): rename and delete projects and companies (B6, #147)"
```

---

### Task 4: Media library backend

**Files:**
- Modify: `backend/src/services/media_service.py` (protocol + `list_files` + `delete_file`), `backend/tests/fixtures/media.py` (fake)
- Create: `backend/src/services/media_usage_service.py`
- Modify: `backend/src/core/dependencies/domain.py` (`get_media_usage_service`), `backend/src/services/exceptions.py` (`MediaInUseError`), `backend/src/schemas/admin_media.py`, `backend/src/routers/admin_media.py`, `test_authz.py`
- Test: `backend/tests/unit/test_media_library.py`, `backend/tests/integration/test_routers/test_media_library.py`

**Interfaces:**
- Produces:
  - `StoredFile` (frozen dataclass: `path: str, kind: Literal["image","video"], size_bytes: int, uploaded_at: datetime`);
  - `MediaService.list_files() -> list[StoredFile]`, sorted newest first;
  - `MediaService.delete_file(path) -> bool` (False when missing);
  - `MediaUsage` (frozen: `lessons: list[tuple[UUID, str, str]]` as id, title, module title; `proposals: int`);
  - `MediaUsageService(content, proposals)` with `usage() -> dict[str, MediaUsage]` and `ensure_unused(path) -> None`, which raises `MediaInUseError`;
  - routes `GET /api/admin/media` → `MediaLibraryResponse{files, total_bytes}`, and `DELETE /api/admin/media/{kind}/{name}` → 204.

- [ ] **Step 1: Extend the fake storage**

In `tests/fixtures/media.py`:
- `RecordingUploader` gains a `stored: dict[str, tuple[int, datetime]]` (path → size and uploaded time) and `deleted: list[str]`;
- `get_container_client(container)` returns a `_FakeContainer` whose `list_blobs()` yields `SimpleNamespace(name=path, size=size, last_modified=ts)` for every stored entry;
- `_FakeBlobClient.delete_blob()` removes the entry and records the path, or raises `azure.core.exceptions.ResourceNotFoundError` when it's absent;
- a successful `upload_blob` also adds to `stored`.

- [ ] **Step 2: Failing unit tests**

```python
# backend/tests/unit/test_media_library.py
from __future__ import annotations

import uuid
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from src.repositories.base import AbstractContentRepository, AbstractProposalRepository
from src.services.exceptions import MediaInUseError
from src.services.media_service import MediaService
from src.services.media_usage_service import MediaUsageService
from tests.fixtures.media import TEST_STORAGE, RecordingUploader

IMG = "images/" + "a" * 32 + ".png"
VID = "videos/" + "b" * 32 + ".mp4"


def _media(uploader: RecordingUploader) -> MediaService:
    return MediaService(
        uploader, account_name=TEST_STORAGE.account_name,
        account_key=TEST_STORAGE.account_key.get_secret_value(),
        blob_endpoint=TEST_STORAGE.blob_endpoint, container=TEST_STORAGE.container,
        sas_ttl_hours=TEST_STORAGE.sas_ttl_hours,
    )


async def test_list_and_delete_files() -> None:
    uploader = RecordingUploader()
    uploader.stored[IMG] = (10, datetime(2026, 1, 1, tzinfo=UTC))
    uploader.stored[VID] = (20, datetime(2026, 2, 1, tzinfo=UTC))
    media = _media(uploader)

    files = await media.list_files()
    assert [(f.path, f.kind, f.size_bytes) for f in files] == [(VID, "video", 20), (IMG, "image", 10)]
    assert await media.delete_file(IMG) is True
    assert await media.delete_file(IMG) is False


def _usage(lessons: list, proposal_sets: list) -> MediaUsageService:  # noqa: ANN401
    content = AsyncMock(spec=AbstractContentRepository)
    content.lessons_with_module_titles.return_value = lessons
    proposals = AsyncMock(spec=AbstractProposalRepository)
    proposals.live_block_sets.return_value = proposal_sets
    return MediaUsageService(content, proposals)


async def test_usage_maps_paths_to_lessons_and_live_proposals() -> None:
    lesson = SimpleNamespace(id=uuid.uuid4(), title="Prompts",
                             content_blocks=[{"id": "i", "type": "image", "blob_path": IMG, "alt": "a"}])
    service = _usage([(lesson, "Basics")], [[{"id": "v", "type": "video", "source": "blob", "blob_path": VID}]])

    usage = await service.usage()

    assert usage[IMG].lessons == [(lesson.id, "Prompts", "Basics")]
    assert usage[VID].proposals == 1


async def test_usage_ignores_dead_proposals_and_embed_videos() -> None:
    lesson = SimpleNamespace(id=uuid.uuid4(), title="L",
                             content_blocks=[{"id": "y", "type": "video", "source": "embed", "url": "https://x"}])
    service = _usage([(lesson, "M")], [])  # live_block_sets already excludes rejected/superseded
    assert await service.usage() == {}


async def test_ensure_unused_refuses_a_referenced_file_naming_the_lesson() -> None:
    lesson = SimpleNamespace(id=uuid.uuid4(), title="Prompts",
                             content_blocks=[{"id": "i", "type": "image", "blob_path": IMG, "alt": "a"}])
    service = _usage([(lesson, "Basics")], [])
    with pytest.raises(MediaInUseError, match="Prompts"):
        await service.ensure_unused(IMG)
    await service.ensure_unused(VID)  # unused: no error
```

Check `TEST_STORAGE`'s attribute names in `src/core/configs/storage.py`; the existing `test_media_service.py` constructs `MediaService` the same way. Copy its construction exactly.

Run: expected FAIL.

- [ ] **Step 3: Implement**

`MediaService`:
- the protocol gains `def get_container_client(self, container: str) -> Any: ...`;
- add:

```python
    async def list_files(self) -> list[StoredFile]:
        """Every uploaded file, newest first (B6 media library)."""
        container = self._uploader.get_container_client(self._container)
        blobs = await run_in_threadpool(lambda: list(container.list_blobs()))
        files = [
            StoredFile(
                path=blob.name,
                kind="image" if blob.name.startswith("images/") else "video",
                size_bytes=int(blob.size or 0),
                uploaded_at=blob.last_modified,
            )
            for blob in blobs
            if blob.name.startswith(("images/", "videos/"))
        ]
        return sorted(files, key=lambda f: f.uploaded_at, reverse=True)

    async def delete_file(self, path: str) -> bool:
        blob = self._uploader.get_blob_client(self._container, path)
        try:
            await run_in_threadpool(blob.delete_blob)
        except ResourceNotFoundError:
            return False
        return True
```

(`from azure.core.exceptions import ResourceNotFoundError`; define `StoredFile` and export it.)

`exceptions.py`: `class MediaInUseError(ConflictError)` with the message `"This file is still used in: " + ", ".join(titles[:5])` (proposal-only use: "an AI content proposal"). It inherits the 409 handler.

```python
# backend/src/services/media_usage_service.py
"""Where each media file is used (B6): lessons, and AI proposals that are still
pending or approved. Any reference means "in use"; deleting is only for unused
files, re-checked at delete time."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from src.core.media_usage import blob_paths
from src.services.exceptions import MediaInUseError

if TYPE_CHECKING:
    from src.repositories.base import AbstractContentRepository, AbstractProposalRepository

__all__ = ["MediaUsage", "MediaUsageService"]


@dataclass
class MediaUsage:
    lessons: list[tuple[uuid.UUID, str, str]] = field(default_factory=list)
    proposals: int = 0


class MediaUsageService:
    def __init__(self, content: AbstractContentRepository, proposals: AbstractProposalRepository) -> None:
        self._content = content
        self._proposals = proposals

    async def usage(self) -> dict[str, MediaUsage]:
        found: dict[str, MediaUsage] = {}
        for lesson, module_title in await self._content.lessons_with_module_titles():
            for path in blob_paths(lesson.content_blocks):
                found.setdefault(path, MediaUsage()).lessons.append((lesson.id, lesson.title, module_title))
        for blocks in await self._proposals.live_block_sets():
            for path in blob_paths(blocks):
                found.setdefault(path, MediaUsage()).proposals += 1
        return found

    async def ensure_unused(self, path: str) -> None:
        use = (await self.usage()).get(path)
        if use is None:
            return
        titles = [title for _, title, _ in use.lessons] or ["an AI content proposal"]
        raise MediaInUseError(titles)
```

(The plan's unit test compares `MediaUsage.lessons`/`.proposals` attributes; a plain `@dataclass` with default factories is fine. `MediaInUseError.__init__(self, titles: list[str])` builds the message.)

DI `get_media_usage_service(content, proposals)` in `domain.py` (a proposal repository provider exists wherever `ContentImprovementService` is wired; reuse it, or add `get_proposal_repository`).

Schemas (`admin_media.py`):
- `MediaUseOut{lesson_id, lesson_title, module_title}`;
- `MediaFileOut{path, kind, size_bytes, uploaded_at, preview_url: str | None, used_in: list[MediaUseOut], proposals: int}`;
- `MediaLibraryResponse{files, total_bytes}`.

Routes (`admin_media.py`):

```python
@router.get("/media", response_model=MediaLibraryResponse, dependencies=[Depends(require_power_admin)])
async def media_library(media: RequiredMediaDep, usage_service: MediaUsageServiceDep) -> MediaLibraryResponse:
    files = await media.list_files()
    usage = await usage_service.usage()
    out = []
    for f in files:
        use = usage.get(f.path)
        out.append(MediaFileOut(
            path=f.path, kind=f.kind, size_bytes=f.size_bytes, uploaded_at=f.uploaded_at,
            preview_url=media.sas_url(f.path) if f.kind == "image" else None,
            used_in=[MediaUseOut(lesson_id=i, lesson_title=t, module_title=m) for i, t, m in (use.lessons if use else [])],
            proposals=use.proposals if use else 0,
        ))
    return MediaLibraryResponse(files=out, total_bytes=sum(f.size_bytes for f in files))


@router.delete("/media/{kind}/{name}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_power_admin)])
async def delete_media(kind: str, name: str, media: RequiredMediaDep, usage_service: MediaUsageServiceDep) -> None:
    """Unused files only, re-checked now (409 names where it is used)."""
    path = media_path(kind, name)
    if path is None:
        raise NotFoundError("Media file")
    await usage_service.ensure_unused(path)
    if not await media.delete_file(path):
        raise NotFoundError("Media file")
    logger.info("media deleted: path=%s", path)
```

Here `RequiredMediaDep = Annotated[MediaService, Depends(require_media_service)]`, as the upload route already uses (check the router's existing alias name and reuse it).

`_MATRIX` rows:
- `("media-list", "GET", "/api/admin/media", …, None, "power")`;
- `("media-delete", "DELETE", "/api/admin/media/{kind}/{name}", lambda s: f"/api/admin/media/images/{'c' * 32}.png", None, "power")`.

With storage unconfigured in the matrix client, the admin gets 404 (allowed); the user gets 403 first, because the route-level guard runs before the media dependency. If the user case instead returns 404, move the media dependency so the guard runs first, and record a ruling.

- [ ] **Step 4: Integration tests**

```python
# backend/tests/integration/test_routers/test_media_library.py
"""GET/DELETE /api/admin/media with the storage faked (pattern of test_admin_media.py)."""
```

Build a `media_client` fixture exactly like `test_admin_media.py`'s (override `get_media_service` with a `MediaService` over a `RecordingUploader`). Then:
- **list:** seed `uploader.stored` with one used and one unused image; create a lesson whose block references the used one. Assert `used_in` names the lesson, the unused one has `[]`, and `total_bytes` is the sum.
- **delete:** deleting the unused one → 204 (and `uploader.deleted` has it); the used one → 409 with the lesson title in the message; a malformed name (`/api/admin/media/images/..%2Fx.png` and `/api/admin/media/docs/{hex}.png`) → 404.

- [ ] **Step 5: Run, then the full backend suite (checkpoint), commit**

Run the new unit and integration tests, `test_admin_media.py`, `test_media_service.py` and `test_authz.py`. Then `uv run poe format-check && uv run poe lint-src && uv run poe ty-src && uv run poe test` (green, coverage ≥ 90%).

```bash
git add backend && git commit -m "feat(admin): media library — list with usage, delete unused (B6, #147)"
```

---

### Task 5: Frontend data layer

**Files:**
- Modify: `frontend/src/api/schema.d.ts` (`npm run gen:api`), `frontend/src/pages/admin2/api.ts`
- Create: `frontend/src/lib/orgImpact.ts`, `frontend/src/lib/mediaLibrary.ts` (+ `.test.ts` each)

**Interfaces:**
- Produces:
  - `impactSentence(kind: 'project' | 'company', name: string, impact: OrgImpact): string`;
  - `mediaSummary(files: MediaFile[]): string` ("38 files · 412 MB · 9 unused (61 MB)");
  - `filterMedia(files, { usage: 'all' | 'unused', kind: 'all' | 'image' | 'video' })`;
  - `formatBytes(n)`;
  - hooks: `useMoveUser()`, `useRenameProject()`, `useRenameCompany()`, `useOrgImpact(kind, id | null)`, `useDeleteOrg()`, `useMediaLibrary()`, `useDeleteMedia()`.

- [ ] **Step 1: Failing helper tests**

```ts
// frontend/src/lib/orgImpact.test.ts
import { describe, expect, it } from 'vitest'
import { impactSentence } from './orgImpact'

describe('impactSentence', () => {
  it('spells out a project delete', () => {
    expect(impactSentence('project', 'Rollout 2025', { projects: 0, users_deleted: 14, power_admins_kept: 1, project_admin_grants: 2, users_with_progress: 12 }))
      .toBe('Deletes Rollout 2025, its 14 users (12 with progress) with their assessments and interviews, its settings and email templates, and 2 project-admin grants. 1 power admin in it keeps their account.')
  })
  it('spells out a company delete with no users', () => {
    expect(impactSentence('company', 'Acme', { projects: 2, users_deleted: 0, power_admins_kept: 0, project_admin_grants: 0, users_with_progress: 0 }))
      .toBe('Deletes Acme and its 2 projects. No users are affected.')
  })
})
```

```ts
// frontend/src/lib/mediaLibrary.test.ts
import { describe, expect, it } from 'vitest'
import { filterMedia, formatBytes, mediaSummary, type MediaFile } from './mediaLibrary'

const f = (path: string, kind: 'image' | 'video', size: number, used: boolean): MediaFile => ({
  path, kind, size_bytes: size, uploaded_at: '2026-10-06T10:00:00Z', preview_url: null,
  used_in: used ? [{ lesson_id: 'l', lesson_title: 'L', module_title: 'M' }] : [], proposals: 0,
})
const FILES = [f('images/a.png', 'image', 1_048_576, true), f('videos/b.mp4', 'video', 3 * 1_048_576, false)]

describe('mediaLibrary', () => {
  it('summarises totals and the unused share', () => {
    expect(mediaSummary(FILES)).toBe('2 files · 4 MB · 1 unused (3 MB)')
  })
  it('filters by usage and kind', () => {
    expect(filterMedia(FILES, { usage: 'unused', kind: 'all' }).map(x => x.path)).toEqual(['videos/b.mp4'])
    expect(filterMedia(FILES, { usage: 'all', kind: 'image' }).map(x => x.path)).toEqual(['images/a.png'])
  })
  it('formats bytes', () => {
    expect(formatBytes(512)).toBe('512 B')
    expect(formatBytes(2048)).toBe('2 KB')
    expect(formatBytes(1_572_864)).toBe('1.5 MB')
  })
})
```

- [ ] **Step 2: Implement**

```ts
// frontend/src/lib/orgImpact.ts
import type { components } from '../api/schema'

export type OrgImpact = components['schemas']['OrgImpactResponse']

const n = (count: number, one: string, many = `${one}s`) => `${count} ${count === 1 ? one : many}`

/** The delete warning (B6): exactly what goes, and who is kept. */
export function impactSentence(kind: 'project' | 'company', name: string, impact: OrgImpact): string {
  const parts: string[] = []
  if (kind === 'company') parts.push(`its ${n(impact.projects, 'project')}`)
  if (impact.users_deleted > 0) {
    parts.push(`its ${n(impact.users_deleted, 'user')} (${impact.users_with_progress} with progress) with their assessments and interviews`)
  }
  if (kind === 'project') parts.push('its settings and email templates')
  if (impact.project_admin_grants > 0) parts.push(n(impact.project_admin_grants, 'project-admin grant'))
  const list = parts.length <= 1 ? parts.join('') : `${parts.slice(0, -1).join(', ')}, and ${parts[parts.length - 1]}`
  let sentence = `Deletes ${name}${list ? (parts.length === 1 ? ` and ${list}` : `, ${list}`) : ''}.`
  if (impact.users_deleted === 0) sentence += ' No users are affected.'
  if (impact.power_admins_kept > 0) {
    sentence += ` ${n(impact.power_admins_kept, 'power admin')} in it ${impact.power_admins_kept === 1 ? 'keeps their account' : 'keep their accounts'}.`
  }
  return sentence
}
```

Run the test. If the project sentence differs only in its joining words, make the code produce exactly the test's string; the test is the spec here.

```ts
// frontend/src/lib/mediaLibrary.ts
import type { components } from '../api/schema'

export type MediaFile = components['schemas']['MediaFileOut']
export interface MediaFilter { usage: 'all' | 'unused'; kind: 'all' | 'image' | 'video' }

export const isUnused = (file: MediaFile) => file.used_in.length === 0 && file.proposals === 0

export function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1_048_576) return `${Math.round(bytes / 1024)} KB`
  const mb = bytes / 1_048_576
  return `${Number.isInteger(mb) ? mb : mb.toFixed(1)} MB`
}

export function mediaSummary(files: MediaFile[]): string {
  const unused = files.filter(isUnused)
  const total = files.reduce((s, f) => s + f.size_bytes, 0)
  const unusedTotal = unused.reduce((s, f) => s + f.size_bytes, 0)
  return `${files.length} file${files.length === 1 ? '' : 's'} · ${formatBytes(total)} · ${unused.length} unused (${formatBytes(unusedTotal)})`
}

export function filterMedia(files: MediaFile[], filter: MediaFilter): MediaFile[] {
  return files.filter(f => (filter.usage === 'all' || isUnused(f)) && (filter.kind === 'all' || f.kind === filter.kind))
}
```

Hooks in `admin2/api.ts`: follow the existing patterns (`client.PUT/PATCH/DELETE/GET`, `errorMessage`, invalidation):
- `useMoveUser` invalidates `['admin','users']` and `['admin','dashboard']`;
- the renames and deletes invalidate `['admin','companies']`;
- `useDeleteMedia` invalidates `['admin','media']`;
- `useOrgImpact(kind, id)` is `enabled: id !== null`.

- [ ] **Step 3: Run, check, commit**

Run: `cd frontend && npm run gen:api && npx vitest run src/lib/orgImpact.test.ts src/lib/mediaLibrary.test.ts && npm run typecheck && npm run lint`.

```bash
git add frontend && git commit -m "feat(admin): housekeeping hooks, impact sentences, media helpers (B6, #147)"
```

---

### Task 6: Move dialog, Projects page rename/delete, Companies section

**Files:**
- Create: `frontend/src/pages/admin2/MoveUserDialog.tsx`, `frontend/src/pages/admin2/OrgDeleteDialog.tsx`
- Modify: `frontend/src/pages/admin2/UserDetailPage.tsx`, `frontend/src/pages/admin2/ProjectsPage.tsx`
- Test: `frontend/src/pages/admin2/Housekeeping.test.tsx`

**Interfaces:**
- `MoveUserDialog({ userId, currentProjectId, holdsGrantOn: string[], onClose })`: a kit `Modal` with a "Company · Project" `<select>`, a note on what changes, a warning line when the chosen project is in `holdsGrantOn`, and **Move**.
- `OrgDeleteDialog({ kind, id, name, onClose, onDeleted })`: a `Modal` that loads `useOrgImpact`, shows `impactSentence`, and has a `ConfirmButton` "Delete {kind}" / "Yes, delete".

- [ ] **Step 1: Failing page tests**

```tsx
// frontend/src/pages/admin2/Housekeeping.test.tsx
// Covers: MoveUserDialog, OrgDeleteDialog, and the Projects page scope reset.
```

Write three tests, mocking `../../api/client` as `ContentPage.test.tsx` does (GET/PUT/PATCH/DELETE `vi.fn()`s routed by path) and `../../contexts/AuthContext` with `{ isPowerAdmin: true, adminProjectIds: [], user: { id: 'me' } }`:
1. **`moves a user and warns about a grant on the destination`:** render `MoveUserDialog` with `holdsGrantOn={['p2']}`. Pick p2 and see "administers this project" text. Click **Move** and assert `PUT('/api/admin/users/{user_id}/project', { params: { path: { user_id: 'u1' } }, body: { project_id: 'p2' } })`.
2. **`shows the impact and needs two clicks to delete`:** render `OrgDeleteDialog` for a project with the impact GET answering the Task 5 project example. Assert the exact `impactSentence` text. Click "Delete project", assert there's no DELETE yet, click "Yes, delete", and assert `DELETE('/api/admin/projects/{project_id}', …)`.
3. **`resets the scope when the scoped project is deleted`:** render `ProjectsPage` inside `MemoryRouter initialEntries={['/admin/projects?project=p1']}`, delete p1 through its card, and assert the URL search no longer has `project=p1`. Use a location probe component that renders `useLocation().search`.

Run: expected FAIL (modules missing).

- [ ] **Step 2: Implement**

- **`MoveUserDialog`:**
  - projects come from `useCompanies()`, flattened to `{id, label: "Company · Project"}`, excluding `currentProjectId`;
  - the explanatory text: "Their assignments, progress, assessment and interview stay. The new project's locks, AI settings and email templates apply from now on.";
  - the grant warning: "They administer this project; that grant is removed, because staff aren't learners of the project they run.";
  - on success `onClose()`.
- **`UserDetailPage`:** for power admins, add an account row "Project: {company · project}" with a **Move…** button opening the dialog. `holdsGrantOn` comes from the user's `admin_project_ids` (already on the enriched user).
- **`OrgDeleteDialog`:** while impact loads, show a `Spinner`; on error, `ErrorState`. The confirm calls `useDeleteOrg().mutate({ kind, id })`, then `onDeleted()`.
- **`ProjectsPage`** (power admins only):
  - each project card's actions gain **Rename** (an inline input in the card header, saved with Enter or a **Save** button) and **Delete…** (opens `OrgDeleteDialog`);
  - `onDeleted`: if `scope.projectId === id`, call `scope.setProject(null, { replace: true })`;
  - a new **Companies** card at the top (power only) lists each company with **Rename** and **Delete…** (kind `company`), with the same scope reset when the scoped project belonged to it.

- [ ] **Step 3: Run, check, commit**

Run: `cd frontend && npx vitest run src/pages/admin2/Housekeeping.test.tsx src/pages/admin2 && npm run typecheck && npm run lint`.

```bash
git add frontend && git commit -m "feat(admin): move user, rename/delete projects and companies (B6, #147, #111)"
```

---

### Task 7: Media page

**Files:**
- Create: `frontend/src/pages/admin2/MediaPage.tsx` (+ `MediaPage.test.tsx`)
- Modify: `frontend/src/pages/admin2/nav.ts` (`{ key: 'media', label: 'Media', icon: 'folder', path: 'media', powerOnly: true }` after `content`), `frontend/src/App.tsx` (lazy route `media`, wrapped in `powerOnly(...)`), `frontend/src/pages/admin2/adminAccess.test.ts` (power admin nav count +1)

- [ ] **Step 1: Failing test**

Mock the client GET for `/api/admin/media` with two files, one used (`used_in` one lesson) and one unused. Assert:
- the summary line;
- the "Used in: L" link points to `/learning/lesson/{lesson_id}?edit=true`;
- the unused row has **Delete** and the used row doesn't;
- the **Unused** filter hides the used row;
- Delete → "Yes, delete" calls `DELETE('/api/admin/media/{kind}/{name}', { params: { path: { kind: 'videos', name: 'b…b.mp4' } } })`.

- [ ] **Step 2: Implement**

A kit `Card` with:
- the `mediaSummary` line;
- two pill groups (All / Unused; All / Images / Videos);
- a `Table` with these columns:
  - thumbnail: `<img src={preview_url}>`, 48 px, or a "▶ video" chip;
  - file name: the part after `/`;
  - type;
  - size (`formatBytes`);
  - uploaded (`formatDate`);
  - "Used in": lesson links, plus "+N AI proposals", or an **Unused** chip;
  - actions: `ConfirmButton` "Delete" on unused rows only.

A 409 from delete shows its message in an `adm-form-msg-err` with `role="alert"`. While loading show a `Spinner`; on error, `ErrorState` (a 404 there means storage isn't configured: show "Media storage isn't configured.").

- [ ] **Step 3: Run, check, commit**

Run: `npx vitest run src/pages/admin2/MediaPage.test.tsx src/pages/admin2/adminAccess.test.ts && npm run typecheck && npm run lint`.

```bash
git add frontend && git commit -m "feat(admin): Media page — files, where used, delete unused (B6, #147)"
```

---

### Task 8: Docs, full checks, review, PR

- [ ] **Step 1: Docs**
  - `docs/feature-index.md`: add "**Admin housekeeping** (#147, #111, B6): move a user, rename/delete projects and companies (deletes their users; power admins kept), media library; `2026-10-06-admin-housekeeping-design.md`; `services/org_deletion_service.py`, `services/media_usage_service.py`, `frontend/src/pages/admin2/MediaPage.tsx`."
  - `SECURITY.md` → "Admin access to learner data": add a paragraph saying a power admin can delete a project or company, and with it every member's account and learner data (progress, assessments, interviews). Power admins are kept. Recovery is only the nightly backup (`docs/db-backup-restore.md`). Each delete logs ids and counts.
- [ ] **Step 2: Full checks**
  - Backend: `uv run poe format-check && uv run poe lint-src && uv run poe ty-src && uv run poe test`.
  - Frontend: `npm run typecheck && npm run lint && npm test && npm run build`.
- [ ] **Step 3: Commit the docs**, then one strong-model review of the whole branch with the spec, this plan and the Review Focus. Fix real findings with a failing test first.
- [ ] **Step 4: PR**

`git push -u origin feat/admin-housekeeping`, then `gh pr create --base main` with `Closes #147` and `Closes #111`. The body covers:
- what changed;
- tests;
- that there's no migration;
- the risk note (deletes are permanent).

End it with `🤖 Generated with [Claude Code](https://claude.com/claude-code)`.
