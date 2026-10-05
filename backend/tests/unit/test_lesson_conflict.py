from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from src.repositories.base import (
    AbstractAssignmentRepository,
    AbstractContentRepository,
    AbstractProjectAdminRepository,
    AbstractUserRepository,
)
from src.services.content_service import ContentService
from src.services.exceptions import LessonChangedError

T0 = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)  # safely in the past: the stamp must be later


def _service(lesson: SimpleNamespace) -> tuple[ContentService, AsyncMock, AsyncMock]:
    content = AsyncMock(spec=AbstractContentRepository)
    content.get_lesson.return_value = lesson
    content.get_lesson_for_update.return_value = lesson
    content.update_lesson.side_effect = lambda le, values: le
    users = AsyncMock(spec=AbstractUserRepository)
    users.get_by_id.return_value = SimpleNamespace(first_name="Aaron", last_name="Neuville")
    service = ContentService(
        content,
        assignments=AsyncMock(spec=AbstractAssignmentRepository),
        users=users,
        project_admins=AsyncMock(spec=AbstractProjectAdminRepository),
    )
    return service, content, users


def _lesson(**kw: object) -> SimpleNamespace:
    return SimpleNamespace(
        **(
            {
                "id": uuid.uuid4(),
                "module_id": uuid.uuid4(),
                "updated_at": T0,
                "updated_by": uuid.uuid4(),
            }
            | kw
        )
    )


async def test_a_stale_expected_updated_at_is_refused_with_who_and_when() -> None:
    lesson = _lesson()
    service, content, _ = _service(lesson)

    with pytest.raises(LessonChangedError) as caught:
        await service.update_lesson(
            lesson.id,
            {"title": "x", "expected_updated_at": T0 - timedelta(seconds=1)},
            actor_id=uuid.uuid4(),
        )

    assert caught.value.updated_at == T0
    assert caught.value.updated_by_name == "Aaron Neuville"
    content.update_lesson.assert_not_awaited()


async def test_a_fresh_save_stamps_time_and_editor() -> None:
    lesson = _lesson()
    service, content, _ = _service(lesson)
    actor = uuid.uuid4()

    await service.update_lesson(
        lesson.id, {"title": "x", "expected_updated_at": T0}, actor_id=actor
    )

    _, values = content.update_lesson.await_args.args
    assert values["title"] == "x"
    assert values["updated_by"] == actor
    assert values["updated_at"] > T0
    assert "expected_updated_at" not in values


async def test_an_omitted_expected_updated_at_still_saves() -> None:
    lesson = _lesson()
    service, content, _ = _service(lesson)
    await service.update_lesson(lesson.id, {"title": "x"}, actor_id=None)
    content.update_lesson.assert_awaited_once()


async def test_conflict_names_nobody_when_the_editor_was_deleted() -> None:
    lesson = _lesson(updated_by=None)
    service, _, _ = _service(lesson)
    with pytest.raises(LessonChangedError) as caught:
        await service.update_lesson(
            lesson.id, {"expected_updated_at": T0 - timedelta(seconds=1)}, actor_id=None
        )
    assert caught.value.updated_by_name is None


async def test_a_checked_save_reads_the_lesson_with_a_row_lock() -> None:
    """Two saves carrying the same expected_updated_at must not both pass: the
    check reads under SELECT ... FOR UPDATE, so the second waits for the first
    commit and then sees the new updated_at (PR #167 review)."""
    lesson = _lesson()
    service, content, _ = _service(lesson)
    content.get_lesson_for_update.return_value = lesson

    await service.update_lesson(lesson.id, {"title": "x", "expected_updated_at": T0}, actor_id=None)

    content.get_lesson_for_update.assert_awaited_once_with(lesson.id)
    content.get_lesson.assert_not_awaited()
