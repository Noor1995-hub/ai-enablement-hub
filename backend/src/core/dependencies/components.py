"""Hard-gate guard for hub components (assessment/learning/interview): a
project's hidden/locked flags used to be a display-only hint for JourneyHome —
any authenticated user could still call the underlying endpoints directly.
This rejects instead, reusing OrgService.resolve_components (the same
resolution JourneyHome already renders from) as the source of truth."""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated

from fastapi import Depends

from src.core.dependencies.auth import get_current_user
from src.core.dependencies.domain import get_org_service
from src.db.models import User
from src.services.exceptions import ComponentLockedError
from src.services.org_service import OrgService

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

__all__ = ["require_component_unlocked"]


def require_component_unlocked(component: str) -> Callable[[User, OrgService], Awaitable[None]]:
    """Router-level dependency factory:
    `dependencies=[Depends(require_component_unlocked("learning"))]`. A
    project-level gate, not a role check — admin and user+ are not exempt
    (see docs/superpowers/specs/2026-07-22-user-plus-role-design.md)."""

    async def _check(
        user: Annotated[User, Depends(get_current_user)],
        org_service: Annotated[OrgService, Depends(get_org_service)],
    ) -> None:
        resolved = await org_service.resolve_components(user.project_id)
        state = resolved[component]
        if state["hidden"] or state["locked"]:
            raise ComponentLockedError(component)

    return _check
