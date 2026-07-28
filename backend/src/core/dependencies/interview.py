"""DI provider for InterviewContextService.

All parameter annotations are runtime imports on purpose: FastAPI evaluates
the deferred annotations against module globals, and an unresolvable name
silently degrades the parameter to a required query param (see database.py).
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from src.core.dependencies.domain import (
    get_learning_service,
    get_maturity_service,
    get_survey_service,
)
from src.services.interview_context import InterviewContextService
from src.services.learning_service import LearningService
from src.services.maturity_service import MaturityService
from src.services.survey_service import SurveyService

__all__ = ["get_interview_context_service"]


def get_interview_context_service(
    surveys: Annotated[SurveyService, Depends(get_survey_service)],
    maturity: Annotated[MaturityService, Depends(get_maturity_service)],
    learning: Annotated[LearningService, Depends(get_learning_service)],
) -> InterviewContextService:
    return InterviewContextService(surveys, maturity, learning)
