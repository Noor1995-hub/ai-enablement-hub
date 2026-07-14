from __future__ import annotations

import uuid

from src.db.models import Feedback
from src.repositories.base import AbstractFeedbackRepository

__all__ = ["FeedbackRepository"]


class FeedbackRepository(AbstractFeedbackRepository):
    async def create(self, user_id: uuid.UUID, lesson_id: uuid.UUID, message: str) -> Feedback:
        feedback = Feedback(user_id=user_id, lesson_id=lesson_id, message=message)
        self._session.add(feedback)
        await self._session.commit()
        await self._session.refresh(feedback)
        return feedback
