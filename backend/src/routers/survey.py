from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from src.core.dependencies.auth import get_current_user
from src.core.dependencies.domain import get_survey_service
from src.db.models import SurveyResponse, User
from src.schemas.survey import (
    SurveyCompleteResponse,
    SurveyDraftRequest,
    SurveyResponseOut,
)
from src.services.survey_service import SurveyService

__all__ = ["router"]

router = APIRouter(prefix="/api/survey", tags=["survey"])

CurrentUserDep = Annotated[User, Depends(get_current_user)]
SurveyServiceDep = Annotated[SurveyService, Depends(get_survey_service)]


@router.get("/me", response_model=SurveyResponseOut | None)
async def get_own_survey(
    user: CurrentUserDep, survey_service: SurveyServiceDep
) -> SurveyResponse | None:
    """The caller's survey row (any status) or null — Assessment resume."""
    return await survey_service.get_own(user.id)


@router.put("/me", response_model=SurveyResponseOut)
async def save_draft(
    body: SurveyDraftRequest, user: CurrentUserDep, survey_service: SurveyServiceDep
) -> SurveyResponse:
    """Upsert the caller's draft; only fields present in the request are
    written. 409 once the survey is complete."""
    return await survey_service.save_draft(user.id, body.model_dump(exclude_unset=True))


@router.post("/complete", response_model=SurveyCompleteResponse)
async def complete_survey(
    user: CurrentUserDep, survey_service: SurveyServiceDep
) -> SurveyCompleteResponse:
    """Score the caller's in-progress draft (409 if none, 422 on missing or
    unrecognised answers) and persist all scored fields."""
    row = await survey_service.complete(user.id)
    return SurveyCompleteResponse(
        score_level=row.score_level or "",
        usage_band=row.usage_band,
        mandatory_modules=row.mandatory_modules or [],
    )
