from __future__ import annotations

from pydantic import BaseModel, ConfigDict, SecretStr

__all__ = ["EntraSettings"]


class EntraSettings(BaseModel):
    """Entra ID (Azure AD) OIDC settings; env prefix `ENTRA__` (see Settings).

    All three fields are required: setting any `ENTRA__*` variable with the
    others missing must fail startup loudly, never half-enable the feature.
    Endpoint URLs are stable Microsoft templates, so no OIDC discovery fetch.
    """

    model_config = ConfigDict(frozen=True)

    tenant_id: str
    client_id: str
    client_secret: SecretStr

    @property
    def authorize_url(self) -> str:
        return f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/authorize"

    @property
    def token_url(self) -> str:
        return f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/token"

    @property
    def jwks_url(self) -> str:
        return f"https://login.microsoftonline.com/{self.tenant_id}/discovery/v2.0/keys"

    @property
    def issuer(self) -> str:
        return f"https://login.microsoftonline.com/{self.tenant_id}/v2.0"
