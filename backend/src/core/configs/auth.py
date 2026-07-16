from __future__ import annotations

from pydantic import BaseModel, ConfigDict, SecretStr, field_validator

__all__ = ["AuthSettings"]

# HS256 access tokens are only as strong as the secret; a short one is
# offline-brute-forceable into token forgery. Require real entropy.
_MIN_JWT_SECRET_LENGTH = 32


class AuthSettings(BaseModel):
    """Auth/JWT settings; env prefix `AUTH__` (see Settings).

    `jwt_secret` has no default on purpose: the app must refuse to start
    without one rather than sign tokens with a guessable value.
    """

    model_config = ConfigDict(frozen=True)

    jwt_secret: SecretStr
    jwt_issuer: str = "ai-hub"
    jwt_audience: str = "ai-hub-api"
    access_token_minutes: int = 30
    refresh_token_days: int = 14
    invite_ttl_days: int = 14
    reset_ttl_days: int = 14

    @field_validator("jwt_secret")
    @classmethod
    def _secret_has_entropy(cls, value: SecretStr) -> SecretStr:
        if len(value.get_secret_value()) < _MIN_JWT_SECRET_LENGTH:
            msg = f"AUTH__JWT_SECRET must be at least {_MIN_JWT_SECRET_LENGTH} characters"
            raise ValueError(msg)
        return value
