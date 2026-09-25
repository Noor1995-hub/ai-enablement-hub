"""StorageSettings: connection-string parsing, SAS TTL floor, and defaults."""

from __future__ import annotations

import pytest
from pydantic import SecretStr, ValidationError

from src.core.configs.storage import StorageSettings

_CONN_STRING = (
    "DefaultEndpointsProtocol=https;"
    "AccountName=myaccount;"
    "AccountKey=fakekeybase64==;"
    "EndpointSuffix=core.windows.net"
)


def _settings(conn_string: str, *, sas_ttl_hours: int | None = None) -> StorageSettings:
    # sas_ttl_hours is only forwarded when the caller cares about it, so tests
    # that don't pass it exercise the real StorageSettings default instead of
    # silently pinning one here. Passed directly (not via **kwargs) so its
    # `int` type lines up with the field instead of a dict type broad enough
    # to also (wrongly) cover the str-typed fields.
    if sas_ttl_hours is None:
        return StorageSettings(connection_string=SecretStr(conn_string))
    return StorageSettings(connection_string=SecretStr(conn_string), sas_ttl_hours=sas_ttl_hours)


class TestConnectionStringParsing:
    def test_valid_conn_string_parses_account_fields(self) -> None:
        settings = _settings(_CONN_STRING)
        assert settings.account_name == "myaccount"
        assert settings.account_key.get_secret_value() == "fakekeybase64=="
        assert settings.blob_endpoint == "https://myaccount.blob.core.windows.net"

    def test_account_key_is_not_leaked_by_repr_or_str(self) -> None:
        settings = _settings(_CONN_STRING)
        for dump in (repr(settings), str(settings)):
            assert "fakekeybase64==" not in dump

    def test_explicit_blob_endpoint_wins_and_trailing_slash_is_stripped(self) -> None:
        conn = (
            "AccountName=myaccount;AccountKey=key123;"
            "BlobEndpoint=https://myaccount.blob.custom.example.com/"
        )
        settings = _settings(conn)
        assert settings.blob_endpoint == "https://myaccount.blob.custom.example.com"

    def test_endpoint_suffix_is_respected(self) -> None:
        conn = "AccountName=myaccount;AccountKey=key123;EndpointSuffix=chinacloudapi.cn"
        settings = _settings(conn)
        assert settings.blob_endpoint == "https://myaccount.blob.chinacloudapi.cn"

    def test_default_endpoint_suffix_is_core_windows_net_when_absent(self) -> None:
        conn = "AccountName=myaccount;AccountKey=key123"
        settings = _settings(conn)
        assert settings.blob_endpoint == "https://myaccount.blob.core.windows.net"

    def test_account_key_with_equals_padding_parsed_intact(self) -> None:
        conn = "AccountName=myaccount;AccountKey=abc123+/def==;EndpointSuffix=core.windows.net"
        settings = _settings(conn)
        assert settings.account_key.get_secret_value() == "abc123+/def=="

    def test_missing_account_name_raises_naming_it(self) -> None:
        conn = "AccountKey=key123;EndpointSuffix=core.windows.net"
        with pytest.raises(ValidationError, match="AccountName"):
            _settings(conn)

    def test_missing_account_key_raises_naming_it(self) -> None:
        conn = "AccountName=myaccount;EndpointSuffix=core.windows.net"
        with pytest.raises(ValidationError, match="AccountKey"):
            _settings(conn)


class TestDefaults:
    def test_container_and_sas_ttl_defaults(self) -> None:
        """A stamped SAS url works with no authentication until it expires, so
        its lifetime is exactly the window a shared url stays usable. The
        default sits one hour above the 25h floor (see _MIN_SAS_TTL_HOURS),
        not at 48h: every extra hour is an hour a leaked url keeps working."""
        settings = _settings(_CONN_STRING)
        assert settings.container == "lesson-media"
        assert settings.sas_ttl_hours == 26

    def test_sas_ttl_below_25_hours_is_rejected(self) -> None:
        with pytest.raises(ValidationError, match="25"):
            _settings(_CONN_STRING, sas_ttl_hours=24)

    def test_sas_ttl_of_25_hours_is_accepted(self) -> None:
        settings = _settings(_CONN_STRING, sas_ttl_hours=25)
        assert settings.sas_ttl_hours == 25
