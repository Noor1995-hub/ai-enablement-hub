"""Admin user directory: listing, invites (wired to Batch 2 token machinery),
reset links, roles, cascade delete, assignments, survey results."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import TYPE_CHECKING

import pytest_asyncio
from sqlalchemy import func, select

from tests.fixtures.auth import auth_headers
from tests.fixtures.factories import (
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
    from src.db.models import Company, Project, User


@dataclass
class Org:
    company: Company
    project: Project
    admin: User
    headers: dict[str, str]


@pytest_asyncio.fixture
async def org(db_session: AsyncSession, test_settings: Settings) -> Org:
    company = await create_company(db_session, "Dir Co")
    project = await create_project(db_session, company, "Dir Project")
    admin = await create_user(db_session, email="dir-admin@example.com", role="admin")
    return Org(company, project, admin, auth_headers(admin, test_settings))


def _extract_token(link: str) -> str:
    assert "/invite/" in link
    return link.rsplit("/invite/", 1)[1]


class TestListUsers:
    async def test_shape_names_and_assignments(
        self, client: AsyncClient, db_session: AsyncSession, org: Org
    ) -> None:
        user = await create_user(
            db_session,
            email="dir-user@example.com",
            company_id=org.company.id,
            project_id=org.project.id,
        )
        track = await create_track(db_session, "Dir Track")
        await assign_track(db_session, user, track)

        response = await client.get("/api/admin/users", headers=org.headers)
        assert response.status_code == 200
        listed = {u["email"]: u for u in response.json()["users"]}
        entry = listed["dir-user@example.com"]
        assert entry["company_name"] == "Dir Co"
        assert entry["project_name"] == "Dir Project"
        assert entry["assigned_track_ids"] == [str(track.id)]
        assert entry["assigned_module_ids"] == []
        assert entry["password_set"] is False
        # The admin (no project) has null org names.
        assert listed["dir-admin@example.com"]["company_name"] is None

    async def test_project_filter(
        self, client: AsyncClient, db_session: AsyncSession, org: Org
    ) -> None:
        await create_user(db_session, email="in-project@example.com", project_id=org.project.id)
        await create_user(db_session, email="elsewhere@example.com")
        response = await client.get(
            f"/api/admin/users?project_id={org.project.id}", headers=org.headers
        )
        emails = [u["email"] for u in response.json()["users"]]
        assert emails == ["in-project@example.com"]


class TestInvite:
    async def test_invite_lifecycle_end_to_end(self, client: AsyncClient, org: Org) -> None:
        """Invite → link → invite-info → set-password → login: proves the Batch 3
        endpoint is correctly wired to the Batch 2 token machinery."""
        response = await client.post(
            "/api/admin/invites",
            json={
                "email": "Newbie@Example.com",
                "first_name": "New",
                "last_name": "Bie",
                "project_id": str(org.project.id),
            },
            headers=org.headers,
        )
        assert response.status_code == 201
        # conftest's test_settings has email=None → the send is skipped.
        assert response.json()["email_status"] == "disabled"
        token = _extract_token(response.json()["link"])

        info = await client.get(f"/api/auth/invite/{token}")
        assert info.status_code == 200
        assert info.json() == {
            "purpose": "invite",
            "email": "newbie@example.com",  # normalised
            "first_name": "New",
        }

        set_pw = await client.post(
            "/api/auth/set-password", json={"token": token, "password": "brand-new-pass1"}
        )
        assert set_pw.status_code == 200

        login = await client.post(
            "/api/auth/login",
            json={"email": "newbie@example.com", "password": "brand-new-pass1"},
        )
        assert login.status_code == 200

        users = (await client.get("/api/admin/users", headers=org.headers)).json()["users"]
        invited = next(u for u in users if u["email"] == "newbie@example.com")
        assert invited["password_set"] is True
        assert invited["company_id"] == str(org.company.id)
        assert invited["project_id"] == str(org.project.id)

    async def test_duplicate_email_is_409(
        self, client: AsyncClient, db_session: AsyncSession, org: Org
    ) -> None:
        await create_user(db_session, email="taken@example.com")
        response = await client.post(
            "/api/admin/invites",
            json={
                "email": "taken@example.com",
                "first_name": "Du",
                "last_name": "Plicate",
                "project_id": str(org.project.id),
            },
            headers=org.headers,
        )
        assert response.status_code == 409

    async def test_unknown_project_is_404(self, client: AsyncClient, org: Org) -> None:
        response = await client.post(
            "/api/admin/invites",
            json={
                "email": "lost@example.com",
                "first_name": "Lo",
                "last_name": "St",
                "project_id": str(uuid.uuid4()),
            },
            headers=org.headers,
        )
        assert response.status_code == 404

    async def test_invalid_email_is_422(self, client: AsyncClient, org: Org) -> None:
        response = await client.post(
            "/api/admin/invites",
            json={
                "email": "not-an-email",
                "first_name": "A",
                "last_name": "B",
                "project_id": str(org.project.id),
            },
            headers=org.headers,
        )
        assert response.status_code == 422

    async def test_rate_limited_per_target_email(self, client: AsyncClient, org: Org) -> None:
        body = {
            "email": "hammered@example.com",
            "first_name": "Ha",
            "last_name": "Mmer",
            "project_id": str(uuid.uuid4()),  # 404s, but attempts still count
        }
        for _ in range(5):
            assert (
                await client.post("/api/admin/invites", json=body, headers=org.headers)
            ).status_code == 404
        response = await client.post("/api/admin/invites", json=body, headers=org.headers)
        assert response.status_code == 429
        assert response.headers["Retry-After"] == "60"


class TestResetLink:
    async def test_reset_link_supersedes_previous_one(
        self, client: AsyncClient, db_session: AsyncSession, org: Org
    ) -> None:
        user = await create_user(
            db_session, email="resettee@example.com", password="old-password-1"
        )
        url = f"/api/admin/users/{user.id}/reset-link"
        first = await client.post(url, headers=org.headers)
        assert first.status_code == 200
        assert first.json()["email_status"] == "disabled"
        second = await client.post(url, headers=org.headers)
        assert second.status_code == 200

        stale = _extract_token(first.json()["link"])
        fresh = _extract_token(second.json()["link"])
        assert (await client.get(f"/api/auth/invite/{stale}")).status_code == 404
        info = await client.get(f"/api/auth/invite/{fresh}")
        assert info.status_code == 200
        assert info.json()["purpose"] == "reset"

    async def test_unknown_user_is_404(self, client: AsyncClient, org: Org) -> None:
        response = await client.post(
            f"/api/admin/users/{uuid.uuid4()}/reset-link", headers=org.headers
        )
        assert response.status_code == 404


class TestRoleAndDelete:
    async def test_patch_role(
        self, client: AsyncClient, db_session: AsyncSession, org: Org
    ) -> None:
        user = await create_user(db_session, email="promotee@example.com")
        response = await client.patch(
            f"/api/admin/users/{user.id}", json={"role": "admin"}, headers=org.headers
        )
        assert response.status_code == 204
        users = (await client.get("/api/admin/users", headers=org.headers)).json()["users"]
        assert next(u for u in users if u["id"] == str(user.id))["role"] == "admin"

    async def test_patch_role_to_user_plus(
        self, client: AsyncClient, db_session: AsyncSession, org: Org
    ) -> None:
        user = await create_user(db_session, email="powerup@example.com")
        response = await client.patch(
            f"/api/admin/users/{user.id}", json={"role": "user+"}, headers=org.headers
        )
        assert response.status_code == 204
        users = (await client.get("/api/admin/users", headers=org.headers)).json()["users"]
        assert next(u for u in users if u["id"] == str(user.id))["role"] == "user+"

    async def test_user_plus_is_denied_admin_endpoints(
        self, client: AsyncClient, db_session: AsyncSession, org: Org, test_settings: Settings
    ) -> None:
        """user+ bypasses learning-path locks but holds no admin powers:
        require_admin gates on role == 'admin', so an admin route 403s."""
        power = await create_user(db_session, email="poweruser@example.com", role="user+")
        response = await client.get("/api/admin/users", headers=auth_headers(power, test_settings))
        assert response.status_code == 403

    async def test_invalid_role_is_422(
        self, client: AsyncClient, db_session: AsyncSession, org: Org
    ) -> None:
        user = await create_user(db_session, email="rolefail@example.com")
        response = await client.patch(
            f"/api/admin/users/{user.id}", json={"role": "superadmin"}, headers=org.headers
        )
        assert response.status_code == 422

    async def test_delete_cascades_all_user_data(
        self, client: AsyncClient, db_session: AsyncSession, org: Org
    ) -> None:
        from src.db.models import LessonProgress, SurveyResponse, UserTrack

        user = await create_user(db_session, email="doomed@example.com", password="doomed-pass-1")
        track = await create_track(db_session, "Doom Track")
        module = await create_module(db_session, track, "Doom Module")
        lesson = await create_lesson(db_session, module, "Doom Lesson")
        await assign_track(db_session, user, track)
        await complete_lesson(db_session, user, lesson)
        await create_survey(db_session, user)
        login = await client.post(
            "/api/auth/login", json={"email": "doomed@example.com", "password": "doomed-pass-1"}
        )
        assert login.status_code == 200

        response = await client.delete(f"/api/admin/users/{user.id}", headers=org.headers)
        assert response.status_code == 204

        for model in (SurveyResponse, LessonProgress, UserTrack):
            count = (
                await db_session.execute(
                    select(func.count()).select_from(model).where(model.user_id == user.id)
                )
            ).scalar_one()
            assert count == 0, model.__name__
        # The orphaned refresh token can no longer be used.
        refresh = await client.post(
            "/api/auth/refresh", json={"refresh_token": login.json()["refresh_token"]}
        )
        assert refresh.status_code == 401

    async def test_delete_unknown_user_is_404(self, client: AsyncClient, org: Org) -> None:
        response = await client.delete(f"/api/admin/users/{uuid.uuid4()}", headers=org.headers)
        assert response.status_code == 404


class TestAssignments:
    async def test_assign_and_unassign_track(
        self, client: AsyncClient, db_session: AsyncSession, org: Org, test_settings: Settings
    ) -> None:
        user = await create_user(db_session, email="assignee@example.com")
        track = await create_track(db_session, "Assign Track")
        url = f"/api/admin/users/{user.id}/tracks/{track.id}"

        for _ in range(2):  # idempotent
            assert (
                await client.put(url, json={"assigned": True}, headers=org.headers)
            ).status_code == 204
        graph = (
            await client.get("/api/learning/graph", headers=auth_headers(user, test_settings))
        ).json()
        assert next(t for t in graph["tracks"] if t["id"] == str(track.id))["assigned"] is True

        assert (
            await client.put(url, json={"assigned": False}, headers=org.headers)
        ).status_code == 204
        graph = (
            await client.get("/api/learning/graph", headers=auth_headers(user, test_settings))
        ).json()
        assert next(t for t in graph["tracks"] if t["id"] == str(track.id))["assigned"] is False

    async def test_assign_track_cascades_to_modules_and_lessons(
        self, client: AsyncClient, db_session: AsyncSession, org: Org
    ) -> None:
        user = await create_user(db_session, email="cascade-track@example.com")
        track = await create_track(db_session, "Cascade Track")
        module = await create_module(db_session, track, "Cascade Module")
        lesson = await create_lesson(db_session, module, "Cascade Lesson")

        response = await client.put(
            f"/api/admin/users/{user.id}/tracks/{track.id}",
            json={"assigned": True},
            headers=org.headers,
        )
        assert response.status_code == 204

        overview = (await client.get("/api/admin/learning", headers=org.headers)).json()
        entry = next(u for u in overview["users"] if u["id"] == str(user.id))
        assert entry["assigned_track_ids"] == [str(track.id)]
        assert entry["assigned_module_ids"] == [str(module.id)]
        assert entry["assigned_lesson_ids"] == [str(lesson.id)]

    async def test_unassign_track_cascades_to_modules_and_lessons(
        self, client: AsyncClient, db_session: AsyncSession, org: Org
    ) -> None:
        user = await create_user(db_session, email="cascade-track-off@example.com")
        track = await create_track(db_session, "Cascade Off Track")
        module = await create_module(db_session, track, "Cascade Off Module")
        await create_lesson(db_session, module, "Cascade Off Lesson")
        url = f"/api/admin/users/{user.id}/tracks/{track.id}"
        assert (
            await client.put(url, json={"assigned": True}, headers=org.headers)
        ).status_code == 204

        response = await client.put(url, json={"assigned": False}, headers=org.headers)
        assert response.status_code == 204

        overview = (await client.get("/api/admin/learning", headers=org.headers)).json()
        entry = next(u for u in overview["users"] if u["id"] == str(user.id))
        assert entry["assigned_track_ids"] == []
        assert entry["assigned_module_ids"] == []
        assert entry["assigned_lesson_ids"] == []

    async def test_assign_track_with_no_modules_does_not_error(
        self, client: AsyncClient, db_session: AsyncSession, org: Org
    ) -> None:
        user = await create_user(db_session, email="cascade-empty-track@example.com")
        track = await create_track(db_session, "Empty Cascade Track")

        response = await client.put(
            f"/api/admin/users/{user.id}/tracks/{track.id}",
            json={"assigned": True},
            headers=org.headers,
        )
        assert response.status_code == 204
        overview = (await client.get("/api/admin/learning", headers=org.headers)).json()
        entry = next(u for u in overview["users"] if u["id"] == str(user.id))
        assert entry["assigned_track_ids"] == [str(track.id)]
        assert entry["assigned_module_ids"] == []

    async def test_assign_module_and_learning_overview(
        self, client: AsyncClient, db_session: AsyncSession, org: Org
    ) -> None:
        user = await create_user(db_session, email="mod-assignee@example.com", first_name="Aaa")
        track = await create_track(db_session, "Overview Track")
        module = await create_module(db_session, track, "Overview Module")
        response = await client.put(
            f"/api/admin/users/{user.id}/modules/{module.id}",
            json={"assigned": True},
            headers=org.headers,
        )
        assert response.status_code == 204

        overview = (await client.get("/api/admin/learning", headers=org.headers)).json()
        assert any(m["id"] == str(module.id) for m in overview["modules"])
        entry = next(u for u in overview["users"] if u["id"] == str(user.id))
        assert entry["assigned_module_ids"] == [str(module.id)]

    async def test_assign_and_unassign_lesson(
        self, client: AsyncClient, db_session: AsyncSession, org: Org, test_settings: Settings
    ) -> None:
        user = await create_user(db_session, email="lesson-assignee@example.com")
        track = await create_track(db_session, "Lesson Track")
        module = await create_module(db_session, track, "Lesson Module")
        lesson = await create_lesson(db_session, module, "Assignable Lesson")
        url = f"/api/admin/users/{user.id}/lessons/{lesson.id}"

        for _ in range(2):  # idempotent
            assert (
                await client.put(url, json={"assigned": True}, headers=org.headers)
            ).status_code == 204
        body = (
            await client.get(
                f"/api/modules/{module.id}/lessons", headers=auth_headers(user, test_settings)
            )
        ).json()
        assert body["lessons"][0]["assigned"] is True

        assert (
            await client.put(url, json={"assigned": False}, headers=org.headers)
        ).status_code == 204
        overview = (await client.get("/api/admin/learning", headers=org.headers)).json()
        entry = next(u for u in overview["users"] if u["id"] == str(user.id))
        assert entry["assigned_lesson_ids"] == []

    async def test_bulk_assign_and_unassign_tracks(
        self, client: AsyncClient, db_session: AsyncSession, org: Org
    ) -> None:
        user = await create_user(db_session, email="bulk-tracks@example.com")
        tracks = [await create_track(db_session, f"Bulk T{i}", sort_order=i) for i in range(3)]
        url = f"/api/admin/users/{user.id}/tracks"
        ids = [str(t.id) for t in tracks]

        response = await client.put(
            url, json={"track_ids": ids, "assigned": True}, headers=org.headers
        )
        assert response.status_code == 204
        overview = (await client.get("/api/admin/learning", headers=org.headers)).json()
        entry = next(u for u in overview["users"] if u["id"] == str(user.id))
        assert sorted(entry["assigned_track_ids"]) == sorted(ids)

        response = await client.put(
            url, json={"track_ids": ids, "assigned": False}, headers=org.headers
        )
        assert response.status_code == 204
        overview = (await client.get("/api/admin/learning", headers=org.headers)).json()
        entry = next(u for u in overview["users"] if u["id"] == str(user.id))
        assert entry["assigned_track_ids"] == []

        response = await client.put(
            url,
            json={"track_ids": [str(uuid.uuid4())], "assigned": True},
            headers=org.headers,
        )
        assert response.status_code == 404

    async def test_bulk_assign_and_unassign_modules(
        self, client: AsyncClient, db_session: AsyncSession, org: Org
    ) -> None:
        user = await create_user(db_session, email="bulk-mods@example.com")
        track = await create_track(db_session, "Bulk Track")
        modules = [
            await create_module(db_session, track, f"Bulk M{i}", sort_order=i) for i in range(3)
        ]
        url = f"/api/admin/users/{user.id}/modules"
        ids = [str(m.id) for m in modules]

        response = await client.put(
            url, json={"module_ids": ids, "assigned": True}, headers=org.headers
        )
        assert response.status_code == 204
        overview = (await client.get("/api/admin/learning", headers=org.headers)).json()
        entry = next(u for u in overview["users"] if u["id"] == str(user.id))
        assert sorted(entry["assigned_module_ids"]) == sorted(ids)

        response = await client.put(
            url, json={"module_ids": ids[:2], "assigned": False}, headers=org.headers
        )
        assert response.status_code == 204
        overview = (await client.get("/api/admin/learning", headers=org.headers)).json()
        entry = next(u for u in overview["users"] if u["id"] == str(user.id))
        assert entry["assigned_module_ids"] == [ids[2]]

    async def test_bulk_assign_lessons_and_overview_lists_lessons(
        self, client: AsyncClient, db_session: AsyncSession, org: Org
    ) -> None:
        user = await create_user(db_session, email="bulk-lessons@example.com")
        track = await create_track(db_session, "Bulk L Track")
        module = await create_module(db_session, track, "Bulk L Module")
        lessons = [
            await create_lesson(db_session, module, f"Bulk L{i}", sort_order=i) for i in range(3)
        ]
        ids = [str(le.id) for le in lessons]

        response = await client.put(
            f"/api/admin/users/{user.id}/lessons",
            json={"lesson_ids": ids, "assigned": True},
            headers=org.headers,
        )
        assert response.status_code == 204

        overview = (await client.get("/api/admin/learning", headers=org.headers)).json()
        listed = [le for le in overview["lessons"] if le["module_id"] == str(module.id)]
        assert [le["id"] for le in listed] == ids  # ordered by sort_order
        entry = next(u for u in overview["users"] if u["id"] == str(user.id))
        assert sorted(entry["assigned_lesson_ids"]) == sorted(ids)

    async def test_bulk_with_unknown_id_is_404_and_writes_nothing(
        self, client: AsyncClient, db_session: AsyncSession, org: Org
    ) -> None:
        user = await create_user(db_session, email="bulk-404@example.com")
        track = await create_track(db_session, "Bulk 404 Track")
        module = await create_module(db_session, track, "Bulk 404 Module")
        lesson = await create_lesson(db_session, module, "Bulk 404 Lesson")

        response = await client.put(
            f"/api/admin/users/{user.id}/modules",
            json={"module_ids": [str(module.id), str(uuid.uuid4())], "assigned": True},
            headers=org.headers,
        )
        assert response.status_code == 404
        response = await client.put(
            f"/api/admin/users/{user.id}/lessons",
            json={"lesson_ids": [str(lesson.id), str(uuid.uuid4())], "assigned": True},
            headers=org.headers,
        )
        assert response.status_code == 404

        overview = (await client.get("/api/admin/learning", headers=org.headers)).json()
        entry = next(u for u in overview["users"] if u["id"] == str(user.id))
        assert entry["assigned_module_ids"] == []
        assert entry["assigned_lesson_ids"] == []

    async def test_bulk_empty_list_is_422(
        self, client: AsyncClient, db_session: AsyncSession, org: Org
    ) -> None:
        user = await create_user(db_session, email="bulk-empty@example.com")
        response = await client.put(
            f"/api/admin/users/{user.id}/modules",
            json={"module_ids": [], "assigned": True},
            headers=org.headers,
        )
        assert response.status_code == 422

    async def test_unknown_user_or_lesson_is_404(
        self, client: AsyncClient, db_session: AsyncSession, org: Org
    ) -> None:
        user = await create_user(db_session, email="lesson-half-known@example.com")
        track = await create_track(db_session, "Lesson Half Track")
        module = await create_module(db_session, track, "Lesson Half Module")
        lesson = await create_lesson(db_session, module, "Lesson Half Lesson")
        assert (
            await client.put(
                f"/api/admin/users/{uuid.uuid4()}/lessons/{lesson.id}",
                json={"assigned": True},
                headers=org.headers,
            )
        ).status_code == 404
        assert (
            await client.put(
                f"/api/admin/users/{user.id}/lessons/{uuid.uuid4()}",
                json={"assigned": True},
                headers=org.headers,
            )
        ).status_code == 404

    async def test_unknown_user_or_track_is_404(
        self, client: AsyncClient, db_session: AsyncSession, org: Org
    ) -> None:
        user = await create_user(db_session, email="half-known@example.com")
        track = await create_track(db_session, "Half Track")
        assert (
            await client.put(
                f"/api/admin/users/{uuid.uuid4()}/tracks/{track.id}",
                json={"assigned": True},
                headers=org.headers,
            )
        ).status_code == 404
        assert (
            await client.put(
                f"/api/admin/users/{user.id}/tracks/{uuid.uuid4()}",
                json={"assigned": True},
                headers=org.headers,
            )
        ).status_code == 404


class TestSurveyResults:
    async def test_levels_bulk_lookup(
        self, client: AsyncClient, db_session: AsyncSession, org: Org
    ) -> None:
        done = await create_user(db_session, email="scored@example.com")
        pending = await create_user(db_session, email="unscored@example.com")
        await create_survey(db_session, done, status="complete", score_level="practitioner")
        await create_survey(db_session, pending, status="in_progress")

        response = await client.get(
            f"/api/admin/surveys?user_ids={done.id},{pending.id}", headers=org.headers
        )
        assert response.status_code == 200
        assert response.json() == {"levels": {str(done.id): "practitioner"}}

    async def test_levels_without_param_is_empty(self, client: AsyncClient, org: Org) -> None:
        response = await client.get("/api/admin/surveys", headers=org.headers)
        assert response.json() == {"levels": {}}

    async def test_levels_with_garbage_ids_is_422(self, client: AsyncClient, org: Org) -> None:
        response = await client.get("/api/admin/surveys?user_ids=not-a-uuid", headers=org.headers)
        assert response.status_code == 422

    async def test_user_survey_null_when_incomplete(
        self, client: AsyncClient, db_session: AsyncSession, org: Org
    ) -> None:
        user = await create_user(db_session, email="in-flight@example.com")
        await create_survey(db_session, user, status="in_progress")
        response = await client.get(f"/api/admin/surveys/{user.id}", headers=org.headers)
        assert response.status_code == 200
        assert response.json() == {"survey": None}

    async def test_user_survey_full_row_when_complete(
        self, client: AsyncClient, db_session: AsyncSession, org: Org
    ) -> None:
        user = await create_user(db_session, email="finished@example.com")
        await create_survey(
            db_session,
            user,
            status="complete",
            score_level="explore",
            usage_band="regular",
            c1_rung=2,
            have_count=1,
            safety_flag=False,
            mandatory_modules=["trust"],
            job_title="Analyst",
        )
        response = await client.get(f"/api/admin/surveys/{user.id}", headers=org.headers)
        survey = response.json()["survey"]
        assert survey["score_level"] == "explore"
        assert survey["usage_band"] == "regular"
        assert survey["mandatory_modules"] == ["trust"]
        assert survey["job_title"] == "Analyst"
        assert survey["c5_codes"] == ["KEPT_OUT"]

    async def test_user_survey_unknown_user_is_404(self, client: AsyncClient, org: Org) -> None:
        response = await client.get(f"/api/admin/surveys/{uuid.uuid4()}", headers=org.headers)
        assert response.status_code == 404
