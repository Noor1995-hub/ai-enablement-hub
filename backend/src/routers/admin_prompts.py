from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from src.core.dependencies.auth import get_current_user, require_admin
from src.core.dependencies.prompt import get_prompt_service
from src.db.models import User
from src.schemas.prompt import PromptDetail, PromptListResponse, PromptUpdateRequest
from src.services.exceptions import DomainError, NotFoundError
from src.services.prompt_service import PromptService

__all__ = ["router"]

router = APIRouter(
    prefix="/api/admin/prompts", tags=["admin-prompts"], dependencies=[Depends(require_admin)]
)

PromptServiceDep = Annotated[PromptService, Depends(get_prompt_service)]
CurrentUserDep = Annotated[User, Depends(get_current_user)]


@router.get("", response_model=PromptListResponse)
async def list_prompts(service: PromptServiceDep) -> PromptListResponse:
    """All known prompt kinds, each labelled with whether it's the shipped
    file default or an admin-saved DB override."""
    return PromptListResponse(prompts=await service.list_all())


@router.get("/{kind}", response_model=PromptDetail)
async def get_prompt(kind: str, service: PromptServiceDep) -> PromptDetail:
    """Unknown kind -> global 404 handler (NotFoundError)."""
    return await service.get(kind)


@router.put("/{kind}", response_model=PromptDetail)
async def put_prompt(
    kind: str, body: PromptUpdateRequest, service: PromptServiceDep, user: CurrentUserDep
) -> PromptDetail:
    """Unknown kind -> global 404. A save that drops a required token raises
    the base DomainError, which we map to 422 here (not the global 400) since
    this is a validation failure on the submitted content, not a generic
    domain error."""
    try:
        await service.update(kind, body.content, user.id)
    except NotFoundError:
        raise  # propagates to the global 404 handler
    except DomainError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=exc.message
        ) from exc
    return await service.get(kind)


@router.delete("/{kind}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_prompt(kind: str, service: PromptServiceDep) -> None:
    """Drop the DB override so the prompt falls back to the shipped file.
    Unknown kind -> global 404 handler (NotFoundError)."""
    await service.reset(kind)
