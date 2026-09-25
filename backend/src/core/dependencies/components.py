"""Hard-gate guard for hub components (assessment/learning/interview): a
project's hidden/locked flags used to be a display-only hint for JourneyHome —
any authenticated user could still call the underlying endpoints directly.
This rejects instead, reusing OrgService.resolve_components (the same
resolution JourneyHome already renders from) as the source of truth."""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated

from fastapi import Depends

from src.core.dependencies.auth import get_current_user
from src.core.dependencies.chat import ChatKind
from src.core.dependencies.domain import get_org_service
from src.db.models import User
from src.services.exceptions import ComponentLockedError
from src.services.org_service import OrgService

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

__all__ = ["require_chat_kind_unlocked", "require_component_unlocked"]

# Chat kinds that are the conversational half of a gated component. Only the
# interview: its turns stream through POST /api/chat/interview and its history
# through GET /api/chat/conversations?kind=interview. The other kinds are AI
# helpers gated by require_ai_surface alone and stay independent of the tiles.
_CHAT_KIND_COMPONENT: dict[str, str] = {"interview": "interview"}


async def _ensure_unlocked(org_service: OrgService, user: User, component: str) -> None:
    resolved = await org_service.resolve_components(user.project_id)
    state = resolved[component]
    if state["hidden"] or state["locked"]:
        raise ComponentLockedError(component)


def require_component_unlocked(component: str) -> Callable[[User, OrgService], Awaitable[None]]:
    """Router-level dependency factory:
    `dependencies=[Depends(require_component_unlocked("learning"))]`. A
    project-level gate, not a role check — admin and user+ are not exempt
    (see docs/superpowers/specs/2026-07-22-user-plus-role-design.md)."""

    async def _check(
        user: Annotated[User, Depends(get_current_user)],
        org_service: Annotated[OrgService, Depends(get_org_service)],
    ) -> None:
        await _ensure_unlocked(org_service, user, component)

    return _check


async def require_chat_kind_unlocked(
    kind: ChatKind,
    user: Annotated[User, Depends(get_current_user)],
    org_service: Annotated[OrgService, Depends(get_org_service)],
) -> None:
    """Chat-router dependency: `kind` binds to the `{kind}` path segment or the
    `?kind=` query param, whichever the route has (same as require_ai_surface).
    Applies the component gate only to kinds in _CHAT_KIND_COMPONENT."""
    component = _CHAT_KIND_COMPONENT.get(kind)
    if component is not None:
        await _ensure_unlocked(org_service, user, component)
