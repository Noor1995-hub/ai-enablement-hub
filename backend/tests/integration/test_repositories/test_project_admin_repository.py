from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from src.repositories.project_admin_repository import ProjectAdminRepository
from src.repositories.user_repository import UserRepository
from tests.fixtures.factories import (
    create_company,
    create_project,
    create_user,
    make_project_admin,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


async def test_grant_list_revoke_roundtrip(db_session: AsyncSession) -> None:
    company = await create_company(db_session, "PA Co")
    a = await create_project(db_session, company, "A")
    b = await create_project(db_session, company, "B")
    power = await create_user(db_session, email="pa-power@example.com", role="admin")
    coach = await create_user(db_session, email="pa-coach@example.com", project_id=a.id)
    repo = ProjectAdminRepository(db_session)

    assert await repo.project_ids_for(coach.id) == frozenset()
    assert not await repo.is_project_admin(coach.id)

    await repo.grant(coach.id, a.id, power.id)
    await repo.grant(coach.id, a.id, power.id)  # idempotent
    await repo.grant(coach.id, b.id, power.id)
    assert await repo.project_ids_for(coach.id) == frozenset({a.id, b.id})
    assert await repo.is_project_admin(coach.id)
    assert await repo.admin_ids_for_project(a.id) == {coach.id}
    assert {(coach.id, a.id), (coach.id, b.id)} <= await repo.all_pairs()
    assert await repo.project_ids_by_user([coach.id, power.id]) == {coach.id: sorted([a.id, b.id])}
    assert await repo.project_ids_by_user([]) == {}
    listed = await repo.list_for_project(a.id)
    assert [user.id for user, _ in listed] == [coach.id]

    assert await repo.revoke(coach.id, a.id) is True
    assert await repo.revoke(coach.id, a.id) is False
    assert await repo.project_ids_for(coach.id) == frozenset({b.id})


async def test_user_repo_scope_helpers(db_session: AsyncSession) -> None:
    company = await create_company(db_session, "PA Co 2")
    a = await create_project(db_session, company, "A2")
    repo = UserRepository(db_session)
    before = await repo.count_power_admins()
    await create_user(db_session, email="pa-power2@example.com", role="admin")
    u1 = await create_user(db_session, email="pa-u1@example.com", project_id=a.id)
    u2 = await create_user(db_session, email="pa-u2@example.com")

    assert await repo.count_power_admins() == before + 1
    assert await repo.project_ids_of([u1.id, u2.id, uuid.uuid4()]) == {u1.id: a.id, u2.id: None}
    assert await repo.project_ids_of([]) == {}


async def test_factory_rows_are_visible(db_session: AsyncSession) -> None:
    company = await create_company(db_session, "PA Co 3")
    a = await create_project(db_session, company, "A3")
    coach = await create_user(db_session, email="pa-coach3@example.com")
    await make_project_admin(db_session, coach, a)
    assert await ProjectAdminRepository(db_session).project_ids_for(coach.id) == frozenset({a.id})
