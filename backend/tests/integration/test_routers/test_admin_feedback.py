from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import select

from src.db.models import Feedback
from tests.fixtures.auth import auth_headers
from tests.fixtures.factories import (
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


async def _seed(db_session: AsyncSession) -> tuple:
    company = await create_company(db_session)
    project = await create_project(db_session, company)
    learner = await create_user(
        db_session, email=f"{uuid.uuid4()}@x.test", project_id=project.id, company_id=company.id
    )
    track = await create_track(db_session)
    module = await create_module(db_session, track)
    lesson = await create_lesson(db_session, module)
    fb = Feedback(user_id=learner.id, lesson_id=lesson.id, message="More examples please")
    db_session.add(fb)
    await db_session.commit()
    await db_session.refresh(fb)
    return project, track, module, lesson, learner, fb


class TestAdminFeedbackList:
    async def test_list_joins_names_and_defaults_to_new(
        self, client: AsyncClient, db_session: AsyncSession, test_settings: Settings
    ) -> None:
        admin = await create_user(db_session, email="fb1@x.test", role="admin")
        project, track, module, lesson, learner, fb = await _seed(db_session)
        resp = await client.get("/api/admin/feedback", headers=auth_headers(admin, test_settings))
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 1
        item = body["items"][0]
        assert item["id"] == str(fb.id)
        assert item["status"] == "new"
        assert item["message"] == "More examples please"
        assert item["lesson_title"] == lesson.title
        assert item["module_id"] == str(module.id)
        assert item["track_id"] == str(track.id)
        assert item["project_name"] == project.name

    async def test_status_and_track_filters(
        self, client: AsyncClient, db_session: AsyncSession, test_settings: Settings
    ) -> None:
        admin = await create_user(db_session, email="fb2@x.test", role="admin")
        _, track, _, _, _, fb = await _seed(db_session)
        headers = auth_headers(admin, test_settings)
        assert (await client.get("/api/admin/feedback?status=accepted", headers=headers)).json()[
            "total"
        ] == 0
        assert (
            await client.get(f"/api/admin/feedback?track_id={track.id}", headers=headers)
        ).json()["total"] == 1
        assert (
            await client.get(f"/api/admin/feedback?track_id={uuid.uuid4()}", headers=headers)
        ).json()["total"] == 0

    async def test_pagination_contract(
        self, client: AsyncClient, db_session: AsyncSession, test_settings: Settings
    ) -> None:
        admin = await create_user(db_session, email="fb3@x.test", role="admin")
        _project, _track, _module, lesson, learner, _fb = await _seed(db_session)
        for i in range(3):
            db_session.add(Feedback(user_id=learner.id, lesson_id=lesson.id, message=f"note {i}"))
        await db_session.commit()
        resp = await client.get(
            "/api/admin/feedback?limit=2&offset=2", headers=auth_headers(admin, test_settings)
        )
        body = resp.json()
        assert body["total"] == 4
        assert body["limit"] == 2
        assert body["offset"] == 2
        assert len(body["items"]) == 2


class TestFeedbackTriage:
    async def test_accept_stamps_reviewer(
        self, client: AsyncClient, db_session: AsyncSession, test_settings: Settings
    ) -> None:
        admin = await create_user(db_session, email="fb4@x.test", role="admin")
        *_, fb = await _seed(db_session)
        resp = await client.patch(
            f"/api/admin/feedback/{fb.id}",
            json={"status": "accepted"},
            headers=auth_headers(admin, test_settings),
        )
        assert resp.status_code == 204
        row = (await db_session.execute(select(Feedback).where(Feedback.id == fb.id))).scalar_one()
        assert row.status == "accepted"
        assert row.reviewed_by == admin.id
        assert row.reviewed_at is not None

    async def test_back_to_new_clears_review_stamp(
        self, client: AsyncClient, db_session: AsyncSession, test_settings: Settings
    ) -> None:
        admin = await create_user(db_session, email="fb5@x.test", role="admin")
        *_, fb = await _seed(db_session)
        headers = auth_headers(admin, test_settings)
        await client.patch(
            f"/api/admin/feedback/{fb.id}", json={"status": "dismissed"}, headers=headers
        )
        resp = await client.patch(
            f"/api/admin/feedback/{fb.id}", json={"status": "new"}, headers=headers
        )
        assert resp.status_code == 204
        row = (await db_session.execute(select(Feedback).where(Feedback.id == fb.id))).scalar_one()
        assert row.status == "new"
        assert row.reviewed_by is None
        assert row.reviewed_at is None

    async def test_unknown_id_404_and_bad_status_422(
        self, client: AsyncClient, db_session: AsyncSession, test_settings: Settings
    ) -> None:
        admin = await create_user(db_session, email="fb6@x.test", role="admin")
        *_, fb = await _seed(db_session)
        headers = auth_headers(admin, test_settings)
        assert (
            await client.patch(
                f"/api/admin/feedback/{uuid.uuid4()}",
                json={"status": "accepted"},
                headers=headers,
            )
        ).status_code == 404
        assert (
            await client.patch(
                f"/api/admin/feedback/{fb.id}", json={"status": "resolved"}, headers=headers
            )
        ).status_code == 422
