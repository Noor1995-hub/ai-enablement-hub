"""Dashboard aggregates — GET /api/admin/dashboard (spec §4.4, Task 10).

One rich seeded scenario exercises every field of DashboardResponse at once:
tiles, per-project funnels, the attention list (all three kinds), and the
maturity distribution — unscoped, scoped to one project, and the unknown-project
404. The attention rules, active-week window and completed-track definition are
the locked spec values reused from core/attention.py + core/constants.py.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

import pytest_asyncio

from src.db.models import AuthSession, Feedback
from tests.fixtures.auth import auth_headers
from tests.fixtures.factories import (
    assign_lesson,
    assign_track,
    complete_lesson,
    create_company,
    create_lesson,
    create_module,
    create_project,
    create_survey,
    create_track,
    create_user,
)

if TYPE_CHECKING:
    from httpx import AsyncClient
    from sqlalchemy.ext.asyncio import AsyncSession

    from src.core.configs.settings import Settings
    from src.db.models import Project, Track, User


@dataclass
class DashSeed:
    project_a: Project
    project_b: Project
    track_a: Track
    u1: User  # invited-only, 10 days ago -> never_activated
    u2: User  # activated, no survey, 8 days ago -> not_assessed
    u3: User  # assessed, 1/2 lessons done 20 days ago -> stalled
    u4: User  # assessed, whole track done yesterday -> completed_track + active
    u5: User  # project B, healthy + active


async def _add_session(db_session: AsyncSession, user: User, last_used_at: datetime) -> None:
    db_session.add(
        AuthSession(
            user_id=user.id,
            token_hash=uuid.uuid4().hex,
            expires_at=datetime.now(UTC) + timedelta(days=14),
            last_used_at=last_used_at,
        )
    )
    await db_session.commit()


async def _seed(db_session: AsyncSession) -> DashSeed:
    now = datetime.now(UTC)

    company_a = await create_company(db_session, "Alpha Co")
    project_a = await create_project(db_session, company_a, "Alpha Project")
    company_b = await create_company(db_session, "Beta Co")
    project_b = await create_project(db_session, company_b, "Beta Project")

    # track_a: practitioner-level, one module with two lessons (u3's stalled track)
    track_a = await create_track(db_session, "Track A", required_level="practitioner", sort_order=0)
    module_a = await create_module(db_session, track_a, "Module A")
    lesson_a1 = await create_lesson(db_session, module_a, "Lesson A1", sort_order=0)
    lesson_a2 = await create_lesson(db_session, module_a, "Lesson A2", sort_order=1)
    # track_b: explore-level, one module with one lesson (u4's fully-completed track)
    track_b = await create_track(db_session, "Track B", required_level="explore", sort_order=1)
    module_b = await create_module(db_session, track_b, "Module B")
    lesson_b1 = await create_lesson(db_session, module_b, "Lesson B1")

    # u1 — invited only, created 10 days ago, never activated (no password).
    u1 = await create_user(
        db_session, email="dash-u1@example.com", company_id=company_a.id, project_id=project_a.id
    )
    u1.created_at = now - timedelta(days=10)
    await db_session.commit()

    # u2 — activated (password set) 8 days ago, no survey, no activity/assignments.
    u2 = await create_user(
        db_session,
        email="dash-u2@example.com",
        password="hunter2hunter2",
        company_id=company_a.id,
        project_id=project_a.id,
    )
    u2.created_at = now - timedelta(days=8)
    await db_session.commit()

    # u3 — activated + assessed (practitioner), 1 of 2 assigned lessons done 20 days ago.
    u3 = await create_user(
        db_session,
        email="dash-u3@example.com",
        password="hunter2hunter2",
        company_id=company_a.id,
        project_id=project_a.id,
    )
    await create_survey(db_session, u3, status="complete", score_level="practitioner")
    await assign_track(db_session, u3, track_a)
    await assign_lesson(db_session, u3, lesson_a1)
    await assign_lesson(db_session, u3, lesson_a2)
    progress = await complete_lesson(db_session, u3, lesson_a1)
    progress.completed_at = now - timedelta(days=20)  # the factory stamps now()
    await db_session.commit()

    # u4 — activated + assessed (explore), whole assigned track completed, active yesterday.
    u4 = await create_user(
        db_session,
        email="dash-u4@example.com",
        password="hunter2hunter2",
        company_id=company_a.id,
        project_id=project_a.id,
    )
    await create_survey(db_session, u4, status="complete", score_level="explore")
    await assign_track(db_session, u4, track_b)
    await assign_lesson(db_session, u4, lesson_b1)
    await complete_lesson(db_session, u4, lesson_b1)
    await _add_session(db_session, u4, now - timedelta(days=1))

    # u5 — project B, healthy learner: activated + assessed (integrator) + active today.
    u5 = await create_user(
        db_session,
        email="dash-u5@example.com",
        password="hunter2hunter2",
        company_id=company_b.id,
        project_id=project_b.id,
    )
    await create_survey(db_session, u5, status="complete", score_level="integrator")
    await _add_session(db_session, u5, now)

    # One still-new feedback row in project A.
    db_session.add(Feedback(user_id=u3.id, lesson_id=lesson_a1.id, message="More examples please"))
    await db_session.commit()

    return DashSeed(project_a, project_b, track_a, u1, u2, u3, u4, u5)


class TestAdminDashboard:
    @pytest_asyncio.fixture
    async def admin(self, db_session: AsyncSession) -> User:
        return await create_user(db_session, email="dash-admin@example.com", role="admin")

    async def test_unscoped_overview(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_settings: Settings,
        admin: User,
    ) -> None:
        s = await _seed(db_session)
        resp = await client.get("/api/admin/dashboard", headers=auth_headers(admin, test_settings))
        assert resp.status_code == 200
        body = resp.json()

        assert body["tiles"] == {
            "learners": 5,
            "active_week": 2,
            "attention": 3,
            "new_feedback": 1,
        }

        assert len(body["funnels"]) == 2
        funnel_a = next(f for f in body["funnels"] if f["project_id"] == str(s.project_a.id))
        assert funnel_a == {
            "project_id": str(s.project_a.id),
            "project_name": "Alpha Project",
            "company_name": "Alpha Co",
            "invited": 4,
            "activated": 3,
            "assessed": 2,
            "started": 2,
            "completed_track": 1,
        }

        by_user = {item["user_id"]: item for item in body["attention"]}
        assert set(by_user) == {str(s.u1.id), str(s.u2.id), str(s.u3.id)}
        assert by_user[str(s.u1.id)]["kind"] == "never_activated"
        assert by_user[str(s.u2.id)]["kind"] == "not_assessed"
        u3_item = by_user[str(s.u3.id)]
        assert u3_item["kind"] == "stalled"
        assert s.track_a.name in u3_item["reason"]
        assert "20" in u3_item["reason"]
        assert u3_item["project_name"] == "Alpha Project"
        assert u3_item["company_name"] == "Alpha Co"

        assert body["maturity"] == {
            "explore": 0,
            "practitioner": 2,
            "integrator": 1,
            "multiplier": 0,
        }

    async def test_scoped_to_project(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_settings: Settings,
        admin: User,
    ) -> None:
        s = await _seed(db_session)
        resp = await client.get(
            f"/api/admin/dashboard?project_id={s.project_b.id}",
            headers=auth_headers(admin, test_settings),
        )
        assert resp.status_code == 200
        body = resp.json()

        assert body["tiles"]["learners"] == 1
        assert body["tiles"]["new_feedback"] == 0
        assert body["attention"] == []
        assert len(body["funnels"]) == 1
        assert body["funnels"][0]["project_id"] == str(s.project_b.id)
        assert body["funnels"][0]["invited"] == 1
        assert body["funnels"][0]["assessed"] == 1
        assert body["funnels"][0]["started"] == 0
        assert body["funnels"][0]["completed_track"] == 0
        assert body["maturity"] == {
            "explore": 0,
            "practitioner": 0,
            "integrator": 1,
            "multiplier": 0,
        }

    async def test_unknown_project_is_404(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_settings: Settings,
        admin: User,
    ) -> None:
        await _seed(db_session)
        resp = await client.get(
            f"/api/admin/dashboard?project_id={uuid.uuid4()}",
            headers=auth_headers(admin, test_settings),
        )
        assert resp.status_code == 404
        assert resp.json()["error"]["code"] == "not_found"
