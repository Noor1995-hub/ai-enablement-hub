from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from src.db.models import Feedback
from src.repositories.feedback_repository import FeedbackRepository
from tests.fixtures.factories import (
    create_company,
    create_lesson,
    create_module,
    create_project,
    create_track,
    create_user,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


async def _seed(db_session: AsyncSession, prefix: str) -> tuple:
    company = await create_company(db_session, f"{prefix} Co")
    project = await create_project(db_session, company, f"{prefix} Project")
    user = await create_user(
        db_session,
        email=f"{prefix}@x.test",
        company_id=company.id,
        project_id=project.id,
    )
    track = await create_track(db_session, f"{prefix} Track")
    module = await create_module(db_session, track, f"{prefix} Module")
    lesson = await create_lesson(db_session, module, f"{prefix} Lesson")
    return project, user, lesson


async def test_lists_only_new_rows_without_a_suggestion(db_session: AsyncSession) -> None:
    _project, user, lesson = await _seed(db_session, "awaiting")
    wanted = Feedback(user_id=user.id, lesson_id=lesson.id, message="unclear")
    already = Feedback(
        user_id=user.id,
        lesson_id=lesson.id,
        message="already suggested",
        ai_suggested_status="accepted",
        ai_rationale="r",
        ai_suggested_at=datetime.now(UTC),
    )
    accepted = Feedback(
        user_id=user.id, lesson_id=lesson.id, message="already triaged", status="accepted"
    )
    db_session.add_all([wanted, already, accepted])
    await db_session.commit()

    repo = FeedbackRepository(db_session)
    rows = await repo.list_awaiting_suggestion(limit=10)

    assert [fb.id for fb, _lesson in rows] == [wanted.id]
    assert rows[0][1].id == lesson.id
    assert await repo.count_awaiting_suggestion() == 1


async def test_limit_and_project_filter(db_session: AsyncSession) -> None:
    project_a, user_a, lesson_a = await _seed(db_session, "scope-a")
    _project_b, user_b, lesson_b = await _seed(db_session, "scope-b")
    db_session.add_all(
        [
            Feedback(user_id=user_a.id, lesson_id=lesson_a.id, message="a1"),
            Feedback(user_id=user_a.id, lesson_id=lesson_a.id, message="a2"),
            Feedback(user_id=user_b.id, lesson_id=lesson_b.id, message="b1"),
        ]
    )
    await db_session.commit()

    repo = FeedbackRepository(db_session)

    assert len(await repo.list_awaiting_suggestion(limit=1)) == 1
    assert await repo.count_awaiting_suggestion(project_id=project_a.id) == 2
    scoped = await repo.list_awaiting_suggestion(project_id=project_a.id, limit=10)
    assert {fb.message for fb, _lesson in scoped} == {"a1", "a2"}


async def test_set_ai_suggestion_never_touches_status(db_session: AsyncSession) -> None:
    _project, user, lesson = await _seed(db_session, "write")
    row = Feedback(user_id=user.id, lesson_id=lesson.id, message="add an example")
    db_session.add(row)
    await db_session.commit()

    repo = FeedbackRepository(db_session)
    await repo.set_ai_suggestion(row, suggested_status="accepted", rationale="Actionable ask.")
    await db_session.refresh(row)

    assert row.ai_suggested_status == "accepted"
    assert row.ai_rationale == "Actionable ask."
    assert row.ai_suggested_at is not None
    assert row.status == "new"
    assert row.reviewed_by is None
    # ...and it drops out of the awaiting queue.
    assert await repo.count_awaiting_suggestion() == 0
