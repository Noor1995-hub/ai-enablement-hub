from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Literal

from src.core.security import create_access_token, hash_token, new_opaque_token
from src.services.exceptions import (
    InvalidSessionError,
    TokenExpiredError,
    TokenNotFoundError,
)

if TYPE_CHECKING:
    from src.core.configs.auth import AuthSettings
    from src.db.models import AuthToken, User
    from src.repositories.base import (
        AbstractAuthSessionRepository,
        AbstractAuthTokenRepository,
        AbstractUserRepository,
    )

__all__ = ["TokenPair", "TokenService"]

logger = logging.getLogger(__name__)

TokenPurpose = Literal["invite", "reset", "entra_login"]
# The purposes an emailed link can carry; the only ones peek/consume accept by default.
ActionPurpose = Literal["invite", "reset"]

# Action-token purposes reachable via the invite/set-password endpoints. A
# purpose outside this set (entra_login) must be invisible there: a leaked
# login code must never be able to set a password.
_ACTION_PURPOSES: tuple[ActionPurpose, ...] = ("invite", "reset")

# An entra_login code only bridges the OAuth callback redirect to the SPA's
# redeem POST — seconds of legitimate lifetime.
_LOGIN_CODE_TTL_SECONDS = 60

# Grace window for refresh-token reuse detection. The SPA's refresh single-flight
# is per tab while tokens sit in shared localStorage, so two tabs whose access
# token expires together both POST the same refresh token: the loser presents a
# token the winner revoked a moment ago. That is a benign race, not theft, and
# must not burn the family (which would kill the winner's brand-new session and
# every other device). 30 s comfortably covers a concurrent request round-trip.
# A later replay of a token revoked by rotation/logout is treated as a leaked
# token (family-revoked tokens never are -- see refresh_pair).
_REUSE_GRACE_SECONDS = 30


@dataclass(frozen=True)
class TokenPair:
    access_token: str
    refresh_token: str
    expires_in: int


class TokenService:
    """All token machinery: JWT access tokens, rotating refresh sessions, and
    single-use invite/reset action tokens. Raw opaque tokens never touch the DB —
    only their SHA-256 (see core/security.py)."""

    def __init__(
        self,
        users: AbstractUserRepository,
        tokens: AbstractAuthTokenRepository,
        sessions: AbstractAuthSessionRepository,
        auth: AuthSettings,
    ) -> None:
        self._users = users
        self._tokens = tokens
        self._sessions = sessions
        self._auth = auth

    # -- access + refresh -------------------------------------------------

    async def issue_pair(self, user: User) -> TokenPair:
        raw_refresh = new_opaque_token()
        expires_at = datetime.now(UTC) + timedelta(days=self._auth.refresh_token_days)
        await self._sessions.create(user.id, hash_token(raw_refresh), expires_at)
        return TokenPair(
            access_token=create_access_token(user.id, self._auth),
            refresh_token=raw_refresh,
            expires_in=self._auth.access_token_minutes * 60,
        )

    async def refresh_pair(self, raw_refresh: str) -> TokenPair:
        """Rotation-on-use: the presented refresh token is revoked and a new pair
        issued (sliding refresh lifetime). Raises InvalidSessionError.

        Presenting an already-REVOKED token is treated as theft, not as an
        ordinary failure: rotation means a live token is revoked exactly once, so
        a second presentation is either the legitimate holder replaying a token
        someone else already used, or the thief. Either way the family is burnt
        (RFC 9700 / OAuth 2 BCP). Unknown and merely-expired tokens are NOT
        treated that way -- an unknown hash identifies no user, and expiry is the
        normal end of a session.

        Only a token revoked one-by-one through revoke() counts. That is rotation
        or logout, and both stamp last_used_at (they can't be told apart, so a
        logged-out token replayed later also burns the family, which is acceptable).
        revoke_all_for_user() (set-password, or a previous detection) leaves
        last_used_at NULL. Such a token is a stale device that was already logged
        out, not a replay, so it only 401s. Otherwise every stale device would
        kill the session the user just created after a password reset.

        Exception: a replay within _REUSE_GRACE_SECONDS of revoked_at is the
        multi-tab race (see the constant) and only 401s.

        Honest limitations: the daily cleanup task deletes revoked sessions
        (purge_expired -> delete_dead), so a token replayed after that sweep
        reads as unknown and goes undetected. Detection covers the window that
        matters -- while the stolen token is still fresh. The family revoke is
        also not serialized against a concurrent rotation of a live sibling
        session: a refresh that passes revoke() just before the family UPDATE
        mints a session that survives it (needs millisecond interleaving).
        """
        now = datetime.now(UTC)
        auth_session = await self._sessions.get_by_hash(hash_token(raw_refresh))
        if auth_session is None:
            raise InvalidSessionError
        if auth_session.revoked_at is not None:
            revoked_one_by_one = auth_session.last_used_at is not None
            outside_grace = now - auth_session.revoked_at > timedelta(seconds=_REUSE_GRACE_SECONDS)
            if revoked_one_by_one and outside_grace:
                logger.warning(
                    "refresh token reuse detected for user %s; revoking all sessions",
                    auth_session.user_id,
                )
                await self._sessions.revoke_all_for_user(auth_session.user_id)
            raise InvalidSessionError
        if auth_session.expires_at <= now:
            raise InvalidSessionError
        user = await self._users.get_by_id(auth_session.user_id)
        if user is None or not user.is_active:
            raise InvalidSessionError
        # Rotation must win exactly once: if a concurrent refresh already revoked
        # this session, do not mint a second pair.
        if not await self._sessions.revoke(auth_session):
            raise InvalidSessionError
        return await self.issue_pair(user)

    async def revoke_session(self, raw_refresh: str) -> None:
        """Logout. Idempotent: unknown or already-revoked tokens are a no-op."""
        auth_session = await self._sessions.get_by_hash(hash_token(raw_refresh))
        if auth_session is not None and auth_session.revoked_at is None:
            await self._sessions.revoke(auth_session)

    # -- invite / reset action tokens --------------------------------------

    async def issue_action_token(self, user: User, purpose: TokenPurpose) -> str:
        """Create a single-use token and return its raw form (the only time it
        exists unhashed). A new reset token revokes prior unused reset tokens."""
        if purpose == "reset":
            await self._tokens.delete_unconsumed(user.id, purpose="reset")
        ttl_days = self._auth.invite_ttl_days if purpose == "invite" else self._auth.reset_ttl_days
        raw = new_opaque_token()
        expires_at = datetime.now(UTC) + timedelta(days=ttl_days)
        await self._tokens.create(user.id, hash_token(raw), purpose, expires_at)
        return raw

    async def peek_action_token(
        self, raw: str, purposes: tuple[str, ...] = _ACTION_PURPOSES
    ) -> tuple[AuthToken, User]:
        """Validate without consuming (the invite-info endpoint).

        Raises TokenNotFoundError (unknown/used/wrong purpose/user gone or
        inactive) or TokenExpiredError.
        """
        token = await self._tokens.get_by_hash(hash_token(raw))
        if token is None or token.consumed_at is not None or token.purpose not in purposes:
            raise TokenNotFoundError
        if token.expires_at <= datetime.now(UTC):
            raise TokenExpiredError
        user = await self._users.get_by_id(token.user_id)
        if user is None or not user.is_active:
            raise TokenNotFoundError
        return token, user

    async def consume_action_token(
        self, raw: str, purposes: tuple[str, ...] = _ACTION_PURPOSES
    ) -> tuple[AuthToken, User]:
        token, user = await self.peek_action_token(raw, purposes)
        # Single-use under races: if a concurrent redemption already consumed it,
        # treat this call as if the token were never valid.
        if not await self._tokens.consume(token):
            raise TokenNotFoundError
        return token, user

    # -- entra login codes ---------------------------------------------------

    async def issue_login_code(self, user: User) -> str:
        """Single-use code bridging the Entra callback redirect to the SPA's
        redeem POST (same hashing/storage as invite/reset, 60-second TTL)."""
        raw = new_opaque_token()
        expires_at = datetime.now(UTC) + timedelta(seconds=_LOGIN_CODE_TTL_SECONDS)
        await self._tokens.create(user.id, hash_token(raw), "entra_login", expires_at)
        return raw

    async def consume_login_code(self, raw: str) -> tuple[AuthToken, User]:
        return await self.consume_action_token(raw, purposes=("entra_login",))

    async def revoke_all_for_user(self, user_id: uuid.UUID) -> None:
        """After set-password: delete the user's other outstanding action tokens
        and revoke every refresh session."""
        await self._tokens.delete_unconsumed(user_id)
        await self._sessions.revoke_all_for_user(user_id)

    # -- maintenance --------------------------------------------------------

    async def purge_expired(self) -> tuple[int, int]:
        """Delete expired action tokens and expired/revoked sessions (fixes DB2).

        Returns (tokens_deleted, sessions_deleted); called by the daily
        lifespan cleanup task in main.py.
        """
        return await self._tokens.delete_expired(), await self._sessions.delete_dead()
