from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from src.core.dependencies.auth import require_admin
from src.core.dependencies.prompt import get_prompt_service
from src.schemas.prompt import PromptDetail, PromptListResponse
from src.services.prompt_service import PromptService

__all__ = ["router"]

router = APIRouter(
    prefix="/api/admin/prompts", tags=["admin-prompts"], dependencies=[Depends(require_admin)]
)

PromptServiceDep = Annotated[PromptService, Depends(get_prompt_service)]


@router.get("", response_model=PromptListResponse)
async def list_prompts(service: PromptServiceDep) -> PromptListResponse:
    """Every known prompt kind with the repo path of its file (the only source of truth)."""
    return PromptListResponse(prompts=service.list_all())


@router.get("/{kind}", response_model=PromptDetail)
async def get_prompt(kind: str, service: PromptServiceDep) -> PromptDetail:
    """Unknown kind -> global 404 handler (NotFoundError). There is no write route:
    prompts change by pull request (2026-09-23)."""
    return service.get(kind)
