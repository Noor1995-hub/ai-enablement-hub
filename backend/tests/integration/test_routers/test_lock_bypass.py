"""Spec 2026-10-01 decision 5: power admins, and project admins on their OWN
project, bypass locked components, the lesson gate and the assessment gate.
hidden stays hidden; AI surface toggles stay a hard gate."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import pytest_asyncio

from src.db.models import ProjectComponentSetting
from tests.fixtures.auth import auth_headers
from tests.fixtures.factories import (
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
    from src.db.models import Lesson, Project, User


@dataclass
class World:
    a: Project
    own: User
    foreign: User
    lesson: Lesson


@pytest_asyncio.fixture
async def world(db_session: AsyncSession) -> World:
    company = await create_company(db_session, "Bypass Co")
    a = await create_project(db_session, company, "Bypass A")  # learning locked by default
    b = await create_project(db_session, company, "Bypass B")
    own = await create_user(db_session, email="bypass-own@example.com", project_id=a.id)
    await make_project_admin(db_session, own, a)
    foreign = await create_user(db_session, email="bypass-foreign@example.com", project_id=a.id)
    await make_project_admin(db_session, foreign, b)
    track = await create_track(db_session, "Bypass Track")
    module = await create_module(db_session, track, "Bypass Module")
    lesson = await create_lesson(db_session, module, "Bypass Lesson")  # assigned to nobody
    return World(a, own, foreign, lesson)


async def test_own_project_admin_bypasses_locked_component_and_lesson_gate(
    client: AsyncClient, world: World, test_settings: Settings
) -> None:
    headers = auth_headers(world.own, test_settings)
    assert (await client.get("/api/learning/graph", headers=headers)).status_code == 200
    lesson = await client.get(f"/api/lessons/{world.lesson.id}", headers=headers)
    assert lesson.status_code == 200
    journey = (await client.get("/api/me/journey", headers=headers)).json()
    assert journey["components"]["learning"]["locked"] is False
    me = (await client.get("/api/me", headers=headers)).json()
    assert me["bypasses_locks"] is True
    assert me["is_power_admin"] is False
    assert me["admin_project_ids"] == [str(world.a.id)]


async def test_admin_of_another_project_does_not_bypass(
    client: AsyncClient, world: World, test_settings: Settings
) -> None:
    headers = auth_headers(world.foreign, test_settings)
    assert (await client.get("/api/learning/graph", headers=headers)).status_code == 403
    assert (await client.get(f"/api/lessons/{world.lesson.id}", headers=headers)).status_code == 403
    journey = (await client.get("/api/me/journey", headers=headers)).json()
    assert journey["components"]["learning"]["locked"] is True
    assert (await client.get("/api/me", headers=headers)).json()["bypasses_locks"] is False


async def test_hidden_stays_hidden_for_a_bypassing_admin(
    client: AsyncClient, db_session: AsyncSession, world: World, test_settings: Settings
) -> None:
    db_session.add(
        ProjectComponentSetting(project_id=world.a.id, component="learning", hidden=True)
    )
    await db_session.commit()
    headers = auth_headers(world.own, test_settings)
    assert (await client.get("/api/learning/graph", headers=headers)).status_code == 403
    journey = (await client.get("/api/me/journey", headers=headers)).json()
    assert journey["components"]["learning"]["hidden"] is True


async def test_ai_surface_toggle_still_gates_a_bypassing_admin(
    client: AsyncClient, world: World, test_settings: Settings
) -> None:
    """The interview component is locked by default (bypassed) and its AI
    surface is off by default: still a 403, from the AI gate."""
    headers = auth_headers(world.own, test_settings)
    response = await client.post("/api/interview/opener", headers=headers)
    assert response.status_code == 403
    assert "AI feature not enabled" in response.json()["error"]["message"]


async def test_learner_profile_reports_no_admin_rights(
    client: AsyncClient, db_session: AsyncSession, world: World, test_settings: Settings
) -> None:
    learner = await create_user(db_session, email="bypass-learner@example.com")
    me = (await client.get("/api/me", headers=auth_headers(learner, test_settings))).json()
    assert me == me | {"is_power_admin": False, "admin_project_ids": [], "bypasses_locks": False}
