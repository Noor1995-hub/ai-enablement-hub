# Lesson Feedback Button + Popup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a floating "Feedback" pill on the lesson learner view that opens a "Share feedback" popup (lesson title + free-text box + Send), persisting each submission to a new `feedback` table.

**Architecture:** Backend follows the mandatory delaware layering — Pydantic schema → `POST /api/feedback` router → `FeedbackService` → `FeedbackRepository` → `Feedback` model, with a new Alembic migration. Frontend adds one self-contained `LessonFeedback` component rendered only in the learner-view branch of `LessonPage`.

**Tech Stack:** FastAPI (Python 3.13, uv, SQLAlchemy async, Alembic, Pydantic v2, pytest/pytest-asyncio), React 18 + TypeScript (Vite, openapi-fetch), Azure PostgreSQL.

**Spec:** `docs/superpowers/specs/2026-07-14-lesson-feedback-design.md`

## Global Constraints

- Backend layering is mandatory (`python-be-architecture.md`): router → service → repository → model; DI providers in `core/dependencies/domain.py`.
- **Iron rule:** no endpoint outside `/admin/*` accepts a user identifier from the request — the user id comes from the token only. `lesson_id` in the body is a resource id and is allowed.
- Accent color everywhere in this feature: `--dlw-primary-red` = `#C42828`.
- Message length cap: `max_length=4000`; empty/whitespace-only rejected in the **Pydantic schema** (→ 422), not the service.
- Endpoint returns **201 Created**.
- `asyncio_mode = "auto"` — async tests need no `@pytest.mark.asyncio` marker.
- Backend gate after each task: `cd backend && uv run poe format && uv run poe lint && uv run poe test` — all green, coverage ≥80%, ruff/ty clean.
- Frontend gate: `cd frontend && npm run typecheck && npm run lint && npm run build` — all green.
- Every git commit message ends with the trailer:
  `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`
- **Do NOT** mutate any Azure DB unattended: applying the migration to the dev/prod app DB, running the dev backend for `gen:api` (triggers a real cleanup DELETE), and `deploy.ps1` are approval gates (see Tasks B1 / C1). Running `poe test` against the dedicated `ai-enablement-hub-test` DB is the normal dev loop and is fine.

## Before you start

- [ ] **Create a feature branch** (repo root `AI ENABLEMENT HUB REBUILD/`). The tree is on `main` and a colleague pushes to `origin/main`; never commit to `main` directly, never push without asking.

```bash
cd "AI ENABLEMENT HUB REBUILD"
git fetch origin
git checkout -b feature/lesson-feedback
```

---

## Phase A — Backend (persistence + API). No Azure DB mutation.

### Task 1: Feedback request/response schema (Phase A)

**Files:**
- Create: `backend/src/schemas/feedback.py`
- Test: `backend/tests/unit/test_feedback_schema.py`

**Interfaces:**
- Produces: `FeedbackCreate { lesson_id: uuid.UUID; message: str }` (message stripped, non-empty, ≤4000) and `FeedbackResponse { id: uuid.UUID; created_at: datetime }` (`from_attributes=True`).

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/unit/test_feedback_schema.py
from __future__ import annotations

import uuid

import pytest
from pydantic import ValidationError

from src.schemas.feedback import FeedbackCreate


def test_strips_and_accepts_message() -> None:
    model = FeedbackCreate(lesson_id=uuid.uuid4(), message="  needs an example  ")
    assert model.message == "needs an example"


def test_rejects_empty_message() -> None:
    with pytest.raises(ValidationError):
        FeedbackCreate(lesson_id=uuid.uuid4(), message="")


def test_rejects_whitespace_only_message() -> None:
    with pytest.raises(ValidationError):
        FeedbackCreate(lesson_id=uuid.uuid4(), message="   \n\t ")


def test_rejects_oversized_message() -> None:
    with pytest.raises(ValidationError):
        FeedbackCreate(lesson_id=uuid.uuid4(), message="x" * 4001)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/unit/test_feedback_schema.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.schemas.feedback'`

- [ ] **Step 3: Write minimal implementation**

```python
# backend/src/schemas/feedback.py
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

__all__ = ["FeedbackCreate", "FeedbackResponse"]


class FeedbackCreate(BaseModel):
    lesson_id: uuid.UUID
    message: str = Field(max_length=4000)

    @field_validator("message")
    @classmethod
    def _strip_non_empty(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            msg = "message must not be empty"
            raise ValueError(msg)
        return stripped


class FeedbackResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    created_at: datetime
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && uv run pytest tests/unit/test_feedback_schema.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add backend/src/schemas/feedback.py backend/tests/unit/test_feedback_schema.py
git commit -m "feat(feedback): add FeedbackCreate/FeedbackResponse schema"
```

---

### Task 2: Model, repository, service, DI wiring (Phase A)

**Files:**
- Create: `backend/src/db/models/feedback.py`
- Modify: `backend/src/db/models/__init__.py` (register `Feedback`)
- Modify: `backend/src/repositories/base.py` (add `AbstractFeedbackRepository`)
- Create: `backend/src/repositories/feedback_repository.py`
- Create: `backend/src/services/feedback_service.py`
- Modify: `backend/src/core/dependencies/domain.py` (add repo + service providers)
- Test: `backend/tests/unit/test_feedback_service.py`

**Interfaces:**
- Consumes: `AbstractContentRepository.get_lesson(lesson_id) -> Lesson | None` (existing).
- Produces:
  - `Feedback` model — columns `id, user_id, lesson_id, message, created_at`.
  - `AbstractFeedbackRepository.create(user_id: uuid.UUID, lesson_id: uuid.UUID, message: str) -> Feedback`.
  - `FeedbackService(feedback: AbstractFeedbackRepository, content: AbstractContentRepository)` with `async submit(user_id: uuid.UUID, lesson_id: uuid.UUID, message: str) -> Feedback` (raises `NotFoundError("Lesson")` when the lesson is unknown).
  - DI: `get_feedback_repository`, `get_feedback_service`.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/unit/test_feedback_service.py
from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from src.repositories.base import AbstractContentRepository, AbstractFeedbackRepository
from src.services.exceptions import NotFoundError
from src.services.feedback_service import FeedbackService


def _service(*, lesson: object | None) -> tuple[FeedbackService, AsyncMock]:
    feedback = AsyncMock(spec=AbstractFeedbackRepository)
    feedback.create.return_value = SimpleNamespace(id=uuid.uuid4())
    content = AsyncMock(spec=AbstractContentRepository)
    content.get_lesson.return_value = lesson
    return FeedbackService(feedback, content), feedback


async def test_submit_persists_when_lesson_exists() -> None:
    service, feedback = _service(lesson=SimpleNamespace(id=uuid.uuid4()))
    user_id, lesson_id = uuid.uuid4(), uuid.uuid4()

    await service.submit(user_id, lesson_id, "great lesson")

    feedback.create.assert_awaited_once_with(user_id, lesson_id, "great lesson")


async def test_submit_unknown_lesson_raises_not_found() -> None:
    service, feedback = _service(lesson=None)

    with pytest.raises(NotFoundError):
        await service.submit(uuid.uuid4(), uuid.uuid4(), "hello")

    feedback.create.assert_not_awaited()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/unit/test_feedback_service.py -v`
Expected: FAIL — `ImportError` (`AbstractFeedbackRepository` / `FeedbackService` do not exist)

- [ ] **Step 3a: Create the model**

```python
# backend/src/db/models/feedback.py
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Text, func, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base

__all__ = ["Feedback"]


class Feedback(Base):
    __tablename__ = "feedback"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    lesson_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("lessons.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    message: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
```

- [ ] **Step 3b: Register the model** in `backend/src/db/models/__init__.py` — add the import and the `__all__` entry (keep alphabetical):

```python
from src.db.models.company import Company, Project, ProjectComponentSetting
from src.db.models.feedback import Feedback
from src.db.models.learning import Curriculum, Lesson, Module, ModulePrerequisite, Track
```

and in `__all__`, add `"Feedback",` between `"Curriculum",` and `"Lesson",`.

- [ ] **Step 3c: Add the abstract repository** to `backend/src/repositories/base.py`.
  In the `TYPE_CHECKING` import block, add `Feedback,` (keep alphabetical, before `Lesson`).
  In `__all__`, add `"AbstractFeedbackRepository",` (before `"AbstractOrgRepository"`).
  Add the class (place it after `AbstractContentRepository`):

```python
class AbstractFeedbackRepository(ABC):
    """feedback — free-text lesson feedback (one row per submission)."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @abstractmethod
    async def create(
        self, user_id: uuid.UUID, lesson_id: uuid.UUID, message: str
    ) -> Feedback: ...
```

- [ ] **Step 3d: Create the concrete repository**

```python
# backend/src/repositories/feedback_repository.py
from __future__ import annotations

import uuid

from src.db.models import Feedback
from src.repositories.base import AbstractFeedbackRepository

__all__ = ["FeedbackRepository"]


class FeedbackRepository(AbstractFeedbackRepository):
    async def create(
        self, user_id: uuid.UUID, lesson_id: uuid.UUID, message: str
    ) -> Feedback:
        feedback = Feedback(user_id=user_id, lesson_id=lesson_id, message=message)
        self._session.add(feedback)
        await self._session.commit()
        await self._session.refresh(feedback)
        return feedback
```

- [ ] **Step 3e: Create the service**

```python
# backend/src/services/feedback_service.py
from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from src.services.exceptions import NotFoundError

if TYPE_CHECKING:
    from src.db.models import Feedback
    from src.repositories.base import (
        AbstractContentRepository,
        AbstractFeedbackRepository,
    )

__all__ = ["FeedbackService"]


class FeedbackService:
    """Persists learner feedback on a lesson after verifying the lesson exists."""

    def __init__(
        self,
        feedback: AbstractFeedbackRepository,
        content: AbstractContentRepository,
    ) -> None:
        self._feedback = feedback
        self._content = content

    async def submit(
        self, user_id: uuid.UUID, lesson_id: uuid.UUID, message: str
    ) -> Feedback:
        if await self._content.get_lesson(lesson_id) is None:
            raise NotFoundError("Lesson")
        return await self._feedback.create(user_id, lesson_id, message)
```

- [ ] **Step 3f: Wire DI** in `backend/src/core/dependencies/domain.py`.
  Add exactly two NEW import lines (the surrounding lines already exist — shown only for placement, do not duplicate them):

```python
from src.repositories.content_repository import ContentRepository
from src.repositories.feedback_repository import FeedbackRepository  # NEW
from src.repositories.org_repository import OrgRepository
```
```python
from src.services.content_service import ContentService
from src.services.feedback_service import FeedbackService  # NEW
from src.services.learning_service import LearningService
```

  Add to `__all__`: `"get_feedback_repository",` and `"get_feedback_service",`.
  Add the providers (place after `get_content_service`):

```python
def get_feedback_repository(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> FeedbackRepository:
    return FeedbackRepository(session)


def get_feedback_service(
    feedback: Annotated[FeedbackRepository, Depends(get_feedback_repository)],
    content: Annotated[ContentRepository, Depends(get_content_repository)],
) -> FeedbackService:
    return FeedbackService(feedback, content)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && uv run pytest tests/unit/test_feedback_service.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Full backend gate + commit**

```bash
cd backend && uv run poe format && uv run poe lint && uv run poe test
```
Expected: all green (existing suite still imports `src.main` cleanly; the new model builds a `feedback` table in the test DB via `Base.metadata.create_all`).

```bash
cd ..
git add backend/src/db/models/feedback.py backend/src/db/models/__init__.py \
  backend/src/repositories/base.py backend/src/repositories/feedback_repository.py \
  backend/src/services/feedback_service.py backend/src/core/dependencies/domain.py \
  backend/tests/unit/test_feedback_service.py
git commit -m "feat(feedback): add Feedback model, repository, service, DI"
```

---

### Task 3: POST /api/feedback router + integration tests + authz (Phase A)

**Files:**
- Create: `backend/src/routers/feedback.py`
- Modify: `backend/src/main.py` (import + `include_router`)
- Create: `backend/tests/integration/test_routers/test_feedback.py`
- Modify: `backend/tests/integration/test_routers/test_authz.py` (add one `_MATRIX` row)

**Interfaces:**
- Consumes: `get_current_user` (auth), `get_feedback_service`, `FeedbackCreate`, `FeedbackResponse`.
- Produces: `POST /api/feedback` → 201 `FeedbackResponse`; 401 anonymous, 422 bad message, 404 unknown lesson.

- [ ] **Step 1: Write the failing integration test**

```python
# backend/tests/integration/test_routers/test_feedback.py
from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import select

from src.db.models import Feedback
from tests.fixtures.auth import auth_headers
from tests.fixtures.factories import create_lesson, create_module, create_track, create_user

if TYPE_CHECKING:
    from httpx import AsyncClient
    from sqlalchemy.ext.asyncio import AsyncSession

    from src.core.configs.settings import Settings


class TestSubmitFeedback:
    async def test_creates_row_and_returns_201(
        self, client: AsyncClient, db_session: AsyncSession, test_settings: Settings
    ) -> None:
        track = await create_track(db_session)
        module = await create_module(db_session, track)
        lesson = await create_lesson(db_session, module, "Prompting basics")
        user = await create_user(db_session, email="fb-user@example.com")

        response = await client.post(
            "/api/feedback",
            json={"lesson_id": str(lesson.id), "message": "  needs an example  "},
            headers=auth_headers(user, test_settings),
        )

        assert response.status_code == 201
        payload = response.json()
        assert set(payload) == {"id", "created_at"}

        rows = (
            await db_session.execute(select(Feedback).where(Feedback.id == uuid.UUID(payload["id"])))
        ).scalars().all()
        assert len(rows) == 1
        assert rows[0].user_id == user.id
        assert rows[0].lesson_id == lesson.id
        assert rows[0].message == "needs an example"  # stored stripped

    async def test_anonymous_is_401(self, client: AsyncClient) -> None:
        response = await client.post(
            "/api/feedback", json={"lesson_id": str(uuid.uuid4()), "message": "hi"}
        )
        assert response.status_code == 401

    async def test_empty_message_is_422(
        self, client: AsyncClient, db_session: AsyncSession, test_settings: Settings
    ) -> None:
        user = await create_user(db_session, email="fb-empty@example.com")
        response = await client.post(
            "/api/feedback",
            json={"lesson_id": str(uuid.uuid4()), "message": "   "},
            headers=auth_headers(user, test_settings),
        )
        assert response.status_code == 422

    async def test_oversized_message_is_422(
        self, client: AsyncClient, db_session: AsyncSession, test_settings: Settings
    ) -> None:
        user = await create_user(db_session, email="fb-big@example.com")
        response = await client.post(
            "/api/feedback",
            json={"lesson_id": str(uuid.uuid4()), "message": "x" * 4001},
            headers=auth_headers(user, test_settings),
        )
        assert response.status_code == 422

    async def test_unknown_lesson_is_404(
        self, client: AsyncClient, db_session: AsyncSession, test_settings: Settings
    ) -> None:
        user = await create_user(db_session, email="fb-404@example.com")
        response = await client.post(
            "/api/feedback",
            json={"lesson_id": str(uuid.uuid4()), "message": "hi"},
            headers=auth_headers(user, test_settings),
        )
        assert response.status_code == 404
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/integration/test_routers/test_feedback.py -v`
Expected: FAIL — all POSTs return 404 (route not registered) / import of nothing new fails; the 201 test fails first.

- [ ] **Step 3a: Create the router**

```python
# backend/src/routers/feedback.py
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status

from src.core.dependencies.auth import get_current_user
from src.core.dependencies.domain import get_feedback_service
from src.db.models import User
from src.schemas.feedback import FeedbackCreate, FeedbackResponse
from src.services.feedback_service import FeedbackService

__all__ = ["router"]

router = APIRouter(prefix="/api/feedback", tags=["feedback"])

CurrentUserDep = Annotated[User, Depends(get_current_user)]


@router.post("", response_model=FeedbackResponse, status_code=status.HTTP_201_CREATED)
async def submit_feedback(
    user: CurrentUserDep,
    body: FeedbackCreate,
    feedback_service: Annotated[FeedbackService, Depends(get_feedback_service)],
) -> FeedbackResponse:
    feedback = await feedback_service.submit(user.id, body.lesson_id, body.message)
    return FeedbackResponse.model_validate(feedback)
```

- [ ] **Step 3b: Register the router** in `backend/src/main.py`.
  Add `feedback` to the router import tuple (keep alphabetical):

```python
from src.routers import (
    admin_content,
    admin_media,
    admin_org,
    admin_users,
    auth,
    auth_entra,
    feedback,
    learning,
    me,
    survey,
)
```

  Add the include after `admin_media` (near line 179):

```python
app.include_router(admin_media.router)
app.include_router(feedback.router)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && uv run pytest tests/integration/test_routers/test_feedback.py -v`
Expected: PASS (5 passed)

- [ ] **Step 5: Add the authz-matrix row** in `backend/tests/integration/test_routers/test_authz.py`.
  Insert into the `_MATRIX` list (e.g. right after the `("lesson", ...)` row) — an authenticated, non-admin endpoint:

```python
    (
        "feedback",
        "POST",
        lambda s: "/api/feedback",
        lambda s: {"lesson_id": str(s.lesson.id), "message": "Great lesson"},
        False,
    ),
```

- [ ] **Step 6: Run the authz matrix to verify it passes**

Run: `cd backend && uv run pytest "tests/integration/test_routers/test_authz.py::test_matrix[feedback]" tests/integration/test_routers/test_authz.py::TestIronRule -v`
Expected: PASS — anonymous→401, user→201, admin→201; the iron-rule scan still finds no `user_id` on `/api/feedback` (the body is `lesson_id` + `message`).

- [ ] **Step 7: Full backend gate + commit**

```bash
cd backend && uv run poe format && uv run poe lint && uv run poe test
cd ..
git add backend/src/routers/feedback.py backend/src/main.py \
  backend/tests/integration/test_routers/test_feedback.py \
  backend/tests/integration/test_routers/test_authz.py
git commit -m "feat(feedback): add POST /api/feedback endpoint + authz"
```
Expected: all green.

---

### Task 4: Alembic migration — file only, not applied (Phase A)

**Files:**
- Create: `backend/alembic/versions/f1a2b3c4d5e6_feedback.py`

**Interfaces:**
- Produces migration revision `f1a2b3c4d5e6`, `down_revision = "e1f2a3b4c5d6"` (current head).

- [ ] **Step 1: Create the migration**

```python
# backend/alembic/versions/f1a2b3c4d5e6_feedback.py
"""feedback — free-text lesson feedback

One row per submission (user + lesson + message). CASCADE on both FKs so a
deleted user or lesson takes its feedback with it. Indexed on lesson_id for
future per-lesson reads.

Revision ID: f1a2b3c4d5e6
Revises: e1f2a3b4c5d6
Create Date: 2026-07-14

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "f1a2b3c4d5e6"
down_revision: str | None = "e1f2a3b4c5d6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "feedback",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("lesson_id", sa.UUID(), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["lesson_id"],
            ["lessons.id"],
            name=op.f("fk_feedback_lesson_id_lessons"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_feedback_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_feedback")),
    )
    op.create_index(op.f("ix_feedback_lesson_id"), "feedback", ["lesson_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_feedback_lesson_id"), table_name="feedback")
    op.drop_table("feedback")
```

- [ ] **Step 2: Verify the migration chain offline (no DB connection)**

Run: `cd backend && uv run alembic heads`
Expected: exactly one head — `f1a2b3c4d5e6 (head)`. (`alembic heads` reads the versions directory only; it does not connect to any database. A syntax/chain error here fails loudly.)

- [ ] **Step 3: Commit**

```bash
cd ..
git add backend/alembic/versions/f1a2b3c4d5e6_feedback.py
git commit -m "feat(feedback): add feedback table migration"
```

**Phase A handoff checkpoint (record before stopping):** files created/modified; total backend test count + result; migration revision `f1a2b3c4d5e6`; note "migration NOT applied to any DB". To resume Phase B, read: this plan, `backend/src/schemas/feedback.py` (exact body shape), `frontend/src/pages/LessonPage.tsx`, `frontend/src/api/client.ts`, `frontend/src/index.css`.

---

## Phase B — Frontend (component + wiring)

### Task 5: Regenerate API types for POST /api/feedback (Phase B)  ⛔ APPROVAL GATE

**Files:**
- Modify: `frontend/src/api/schema.d.ts` (generated)

- [ ] **Step 1: Ask the user before regenerating.** `npm run gen:api` requires the dev backend running against the Azure dev DB, and starting it runs the daily auth-cleanup DELETE against that DB (documented in `CLAUDE.md`). Ask: "OK to launch the dev backend to regenerate `schema.d.ts`? It runs a cleanup DELETE on the Azure dev DB." If **no**, use the hand-patch fallback in Step 3.

- [ ] **Step 2 (preferred, on approval): Regenerate.**

```bash
cd backend && uv run uvicorn src.main:app --port 8000 &
# wait until http://localhost:8000/api/health is 200, then:
cd ../frontend && npm run gen:api
# stop the backend afterward
```

- [ ] **Step 3 (fallback, if not approved): Hand-patch `frontend/src/api/schema.d.ts`.**
  Add a `"/api/feedback"` path with a `post` operation whose `requestBody` references a new `FeedbackCreate` schema (`{ lesson_id: string; message: string }`, both required) and whose 201 response references `FeedbackResponse` (`{ id: string; created_at: string }`). Mirror the shape of an existing POST entry (e.g. `/api/admin/tracks`) for exact typing conventions. Add a `// TODO: regenerate via npm run gen:api` note.

- [ ] **Step 4: Verify the type exists.**

Run: `cd frontend && npm run typecheck`
Expected: PASS. Confirm `grep -c "/api/feedback" src/api/schema.d.ts` returns ≥1.

- [ ] **Step 5: Commit**

```bash
cd ..
git add frontend/src/api/schema.d.ts
git commit -m "feat(feedback): add /api/feedback to generated API types"
```

---

### Task 6: LessonFeedback component + LessonPage wiring (Phase B)

**Files:**
- Create: `frontend/src/components/LessonFeedback.tsx`
- Modify: `frontend/src/pages/LessonPage.tsx` (import + render in learner-view branch)

**Interfaces:**
- Consumes: `client.POST('/api/feedback', { body: { lesson_id, message } })`; `lesson.id`, `lesson.title` from `LessonPage`.
- Produces: default-exported `LessonFeedback({ lessonId, lessonTitle })`.

- [ ] **Step 1: Create the component**

```tsx
// frontend/src/components/LessonFeedback.tsx
import { useEffect, useRef, useState } from 'react'
import { client } from '../api/client'

type Status = 'idle' | 'sending' | 'sent' | 'error'

const RED = '#C42828'

export default function LessonFeedback({
  lessonId,
  lessonTitle,
}: {
  lessonId: string
  lessonTitle: string
}) {
  const [open, setOpen]       = useState(false)
  const [message, setMessage] = useState('')
  const [status, setStatus]   = useState<Status>('idle')
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  function close() {
    setOpen(false)
    setMessage('')
    setStatus('idle')
  }

  // Focus the textarea on open; Escape closes the popup.
  useEffect(() => {
    if (!open) return
    textareaRef.current?.focus()
    function onKey(e: KeyboardEvent) {
      if (e.key === 'Escape') close()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [open])

  async function send() {
    const trimmed = message.trim()
    if (!trimmed || status === 'sending') return
    setStatus('sending')
    const { error } = await client.POST('/api/feedback', {
      body: { lesson_id: lessonId, message: trimmed },
    })
    setStatus(error ? 'error' : 'sent')
  }

  const canSend = message.trim().length > 0 && status !== 'sending'

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="lesson-cta"
        aria-label="Share feedback"
        style={{
          position: 'fixed', bottom: 24, right: 24, zIndex: 50,
          padding: '11px 22px', borderRadius: 999, border: 'none',
          background: RED, color: '#fff',
          fontFamily: 'var(--dlw-font-body)', fontWeight: 800, fontSize: 14,
          cursor: 'pointer', boxShadow: 'var(--dlw-shadow-lg)',
          transition: 'background 180ms',
        }}
      >
        Feedback
      </button>

      {open && (
        <div
          onClick={close}
          style={{
            position: 'fixed', inset: 0, zIndex: 1000,
            background: 'rgba(16,24,32,.45)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            padding: 20,
          }}
        >
          <div
            onClick={e => e.stopPropagation()}
            role="dialog"
            aria-modal="true"
            aria-label="Share feedback"
            style={{
              width: '100%', maxWidth: 440, background: '#fff',
              borderRadius: 'var(--dlw-radius-xl)', boxShadow: 'var(--dlw-shadow-lg)',
              padding: 24, fontFamily: 'var(--dlw-font-body)',
            }}
          >
            {status === 'sent' ? (
              <div style={{ textAlign: 'center', padding: '12px 0' }}>
                <p style={{ margin: '0 0 18px', fontSize: 15, fontWeight: 600, color: '#101820' }}>
                  Thanks — your feedback was sent.
                </p>
                <button
                  type="button"
                  onClick={close}
                  style={{
                    padding: '10px 22px', borderRadius: 8, border: 'none',
                    background: RED, color: '#fff', fontFamily: 'var(--dlw-font-body)',
                    fontWeight: 700, fontSize: 14, cursor: 'pointer',
                  }}
                >
                  Close
                </button>
              </div>
            ) : (
              <>
                <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: 4 }}>
                  <h2 style={{ margin: 0, fontSize: 18, fontWeight: 700, color: RED }}>
                    Share feedback
                  </h2>
                  <button
                    type="button"
                    onClick={close}
                    aria-label="Close"
                    style={{
                      background: 'none', border: 'none', cursor: 'pointer',
                      fontSize: 22, lineHeight: 1, color: '#8A8A8A', padding: 0,
                    }}
                  >
                    ×
                  </button>
                </div>
                <p style={{ margin: '0 0 14px', fontSize: 13, color: '#8A8A8A' }}>
                  {lessonTitle}
                </p>
                <textarea
                  ref={textareaRef}
                  value={message}
                  onChange={e => {
                    setMessage(e.target.value)
                    if (status === 'error') setStatus('idle')
                  }}
                  placeholder="What's on your mind?"
                  rows={5}
                  style={{
                    width: '100%', boxSizing: 'border-box', resize: 'vertical',
                    padding: '12px 14px', borderRadius: 10,
                    border: `1.5px solid ${RED}`, outline: 'none',
                    fontFamily: 'var(--dlw-font-body)', fontSize: 14, color: '#3C3C3C',
                    marginBottom: 14,
                  }}
                />
                {status === 'error' && (
                  <p style={{ margin: '0 0 12px', fontSize: 13, color: RED }}>
                    Couldn't send feedback. Please try again.
                  </p>
                )}
                <button
                  type="button"
                  onClick={send}
                  disabled={!canSend}
                  style={{
                    width: '100%', padding: '12px', borderRadius: 8, border: 'none',
                    background: canSend ? RED : '#E2E2E2',
                    color: canSend ? '#fff' : '#8A8A8A',
                    fontFamily: 'var(--dlw-font-body)', fontWeight: 800, fontSize: 14,
                    cursor: canSend ? 'pointer' : 'default',
                  }}
                >
                  {status === 'sending' ? 'Sending…' : 'Send feedback'}
                </button>
              </>
            )}
          </div>
        </div>
      )}
    </>
  )
}
```

- [ ] **Step 2: Wire it into `frontend/src/pages/LessonPage.tsx`.**
  Add the import near the other component imports (after `LessonEditor`):

```tsx
import LessonFeedback from '../components/LessonFeedback'
```

  In the learner-view branch (the final `) : (` block that renders `<aside>` + `<main>`), add the component immediately after the closing `</main>`, still inside that fragment:

```tsx
            </main>
            <LessonFeedback lessonId={lesson.id} lessonTitle={lesson.title} />
          </>
        )}
```
  (Do NOT add it to the `edit` or `mdx` branches — learner view only.)

- [ ] **Step 3: Frontend gate**

Run: `cd frontend && npm run typecheck && npm run lint && npm run build`
Expected: all green.

- [ ] **Step 4: Commit**

```bash
cd ..
git add frontend/src/components/LessonFeedback.tsx frontend/src/pages/LessonPage.tsx
git commit -m "feat(feedback): add LessonFeedback pill + popup to lesson page"
```

**Phase B handoff checkpoint (record):** component + wiring done; whether `schema.d.ts` was regenerated or hand-patched; whether the dev DB migration was applied yet (Phase C needs it). To resume Phase C, read: this plan.

---

## Phase C — End-to-end verification + deploy  ⛔ APPROVAL GATES

### Task 7: Verify against a real backend, then deploy (Phase C)  ⛔ APPROVAL GATES

- [ ] **Step 1: Apply the migration to the dev DB — ASK FIRST** (Azure mutation). On approval:

```bash
cd backend && uv run alembic upgrade head
```
Expected: `Running upgrade e1f2a3b4c5d6 -> f1a2b3c4d5e6`. Confirm the table:
`uv run alembic current` shows `f1a2b3c4d5e6 (head)`.

- [ ] **Step 2: Run locally and browser-verify** (use the `/run` or `/verify` skill). Start backend (`uvicorn src.main:app --port 8000`) + frontend (`npm run dev`). As a **non-admin** learner, open a lesson and confirm:
  - the red "Feedback" pill is fixed bottom-right;
  - clicking opens the popup with the **lesson title** as the subtitle;
  - Send is disabled until text is entered; sending shows "Sending…" then the "Thanks" confirmation;
  - Escape and backdrop-click close the popup;
  - a row appears in `feedback` (SQL: `SELECT user_id, lesson_id, message FROM feedback ORDER BY created_at DESC LIMIT 1;`).

- [ ] **Step 3: Deploy — ASK FIRST** (outward-facing). On approval, from the repo root:

```bash
./deploy.ps1
```
The prod DB migrates automatically on container start (`startup.py` runs `alembic upgrade`). After deploy, confirm `/api/health` is green and a submission on the live URL lands a row.

- [ ] **Step 4: Finish the branch.** Invoke `superpowers:finishing-a-development-branch` to choose merge/PR. Do not push without the user's go-ahead (a colleague pushes to `origin/main`; fetch/rebase first).

**Phase C handoff checkpoint (record):** browser results; deploy image tag + revision; prod migration head after deploy; follow-ups (e.g. admin viewer to read feedback).

---

## Self-review notes (author)

- **Spec coverage:** DB-only storage (A2/A4), `#C42828` accent (B2), learner-view-only pill (B2 Step 2), lesson-title subtitle (B2), no counter (B2), 422-via-Pydantic (A1), 404 unknown lesson (A2/A3), authz non-admin (A3), CASCADE FKs + lesson_id index (A2 model + A4 migration), zoom (no compensation — B2 uses plain fixed offsets). All mapped.
- **No user_id in body** (iron rule) — verified by the existing `TestIronRule` openapi scan (A3 Step 6).
- **Type consistency:** `submit(user_id, lesson_id, message)` and `create(user_id, lesson_id, message)` signatures match across service, repo, router, and both tests; `FeedbackResponse` fields (`id`, `created_at`) match the model columns and the 201 test assertion.
