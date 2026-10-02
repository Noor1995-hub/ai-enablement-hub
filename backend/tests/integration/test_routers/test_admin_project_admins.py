"""Granting/revoking project admins and the self / last-power-admin guards
(spec 2026-10-01-project-scoped-admin-design.md)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from tests.fixtures.auth import auth_headers
from tests.fixtures.factories import create_company, create_project, create_user

if TYPE_CHECKING:
    from httpx import AsyncClient
    from sqlalchemy.ext.asyncio import AsyncSession

    from src.core.configs.settings import Settings


async def test_grant_list_revoke(
    client: AsyncClient, db_session: AsyncSession, test_settings: Settings
) -> None:
    company = await create_company(db_session, "Grant Co")
    project = await create_project(db_session, company, "Grant P")
    power = await create_user(db_session, email="grant-power@example.com", role="admin")
    coach = await create_user(db_session, email="grant-coach@example.com")
    power_headers = auth_headers(power, test_settings)
    coach_headers = auth_headers(coach, test_settings)
    base = f"/api/admin/projects/{project.id}/admins"

    assert (await client.get(base, headers=coach_headers)).status_code == 403
    assert (await client.put(f"{base}/{coach.id}", headers=power_headers)).status_code == 204
    assert (await client.put(f"{base}/{coach.id}", headers=power_headers)).status_code == 204
    listed = (await client.get(base, headers=power_headers)).json()["admins"]
    assert [a["user_id"] for a in listed] == [str(coach.id)]
    assert listed[0]["email"] == "grant-coach@example.com"

    # The coach can now read their own project's admin list, but not grant.
    assert (await client.get(base, headers=coach_headers)).status_code == 200
    assert (await client.put(f"{base}/{power.id}", headers=coach_headers)).status_code == 403
    assert (await client.delete(f"{base}/{coach.id}", headers=coach_headers)).status_code == 403

    assert (await client.delete(f"{base}/{coach.id}", headers=power_headers)).status_code == 204
    assert (await client.delete(f"{base}/{coach.id}", headers=power_headers)).status_code == 404
    # Revoked: no admin access at all on the next request.
    assert (await client.get(base, headers=coach_headers)).status_code == 403


async def test_grant_to_a_power_admin_is_a_no_op(
    client: AsyncClient, db_session: AsyncSession, test_settings: Settings
) -> None:
    company = await create_company(db_session, "Grant Co 2")
    project = await create_project(db_session, company, "Grant P2")
    power = await create_user(db_session, email="grant-power2@example.com", role="admin")
    other_power = await create_user(db_session, email="grant-power3@example.com", role="admin")
    headers = auth_headers(power, test_settings)
    base = f"/api/admin/projects/{project.id}/admins"
    assert (await client.put(f"{base}/{other_power.id}", headers=headers)).status_code == 204
    assert (await client.get(base, headers=headers)).json()["admins"] == []


async def test_grant_unknown_project_or_user_is_404(
    client: AsyncClient, db_session: AsyncSession, test_settings: Settings
) -> None:
    import uuid

    company = await create_company(db_session, "Grant Co 3")
    project = await create_project(db_session, company, "Grant P3")
    power = await create_user(db_session, email="grant-power4@example.com", role="admin")
    coach = await create_user(db_session, email="grant-coach4@example.com")
    headers = auth_headers(power, test_settings)
    missing = uuid.uuid4()
    assert (
        await client.put(f"/api/admin/projects/{missing}/admins/{coach.id}", headers=headers)
    ).status_code == 404
    assert (
        await client.put(f"/api/admin/projects/{project.id}/admins/{missing}", headers=headers)
    ).status_code == 404


async def test_admin_cannot_demote_or_delete_themselves(
    client: AsyncClient, db_session: AsyncSession, test_settings: Settings
) -> None:
    power = await create_user(db_session, email="self-power@example.com", role="admin")
    await create_user(db_session, email="self-power-2@example.com", role="admin")
    headers = auth_headers(power, test_settings)
    demote = await client.patch(
        f"/api/admin/users/{power.id}", json={"role": "user"}, headers=headers
    )
    assert demote.status_code == 409
    assert (await client.delete(f"/api/admin/users/{power.id}", headers=headers)).status_code == 409
    await db_session.refresh(power)
    assert power.role == "admin"


async def test_deleting_a_project_admin_removes_their_grants(
    client: AsyncClient, db_session: AsyncSession, test_settings: Settings
) -> None:
    company = await create_company(db_session, "Grant Co 5")
    project = await create_project(db_session, company, "Grant P5")
    power = await create_user(db_session, email="grant-power5@example.com", role="admin")
    coach = await create_user(db_session, email="grant-coach5@example.com")
    headers = auth_headers(power, test_settings)
    base = f"/api/admin/projects/{project.id}/admins"
    assert (await client.put(f"{base}/{coach.id}", headers=headers)).status_code == 204
    assert (await client.delete(f"/api/admin/users/{coach.id}", headers=headers)).status_code == 204
    assert (await client.get(base, headers=headers)).json()["admins"] == []
