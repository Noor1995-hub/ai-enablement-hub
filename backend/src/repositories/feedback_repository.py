from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import Select, func, select

from src.db.models import Company, Feedback, Lesson, Module, Project, Track, User
from src.repositories.base import AbstractFeedbackRepository

__all__ = ["FeedbackRepository"]


class FeedbackRepository(AbstractFeedbackRepository):
    async def create(self, user_id: uuid.UUID, lesson_id: uuid.UUID, message: str) -> Feedback:
        feedback = Feedback(user_id=user_id, lesson_id=lesson_id, message=message)
        self._session.add(feedback)
        await self._session.commit()
        await self._session.refresh(feedback)
        return feedback

    def _admin_query(
        self,
        status: str | None,
        track_id: uuid.UUID | None,
        project_id: uuid.UUID | None,
    ) -> Select[Any]:
        query = (
            select(
                Feedback,
                User.first_name,
                User.last_name,
                Company.name.label("company_name"),
                Project.name.label("project_name"),
                Lesson.title.label("lesson_title"),
                Module.id.label("module_id"),
                Module.title.label("module_title"),
                Track.id.label("track_id"),
                Track.name.label("track_name"),
                Track.required_level.label("track_level"),
            )
            .join(User, User.id == Feedback.user_id)
            .outerjoin(Company, Company.id == User.company_id)
            .outerjoin(Project, Project.id == User.project_id)
            .join(Lesson, Lesson.id == Feedback.lesson_id)
            .join(Module, Module.id == Lesson.module_id)
            .join(Track, Track.id == Module.track_id)
        )
        if status is not None:
            query = query.where(Feedback.status == status)
        if track_id is not None:
            query = query.where(Track.id == track_id)
        if project_id is not None:
            query = query.where(User.project_id == project_id)
        return query

    async def list_admin(
        self,
        *,
        status: str | None = None,
        track_id: uuid.UUID | None = None,
        project_id: uuid.UUID | None = None,
        limit: int,
        offset: int,
    ) -> list[Any]:
        query = (
            self._admin_query(status, track_id, project_id)
            .order_by(Feedback.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list((await self._session.execute(query)).all())

    async def count_admin(
        self,
        *,
        status: str | None = None,
        track_id: uuid.UUID | None = None,
        project_id: uuid.UUID | None = None,
    ) -> int:
        query = select(func.count()).select_from(
            self._admin_query(status, track_id, project_id).subquery()
        )
        return int((await self._session.execute(query)).scalar_one())

    async def count_new(self, project_id: uuid.UUID | None = None) -> int:
        return await self.count_admin(status="new", project_id=project_id)

    async def get_by_id(self, feedback_id: uuid.UUID) -> Feedback | None:
        result = await self._session.execute(select(Feedback).where(Feedback.id == feedback_id))
        return result.scalar_one_or_none()

    async def set_status(
        self, feedback: Feedback, status: str, reviewed_by: uuid.UUID | None
    ) -> None:
        feedback.status = status
        feedback.reviewed_by = reviewed_by
        feedback.reviewed_at = None if reviewed_by is None else datetime.now(UTC)
        await self._session.commit()

    def _awaiting_suggestion_query(self, project_id: uuid.UUID | None) -> Select[Any]:
        query = (
            select(Feedback, Lesson)
            .join(Lesson, Lesson.id == Feedback.lesson_id)
            .where(Feedback.status == "new", Feedback.ai_suggested_at.is_(None))
        )
        if project_id is not None:
            query = query.join(User, User.id == Feedback.user_id).where(
                User.project_id == project_id
            )
        return query

    async def list_awaiting_suggestion(
        self, *, project_id: uuid.UUID | None = None, limit: int
    ) -> list[tuple[Feedback, Lesson]]:
        query = (
            self._awaiting_suggestion_query(project_id).order_by(Feedback.created_at).limit(limit)
        )
        rows = (await self._session.execute(query)).all()
        return [(row[0], row[1]) for row in rows]

    async def count_awaiting_suggestion(self, *, project_id: uuid.UUID | None = None) -> int:
        query = select(func.count()).select_from(
            self._awaiting_suggestion_query(project_id).subquery()
        )
        return int((await self._session.execute(query)).scalar_one())

    async def set_ai_suggestion(
        self, feedback: Feedback, *, suggested_status: str, rationale: str
    ) -> None:
        feedback.ai_suggested_status = suggested_status
        feedback.ai_rationale = rationale
        feedback.ai_suggested_at = datetime.now(UTC)
        await self._session.commit()
