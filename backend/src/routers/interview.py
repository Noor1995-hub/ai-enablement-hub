from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from src.core.dependencies.auth import get_current_user, require_admin
from src.core.dependencies.components import require_component_unlocked
from src.core.dependencies.domain import get_admin_user_service
from src.core.dependencies.interview import (
    get_interview_service,
    require_completed_assessment,
    require_interview_surface,
)
from src.core.dependencies.ratelimit import get_rate_limiter
from src.core.ratelimit import RateLimiter
from src.db.models import User
from src.schemas.interview import (
    AdminInterviewResponse,
    InterviewOpenerResponse,
    InterviewStateResponse,
    PlaybookResponse,
)
from src.services.admin_user_service import AdminUserService
from src.services.interview_service import InterviewService

__all__ = ["admin_router", "router"]

# TWO router-level gates, deliberately: the component lock is the project-level
# "is this part of the hub switched on at all" flag (same as
# survey.py/learning.py), while require_interview_surface is the per-project
# AI-spend toggle. Interview is one of the three gated components
# (core/constants.py COMPONENTS), so an admin who hides or locks the Interview
# tile must also close the API. The chat router applies the same component gate
# to kind=interview (require_chat_kind_unlocked).
# A THIRD gate sits on the two write routes only (opener, playbook):
# require_completed_assessment (spec 2026-09-26 A.3.5) — admins are exempt so
# they can test the flow, but a learner must have a COMPLETED assessment before
# starting the interview, since it is briefed from that assessment. It is
# deliberately NOT on GET /me: a learner who already has a playbook (e.g. built
# before this gate shipped, or by an admin on their behalf) must still be able
# to read it.
# admin_router is deliberately NOT gated: reading a learner's interview must not
# depend on the admin's own project flags.
router = APIRouter(
    prefix="/api/interview",
    tags=["interview"],
    dependencies=[
        Depends(require_component_unlocked("interview")),
        Depends(require_interview_surface),
    ],
)
admin_router = APIRouter(
    prefix="/api/admin", tags=["admin:interview"], dependencies=[Depends(require_admin)]
)

CurrentUserDep = Annotated[User, Depends(get_current_user)]
InterviewServiceDep = Annotated[InterviewService | None, Depends(get_interview_service)]
AdminUserServiceDep = Annotated[AdminUserService, Depends(get_admin_user_service)]
RateLimiterDep = Annotated[RateLimiter, Depends(get_rate_limiter)]

_NOT_CONFIGURED = HTTPException(
    status_code=status.HTTP_404_NOT_FOUND, detail="Interview is not configured"
)


@router.get("/me", response_model=InterviewStateResponse)
async def get_my_interview_state(
    current_user: CurrentUserDep,
    interview_service: InterviewServiceDep,
) -> InterviewStateResponse:
    if interview_service is None:
        raise _NOT_CONFIGURED
    return await interview_service.get_state(user=current_user)


@router.post(
    "/opener",
    response_model=InterviewOpenerResponse,
    dependencies=[Depends(require_completed_assessment)],
)
async def open_my_interview(
    current_user: CurrentUserDep,
    interview_service: InterviewServiceDep,
    limiter: RateLimiterDep,
) -> InterviewOpenerResponse:
    if limiter.is_limited(f"interview-opener:{current_user.id}", max_calls=10, window_seconds=600):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many interview starts - please wait a few minutes.",
            headers={"Retry-After": "600"},
        )
    if interview_service is None:
        raise _NOT_CONFIGURED
    return await interview_service.open_interview(user=current_user)


@router.post(
    "/playbook",
    response_model=PlaybookResponse,
    dependencies=[Depends(require_completed_assessment)],
)
async def create_my_playbook(
    current_user: CurrentUserDep,
    interview_service: InterviewServiceDep,
    limiter: RateLimiterDep,
) -> PlaybookResponse:
    if limiter.is_limited(f"interview-playbook:{current_user.id}", max_calls=5, window_seconds=600):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many playbook builds — please wait a few minutes.",
            headers={"Retry-After": "600"},
        )
    if interview_service is None:
        raise _NOT_CONFIGURED
    shared = await interview_service.build_playbook(user=current_user)
    return PlaybookResponse(playbook=shared)


@admin_router.get("/interviews/{user_id}", response_model=AdminInterviewResponse)
async def get_admin_interview(
    user_id: uuid.UUID,
    admin_user_service: AdminUserServiceDep,
    interview_service: InterviewServiceDep,
) -> AdminInterviewResponse:
    await admin_user_service.get_user(user_id)  # 404 for unknown users
    if interview_service is None:
        raise _NOT_CONFIGURED
    return await interview_service.get_admin_view(user_id=user_id)


@admin_router.delete("/interviews/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_admin_interview(
    user_id: uuid.UUID,
    admin_user_service: AdminUserServiceDep,
    interview_service: InterviewServiceDep,
) -> None:
    await admin_user_service.get_user(user_id)  # 404 for unknown users
    if interview_service is None:
        raise _NOT_CONFIGURED
    await interview_service.reset(user_id=user_id)
