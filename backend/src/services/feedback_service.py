from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

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
                "ai_suggested_status": fb.ai_suggested_status,
                "ai_rationale": fb.ai_rationale,
                "ai_suggested_at": fb.ai_suggested_at,
            }
            for (
                fb,
                first_name,
                last_name,
                company_name,
                project_name,
                lesson_title,
                module_id,
                module_title,
                track_id_,
                track_name,
                track_level,
            ) in rows
        ]
        return items, total

    async def set_status(self, feedback_id: uuid.UUID, status: str, reviewed_by: uuid.UUID) -> None:
        feedback = await self._feedback.get_by_id(feedback_id)
        if feedback is None:
            raise NotFoundError("Feedback")
        reviewer = None if status == "new" else reviewed_by
        await self._feedback.set_status(feedback, status, reviewer)
