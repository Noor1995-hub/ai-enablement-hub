from __future__ import annotations

from pydantic import BaseModel, ConfigDict, SecretStr

__all__ = ["EmailSettings"]


class EmailSettings(BaseModel):
    """Azure Communication Services email settings; env prefix `EMAIL__`
    (see Settings).

    Both fields are required: setting one `EMAIL__*` variable with the other
    missing must fail startup loudly, never half-enable the feature.
    """

    model_config = ConfigDict(frozen=True)

    # ACS connection string ("endpoint=https://...;accesskey=...").
    connection_string: SecretStr
    # A sender username on the linked ACS email domain, e.g.
    # "DoNotReply@<guid>.azurecomm.net".
    sender_address: str
