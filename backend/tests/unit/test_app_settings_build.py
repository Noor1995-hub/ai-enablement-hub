"""APP__BUILD_SHA / APP__BUILD_TIME are stamped by deploy workflow; defaults mark a dev build."""

from __future__ import annotations

import pytest
from pydantic import SecretStr

from src.core.configs.app import AppSettings
from src.core.configs.auth import AuthSettings
from src.core.configs.settings import Settings

pytestmark = pytest.mark.unit


def test_defaults_mark_a_dev_build() -> None:
    app = AppSettings()
    assert app.build_sha == "dev"
    assert app.build_time == ""


def test_env_vars_populate_build_identity(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP__BUILD_SHA", "0123456789abcdef0123456789abcdef01234567")
    monkeypatch.setenv("APP__BUILD_TIME", "2026-09-22T12:00:00Z")
    settings = Settings(auth=AuthSettings(jwt_secret=SecretStr("x" * 40)), _env_file=None)
    assert settings.app.build_sha == "0123456789abcdef0123456789abcdef01234567"
    assert settings.app.build_time == "2026-09-22T12:00:00Z"
