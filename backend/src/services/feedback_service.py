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

    async def submit(self, user_id: uuid.UUID, lesson_id: uuid.UUID, message: str) -> Feedback:
        if await self._content.get_lesson(lesson_id) is None:
            raise NotFoundError("Lesson")
        return await self._feedback.create(user_id, lesson_id, message)
