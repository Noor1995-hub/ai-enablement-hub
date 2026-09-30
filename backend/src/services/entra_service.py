from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Protocol
from urllib.parse import urlencode

import httpx
import jwt
from starlette.concurrency import run_in_threadpool

from src.services.exceptions import EntraExchangeError, EntraUserNotFoundError

if TYPE_CHECKING:
    from src.core.configs.entra import EntraSettings
    from src.db.models import User
    from src.repositories.base import AbstractUserRepository

__all__ = ["EntraService", "SigningKeyProvider"]

logger = logging.getLogger(__name__)

_EXCHANGE_TIMEOUT_SECONDS = 10.0
# Absorbs clock skew between this container and Microsoft's token service.
_LEEWAY_SECONDS = 60


class SigningKeyProvider(Protocol):
    """The one PyJWKClient method the service needs; tests stub it with the
    test keypair's public key."""

    def get_signing_key_from_jwt(self, token: str) -> Any: ...


class EntraService:
    """Server-side Entra ID OIDC: authorize-URL construction, confidential-client
    code exchange, id_token validation, and invite-gated user resolution.

    Sign-in never provisions a user — an admin-created row must already exist
    (matched by linked oid, or once by email). Identity claim is `oid` (the
    immutable tenant-wide object id `users.external_id` was reserved for),
    never `sub` (pairwise per app registration).
    """

    def __init__(
        self,
        entra: EntraSettings,
        users: AbstractUserRepository,
        jwks: SigningKeyProvider,
        http: httpx.AsyncClient | None = None,
    ) -> None:
        self._entra = entra
        self._users = users
        self._jwks = jwks
        self._http = http

    def build_authorize_url(
        self, *, state: str, nonce: str, code_challenge: str, redirect_uri: str
    ) -> str:
        params = {
            "client_id": self._entra.client_id,
            "response_type": "code",
            "redirect_uri": redirect_uri,
            "response_mode": "query",
            "scope": "openid profile email",
            "state": state,
            "nonce": nonce,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
            "prompt": "select_account",
        }
        return f"{self._entra.authorize_url}?{urlencode(params)}"

    async def exchange_code(self, *, code: str, code_verifier: str, redirect_uri: str) -> str:
        """Redeem the authorization code at the token endpoint; returns the raw
        id_token. Raises EntraExchangeError on any failure."""
        data = {
            "grant_type": "authorization_code",
            "client_id": self._entra.client_id,
            "client_secret": self._entra.client_secret.get_secret_value(),
            "code": code,
            "redirect_uri": redirect_uri,
            "code_verifier": code_verifier,
        }
        try:
            response = await self._post_token(data)
        except httpx.HTTPError as exc:
            raise EntraExchangeError("token endpoint unreachable") from exc
        if response.status_code != 200:
            raise EntraExchangeError(f"token endpoint returned {response.status_code}")
        try:
            id_token = response.json().get("id_token")
        except ValueError as exc:
            raise EntraExchangeError("token endpoint returned non-JSON") from exc
        if not isinstance(id_token, str) or not id_token:
            raise EntraExchangeError("token response carries no id_token")
        return id_token

    async def validate_id_token(self, id_token: str, *, nonce: str) -> dict[str, Any]:
        """RS256 signature via tenant JWKS + iss/aud/exp/nonce checks; returns
        the claims. Raises EntraExchangeError on any failure."""
        try:
            # PyJWKClient is sync urllib — never run it on the event loop.
            signing_key = await run_in_threadpool(self._jwks.get_signing_key_from_jwt, id_token)
        except jwt.PyJWTError as exc:
            raise EntraExchangeError("could not resolve id_token signing key") from exc
        try:
            claims: dict[str, Any] = jwt.decode(
                id_token,
                getattr(signing_key, "key", signing_key),
                algorithms=["RS256"],
                audience=self._entra.client_id,
                issuer=self._entra.issuer,
                leeway=_LEEWAY_SECONDS,
                options={"require": ["exp", "iat", "sub"]},
            )
        except jwt.InvalidTokenError as exc:
            raise EntraExchangeError("id_token validation failed") from exc
        if claims.get("nonce") != nonce:
            raise EntraExchangeError("id_token nonce mismatch")
        if not claims.get("oid"):
            raise EntraExchangeError("id_token carries no oid claim")
        return claims

    async def resolve_user(self, claims: dict[str, Any]) -> User:
        """Invite-gated matching: linked oid first, then one-time email linking.
        Raises EntraUserNotFoundError; never creates a row."""
        oid: str = claims["oid"]
        email = self._email_claim(claims)
        user = await self._users.get_by_external_id(oid)
        if user is not None:
            if not user.is_active:
                logger.warning("entra sign-in rejected: linked user inactive (oid=%s)", oid)
                raise EntraUserNotFoundError
            if email and user.email != email:
                # Informational only — oid wins, an Entra email change never locks out.
                # Neither address is logged (review 9.12): the oid is enough to look
                # both up.
                logger.info("entra email differs from the hub record (oid=%s)", oid)
            return user
        user = await self._users.get_by_email(email) if email else None
        if user is None or not user.is_active:
            # Domain only (review 9.12): separates "wrong tenant" from "not invited"
            # without identifying anyone. partition, not rpartition, so a claim with
            # no "@" logs "unknown" rather than the whole value.
            logger.warning(
                "entra sign-in rejected: no invited user (oid=%s email_domain=%s)",
                oid,
                email.partition("@")[2] or "unknown",
            )
            raise EntraUserNotFoundError
        if user.external_id is not None:
            # Same email, different oid — the linked-oid lookup above already
            # missed, so this is a conflicting account. Never relink silently.
            logger.error(
                "entra sign-in rejected: this hub user is already linked to another oid "
                "(hub_user=%s linked_oid=%s incoming_oid=%s)",
                user.id,
                user.external_id,
                oid,
            )
            raise EntraUserNotFoundError
        await self._users.link_external_id(user, oid)
        logger.info("entra first-login link: user=%s ← oid=%s", user.id, oid)
        return user

    @staticmethod
    def _email_claim(claims: dict[str, Any]) -> str:
        """The `email` claim first (Entra `mail` attribute — matches hub emails
        like firstname.lastname@delaware.pro), falling back to
        `preferred_username` (the UPN, e.g. danneelm@delawareconsulting.com)."""
        raw = claims.get("email") or claims.get("preferred_username") or ""
        return raw.strip().lower()

    async def _post_token(self, data: dict[str, str]) -> httpx.Response:
        if self._http is not None:
            return await self._http.post(self._entra.token_url, data=data)
        async with httpx.AsyncClient(timeout=_EXCHANGE_TIMEOUT_SECONDS) as client:
            return await client.post(self._entra.token_url, data=data)
