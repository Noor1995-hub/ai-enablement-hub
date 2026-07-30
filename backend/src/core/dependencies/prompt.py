"""DI provider for PromptService (admin System-Prompts editor).

All parameter annotations are runtime imports on purpose: FastAPI evaluates
the deferred annotations against module globals, and an unresolvable name
silently degrades the parameter to a required query param (see database.py).
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.dependencies.database import get_session
from src.repositories.prompt_repository import PromptRepository
from src.services.prompt_service import PromptService

__all__ = ["get_prompt_service"]


def get_prompt_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> PromptService:
    return PromptService(PromptRepository(session))
