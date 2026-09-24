# Plan — Database robustness (Batch 6 of CODE-REVIEW-2026-07-31.md)

**Goal:** close every database-layer finding in Batch 6 of `CODE-REVIEW-2026-07-31.md`: make the
survey seed repairable instead of permanently half-written, introduce a real unit-of-work seam for the
two multi-write flows that need atomicity, add the missing FK index and the missing DB-level guards,
remove the drift between newer and older tables, and pay off the four query-efficiency carryovers.

**Architecture:** All schema changes ship as small, additive, forward-only Alembic revisions on one
linear chain off the current head `1cd2cc2d05a9` (verified single head 2026-07-31 by walking every
`down_revision` in `backend/alembic/versions/` — 17 revisions, one head, no branches). Code changes
stay inside the existing `routers/ -> services/ -> repositories/` layering: repositories keep owning
the session, and the new unit-of-work object is a *repository-layer* collaborator, so a service
calling `uow.commit()` is a downward call, not a service-to-service one. Each task is independently
shippable and ends in its own commit.

**Tech Stack:** Python 3.13, FastAPI, SQLAlchemy 2.x async (asyncpg), Alembic, Azure Database for
PostgreSQL, pytest + pytest-asyncio + pytest-xdist, ruff, poethepoet.

## Global Constraints

- **Layering is absolute.** `routers/ -> services/ -> repositories/`. A service must NEVER call
  another service (`python-be-architecture.md`). Where two services need the same derivation, the
  shared logic goes into a pure helper (`core/constants.py::advance_level`, `core/attention.py`) and
  each service assembles its own inputs — this is the accepted, documented duplication in
  `admin_user_service.py` and `dashboard_service.py`, and Task 4 follows the same precedent.
- **Backend verification after every task**, run from inside `backend/`:
  `uv run poe format && uv run poe lint && uv run poe test`
- **Migrations are applied with** `uv run poe upgrade` (from `backend/`), never by hand-written SQL.
  Check the resulting head with `uv run alembic current` before committing.
- **Integration tests do NOT run migrations.** `backend/tests/conftest.py:143-145` builds the test
  schema with `Base.metadata.drop_all` / `create_all` against the shared remote
  `ai-enablement-hub-test` database (each xdist worker in its own PG schema). **Consequence: every
  model change and its migration must agree exactly.** If a migration adds an index/constraint that
  the model does not declare, integration tests will pass against a schema prod does not have (or
  vice-versa) and the divergence is invisible. Every schema task below therefore changes the model
  *and* the migration in the same commit, and asserts the object exists via the model-built test
  schema.
- **PROD RUNS `alembic upgrade head` AUTOMATICALLY ON CONTAINER START, BEFORE THE PORT BINDS**
  (`backend/startup.py:16-18`; startup probe budget ≈245 s, `infra/containerapp.yaml:66-76`;
  `minReplicas: 1`). Therefore: (a) every migration must be fast and additive; (b) a migration that
  **raises** does not just fail — it prevents the new revision from ever serving traffic. Any
  migration whose success depends on the shape of live data (a new CHECK, a new UNIQUE index) MUST be
  preceded by the verification query given in its task, run against prod, with the result recorded in
  the commit message. Never "just try it and see".
- **Never write two Alembic heads.** Each schema task states its `revision` and `down_revision`
  literally. Ship them in the task order given; if you skip a task, re-parent the next one and say so
  in the commit message.
- All new DB objects follow `backend/src/db/base.py:8-14` naming (`ix_`/`uq_`/`ck_`/`fk_`/`pk_`).
- Timestamps are `DateTime(timezone=True)` with `server_default=func.now()`, matching every existing
  table.

---

### Task 1: Make the survey assessment seed self-healing (6.1a — urgent, no migration)

Today a crash between the four commits of `complete()` freezes a user in a half-seeded state
**forever**: `_seed_assignments` returns early whenever the user already has *any* track row, and the
survey is already `complete` so `complete()` refuses to re-run. Fix it by reordering two things so
the retry path exists and converges — no schema change, no new abstraction, shippable alone and
before the unit-of-work seam in Task 13.

**Files:**
- Modify: `backend/src/services/survey_service.py` (lines 48-75 `complete`, lines 77-128
  `_seed_assignments`)
- Create test: `backend/tests/unit/test_survey_service.py`

**Interfaces:**
- Consumes: `AbstractSurveyRepository.get_by_user_id/update`, `AbstractContentRepository.list_tracks/
  list_modules/list_lesson_summaries`, `AbstractAssignmentRepository.track_ids_for_user/
  set_user_tracks/set_user_modules/set_user_lessons`, `src.services.scoring.score_response`.
- Produces: unchanged public signatures — `SurveyService.complete(user_id: uuid.UUID) ->
  SurveyResponse`, `SurveyService._seed_assignments(user_id: uuid.UUID, score_level: str | None) ->
  None`. New invariant later tasks may rely on: **a non-empty `user_tracks` set for a user means the
  seed ran to completion**, because the track rows are written last.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/unit/test_survey_service.py`:

```python
from __future__ import annotations

import uuid
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock

import pytest

from src.repositories.base import (
    AbstractAssignmentRepository,
    AbstractContentRepository,
    AbstractSurveyRepository,
)
from src.services.survey_service import SurveyService

# A complete, valid answer set — scores to practitioner (mirrors
# tests/fixtures/factories.py::VALID_ANSWERS).
_ANSWERS: dict[str, Any] = {
    "c1_code": "HAVE",
    "c2_code": "HAVE",
    "c3_code": "HAVE",
    "c4_code": "PARTIAL",
    "c5_codes": ["KEPT_OUT"],
    "c6_code": "HAVE",
    "b_freq": "WEEKLY",
    "b_breadth": "SEVERAL",
}


def _row(status: str = "in_progress") -> Any:
    return SimpleNamespace(status=status, score_level=None, **_ANSWERS)


def _service(
    row: Any, *, tracks: list[Any], modules: list[Any], lessons: list[Any]
) -> tuple[SurveyService, AsyncMock, AsyncMock]:
    surveys = AsyncMock(spec=AbstractSurveyRepository)
    surveys.get_by_user_id.return_value = row
    surveys.update.return_value = row
    content = AsyncMock(spec=AbstractContentRepository)
    content.list_tracks.return_value = tracks
    content.list_modules.return_value = modules
    content.list_lesson_summaries.return_value = lessons
    assignments = AsyncMock(spec=AbstractAssignmentRepository)
    assignments.track_ids_for_user.return_value = set()
    return SurveyService(surveys, content, assignments), surveys, assignments


def _fixture_graph() -> tuple[list[Any], list[Any], list[Any]]:
    track = SimpleNamespace(
        id=uuid.uuid4(), required_level="explore", is_introduction=False, name="General I"
    )
    module = SimpleNamespace(id=uuid.uuid4(), track_id=track.id)
    lesson = SimpleNamespace(id=uuid.uuid4(), module_id=module.id)
    return [track], [module], [lesson]


async def test_track_rows_are_written_last_so_they_mark_the_seed_complete() -> None:
    """The track write is the completion marker `_seed_assignments` guards on, so
    it must land after the module and lesson writes."""
    tracks, modules, lessons = _fixture_graph()
    service, _surveys, assignments = _service(
        _row(), tracks=tracks, modules=modules, lessons=lessons
    )
    order: list[str] = []
    assignments.set_user_tracks.side_effect = lambda *a, **k: order.append("tracks")
    assignments.set_user_modules.side_effect = lambda *a, **k: order.append("modules")
    assignments.set_user_lessons.side_effect = lambda *a, **k: order.append("lessons")

    await service.complete(uuid.uuid4())

    assert order == ["modules", "lessons", "tracks"]


async def test_a_failed_seed_leaves_the_survey_in_progress_so_a_retry_can_heal_it() -> None:
    """If the seed blows up the survey must NOT be marked complete — otherwise
    complete() can never re-run and the partial assignment set is permanent."""
    tracks, modules, lessons = _fixture_graph()
    service, surveys, assignments = _service(
        _row(), tracks=tracks, modules=modules, lessons=lessons
    )
    assignments.set_user_tracks.side_effect = RuntimeError("connection reset")

    with pytest.raises(RuntimeError):
        await service.complete(uuid.uuid4())

    surveys.update.assert_not_awaited()


async def test_retry_after_a_partial_seed_reseeds_and_then_completes() -> None:
    """Second attempt: no track rows exist (they are written last), so the guard
    lets the seed run again — every insert is ON CONFLICT DO NOTHING, so it only
    adds what is missing — and the survey is marked complete."""
    tracks, modules, lessons = _fixture_graph()
    service, surveys, assignments = _service(
        _row(), tracks=tracks, modules=modules, lessons=lessons
    )

    await service.complete(uuid.uuid4())

    assignments.set_user_modules.assert_awaited_once()
    assignments.set_user_lessons.assert_awaited_once()
    assignments.set_user_tracks.assert_awaited_once()
    surveys.update.assert_awaited_once()
    assert surveys.update.await_args.args[1]["status"] == "complete"
```

- [ ] **Step 2: Run test to verify it fails**

```
cd backend
uv run pytest tests/unit/test_survey_service.py -v
```

Expected: `test_track_rows_are_written_last...` fails with
`AssertionError: assert ['tracks', 'modules', 'lessons'] == ['modules', 'lessons', 'tracks']`, and
`test_a_failed_seed_leaves_the_survey_in_progress...` fails with
`AssertionError: Expected 'update' to not have been awaited. Awaited 1 times.` (today `update` runs
before the seed).

- [ ] **Step 3: Write minimal implementation**

In `backend/src/services/survey_service.py`, replace the tail of `complete()` (currently lines 70-75):

```python
        now = datetime.now(UTC)
        # Seed BEFORE marking the survey complete. The seed is a multi-statement
        # write with no shared transaction (each repository call commits itself),
        # so the only way a partial seed can be repaired is for the survey to
        # stay `in_progress` on failure — then the learner's retry of
        # POST /api/survey/complete re-enters here and converges. Scoring is
        # pure and deterministic, so recomputing it on a retry is free.
        await self._seed_assignments(user_id, scores["score_level"])
        return await self._surveys.update(
            row, {**scores, "status": "complete", "completed_at": now, "scored_at": now}
        )
```

and replace the three write calls at the end of `_seed_assignments()` (currently lines 124-128):

```python
        # Order is load-bearing: the track rows are written LAST, which is what
        # makes the `track_ids_for_user` guard above a reliable "this seed already
        # finished" marker. A failure between these statements leaves no track
        # rows, so the retry path re-runs the whole seed; every insert is
        # ON CONFLICT DO NOTHING, so a re-run only ever adds what is missing and
        # can never clobber an admin's edits.
        if module_ids:
            await self._assignments.set_user_modules(user_id, module_ids, assigned=True)
        if lesson_ids:
            await self._assignments.set_user_lessons(user_id, lesson_ids, assigned=True)
        await self._assignments.set_user_tracks(user_id, track_ids, assigned=True)
```

Also extend the `_seed_assignments` docstring's "Seeds ONLY when the user has no track assignments
yet" paragraph with one sentence: `Because the track rows are written last, that guard doubles as the
"seed finished" marker — see the write order at the bottom of this method.`

- [ ] **Step 4: Run test to verify it passes**

```
cd backend
uv run pytest tests/unit/test_survey_service.py tests/integration/test_routers/test_survey_flow.py -v
uv run poe format && uv run poe lint && uv run poe test
```

`test_survey_flow.py::TestAutoAssignOnComplete` must stay green unchanged — in particular
`test_does_not_seed_when_user_already_has_an_assignment`, which is the behaviour the guard exists for
(the guard still runs before any write, so an admin-curated user is still skipped).

- [ ] **Step 5: Commit**

```
git add backend/src/services/survey_service.py backend/tests/unit/test_survey_service.py
git commit -m "$(cat <<'EOF'
Make the assessment seed self-healing after a partial failure

Review finding 6.1a. complete() committed the survey first and
_seed_assignments returned early on any existing track row, so a failure
between the seed's commits froze a user with tracks but no modules or
lessons permanently: the survey was already `complete` so complete()
refused to re-run, and any retry hit the guard.

Two reorderings, no schema change: seed before marking the survey
complete (a failure now leaves it `in_progress`, so a retry re-enters),
and write the track rows last (so the guard is a true "seed finished"
marker and a retry re-runs the whole additive seed).

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 2: Index `feedback.user_id` and the four SET NULL audit FKs (6.2 — migration 1/3)

**Live data:** creates five B-tree indexes. Purely additive, writes no rows, changes no row. `feedback`
and the three review tables are small (hundreds of rows), so `CREATE INDEX` takes milliseconds and
its brief `ROW EXCLUSIVE`-blocking lock is not a concern at this size — no `CONCURRENTLY` needed
(and `CONCURRENTLY` cannot run inside Alembic's transaction anyway). **Fully reversible without
loss** (downgrade drops the indexes).

**Files:**
- Create: `backend/alembic/versions/a1b2c3d4e5f6_fk_indexes.py`
- Modify: `backend/src/db/models/feedback.py` (lines 28-30 `user_id`, lines 40-42 `reviewed_by`),
  `backend/src/db/models/proposal.py` (lines 63-65 `reviewed_by`),
  `backend/src/db/models/calibration_note.py` (lines 54-56 `reviewed_by`),
  `backend/src/db/models/prompt.py` (lines 20-22 `updated_by`)
- Create test: `backend/tests/integration/test_models/test_fk_indexes.py`

**Interfaces:**
- Consumes: nothing.
- Produces: revision `a1b2c3d4e5f6`, `down_revision = "1cd2cc2d05a9"`. Index names (the naming
  convention's `ix_%(column_0_label)s` form, which is what `index=True` on the column generates):
  `ix_feedback_user_id`, `ix_feedback_reviewed_by`, `ix_lesson_content_proposals_reviewed_by`,
  `ix_calibration_notes_reviewed_by`, `ix_prompts_updated_by`.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/integration/test_models/test_fk_indexes.py`:

```python
"""Every FK column we join or cascade on must be indexed.

Asserted against the live test schema (built from Base.metadata by the session
engine fixture), so this fails if a model declares an index the migration
forgot — or the reverse.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from sqlalchemy import inspect

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncEngine

_EXPECTED = [
    ("feedback", "user_id"),
    ("feedback", "reviewed_by"),
    ("lesson_content_proposals", "reviewed_by"),
    ("calibration_notes", "reviewed_by"),
    ("prompts", "updated_by"),
]


@pytest.mark.parametrize(("table", "column"), _EXPECTED)
async def test_fk_column_is_indexed(engine: AsyncEngine, table: str, column: str) -> None:
    async with engine.connect() as conn:
        indexes = await conn.run_sync(lambda sync: inspect(sync).get_indexes(table))
    indexed_leading_columns = {tuple(ix["column_names"][:1]) for ix in indexes}
    assert (column,) in indexed_leading_columns, (
        f"{table}.{column} has no index with it as the leading column; "
        f"found {sorted(indexed_leading_columns)}"
    )
```

- [ ] **Step 2: Run test to verify it fails**

```
cd backend
uv run pytest tests/integration/test_models/test_fk_indexes.py -v
```

Expected: all five parametrised cases fail with
`AssertionError: feedback.user_id has no index with it as the leading column; found [('lesson_id',)]`
(and the equivalent for the other four).

- [ ] **Step 3: Write minimal implementation**

Add `index=True` to the five columns. `backend/src/db/models/feedback.py`:

```python
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
```

```python
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
```

`backend/src/db/models/proposal.py`:

```python
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
```

`backend/src/db/models/calibration_note.py`:

```python
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
```

`backend/src/db/models/prompt.py`:

```python
    updated_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
```

Create `backend/alembic/versions/a1b2c3d4e5f6_fk_indexes.py`:

```python
"""index the FK columns we join and cascade on

`feedback.user_id` was the load-bearing gap: deleting a user cascaded through a
seq-scan of `feedback`, and the project-scoped admin feedback queue joins
`users` to filter on `project_id`. The four `ON DELETE SET NULL` audit columns
(`feedback.reviewed_by`, `lesson_content_proposals.reviewed_by`,
`calibration_notes.reviewed_by`, `prompts.updated_by`) had the same problem on a
smaller scale — a user delete had to seq-scan each of them.

Purely additive: five B-tree indexes, no row is read or written. All four tables
are small (hundreds of rows), so each CREATE INDEX is a millisecond-scale
operation — safe inside the automatic `alembic upgrade head` that runs on
container start.

Revision ID: a1b2c3d4e5f6
Revises: 1cd2cc2d05a9
Create Date: 2026-07-31

"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "a1b2c3d4e5f6"
down_revision: str | None = "1cd2cc2d05a9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# (index name, table, column) — names match the metadata naming convention's
# `ix_%(column_0_label)s`, i.e. what `index=True` on the model column produces.
_INDEXES = (
    ("ix_feedback_user_id", "feedback", "user_id"),
    ("ix_feedback_reviewed_by", "feedback", "reviewed_by"),
    (
        "ix_lesson_content_proposals_reviewed_by",
        "lesson_content_proposals",
        "reviewed_by",
    ),
    ("ix_calibration_notes_reviewed_by", "calibration_notes", "reviewed_by"),
    ("ix_prompts_updated_by", "prompts", "updated_by"),
)


def upgrade() -> None:
    for name, table, column in _INDEXES:
        op.create_index(op.f(name), table, [column], unique=False)


def downgrade() -> None:
    for name, table, _column in reversed(_INDEXES):
        op.drop_index(op.f(name), table_name=table)
```

- [ ] **Step 4: Run test to verify it passes**

```
cd backend
uv run poe upgrade
uv run alembic current          # expect: a1b2c3d4e5f6 (head)
uv run pytest tests/integration/test_models/test_fk_indexes.py -v
uv run poe format && uv run poe lint && uv run poe test
```

- [ ] **Step 5: Commit**

```
git add backend/alembic/versions/a1b2c3d4e5f6_fk_indexes.py backend/src/db/models/feedback.py backend/src/db/models/proposal.py backend/src/db/models/calibration_note.py backend/src/db/models/prompt.py backend/tests/integration/test_models/test_fk_indexes.py
git commit -m "$(cat <<'EOF'
Index feedback.user_id and the four SET NULL audit FKs

Review finding 6.2. feedback.user_id had no index, so user deletes and
the project-scoped feedback queue (which joins users to filter on
project_id) seq-scanned the table; the reviewed_by/updated_by columns had
the same problem on the delete path.

Additive migration a1b2c3d4e5f6 (revises 1cd2cc2d05a9): five B-tree
indexes on small tables, reversible without loss.

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 3: Give `messages` ordering a total order (6.3)

`created_at` alone is not a total order. The same codebase already treats this as load-bearing
(`calibration_note_repository.py:61-74` adds `id DESC` with a comment explaining that a tied batch
straddling a page boundary can return a row twice or never). Messages carry per-row client-generated
timestamps so ties are unlikely — but two turns in the same microsecond would silently flip the
transcript, which is the one thing the interviewer's playbook generation and the admin transcript view
cannot tolerate. Code-only, no migration.

**Files:**
- Modify: `backend/src/repositories/message_repository.py` (lines 44-50 `list_for_conversation`,
  lines 52-61 `list_recent`)
- Modify test: `backend/tests/integration/test_repositories/test_message_repository.py` (append)

**Interfaces:**
- Consumes: `src.db.models.Message`.
- Produces: unchanged signatures `list_for_conversation(conversation_id) -> list[Message]` and
  `list_recent(conversation_id, *, limit) -> list[Message]`, now with a documented total order
  `(created_at, id)` ascending — `ChatService._history_for` and
  `InterviewService.build_playbook`/`get_admin_view` depend on it.

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/integration/test_repositories/test_message_repository.py`:

```python
async def test_ties_on_created_at_keep_a_stable_total_order(db_session: AsyncSession) -> None:
    """created_at alone is not a total order. Rows written with an identical
    timestamp must still come back in one deterministic order (created_at, id),
    or a transcript can silently reorder itself between reads."""
    from datetime import UTC, datetime

    from src.db.models import Message

    user = await create_user(db_session, email="msg-tie@example.com")
    conversations = ConversationRepository(db_session)
    conversation = await conversations.create(user_id=user.id, kind="chatbot")
    stamp = datetime.now(UTC)
    db_session.add_all(
        Message(
            conversation_id=conversation.id,
            role="user",
            content=f"tied {i}",
            metadata_=None,
            created_at=stamp,
        )
        for i in range(6)
    )
    await db_session.commit()

    messages = MessageRepository(db_session)
    first = [(m.created_at, m.id) for m in await messages.list_for_conversation(conversation.id)]
    second = [(m.created_at, m.id) for m in await messages.list_for_conversation(conversation.id)]

    assert first == second
    assert first == sorted(first)
    # list_recent must agree with the tail of the full transcript.
    recent = await messages.list_recent(conversation.id, limit=3)
    assert [(m.created_at, m.id) for m in recent] == first[-3:]
```

- [ ] **Step 2: Run test to verify it fails**

```
cd backend
uv run pytest tests/integration/test_repositories/test_message_repository.py -v
```

Expected: `test_ties_on_created_at_keep_a_stable_total_order` fails on `assert first == sorted(first)`
(or on the `recent` comparison) — with six rows sharing one timestamp, Postgres is free to return any
permutation, and the `list_recent` DESC/reverse path does not agree with the ASC path.

- [ ] **Step 3: Write minimal implementation**

In `backend/src/repositories/message_repository.py`:

```python
    async def list_for_conversation(self, conversation_id: uuid.UUID) -> list[Message]:
        # `id` is the tiebreaker and it is load-bearing: created_at alone is not
        # a total order, and two turns written in the same microsecond would
        # otherwise be free to swap places between reads — silently reordering a
        # transcript that the playbook generator and the admin view both read.
        result = await self._session.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.asc(), Message.id.asc())
        )
        return list(result.scalars().all())

    async def list_recent(self, conversation_id: uuid.UUID, *, limit: int) -> list[Message]:
        # Mirror image of list_for_conversation's order, so the window this sends
        # to the model is exactly the tail of the stored transcript.
        result = await self._session.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.desc(), Message.id.desc())
            .limit(limit)
        )
        rows = list(result.scalars().all())
        rows.reverse()
        return rows
```

Also update the two abstract docstrings in `backend/src/repositories/base.py` (lines 680-685) to say
`Chronological — ordered by (created_at, id), a total order` and
`Last `limit` messages in the same total order (window cap sent to the model)`.

- [ ] **Step 4: Run test to verify it passes**

```
cd backend
uv run pytest tests/integration/test_repositories/test_message_repository.py -v
uv run poe format && uv run poe lint && uv run poe test
```

- [ ] **Step 5: Commit**

```
git add backend/src/repositories/message_repository.py backend/src/repositories/base.py backend/tests/integration/test_repositories/test_message_repository.py
git commit -m "$(cat <<'EOF'
Order messages by (created_at, id) so transcripts are stable

Review finding 6.3. created_at alone is not a total order; two turns
sharing a timestamp could swap places between reads, reordering a
transcript under the playbook generator and the admin view. Matches the
tiebreaker calibration_note_repository already documents as load-bearing.

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 4: Remove the three duplicate reads on `/learning/graph` (6.9, prior 2.2)

`routers/learning.py:46-47` calls `MaturityService.effective_level(user)` and then
`LearningService.graph(user.id, effective)`. Each independently runs `list_tracks()`,
`list_modules()` and `assigned_lesson_counts_by_module()` — three duplicated queries on the learner's
main screen. The fix follows the house precedent for exactly this situation (`admin_user_service.py:
180-201` and `dashboard_service.py`, both of which assemble the maturity inputs themselves rather than
call `MaturityService`): `LearningService.graph` computes the effective level from the rows it has
already fetched, using the shared pure `advance_level`. `MaturityService` is untouched — it still
serves `interview_context.py` and the admin override endpoint.

**Files:**
- Modify: `backend/src/services/learning_service.py` (lines 22-34 `__init__`, lines 36-131 `graph`)
- Modify: `backend/src/routers/learning.py` (lines 37-47 `get_learning_graph`)
- Modify: `backend/src/core/dependencies/domain.py` (lines 110-115 `get_learning_service`)
- Modify test: `backend/tests/integration/test_routers/test_learning.py` (append)

**Interfaces:**
- Consumes: `AbstractSurveyRepository.get_complete_levels(user_ids) -> dict[UUID, str]` (new
  dependency of `LearningService`), `core.constants.advance_level(base, module_level, counts)`.
- Produces: **changed signature** — `LearningService.graph(user: User) -> dict[str, Any]` (was
  `graph(user_id: uuid.UUID, effective_level: str | None = None)`). Response payload is byte-for-byte
  unchanged, including `maturity_level`. `LearningService.__init__(content, assignments, progress,
  surveys)`.

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/integration/test_routers/test_learning.py`:

```python
async def test_graph_does_not_run_its_shared_reads_twice(
    client: AsyncClient, learner: User, test_settings: Settings, db_session: AsyncSession
) -> None:
    """/learning/graph used to compute maturity and the graph independently, so
    list_tracks / list_modules / assigned_lesson_counts_by_module each ran twice
    per request. Count the statements to keep that from coming back."""
    from sqlalchemy import event

    track = await create_track(db_session, "General I", required_level="explore")
    module = await create_module(db_session, track, "M")
    await create_lesson(db_session, module, "L")
    await assign_track(db_session, learner, track)

    seen: list[str] = []

    def _record(conn, cursor, statement, parameters, context, executemany) -> None:  # noqa: ANN001
        seen.append(" ".join(statement.split()))

    event.listen(db_session.sync_session.bind.engine, "before_cursor_execute", _record)
    try:
        response = await client.get(
            "/api/learning/graph", headers=auth_headers(learner, test_settings)
        )
    finally:
        event.remove(db_session.sync_session.bind.engine, "before_cursor_execute", _record)

    assert response.status_code == 200
    tracks_selects = [s for s in seen if s.startswith("SELECT tracks.")]
    modules_selects = [s for s in seen if s.startswith("SELECT modules.")]
    assert len(tracks_selects) == 1, f"tracks read {len(tracks_selects)}x: {tracks_selects}"
    assert len(modules_selects) == 1, f"modules read {len(modules_selects)}x: {modules_selects}"
```

- [ ] **Step 2: Run test to verify it fails**

```
cd backend
uv run pytest tests/integration/test_routers/test_learning.py -k does_not_run_its_shared_reads -v
```

Expected: `AssertionError: tracks read 2x: [...]` — `effective_level` and `graph` each issue their own
`SELECT tracks...`.

- [ ] **Step 3: Write minimal implementation**

`backend/src/services/learning_service.py` — add the survey repository and compute the level inline:

```python
from src.core.constants import LEVEL_RANK, advance_level
```

```python
    def __init__(
        self,
        content: AbstractContentRepository,
        assignments: AbstractAssignmentRepository,
        progress: AbstractProgressRepository,
        surveys: AbstractSurveyRepository,
    ) -> None:
        self._content = content
        self._assignments = assignments
        self._progress = progress
        self._surveys = surveys
```

```python
    async def graph(self, user: User) -> dict[str, Any]:
        """The one aggregate replacing LearningPath's legacy 7-query chain.

        ... (keep the existing docstring body) ...

        The caller's effective maturity is computed HERE, from the very rows this
        method already reads, via the shared `advance_level` ladder walk — not by
        calling MaturityService (services never call services), which would
        re-run list_tracks/list_modules/assigned_lesson_counts_by_module. Same
        pattern AdminUserService and DashboardService use.
        """
        user_id = user.id
        tracks = await self._content.list_tracks()
        modules = await self._content.list_modules()
        prerequisites = await self._content.list_prerequisites()
        assigned_tracks = await self._assignments.track_ids_for_user(user_id)
        assigned_modules = await self._assignments.module_ids_for_user(user_id)
        lesson_counts = await self._assignments.assigned_lesson_counts_by_module(user_id)

        track_level = {track.id: track.required_level for track in tracks}
        module_level = {
            module.id: track_level[module.track_id]
            for module in modules
            if module.track_id in track_level
        }
        base = user.maturity_override or (await self._surveys.get_complete_levels([user_id])).get(
            user_id
        )
        effective_level = (
            advance_level(base, module_level, lesson_counts) if base is not None else None
        )

        caller_rank = LEVEL_RANK[effective_level] if effective_level is not None else None
```

(the rest of `graph` — from `def track_unlocked` to the returned dict — is unchanged; it already reads
`effective_level` and `lesson_counts` from local scope.)

Add to the `TYPE_CHECKING` block:

```python
if TYPE_CHECKING:
    from src.db.models import Lesson, User
    from src.repositories.base import (
        AbstractAssignmentRepository,
        AbstractContentRepository,
        AbstractProgressRepository,
        AbstractSurveyRepository,
    )
```

`backend/src/routers/learning.py` — drop the maturity call from this endpoint:

```python
@router.get("/learning/graph", response_model=LearningGraphResponse)
async def get_learning_graph(
    user: CurrentUserDep,
    learning_service: LearningServiceDep,
) -> LearningGraphResponse:
    """One aggregate replacing LearningPath's legacy 7-query chain; `assigned`
    flags are computed for the caller only. Per-track maturity locks come from
    the caller's effective level (override + live progression), which the
    service derives from the rows it already reads."""
    return LearningGraphResponse(**await learning_service.graph(user))
```

Remove the now-unused `maturity_service` parameter, and remove `MaturityServiceDep`/the
`MaturityService` import from `routers/learning.py` **only if no other route in that file uses them**
(check with `grep -n MaturityService src/routers/learning.py` — if another route does, keep them).

`backend/src/core/dependencies/domain.py`:

```python
def get_learning_service(
    content: Annotated[ContentRepository, Depends(get_content_repository)],
    assignments: Annotated[AssignmentRepository, Depends(get_assignment_repository)],
    progress: Annotated[ProgressRepository, Depends(get_progress_repository)],
    surveys: Annotated[SurveyRepository, Depends(get_survey_repository)],
) -> LearningService:
    return LearningService(content, assignments, progress, surveys)
```

- [ ] **Step 4: Run test to verify it passes**

```
cd backend
uv run pytest tests/integration/test_routers/test_learning.py tests/integration/test_routers/test_maturity.py tests/integration/test_routers/test_introduction.py -v
uv run poe format && uv run poe lint && uv run poe test
```

`test_maturity.py` exercises maturity through the HTTP endpoint, so the unchanged payload keeps it
green; if any test constructs `LearningService(...)` positionally it needs the fourth argument.

- [ ] **Step 5: Commit**

```
git add backend/src/services/learning_service.py backend/src/routers/learning.py backend/src/core/dependencies/domain.py backend/tests/integration/test_routers/test_learning.py
git commit -m "$(cat <<'EOF'
Compute maturity inside LearningService.graph to kill 3 duplicate reads

Review finding 6.9 (prior 2.2). /learning/graph ran list_tracks,
list_modules and assigned_lesson_counts_by_module twice per request —
once for MaturityService.effective_level, once for the graph itself.
graph() now derives the effective level from the rows it already reads
via the shared advance_level helper, the same way AdminUserService and
DashboardService do (services never call services). Payload unchanged.

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 5: Reorder lessons in one round-trip (6.9)

`content_repository.set_lesson_orders` issues M sequential `UPDATE`s inside one transaction. Replace
with a single ORM bulk-update-by-primary-key (one executemany round-trip).

**Files:**
- Modify: `backend/src/repositories/content_repository.py` (lines 171-176 `set_lesson_orders`)
- Modify test: `backend/tests/integration/test_routers/test_admin_content.py` (append)

**Interfaces:**
- Consumes: `src.db.models.Lesson`.
- Produces: unchanged signature `set_lesson_orders(orders: list[tuple[uuid.UUID, int]]) -> None`; an
  empty list is now an explicit no-op that issues no statement.

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/integration/test_routers/test_admin_content.py`:

```python
async def test_reorder_lessons_issues_one_update_round_trip(db_session: AsyncSession) -> None:
    """Reordering used to fire one UPDATE per lesson. Keep it to a single
    statement so a long module does not cost M round-trips to Azure."""
    from sqlalchemy import event

    from src.repositories.content_repository import ContentRepository

    track = await create_track(db_session, "Reorder Track")
    module = await create_module(db_session, track, "Reorder Module")
    lessons = [
        await create_lesson(db_session, module, f"L{i}", sort_order=i) for i in range(5)
    ]

    updates: list[str] = []

    def _record(conn, cursor, statement, parameters, context, executemany) -> None:  # noqa: ANN001
        if statement.strip().upper().startswith("UPDATE LESSONS"):
            updates.append(statement)

    repo = ContentRepository(db_session)
    event.listen(db_session.sync_session.bind.engine, "before_cursor_execute", _record)
    try:
        await repo.set_lesson_orders(
            [(lesson.id, index) for index, lesson in enumerate(reversed(lessons))]
        )
    finally:
        event.remove(db_session.sync_session.bind.engine, "before_cursor_execute", _record)

    assert len(updates) == 1, f"expected one UPDATE statement, got {len(updates)}"
    reordered = await repo.list_lessons(module.id)
    assert [lesson.title for lesson in reordered] == ["L4", "L3", "L2", "L1", "L0"]


async def test_set_lesson_orders_with_no_rows_issues_no_statement(
    db_session: AsyncSession,
) -> None:
    from src.repositories.content_repository import ContentRepository

    await ContentRepository(db_session).set_lesson_orders([])
```

- [ ] **Step 2: Run test to verify it fails**

```
cd backend
uv run pytest tests/integration/test_routers/test_admin_content.py -k issues_one_update_round_trip -v
```

Expected: `AssertionError: expected one UPDATE statement, got 5`.

- [ ] **Step 3: Write minimal implementation**

In `backend/src/repositories/content_repository.py`:

```python
    async def set_lesson_orders(self, orders: list[tuple[uuid.UUID, int]]) -> None:
        if not orders:
            return
        # One executemany round-trip, not M sequential UPDATEs: SQLAlchemy's ORM
        # bulk-update-by-primary-key takes a list of dicts that each carry the pk
        # plus the columns to set. `sort_order` has no uniqueness constraint, so
        # the intermediate states of a permutation are never a problem.
        await self._session.execute(
            update(Lesson),
            [{"id": lesson_id, "sort_order": sort_order} for lesson_id, sort_order in orders],
        )
        await self._session.commit()
```

- [ ] **Step 4: Run test to verify it passes**

```
cd backend
uv run pytest tests/integration/test_routers/test_admin_content.py -v
uv run poe format && uv run poe lint && uv run poe test
```

- [ ] **Step 5: Commit**

```
git add backend/src/repositories/content_repository.py backend/tests/integration/test_routers/test_admin_content.py
git commit -m "$(cat <<'EOF'
Reorder lessons in one bulk UPDATE instead of M round-trips

Review finding 6.9. set_lesson_orders looped one UPDATE per lesson; it
now issues a single ORM bulk-update-by-primary-key, and an empty list is
an explicit no-op.

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 6: Scope `lesson_ids_for_user` and give "next lesson" a total order (6.9, 6.5/prior 10.2a)

Two related learner-path fixes in one commit, both in the same call paths:
1. `lesson_ids_for_user(user_id)` pulls **every** lesson id assigned to the user in order to test
   membership for one module (`learning_service.py:159` and `:196`). Add an optional id filter,
   mirroring `ProgressRepository.completed_lesson_ids`.
2. "Next lesson" uses strict `le.sort_order > lesson.sort_order` (`learning_service.py:204-210`).
   `sort_order` is not unique, so a tied sibling is skipped — and it disagrees with
   `list_lessons`'s own `(sort_order, id)` ordering. Compare the `(sort_order, id)` tuple instead.
   This is the code-side half of 6.5's sort_order item; the DB-side half is Task 11.

**Files:**
- Modify: `backend/src/repositories/base.py` (line 509, `AbstractAssignmentRepository.
  lesson_ids_for_user`)
- Modify: `backend/src/repositories/assignment_repository.py` (lines 27-31 `lesson_ids_for_user`)
- Modify: `backend/src/services/learning_service.py` (`module_lessons` lines 148-181,
  `lesson_detail` lines 183-242)
- Modify test: `backend/tests/integration/test_routers/test_learning.py` (append)

**Interfaces:**
- Produces: `AbstractAssignmentRepository.lesson_ids_for_user(user_id: uuid.UUID, lesson_ids:
  list[uuid.UUID] | None = None) -> set[uuid.UUID]` — the optional argument restricts the read; `None`
  keeps today's unbounded behaviour for any other caller.

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/integration/test_routers/test_learning.py`:

```python
async def test_lesson_ids_for_user_can_be_scoped_to_a_candidate_set(
    db_session: AsyncSession, learner: User
) -> None:
    from src.repositories.assignment_repository import AssignmentRepository

    track = await create_track(db_session, "Scope Track")
    module = await create_module(db_session, track, "Scope Module")
    wanted = await create_lesson(db_session, module, "Wanted", sort_order=0)
    other = await create_lesson(db_session, module, "Other", sort_order=1)
    await assign_lesson(db_session, learner, wanted)
    await assign_lesson(db_session, learner, other)

    assignments = AssignmentRepository(db_session)

    assert await assignments.lesson_ids_for_user(learner.id) == {wanted.id, other.id}
    assert await assignments.lesson_ids_for_user(learner.id, [wanted.id]) == {wanted.id}
    assert await assignments.lesson_ids_for_user(learner.id, []) == set()


async def test_next_lesson_does_not_skip_a_tied_sort_order(
    client: AsyncClient, learner: User, test_settings: Settings, db_session: AsyncSession
) -> None:
    """sort_order is not unique. Two lessons sharing one must still form a
    sequence — the strict `>` comparison skipped the tied sibling entirely."""
    track = await create_track(db_session, "Tie Track")
    module = await create_module(db_session, track, "Tie Module")
    first = await create_lesson(db_session, module, "First", sort_order=1)
    tied = await create_lesson(db_session, module, "Tied", sort_order=1)
    await assign_lesson(db_session, learner, first)
    await assign_lesson(db_session, learner, tied)
    earlier, later = sorted([first, tied], key=lambda lesson: (lesson.sort_order, lesson.id))

    response = await client.get(
        f"/api/lessons/{earlier.id}", headers=auth_headers(learner, test_settings)
    )

    assert response.status_code == 200
    assert response.json()["next_lesson_id"] == str(later.id)
```

- [ ] **Step 2: Run test to verify it fails**

```
cd backend
uv run pytest tests/integration/test_routers/test_learning.py -k "scoped_to_a_candidate_set or tied_sort_order" -v
```

Expected: the first fails with `TypeError: lesson_ids_for_user() takes 2 positional arguments but 3
were given`; the second fails with `assert None == '<uuid>'` (the tied sibling is skipped, so
`next_lesson_id` is null).

- [ ] **Step 3: Write minimal implementation**

`backend/src/repositories/base.py`:

```python
    @abstractmethod
    async def lesson_ids_for_user(
        self, user_id: uuid.UUID, lesson_ids: list[uuid.UUID] | None = None
    ) -> set[uuid.UUID]:
        """The user's assigned lesson ids, optionally restricted to a candidate
        set (so a caller testing one module's membership does not read every
        lesson the user owns). An empty list reads nothing and returns empty."""
```

`backend/src/repositories/assignment_repository.py`:

```python
    async def lesson_ids_for_user(
        self, user_id: uuid.UUID, lesson_ids: list[uuid.UUID] | None = None
    ) -> set[uuid.UUID]:
        if lesson_ids is not None and not lesson_ids:
            return set()
        stmt = select(UserLesson.lesson_id).where(UserLesson.user_id == user_id)
        if lesson_ids is not None:
            stmt = stmt.where(UserLesson.lesson_id.in_(lesson_ids))
        result = await self._session.execute(stmt)
        return set(result.scalars().all())
```

`backend/src/services/learning_service.py` — in `module_lessons`, scope the read to the module's
lessons:

```python
        lessons = await self._content.list_lessons(module_id)
        completed = await self._progress.completed_lesson_ids(user_id, [le.id for le in lessons])
        assigned = await self._assignments.lesson_ids_for_user(
            user_id, [le.id for le in lessons]
        )
```

and in `lesson_detail`, scope each read to the candidate set it is actually about:

```python
        progress = await self._progress.get(user_id, lesson_id)
        track = await self._content.get_track(module.track_id)
        intro = track is not None and track.is_introduction

        module_lessons = await self._content.list_lessons(lesson.module_id)
        assigned = await self._assignments.lesson_ids_for_user(
            user_id, [le.id for le in module_lessons]
        )

        def is_assigned(lesson_id_: uuid.UUID, assigned_ids: set[uuid.UUID]) -> bool:
            return intro or lesson_id_ in assigned_ids

        # (sort_order, id) — the same total order list_lessons returns. Strict
        # `sort_order >` skipped a tied sibling entirely, and sort_order is not
        # unique (creation is max+1, reorder writes 0-based indices).
        here = (lesson.sort_order, lesson.id)
        next_module_id: uuid.UUID | None = None
        next_lesson: Lesson | None = next(
            (
                le
                for le in module_lessons
                if (le.sort_order, le.id) > here and is_assigned(le.id, assigned)
            ),
            None,
        )
        if next_lesson is None:
            next_module = await self._content.next_module_in_track(
                module.track_id, module.sort_order
            )
            if next_module is not None:
                next_module_id = next_module.id
                next_module_lessons = await self._content.list_lessons(next_module.id)
                next_assigned = await self._assignments.lesson_ids_for_user(
                    user_id, [le.id for le in next_module_lessons]
                )
                next_lesson = next(
                    (le for le in next_module_lessons if is_assigned(le.id, next_assigned)),
                    None,
                )
```

- [ ] **Step 4: Run test to verify it passes**

```
cd backend
uv run pytest tests/integration/test_routers/test_learning.py tests/integration/test_routers/test_introduction.py -v
uv run poe format && uv run poe lint && uv run poe test
```

- [ ] **Step 5: Commit**

```
git add backend/src/repositories/base.py backend/src/repositories/assignment_repository.py backend/src/services/learning_service.py backend/tests/integration/test_routers/test_learning.py
git commit -m "$(cat <<'EOF'
Scope assigned-lesson reads and order "next lesson" totally

Review findings 6.9 and 6.5/prior 10.2a. lesson_ids_for_user now takes an
optional candidate set, so testing one module's membership no longer
reads every lesson a user owns. "Next lesson" compares the
(sort_order, id) tuple — the same total order list_lessons returns —
instead of a strict sort_order >, which silently skipped tied siblings.

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 7: Add `pool_recycle` to the Azure PG engine (6.9)

`pool_pre_ping=True` already catches connections Azure has killed, at the cost of a failed round-trip
per stale connection. Recycling proactively at 30 minutes means most idle kills are never observed.

**Files:**
- Modify: `backend/src/main.py` (lines 105-115, the `lifespan` engine kwargs)
- Modify: `backend/src/core/configs/database.py` (lines 31-32, add `pool_recycle_seconds`)
- Create test: `backend/tests/unit/test_database_config.py`

**Interfaces:**
- Produces: `DatabaseSettings.pool_recycle_seconds: int = 1800` (env `DATABASE__POOL_RECYCLE_SECONDS`).

- [ ] **Step 1: Write the failing test**

Create `backend/tests/unit/test_database_config.py`:

```python
from __future__ import annotations

from src.core.configs.database import DatabaseSettings


def test_pool_recycle_defaults_to_thirty_minutes() -> None:
    """Azure PG closes idle connections; recycling before it does keeps
    pool_pre_ping from having to discover it the expensive way."""
    assert DatabaseSettings().pool_recycle_seconds == 1800


def test_pool_recycle_is_overridable() -> None:
    assert DatabaseSettings(pool_recycle_seconds=60).pool_recycle_seconds == 60
```

- [ ] **Step 2: Run test to verify it fails**

```
cd backend
uv run pytest tests/unit/test_database_config.py -v
```

Expected: `AttributeError: 'DatabaseSettings' object has no attribute 'pool_recycle_seconds'`.

- [ ] **Step 3: Write minimal implementation**

`backend/src/core/configs/database.py`, after `max_overflow`:

```python
    pool_size: int = 5
    max_overflow: int = 10
    # Azure Database for PostgreSQL closes idle server-side connections. Recycle
    # ours first: pool_pre_ping (set in main.py) already recovers from a killed
    # connection, but only after paying a failed round-trip to discover it.
    pool_recycle_seconds: int = 1800
```

`backend/src/main.py`, inside the PostgreSQL branch of `lifespan`:

```python
    if settings.database.protocol is DatabaseProtocol.POSTGRESQL:
        kwargs.update(
            pool_size=settings.database.pool_size,
            max_overflow=settings.database.max_overflow,
            pool_pre_ping=True,
            pool_recycle=settings.database.pool_recycle_seconds,
        )
```

- [ ] **Step 4: Run test to verify it passes**

```
cd backend
uv run pytest tests/unit/test_database_config.py -v
uv run poe format && uv run poe lint && uv run poe test
```

- [ ] **Step 5: Commit**

```
git add backend/src/core/configs/database.py backend/src/main.py backend/tests/unit/test_database_config.py
git commit -m "$(cat <<'EOF'
Recycle pooled connections after 30 minutes

Review finding 6.9. Azure PG kills idle connections; pool_pre_ping only
discovers that after a failed round-trip. pool_recycle=1800 (configurable
via DATABASE__POOL_RECYCLE_SECONDS) retires them first.

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 8: Close the newer-table drift on `prompts` and `project_ai_settings` (6.4 — migration 2/3)

> **Amended 2026-09-23 (PR #16, spec `docs/superpowers/specs/2026-09-23-prompts-git-only-design.md`):** prompts are git-only; no code reads or writes `prompts` any more. The `prompts` half of this task is **replaced**: do not add the `kind` CHECK or `created_at` — instead drop the `prompts` table and `backend/src/db/models/prompt.py` in this migration (expand-first is already satisfied: no deployed code uses the table after PR #16 ships; confirm that deploy happened first). The `project_ai_settings` half stands as written.

`prompts.kind` is the only enum-as-text column in the schema with no CHECK, `prompts` has no
`created_at`, and `project_ai_settings` has neither timestamp while its sibling
`project_component_settings` has `updated_at`.

**Live data:** adds three `TIMESTAMPTZ NOT NULL DEFAULT now()` columns (existing rows get the
migration's timestamp — acceptable: these are settings/override rows whose creation time was never
recorded) and one CHECK on `prompts.kind`. **The CHECK validates existing rows, so an unexpected
`kind` value makes the migration RAISE — and because prod runs `alembic upgrade head` before binding
the port, that would stop the new revision from ever serving.** Step 1 below therefore *verifies prod
first*. Tables are tiny (≤ 9 prompt rows, ≤ 4 settings rows per project). **Reversible without loss**
except that the downgrade drops the three timestamp columns (their values are not recoverable — they
carry no information beyond the migration moment, so this is acceptable).

**Tradeoff to accept explicitly:** with the CHECK in place, adding a new prompt kind needs a
migration alongside the `KNOWN_PROMPTS` entry. That is the same cost every other enum in this schema
already pays (`conversations.kind`, `project_ai_settings.kind`, `auth_tokens.purpose`), and it is
exactly the protection that makes a typo'd kind impossible.

**Files:**
- Create: `backend/alembic/versions/b2c3d4e5f6a7_prompts_and_ai_settings_drift.py`
- Modify: `backend/src/db/models/prompt.py` (whole class), `backend/src/db/models/company.py`
  (lines 113-133 `ProjectAiSetting`)
- Create test: `backend/tests/integration/test_models/test_prompt_and_ai_setting_schema.py`

**Interfaces:**
- Produces: revision `b2c3d4e5f6a7`, `down_revision = "a1b2c3d4e5f6"`. New constraint
  `ck_prompts_kind`; new columns `prompts.created_at`, `project_ai_settings.created_at`,
  `project_ai_settings.updated_at`. `Prompt.created_at: Mapped[datetime]`,
  `ProjectAiSetting.created_at/updated_at: Mapped[datetime]`.

- [ ] **Step 1: Write the failing test** (and first, verify prod)

**Verify against prod before writing the migration.** The CHECK must cover every `kind` already
stored. Run (read-only) against the production database:

```sql
SELECT kind, count(*)
FROM prompts
WHERE kind NOT IN (
  'interview', 'interview_playbook', 'chatbot', 'assessment', 'lesson',
  'content_improvement', 'content_improvement_critique', 'house_style', 'feedback_triage'
)
GROUP BY kind;
```

Expected: **zero rows** (the admin endpoint only accepts `KNOWN_PROMPTS`, `prompt_service.py:29-41`).
If it returns any row, STOP: either the list here is stale or a row was written by hand — reconcile
with Matthias before proceeding, and paste the query result into the commit message either way.

Create `backend/tests/integration/test_models/test_prompt_and_ai_setting_schema.py`:

```python
from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from sqlalchemy.exc import IntegrityError

from src.db.models import Prompt, ProjectAiSetting
from src.services.prompt_service import KNOWN_PROMPTS
from tests.fixtures.factories import create_company, create_project

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


async def test_prompt_rejects_an_unknown_kind(db_session: AsyncSession) -> None:
    db_session.add(Prompt(kind="not-a-real-prompt", content="x"))
    with pytest.raises(IntegrityError):
        await db_session.commit()
    await db_session.rollback()


async def test_prompt_accepts_every_known_kind(db_session: AsyncSession) -> None:
    db_session.add_all(Prompt(kind=meta.kind, content="x") for meta in KNOWN_PROMPTS)
    await db_session.commit()


async def test_prompt_stamps_created_at(db_session: AsyncSession) -> None:
    prompt = Prompt(kind="house_style", content="x")
    db_session.add(prompt)
    await db_session.commit()
    await db_session.refresh(prompt)
    assert prompt.created_at is not None


async def test_ai_setting_stamps_both_timestamps(db_session: AsyncSession) -> None:
    company = await create_company(db_session, "Drift Co")
    project = await create_project(db_session, company, "Drift Project")
    setting = ProjectAiSetting(project_id=project.id, kind="chatbot")
    db_session.add(setting)
    await db_session.commit()
    await db_session.refresh(setting)
    assert setting.created_at is not None
    assert setting.updated_at is not None
```

- [ ] **Step 2: Run test to verify it fails**

```
cd backend
uv run pytest tests/integration/test_models/test_prompt_and_ai_setting_schema.py -v
```

Expected: `test_prompt_rejects_an_unknown_kind` fails with `DID NOT RAISE
<class 'sqlalchemy.exc.IntegrityError'>`; the three timestamp tests fail with
`AttributeError: 'Prompt' object has no attribute 'created_at'` /
`'ProjectAiSetting' object has no attribute 'created_at'`.

- [ ] **Step 3: Write minimal implementation**

`backend/src/db/models/prompt.py` — full replacement:

```python
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base

__all__ = ["KIND_VALUES", "Prompt"]

# Mirrors services/prompt_service.py::KNOWN_PROMPTS. Duplicated here on purpose:
# models must not import from services (layering), and the DB is the last line
# of defence — every other enum-as-text column in this schema has a CHECK.
# Adding a prompt kind therefore needs a migration alongside the KNOWN_PROMPTS
# entry; that is the same cost conversations.kind and auth_tokens.purpose pay.
KIND_VALUES = (
    "interview",
    "interview_playbook",
    "chatbot",
    "assessment",
    "lesson",
    "content_improvement",
    "content_improvement_critique",
    "house_style",
    "feedback_triage",
)
_KINDS = ", ".join(f"'{kind}'" for kind in KIND_VALUES)


class Prompt(Base):
    __tablename__ = "prompts"
    __table_args__ = (CheckConstraint(f"kind IN ({_KINDS})", name="kind"),)

    kind: Mapped[str] = mapped_column(Text, primary_key=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    updated_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
```

`backend/src/db/models/company.py` — add the two timestamps to `ProjectAiSetting`:

```python
    kind: Mapped[str] = mapped_column(Text, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
```

Add a guard test so the two kind lists cannot drift — append to the new test file:

```python
async def test_model_kind_list_matches_known_prompts() -> None:
    from src.db.models.prompt import KIND_VALUES

    assert set(KIND_VALUES) == {meta.kind for meta in KNOWN_PROMPTS}
```

Create `backend/alembic/versions/b2c3d4e5f6a7_prompts_and_ai_settings_drift.py`:

```python
"""close the newer-table drift on prompts and project_ai_settings

Three additive columns and one CHECK:
  - prompts.kind gains a CHECK. It was the only enum-as-text column in the
    schema without one (users.role, tracks.track_type/required_level,
    auth_tokens.purpose, conversations.kind, feedback.status, ... all have one),
    so a typo'd kind was caught only by service-level validation.
  - prompts.created_at, project_ai_settings.created_at/updated_at: every other
    table records when its rows appeared; these two did not.

Live data: the three columns are NOT NULL DEFAULT now(), so existing rows are
backfilled with this migration's timestamp (they carry no other creation record).
The CHECK validates existing rows — verified beforehand against prod that every
stored `kind` is in the list below (see the query in the plan/commit message).
Both tables are tiny, so this runs in milliseconds inside the automatic
`alembic upgrade head` on container start.

Reversible; the downgrade drops the three timestamp columns, whose values are
not recoverable but carry no information beyond the migration moment.

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-07-31

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "b2c3d4e5f6a7"
down_revision: str | None = "a1b2c3d4e5f6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Must equal src/db/models/prompt.py::KIND_VALUES (a test asserts that list
# equals services/prompt_service.py::KNOWN_PROMPTS).
_PROMPT_KINDS = (
    "'interview', 'interview_playbook', 'chatbot', 'assessment', 'lesson', "
    "'content_improvement', 'content_improvement_critique', 'house_style', 'feedback_triage'"
)


def upgrade() -> None:
    op.add_column(
        "prompts",
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_check_constraint(
        op.f("ck_prompts_kind"), "prompts", f"kind IN ({_PROMPT_KINDS})"
    )
    for column in ("created_at", "updated_at"):
        op.add_column(
            "project_ai_settings",
            sa.Column(
                column,
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=False,
            ),
        )


def downgrade() -> None:
    op.drop_column("project_ai_settings", "updated_at")
    op.drop_column("project_ai_settings", "created_at")
    op.drop_constraint(op.f("ck_prompts_kind"), "prompts", type_="check")
    op.drop_column("prompts", "created_at")
```

- [ ] **Step 4: Run test to verify it passes**

```
cd backend
uv run poe upgrade
uv run alembic current          # expect: b2c3d4e5f6a7 (head)
uv run pytest tests/integration/test_models/test_prompt_and_ai_setting_schema.py tests/integration/test_routers/test_admin_prompts.py tests/unit/test_prompt_service.py -v
uv run poe format && uv run poe lint && uv run poe test
```

- [ ] **Step 5: Commit**

```
git add backend/alembic/versions/b2c3d4e5f6a7_prompts_and_ai_settings_drift.py backend/src/db/models/prompt.py backend/src/db/models/company.py backend/tests/integration/test_models/test_prompt_and_ai_setting_schema.py
git commit -m "$(cat <<'EOF'
CHECK prompts.kind and add the missing creation timestamps

Review finding 6.4. prompts.kind was the only enum-as-text column in the
schema with no CHECK, prompts had no created_at, and
project_ai_settings had neither timestamp while its sibling
project_component_settings has updated_at.

Migration b2c3d4e5f6a7 (revises a1b2c3d4e5f6). Verified against prod
before shipping that every stored prompts.kind is in the CHECK list
(0 rows outside it) — the CHECK validates existing rows and prod runs
alembic upgrade head before binding the port.

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 9: Make the survey first draft an upsert (6.5)

`save_draft` is get-then-create (`survey_service.py:40-46`); two concurrent first saves both see
`None`, the second violates `uq_survey_responses_user_id`, and the learner gets a raw 500. Turn it
into a real upsert so the second save is simply an update. Code-only.

**Files:**
- Modify: `backend/src/repositories/base.py` (`AbstractSurveyRepository`, lines 273-296 — add
  `create_or_update`)
- Modify: `backend/src/repositories/survey_repository.py` (add `create_or_update`)
- Modify: `backend/src/services/survey_service.py` (lines 38-46 `save_draft`)
- Modify test: `backend/tests/integration/test_routers/test_survey_flow.py` (append)

**Interfaces:**
- Produces: `AbstractSurveyRepository.create_or_update(user_id: uuid.UUID, values: dict[str, Any]) ->
  SurveyResponse` — inserts the row or updates the existing one for that user, in one statement.
  `create()` and `update()` stay for their existing callers.

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/integration/test_routers/test_survey_flow.py`:

```python
async def test_concurrent_first_drafts_do_not_500(
    client: AsyncClient, learner: User, test_settings: Settings
) -> None:
    """Two first saves racing on the same user used to hit
    uq_survey_responses_user_id and surface as a raw 500. Sequentially forcing
    the same code path (no row -> row) must be a clean 200 either way."""
    headers = auth_headers(learner, test_settings)

    first = await client.put("/api/survey/me", json={"job_title": "A"}, headers=headers)
    second = await client.put("/api/survey/me", json={"job_title": "B"}, headers=headers)

    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json()["job_title"] == "B"


async def test_repository_upsert_is_idempotent_for_one_user(
    db_session: AsyncSession, learner: User
) -> None:
    from sqlalchemy import func, select

    from src.db.models import SurveyResponse
    from src.repositories.survey_repository import SurveyRepository

    surveys = SurveyRepository(db_session)

    await surveys.create_or_update(learner.id, {"status": "in_progress", "job_title": "One"})
    row = await surveys.create_or_update(learner.id, {"status": "in_progress", "job_title": "Two"})

    assert row.job_title == "Two"
    count = await db_session.execute(
        select(func.count()).select_from(SurveyResponse).where(SurveyResponse.user_id == learner.id)
    )
    assert count.scalar_one() == 1
```

- [ ] **Step 2: Run test to verify it fails**

```
cd backend
uv run pytest tests/integration/test_routers/test_survey_flow.py -k "concurrent_first_drafts or repository_upsert" -v
```

Expected: `test_repository_upsert_is_idempotent_for_one_user` fails with
`AttributeError: 'SurveyRepository' object has no attribute 'create_or_update'`.
(`test_concurrent_first_drafts_do_not_500` passes today — it documents the sequential contract that
must not regress; the race itself is what the upsert removes.)

- [ ] **Step 3: Write minimal implementation**

`backend/src/repositories/base.py`, in `AbstractSurveyRepository`:

```python
    @abstractmethod
    async def create_or_update(self, user_id: uuid.UUID, values: dict[str, Any]) -> SurveyResponse:
        """Insert the user's draft or update the existing one, in ONE statement.
        The table has UNIQUE(user_id), so a get-then-create pair loses the race
        between two concurrent first saves; ON CONFLICT makes the second an
        update instead of an IntegrityError."""
```

`backend/src/repositories/survey_repository.py`:

```python
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
```

```python
    async def create_or_update(self, user_id: uuid.UUID, values: dict[str, Any]) -> SurveyResponse:
        stmt = pg_insert(SurveyResponse).values(user_id=user_id, **values)
        stmt = stmt.on_conflict_do_update(
            index_elements=["user_id"],
            set_={column: stmt.excluded[column] for column in values},
        ).returning(SurveyResponse.id)
        row_id = (await self._session.execute(stmt)).scalar_one()
        await self._session.commit()
        # Re-read through the ORM: the Core upsert bypasses the identity map, so
        # an instance loaded earlier in this session would otherwise keep its
        # stale values (same reason OrgRepository.get_ai_settings uses
        # populate_existing).
        result = await self._session.execute(
            select(SurveyResponse)
            .where(SurveyResponse.id == row_id)
            .execution_options(populate_existing=True)
        )
        return result.scalar_one()
```

`backend/src/services/survey_service.py`:

```python
    async def save_draft(self, user_id: uuid.UUID, values: dict[str, Any]) -> SurveyResponse:
        """Upsert the caller's draft; a completed survey can no longer be edited.

        One ON CONFLICT statement rather than get-then-create: the table has
        UNIQUE(user_id), so two concurrent first saves would otherwise race and
        the loser got a raw 500 from the constraint.
        """
        row = await self._surveys.get_by_user_id(user_id)
        if row is not None and row.status == "complete":
            raise SurveyAlreadyCompleteError
        return await self._surveys.create_or_update(user_id, {**values, "status": "in_progress"})
```

(The `complete`-status pre-check stays: it is a business rule with its own 409, and it is not what the
race was about.)

- [ ] **Step 4: Run test to verify it passes**

```
cd backend
uv run pytest tests/integration/test_routers/test_survey_flow.py -v
uv run poe format && uv run poe lint && uv run poe test
```

Watch `test_partial_put_keeps_other_fields` and `test_explicit_null_clears_a_field`: the `set_` dict is
built from `values`, so only submitted keys are written — which is exactly the existing PATCH-like
semantics those two tests pin.

- [ ] **Step 5: Commit**

```
git add backend/src/repositories/base.py backend/src/repositories/survey_repository.py backend/src/services/survey_service.py backend/tests/integration/test_routers/test_survey_flow.py
git commit -m "$(cat <<'EOF'
Upsert the survey draft instead of get-then-create

Review finding 6.5. survey_responses has UNIQUE(user_id), so two
concurrent first saves raced and the loser got a raw 500 from the
constraint. One ON CONFLICT DO UPDATE statement makes the second save an
update. Partial-update and explicit-null semantics are unchanged (only
submitted keys are written).

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 10: Enforce one interview conversation per user in the DB (6.5 — migration 3/3)

`InterviewService` treats "one `interview` conversation per user" as an invariant — `_interview_
conversation` takes `conversations[0]` and `open_interview` is check-then-create — but nothing in the
DB enforces it, so two concurrent openers create two rows and one transcript becomes invisible.

**Live data:** creates a *partial* unique index on `conversations (user_id) WHERE kind = 'interview'`.
Additive; writes no rows. **It fails if any user already has two interview conversations — and prod
runs `alembic upgrade head` before binding the port, so that failure would stop the release.** Step 1
verifies prod first. **This migration deliberately does NOT de-duplicate**: an interview conversation
is a learner's transcript, and silently deleting one to make an index build is not a decision a
migration gets to make. If duplicates exist, stop and escalate. Reversible without loss.

**Files:**
- Create: `backend/alembic/versions/c3d4e5f6a7b8_one_interview_conversation_per_user.py`
- Modify: `backend/src/db/models/conversation.py` (lines 18-39, `Conversation.__table_args__`)
- Create test: `backend/tests/integration/test_models/test_interview_uniqueness.py`

**Interfaces:**
- Produces: revision `c3d4e5f6a7b8`, `down_revision = "b2c3d4e5f6a7"`; index
  `uq_conversations_interview_user_id` (unique, partial on `kind = 'interview'`). Declared on the
  model too, so `Base.metadata.create_all` gives integration tests the same schema as prod.

- [ ] **Step 1: Write the failing test** (and first, verify prod)

**Verify against prod before writing the migration** (read-only):

```sql
SELECT user_id, count(*)
FROM conversations
WHERE kind = 'interview'
GROUP BY user_id
HAVING count(*) > 1;
```

Expected: **zero rows**. If any row comes back, STOP — do not ship this migration and do not delete
anything. Report the user ids to Matthias; he decides which transcript survives, and the cleanup
happens as a separate, human-approved data fix before this task resumes.

Create `backend/tests/integration/test_models/test_interview_uniqueness.py`:

```python
from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from sqlalchemy.exc import IntegrityError

from src.repositories.conversation_repository import ConversationRepository
from tests.fixtures.factories import create_user

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


async def test_a_user_cannot_have_two_interview_conversations(db_session: AsyncSession) -> None:
    """InterviewService treats "one interview per user" as an invariant
    (_interview_conversation takes conversations[0]); the DB must enforce it, or
    a concurrent double-open hides one learner's transcript forever."""
    user = await create_user(db_session, email="one-interview@example.com")
    conversations = ConversationRepository(db_session)
    await conversations.create(user_id=user.id, kind="interview")

    with pytest.raises(IntegrityError):
        await conversations.create(user_id=user.id, kind="interview")
    await db_session.rollback()


async def test_the_guard_is_partial_and_leaves_other_kinds_alone(
    db_session: AsyncSession,
) -> None:
    """Chat conversations are many-per-user by design — the index must be
    partial, not a blanket unique on user_id."""
    user = await create_user(db_session, email="many-chats@example.com")
    conversations = ConversationRepository(db_session)

    first = await conversations.create(user_id=user.id, kind="chatbot")
    second = await conversations.create(user_id=user.id, kind="chatbot")

    assert first.id != second.id


async def test_two_users_can_each_have_an_interview(db_session: AsyncSession) -> None:
    conversations = ConversationRepository(db_session)
    one = await create_user(db_session, email="interview-a@example.com")
    two = await create_user(db_session, email="interview-b@example.com")

    await conversations.create(user_id=one.id, kind="interview")
    await conversations.create(user_id=two.id, kind="interview")
```

- [ ] **Step 2: Run test to verify it fails**

```
cd backend
uv run pytest tests/integration/test_models/test_interview_uniqueness.py -v
```

Expected: `test_a_user_cannot_have_two_interview_conversations` fails with
`DID NOT RAISE <class 'sqlalchemy.exc.IntegrityError'>`. The other two pass already and are the
regression net proving the guard stays partial.

- [ ] **Step 3: Write minimal implementation**

`backend/src/db/models/conversation.py` — add `Index` to the imports and to `__table_args__`:

```python
from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Text, func, text
```

```python
class Conversation(Base):
    __tablename__ = "conversations"
    __table_args__ = (
        CheckConstraint(f"kind IN ({_KINDS})", name="kind"),
        # A learner has exactly one interview (InterviewService._interview_
        # conversation takes conversations[0], open_interview is idempotent), but
        # chat kinds are many-per-user — hence a PARTIAL unique index rather than
        # a unique constraint. Declared on the model as well as in migration
        # c3d4e5f6a7b8 so the metadata-built test schema matches prod.
        Index(
            "uq_conversations_interview_user_id",
            "user_id",
            unique=True,
            postgresql_where=text("kind = 'interview'"),
        ),
    )
```

Create `backend/alembic/versions/c3d4e5f6a7b8_one_interview_conversation_per_user.py`:

```python
"""one interview conversation per user

InterviewService treats "one `interview` conversation per user" as an invariant —
`_interview_conversation` returns `conversations[0]` and `open_interview` is
check-then-create — but nothing enforced it, so two concurrent openers could
create two rows and leave one transcript permanently invisible.

A PARTIAL unique index, not a unique constraint: chat kinds are many-per-user by
design, so only `kind = 'interview'` is constrained.

Live data: additive, writes no rows, `conversations` is small. It DOES validate
existing rows — verified beforehand against prod that no user has two interview
conversations (query in the plan/commit message). This migration deliberately
does not de-duplicate: an interview conversation is a learner's transcript, and
choosing which one to destroy is a human decision, not a migration's.

Reversible without loss (the downgrade drops the index).

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-07-31

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "c3d4e5f6a7b8"
down_revision: str | None = "b2c3d4e5f6a7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_INDEX_NAME = "uq_conversations_interview_user_id"


def upgrade() -> None:
    op.create_index(
        _INDEX_NAME,
        "conversations",
        ["user_id"],
        unique=True,
        postgresql_where=sa.text("kind = 'interview'"),
    )


def downgrade() -> None:
    op.drop_index(_INDEX_NAME, table_name="conversations")
```

Then make the service's create path fail gracefully rather than 500 if it loses the race — in
`backend/src/services/interview_service.py::open_interview`, wrap the create and re-read:

```python
        conversation = await self._conversations.create(user_id=user.id, kind=_KIND)
```

becomes

```python
        try:
            conversation = await self._conversations.create(user_id=user.id, kind=_KIND)
        except IntegrityError:
            # Lost the race against a concurrent opener (partial unique index
            # uq_conversations_interview_user_id). The other request's greeting
            # is the real one — return it instead of failing this caller.
            existing = await self._interview_conversation(user.id)
            if existing is None:  # pragma: no cover - the index guarantees a row
                raise
            rows = await self._messages.list_for_conversation(existing.id)
            greeting = next((m.content for m in rows if m.role == "assistant"), "")
            return InterviewOpenerResponse(conversation_id=existing.id, greeting=greeting)
```

with `from sqlalchemy.exc import IntegrityError` added to the imports. Note the ordering constraint:
the `except` branch must come *after* the LLM call in the existing code (it already does — the
conversation is created only once a greeting exists).

- [ ] **Step 4: Run test to verify it passes**

```
cd backend
uv run poe upgrade
uv run alembic current          # expect: c3d4e5f6a7b8 (head)
uv run pytest tests/integration/test_models/test_interview_uniqueness.py tests/unit/test_interview_service.py -v
uv run poe format && uv run poe lint && uv run poe test
```

- [ ] **Step 5: Commit**

```
git add backend/alembic/versions/c3d4e5f6a7b8_one_interview_conversation_per_user.py backend/src/db/models/conversation.py backend/src/services/interview_service.py backend/tests/integration/test_models/test_interview_uniqueness.py
git commit -m "$(cat <<'EOF'
Enforce one interview conversation per user

Review finding 6.5. InterviewService treats it as an invariant
(_interview_conversation takes conversations[0]) but nothing enforced it,
so a concurrent double-open could hide a learner's transcript. Partial
unique index on conversations(user_id) WHERE kind='interview' (chat kinds
stay many-per-user), plus a graceful loser path in open_interview.

Migration c3d4e5f6a7b8 (revises b2c3d4e5f6a7). Verified against prod
first: no user has two interview conversations. The migration
deliberately does not de-duplicate.

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 11: VERIFY FIRST — is `UNIQUE (module_id, sort_order)` safe on live data? (6.5, investigation)

**This task ships no migration by default.** I cannot prove statically that the live data is free of
duplicate `sort_order` values within a module, and there is positive reason to expect duplicates:
`create_lesson`/`create_module` assign `max(sort_order)+1` while `reorder_lessons` rewrites 0-based
indices (`content_service.py:115-126`), migration `b4e5f6a7c8d9` moved three modules between tracks
*keeping their sort_order*, and `f3a4b5c6d7e8` inserted an Introduction track/module/lesson all at
`sort_order = 0`. A blind `CREATE UNIQUE INDEX` here would raise inside the automatic
`alembic upgrade head` and stop the release. The code-side determinism fix already shipped in Task 6,
so nothing is blocked on this.

**Files:**
- Create: `backend/scripts/check_sort_order_uniqueness.sql` (a read-only investigation query kept in
  the repo so it can be re-run)
- Conditionally create (only if the check is clean AND Matthias approves):
  `backend/alembic/versions/d4e5f6a7b8c9_unique_sort_order.py` with
  `down_revision = "c3d4e5f6a7b8"`

**Interfaces:**
- Produces: a written answer in the commit message — clean or not, with counts.

- [ ] **Step 1: Write the failing test**

No test yet: the question is about production data, not behaviour. Create
`backend/scripts/check_sort_order_uniqueness.sql`:

```sql
-- Read-only. Answers: can we add UNIQUE (module_id, sort_order) on lessons and
-- UNIQUE (track_id, sort_order) on modules without the migration raising?
-- Run against PROD (and the dev DB) before writing any such migration:
--   psql "$PGURL" -f backend/scripts/check_sort_order_uniqueness.sql
-- Any row returned by either query = a blocker. See plan Task 11.

\echo '== lessons with a duplicate sort_order inside one module =='
SELECT module_id, sort_order, count(*) AS lessons
FROM lessons
GROUP BY module_id, sort_order
HAVING count(*) > 1
ORDER BY count(*) DESC;

\echo '== modules with a duplicate sort_order inside one track =='
SELECT track_id, sort_order, count(*) AS modules
FROM modules
GROUP BY track_id, sort_order
HAVING count(*) > 1
ORDER BY count(*) DESC;

\echo '== tracks with a duplicate sort_order =='
SELECT sort_order, count(*) AS tracks
FROM tracks
GROUP BY sort_order
HAVING count(*) > 1
ORDER BY count(*) DESC;
```

- [ ] **Step 2: Run test to verify it fails** — i.e. run the check and record the answer

```
cd "AI ENABLEMENT HUB REBUILD"
psql "$PGURL" -f backend/scripts/check_sort_order_uniqueness.sql
```

Record all three result sets. Then branch:
- **Any duplicates → STOP.** Do not write a migration. The correct sequence would be a data
  normalisation pass (renumber each group densely by `(sort_order, id)`), which changes what learners
  see and therefore needs Matthias's sign-off as its own piece of work. Note the counts in the commit
  message and leave the constraint unshipped — Task 6 already made the *reading* side deterministic,
  which is the part that actually affected behaviour.
- **Zero duplicates everywhere → still do not ship blind.** A unique constraint also breaks
  `reorder_lessons`, which writes `0..N-1` in one statement: any permutation passes through
  intermediate states where two lessons briefly share a value. With the single bulk `UPDATE` from
  Task 5 that is evaluated as one statement (so it is fine for a non-deferrable index in practice
  *only* because Postgres checks uniqueness per row as the statement progresses — it is NOT
  guaranteed). Shipping this constraint therefore requires either `DEFERRABLE INITIALLY DEFERRED`
  (which Postgres supports only for constraints, not indexes) or a two-phase renumber. Report both
  the clean result and this cost to Matthias and let him decide; do not invent the answer.

- [ ] **Step 3: Write minimal implementation**

Only if Step 2 came back clean *and* Matthias approved the deferrable-constraint approach, create
`backend/alembic/versions/d4e5f6a7b8c9_unique_sort_order.py`:

```python
"""unique (module_id, sort_order) on lessons — DEFERRABLE

ONLY ship this after backend/scripts/check_sort_order_uniqueness.sql returns
zero rows against prod (see plan Task 11). DEFERRABLE INITIALLY DEFERRED is
required, not optional: reorder_lessons rewrites 0..N-1 for a whole module in one
transaction, which passes through intermediate states where two lessons share a
value.

Live data: adds one unique constraint. It validates existing rows, so it RAISES
on any duplicate — and prod runs `alembic upgrade head` before binding the port.
Reversible without loss.

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: TBD

"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "d4e5f6a7b8c9"
down_revision: str | None = "c3d4e5f6a7b8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_unique_constraint(
        op.f("uq_lessons_module_id_sort_order"),
        "lessons",
        ["module_id", "sort_order"],
        deferrable=True,
        initially="DEFERRED",
    )


def downgrade() -> None:
    op.drop_constraint(op.f("uq_lessons_module_id_sort_order"), "lessons", type_="unique")
```

with the matching model change in `backend/src/db/models/learning.py`:

```python
class Lesson(Base):
    __tablename__ = "lessons"
    __table_args__ = (
        UniqueConstraint(
            "module_id", "sort_order", deferrable=True, initially="DEFERRED"
        ),
    )
```

- [ ] **Step 4: Run test to verify it passes**

If shipped:

```
cd backend
uv run poe upgrade
uv run alembic current          # expect: d4e5f6a7b8c9 (head)
uv run pytest tests/integration/test_routers/test_admin_content.py -v   # reorder must still work
uv run poe format && uv run poe lint && uv run poe test
```

If not shipped: `uv run poe lint` only (the SQL script is not linted), and the commit is the script
plus the recorded answer.

- [ ] **Step 5: Commit**

```
git add backend/scripts/check_sort_order_uniqueness.sql
git commit -m "$(cat <<'EOF'
Add the sort_order uniqueness pre-flight check (finding 6.5)

Review finding 6.5 asks whether UNIQUE (module_id, sort_order) is safe.
It cannot be answered from the code: creation uses max+1, reorder writes
0-based indices, and two migrations placed rows at fixed sort_orders.
This is the read-only query that answers it against prod.

Result of this run: <PASTE THE THREE RESULT SETS HERE>

No migration shipped in this commit. The behavioural half of the finding
(reads skipping tied siblings) is already fixed by the (sort_order, id)
ordering change.

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 12: Reject cross-track prerequisites, and prove the create path cannot cycle (6.6)

**Decision stated up front: no DB constraint.** Two reasons, both evidence-based.
1. **A cycle cannot be expressed as a CHECK.** It is a graph property over many rows; enforcing it in
   the DB needs a trigger or a recursive-CTE constraint trigger — real machinery, and a per-insert
   recursive query, for an edge case the application can prevent outright.
2. **A cross-track CHECK would reject live data.** Migration `b4e5f6a7c8d9:79-81` *deliberately kept*
   a cross-track edge (Integrating ← Using AI safely) when it split General into I and II, and
   documented it as such. A DB-level rule would make that row illegal and any future
   `alembic upgrade`/restore of it fail. So the new rule is applied to *new* edges at the service
   layer and the existing edge is grandfathered.

There is also a finding-within-the-finding worth recording: **the application cannot currently create
a cycle at all.** `ModulePrerequisite` rows are written in exactly one place —
`ContentRepository.create_module` (`content_repository.py:72-88`), called only by
`ContentService.create_module` — and a brand-new module has no dependents yet, so its outgoing edges
can never close a loop. Cycles in prod could only come from `db/sync_content_from_supabase.py` or
manual SQL. The cycle check below is therefore a *guard for the future* (the first endpoint that lets
an admin add a prerequisite to an existing module) plus an explicit test pinning today's reality.

**Files:**
- Modify: `backend/src/services/content_service.py` (lines 49-83 `create_module`)
- Create: `backend/tests/unit/test_prerequisite_validation.py`
- Modify test: `backend/tests/integration/test_routers/test_admin_content.py` (append one case)

**Interfaces:**
- Consumes: `AbstractContentRepository.get_module`, `AbstractContentRepository.list_prerequisites`.
- Produces: `ContentService._reject_invalid_prerequisites(track_id: uuid.UUID, prerequisite_modules:
  list[Module]) -> None` raising `InvalidRequestError` (→ 400 via the existing `DomainError` handler);
  and module-level `has_path(edges: dict[uuid.UUID, set[uuid.UUID]], start: uuid.UUID, target:
  uuid.UUID) -> bool`, a pure reachability helper for the future edge-adding path.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/unit/test_prerequisite_validation.py`:

```python
from __future__ import annotations

import uuid
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock

import pytest

from src.repositories.base import AbstractContentRepository
from src.services.content_service import ContentService, has_path
from src.services.exceptions import InvalidRequestError


def _module(track_id: uuid.UUID) -> Any:
    return SimpleNamespace(id=uuid.uuid4(), track_id=track_id, sort_order=0, title="M")


def _service(track_id: uuid.UUID, modules: dict[uuid.UUID, Any]) -> ContentService:
    content = AsyncMock(spec=AbstractContentRepository)
    content.get_track.return_value = SimpleNamespace(id=track_id, name="T")
    content.get_module.side_effect = lambda module_id: modules.get(module_id)
    content.max_module_sort_order.return_value = 0
    content.list_prerequisites.return_value = []
    content.create_module.side_effect = lambda *a, **k: _module(track_id)
    return ContentService(content)


async def test_a_prerequisite_in_another_track_is_rejected() -> None:
    """A cross-track edge locks every dependent with no edge drawn to explain
    why — the frontend drops cross-track predecessors from its layout."""
    track_id = uuid.uuid4()
    foreign = _module(uuid.uuid4())
    service = _service(track_id, {foreign.id: foreign})

    with pytest.raises(InvalidRequestError) as excinfo:
        await service.create_module(track_id, "New", None, [foreign.id])

    assert "same track" in str(excinfo.value.message)


async def test_a_prerequisite_in_the_same_track_is_accepted() -> None:
    track_id = uuid.uuid4()
    sibling = _module(track_id)
    service = _service(track_id, {sibling.id: sibling})

    module = await service.create_module(track_id, "New", None, [sibling.id])

    assert module is not None


async def test_a_new_module_can_never_close_a_cycle() -> None:
    """Pins today's reality: create_module is the only writer of prerequisite
    edges, and a brand-new module has no dependents, so its outgoing edges
    cannot form a loop. If a future endpoint adds edges to an EXISTING module,
    it must call has_path — this test is the reminder."""
    a, b = uuid.uuid4(), uuid.uuid4()
    edges = {a: {b}}

    assert has_path(edges, b, a) is False
    assert has_path(edges, a, b) is True


def test_has_path_finds_a_transitive_route() -> None:
    a, b, c = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    edges = {a: {b}, b: {c}}

    assert has_path(edges, a, c) is True
    assert has_path(edges, c, a) is False


def test_has_path_terminates_on_an_existing_cycle() -> None:
    """Prod could already hold a cycle (written by the sync script or by hand);
    the walk must not spin forever on it."""
    a, b = uuid.uuid4(), uuid.uuid4()
    edges = {a: {b}, b: {a}}

    assert has_path(edges, a, a) is True
```

- [ ] **Step 2: Run test to verify it fails**

```
cd backend
uv run pytest tests/unit/test_prerequisite_validation.py -v
```

Expected: collection fails with
`ImportError: cannot import name 'has_path' from 'src.services.content_service'`.

- [ ] **Step 3: Write minimal implementation**

In `backend/src/services/content_service.py`, add the pure helper and the validation, and update
`__all__`:

```python
__all__ = ["ContentService", "has_path"]


def has_path(
    edges: dict[uuid.UUID, set[uuid.UUID]], start: uuid.UUID, target: uuid.UUID
) -> bool:
    """Is `target` reachable from `start` by following prerequisite edges?

    `edges` maps module_id -> the module_ids it depends on. Used to refuse an
    edge that would close a cycle: adding `m depends on p` is a cycle iff `m` is
    already reachable from `p`. Iterative with a visited set, so it terminates
    even if the stored graph ALREADY contains a cycle (prod rows can predate this
    check — `db/sync_content_from_supabase.py` and manual SQL both bypass it).
    """
    seen: set[uuid.UUID] = set()
    stack = [start]
    while stack:
        current = stack.pop()
        if current == target and current in seen:
            return True
        if current in seen:
            continue
        seen.add(current)
        for nxt in edges.get(current, ()):
            if nxt == target:
                return True
            stack.append(nxt)
    return False
```

then, inside `create_module`, replace the existence-only prerequisite loop (currently lines 62-68):

```python
        deduped: list[uuid.UUID] = []
        for prereq_id in prerequisite_ids:
            if prereq_id not in deduped:
                deduped.append(prereq_id)
        prerequisite_modules: list[Module] = []
        for prereq_id in deduped:
            prereq = await self._content.get_module(prereq_id)
            if prereq is None:
                raise NotFoundError("Prerequisite module")
            prerequisite_modules.append(prereq)
        self._reject_cross_track_prerequisites(track_id, prerequisite_modules)
```

and add the private validator:

```python
    def _reject_cross_track_prerequisites(
        self, track_id: uuid.UUID, prerequisite_modules: list[Module]
    ) -> None:
        """A prerequisite in another track locks every dependent with no edge
        drawn to explain why (the learning-path layout only draws intra-track
        edges), so new ones are refused here.

        Deliberately application-level, not a DB constraint: migration
        b4e5f6a7c8d9 KEPT one cross-track edge on purpose when it split General
        into I and II, so a CHECK would make live data illegal. That row is
        grandfathered; new ones are not allowed.

        Cycles are not checked here because they are unreachable on this path: a
        brand-new module has no dependents, so its outgoing edges cannot close a
        loop. Any future endpoint that adds an edge to an EXISTING module must
        call `has_path` before inserting.
        """
        foreign = [
            prereq.title for prereq in prerequisite_modules if prereq.track_id != track_id
        ]
        if foreign:
            msg = (
                "prerequisites must belong to the same track as the module: "
                + ", ".join(sorted(foreign))
            )
            raise InvalidRequestError(msg)
```

Append one end-to-end case to `backend/tests/integration/test_routers/test_admin_content.py`:

```python
async def test_creating_a_module_with_a_cross_track_prerequisite_is_400(
    client: AsyncClient, admin: User, test_settings: Settings, db_session: AsyncSession
) -> None:
    home = await create_track(db_session, "Home Track")
    elsewhere = await create_track(db_session, "Other Track", sort_order=1)
    foreign_module = await create_module(db_session, elsewhere, "Foreign")

    response = await client.post(
        "/api/admin/modules",
        json={
            "track_id": str(home.id),
            "title": "Depends across tracks",
            "prerequisite_ids": [str(foreign_module.id)],
        },
        headers=auth_headers(admin, test_settings),
    )

    assert response.status_code == 400
    assert "same track" in response.json()["error"]["message"]
```

(Check the exact request field names against `backend/src/schemas/admin_content.py:55-62` and the route
path in `backend/src/routers/admin_content.py` before running — adjust the JSON body to match, not the
assertion.)

- [ ] **Step 4: Run test to verify it passes**

```
cd backend
uv run pytest tests/unit/test_prerequisite_validation.py tests/integration/test_routers/test_admin_content.py -v
uv run poe format && uv run poe lint && uv run poe test
```

- [ ] **Step 5: Commit**

```
git add backend/src/services/content_service.py backend/tests/unit/test_prerequisite_validation.py backend/tests/integration/test_routers/test_admin_content.py
git commit -m "$(cat <<'EOF'
Reject cross-track prerequisites; add a reusable cycle check

Review finding 6.6 (carried from prior 10.1). New prerequisite edges must
stay inside one track: a cross-track edge locks dependents with no edge
drawn to explain why. No DB constraint, on purpose — a cycle is not
expressible as a CHECK, and migration b4e5f6a7c8d9 deliberately kept one
cross-track edge, which a CHECK would make illegal. That row is
grandfathered.

Also records that the app cannot currently create a cycle at all
(create_module is the only edge writer and a new module has no
dependents); `has_path` is the guard the first edge-adding endpoint must
use, with tests pinning both facts.

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 13: The unit-of-work seam, scoped to survey completion and proposal approval (6.1b)

**Scope decision: survey completion + proposal approval only.** Converting all 17 repositories would
touch every service and every test in one sitting; these two are the flows where a half-applied write
is user-visible and unrepairable. Task 1 already made the survey seed *converge* after a failure; this
task makes it *never happen*, and does the same for proposal approval (today: `update_lesson` commits
the rewritten lesson, then `set_approved` commits — a failure between them leaves the lesson changed
while the proposal still reads `pending`, and re-approving mis-reports "superseded"). Every other
repository keeps its internal commit; nothing else changes.

**Seam design.** Repositories keep owning the session. Each participating write gains a **flush-only
twin named `stage_*`**, and the existing committing method is rewritten to delegate to it plus
`commit()` — so there is exactly one copy of each statement and no other caller changes behaviour. A
new `UnitOfWork` object (repository layer, wraps the same request-scoped `AsyncSession`) gives the
service one `commit()`; a service depending on it is a downward call, so the no-service-to-service
rule holds.

**Files:**
- Create: `backend/src/repositories/unit_of_work.py`
- Modify: `backend/src/repositories/base.py` (add `AbstractUnitOfWork`; add the `stage_*` abstract
  methods to `AbstractAssignmentRepository`, `AbstractSurveyRepository`, `AbstractContentRepository`,
  `AbstractProposalRepository`; extend `__all__`)
- Modify: `backend/src/repositories/assignment_repository.py` (lines 167-249),
  `backend/src/repositories/survey_repository.py` (lines 28-33),
  `backend/src/repositories/content_repository.py` (lines 160-165),
  `backend/src/repositories/proposal_repository.py` (lines 106-117)
- Modify: `backend/src/services/survey_service.py` (`__init__`, `complete`, `_seed_assignments`),
  `backend/src/services/content_improvement_service.py` (`__init__`, `_apply` tail)
- Modify: `backend/src/core/dependencies/domain.py` (`get_unit_of_work`, `get_survey_service`),
  `backend/src/core/dependencies/content_ai.py` (`get_content_improvement_service`)
- Modify tests: `backend/tests/unit/test_survey_service.py`,
  `backend/tests/unit/test_content_improvement_review.py`,
  `backend/tests/unit/test_content_improvement_service.py`,
  `backend/tests/unit/test_content_improvement_critique.py`
- Create test: `backend/tests/integration/test_repositories/test_unit_of_work.py`

**Interfaces:**
- Produces:
  - `AbstractUnitOfWork.commit() -> None`, `.rollback() -> None`; `UnitOfWork(session: AsyncSession)`.
  - `AssignmentRepository.stage_user_tracks/stage_user_modules/stage_user_lessons(user_id, ids,
    assigned, *, assigned_via="manual") -> None` (same signature as the committing versions).
  - `SurveyRepository.stage_update(row: SurveyResponse, values: dict[str, Any]) -> SurveyResponse`.
  - `ContentRepository.stage_lesson_update(lesson: Lesson, values: dict[str, Any]) -> Lesson`.
  - `ProposalRepository.stage_approved(proposal, *, edited_blocks, reviewed_by) -> None`.
  - `SurveyService(surveys, content, assignments, uow)`;
    `ContentImprovementService(proposals, feedback, content, llm, calibration_notes, uow)`.

**Tests that WILL break, and how:** every unit test that constructs one of the two services
positionally needs the extra `uow` argument — `tests/unit/test_content_improvement_review.py::_service`
(lines 42-56), `tests/unit/test_content_improvement_service.py`,
`tests/unit/test_content_improvement_critique.py`, and the `_service` helper added in Task 1. And every
assertion naming a now-staged method must be renamed: in `test_content_improvement_review.py`,
`content.update_lesson.assert_awaited_once_with(...)` becomes
`content.stage_lesson_update.assert_awaited_once_with(...)` and
`proposals.set_approved.assert_awaited_once_with(...)` becomes
`proposals.stage_approved.assert_awaited_once_with(...)` (at least four occurrences — grep for both
names). `AsyncMock(spec=Abstract...)` picks the new methods up automatically once they are declared
abstract, so no mock plumbing changes. **Integration tests need no changes**: `conftest.py:158-167`
binds the session with `join_transaction_mode="create_savepoint"`, so an application `commit()` only
releases a savepoint — staging N writes then committing once persists exactly as before within the
test's outer transaction.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/integration/test_repositories/test_unit_of_work.py`:

```python
"""The two flows that must be all-or-nothing: assessment completion and
proposal approval. Both used to commit each step separately."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from sqlalchemy import func, select

from src.db.models import SurveyResponse, UserLesson, UserModule, UserTrack
from src.repositories.assignment_repository import AssignmentRepository
from src.repositories.content_repository import ContentRepository
from src.repositories.survey_repository import SurveyRepository
from src.repositories.unit_of_work import UnitOfWork
from src.services.survey_service import SurveyService
from tests.fixtures.factories import (
    VALID_ANSWERS,
    create_lesson,
    create_module,
    create_track,
    create_user,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


async def test_staged_assignment_writes_are_invisible_until_the_uow_commits(
    db_session: AsyncSession,
) -> None:
    user = await create_user(db_session, email="uow-stage@example.com")
    track = await create_track(db_session, "UoW Track")
    assignments = AssignmentRepository(db_session)
    uow = UnitOfWork(db_session)

    await assignments.stage_user_tracks(user.id, [track.id], True)
    # Still inside the unit of work: the row is in the session, not committed.
    assert db_session.in_transaction()

    await uow.commit()

    count = await db_session.execute(
        select(func.count()).select_from(UserTrack).where(UserTrack.user_id == user.id)
    )
    assert count.scalar_one() == 1


async def test_a_failing_seed_write_rolls_back_the_whole_completion(
    db_session: AsyncSession,
) -> None:
    """One transaction: if the last staged write fails, the survey must NOT be
    scored and no partial assignment rows may survive."""
    user = await create_user(db_session, email="uow-atomic@example.com")
    track = await create_track(db_session, "Atomic Track", required_level="explore")
    module = await create_module(db_session, track, "Atomic Module")
    await create_lesson(db_session, module, "Atomic Lesson")
    surveys = SurveyRepository(db_session)
    await surveys.create_or_update(user.id, {"status": "in_progress", **VALID_ANSWERS})

    assignments = AssignmentRepository(db_session)
    uow = UnitOfWork(db_session)
    service = SurveyService(surveys, ContentRepository(db_session), assignments, uow)

    # Force the final staged write to fail.
    async def _boom(*args: object, **kwargs: object) -> None:
        raise RuntimeError("connection reset")

    assignments.stage_user_tracks = _boom  # type: ignore[method-assign]

    with pytest.raises(RuntimeError):
        await service.complete(user.id)
    await db_session.rollback()

    for model in (UserTrack, UserModule, UserLesson):
        count = await db_session.execute(
            select(func.count()).select_from(model).where(model.user_id == user.id)
        )
        assert count.scalar_one() == 0, f"{model.__tablename__} kept a partial row"
    row = (
        await db_session.execute(select(SurveyResponse).where(SurveyResponse.user_id == user.id))
    ).scalar_one()
    assert row.status == "in_progress"
    assert row.score_level is None
```

- [ ] **Step 2: Run test to verify it fails**

```
cd backend
uv run pytest tests/integration/test_repositories/test_unit_of_work.py -v
```

Expected: collection fails with `ModuleNotFoundError: No module named 'src.repositories.unit_of_work'`.

- [ ] **Step 3: Write minimal implementation**

Create `backend/src/repositories/unit_of_work.py`:

```python
from __future__ import annotations

from typing import TYPE_CHECKING

from src.repositories.base import AbstractUnitOfWork

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

__all__ = ["UnitOfWork"]


class UnitOfWork(AbstractUnitOfWork):
    """The commit boundary for a use case that writes more than once.

    Repositories still own the session; this is the seam that lets a SERVICE
    decide where the transaction ends without reaching into the session itself.
    It lives in the repository layer, so a service depending on it is a downward
    call — the "services never call services" rule is untouched.

    Only the flows that need atomicity use it (assessment completion, proposal
    approval). Every other repository method keeps committing internally.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def commit(self) -> None:
        await self._session.commit()

    async def rollback(self) -> None:
        await self._session.rollback()
```

In `backend/src/repositories/base.py`, add to `__all__` (`"AbstractUnitOfWork",`) and define:

```python
class AbstractUnitOfWork(ABC):
    """Commit boundary handed to services that must write atomically."""

    @abstractmethod
    async def commit(self) -> None:
        """Commit everything staged on this request's session."""

    @abstractmethod
    async def rollback(self) -> None:
        """Discard everything staged on this request's session."""
```

and declare the four staged twins, e.g. in `AbstractAssignmentRepository`:

```python
    @abstractmethod
    async def stage_user_tracks(
        self,
        user_id: uuid.UUID,
        track_ids: list[uuid.UUID],
        assigned: bool,
        *,
        assigned_via: str = "manual",
    ) -> None:
        """Flush-only twin of set_user_tracks: same statement, NO commit, so a
        service can compose several writes into one transaction and commit once
        via AbstractUnitOfWork."""
```

(identically for `stage_user_modules`, `stage_user_lessons`; plus
`AbstractSurveyRepository.stage_update`, `AbstractContentRepository.stage_lesson_update`,
`AbstractProposalRepository.stage_approved` with the signatures listed under **Interfaces**.)

`backend/src/repositories/assignment_repository.py` — extract the statement, then delegate:

```python
    async def stage_user_tracks(
        self,
        user_id: uuid.UUID,
        track_ids: list[uuid.UUID],
        assigned: bool,
        *,
        assigned_via: str = "manual",
    ) -> None:
        if assigned:
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
            await self._session.execute(stmt)
        else:
            await self._session.execute(
                delete(UserTrack).where(
                    UserTrack.user_id == user_id, UserTrack.track_id.in_(track_ids)
                )
            )

    async def set_user_tracks(
        self,
        user_id: uuid.UUID,
        track_ids: list[uuid.UUID],
        assigned: bool,
        *,
        assigned_via: str = "manual",
    ) -> None:
        await self.stage_user_tracks(user_id, track_ids, assigned, assigned_via=assigned_via)
        await self._session.commit()
```

(same shape for `stage_user_modules`/`set_user_modules` and `stage_user_lessons`/`set_user_lessons`.)

`backend/src/repositories/survey_repository.py`:

```python
    async def stage_update(self, row: SurveyResponse, values: dict[str, Any]) -> SurveyResponse:
        for field, value in values.items():
            setattr(row, field, value)
        await self._session.flush()
        return row

    async def update(self, row: SurveyResponse, values: dict[str, Any]) -> SurveyResponse:
        await self.stage_update(row, values)
        await self._session.commit()
        await self._session.refresh(row)
        return row
```

`backend/src/repositories/content_repository.py`:

```python
    async def stage_lesson_update(self, lesson: Lesson, values: dict[str, Any]) -> Lesson:
        for field, value in values.items():
            setattr(lesson, field, value)
        await self._session.flush()
        return lesson

    async def update_lesson(self, lesson: Lesson, values: dict[str, Any]) -> Lesson:
        await self.stage_lesson_update(lesson, values)
        await self._session.commit()
        await self._session.refresh(lesson)
        return lesson
```

`backend/src/repositories/proposal_repository.py`:

```python
    async def stage_approved(
        self,
        proposal: LessonContentProposal,
        *,
        edited_blocks: list[Any] | None,
        reviewed_by: uuid.UUID,
    ) -> None:
        proposal.status = "approved"
        proposal.edited_blocks = edited_blocks
        proposal.reviewed_by = reviewed_by
        proposal.reviewed_at = datetime.now(UTC)
        await self._session.flush()

    async def set_approved(
        self,
        proposal: LessonContentProposal,
        *,
        edited_blocks: list[Any] | None,
        reviewed_by: uuid.UUID,
    ) -> None:
        await self.stage_approved(
            proposal, edited_blocks=edited_blocks, reviewed_by=reviewed_by
        )
        await self._session.commit()
```

`backend/src/services/survey_service.py` — take the UoW, stage everything, commit once:

```python
    def __init__(
        self,
        surveys: AbstractSurveyRepository,
        content: AbstractContentRepository,
        assignments: AbstractAssignmentRepository,
        uow: AbstractUnitOfWork,
    ) -> None:
        self._surveys = surveys
        self._content = content
        self._assignments = assignments
        self._uow = uow
```

```python
        now = datetime.now(UTC)
        # ONE transaction for the whole completion: the scored fields and all
        # three assignment writes are staged, then committed together. Task 1's
        # ordering (seed first, tracks last) is kept as belt-and-braces for any
        # failure the transaction cannot cover (e.g. the process dying between
        # the commit and the response).
        await self._seed_assignments(user_id, scores["score_level"])
        completed = await self._surveys.stage_update(
            row, {**scores, "status": "complete", "completed_at": now, "scored_at": now}
        )
        await self._uow.commit()
        return completed
```

and inside `_seed_assignments` swap the three calls to their `stage_` twins (`stage_user_modules`,
`stage_user_lessons`, `stage_user_tracks`), keeping the ordering comment.

`backend/src/services/content_improvement_service.py` — add `uow: AbstractUnitOfWork` as the last
constructor parameter (`self._uow = uow`) and replace the tail of `_apply`:

```python
        # ONE transaction: the lesson rewrite and the proposal's approved stamp
        # must land together. Committing them separately left a window where the
        # lesson was already rewritten while the proposal still read `pending`,
        # so re-approving compared the new lesson against the old base_blocks and
        # mis-reported "superseded".
        await self._content.stage_lesson_update(
            lesson, {"content_blocks": strip_ephemeral(list(blocks))}
        )
        await self._proposals.stage_approved(
            proposal, edited_blocks=admin_edits, reviewed_by=reviewer_id
        )
        await self._uow.commit()
```

DI — `backend/src/core/dependencies/domain.py`:

```python
def get_unit_of_work(session: Annotated[AsyncSession, Depends(get_session)]) -> UnitOfWork:
    """One commit boundary per request, on the same session the repositories use."""
    return UnitOfWork(session)


def get_survey_service(
    surveys: Annotated[SurveyRepository, Depends(get_survey_repository)],
    content: Annotated[ContentRepository, Depends(get_content_repository)],
    assignments: Annotated[AssignmentRepository, Depends(get_assignment_repository)],
    uow: Annotated[UnitOfWork, Depends(get_unit_of_work)],
) -> SurveyService:
    return SurveyService(surveys, content, assignments, uow)
```

with `from src.repositories.unit_of_work import UnitOfWork` added and `"get_unit_of_work"` in
`__all__`; and in `backend/src/core/dependencies/content_ai.py` add
`uow: Annotated[UnitOfWork, Depends(get_unit_of_work)]` to
`get_content_improvement_service` and pass it as the sixth argument.

Finally update the four unit-test files as listed under **Tests that WILL break**.

- [ ] **Step 4: Run test to verify it passes**

```
cd backend
uv run pytest tests/integration/test_repositories/test_unit_of_work.py -v
uv run pytest tests/unit/test_survey_service.py tests/unit/test_content_improvement_review.py tests/unit/test_content_improvement_service.py tests/unit/test_content_improvement_critique.py -v
uv run pytest tests/integration/test_routers/test_survey_flow.py tests/integration/test_routers/test_admin_content_improvement.py -v
uv run poe format && uv run poe lint && uv run poe test
```

- [ ] **Step 5: Commit**

```
git add backend/src/repositories/unit_of_work.py backend/src/repositories/base.py backend/src/repositories/assignment_repository.py backend/src/repositories/survey_repository.py backend/src/repositories/content_repository.py backend/src/repositories/proposal_repository.py backend/src/services/survey_service.py backend/src/services/content_improvement_service.py backend/src/core/dependencies/domain.py backend/src/core/dependencies/content_ai.py backend/tests
git commit -m "$(cat <<'EOF'
Add a unit-of-work seam for assessment completion and proposal approval

Review finding 6.1b. Repositories commit internally, so no multi-step
operation was atomic: completing an assessment wrote across four
transactions, and approving a proposal committed the rewritten lesson
before stamping the proposal (a failure between them left the lesson
changed while the proposal read `pending`, and re-approving mis-reported
"superseded").

Each participating write gains a flush-only `stage_*` twin and the
committing method delegates to it, so no other caller changes. A new
repository-layer UnitOfWork gives the two services one commit() —
services -> repositories, so the no-service-to-service rule holds.
Scoped to these two flows on purpose; every other repository keeps its
internal commit.

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 14: DECISION — validation and a size ceiling on admin lesson writes (6.8)

**This task needs Matthias's answer before any code is written.** Do not guess.

`routers/admin_content.py:107-120` → `ContentService.update_lesson` persists whatever
`content_blocks` array the admin editor sends, after only stripping ephemeral SAS URLs. The strict
`validate_content_blocks` is wired **only** into the AI path
(`content_improvement_service.py:589,666`). So an AI draft is gated and a human save is not — and
there is no request-size ceiling on this endpoint, unlike media uploads (`MAX_UPLOAD_BYTES`) and CSV
invites (`MAX_INVITE_CSV_BYTES`).

**Why this is genuinely ambiguous:** per project history, **66 of 91 live lessons lack the nested ids
`validate_content_blocks` requires**. Turning the validator on for human saves would make those 66
lessons unsavable until they are migrated — the asymmetry may well be deliberate.

**Option A — document the asymmetry, add only the size ceiling.** Effort **S** (~1 h).
- Add `MAX_LESSON_BLOCKS_BYTES = 1_048_576` (1 MiB, matching the CSV ceiling) checked in
  `routers/admin_content.py::update_lesson` before the service call, raising the existing
  `PayloadTooLargeError` (→ 413, already handled in `main.py:281-283`).
- Add a comment in `ContentService.update_lesson` and a line in the backend `CLAUDE.md` recording
  that human saves are trusted by design and why (66/91 lessons predate the validator).
- Cost: none to existing content. Risk: an admin can still save structurally broken blocks that the
  learner page may fail to render.

**Option B — validate human saves too, behind a compatibility rule.** Effort **M** (~1 day).
- Run `validate_content_blocks` on `update_lesson`, but only **reject regressions**: compute the
  validator's errors for the *stored* blocks first and reject only errors the save *introduces*. A
  lesson that was already non-conforming stays savable; a save cannot make it worse. This is the same
  shape as the existing `check_media_immutable(base, blocks)` comparison, so the pattern is proven.
- Plus the 1 MiB ceiling from Option A.
- Cost: needs a census run first (`db/content_tools/`) to confirm no *current* lesson would be
  rejected by the diff rule; ~1 day including tests for the "already broken, still savable" case.
- Risk: a false positive blocks a real edit mid-session, on the highest-traffic admin surface.

**Recommendation: Option A now, Option B when the nested-id backfill happens.** The 66/91 figure says
the content, not the code, is what is out of date; adding a hard gate before that is fixed converts a
rendering risk into an authoring outage. The 1 MiB ceiling is unambiguously worth having either way.

- [ ] **Step 1: Put both options to Matthias** (paste the two option blocks above; ask specifically
      whether human lesson saves should be gated, and confirm 1 MiB is the right ceiling).
- [ ] **Step 2: Record his answer** in this plan file under this task, dated.
- [ ] **Step 3: Implement the chosen option** as its own task with the standard 5 steps, written after
      the decision is recorded — including the exact test for the chosen behaviour.
- [ ] **Step 4: Run** `cd backend && uv run poe format && uv run poe lint && uv run poe test`.
- [ ] **Step 5: Commit** with the decision quoted in the commit message.

---

## Decision needed (no code in this plan): conversation and message retention (6.7)

`conversations` and `messages` grow forever by design — "save all dialogue for admin analysis" is the
feature. The daily cleanup task (`main.py:77-99`) purges only auth tokens and sessions, and
`ConversationRepository.list_for_user` (`conversation_repository.py:45-51`) has no `LIMIT`. That is
fine today: `interview` is one row per user, and the chat surfaces are still dark per project memory.
It stops being fine when real ChatPanels mount for a few hundred learners. **No code is proposed here
— this is a product/legal decision about how long a learner's dialogue is kept.**

Options, with what each costs:

1. **Keep everything, cap the read (S, ~2 h).** Add `limit`/`offset` to `list_for_user` and the
   history endpoint. Storage still grows without bound (a 20-turn chat is a few KB, so ~100 k
   messages ≈ tens of MB — genuinely small for years), but no endpoint can ever return an unbounded
   list. **Cheapest, and it removes the only immediate technical risk.**
2. **Time-boxed retention (M, ~1 day).** Extend the existing daily cleanup loop to delete
   `conversations` older than N days where `kind != 'interview'` (interviews feed the playbook and
   must persist), cascading to messages via the existing FK. Needs: N agreed, an admin-visible note
   that chats expire, and a test. Bounds storage permanently.
3. **Per-user cap (M, ~1 day).** Keep the newest K conversations per user per kind, prune the rest
   nightly. Bounds worst-case per user rather than by age; slightly more code than option 2 and a
   less obvious rule to explain to a learner.
4. **Do nothing, revisit at rollout (S, 0 h).** Acceptable only while the chat surfaces stay
   toggled off per project. Should be recorded as a dated decision with a trigger ("revisit before
   enabling `chatbot` for any project"), not left implicit.

**Recommendation: option 1 now, and option 2's value of N decided before the chatbot surface is
enabled for a real project.** Option 1 is small and purely defensive; option 2 needs a human answer to
"how long may we keep a learner's conversation?", which is not a decision this plan can make.
