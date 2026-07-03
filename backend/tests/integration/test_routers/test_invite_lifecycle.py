from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

from src.core.security import hash_token, new_opaque_token
from src.repositories.auth_token_repository import AuthTokenRepository
from tests.fixtures.factories import create_user

if TYPE_CHECKING:
    from httpx import AsyncClient
    from sqlalchemy.ext.asyncio import AsyncSession

    from src.services.token_service import TokenService

NEW_PASSWORD = "chosen-by-the-user-99"


class TestInviteLifecycle:
    async def test_full_invite_flow(
        self, client: AsyncClient, db_session: AsyncSession, token_service: TokenService
    ) -> None:
        """The Batch-2 acceptance path: invite → link info → set-password →
        auto-login → normal login; the link is single-use."""
        user = await create_user(
            db_session, email="newhire@example.com", password=None, first_name="Nora"
        )
        raw = await token_service.issue_action_token(user, "invite")

        info = await client.get(f"/api/auth/invite/{raw}")
        assert info.status_code == 200
        assert info.json() == {
            "purpose": "invite",
            "email": "newhire@example.com",
            "first_name": "Nora",
        }

        completed = await client.post(
            "/api/auth/set-password", json={"token": raw, "password": NEW_PASSWORD}
        )
        assert completed.status_code == 200
        access = completed.json()["access_token"]
        me = await client.get("/api/_test/me", headers={"Authorization": f"Bearer {access}"})
        assert me.status_code == 200

        login = await client.post(
            "/api/auth/login", json={"email": "newhire@example.com", "password": NEW_PASSWORD}
        )
        assert login.status_code == 200

        # Single use: the consumed link is dead for both endpoints.
        assert (await client.get(f"/api/auth/invite/{raw}")).status_code == 404
        reuse = await client.post(
            "/api/auth/set-password", json={"token": raw, "password": "another-password-1"}
        )
        assert reuse.status_code == 404

    async def test_unknown_token_is_404(self, client: AsyncClient) -> None:
        response = await client.get(f"/api/auth/invite/{new_opaque_token()}")
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "not_found"

    async def test_expired_token_is_410(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await create_user(db_session, email="late@example.com", password=None)
        raw = new_opaque_token()
        await AuthTokenRepository(db_session).create(
            user.id, hash_token(raw), "invite", datetime.now(UTC) - timedelta(minutes=1)
        )

        info = await client.get(f"/api/auth/invite/{raw}")
        assert info.status_code == 410
        assert info.json()["error"]["code"] == "gone"
        completed = await client.post(
            "/api/auth/set-password", json={"token": raw, "password": NEW_PASSWORD}
        )
        assert completed.status_code == 410

    async def test_invite_for_deactivated_user_is_404(
        self, client: AsyncClient, db_session: AsyncSession, token_service: TokenService
    ) -> None:
        user = await create_user(db_session, email="gone@example.com", password=None)
        raw = await token_service.issue_action_token(user, "invite")
        user.is_active = False
        await db_session.commit()
        assert (await client.get(f"/api/auth/invite/{raw}")).status_code == 404

    async def test_short_password_rejected(
        self, client: AsyncClient, db_session: AsyncSession, token_service: TokenService
    ) -> None:
        user = await create_user(db_session, email="short@example.com", password=None)
        raw = await token_service.issue_action_token(user, "invite")

        response = await client.post(
            "/api/auth/set-password", json={"token": raw, "password": "seven77"}
        )

        assert response.status_code == 422
        error = response.json()["error"]
        assert error["code"] == "validation_error"
        assert error["fields"][0]["field"] == "password"
        # The too-short attempt must not have consumed the token.
        assert (await client.get(f"/api/auth/invite/{raw}")).status_code == 200


class TestResetLifecycle:
    async def test_reset_flow_revokes_sessions_and_old_password(
        self, client: AsyncClient, db_session: AsyncSession, token_service: TokenService
    ) -> None:
        user = await create_user(db_session, email="reset@example.com", password="old-password-1")
        login = await client.post(
            "/api/auth/login", json={"email": "reset@example.com", "password": "old-password-1"}
        )
        old_refresh = login.json()["refresh_token"]

        raw = await token_service.issue_action_token(user, "reset")
        info = await client.get(f"/api/auth/invite/{raw}")
        assert info.status_code == 200
        assert info.json()["purpose"] == "reset"

        completed = await client.post(
            "/api/auth/set-password", json={"token": raw, "password": NEW_PASSWORD}
        )
        assert completed.status_code == 200

        # Every pre-reset session is revoked; the old password is gone.
        replay = await client.post("/api/auth/refresh", json={"refresh_token": old_refresh})
        assert replay.status_code == 401
        old_login = await client.post(
            "/api/auth/login", json={"email": "reset@example.com", "password": "old-password-1"}
        )
        assert old_login.status_code == 401
        new_login = await client.post(
            "/api/auth/login", json={"email": "reset@example.com", "password": NEW_PASSWORD}
        )
        assert new_login.status_code == 200
        # The pair returned by set-password itself must survive the revocation.
        still_valid = await client.post(
            "/api/auth/refresh", json={"refresh_token": completed.json()["refresh_token"]}
        )
        assert still_valid.status_code == 200

    async def test_new_reset_link_revokes_previous_one(
        self, db_session: AsyncSession, client: AsyncClient, token_service: TokenService
    ) -> None:
        user = await create_user(db_session, email="tworesets@example.com", password="pw-123456")
        first = await token_service.issue_action_token(user, "reset")
        second = await token_service.issue_action_token(user, "reset")

        assert (await client.get(f"/api/auth/invite/{first}")).status_code == 404
        assert (await client.get(f"/api/auth/invite/{second}")).status_code == 200

    async def test_set_password_removes_other_outstanding_tokens(
        self, client: AsyncClient, db_session: AsyncSession, token_service: TokenService
    ) -> None:
        user = await create_user(db_session, email="multi@example.com", password=None)
        invite = await token_service.issue_action_token(user, "invite")
        reset = await token_service.issue_action_token(user, "reset")

        completed = await client.post(
            "/api/auth/set-password", json={"token": reset, "password": NEW_PASSWORD}
        )
        assert completed.status_code == 200
        # The unused invite link died with the reset completion.
        assert (await client.get(f"/api/auth/invite/{invite}")).status_code == 404
