"""Scoped admin routes beyond the matrix's status checks: what a project admin
sees, and that bulk and invite requests can't reach outside their projects
(spec 2026-10-01-project-scoped-admin-design.md)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import pytest_asyncio
from sqlalchemy import select

from src.db.models import User, UserTrack
from tests.fixtures.auth import auth_headers
from tests.fixtures.factories import (
    create_company,
    create_project,
    create_track,
    create_user,
    make_project_admin,
)

if TYPE_CHECKING:
    from httpx import AsyncClient
    from sqlalchemy.ext.asyncio import AsyncSession

    from src.core.configs.settings import Settings
    from src.db.models import Project, Track


@dataclass
class World:
    a: Project
    b: Project
    coach: User
    la: User
    lb: User
    track: Track


@pytest_asyncio.fixture
async def world(db_session: AsyncSession) -> World:
    company = await create_company(db_session, "Scope Co")
    a = await create_project(db_session, company, "Scope A")
    b = await create_project(db_session, company, "Scope B")
    coach = await create_user(db_session, email="scope-coach@example.com", password="x" * 12)
    await make_project_admin(db_session, coach, a)
    la = await create_user(
        db_session, email="scope-la@example.com", company_id=company.id, project_id=a.id
    )
    lb = await create_user(
        db_session, email="scope-lb@example.com", company_id=company.id, project_id=b.id
    )
    track = await create_track(db_session, "Scope Track")
    return World(a, b, coach, la, lb, track)


async def test_user_list_defaults_to_the_only_project(
    client: AsyncClient, world: World, test_settings: Settings
) -> None:
    response = await client.get(
        "/api/admin/users", headers=auth_headers(world.coach, test_settings)
    )
    assert response.status_code == 200
    ids = {u["id"] for u in response.json()["users"]}
    assert str(world.la.id) in ids
    assert str(world.lb.id) not in ids


async def test_user_list_for_a_foreign_project_is_404(
    client: AsyncClient, world: World, test_settings: Settings
) -> None:
    response = await client.get(
        f"/api/admin/users?project_id={world.b.id}",
        headers=auth_headers(world.coach, test_settings),
    )
    assert response.status_code == 404


async def test_multi_project_admin_must_name_a_project(
    client: AsyncClient, db_session: AsyncSession, world: World, test_settings: Settings
) -> None:
    await make_project_admin(db_session, world.coach, world.b)
    headers = auth_headers(world.coach, test_settings)
    assert (await client.get("/api/admin/users", headers=headers)).status_code == 400
    named = await client.get(f"/api/admin/users?project_id={world.b.id}", headers=headers)
    assert named.status_code == 200
    assert {u["id"] for u in named.json()["users"]} >= {str(world.lb.id)}


async def test_bulk_assign_with_one_foreign_user_writes_nothing(
    client: AsyncClient, db_session: AsyncSession, world: World, test_settings: Settings
) -> None:
    response = await client.post(
        "/api/admin/assignments/bulk",
        json={
            "user_ids": [str(world.la.id), str(world.lb.id)],
            "track_ids": [str(world.track.id)],
            "assigned": True,
        },
        headers=auth_headers(world.coach, test_settings),
    )
    assert response.status_code == 404
    rows = (
        (
            await db_session.execute(
                select(UserTrack).where(UserTrack.user_id.in_([world.la.id, world.lb.id]))
            )
        )
        .scalars()
        .all()
    )
    assert rows == []


async def test_survey_levels_reject_a_foreign_user(
    client: AsyncClient, world: World, test_settings: Settings
) -> None:
    response = await client.get(
        f"/api/admin/surveys?user_ids={world.la.id},{world.lb.id}",
        headers=auth_headers(world.coach, test_settings),
    )
    assert response.status_code == 404


async def test_invite_into_a_foreign_project_is_404_and_own_project_creates_a_user(
    client: AsyncClient, db_session: AsyncSession, world: World, test_settings: Settings
) -> None:
    headers = auth_headers(world.coach, test_settings)
    body = {"first_name": "New", "last_name": "Learner", "send_email": False}
    foreign = await client.post(
        "/api/admin/invites",
        json={**body, "email": "scope-new-b@example.com", "project_id": str(world.b.id)},
        headers=headers,
    )
    assert foreign.status_code == 404
    own = await client.post(
        "/api/admin/invites",
        json={**body, "email": "scope-new-a@example.com", "project_id": str(world.a.id)},
        headers=headers,
    )
    assert own.status_code == 201
    created = (
        await db_session.execute(select(User).where(User.email == "scope-new-a@example.com"))
    ).scalar_one()
    assert created.role == "user"
    assert created.project_id == world.a.id


async def test_role_change_is_power_admin_only(
    client: AsyncClient, world: World, test_settings: Settings
) -> None:
    response = await client.patch(
        f"/api/admin/users/{world.la.id}",
        json={"role": "admin"},
        headers=auth_headers(world.coach, test_settings),
    )
    assert response.status_code == 403


async def test_companies_list_only_shows_scoped_projects(
    client: AsyncClient, world: World, test_settings: Settings
) -> None:
    response = await client.get(
        "/api/admin/companies", headers=auth_headers(world.coach, test_settings)
    )
    assert response.status_code == 200
    project_ids = {p["id"] for c in response.json()["companies"] for p in c["projects"]}
    assert project_ids == {str(world.a.id)}


async def test_project_admin_cannot_touch_another_project_admin(
    client: AsyncClient, db_session: AsyncSession, world: World, test_settings: Settings
) -> None:
    other_coach = await create_user(
        db_session, email="scope-coach2@example.com", project_id=world.a.id
    )
    await make_project_admin(db_session, other_coach, world.b)
    response = await client.delete(
        f"/api/admin/users/{other_coach.id}", headers=auth_headers(world.coach, test_settings)
    )
    assert response.status_code == 403


async def test_admin_interview_view_is_scoped(
    client: AsyncClient, world: World, test_settings: Settings
) -> None:
    """The matrix can't tell these apart (LLM is unconfigured in tests, so an
    in-scope call also 404s), so compare the bodies: out of scope is "User not
    found", in scope gets past the guard to the not-configured 404."""
    headers = auth_headers(world.coach, test_settings)
    foreign = await client.get(f"/api/admin/interviews/{world.lb.id}", headers=headers)
    own = await client.get(f"/api/admin/interviews/{world.la.id}", headers=headers)
    assert foreign.status_code == 404
    assert foreign.json()["error"]["message"] == "User not found"
    assert own.status_code == 404
    assert own.json()["error"]["message"] != "User not found"
    foreign_reset = await client.delete(f"/api/admin/interviews/{world.lb.id}", headers=headers)
    own_reset = await client.delete(f"/api/admin/interviews/{world.la.id}", headers=headers)
    assert foreign_reset.json()["error"]["message"] == "User not found"
    assert own_reset.json()["error"]["message"] != "User not found"


async def test_dashboard_for_a_foreign_project_is_404(
    client: AsyncClient, world: World, test_settings: Settings
) -> None:
    headers = auth_headers(world.coach, test_settings)
    assert (
        await client.get(f"/api/admin/dashboard?project_id={world.b.id}", headers=headers)
    ).status_code == 404
    assert (await client.get("/api/admin/dashboard", headers=headers)).status_code == 200


async def test_project_admins_get_invite_and_reset_links_in_their_project(
    client: AsyncClient, world: World, test_settings: Settings
) -> None:
    """Decision 2026-10-01: project admins get the manual fallback link for
    their own learners, like power admins (accepted risk, see SECURITY.md);
    out of scope stays a 404."""
    coach = auth_headers(world.coach, test_settings)
    reset = await client.post(
        f"/api/admin/users/{world.la.id}/reset-link", json={"send_email": False}, headers=coach
    )
    assert reset.status_code == 200
    assert reset.json()["link"].startswith("http")
    foreign = await client.post(
        f"/api/admin/users/{world.lb.id}/reset-link", json={"send_email": False}, headers=coach
    )
    assert foreign.status_code == 404

    invite = await client.post(
        "/api/admin/invites",
        json={
            "email": "scope-withlink@example.com",
            "first_name": "With",
            "last_name": "Link",
            "project_id": str(world.a.id),
            "send_email": False,
        },
        headers=coach,
    )
    assert invite.status_code == 201
    assert invite.json()["link"].startswith("http")
