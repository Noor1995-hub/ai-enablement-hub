from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import select

from src.db.models import User
from src.repositories.assignment_repository import AssignmentRepository
from tests.fixtures.auth import auth_headers
from tests.fixtures.factories import (
    assign_lesson,
    create_company,
    create_lesson,
    create_module,
    create_project,
    create_track,
    create_user,
)

if TYPE_CHECKING:
    from httpx import AsyncClient
    from sqlalchemy.ext.asyncio import AsyncSession

    from src.core.configs.settings import Settings


async def test_move_keeps_assignments_and_updates_company(
    client: AsyncClient, db_session: AsyncSession, test_settings: Settings
) -> None:
    power = await create_user(db_session, email="b6-move-power@example.com", role="admin")
    old_co = await create_company(db_session, "B6 Old Co")
    new_co = await create_company(db_session, "B6 New Co")
    old = await create_project(db_session, old_co, "B6 Old")
    new = await create_project(db_session, new_co, "B6 New")
    learner = await create_user(
        db_session, email="b6-mover@example.com", company_id=old_co.id, project_id=old.id
    )
    lesson = await create_lesson(
        db_session, await create_module(db_session, await create_track(db_session))
    )
    await assign_lesson(db_session, learner, lesson)

    response = await client.put(
        f"/api/admin/users/{learner.id}/project",
        json={"project_id": str(new.id)},
        headers=auth_headers(power, test_settings),
    )

    assert response.status_code == 204
    moved = (await db_session.execute(select(User).where(User.id == learner.id))).scalar_one()
    await db_session.refresh(moved)
    assert (moved.project_id, moved.company_id) == (new.id, new_co.id)
    assert lesson.id in await AssignmentRepository(db_session).lesson_ids_for_user(learner.id)
