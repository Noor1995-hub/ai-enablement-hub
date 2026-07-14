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
