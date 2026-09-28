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


class TestSubmitFeedbackRateLimit:
    """Mirrors the TestLoginRateLimit / chat convention: hammer N+1 times on one
    key and assert the over-limit call is 429 + Retry-After. `rate_limiter` is a
    process-global reset by conftest's autouse `_reset_rate_limiter`, so this is
    deterministic."""

    async def test_eleventh_submission_in_the_window_is_429(
        self, client: AsyncClient, db_session: AsyncSession, test_settings: Settings
    ) -> None:
        track = await create_track(db_session)
        module = await create_module(db_session, track)
        lesson = await create_lesson(db_session, module, "Rate limited lesson")
        user = await create_user(db_session, email="fb-flood@example.com")
        headers = auth_headers(user, test_settings)
        body = {"lesson_id": str(lesson.id), "message": "more examples please"}

        for _ in range(10):
            response = await client.post("/api/feedback", json=body, headers=headers)
            assert response.status_code == 201

        response = await client.post("/api/feedback", json=body, headers=headers)
        assert response.status_code == 429
        assert response.json()["error"]["code"] == "rate_limited"
        assert response.headers["Retry-After"] == "600"

    async def test_the_limit_is_per_user(
        self, client: AsyncClient, db_session: AsyncSession, test_settings: Settings
    ) -> None:
        """One learner spamming must not silence their colleagues."""
        track = await create_track(db_session)
        module = await create_module(db_session, track)
        lesson = await create_lesson(db_session, module, "Shared lesson")
        noisy = await create_user(db_session, email="fb-noisy@example.com")
        quiet = await create_user(db_session, email="fb-quiet@example.com")
        body = {"lesson_id": str(lesson.id), "message": "a note"}

        for _ in range(11):
            await client.post(
                "/api/feedback", json=body, headers=auth_headers(noisy, test_settings)
            )

        response = await client.post(
            "/api/feedback", json=body, headers=auth_headers(quiet, test_settings)
        )
        assert response.status_code == 201
