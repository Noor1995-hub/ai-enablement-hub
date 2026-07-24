from __future__ import annotations

import uuid

from sqlalchemy import select

from src.db.models import ProjectTrackDefault, UserLesson, UserModule, UserTrack
from tests.fixtures.auth import auth_headers
from tests.fixtures.factories import (
    assign_track,
    create_company,
    create_lesson,
    create_module,
    create_project,
    create_track,
    create_user,
)


class TestDefaultsEndpoints:
    async def test_get_empty_defaults(self, client, db_session, test_settings) -> None:
        admin = await create_user(db_session, email="a1@x.test", role="admin")
        company = await create_company(db_session)
        project = await create_project(db_session, company)
        resp = await client.get(
            f"/api/admin/projects/{project.id}/defaults",
            headers=auth_headers(admin, test_settings),
        )
        assert resp.status_code == 200
        assert resp.json() == {"track_ids": []}

    async def test_put_then_get_roundtrip(self, client, db_session, test_settings) -> None:
        admin = await create_user(db_session, email="a2@x.test", role="admin")
        company = await create_company(db_session)
        project = await create_project(db_session, company)
        track = await create_track(db_session)
        headers = auth_headers(admin, test_settings)
        put = await client.put(
            f"/api/admin/projects/{project.id}/defaults",
            json={"track_ids": [str(track.id)]},
            headers=headers,
        )
        assert put.status_code == 204
        got = await client.get(f"/api/admin/projects/{project.id}/defaults", headers=headers)
        assert got.json() == {"track_ids": [str(track.id)]}

    async def test_put_empty_clears(self, client, db_session, test_settings) -> None:
        admin = await create_user(db_session, email="a3@x.test", role="admin")
        company = await create_company(db_session)
        project = await create_project(db_session, company)
        track = await create_track(db_session)
        headers = auth_headers(admin, test_settings)
        await client.put(
            f"/api/admin/projects/{project.id}/defaults",
            json={"track_ids": [str(track.id)]},
            headers=headers,
        )
        cleared = await client.put(
            f"/api/admin/projects/{project.id}/defaults", json={"track_ids": []}, headers=headers
        )
        assert cleared.status_code == 204
        got = await client.get(f"/api/admin/projects/{project.id}/defaults", headers=headers)
        assert got.json() == {"track_ids": []}

    async def test_unknown_project_404(self, client, db_session, test_settings) -> None:
        admin = await create_user(db_session, email="a4@x.test", role="admin")
        resp = await client.get(
            f"/api/admin/projects/{uuid.uuid4()}/defaults",
            headers=auth_headers(admin, test_settings),
        )
        assert resp.status_code == 404

    async def test_unknown_track_404_writes_nothing(
        self, client, db_session, test_settings
    ) -> None:
        admin = await create_user(db_session, email="a5@x.test", role="admin")
        company = await create_company(db_session)
        project = await create_project(db_session, company)
        headers = auth_headers(admin, test_settings)
        resp = await client.put(
            f"/api/admin/projects/{project.id}/defaults",
            json={"track_ids": [str(uuid.uuid4())]},
            headers=headers,
        )
        assert resp.status_code == 404
        got = await client.get(f"/api/admin/projects/{project.id}/defaults", headers=headers)
        assert got.json() == {"track_ids": []}


class TestMaterializeOnInvite:
    async def _project_with_default(self, db_session):
        company = await create_company(db_session)
        project = await create_project(db_session, company)
        track = await create_track(db_session)
        module = await create_module(db_session, track)
        lesson = await create_lesson(db_session, module)
        db_session.add(ProjectTrackDefault(project_id=project.id, track_id=track.id))
        await db_session.commit()
        return project, track, module, lesson

    async def test_invite_materializes_defaults_with_provenance(
        self, client, db_session, test_settings
    ) -> None:
        admin = await create_user(db_session, email="m1@x.test", role="admin")
        project, track, module, lesson = await self._project_with_default(db_session)
        resp = await client.post(
            "/api/admin/invites",
            json={
                "email": "newbie@example.com",
                "first_name": "New",
                "last_name": "Bie",
                "project_id": str(project.id),
                "send_email": False,
            },
            headers=auth_headers(admin, test_settings),
        )
        assert resp.status_code == 201
        rows = (await db_session.execute(select(UserTrack))).scalars().all()
        assert [(r.track_id, r.assigned_via) for r in rows if r.track_id == track.id] == [
            (track.id, "default")
        ]
        module_rows = (await db_session.execute(select(UserModule))).scalars().all()
        lesson_rows = (await db_session.execute(select(UserLesson))).scalars().all()
        assert {r.assigned_via for r in module_rows} == {"default"}
        assert {r.lesson_id for r in lesson_rows} == {lesson.id}

    async def test_invite_without_defaults_assigns_nothing(
        self, client, db_session, test_settings
    ) -> None:
        admin = await create_user(db_session, email="m2@x.test", role="admin")
        company = await create_company(db_session)
        project = await create_project(db_session, company)
        resp = await client.post(
            "/api/admin/invites",
            json={
                "email": "plain@example.com",
                "first_name": "Pl",
                "last_name": "Ain",
                "project_id": str(project.id),
                "send_email": False,
            },
            headers=auth_headers(admin, test_settings),
        )
        assert resp.status_code == 201
        assert (await db_session.execute(select(UserTrack))).scalars().all() == []


class TestApplyDefaults:
    async def test_apply_is_additive_and_keeps_manual_provenance(
        self, client, db_session, test_settings
    ) -> None:
        admin = await create_user(db_session, email="ap1@x.test", role="admin")
        company = await create_company(db_session)
        project = await create_project(db_session, company)
        track = await create_track(db_session)
        extra_track = await create_track(db_session)
        existing = await create_user(
            db_session, email="old@x.test", project_id=project.id, company_id=company.id
        )
        await assign_track(db_session, existing, extra_track)  # manual, pre-existing
        db_session.add(ProjectTrackDefault(project_id=project.id, track_id=track.id))
        await db_session.commit()
        resp = await client.post(
            f"/api/admin/projects/{project.id}/defaults/apply",
            headers=auth_headers(admin, test_settings),
        )
        assert resp.status_code == 200
        assert resp.json() == {"users_updated": 1}
        rows = (await db_session.execute(select(UserTrack))).scalars().all()
        by_track = {r.track_id: r.assigned_via for r in rows}
        assert by_track[track.id] == "default"  # backfilled
        assert by_track[extra_track.id] == "manual"  # untouched, never removed/rewritten
