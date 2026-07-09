"""DI providers for the Batch 3 domain repositories and services.

All parameter annotations are runtime imports on purpose: FastAPI evaluates
the deferred annotations against module globals, and an unresolvable name
silently degrades the parameter to a required query param (see database.py).
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.dependencies.database import get_session
from src.core.dependencies.user import get_user_repository
from src.repositories.assignment_repository import AssignmentRepository
from src.repositories.content_repository import ContentRepository
from src.repositories.org_repository import OrgRepository
from src.repositories.progress_repository import ProgressRepository
from src.repositories.survey_repository import SurveyRepository
from src.repositories.user_repository import UserRepository
from src.services.admin_user_service import AdminUserService
from src.services.content_service import ContentService
from src.services.learning_service import LearningService
from src.services.maturity_service import MaturityService
from src.services.org_service import OrgService
from src.services.survey_service import SurveyService

__all__ = [
    "get_admin_user_service",
    "get_assignment_repository",
    "get_content_repository",
    "get_content_service",
    "get_learning_service",
    "get_maturity_service",
    "get_org_repository",
    "get_org_service",
    "get_progress_repository",
    "get_survey_repository",
    "get_survey_service",
]


def get_org_repository(session: Annotated[AsyncSession, Depends(get_session)]) -> OrgRepository:
    return OrgRepository(session)


def get_survey_repository(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> SurveyRepository:
    return SurveyRepository(session)


def get_content_repository(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ContentRepository:
    return ContentRepository(session)


def get_assignment_repository(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> AssignmentRepository:
    return AssignmentRepository(session)


def get_progress_repository(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ProgressRepository:
    return ProgressRepository(session)


def get_survey_service(
    surveys: Annotated[SurveyRepository, Depends(get_survey_repository)],
    content: Annotated[ContentRepository, Depends(get_content_repository)],
    assignments: Annotated[AssignmentRepository, Depends(get_assignment_repository)],
) -> SurveyService:
    return SurveyService(surveys, content, assignments)


def get_org_service(org: Annotated[OrgRepository, Depends(get_org_repository)]) -> OrgService:
    return OrgService(org)


def get_learning_service(
    content: Annotated[ContentRepository, Depends(get_content_repository)],
    assignments: Annotated[AssignmentRepository, Depends(get_assignment_repository)],
    progress: Annotated[ProgressRepository, Depends(get_progress_repository)],
) -> LearningService:
    return LearningService(content, assignments, progress)


def get_content_service(
    content: Annotated[ContentRepository, Depends(get_content_repository)],
) -> ContentService:
    return ContentService(content)


def get_maturity_service(
    users: Annotated[UserRepository, Depends(get_user_repository)],
    surveys: Annotated[SurveyRepository, Depends(get_survey_repository)],
    content: Annotated[ContentRepository, Depends(get_content_repository)],
    assignments: Annotated[AssignmentRepository, Depends(get_assignment_repository)],
) -> MaturityService:
    return MaturityService(users, surveys, content, assignments)


def get_admin_user_service(
    users: Annotated[UserRepository, Depends(get_user_repository)],
    org: Annotated[OrgRepository, Depends(get_org_repository)],
    assignments: Annotated[AssignmentRepository, Depends(get_assignment_repository)],
    content: Annotated[ContentRepository, Depends(get_content_repository)],
    surveys: Annotated[SurveyRepository, Depends(get_survey_repository)],
) -> AdminUserService:
    return AdminUserService(users, org, assignments, content, surveys)
