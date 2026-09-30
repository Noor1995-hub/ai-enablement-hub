"""Chat router: SSE streaming POST + two GET history endpoints.

test_settings.llm is None (conftest keeps LLM__* out of the hermetic test
settings), so the real DI chain (get_llm_service -> get_chat_service) always
resolves to None here — every route would otherwise 404 as "not configured".
`chat_client` below overrides get_chat_service with a real ChatService (repos
bound to db_session) wired to a FakeLlmClient, mirroring test_admin_email.py's
`make_client` factory-fixture pattern (its own AsyncClient + dependency_overrides,
not the plain conftest `client` fixture).

AI-enablement is seeded directly via OrgRepository.upsert_ai_setting rather than
through PUT /api/admin/projects/{id}/ai/{kind} — that admin endpoint is Task 13,
not built yet, so seeding the repository keeps this task's tests self-contained.
"""

from __future__ import annotations

import json
import uuid
from typing import TYPE_CHECKING

import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from src.core.dependencies.chat import get_chat_service
from src.core.dependencies.database import get_session
from src.core.dependencies.settings import get_settings
from src.main import app
from src.repositories.conversation_repository import ConversationRepository
from src.repositories.message_repository import MessageRepository
from src.repositories.org_repository import OrgRepository
from src.services.chat_service import ChatService
from src.services.prompts import prompt_version
from tests.fixtures.auth import auth_headers
from tests.fixtures.factories import (
    create_company,
    create_project,
    create_survey,
    create_user,
    unlock_component,
)
from tests.fixtures.llm import FailingLlmClient, FakeLlmClient, in_stream_error

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator, Callable

    from sqlalchemy.ext.asyncio import AsyncSession

    from src.core.configs.settings import Settings
    from src.db.models import Project, User


def _parse_sse(raw: str) -> list[tuple[str, dict]]:
    """Minimal SSE parser for test assertions: [(event, data_dict), ...]."""
    events = []
    event_name = "message"
    for line in raw.splitlines():
        if line.startswith("event:"):
            event_name = line.removeprefix("event:").strip()
        elif line.startswith("data:"):
            events.append((event_name, json.loads(line.removeprefix("data:").strip())))
            event_name = "message"
    return events


async def _enable_ai(db_session: AsyncSession, project_id: uuid.UUID, kind: str) -> None:
    await OrgRepository(db_session).upsert_ai_setting(project_id, kind, enabled=True)


@pytest_asyncio.fixture
async def chat_client(
    db_session: AsyncSession, test_settings: Settings
) -> AsyncGenerator[Callable[[FakeLlmClient], AsyncClient]]:
    """Factory: an AsyncClient with get_chat_service overridden to a real
    ChatService (repos bound to db_session) backed by the given FakeLlmClient."""
    clients: list[AsyncClient] = []

    def _make(fake_llm: FakeLlmClient) -> AsyncClient:
        async def _override_session() -> AsyncGenerator[AsyncSession]:
            yield db_session

        service = ChatService(
            ConversationRepository(db_session),
            MessageRepository(db_session),
            fake_llm,
        )
        app.dependency_overrides[get_session] = _override_session
        app.dependency_overrides[get_settings] = lambda: test_settings
        app.dependency_overrides[get_chat_service] = lambda: service
        client = AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver")
        clients.append(client)
        return client

    try:
        yield _make
    finally:
        app.dependency_overrides.clear()
        for client in clients:
            await client.aclose()


class TestSendChatMessage:
    async def test_streams_tokens_and_done_when_enabled(
        self,
        chat_client: Callable[[FakeLlmClient], AsyncClient],
        db_session: AsyncSession,
        test_settings: Settings,
    ) -> None:
        company = await create_company(db_session, "Chat Router Co")
        project = await create_project(db_session, company, "Chat Router Project")
        user = await create_user(
            db_session,
            email="chat-router-user@example.com",
            company_id=company.id,
            project_id=project.id,
        )
        await _enable_ai(db_session, project.id, "chatbot")

        client = chat_client(FakeLlmClient(chunks=["Hi", " there!"]))
        async with client.stream(
            "POST",
            "/api/chat/chatbot",
            json={"content": "hi"},
            headers=auth_headers(user, test_settings),
        ) as response:
            assert response.status_code == 200
            raw = "".join([chunk async for chunk in response.aiter_text()])

        events = _parse_sse(raw)
        assert [e for e, _ in events] == ["token", "token", "done"]
        assert events[0][1] == {"text": "Hi"}
        done_data = events[2][1]
        assert done_data["truncated"] is False
        # Pins the `done` event's contract for Task 15's frontend: usage must
        # mirror FakeLlmClient's default (input_tokens=10, output_tokens=len(chunks)),
        # and conversation_id must be present and a valid uuid string.
        assert done_data["usage"] == {"input_tokens": 10, "output_tokens": 2}
        assert uuid.UUID(done_data["conversation_id"])

    async def test_21st_call_in_window_is_429_with_retry_after(
        self,
        chat_client: Callable[[FakeLlmClient], AsyncClient],
        db_session: AsyncSession,
        test_settings: Settings,
    ) -> None:
        """Mirrors test_cross_cutting.py's TestLoginRateLimit/TestSetPasswordRateLimit
        convention: hammer the endpoint N+1 times on the same key and assert the
        over-limit call is 429 + Retry-After. `_prepare_chat_message` enforces the
        SHORT window first (`chat:{user.id}`, max_calls=20/300s), so the 21st call
        here trips `_RATE_LIMITED_SHORT` before the DAILY check (`chat-daily:{user.id}`,
        max_calls=200/86400s) is ever reached — the daily path shares the exact same
        `RateLimiter.is_limited` call and is covered by inspection rather than a
        201-iteration loop. `rate_limiter` is a process-global reset by conftest's
        autouse `_reset_rate_limiter` fixture before/after every test, so this test
        is deterministic and can't leak counters into other tests."""
        company = await create_company(db_session, "Chat Rate Limit Co")
        project = await create_project(db_session, company, "Chat Rate Limit Project")
        user = await create_user(
            db_session,
            email="chat-rate-limited@example.com",
            company_id=company.id,
            project_id=project.id,
        )
        await _enable_ai(db_session, project.id, "chatbot")

        client = chat_client(FakeLlmClient(chunks=["hi"]))
        for _ in range(20):
            response = await client.post(
                "/api/chat/chatbot",
                json={"content": "hi"},
                headers=auth_headers(user, test_settings),
            )
            assert response.status_code == 200

        response = await client.post(
            "/api/chat/chatbot", json={"content": "hi"}, headers=auth_headers(user, test_settings)
        )
        assert response.status_code == 429
        assert response.headers["Retry-After"] == "60"

    async def test_provider_failure_mid_stream_sends_an_error_frame(
        self,
        chat_client: Callable[[FakeLlmClient], AsyncClient],
        db_session: AsyncSession,
        test_settings: Settings,
    ) -> None:
        """End-to-end proof that the frame reaches the wire: the response is
        still 200 (headers were committed before the failure), the last SSE
        event is `error`, not `done`, and it names the conversation so the
        client can continue it instead of orphaning it."""
        company = await create_company(db_session, "Chat Error Co")
        project = await create_project(db_session, company, "Chat Error Project")
        user = await create_user(
            db_session,
            email="chat-stream-error@example.com",
            company_id=company.id,
            project_id=project.id,
        )
        await _enable_ai(db_session, project.id, "chatbot")

        client = chat_client(FailingLlmClient(in_stream_error(), chunks=["Par"]))
        async with client.stream(
            "POST",
            "/api/chat/chatbot",
            json={"content": "hi"},
            headers=auth_headers(user, test_settings),
        ) as response:
            assert response.status_code == 200
            raw = "".join([chunk async for chunk in response.aiter_text()])

        events = _parse_sse(raw)
        assert [e for e, _ in events] == ["token", "error"]
        error_data = events[1][1]
        assert error_data["message"] == (
            "The assistant is busy right now - please try again in a moment."
        )
        conversation_id = uuid.UUID(error_data["conversation_id"])
        stored = await MessageRepository(db_session).list_for_conversation(conversation_id)
        assert [(m.role, m.content) for m in stored] == [("user", "hi"), ("assistant", "Par")]
        assert stored[1].metadata_ == {
            "truncated": True,
            "model": "fake-model",
            "prompt_version": prompt_version("chatbot"),
        }

    async def test_403_when_ai_disabled(
        self,
        chat_client: Callable[[FakeLlmClient], AsyncClient],
        db_session: AsyncSession,
        test_settings: Settings,
    ) -> None:
        company = await create_company(db_session, "Chat Router Co 2")
        project = await create_project(db_session, company, "Chat Router Project 2")
        user = await create_user(
            db_session,
            email="chat-router-disabled@example.com",
            company_id=company.id,
            project_id=project.id,
        )

        client = chat_client(FakeLlmClient(chunks=[]))
        response = await client.post(
            "/api/chat/chatbot", json={"content": "hi"}, headers=auth_headers(user, test_settings)
        )
        assert response.status_code == 403

    async def test_anonymous_is_401(
        self, chat_client: Callable[[FakeLlmClient], AsyncClient]
    ) -> None:
        client = chat_client(FakeLlmClient(chunks=[]))
        response = await client.post("/api/chat/chatbot", json={"content": "hi"})
        assert response.status_code == 401

    async def test_unknown_conversation_id_is_404(
        self,
        chat_client: Callable[[FakeLlmClient], AsyncClient],
        db_session: AsyncSession,
        test_settings: Settings,
    ) -> None:
        company = await create_company(db_session, "Chat Router Co 3")
        project = await create_project(db_session, company, "Chat Router Project 3")
        user = await create_user(
            db_session,
            email="chat-router-404@example.com",
            company_id=company.id,
            project_id=project.id,
        )
        await _enable_ai(db_session, project.id, "chatbot")

        client = chat_client(FakeLlmClient(chunks=[]))
        response = await client.post(
            "/api/chat/chatbot",
            json={"content": "hi", "conversation_id": str(uuid.uuid4())},
            headers=auth_headers(user, test_settings),
        )
        assert response.status_code == 404

    async def test_interview_conversation_id_rejected_on_the_chatbot_surface(
        self,
        chat_client: Callable[[FakeLlmClient], AsyncClient],
        db_session: AsyncSession,
        test_settings: Settings,
    ) -> None:
        """Only `chatbot` is enabled here. Posting the user's own INTERVIEW
        conversation id must 404 rather than append a turn to the interview
        transcript that admins read and the playbook generator consumes."""
        company = await create_company(db_session, "Chat Kind Co")
        project = await create_project(db_session, company, "Chat Kind Project")
        user = await create_user(
            db_session,
            email="chat-kind-confusion@example.com",
            company_id=company.id,
            project_id=project.id,
        )
        await _enable_ai(db_session, project.id, "chatbot")
        interview = await ConversationRepository(db_session).create(
            user_id=user.id, kind="interview"
        )

        client = chat_client(FakeLlmClient(chunks=["hi"]))
        response = await client.post(
            "/api/chat/chatbot",
            json={"content": "hi", "conversation_id": str(interview.id)},
            headers=auth_headers(user, test_settings),
        )
        assert response.status_code == 404


class TestListAndGetConversations:
    async def test_list_and_detail_ungated_by_ai_setting(
        self,
        chat_client: Callable[[FakeLlmClient], AsyncClient],
        db_session: AsyncSession,
        test_settings: Settings,
    ) -> None:
        # AI stays default-disabled for this project, but history endpoints
        # aren't gated by require_ai_surface.
        company = await create_company(db_session, "Chat History Co")
        project = await create_project(db_session, company, "Chat History Project")
        user = await create_user(
            db_session,
            email="chat-history@example.com",
            company_id=company.id,
            project_id=project.id,
        )
        conversation = await ConversationRepository(db_session).create(
            user_id=user.id, kind="chatbot"
        )

        client = chat_client(FakeLlmClient(chunks=[]))
        list_response = await client.get(
            "/api/chat/conversations?kind=chatbot", headers=auth_headers(user, test_settings)
        )
        assert list_response.status_code == 200
        assert len(list_response.json()["conversations"]) == 1

        detail_response = await client.get(
            f"/api/chat/conversations/{conversation.id}", headers=auth_headers(user, test_settings)
        )
        assert detail_response.status_code == 200

    async def test_detail_404_for_someone_elses_conversation(
        self,
        chat_client: Callable[[FakeLlmClient], AsyncClient],
        db_session: AsyncSession,
        test_settings: Settings,
    ) -> None:
        company = await create_company(db_session, "Chat History Co 2")
        project = await create_project(db_session, company, "Chat History Project 2")
        owner = await create_user(
            db_session, email="chat-owner@example.com", company_id=company.id, project_id=project.id
        )
        other = await create_user(db_session, email="chat-other@example.com")
        conversation = await ConversationRepository(db_session).create(
            user_id=owner.id, kind="chatbot"
        )

        client = chat_client(FakeLlmClient(chunks=[]))
        response = await client.get(
            f"/api/chat/conversations/{conversation.id}", headers=auth_headers(other, test_settings)
        )
        assert response.status_code == 404

    async def test_detail_anonymous_is_401(
        self, chat_client: Callable[[FakeLlmClient], AsyncClient]
    ) -> None:
        client = chat_client(FakeLlmClient(chunks=[]))
        response = await client.get(f"/api/chat/conversations/{uuid.uuid4()}")
        assert response.status_code == 401

    async def test_list_anonymous_is_401(
        self, chat_client: Callable[[FakeLlmClient], AsyncClient]
    ) -> None:
        client = chat_client(FakeLlmClient(chunks=[]))
        response = await client.get("/api/chat/conversations?kind=chatbot")
        assert response.status_code == 401


class TestInterviewKindComponentGate:
    """`kind=interview` on the chat router honours the project's `interview`
    component lock (same 403 ComponentLockedError as /api/interview/*): interview
    turns stream through POST /api/chat/interview and history reads through
    GET /api/chat/conversations?kind=interview. The AI surface is enabled in
    every case, so a 403 here can only come from the component gate (asserted
    via the "interview component" message). Other kinds ignore the lock."""

    async def _learner(self, db_session: AsyncSession, slug: str) -> tuple[User, Project]:
        company = await create_company(db_session, f"Chat Interview Gate Co {slug}")
        project = await create_project(db_session, company, f"Chat Interview Gate {slug}")
        user = await create_user(
            db_session,
            email=f"chat-interview-{slug}@example.com",
            company_id=company.id,
            project_id=project.id,
        )
        await _enable_ai(db_session, project.id, "interview")
        await _enable_ai(db_session, project.id, "chatbot")
        return user, project

    async def test_post_interview_403_when_locked_by_default(
        self,
        chat_client: Callable[[FakeLlmClient], AsyncClient],
        db_session: AsyncSession,
        test_settings: Settings,
    ) -> None:
        user, _ = await self._learner(db_session, "post-locked")
        client = chat_client(FakeLlmClient(chunks=["never"]))
        response = await client.post(
            "/api/chat/interview", json={"content": "hi"}, headers=auth_headers(user, test_settings)
        )
        assert response.status_code == 403
        assert "interview component" in response.json()["error"]["message"]

    async def test_post_interview_403_when_hidden(
        self,
        chat_client: Callable[[FakeLlmClient], AsyncClient],
        db_session: AsyncSession,
        test_settings: Settings,
    ) -> None:
        user, project = await self._learner(db_session, "post-hidden")
        await unlock_component(db_session, project, "interview", hidden=True)
        client = chat_client(FakeLlmClient(chunks=["never"]))
        response = await client.post(
            "/api/chat/interview", json={"content": "hi"}, headers=auth_headers(user, test_settings)
        )
        assert response.status_code == 403
        assert "interview component" in response.json()["error"]["message"]

    async def test_post_interview_streams_when_unlocked(
        self,
        chat_client: Callable[[FakeLlmClient], AsyncClient],
        db_session: AsyncSession,
        test_settings: Settings,
    ) -> None:
        user, project = await self._learner(db_session, "post-open")
        await unlock_component(db_session, project, "interview")
        await create_survey(db_session, user, status="complete")
        client = chat_client(FakeLlmClient(chunks=["Hello"]))
        async with client.stream(
            "POST",
            "/api/chat/interview",
            json={"content": "hi"},
            headers=auth_headers(user, test_settings),
        ) as response:
            assert response.status_code == 200
            raw = "".join([chunk async for chunk in response.aiter_text()])
        assert [e for e, _ in _parse_sse(raw)] == ["token", "done"]

    async def test_post_interview_without_id_continues_the_existing_interview(
        self,
        chat_client: Callable[[FakeLlmClient], AsyncClient],
        db_session: AsyncSession,
        test_settings: Settings,
    ) -> None:
        """One interview per user (uq_conversations_interview_user_id): a turn
        posted without a conversation_id joins the learner's interview rather
        than trying to insert a second one (which the index would turn into a 500)."""
        user, project = await self._learner(db_session, "post-no-id")
        await unlock_component(db_session, project, "interview")
        await create_survey(db_session, user, status="complete")
        conversations = ConversationRepository(db_session)
        existing = await conversations.create(user_id=user.id, kind="interview")
        client = chat_client(FakeLlmClient(chunks=["Hello"]))
        async with client.stream(
            "POST",
            "/api/chat/interview",
            json={"content": "hi"},
            headers=auth_headers(user, test_settings),
        ) as response:
            assert response.status_code == 200
            raw = "".join([chunk async for chunk in response.aiter_text()])
        done = [data for event, data in _parse_sse(raw) if event == "done"]
        assert done[0]["conversation_id"] == str(existing.id)
        rows = await conversations.list_for_user(user.id, "interview")
        assert [c.id for c in rows] == [existing.id]

    async def test_list_interview_403_when_locked(
        self,
        chat_client: Callable[[FakeLlmClient], AsyncClient],
        db_session: AsyncSession,
        test_settings: Settings,
    ) -> None:
        user, _ = await self._learner(db_session, "list-locked")
        client = chat_client(FakeLlmClient(chunks=[]))
        response = await client.get(
            "/api/chat/conversations?kind=interview", headers=auth_headers(user, test_settings)
        )
        assert response.status_code == 403
        assert "interview component" in response.json()["error"]["message"]

    async def test_list_interview_403_when_hidden(
        self,
        chat_client: Callable[[FakeLlmClient], AsyncClient],
        db_session: AsyncSession,
        test_settings: Settings,
    ) -> None:
        user, project = await self._learner(db_session, "list-hidden")
        await unlock_component(db_session, project, "interview", hidden=True)
        client = chat_client(FakeLlmClient(chunks=[]))
        response = await client.get(
            "/api/chat/conversations?kind=interview", headers=auth_headers(user, test_settings)
        )
        assert response.status_code == 403

    async def test_list_interview_allowed_when_unlocked(
        self,
        chat_client: Callable[[FakeLlmClient], AsyncClient],
        db_session: AsyncSession,
        test_settings: Settings,
    ) -> None:
        user, project = await self._learner(db_session, "list-open")
        await unlock_component(db_session, project, "interview")
        await ConversationRepository(db_session).create(user_id=user.id, kind="interview")
        client = chat_client(FakeLlmClient(chunks=[]))
        response = await client.get(
            "/api/chat/conversations?kind=interview", headers=auth_headers(user, test_settings)
        )
        assert response.status_code == 200
        assert len(response.json()["conversations"]) == 1

    async def test_other_kinds_ignore_the_interview_lock(
        self,
        chat_client: Callable[[FakeLlmClient], AsyncClient],
        db_session: AsyncSession,
        test_settings: Settings,
    ) -> None:
        """interview stays default-locked here; chatbot must still work."""
        user, _ = await self._learner(db_session, "other-kind")
        client = chat_client(FakeLlmClient(chunks=["ok"]))
        headers = auth_headers(user, test_settings)
        async with client.stream(
            "POST", "/api/chat/chatbot", json={"content": "hi"}, headers=headers
        ) as response:
            assert response.status_code == 200
            _ = [chunk async for chunk in response.aiter_text()]
        list_response = await client.get("/api/chat/conversations?kind=chatbot", headers=headers)
        assert list_response.status_code == 200
        assert len(list_response.json()["conversations"]) == 1
