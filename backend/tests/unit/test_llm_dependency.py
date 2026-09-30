from __future__ import annotations

from unittest.mock import MagicMock

from pydantic import SecretStr

from src.core.configs.auth import AuthSettings
from src.core.configs.llm import LlmSettings
from src.core.configs.settings import Settings
from src.core.dependencies.chat import get_chat_service
from src.core.dependencies.llm import get_llm_service
from src.services.llm_service import AnthropicLlmClient


def _settings(llm: LlmSettings | None) -> Settings:
    return Settings(
        auth=AuthSettings(jwt_secret=SecretStr("x" * 32)), email=None, storage=None, llm=llm
    )


def test_returns_none_when_unconfigured() -> None:
    assert get_llm_service(_settings(None)) is None


def test_returns_client_when_configured() -> None:
    settings = _settings(LlmSettings(model="claude-haiku-4-5", api_key=SecretStr("sk-test")))
    service = get_llm_service(settings)
    assert isinstance(service, AnthropicLlmClient)


def test_chat_service_gets_the_interview_hard_stop_setting() -> None:
    llm_settings = LlmSettings(
        model="claude-haiku-4-5",
        api_key=SecretStr("sk-test"),
        interview_hard_stop=True,
    )
    settings = _settings(llm_settings)
    service = get_chat_service(MagicMock(), MagicMock(), get_llm_service(settings), settings)
    assert service is not None
    assert service.interview_hard_stop is True
