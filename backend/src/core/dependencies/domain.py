"""DI providers for the Batch 3 domain repositories and services.

All parameter annotations are runtime imports on purpose: FastAPI evaluates
the deferred annotations against module globals, and an unresolvable name
silently degrades the parameter to a required query param (see database.py).
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.dependencies.auth import get_auth_session_repository
from src.core.dependencies.database import get_session
from src.core.dependencies.user import get_user_repository
from src.repositories.assignment_repository import AssignmentRepository
from src.repositories.auth_session_repository import AuthSessionRepository
from src.repositories.content_repository import ContentRepository
from src.repositories.email_template_repository import EmailTemplateRepository
from src.repositories.feedback_repository import FeedbackRepository
from src.repositories.org_repository import OrgRepository
from src.repositories.progress_repository import ProgressRepository
from src.repositories.project_admin_repository import ProjectAdminRepository
from src.repositories.survey_repository import SurveyRepository
from src.repositories.unit_of_work import UnitOfWork
from src.repositories.user_repository import UserRepository
from src.services.admin_scope_service import AdminScopeService
from src.services.admin_user_service import AdminUserService
from src.services.content_service import ContentService
from src.services.dashboard_service import DashboardService
from src.services.email_template_service import EmailTemplateService
from src.services.feedback_service import FeedbackService
from src.services.learning_service import LearningService
from src.services.maturity_service import MaturityService
from src.services.org_service import OrgService
from src.services.survey_service import SurveyService

__all__ = [
    "get_admin_scope_service",
    "get_admin_user_service",
    "get_assignment_repository",
    "get_content_repository",
    "get_content_service",
    "get_dashboard_service",
    "get_email_template_repository",
    "get_email_template_service",
    "get_feedback_repository",
    "get_feedback_service",
    "get_learning_service",
    "get_maturity_service",
    "get_org_repository",
    "get_org_service",
    "get_progress_repository",
    "get_project_admin_repository",
    "get_survey_repository",
    "get_survey_service",
    "get_unit_of_work",
]


def get_project_admin_repository(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ProjectAdminRepository:
    return ProjectAdminRepository(session)


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


def get_unit_of_work(session: Annotated[AsyncSession, Depends(get_session)]) -> UnitOfWork:
    """One commit boundary per request, on the same session the repositories use."""
    return UnitOfWork(session)


def get_survey_service(
    surveys: Annotated[SurveyRepository, Depends(get_survey_repository)],
    content: Annotated[ContentRepository, Depends(get_content_repository)],
    assignments: Annotated[AssignmentRepository, Depends(get_assignment_repository)],
    uow: Annotated[UnitOfWork, Depends(get_unit_of_work)],
) -> SurveyService:
    return SurveyService(surveys, content, assignments, uow)


def get_org_service(org: Annotated[OrgRepository, Depends(get_org_repository)]) -> OrgService:
    return OrgService(org)


def get_email_template_repository(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> EmailTemplateRepository:
    return EmailTemplateRepository(session)


def get_email_template_service(
    templates: Annotated[EmailTemplateRepository, Depends(get_email_template_repository)],
    org: Annotated[OrgRepository, Depends(get_org_repository)],
) -> EmailTemplateService:
    return EmailTemplateService(templates, org)


def get_learning_service(
    content: Annotated[ContentRepository, Depends(get_content_repository)],
    assignments: Annotated[AssignmentRepository, Depends(get_assignment_repository)],
    progress: Annotated[ProgressRepository, Depends(get_progress_repository)],
    surveys: Annotated[SurveyRepository, Depends(get_survey_repository)],
) -> LearningService:
    return LearningService(content, assignments, progress, surveys)


def get_feedback_repository(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> FeedbackRepository:
    return FeedbackRepository(session)


def get_feedback_service(
    feedback: Annotated[FeedbackRepository, Depends(get_feedback_repository)],
    content: Annotated[ContentRepository, Depends(get_content_repository)],
) -> FeedbackService:
    return FeedbackService(feedback, content)


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
    sessions: Annotated[AuthSessionRepository, Depends(get_auth_session_repository)],
    progress: Annotated[ProgressRepository, Depends(get_progress_repository)],
    project_admins: Annotated[ProjectAdminRepository, Depends(get_project_admin_repository)],
) -> AdminUserService:
    return AdminUserService(
        users,
        org,
        assignments,
        content,
        surveys,
        sessions,
        progress,
        project_admins=project_admins,
    )


def get_dashboard_service(
    users: Annotated[UserRepository, Depends(get_user_repository)],
    org: Annotated[OrgRepository, Depends(get_org_repository)],
    assignments: Annotated[AssignmentRepository, Depends(get_assignment_repository)],
    content: Annotated[ContentRepository, Depends(get_content_repository)],
    surveys: Annotated[SurveyRepository, Depends(get_survey_repository)],
    sessions: Annotated[AuthSessionRepository, Depends(get_auth_session_repository)],
    progress: Annotated[ProgressRepository, Depends(get_progress_repository)],
    feedback: Annotated[FeedbackRepository, Depends(get_feedback_repository)],
    project_admins: Annotated[ProjectAdminRepository, Depends(get_project_admin_repository)],
) -> DashboardService:
    return DashboardService(
        users,
        org,
        assignments,
        content,
        surveys,
        sessions,
        progress,
        feedback,
        project_admins=project_admins,
    )


def get_admin_scope_service(
    users: Annotated[UserRepository, Depends(get_user_repository)],
    admins: Annotated[ProjectAdminRepository, Depends(get_project_admin_repository)],
) -> AdminScopeService:
    return AdminScopeService(users, admins)


def get_content_service(
    content: Annotated[ContentRepository, Depends(get_content_repository)],
    assignments: Annotated[AssignmentRepository, Depends(get_assignment_repository)],
    users: Annotated[UserRepository, Depends(get_user_repository)],
    project_admins: Annotated[ProjectAdminRepository, Depends(get_project_admin_repository)],
) -> ContentService:
    return ContentService(
        content, assignments=assignments, users=users, project_admins=project_admins
    )
