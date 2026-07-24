from __future__ import annotations

from pydantic import SecretStr

from src.core.configs.llm import LlmSettings


def test_llm_settings_holds_secret_key() -> None:
    settings = LlmSettings(
        provider="anthropic", model="claude-haiku-4-5", api_key=SecretStr("sk-test")
    )
    assert settings.provider == "anthropic"
    assert settings.model == "claude-haiku-4-5"
    assert settings.api_key.get_secret_value() == "sk-test"
