from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

from src.core.security import hash_token, new_opaque_token
from src.repositories.auth_session_repository import AuthSessionRepository
from tests.fixtures.factories import create_user

if TYPE_CHECKING:
    from httpx import AsyncClient
    from sqlalchemy.ext.asyncio import AsyncSession

PASSWORD = "a-valid-password-123"


class TestLogin:
    async def test_valid_credentials_return_working_token_pair(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await create_user(db_session, email="login@example.com", password=PASSWORD)

        response = await client.post(
            "/api/auth/login", json={"email": "login@example.com", "password": PASSWORD}
        )

        assert response.status_code == 200
        body = response.json()
        assert body["token_type"] == "bearer"
        assert body["expires_in"] == 30 * 60
        me = await client.get(
            "/api/me", headers={"Authorization": f"Bearer {body['access_token']}"}
        )
        assert me.status_code == 200
        assert me.json()["id"] == str(user.id)

    async def test_email_lookup_is_case_insensitive(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        await create_user(db_session, email="case@example.com", password=PASSWORD)
        response = await client.post(
            "/api/auth/login", json={"email": "Case@EXAMPLE.com", "password": PASSWORD}
        )
        assert response.status_code == 200

    async def test_wrong_password_rejected(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        await create_user(db_session, email="wrongpw@example.com", password=PASSWORD)
        response = await client.post(
            "/api/auth/login", json={"email": "wrongpw@example.com", "password": "not-it"}
        )
        assert response.status_code == 401
        assert response.json()["error"]["code"] == "unauthorized"
        assert response.headers["WWW-Authenticate"] == "Bearer"

    async def test_unknown_email_rejected(self, client: AsyncClient) -> None:
        response = await client.post(
            "/api/auth/login", json={"email": "ghost@example.com", "password": PASSWORD}
        )
        assert response.status_code == 401

    async def test_invalid_email_format_rejected(self, client: AsyncClient) -> None:
        response = await client.post(
            "/api/auth/login", json={"email": "not-an-email", "password": PASSWORD}
        )
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "validation_error"

    async def test_user_without_password_rejected(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        # Migrated users: password_set=false until re-invited.
        await create_user(db_session, email="invited@example.com", password=None)
        response = await client.post(
            "/api/auth/login", json={"email": "invited@example.com", "password": PASSWORD}
        )
        assert response.status_code == 401

    async def test_inactive_user_rejected(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        await create_user(
            db_session, email="inactive@example.com", password=PASSWORD, is_active=False
        )
        response = await client.post(
            "/api/auth/login", json={"email": "inactive@example.com", "password": PASSWORD}
        )
        assert response.status_code == 401


class TestRefresh:
    async def test_rotation_issues_new_pair_and_kills_old_token(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        await create_user(db_session, email="rotate@example.com", password=PASSWORD)
        login = await client.post(
            "/api/auth/login", json={"email": "rotate@example.com", "password": PASSWORD}
        )
        old_refresh = login.json()["refresh_token"]

        first = await client.post("/api/auth/refresh", json={"refresh_token": old_refresh})
        assert first.status_code == 200
        new_refresh = first.json()["refresh_token"]
        assert new_refresh != old_refresh

        replay = await client.post("/api/auth/refresh", json={"refresh_token": old_refresh})
        assert replay.status_code == 401

        second = await client.post("/api/auth/refresh", json={"refresh_token": new_refresh})
        assert second.status_code == 200

    async def test_garbage_token_rejected(self, client: AsyncClient) -> None:
        response = await client.post(
            "/api/auth/refresh", json={"refresh_token": "never-issued-token"}
        )
        assert response.status_code == 401
        assert response.json()["error"]["code"] == "unauthorized"

    async def test_expired_session_rejected(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await create_user(db_session, email="expired@example.com", password=PASSWORD)
        raw = new_opaque_token()
        await AuthSessionRepository(db_session).create(
            user.id, hash_token(raw), datetime.now(UTC) - timedelta(seconds=1)
        )
        response = await client.post("/api/auth/refresh", json={"refresh_token": raw})
        assert response.status_code == 401

    async def test_deactivated_user_rejected(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await create_user(db_session, email="deact@example.com", password=PASSWORD)
        login = await client.post(
            "/api/auth/login", json={"email": "deact@example.com", "password": PASSWORD}
        )
        user.is_active = False
        await db_session.commit()
        response = await client.post(
            "/api/auth/refresh", json={"refresh_token": login.json()["refresh_token"]}
        )
        assert response.status_code == 401


class TestLogout:
    async def test_logout_revokes_the_session(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        await create_user(db_session, email="logout@example.com", password=PASSWORD)
        login = await client.post(
            "/api/auth/login", json={"email": "logout@example.com", "password": PASSWORD}
        )
        refresh_token = login.json()["refresh_token"]

        logout = await client.post("/api/auth/logout", json={"refresh_token": refresh_token})
        assert logout.status_code == 204

        response = await client.post("/api/auth/refresh", json={"refresh_token": refresh_token})
        assert response.status_code == 401

    async def test_logout_is_idempotent_and_blind(self, client: AsyncClient) -> None:
        response = await client.post(
            "/api/auth/logout", json={"refresh_token": "never-issued-token"}
        )
        assert response.status_code == 204
