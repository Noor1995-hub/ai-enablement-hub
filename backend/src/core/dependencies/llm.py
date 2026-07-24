from __future__ import annotations

from functools import lru_cache
from typing import Annotated

from anthropic import AsyncAnthropic
from fastapi import Depends

from src.core.configs.settings import Settings
from src.core.dependencies.settings import get_settings
from src.services.llm_service import AnthropicLlmClient

__all__ = ["get_llm_service"]


@lru_cache
def _anthropic_client(api_key: str) -> AsyncAnthropic:
    """Process-lifetime client, mirrors _email_client's @lru_cache pattern."""
    return AsyncAnthropic(api_key=api_key)


def get_llm_service(
    settings: Annotated[Settings, Depends(get_settings)],
) -> AnthropicLlmClient | None:
    """None when LLM__* is unconfigured — the chat router 404s in that case
    (mirrors EntraService's all-or-nothing pattern, not EmailService's, because
    chat has no meaning without a model)."""
    if settings.llm is None:
        return None
    return AnthropicLlmClient(
        _anthropic_client(settings.llm.api_key.get_secret_value()), model=settings.llm.model
    )
