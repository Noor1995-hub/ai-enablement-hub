from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from src.core.dependencies.auth import get_current_user
from src.core.dependencies.domain import (
    get_learning_service,
    get_org_service,
    get_survey_service,
)
from src.db.models import User
from src.schemas.me import ComponentState, JourneyResponse, UserProfileResponse
from src.services.learning_service import LearningService
from src.services.org_service import OrgService
from src.services.survey_service import SurveyService

__all__ = ["router"]

router = APIRouter(prefix="/api/me", tags=["me"])

CurrentUserDep = Annotated[User, Depends(get_current_user)]


@router.get("", response_model=UserProfileResponse)
async def get_profile(user: CurrentUserDep) -> User:
    return user


@router.get("/journey", response_model=JourneyResponse)
async def get_journey(
    user: CurrentUserDep,
    org_service: Annotated[OrgService, Depends(get_org_service)],
    survey_service: Annotated[SurveyService, Depends(get_survey_service)],
    learning_service: Annotated[LearningService, Depends(get_learning_service)],
) -> JourneyResponse:
    """JourneyHome's legacy queries in one call; the DEFAULT_HIDDEN/LOCKED
    fallback now lives server-side (kills the old D4 duplication)."""
    components = await org_service.resolve_components(user.project_id)
    survey_status = await survey_service.survey_status(user.id)
    learning_status = await learning_service.learning_status(user.id)
    return JourneyResponse(
        components={comp: ComponentState(**state) for comp, state in components.items()},
        survey_status=survey_status,
        learning_status=learning_status,
    )
