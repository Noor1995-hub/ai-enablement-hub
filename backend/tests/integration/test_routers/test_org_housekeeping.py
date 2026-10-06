from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import select

from src.db.models import Company, Project, User
from tests.fixtures.auth import auth_headers
from tests.fixtures.factories import (
    complete_lesson,
    create_company,
    create_lesson,
    create_module,
    create_project,
    create_track,
    create_user,
    make_project_admin,
)

if TYPE_CHECKING:
    from httpx import AsyncClient
    from sqlalchemy.ext.asyncio import AsyncSession

    from src.core.configs.settings import Settings


async def _exists(db_session: AsyncSession, model, id_) -> bool:  # noqa: ANN001
    return (
        await db_session.execute(select(model).where(model.id == id_))
    ).scalar_one_or_none() is not None


async def test_delete_project_impact_then_delete(
    client: AsyncClient, db_session: AsyncSession, test_settings: Settings
) -> None:
    caller = await create_user(db_session, email="b6-del-caller@example.com", role="admin")
    company = await create_company(db_session, "B6 Del Co")
    project = await create_project(db_session, company, "B6 Del P")
    elsewhere = await create_project(db_session, company, "B6 Elsewhere")
    learner = await create_user(
        db_session, email="b6-del-l@example.com", company_id=company.id, project_id=project.id
    )
    power = await create_user(
        db_session,
        email="b6-del-power@example.com",
        role="admin",
        company_id=company.id,
        project_id=project.id,
    )
    coach = await create_user(
        db_session, email="b6-del-coach@example.com", company_id=company.id, project_id=elsewhere.id
    )
    await make_project_admin(db_session, coach, project)
    lesson = await create_lesson(
        db_session, await create_module(db_session, await create_track(db_session))
    )
    await complete_lesson(db_session, learner, lesson)
    headers = auth_headers(caller, test_settings)

    impact = await client.get(f"/api/admin/projects/{project.id}/impact", headers=headers)
    assert impact.json() == {
        "projects": 0,
        "users_deleted": 1,
        "power_admins_kept": 1,
        "project_admin_grants": 1,
        "users_with_progress": 1,
        "other_project_admins_deleted": 0,
    }

    assert (
        await client.delete(f"/api/admin/projects/{project.id}", headers=headers)
    ).status_code == 204
    assert not await _exists(db_session, Project, project.id)
    assert not await _exists(db_session, User, learner.id)
    assert await _exists(
        db_session, User, coach.id
    )  # member of another project, only lost the grant
    kept = (await db_session.execute(select(User).where(User.id == power.id))).scalar_one()
    await db_session.refresh(kept)
    assert kept.project_id is None


async def test_delete_company_takes_projects_and_company_only_users(
    client: AsyncClient, db_session: AsyncSession, test_settings: Settings
) -> None:
    caller = await create_user(db_session, email="b6-delco-caller@example.com", role="admin")
    company = await create_company(db_session, "B6 DelCo")
    project = await create_project(db_session, company, "B6 DelCo P")
    member = await create_user(
        db_session, email="b6-delco-m@example.com", company_id=company.id, project_id=project.id
    )
    loose = await create_user(db_session, email="b6-delco-loose@example.com", company_id=company.id)

    response = await client.delete(
        f"/api/admin/companies/{company.id}", headers=auth_headers(caller, test_settings)
    )

    assert response.status_code == 204
    for model, id_ in (
        (Company, company.id),
        (Project, project.id),
        (User, member.id),
        (User, loose.id),
    ):
        assert not await _exists(db_session, model, id_)


async def test_rename_project_and_duplicate_company_name(
    client: AsyncClient, db_session: AsyncSession, test_settings: Settings
) -> None:
    caller = await create_user(db_session, email="b6-ren@example.com", role="admin")
    a = await create_company(db_session, "B6 Alpha")
    await create_company(db_session, "B6 Beta")
    project = await create_project(db_session, a, "B6 Old")
    headers = auth_headers(caller, test_settings)

    renamed = await client.patch(
        f"/api/admin/projects/{project.id}", json={"name": " B6 New "}, headers=headers
    )
    assert renamed.json()["name"] == "B6 New"
    clash = await client.patch(
        f"/api/admin/companies/{a.id}", json={"name": "b6 beta"}, headers=headers
    )
    assert clash.status_code == 409
    blank = await client.patch(f"/api/admin/companies/{a.id}", json={"name": "  "}, headers=headers)
    assert blank.status_code == 422
