from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from src.core.configs.settings import Settings
from src.core.dependencies.auth import require_admin
from src.core.dependencies.domain import get_admin_user_service, get_survey_service
from src.core.dependencies.ratelimit import get_rate_limiter
from src.core.dependencies.settings import get_settings
from src.core.ratelimit import RateLimiter
from src.schemas.admin_users import (
    AdminLearningResponse,
    AdminSurveyOut,
    AdminUserOut,
    AdminUsersResponse,
    AssignmentRequest,
    InviteRequest,
    LinkResponse,
    RoleUpdateRequest,
    SurveyLevelsResponse,
    UserSurveyResponse,
)
from src.services.admin_user_service import AdminUserService
from src.services.survey_service import SurveyService

__all__ = ["router"]

router = APIRouter(prefix="/api/admin", tags=["admin:users"], dependencies=[Depends(require_admin)])

AdminUserServiceDep = Annotated[AdminUserService, Depends(get_admin_user_service)]
SurveyServiceDep = Annotated[SurveyService, Depends(get_survey_service)]
SettingsDep = Annotated[Settings, Depends(get_settings)]
RateLimiterDep = Annotated[RateLimiter, Depends(get_rate_limiter)]

_RATE_LIMITED = HTTPException(
    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
    detail="Too many attempts — try again in a minute",
    headers={"Retry-After": "60"},
)


def _invite_link(settings: Settings, raw_token: str) -> str:
    return f"{settings.app.url.rstrip('/')}/invite/{raw_token}"


@router.get("/users", response_model=AdminUsersResponse)
async def list_users(
    admin_user_service: AdminUserServiceDep,
    project_id: Annotated[uuid.UUID | None, Query()] = None,
) -> AdminUsersResponse:
    users = await admin_user_service.list_users(project_id)
    return AdminUsersResponse(users=[AdminUserOut.model_validate(user) for user in users])


@router.post("/invites", response_model=LinkResponse, status_code=status.HTTP_201_CREATED)
async def create_invite(
    body: InviteRequest,
    admin_user_service: AdminUserServiceDep,
    settings: SettingsDep,
    limiter: RateLimiterDep,
) -> LinkResponse:
    """Create the user row + single-use invite token; the admin copies the
    returned link manually (no email is sent), as in the old app."""
    if limiter.is_limited(f"invite:{body.email.strip().lower()}"):
        raise _RATE_LIMITED
    _, raw_token = await admin_user_service.invite(
        body.email, body.first_name, body.last_name, body.project_id
    )
    return LinkResponse(link=_invite_link(settings, raw_token))


@router.post("/users/{user_id}/reset-link", response_model=LinkResponse)
async def create_reset_link(
    user_id: uuid.UUID,
    admin_user_service: AdminUserServiceDep,
    settings: SettingsDep,
    limiter: RateLimiterDep,
) -> LinkResponse:
    """Issue a password-reset link; prior unused reset tokens are revoked."""
    user = await admin_user_service.get_user(user_id)
    if limiter.is_limited(f"reset:{user.email}"):
        raise _RATE_LIMITED
    _, raw_token = await admin_user_service.reset_link(user_id)
    return LinkResponse(link=_invite_link(settings, raw_token))


@router.patch("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def update_user_role(
    user_id: uuid.UUID, body: RoleUpdateRequest, admin_user_service: AdminUserServiceDep
) -> None:
    await admin_user_service.set_role(user_id, body.role)


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(user_id: uuid.UUID, admin_user_service: AdminUserServiceDep) -> None:
    """Single DELETE; FK cascades wipe tokens/sessions/survey/progress (fixes
    the legacy two-system atomicity problem B2 by construction)."""
    await admin_user_service.delete_user(user_id)


@router.put("/users/{user_id}/tracks/{track_id}", status_code=status.HTTP_204_NO_CONTENT)
async def set_user_track(
    user_id: uuid.UUID,
    track_id: uuid.UUID,
    body: AssignmentRequest,
    admin_user_service: AdminUserServiceDep,
) -> None:
    await admin_user_service.set_track_assignment(user_id, track_id, body.assigned)


@router.put("/users/{user_id}/modules/{module_id}", status_code=status.HTTP_204_NO_CONTENT)
async def set_user_module(
    user_id: uuid.UUID,
    module_id: uuid.UUID,
    body: AssignmentRequest,
    admin_user_service: AdminUserServiceDep,
) -> None:
    await admin_user_service.set_module_assignment(user_id, module_id, body.assigned)


@router.get("/learning", response_model=AdminLearningResponse)
async def get_learning_overview(admin_user_service: AdminUserServiceDep) -> AdminLearningResponse:
    return AdminLearningResponse(**await admin_user_service.learning_overview())


@router.get("/surveys", response_model=SurveyLevelsResponse)
async def get_survey_levels(
    survey_service: SurveyServiceDep,
    user_ids: Annotated[str | None, Query(description="comma-separated user UUIDs")] = None,
) -> SurveyLevelsResponse:
    if not user_ids:
        return SurveyLevelsResponse(levels={})
    try:
        parsed = [uuid.UUID(item.strip()) for item in user_ids.split(",") if item.strip()]
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="user_ids must be comma-separated UUIDs",
        ) from exc
    return SurveyLevelsResponse(levels=await survey_service.complete_levels(parsed))


@router.get("/surveys/{user_id}", response_model=UserSurveyResponse)
async def get_user_survey(
    user_id: uuid.UUID,
    admin_user_service: AdminUserServiceDep,
    survey_service: SurveyServiceDep,
) -> UserSurveyResponse:
    """The user's completed survey (or null) — admin results panel."""
    await admin_user_service.get_user(user_id)  # 404 for unknown users
    row = await survey_service.complete_survey_for(user_id)
    return UserSurveyResponse(
        survey=AdminSurveyOut.model_validate(row) if row is not None else None
    )
