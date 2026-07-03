from __future__ import annotations

from pydantic import BaseModel, ConfigDict, SecretStr

__all__ = ["AuthSettings"]


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
    invite_ttl_days: int = 7
    reset_ttl_days: int = 7
