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
    AbstractUnitOfWork,
)
from src.services.exceptions import SurveyAlreadyCompleteError
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
) -> tuple[SurveyService, AsyncMock, AsyncMock, AsyncMock]:
    surveys = AsyncMock(spec=AbstractSurveyRepository)
    surveys.get_by_user_id.return_value = row

    # The real repository's `stage_update` applies the merged values and returns the
    # updated row — in particular `score_level`, which `complete()` reads off
    # its return value to pass to `_seed_assignments`. A mock that echoes back
    # the original (unscored) `row` masks that: `_seed_assignments` would bail
    # out immediately on `score_level=None` and every test would pass for the
    # wrong reason (no seed ever runs). Build the update side effect so the
    # returned row carries whatever values were written, like the ORM does.
    def _update(target_row: Any, values: dict[str, Any]) -> Any:
        return SimpleNamespace(**{**vars(target_row), **values})

    surveys.stage_update.side_effect = _update

    content = AsyncMock(spec=AbstractContentRepository)
    content.list_tracks.return_value = tracks
    content.list_modules.return_value = modules
    content.list_lesson_summaries.return_value = lessons
    assignments = AsyncMock(spec=AbstractAssignmentRepository)
    assignments.track_ids_for_user.return_value = set()
    uow = AsyncMock(spec=AbstractUnitOfWork)
    return SurveyService(surveys, content, assignments, uow), surveys, assignments, uow


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
    service, _surveys, assignments, _uow = _service(
        _row(), tracks=tracks, modules=modules, lessons=lessons
    )
    order: list[str] = []
    assignments.stage_user_tracks.side_effect = lambda *a, **k: order.append("tracks")
    assignments.stage_user_modules.side_effect = lambda *a, **k: order.append("modules")
    assignments.stage_user_lessons.side_effect = lambda *a, **k: order.append("lessons")

    await service.complete(uuid.uuid4())

    assert order == ["modules", "lessons", "tracks"]


async def test_a_failed_seed_leaves_the_survey_in_progress_so_a_retry_can_heal_it() -> None:
    """If the seed blows up the survey must NOT be marked complete — otherwise
    complete() can never re-run and the partial assignment set is permanent."""
    tracks, modules, lessons = _fixture_graph()
    service, surveys, assignments, uow = _service(
        _row(), tracks=tracks, modules=modules, lessons=lessons
    )
    assignments.stage_user_tracks.side_effect = RuntimeError("connection reset")

    with pytest.raises(RuntimeError):
        await service.complete(uuid.uuid4())

    surveys.stage_update.assert_not_awaited()
    # Nothing staged before the failure is committed: the request's session
    # discards it on close.
    uow.commit.assert_not_awaited()


async def test_a_normal_completion_seeds_modules_lessons_tracks_then_marks_complete() -> None:
    """A one-shot completion (nothing partial) writes modules, then lessons,
    then tracks, and marks the survey complete — the same call path a retry
    takes (see the two tests above for the actual self-healing guarantees:
    write order, and "a failed seed leaves `in_progress`").

    This is deliberately NOT a test of resuming a genuinely partial DB state:
    `_seed_assignments`'s only "already ran" signal is
    `track_ids_for_user(user_id)`, which is empty both for a brand-new user
    and for a user whose first attempt crashed after the module/lesson writes
    but before the (now-last) track write — the two cases are indistinguishable
    to this method, by design (that's what makes the retry "just call
    `complete()` again"). A mock can't add a distinguishing prior state here:
    `stage_user_modules`/`stage_user_lessons` are unconditionally re-issued on
    every call regardless of what already exists; their idempotency
    (ON CONFLICT DO NOTHING) is real-database behaviour a repository mock
    can't represent. See the task report for why the brief's literal
    "survey already complete" precondition for a retry test is unreachable:
    `complete()` raises `SurveyNotInProgressError` for any row whose `status`
    isn't `in_progress`, before it ever looks at the seed.
    """
    tracks, modules, lessons = _fixture_graph()
    service, surveys, assignments, uow = _service(
        _row(), tracks=tracks, modules=modules, lessons=lessons
    )

    await service.complete(uuid.uuid4())

    assignments.stage_user_modules.assert_awaited_once()
    assignments.stage_user_lessons.assert_awaited_once()
    assignments.stage_user_tracks.assert_awaited_once()
    surveys.stage_update.assert_awaited_once()
    assert surveys.stage_update.await_args.args[1]["status"] == "complete"
    uow.commit.assert_awaited_once()


async def test_completion_commits_once_after_every_write_is_staged() -> None:
    """The whole completion is one transaction: every write is a flush-only
    `stage_*` call, and the unit of work commits exactly once, last. The
    committing twins (`set_user_*`, `update`) must not be used — each of them
    would end the transaction early."""
    tracks, modules, lessons = _fixture_graph()
    service, surveys, assignments, uow = _service(
        _row(), tracks=tracks, modules=modules, lessons=lessons
    )
    order: list[str] = []
    assignments.stage_user_modules.side_effect = lambda *a, **k: order.append("modules")
    assignments.stage_user_lessons.side_effect = lambda *a, **k: order.append("lessons")
    assignments.stage_user_tracks.side_effect = lambda *a, **k: order.append("tracks")

    def _stage_update(target_row: Any, values: dict[str, Any]) -> Any:
        order.append("survey")
        return SimpleNamespace(**{**vars(target_row), **values})

    surveys.stage_update.side_effect = _stage_update
    uow.commit.side_effect = lambda: order.append("commit")

    await service.complete(uuid.uuid4())

    assert order == ["modules", "lessons", "tracks", "survey", "commit"]
    assignments.set_user_modules.assert_not_awaited()
    assignments.set_user_lessons.assert_not_awaited()
    assignments.set_user_tracks.assert_not_awaited()
    surveys.update.assert_not_awaited()


async def test_save_draft_delegates_to_the_repository_upsert() -> None:
    """save_draft is a single upsert call, not get-then-create: whatever row
    `create_or_update` returns is what the caller gets back."""
    service, surveys, _assignments, _uow = _service(_row(), tracks=[], modules=[], lessons=[])
    upserted = SimpleNamespace(status="in_progress", job_title="New")
    surveys.create_or_update.return_value = upserted

    result = await service.save_draft(uuid.uuid4(), {"job_title": "New"})

    assert result is upserted
    surveys.create_or_update.assert_awaited_once()


async def test_save_draft_raises_when_a_concurrent_complete_wins_the_race() -> None:
    """The pre-check (`get_by_user_id`) sees an in-progress row, but a
    concurrent POST /complete finishes first: the upsert's WHERE guard then
    leaves the now-complete row untouched and returns no row. save_draft must
    surface the same SurveyAlreadyCompleteError as the normal pre-check path,
    not silently drop the write."""
    service, surveys, _assignments, _uow = _service(_row(), tracks=[], modules=[], lessons=[])
    surveys.create_or_update.return_value = None

    with pytest.raises(SurveyAlreadyCompleteError):
        await service.save_draft(uuid.uuid4(), {"job_title": "New"})
