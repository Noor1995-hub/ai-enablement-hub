"""Authorization matrix (design-backend.md §4).

Every protected endpoint × {no token, user token, admin token}, own-row
isolation, and the iron rule: no endpoint outside /admin/* accepts a user
identifier from the request — ownership comes exclusively from the token.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

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
        # The component lock isn't a role check (admin is not exempt — see
        # test_component_lock.py::test_admin_is_not_exempt) — this matrix's
        # blanket "admin succeeds everywhere non-admin-only" needs the admin
        # to actually belong to a project with `learning` unlocked, same as
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
    return Seed(company, project, track, module, lesson, admin, user, other, conversation, feedback)


# (name, method, path builder, body builder, admin_only)
_MATRIX: list[tuple[str, str, Any, Any, bool]] = [
    ("me", "GET", lambda s: "/api/me", lambda s: None, False),
    ("journey", "GET", lambda s: "/api/me/journey", lambda s: None, False),
    ("survey-get", "GET", lambda s: "/api/survey/me", lambda s: None, False),
    ("survey-put", "PUT", lambda s: "/api/survey/me", lambda s: {"job_title": "Dev"}, False),
    ("survey-complete", "POST", lambda s: "/api/survey/complete", lambda s: None, False),
    ("graph", "GET", lambda s: "/api/learning/graph", lambda s: None, False),
    (
        "module-lessons",
        "GET",
        lambda s: f"/api/modules/{s.module.id}/lessons",
        lambda s: None,
        False,
    ),
    ("lesson", "GET", lambda s: f"/api/lessons/{s.lesson.id}", lambda s: None, False),
    (
        "feedback",
        "POST",
        lambda s: "/api/feedback",
        lambda s: {"lesson_id": str(s.lesson.id), "message": "Great lesson"},
        False,
    ),
    (
        "progress",
        "PUT",
        lambda s: f"/api/lessons/{s.lesson.id}/progress",
        lambda s: {"answers": {}},
        False,
    ),
    ("tracks", "GET", lambda s: "/api/tracks", lambda s: None, False),
    ("track-modules", "GET", lambda s: f"/api/tracks/{s.track.id}/modules", lambda s: None, False),
    ("companies-get", "GET", lambda s: "/api/admin/companies", lambda s: None, True),
    (
        "companies-post",
        "POST",
        lambda s: "/api/admin/companies",
        lambda s: {"name": "Fresh Co"},
        True,
    ),
    (
        "projects-post",
        "POST",
        lambda s: "/api/admin/projects",
        lambda s: {"name": "P2", "company_id": str(s.company.id)},
        True,
    ),
    (
        "components-get",
        "GET",
        lambda s: f"/api/admin/projects/{s.project.id}/components",
        lambda s: None,
        True,
    ),
    (
        "components-put",
        "PUT",
        lambda s: f"/api/admin/projects/{s.project.id}/components/assessment",
        lambda s: {"hidden": True},
        True,
    ),
    (
        "email-templates-get",
        "GET",
        lambda s: f"/api/admin/projects/{s.project.id}/email-templates",
        lambda s: None,
        True,
    ),
    (
        "email-templates-put",
        "PUT",
        lambda s: f"/api/admin/projects/{s.project.id}/email-templates/invite",
        lambda s: {"subject": "Hi", "body_markdown": "Welcome {{invite_link}}"},
        True,
    ),
    (
        "email-templates-delete",
        "DELETE",
        lambda s: f"/api/admin/projects/{s.project.id}/email-templates/invite",
        lambda s: None,
        True,
    ),
    (
        "email-templates-preview",
        "POST",
        lambda s: f"/api/admin/projects/{s.project.id}/email-templates/invite/preview",
        lambda s: {"subject": "Hi", "body_markdown": "Welcome {{invite_link}}"},
        True,
    ),
    ("users-get", "GET", lambda s: "/api/admin/users", lambda s: None, True),
    (
        "invite",
        "POST",
        lambda s: "/api/admin/invites",
        lambda s: {
            "email": "matrix-new@example.com",
            "first_name": "New",
            "last_name": "Joiner",
            "project_id": str(s.project.id),
        },
        True,
    ),
    (
        "reset-link",
        "POST",
        lambda s: f"/api/admin/users/{s.other.id}/reset-link",
        lambda s: None,
        True,
    ),
    (
        "reminder",
        "POST",
        lambda s: f"/api/admin/users/{s.other.id}/reminder",
        lambda s: None,
        True,
    ),
    (
        "role-patch",
        "PATCH",
        lambda s: f"/api/admin/users/{s.other.id}",
        lambda s: {"role": "user"},
        True,
    ),
    (
        "maturity-put",
        "PUT",
        lambda s: f"/api/admin/users/{s.other.id}/maturity",
        lambda s: {"level": "practitioner"},
        True,
    ),
    ("user-delete", "DELETE", lambda s: f"/api/admin/users/{s.other.id}", lambda s: None, True),
    (
        "assign-track",
        "PUT",
        lambda s: f"/api/admin/users/{s.other.id}/tracks/{s.track.id}",
        lambda s: {"assigned": True},
        True,
    ),
    (
        "assign-module",
        "PUT",
        lambda s: f"/api/admin/users/{s.other.id}/modules/{s.module.id}",
        lambda s: {"assigned": True},
        True,
    ),
    (
        "assign-lesson",
        "PUT",
        lambda s: f"/api/admin/users/{s.other.id}/lessons/{s.lesson.id}",
        lambda s: {"assigned": True},
        True,
    ),
    (
        "assign-tracks-bulk",
        "PUT",
        lambda s: f"/api/admin/users/{s.other.id}/tracks",
        lambda s: {"track_ids": [str(s.track.id)], "assigned": True},
        True,
    ),
    (
        "assign-modules-bulk",
        "PUT",
        lambda s: f"/api/admin/users/{s.other.id}/modules",
        lambda s: {"module_ids": [str(s.module.id)], "assigned": True},
        True,
    ),
    (
        "assign-lessons-bulk",
        "PUT",
        lambda s: f"/api/admin/users/{s.other.id}/lessons",
        lambda s: {"lesson_ids": [str(s.lesson.id)], "assigned": True},
        True,
    ),
    (
        "assignments-bulk",
        "POST",
        lambda s: "/api/admin/assignments/bulk",
        lambda s: {"user_ids": [str(s.other.id)], "track_ids": [str(s.track.id)], "assigned": True},
        True,
    ),
    ("admin-learning", "GET", lambda s: "/api/admin/learning", lambda s: None, True),
    (
        "survey-levels",
        "GET",
        lambda s: f"/api/admin/surveys?user_ids={s.other.id}",
        lambda s: None,
        True,
    ),
    ("user-survey", "GET", lambda s: f"/api/admin/surveys/{s.other.id}", lambda s: None, True),
    (
        "tracks-post",
        "POST",
        lambda s: "/api/admin/tracks",
        lambda s: {"name": "T2", "track_type": "general"},
        True,
    ),
    (
        "modules-post",
        "POST",
        lambda s: "/api/admin/modules",
        lambda s: {"track_id": str(s.track.id), "title": "M2"},
        True,
    ),
    (
        "module-delete",
        "DELETE",
        lambda s: f"/api/admin/modules/{s.module.id}",
        lambda s: None,
        True,
    ),
    (
        "lessons-post",
        "POST",
        lambda s: "/api/admin/lessons",
        lambda s: {"module_id": str(s.module.id), "title": "L2"},
        True,
    ),
    (
        "lesson-patch",
        "PATCH",
        lambda s: f"/api/admin/lessons/{s.lesson.id}",
        lambda s: {"title": "Renamed"},
        True,
    ),
    (
        "lesson-delete",
        "DELETE",
        lambda s: f"/api/admin/lessons/{s.lesson.id}",
        lambda s: None,
        True,
    ),
    (
        "lessons-order",
        "PUT",
        lambda s: f"/api/admin/modules/{s.module.id}/lessons/order",
        lambda s: {"lesson_ids": [str(s.lesson.id)]},
        True,
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
        lambda s: "/api/chat/conversations?kind=chatbot",
        lambda s: None,
        False,
    ),
    (
        "defaults-get",
        "GET",
        lambda s: f"/api/admin/projects/{s.project.id}/defaults",
        lambda s: None,
        True,
    ),
    (
        "defaults-put",
        "PUT",
        lambda s: f"/api/admin/projects/{s.project.id}/defaults",
        lambda s: {"track_ids": [str(s.track.id)]},
        True,
    ),
    (
        "defaults-apply",
        "POST",
        lambda s: f"/api/admin/projects/{s.project.id}/defaults/apply",
        lambda s: None,
        True,
    ),
    ("feedback-admin-list", "GET", lambda s: "/api/admin/feedback", lambda s: None, True),
    (
        "feedback-admin-patch",
        "PATCH",
        lambda s: f"/api/admin/feedback/{s.feedback.id}",
        lambda s: {"status": "accepted"},
        True,
    ),
    # test_settings.llm is None here, so get_feedback_triage_service resolves to
    # None and this 404s "AI triage is not configured" for the admin — before
    # any model call. The row still validly pins anonymous->401 and
    # non-admin->403 (the router-level require_admin fires first); the 200 path
    # is covered by test_admin_feedback_triage.py, which overrides the DI.
    (
        "feedback-admin-suggest-triage",
        "POST",
        lambda s: "/api/admin/feedback/suggest-triage",
        lambda s: None,
        True,
    ),
    # As with the triage row: test_settings.llm is None here, so
    # get_content_improvement_service resolves to None and all four 404 for the
    # admin — before any model call or DB write. The rows still pin
    # anonymous->401 and non-admin->403 (router-level require_admin). The 200
    # paths are covered by test_admin_content_improvement.py via a DI override.
    (
        "content-improvement-run",
        "POST",
        lambda s: "/api/admin/content-improvement/run",
        lambda s: None,
        True,
    ),
    (
        "content-improvement-list",
        "GET",
        lambda s: "/api/admin/content-improvement",
        lambda s: None,
        True,
    ),
    (
        "content-improvement-detail",
        "GET",
        lambda s: f"/api/admin/content-improvement/{uuid.uuid4()}",
        lambda s: None,
        True,
    ),
    (
        "content-improvement-review",
        "POST",
        lambda s: f"/api/admin/content-improvement/{uuid.uuid4()}/review",
        lambda s: {"decision": "reject"},
        True,
    ),
    ("dashboard", "GET", lambda s: "/api/admin/dashboard", lambda s: None, True),
]


@pytest.mark.parametrize(
    ("method", "path_of", "body_of", "admin_only"),
    [spec[1:] for spec in _MATRIX],
    ids=[spec[0] for spec in _MATRIX],
)
async def test_matrix(
    client: AsyncClient,
    seed: Seed,
    test_settings: Settings,
    method: str,
    path_of: Any,
    body_of: Any,
    admin_only: bool,
) -> None:
    path, body = path_of(seed), body_of(seed)

    anonymous = await client.request(method, path, json=body)
    assert anonymous.status_code == 401, f"anonymous {method} {path}"
    assert anonymous.json()["error"]["code"] == "unauthorized"

    as_user = await client.request(
        method, path, json=body, headers=auth_headers(seed.user, test_settings)
    )
    if admin_only:
        assert as_user.status_code == 403, f"user {method} {path}"
        assert as_user.json()["error"]["code"] == "forbidden"
    else:
        # Business-rule statuses (e.g. 409 complete-without-draft) are fine;
        # what matters is that authz passed.
        assert as_user.status_code not in (401, 403, 500), f"user {method} {path}"

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
