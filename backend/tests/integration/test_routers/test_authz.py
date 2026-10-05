"""Authorization matrix (design-backend.md §4).

Every protected endpoint × {no token, user token, admin token}, own-row
isolation, and the iron rule: no endpoint outside /admin/* accepts a user
identifier from the request — ownership comes exclusively from the token.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Literal

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from src.core.dependencies.database import get_session
from src.core.dependencies.settings import get_settings
from src.core.dependencies.storage import get_media_service
from src.core.security import create_access_token
from src.db.models import Feedback
from src.main import app
from src.repositories.conversation_repository import ConversationRepository
from src.services.media_service import MediaService
from tests.fixtures.auth import auth_headers, bearer
from tests.fixtures.factories import (
    assign_lesson,
    assign_module,
    assign_track,
    complete_lesson,
    create_company,
    create_lesson,
    create_module,
    create_project,
    create_survey,
    create_track,
    create_user,
    make_project_admin,
    unlock_component,
)
from tests.fixtures.media import TEST_STORAGE, RecordingUploader

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from sqlalchemy.ext.asyncio import AsyncSession

    from src.core.configs.settings import Settings
    from src.db.models import Company, Conversation, Lesson, Module, Project, Track, User


@dataclass
class Seed:
    company: Company
    project: Project
    track: Track
    module: Module
    lesson: Lesson
    admin: User
    user: User
    other: User
    conversation: Conversation
    feedback: Feedback
    other_project: Project
    pa_in: User
    pa_out: User


@pytest_asyncio.fixture
async def seed(db_session: AsyncSession) -> Seed:
    company = await create_company(db_session, "Matrix Co")
    project = await create_project(db_session, company, "Matrix Project")
    await unlock_component(db_session, project, "learning")
    track = await create_track(db_session, "Matrix Track")
    module = await create_module(db_session, track, "Matrix Module")
    lesson = await create_lesson(db_session, module, "Matrix Lesson")
    admin = await create_user(
        db_session,
        email="matrix-admin@example.com",
        role="admin",
        password="hunter2hunter2",
        # Admins now bypass a `locked` component but not a `hidden` one (see
        # test_component_lock.py::test_admin_bypasses_locked_but_not_hidden);
        # the matrix still seats the admin in a project with `learning`
        # unlocked, same as
        # a real onboarded admin account would.
        project_id=project.id,
    )
    user = await create_user(
        db_session,
        email="matrix-user@example.com",
        password="hunter2hunter2",
        company_id=company.id,
        project_id=project.id,
    )
    # The lesson gate is not a role check either: the matrix's blanket "user
    # succeeds everywhere non-admin-only" needs this lesson to actually be on
    # the user's learning path, same as a real onboarded learner. (seed.admin
    # bypasses as a power admin.)
    await assign_lesson(db_session, user, lesson)
    other = await create_user(db_session, email="matrix-other@example.com")
    # For the "chat-conversations-list" _MATRIX entry below — this fixture's
    # `client` has test_settings.llm=None, so get_llm_service -> get_chat_service
    # resolve to None and GET /api/chat/conversations 404s "Chat is not
    # configured" for every caller here, before chat_service.list_conversations
    # is ever reached. The matrix row still validly exercises anonymous->401 and
    # "no accidental admin-only gate" for this endpoint; it does NOT exercise the
    # 200/list-content happy path (that's covered by test_chat.py's
    # TestListAndGetConversations, whose `chat_client` fixture wires a real
    # ChatService). The seeded conversation below is future-proofing for this
    # fixture only — harmless now, but not actually read by this matrix row.
    conversation = await ConversationRepository(db_session).create(user_id=user.id, kind="chatbot")
    feedback = Feedback(user_id=user.id, lesson_id=lesson.id, message="Matrix feedback")
    db_session.add(feedback)
    await db_session.commit()
    await db_session.refresh(feedback)
    # Project admins (spec 2026-10-01): pa_in administers `project` (the seed
    # user's project) but is itself a member of other_project; pa_out
    # administers only other_project.
    other_project = await create_project(db_session, company, "Matrix Other Project")
    pa_in = await create_user(
        db_session,
        email="matrix-pa-in@example.com",
        password="hunter2hunter2",
        company_id=company.id,
        project_id=other_project.id,
    )
    await make_project_admin(db_session, pa_in, project, granted_by=admin)
    pa_out = await create_user(
        db_session,
        email="matrix-pa-out@example.com",
        password="hunter2hunter2",
        company_id=company.id,
        project_id=other_project.id,
    )
    await make_project_admin(db_session, pa_out, other_project, granted_by=admin)
    return Seed(
        company,
        project,
        track,
        module,
        lesson,
        admin,
        user,
        other,
        conversation,
        feedback,
        other_project,
        pa_in,
        pa_out,
    )


# Access kinds (spec 2026-10-01-project-scoped-admin-design.md):
#   "any"         - any signed-in user (learner endpoints)
#   "power"       - power admin only; learners and project admins get 403
#   "scoped"      - project admins of the row's target project succeed (pa_in);
#                   project admins of another project get 404 (pa_out)
#   "scoped_list" - project admins reach it either way; this row only proves
#                   authz passes. What they SEE (filtering, 404 on a named
#                   foreign project) is asserted in test_admin_scope_routes.py
Access = Literal["any", "power", "scoped", "scoped_list"]

# (name, method, declared route, path builder, body builder, access). The
# declared route is what test_every_admin_route_is_in_the_matrix compares
# against the OpenAPI schema. Per-user admin rows target seed.user, a learner
# in seed.project (so pa_in is in scope).
_MATRIX: list[tuple[str, str, str, Any, Any, Access]] = [
    ("me", "GET", "/api/me", lambda s: "/api/me", lambda s: None, "any"),
    ("journey", "GET", "/api/me/journey", lambda s: "/api/me/journey", lambda s: None, "any"),
    ("survey-get", "GET", "/api/survey/me", lambda s: "/api/survey/me", lambda s: None, "any"),
    (
        "survey-put",
        "PUT",
        "/api/survey/me",
        lambda s: "/api/survey/me",
        lambda s: {"job_title": "Dev"},
        "any",
    ),
    (
        "survey-complete",
        "POST",
        "/api/survey/complete",
        lambda s: "/api/survey/complete",
        lambda s: None,
        "any",
    ),
    ("graph", "GET", "/api/learning/graph", lambda s: "/api/learning/graph", lambda s: None, "any"),
    (
        "module-lessons",
        "GET",
        "/api/modules/{module_id}/lessons",
        lambda s: f"/api/modules/{s.module.id}/lessons",
        lambda s: None,
        "any",
    ),
    (
        "lesson",
        "GET",
        "/api/lessons/{lesson_id}",
        lambda s: f"/api/lessons/{s.lesson.id}",
        lambda s: None,
        "any",
    ),
    (
        "feedback",
        "POST",
        "/api/feedback",
        lambda s: "/api/feedback",
        lambda s: {"lesson_id": str(s.lesson.id), "message": "Great lesson"},
        "any",
    ),
    (
        "progress",
        "PUT",
        "/api/lessons/{lesson_id}/progress",
        lambda s: f"/api/lessons/{s.lesson.id}/progress",
        lambda s: {"answers": {}},
        "any",
    ),
    ("tracks", "GET", "/api/tracks", lambda s: "/api/tracks", lambda s: None, "any"),
    (
        "track-modules",
        "GET",
        "/api/tracks/{track_id}/modules",
        lambda s: f"/api/tracks/{s.track.id}/modules",
        lambda s: None,
        "any",
    ),
    # POST /api/chat/{kind} is deliberately NOT here: it has a third gating
    # dimension (the project's AI setting) this flat matrix can't model — see
    # TestSendChatMessage in test_chat.py. GET /api/chat/conversations/{id}
    # (detail) needs a real per-seed-user conversation id too awkward for this
    # table's path-builder shape — see TestListAndGetConversations, also in
    # test_chat.py. Only the plain auth-gated list endpoint fits here.
    (
        "chat-conversations-list",
        "GET",
        "/api/chat/conversations",
        lambda s: "/api/chat/conversations?kind=chatbot",
        lambda s: None,
        "any",
    ),
    # --- org ---
    (
        "companies-get",
        "GET",
        "/api/admin/companies",
        lambda s: "/api/admin/companies",
        lambda s: None,
        "scoped_list",
    ),
    (
        "companies-post",
        "POST",
        "/api/admin/companies",
        lambda s: "/api/admin/companies",
        lambda s: {"name": "Fresh Co"},
        "power",
    ),
    (
        "projects-post",
        "POST",
        "/api/admin/projects",
        lambda s: "/api/admin/projects",
        lambda s: {"name": "P2", "company_id": str(s.company.id)},
        "power",
    ),
    (
        "components-get",
        "GET",
        "/api/admin/projects/{project_id}/components",
        lambda s: f"/api/admin/projects/{s.project.id}/components",
        lambda s: None,
        "scoped",
    ),
    (
        "components-put",
        "PUT",
        "/api/admin/projects/{project_id}/components/{component}",
        lambda s: f"/api/admin/projects/{s.project.id}/components/assessment",
        lambda s: {"hidden": True},
        "scoped",
    ),
    (
        "ai-get",
        "GET",
        "/api/admin/projects/{project_id}/ai",
        lambda s: f"/api/admin/projects/{s.project.id}/ai",
        lambda s: None,
        "scoped",
    ),
    (
        "ai-put",
        "PUT",
        "/api/admin/projects/{project_id}/ai/{kind}",
        lambda s: f"/api/admin/projects/{s.project.id}/ai/chatbot",
        lambda s: {"enabled": False},
        "scoped",
    ),
    # --- email templates ---
    (
        "email-templates-get",
        "GET",
        "/api/admin/projects/{project_id}/email-templates",
        lambda s: f"/api/admin/projects/{s.project.id}/email-templates",
        lambda s: None,
        "scoped",
    ),
    (
        "email-templates-put",
        "PUT",
        "/api/admin/projects/{project_id}/email-templates/{purpose}",
        lambda s: f"/api/admin/projects/{s.project.id}/email-templates/invite",
        lambda s: {"subject": "Hi", "body_markdown": "Welcome {{invite_link}}"},
        "scoped",
    ),
    (
        "email-templates-delete",
        "DELETE",
        "/api/admin/projects/{project_id}/email-templates/{purpose}",
        lambda s: f"/api/admin/projects/{s.project.id}/email-templates/invite",
        lambda s: None,
        "scoped",
    ),
    (
        "email-templates-preview",
        "POST",
        "/api/admin/projects/{project_id}/email-templates/{purpose}/preview",
        lambda s: f"/api/admin/projects/{s.project.id}/email-templates/invite/preview",
        lambda s: {"subject": "Hi", "body_markdown": "Welcome {{invite_link}}"},
        "scoped",
    ),
    # --- defaults ---
    (
        "defaults-get",
        "GET",
        "/api/admin/projects/{project_id}/defaults",
        lambda s: f"/api/admin/projects/{s.project.id}/defaults",
        lambda s: None,
        "scoped",
    ),
    (
        "defaults-put",
        "PUT",
        "/api/admin/projects/{project_id}/defaults",
        lambda s: f"/api/admin/projects/{s.project.id}/defaults",
        lambda s: {"track_ids": [str(s.track.id)]},
        "scoped",
    ),
    (
        "defaults-apply",
        "POST",
        "/api/admin/projects/{project_id}/defaults/apply",
        lambda s: f"/api/admin/projects/{s.project.id}/defaults/apply",
        lambda s: None,
        "scoped",
    ),
    (
        "project-export",
        "GET",
        "/api/admin/projects/{project_id}/export",
        lambda s: f"/api/admin/projects/{s.project.id}/export?sections=people",
        lambda s: None,
        "scoped",
    ),
    # --- content structure (B4) ---
    (
        "content-tree",
        "GET",
        "/api/admin/content/tree",
        lambda s: "/api/admin/content/tree",
        lambda s: None,
        "scoped_list",
    ),
    (
        "track-patch",
        "PATCH",
        "/api/admin/tracks/{track_id}",
        lambda s: f"/api/admin/tracks/{s.track.id}",
        lambda s: {"name": "Renamed"},
        "power",
    ),
    (
        "track-impact",
        "GET",
        "/api/admin/tracks/{track_id}/impact",
        lambda s: f"/api/admin/tracks/{s.track.id}/impact",
        lambda s: None,
        "power",
    ),
    (
        "tracks-order",
        "PUT",
        "/api/admin/tracks/order",
        lambda s: "/api/admin/tracks/order",
        lambda s: {"track_ids": [str(s.track.id)]},
        "power",
    ),
    (
        "modules-order",
        "PUT",
        "/api/admin/tracks/{track_id}/modules/order",
        lambda s: f"/api/admin/tracks/{s.track.id}/modules/order",
        lambda s: {"module_ids": [str(s.module.id)]},
        "power",
    ),
    (
        "module-patch",
        "PATCH",
        "/api/admin/modules/{module_id}",
        lambda s: f"/api/admin/modules/{s.module.id}",
        lambda s: {"title": "Renamed"},
        "power",
    ),
    (
        "module-prerequisites",
        "PUT",
        "/api/admin/modules/{module_id}/prerequisites",
        lambda s: f"/api/admin/modules/{s.module.id}/prerequisites",
        lambda s: {"prerequisite_ids": []},
        "power",
    ),
    (
        "module-impact",
        "GET",
        "/api/admin/modules/{module_id}/impact",
        lambda s: f"/api/admin/modules/{s.module.id}/impact",
        lambda s: None,
        "power",
    ),
    (
        "module-gap",
        "GET",
        "/api/admin/modules/{module_id}/assignment-gap",
        lambda s: f"/api/admin/modules/{s.module.id}/assignment-gap",
        lambda s: None,
        "power",
    ),
    (
        "module-assign-gap",
        "POST",
        "/api/admin/modules/{module_id}/assign-new-lessons",
        lambda s: f"/api/admin/modules/{s.module.id}/assign-new-lessons",
        lambda s: None,
        "power",
    ),
    (
        "project-module-gap",
        "GET",
        "/api/admin/projects/{project_id}/modules/{module_id}/assignment-gap",
        lambda s: f"/api/admin/projects/{s.project.id}/modules/{s.module.id}/assignment-gap",
        lambda s: None,
        "scoped",
    ),
    (
        "project-module-assign-gap",
        "POST",
        "/api/admin/projects/{project_id}/modules/{module_id}/assign-new-lessons",
        lambda s: f"/api/admin/projects/{s.project.id}/modules/{s.module.id}/assign-new-lessons",
        lambda s: None,
        "scoped",
    ),
    # Last: deletes the seed track (each row gets a fresh seed, but keep
    # destructive rows at the end of the block for readability).
    (
        "track-delete",
        "DELETE",
        "/api/admin/tracks/{track_id}",
        lambda s: f"/api/admin/tracks/{s.track.id}",
        lambda s: None,
        "power",
    ),
    # --- users ---
    (
        "users-get",
        "GET",
        "/api/admin/users",
        lambda s: "/api/admin/users",
        lambda s: None,
        "scoped_list",
    ),
    (
        "user-get",
        "GET",
        "/api/admin/users/{user_id}",
        lambda s: f"/api/admin/users/{s.user.id}",
        lambda s: None,
        "scoped",
    ),
    (
        "invite",
        "POST",
        "/api/admin/invites",
        lambda s: "/api/admin/invites",
        lambda s: {
            "email": "matrix-new@example.com",
            "first_name": "New",
            "last_name": "Joiner",
            "project_id": str(s.project.id),
            "send_email": False,
        },
        "scoped",
    ),
    (
        "reset-link",
        "POST",
        "/api/admin/users/{user_id}/reset-link",
        lambda s: f"/api/admin/users/{s.user.id}/reset-link",
        lambda s: {"send_email": False},
        "scoped",
    ),
    (
        "reminder",
        "POST",
        "/api/admin/users/{user_id}/reminder",
        lambda s: f"/api/admin/users/{s.user.id}/reminder",
        lambda s: None,
        "scoped",
    ),
    (
        "role-patch",
        "PATCH",
        "/api/admin/users/{user_id}",
        lambda s: f"/api/admin/users/{s.user.id}",
        lambda s: {"role": "user"},
        "power",
    ),
    (
        "maturity-put",
        "PUT",
        "/api/admin/users/{user_id}/maturity",
        lambda s: f"/api/admin/users/{s.user.id}/maturity",
        lambda s: {"level": "practitioner"},
        "scoped",
    ),
    (
        "user-delete",
        "DELETE",
        "/api/admin/users/{user_id}",
        lambda s: f"/api/admin/users/{s.user.id}",
        lambda s: None,
        "scoped",
    ),
    (
        "assign-track",
        "PUT",
        "/api/admin/users/{user_id}/tracks/{track_id}",
        lambda s: f"/api/admin/users/{s.user.id}/tracks/{s.track.id}",
        lambda s: {"assigned": True},
        "scoped",
    ),
    (
        "assign-module",
        "PUT",
        "/api/admin/users/{user_id}/modules/{module_id}",
        lambda s: f"/api/admin/users/{s.user.id}/modules/{s.module.id}",
        lambda s: {"assigned": True},
        "scoped",
    ),
    (
        "assign-lesson",
        "PUT",
        "/api/admin/users/{user_id}/lessons/{lesson_id}",
        lambda s: f"/api/admin/users/{s.user.id}/lessons/{s.lesson.id}",
        lambda s: {"assigned": True},
        "scoped",
    ),
    (
        "assign-tracks-bulk",
        "PUT",
        "/api/admin/users/{user_id}/tracks",
        lambda s: f"/api/admin/users/{s.user.id}/tracks",
        lambda s: {"track_ids": [str(s.track.id)], "assigned": True},
        "scoped",
    ),
    (
        "assign-modules-bulk",
        "PUT",
        "/api/admin/users/{user_id}/modules",
        lambda s: f"/api/admin/users/{s.user.id}/modules",
        lambda s: {"module_ids": [str(s.module.id)], "assigned": True},
        "scoped",
    ),
    (
        "assign-lessons-bulk",
        "PUT",
        "/api/admin/users/{user_id}/lessons",
        lambda s: f"/api/admin/users/{s.user.id}/lessons",
        lambda s: {"lesson_ids": [str(s.lesson.id)], "assigned": True},
        "scoped",
    ),
    (
        "assignments-bulk",
        "POST",
        "/api/admin/assignments/bulk",
        lambda s: "/api/admin/assignments/bulk",
        lambda s: {"user_ids": [str(s.user.id)], "track_ids": [str(s.track.id)], "assigned": True},
        "scoped",
    ),
    (
        "admin-learning",
        "GET",
        "/api/admin/learning",
        lambda s: "/api/admin/learning",
        lambda s: None,
        "scoped_list",
    ),
    (
        "survey-levels",
        "GET",
        "/api/admin/surveys",
        lambda s: f"/api/admin/surveys?user_ids={s.user.id}",
        lambda s: None,
        "scoped",
    ),
    (
        "user-survey",
        "GET",
        "/api/admin/surveys/{user_id}",
        lambda s: f"/api/admin/surveys/{s.user.id}",
        lambda s: None,
        "scoped",
    ),
    # test_settings.llm is None here, so the interview service resolves to None
    # and both 404 "not configured" for every caller that passes authz — the
    # matrix can't tell in-scope from out-of-scope, so these are scoped_list and
    # test_admin_scope_routes.py::test_admin_interview_view_is_scoped compares
    # the bodies instead.
    (
        "interview-admin-get",
        "GET",
        "/api/admin/interviews/{user_id}",
        lambda s: f"/api/admin/interviews/{s.user.id}",
        lambda s: None,
        "scoped_list",
    ),
    (
        "interview-admin-delete",
        "DELETE",
        "/api/admin/interviews/{user_id}",
        lambda s: f"/api/admin/interviews/{s.user.id}",
        lambda s: None,
        "scoped_list",
    ),
    (
        "dashboard",
        "GET",
        "/api/admin/dashboard",
        lambda s: "/api/admin/dashboard",
        lambda s: None,
        "scoped_list",
    ),
    # --- project admins ---
    (
        "project-admins-list",
        "GET",
        "/api/admin/projects/{project_id}/admins",
        lambda s: f"/api/admin/projects/{s.project.id}/admins",
        lambda s: None,
        "scoped",
    ),
    (
        "project-admins-grant",
        "PUT",
        "/api/admin/projects/{project_id}/admins/{user_id}",
        lambda s: f"/api/admin/projects/{s.project.id}/admins/{s.user.id}",
        lambda s: None,
        "power",
    ),
    (
        "project-admins-revoke",
        "DELETE",
        "/api/admin/projects/{project_id}/admins/{user_id}",
        lambda s: f"/api/admin/projects/{s.project.id}/admins/{s.pa_in.id}",
        lambda s: None,
        "power",
    ),
    # --- content ---
    (
        "tracks-post",
        "POST",
        "/api/admin/tracks",
        lambda s: "/api/admin/tracks",
        lambda s: {"name": "T2", "track_type": "general"},
        "power",
    ),
    (
        "modules-post",
        "POST",
        "/api/admin/modules",
        lambda s: "/api/admin/modules",
        lambda s: {"track_id": str(s.track.id), "title": "M2"},
        "power",
    ),
    (
        "module-delete",
        "DELETE",
        "/api/admin/modules/{module_id}",
        lambda s: f"/api/admin/modules/{s.module.id}",
        lambda s: None,
        "power",
    ),
    (
        "lessons-post",
        "POST",
        "/api/admin/lessons",
        lambda s: "/api/admin/lessons",
        lambda s: {"module_id": str(s.module.id), "title": "L2"},
        "power",
    ),
    (
        "lesson-patch",
        "PATCH",
        "/api/admin/lessons/{lesson_id}",
        lambda s: f"/api/admin/lessons/{s.lesson.id}",
        lambda s: {"title": "Renamed"},
        "power",
    ),
    (
        "lesson-delete",
        "DELETE",
        "/api/admin/lessons/{lesson_id}",
        lambda s: f"/api/admin/lessons/{s.lesson.id}",
        lambda s: None,
        "power",
    ),
    (
        "lessons-order",
        "PUT",
        "/api/admin/modules/{module_id}/lessons/order",
        lambda s: f"/api/admin/modules/{s.module.id}/lessons/order",
        lambda s: {"lesson_ids": [str(s.lesson.id)]},
        "power",
    ),
    (
        "prompts-list",
        "GET",
        "/api/admin/prompts",
        lambda s: "/api/admin/prompts",
        lambda s: None,
        "power",
    ),
    (
        "prompts-detail",
        "GET",
        "/api/admin/prompts/{kind}",
        lambda s: "/api/admin/prompts/chatbot",
        lambda s: None,
        "power",
    ),
    # --- feedback ---
    (
        "feedback-admin-list",
        "GET",
        "/api/admin/feedback",
        lambda s: "/api/admin/feedback",
        lambda s: None,
        "power",
    ),
    (
        "feedback-admin-patch",
        "PATCH",
        "/api/admin/feedback/{feedback_id}",
        lambda s: f"/api/admin/feedback/{s.feedback.id}",
        lambda s: {"status": "accepted"},
        "power",
    ),
    # test_settings.llm is None here, so get_feedback_triage_service resolves to
    # None and this 404s "AI triage is not configured" for the admin — before
    # any model call. The row still validly pins anonymous->401 and
    # non-admin->403 (the router-level require_power_admin fires first); the 200 path
    # is covered by test_admin_feedback_triage.py, which overrides the DI.
    (
        "feedback-admin-suggest-triage",
        "POST",
        "/api/admin/feedback/suggest-triage",
        lambda s: "/api/admin/feedback/suggest-triage",
        lambda s: None,
        "power",
    ),
    # As with the triage row: test_settings.llm is None here, so
    # get_content_improvement_service resolves to None and all four 404 for the
    # admin — before any model call or DB write. The rows still pin
    # anonymous->401 and non-admin->403 (router-level require_power_admin). The 200
    # paths are covered by test_admin_content_improvement.py via a DI override.
    (
        "content-improvement-run",
        "POST",
        "/api/admin/content-improvement/run",
        lambda s: "/api/admin/content-improvement/run",
        lambda s: {"lesson_ids": [str(uuid.uuid4())]},
        "power",
    ),
    (
        "content-improvement-queue",
        "GET",
        "/api/admin/content-improvement/queue",
        lambda s: "/api/admin/content-improvement/queue",
        lambda s: None,
        "power",
    ),
    (
        "content-improvement-list",
        "GET",
        "/api/admin/content-improvement",
        lambda s: "/api/admin/content-improvement",
        lambda s: None,
        "power",
    ),
    (
        "content-improvement-detail",
        "GET",
        "/api/admin/content-improvement/{proposal_id}",
        lambda s: f"/api/admin/content-improvement/{uuid.uuid4()}",
        lambda s: None,
        "power",
    ),
    (
        "content-improvement-review",
        "POST",
        "/api/admin/content-improvement/{proposal_id}/review",
        lambda s: f"/api/admin/content-improvement/{uuid.uuid4()}/review",
        lambda s: {"decision": "reject"},
        "power",
    ),
    (
        "content-improvement-critique",
        "POST",
        "/api/admin/content-improvement/{proposal_id}/critique",
        lambda s: f"/api/admin/content-improvement/{uuid.uuid4()}/critique",
        lambda s: None,
        "power",
    ),
    # Unlike the content-improvement rows, this router is NOT LLM-gated —
    # curating notes needs no model. So the admin case here hits the real
    # handler: a 200 for the list, and a genuine 404 (NotFoundError) for a
    # random note id on review/graduate, rather than "not configured". That
    # difference is deliberate, not a copy-paste slip.
    (
        "calibration-notes-list",
        "GET",
        "/api/admin/calibration-notes",
        lambda s: "/api/admin/calibration-notes",
        lambda s: None,
        "power",
    ),
    (
        "calibration-notes-review",
        "POST",
        "/api/admin/calibration-notes/{note_id}/review",
        lambda s: f"/api/admin/calibration-notes/{uuid.uuid4()}/review",
        lambda s: {"decision": "approve"},
        "power",
    ),
    (
        "calibration-notes-graduate",
        "POST",
        "/api/admin/calibration-notes/{note_id}/graduate",
        lambda s: f"/api/admin/calibration-notes/{uuid.uuid4()}/graduate",
        lambda s: None,
        "power",
    ),
]

# Admin routes that can't be a JSON _MATRIX row; each has its own authz class.
_MATRIX_EXEMPT: dict[tuple[str, str], str] = {
    ("POST", "/api/admin/media"): "multipart: TestMediaUploadAuthz below",
    ("POST", "/api/admin/invites/bulk"): "multipart: test_admin_bulk_invite.py",
}


def test_every_admin_route_is_in_the_matrix() -> None:
    """A new /api/admin route must declare its access level here, or fail."""
    covered = {(method, route) for _, method, route, _, _, _ in _MATRIX}
    schema = app.openapi()
    missing = sorted(
        (method.upper(), path)
        for path, operations in schema["paths"].items()
        if path.startswith("/api/admin")
        for method in operations
        if (method.upper(), path) not in covered and (method.upper(), path) not in _MATRIX_EXEMPT
    )
    assert not missing, f"admin routes missing from _MATRIX: {missing}"


@pytest.mark.parametrize(
    ("method", "path_of", "body_of", "access"),
    [(spec[1], spec[3], spec[4], spec[5]) for spec in _MATRIX],
    ids=[spec[0] for spec in _MATRIX],
)
async def test_matrix(
    client: AsyncClient,
    seed: Seed,
    test_settings: Settings,
    method: str,
    path_of: Any,
    body_of: Any,
    access: Access,
) -> None:
    """Order matters: non-mutating denials first, then pa_in, admin last, so a
    destructive row (DELETE, invite) is consumed by the in-scope caller and
    the admin's 404/409 on the already-consumed target still passes authz."""
    path, body = path_of(seed), body_of(seed)

    anonymous = await client.request(method, path, json=body)
    assert anonymous.status_code == 401, f"anonymous {method} {path}"
    assert anonymous.json()["error"]["code"] == "unauthorized"

    as_user = await client.request(
        method, path, json=body, headers=auth_headers(seed.user, test_settings)
    )
    if access == "any":
        # Business-rule statuses (e.g. 409 complete-without-draft) are fine;
        # what matters is that authz passed.
        assert as_user.status_code not in (401, 403, 500), f"user {method} {path}"
    else:
        assert as_user.status_code == 403, f"user {method} {path}"
        assert as_user.json()["error"]["code"] == "forbidden"

        as_pa_out = await client.request(
            method, path, json=body, headers=auth_headers(seed.pa_out, test_settings)
        )
        as_pa_in = await client.request(
            method, path, json=body, headers=auth_headers(seed.pa_in, test_settings)
        )
        if access == "power":
            assert as_pa_out.status_code == 403, f"other project admin {method} {path}"
            assert as_pa_in.status_code == 403, f"project admin {method} {path}"
        elif access == "scoped":
            assert as_pa_out.status_code == 404, f"other project admin {method} {path}"
            assert as_pa_in.status_code not in (401, 403, 404, 500), (
                f"project admin {method} {path}"
            )
        else:  # scoped_list
            assert as_pa_out.status_code not in (401, 403, 500), f"other pa {method} {path}"
            assert as_pa_in.status_code not in (401, 403, 500), f"project admin {method} {path}"

    as_admin = await client.request(
        method, path, json=body, headers=auth_headers(seed.admin, test_settings)
    )
    assert as_admin.status_code not in (401, 403, 500), f"admin {method} {path}"


@pytest_asyncio.fixture
async def media_client(
    db_session: AsyncSession, test_settings: Settings
) -> AsyncGenerator[AsyncClient]:
    """POST /api/admin/media can't be a plain _MATRIX row above (multipart,
    not JSON) and needs the feature actually configured — otherwise even the
    admin case would incidentally "pass" the not-in-(401,403,500) check via
    the storage-unset 404 without exercising authz at all. Mirrors
    test_admin_media.py's media_client."""
    service = MediaService(
        RecordingUploader(),
        account_name=TEST_STORAGE.account_name,
        account_key=TEST_STORAGE.account_key.get_secret_value(),
        blob_endpoint=TEST_STORAGE.blob_endpoint,
        container=TEST_STORAGE.container,
        sas_ttl_hours=TEST_STORAGE.sas_ttl_hours,
    )

    async def _override_session() -> AsyncGenerator[AsyncSession]:
        yield db_session

    app.dependency_overrides[get_session] = _override_session
    app.dependency_overrides[get_settings] = lambda: test_settings
    app.dependency_overrides[get_media_service] = lambda: service
    client = AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver")
    try:
        yield client
    finally:
        await client.aclose()
        app.dependency_overrides.clear()


class TestMediaUploadAuthz:
    """POST /api/admin/media, same assertions as an admin_only _MATRIX row
    (anonymous -> 401 unauthorized, non-admin -> 403 forbidden, admin ->
    succeeds), with the media feature configured via the DI override."""

    _FILES = {"file": ("photo.png", b"data", "image/png")}

    async def test_anonymous_is_401(self, media_client: AsyncClient) -> None:
        response = await media_client.post("/api/admin/media", files=self._FILES)
        assert response.status_code == 401
        assert response.json()["error"]["code"] == "unauthorized"

    async def test_non_admin_is_403(
        self, media_client: AsyncClient, db_session: AsyncSession, test_settings: Settings
    ) -> None:
        user = await create_user(db_session, email="media-authz-user@example.com")
        response = await media_client.post(
            "/api/admin/media", files=self._FILES, headers=auth_headers(user, test_settings)
        )
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "forbidden"

    async def test_admin_succeeds(
        self, media_client: AsyncClient, db_session: AsyncSession, test_settings: Settings
    ) -> None:
        admin = await create_user(db_session, email="media-authz-admin@example.com", role="admin")
        response = await media_client.post(
            "/api/admin/media", files=self._FILES, headers=auth_headers(admin, test_settings)
        )
        assert response.status_code == 201


class TestIronRule:
    """No endpoint outside /admin/* accepts a user identifier from the request."""

    def test_no_user_id_parameter_outside_admin(self) -> None:
        schema = app.openapi()
        offenders = []
        for path, methods in schema["paths"].items():
            if path.startswith("/api/admin/"):
                continue
            if "{user_id}" in path:
                offenders.append(path)
            for spec in methods.values():
                for param in spec.get("parameters", []):
                    if param["name"] == "user_id":
                        offenders.append(f"{path} ?{param['name']}")
                ref = (
                    spec.get("requestBody", {})
                    .get("content", {})
                    .get("application/json", {})
                    .get("schema", {})
                    .get("$ref", "")
                )
                if ref:
                    component = schema["components"]["schemas"][ref.rsplit("/", 1)[1]]
                    if "user_id" in component.get("properties", {}):
                        offenders.append(f"{path} body")
        assert offenders == []

    async def test_survey_ignores_caller_supplied_user_id(
        self, client: AsyncClient, db_session: AsyncSession, test_settings: Settings
    ) -> None:
        alice = await create_user(db_session, email="iron-alice@example.com")
        bob = await create_user(db_session, email="iron-bob@example.com")
        await create_survey(db_session, bob, status="complete")

        # Query-string and body user identifiers are silently ignored.
        response = await client.get(
            f"/api/survey/me?user_id={bob.id}", headers=auth_headers(alice, test_settings)
        )
        assert response.status_code == 200
        assert response.json() is None

        response = await client.put(
            "/api/survey/me",
            json={"job_title": "Smith", "user_id": str(bob.id)},
            headers=auth_headers(alice, test_settings),
        )
        assert response.status_code == 200
        assert response.json()["user_id"] == str(alice.id)

    async def test_progress_isolated_between_users(
        self, client: AsyncClient, db_session: AsyncSession, test_settings: Settings
    ) -> None:
        company = await create_company(db_session, "Iso Co")
        project = await create_project(db_session, company, "Iso Project")
        await unlock_component(db_session, project, "learning")
        track = await create_track(db_session, "Iso Track")
        module = await create_module(db_session, track, "Iso Module")
        lesson = await create_lesson(db_session, module, "Iso Lesson")
        alice = await create_user(db_session, email="iso-alice@example.com", project_id=project.id)
        bob = await create_user(db_session, email="iso-bob@example.com", project_id=project.id)
        await complete_lesson(db_session, bob, lesson)
        await assign_track(db_session, bob, track)
        await assign_module(db_session, bob, module)
        await assign_lesson(db_session, bob, lesson)

        response = await client.get(
            f"/api/modules/{module.id}/lessons", headers=auth_headers(alice, test_settings)
        )
        assert response.status_code == 200
        assert response.json()["lessons"][0]["completed"] is False

        graph = (
            await client.get("/api/learning/graph", headers=auth_headers(alice, test_settings))
        ).json()
        iso_module = next(m for m in graph["modules"] if m["id"] == str(module.id))
        assert iso_module["completed_lesson_count"] == 0
        iso_track = next(t for t in graph["tracks"] if t["id"] == str(track.id))
        assert iso_track["assigned"] is False

        graph_bob = (
            await client.get("/api/learning/graph", headers=auth_headers(bob, test_settings))
        ).json()
        assert (
            next(m for m in graph_bob["modules"] if m["id"] == str(module.id))[
                "completed_lesson_count"
            ]
            == 1
        )
        assert next(t for t in graph_bob["tracks"] if t["id"] == str(track.id))["assigned"] is True


class TestTokenValidation:
    """Carried over from Batch 2, now against the real /api/me route."""

    async def test_missing_token_is_401(self, client: AsyncClient) -> None:
        response = await client.get("/api/me")
        assert response.status_code == 401
        assert response.headers["WWW-Authenticate"] == "Bearer"

    async def test_garbage_token_is_401(self, client: AsyncClient) -> None:
        assert (await client.get("/api/me", headers=bearer("not.a.jwt"))).status_code == 401

    async def test_expired_token_is_401(
        self, client: AsyncClient, db_session: AsyncSession, test_settings: Settings
    ) -> None:
        user = await create_user(db_session, email="expired-jwt@example.com")
        expired_auth = test_settings.auth.model_copy(update={"access_token_minutes": -1})
        response = await client.get(
            "/api/me", headers=bearer(create_access_token(user.id, expired_auth))
        )
        assert response.status_code == 401

    async def test_wrong_secret_token_is_401(
        self, client: AsyncClient, db_session: AsyncSession, test_settings: Settings
    ) -> None:
        from pydantic import SecretStr

        user = await create_user(db_session, email="forged@example.com")
        forged_auth = test_settings.auth.model_copy(
            update={"jwt_secret": SecretStr("attacker-secret-0123456789-0123456789")}
        )
        response = await client.get(
            "/api/me", headers=bearer(create_access_token(user.id, forged_auth))
        )
        assert response.status_code == 401

    async def test_token_for_unknown_user_is_401(
        self, client: AsyncClient, test_settings: Settings
    ) -> None:
        response = await client.get(
            "/api/me", headers=bearer(create_access_token(uuid.uuid4(), test_settings.auth))
        )
        assert response.status_code == 401

    async def test_token_for_deactivated_user_is_401(
        self, client: AsyncClient, db_session: AsyncSession, test_settings: Settings
    ) -> None:
        user = await create_user(db_session, email="benched@example.com", is_active=False)
        response = await client.get("/api/me", headers=auth_headers(user, test_settings))
        assert response.status_code == 401

    async def test_role_change_takes_effect_immediately(
        self, client: AsyncClient, db_session: AsyncSession, test_settings: Settings
    ) -> None:
        """No role claim in the JWT: demotion applies on the very next request
        with the same still-valid token."""
        user = await create_user(db_session, email="demoted@example.com", role="admin")
        headers = auth_headers(user, test_settings)
        assert (await client.get("/api/admin/learning", headers=headers)).status_code == 200

        user.role = "user"
        await db_session.commit()
        assert (await client.get("/api/admin/learning", headers=headers)).status_code == 403


class TestPublicEndpoints:
    async def test_auth_endpoints_do_not_require_a_token(self, client: AsyncClient) -> None:
        # 404/204/200 (never "401 missing credentials") prove these are public.
        assert (await client.get("/api/auth/invite/unknown-token")).status_code == 404
        assert (
            await client.post("/api/auth/logout", json={"refresh_token": "x"})
        ).status_code == 204
        assert (await client.get("/api/health")).status_code == 200
