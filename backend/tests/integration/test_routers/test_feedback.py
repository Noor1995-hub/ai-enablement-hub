from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import select

from src.db.models import Feedback
from tests.fixtures.auth import auth_headers
from tests.fixtures.factories import create_lesson, create_module, create_track, create_user

if TYPE_CHECKING:
    from httpx import AsyncClient
    from sqlalchemy.ext.asyncio import AsyncSession

    from src.core.configs.settings import Settings


class TestSubmitFeedback:
    async def test_creates_row_and_returns_201(
        self, client: AsyncClient, db_session: AsyncSession, test_settings: Settings
    ) -> None:
        track = await create_track(db_session)
        module = await create_module(db_session, track)
        lesson = await create_lesson(db_session, module, "Prompting basics")
        user = await create_user(db_session, email="fb-user@example.com")

        response = await client.post(
            "/api/feedback",
            json={"lesson_id": str(lesson.id), "message": "  needs an example  "},
            headers=auth_headers(user, test_settings),
        )

        assert response.status_code == 201
        payload = response.json()
        assert set(payload) == {"id", "created_at"}

        rows = (
            (
                await db_session.execute(
                    select(Feedback).where(Feedback.id == uuid.UUID(payload["id"]))
                )
            )
            .scalars()
            .all()
        )
        assert len(rows) == 1
        assert rows[0].user_id == user.id
        assert rows[0].lesson_id == lesson.id
        assert rows[0].message == "needs an example"  # stored stripped

    async def test_anonymous_is_401(self, client: AsyncClient) -> None:
        response = await client.post(
            "/api/feedback", json={"lesson_id": str(uuid.uuid4()), "message": "hi"}
        )
        assert response.status_code == 401

    async def test_empty_message_is_422(
        self, client: AsyncClient, db_session: AsyncSession, test_settings: Settings
    ) -> None:
        user = await create_user(db_session, email="fb-empty@example.com")
        response = await client.post(
            "/api/feedback",
            json={"lesson_id": str(uuid.uuid4()), "message": "   "},
            headers=auth_headers(user, test_settings),
        )
        assert response.status_code == 422

    async def test_oversized_message_is_422(
        self, client: AsyncClient, db_session: AsyncSession, test_settings: Settings
    ) -> None:
        user = await create_user(db_session, email="fb-big@example.com")
        response = await client.post(
            "/api/feedback",
            json={"lesson_id": str(uuid.uuid4()), "message": "x" * 4001},
            headers=auth_headers(user, test_settings),
        )
        assert response.status_code == 422

    async def test_unknown_lesson_is_404(
        self, client: AsyncClient, db_session: AsyncSession, test_settings: Settings
    ) -> None:
        user = await create_user(db_session, email="fb-404@example.com")
        response = await client.post(
            "/api/feedback",
            json={"lesson_id": str(uuid.uuid4()), "message": "hi"},
            headers=auth_headers(user, test_settings),
        )
        assert response.status_code == 404
