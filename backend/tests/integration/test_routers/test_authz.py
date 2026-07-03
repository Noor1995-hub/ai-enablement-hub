from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from src.core.security import create_access_token
from tests.fixtures.factories import create_user

if TYPE_CHECKING:
    from httpx import AsyncClient
    from sqlalchemy.ext.asyncio import AsyncSession

    from src.core.configs.settings import Settings


def bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


class TestGetCurrentUser:
    async def test_missing_token_is_401(self, client: AsyncClient) -> None:
        response = await client.get("/api/_test/me")
        assert response.status_code == 401
        assert response.json()["error"]["code"] == "unauthorized"
        assert response.headers["WWW-Authenticate"] == "Bearer"

    async def test_garbage_token_is_401(self, client: AsyncClient) -> None:
        response = await client.get("/api/_test/me", headers=bearer("not.a.jwt"))
        assert response.status_code == 401

    async def test_expired_token_is_401(
        self, client: AsyncClient, db_session: AsyncSession, test_settings: Settings
    ) -> None:
        user = await create_user(db_session, email="expired-jwt@example.com", password=None)
        expired_auth = test_settings.auth.model_copy(update={"access_token_minutes": -1})
        response = await client.get(
            "/api/_test/me", headers=bearer(create_access_token(user.id, expired_auth))
        )
        assert response.status_code == 401

    async def test_wrong_secret_token_is_401(
        self, client: AsyncClient, db_session: AsyncSession, test_settings: Settings
    ) -> None:
        from pydantic import SecretStr

        user = await create_user(db_session, email="forged@example.com", password=None)
        forged_auth = test_settings.auth.model_copy(
            update={"jwt_secret": SecretStr("attacker-secret-0123456789-0123456789")}
        )
        response = await client.get(
            "/api/_test/me", headers=bearer(create_access_token(user.id, forged_auth))
        )
        assert response.status_code == 401

    async def test_token_for_unknown_user_is_401(
        self, client: AsyncClient, test_settings: Settings
    ) -> None:
        response = await client.get(
            "/api/_test/me", headers=bearer(create_access_token(uuid.uuid4(), test_settings.auth))
        )
        assert response.status_code == 401

    async def test_token_for_deactivated_user_is_401(
        self, client: AsyncClient, db_session: AsyncSession, test_settings: Settings
    ) -> None:
        user = await create_user(
            db_session, email="benched@example.com", password=None, is_active=False
        )
        response = await client.get(
            "/api/_test/me", headers=bearer(create_access_token(user.id, test_settings.auth))
        )
        assert response.status_code == 401

    async def test_valid_token_loads_role_from_db(
        self, client: AsyncClient, db_session: AsyncSession, test_settings: Settings
    ) -> None:
        user = await create_user(db_session, email="reader@example.com", password=None)
        response = await client.get(
            "/api/_test/me", headers=bearer(create_access_token(user.id, test_settings.auth))
        )
        assert response.status_code == 200
        assert response.json() == {"id": str(user.id), "role": "user"}


class TestRequireAdmin:
    async def test_plain_user_is_403(
        self, client: AsyncClient, db_session: AsyncSession, test_settings: Settings
    ) -> None:
        user = await create_user(db_session, email="pleb@example.com", password=None)
        response = await client.get(
            "/api/_test/admin", headers=bearer(create_access_token(user.id, test_settings.auth))
        )
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "forbidden"

    async def test_admin_passes(
        self, client: AsyncClient, db_session: AsyncSession, test_settings: Settings
    ) -> None:
        admin = await create_user(db_session, email="boss@example.com", password=None, role="admin")
        response = await client.get(
            "/api/_test/admin", headers=bearer(create_access_token(admin.id, test_settings.auth))
        )
        assert response.status_code == 200

    async def test_role_change_takes_effect_immediately(
        self, client: AsyncClient, db_session: AsyncSession, test_settings: Settings
    ) -> None:
        """No role claim in the JWT: demotion applies on the very next request
        with the same still-valid token."""
        user = await create_user(
            db_session, email="demoted@example.com", password=None, role="admin"
        )
        token = create_access_token(user.id, test_settings.auth)
        assert (await client.get("/api/_test/admin", headers=bearer(token))).status_code == 200

        user.role = "user"
        await db_session.commit()
        assert (await client.get("/api/_test/admin", headers=bearer(token))).status_code == 403


class TestPublicEndpoints:
    async def test_auth_endpoints_do_not_require_a_token(self, client: AsyncClient) -> None:
        # 404/204/401 (never "401 missing credentials") prove these are public.
        assert (await client.get("/api/auth/invite/unknown-token")).status_code == 404
        assert (
            await client.post("/api/auth/logout", json={"refresh_token": "x"})
        ).status_code == 204
        assert (await client.get("/api/health")).status_code == 200
