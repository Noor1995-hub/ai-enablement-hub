from __future__ import annotations

import pytest
from pydantic import SecretStr

from src.core.configs.llm import LlmSettings
from src.core.configs.settings import Settings


def test_llm_settings_holds_secret_key() -> None:
    settings = LlmSettings(model="claude-haiku-4-5", api_key=SecretStr("sk-test"))
    assert settings.model == "claude-haiku-4-5"
    assert settings.api_key.get_secret_value() == "sk-test"


def test_stale_llm_provider_env_var_is_ignored(monkeypatch: pytest.MonkeyPatch) -> None:
    """Production may still set LLM__PROVIDER; it must not crash boot."""
    monkeypatch.setenv("AUTH__JWT_SECRET", "x" * 32)
    monkeypatch.setenv("LLM__PROVIDER", "anything-at-all")
    monkeypatch.setenv("LLM__MODEL", "claude-haiku-4-5")
    monkeypatch.setenv("LLM__API_KEY", "sk-test")
    settings = Settings(_env_file=None)
    assert settings.llm is not None
    assert settings.llm.model == "claude-haiku-4-5"
    assert not hasattr(settings.llm, "provider")


def test_interview_hard_stop_is_off_by_default() -> None:
    # #96: the stop at the interviewer's first question ships dark; production turns it on.
    settings = LlmSettings(model="claude-haiku-4-5", api_key=SecretStr("sk-test"))
    assert settings.interview_hard_stop is False
