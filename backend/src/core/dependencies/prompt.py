"""DI provider for PromptService (read-only admin System Prompts page)."""

from __future__ import annotations

from src.services.prompt_service import PromptService

__all__ = ["get_prompt_service"]


def get_prompt_service() -> PromptService:
    return PromptService()
