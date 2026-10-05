"""DI provider for the project data export (#92).

Its own module because it needs the conversation/message repositories from
chat.py, and chat.py already imports domain.py. All parameter annotations are
runtime imports on purpose (see database.py)."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from src.core.dependencies.auth import get_auth_session_repository
from src.core.dependencies.chat import get_conversation_repository, get_message_repository
from src.core.dependencies.domain import (
    get_assignment_repository,
    get_content_repository,
    get_org_repository,
    get_progress_repository,
    get_project_admin_repository,
    get_survey_repository,
)
from src.core.dependencies.user import get_user_repository
from src.repositories.assignment_repository import AssignmentRepository
from src.repositories.auth_session_repository import AuthSessionRepository
from src.repositories.content_repository import ContentRepository
from src.repositories.conversation_repository import ConversationRepository
from src.repositories.message_repository import MessageRepository
from src.repositories.org_repository import OrgRepository
from src.repositories.progress_repository import ProgressRepository
from src.repositories.project_admin_repository import ProjectAdminRepository
from src.repositories.survey_repository import SurveyRepository
from src.repositories.user_repository import UserRepository
from src.services.project_export_service import ProjectExportService

__all__ = ["get_project_export_service"]


def get_project_export_service(
    users: Annotated[UserRepository, Depends(get_user_repository)],
    org: Annotated[OrgRepository, Depends(get_org_repository)],
    project_admins: Annotated[ProjectAdminRepository, Depends(get_project_admin_repository)],
    sessions: Annotated[AuthSessionRepository, Depends(get_auth_session_repository)],
    surveys: Annotated[SurveyRepository, Depends(get_survey_repository)],
    assignments: Annotated[AssignmentRepository, Depends(get_assignment_repository)],
    content: Annotated[ContentRepository, Depends(get_content_repository)],
    progress: Annotated[ProgressRepository, Depends(get_progress_repository)],
    conversations: Annotated[ConversationRepository, Depends(get_conversation_repository)],
    messages: Annotated[MessageRepository, Depends(get_message_repository)],
) -> ProjectExportService:
    return ProjectExportService(
        users,
        org,
        project_admins,
        sessions,
        surveys,
        assignments,
        content,
        progress,
        conversations,
        messages,
    )
