from __future__ import annotations

import uuid

from tests.fixtures.auth import auth_headers
from tests.fixtures.factories import create_company, create_project, create_track, create_user


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
