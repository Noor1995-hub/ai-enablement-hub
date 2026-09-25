from __future__ import annotations

from pydantic import BaseModel, ConfigDict, SecretStr, field_validator, model_validator

__all__ = ["StorageSettings"]

# A read-time SAS is quantized to midnight UTC (see SAS generation, added in a
# later task); a fetch requested just before midnight must still resolve to a
# token that stays valid through a full day. 24h alone can expire seconds
# after issuance, so the floor is one hour above a full day.
_MIN_SAS_TTL_HOURS = 25
_DEFAULT_ENDPOINT_SUFFIX = "core.windows.net"


class StorageSettings(BaseModel):
    """Azure Blob Storage settings for lesson media; env prefix `STORAGE__`
    (see Settings).

    `connection_string` is parsed once, eagerly, into `account_name`,
    `account_key`, and `blob_endpoint` at construction, so a malformed value
    fails loudly at app startup instead of on first upload/SAS generation.
    """

    model_config = ConfigDict(frozen=True)

    connection_string: SecretStr
    container: str = "lesson-media"
    # SAS windows start at midnight UTC and run for this many hours, so a
    # stamped url works with no authentication until it expires: its lifetime
    # is exactly the window a leaked url stays usable. 26 is one hour above
    # _MIN_SAS_TTL_HOURS (25), not 48 — the cost is that a url minted just
    # before midnight UTC has only ~2h of validity left instead of ~24h (a
    # lesson tab left open across ~02:00 UTC may need a reload to keep
    # loading/seeking media); re-fetch cadence is unchanged either way.
    sas_ttl_hours: int = 26

    # Derived from connection_string by _parse_connection_string below; these
    # defaults are placeholders only, always overwritten at construction.
    # account_key is SecretStr so it never prints in repr()/logs (architecture
    # rule: secrets stay secret); SAS generation reads .get_secret_value().
    account_name: str = ""
    account_key: SecretStr = SecretStr("")
    blob_endpoint: str = ""

    @field_validator("sas_ttl_hours")
    @classmethod
    def _ttl_covers_a_full_day(cls, value: int) -> int:
        if value < _MIN_SAS_TTL_HOURS:
            msg = (
                f"STORAGE__SAS_TTL_HOURS must be >= {_MIN_SAS_TTL_HOURS}: a SAS window "
                "quantized to midnight UTC must still be valid for a full day's fetch "
                "even when requested just before midnight"
            )
            raise ValueError(msg)
        return value

    @model_validator(mode="after")
    def _parse_connection_string(self) -> StorageSettings:
        parts: dict[str, str] = {}
        for pair in self.connection_string.get_secret_value().split(";"):
            if not pair:
                continue
            key, _sep, value = pair.partition("=")
            parts[key.strip()] = value.strip()

        account_name = parts.get("AccountName")
        account_key = parts.get("AccountKey")
        if not account_name or not account_key:
            missing = [
                name
                for name, value in (("AccountName", account_name), ("AccountKey", account_key))
                if not value
            ]
            msg = f"STORAGE__CONNECTION_STRING is missing {' and '.join(missing)}"
            raise ValueError(msg)

        endpoint = parts.get("BlobEndpoint")
        if not endpoint:
            suffix = parts.get("EndpointSuffix") or _DEFAULT_ENDPOINT_SUFFIX
            endpoint = f"https://{account_name}.blob.{suffix}"

        # Fields are frozen; this is the one place they're ever written, right
        # after validation, so downstream code only ever sees the parsed form.
        object.__setattr__(self, "account_name", account_name)
        object.__setattr__(self, "account_key", SecretStr(account_key))
        object.__setattr__(self, "blob_endpoint", endpoint.rstrip("/"))
        return self
