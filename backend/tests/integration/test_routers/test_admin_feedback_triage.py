"""POST /api/admin/feedback/suggest-triage + the ai_* fields on the queue.

test_settings.llm is None (conftest keeps LLM__* out of the hermetic test
settings), so the real DI chain (get_llm_service -> get_feedback_triage_service)
always resolves to None here and the endpoint 404s "not configured".
`triage_client` below overrides get_feedback_triage_service with a real service
(repository bound to db_session) wired to a fake LLM, mirroring test_chat.py's
`chat_client` factory-fixture pattern.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from src.core.dependencies.content_ai import get_feedback_triage_service
from src.core.dependencies.database import get_session
from src.core.dependencies.settings import get_settings
from src.db.models import Feedback
from src.main import app
from src.repositories.feedback_repository import FeedbackRepository
from src.services.feedback_triage_service import FeedbackTriageService
from src.services.llm_service import LlmUsage
from tests.fixtures.auth import auth_headers
from tests.fixtures.factories import (
    create_company,
    create_lesson,
    create_module,
    create_project,
    create_track,
    create_user,
)

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator, Callable

    from sqlalchemy.ext.asyncio import AsyncSession

    from src.core.configs.settings import Settings


class FakeTriageLlm:
    def __init__(self, result: dict[str, Any]) -> None:
        self.result = result
        self.calls = 0

    async def complete_structured(
        self, *, system: str, prompt: str, schema: object, max_tokens: int
    ) -> tuple[dict[str, Any], LlmUsage]:
        self.calls += 1
        return dict(self.result), LlmUsage(input_tokens=10, output_tokens=5)


@pytest_asyncio.fixture
async def triage_client(
    db_session: AsyncSession, test_settings: Settings
) -> AsyncGenerator[Callable[[FakeTriageLlm], AsyncClient]]:
    clients: list[AsyncClient] = []

    def _make(fake_llm: FakeTriageLlm) -> AsyncClient:
        async def _override_session() -> AsyncGenerator[AsyncSession]:
            yield db_session

        service = FeedbackTriageService(
            FeedbackRepository(db_session),
            fake_llm,  # ty: ignore[invalid-argument-type]
        )
        app.dependency_overrides[get_session] = _override_session
        app.dependency_overrides[get_settings] = lambda: test_settings
        app.dependency_overrides[get_feedback_triage_service] = lambda: service
        client = AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver")
        clients.append(client)
        return client

    try:
        yield _make
    finally:
        app.dependency_overrides.clear()
        for client in clients:
            await client.aclose()


async def _seed(db_session: AsyncSession, prefix: str) -> tuple:
    company = await create_company(db_session, f"{prefix} Co")
    project = await create_project(db_session, company, f"{prefix} Project")
    admin = await create_user(db_session, email=f"{prefix}-admin@x.test", role="admin")
    learner = await create_user(
        db_session,
        email=f"{prefix}-learner@x.test",
        company_id=company.id,
        project_id=project.id,
    )
    track = await create_track(db_session, f"{prefix} Track")
    module = await create_module(db_session, track, f"{prefix} Module")
    lesson = await create_lesson(db_session, module, f"{prefix} Lesson")
    feedback = Feedback(user_id=learner.id, lesson_id=lesson.id, message="Add an example please")
    db_session.add(feedback)
    await db_session.commit()
    await db_session.refresh(feedback)
    return project, admin, feedback


class TestSuggestTriage:
    async def test_writes_suggestion_and_returns_counts(
        self,
        triage_client: Callable[[FakeTriageLlm], AsyncClient],
        db_session: AsyncSession,
        test_settings: Settings,
    ) -> None:
        _project, admin, feedback = await _seed(db_session, "triage-ok")
        llm = FakeTriageLlm({"suggested_status": "accepted", "rationale": "Actionable ask."})
        client = triage_client(llm)

        resp = await client.post(
            "/api/admin/feedback/suggest-triage", headers=auth_headers(admin, test_settings)
        )

        assert resp.status_code == 200
        assert resp.json() == {"suggested": 1, "failed": 0, "remaining": 0}
        row = (
            await db_session.execute(select(Feedback).where(Feedback.id == feedback.id))
        ).scalar_one()
        assert row.ai_suggested_status == "accepted"
        assert row.ai_rationale == "Actionable ask."
        assert row.ai_suggested_at is not None
        # The real disposition is untouched.
        assert row.status == "new"

    async def test_second_run_is_a_no_op(
        self,
        triage_client: Callable[[FakeTriageLlm], AsyncClient],
        db_session: AsyncSession,
        test_settings: Settings,
    ) -> None:
        _project, admin, _feedback = await _seed(db_session, "triage-idem")
        llm = FakeTriageLlm({"suggested_status": "accepted", "rationale": "Actionable."})
        client = triage_client(llm)
        headers = auth_headers(admin, test_settings)

        await client.post("/api/admin/feedback/suggest-triage", headers=headers)
        resp = await client.post("/api/admin/feedback/suggest-triage", headers=headers)

        assert resp.json() == {"suggested": 0, "failed": 0, "remaining": 0}
        assert llm.calls == 1

    async def test_limit_bounds_the_run(
        self,
        triage_client: Callable[[FakeTriageLlm], AsyncClient],
        db_session: AsyncSession,
        test_settings: Settings,
    ) -> None:
        _project, admin, feedback = await _seed(db_session, "triage-limit")
        db_session.add(
            Feedback(user_id=feedback.user_id, lesson_id=feedback.lesson_id, message="second")
        )
        await db_session.commit()
        llm = FakeTriageLlm({"suggested_status": "dismissed", "rationale": "Off topic."})
        client = triage_client(llm)

        resp = await client.post(
            "/api/admin/feedback/suggest-triage?limit=1",
            headers=auth_headers(admin, test_settings),
        )

        assert resp.json() == {"suggested": 1, "failed": 0, "remaining": 1}

    async def test_bad_limit_is_422(
        self,
        triage_client: Callable[[FakeTriageLlm], AsyncClient],
        db_session: AsyncSession,
        test_settings: Settings,
    ) -> None:
        _project, admin, _feedback = await _seed(db_session, "triage-422")
        client = triage_client(FakeTriageLlm({"suggested_status": "accepted", "rationale": "x"}))

        resp = await client.post(
            "/api/admin/feedback/suggest-triage?limit=99",
            headers=auth_headers(admin, test_settings),
        )

        assert resp.status_code == 422

    async def test_a_failed_row_does_not_come_back_on_the_next_run(
        self,
        triage_client: Callable[[FakeTriageLlm], AsyncClient],
        db_session: AsyncSession,
        test_settings: Settings,
    ) -> None:
        _project, admin, feedback = await _seed(db_session, "triage-poison")
        # An unusable enum value fails validation for this row every time.
        llm = FakeTriageLlm({"suggested_status": "maybe", "rationale": "nope"})
        client = triage_client(llm)
        headers = auth_headers(admin, test_settings)

        first = await client.post("/api/admin/feedback/suggest-triage", headers=headers)
        second = await client.post("/api/admin/feedback/suggest-triage", headers=headers)

        assert first.json() == {"suggested": 0, "failed": 1, "remaining": 0}
        # The second run finds nothing to do — no repeat model call, no starvation.
        assert second.json() == {"suggested": 0, "failed": 0, "remaining": 0}
        assert llm.calls == 1
        row = (
            await db_session.execute(select(Feedback).where(Feedback.id == feedback.id))
        ).scalar_one()
        assert row.ai_suggested_at is not None
        assert row.ai_suggested_status is None
        assert row.status == "new"

    async def test_404_when_llm_unconfigured(
        self, client: AsyncClient, db_session: AsyncSession, test_settings: Settings
    ) -> None:
        # The plain conftest `client` uses the real DI chain with llm=None.
        _project, admin, _feedback = await _seed(db_session, "triage-off")

        resp = await client.post(
            "/api/admin/feedback/suggest-triage", headers=auth_headers(admin, test_settings)
        )

        assert resp.status_code == 404
        assert resp.json()["error"]["code"] == "not_found"


class TestQueueExposesTheSuggestion:
    async def test_ai_fields_on_the_admin_list(
        self,
        triage_client: Callable[[FakeTriageLlm], AsyncClient],
        db_session: AsyncSession,
        test_settings: Settings,
    ) -> None:
        _project, admin, _feedback = await _seed(db_session, "triage-list")
        client = triage_client(
            FakeTriageLlm({"suggested_status": "accepted", "rationale": "Names a gap."})
        )
        headers = auth_headers(admin, test_settings)

        await client.post("/api/admin/feedback/suggest-triage", headers=headers)
        item = (await client.get("/api/admin/feedback", headers=headers)).json()["items"][0]

        assert item["ai_suggested_status"] == "accepted"
        assert item["ai_rationale"] == "Names a gap."
        assert item["ai_suggested_at"] is not None
        assert item["status"] == "new"

    async def test_ai_fields_are_null_before_a_run(
        self, client: AsyncClient, db_session: AsyncSession, test_settings: Settings
    ) -> None:
        _project, admin, _feedback = await _seed(db_session, "triage-null")

        item = (
            await client.get("/api/admin/feedback", headers=auth_headers(admin, test_settings))
        ).json()["items"][0]

        assert item["ai_suggested_status"] is None
        assert item["ai_rationale"] is None
        assert item["ai_suggested_at"] is None


class TestProjectScope:
    async def test_project_filter_limits_the_run(
        self,
        triage_client: Callable[[FakeTriageLlm], AsyncClient],
        db_session: AsyncSession,
        test_settings: Settings,
    ) -> None:
        project_a, admin, _feedback_a = await _seed(db_session, "triage-scope-a")
        _project_b, _admin_b, _feedback_b = await _seed(db_session, "triage-scope-b")
        client = triage_client(
            FakeTriageLlm({"suggested_status": "accepted", "rationale": "Actionable."})
        )

        resp = await client.post(
            f"/api/admin/feedback/suggest-triage?project_id={project_a.id}",
            headers=auth_headers(admin, test_settings),
        )

        assert resp.json() == {"suggested": 1, "failed": 0, "remaining": 0}
        # The other project's item was never touched.
        others = (
            (await db_session.execute(select(Feedback).where(Feedback.ai_suggested_at.is_(None))))
            .scalars()
            .all()
        )
        assert len(others) == 1

    async def test_unknown_project_suggests_nothing(
        self,
        triage_client: Callable[[FakeTriageLlm], AsyncClient],
        db_session: AsyncSession,
        test_settings: Settings,
    ) -> None:
        _project, admin, _feedback = await _seed(db_session, "triage-scope-none")
        client = triage_client(
            FakeTriageLlm({"suggested_status": "accepted", "rationale": "Actionable."})
        )

        resp = await client.post(
            f"/api/admin/feedback/suggest-triage?project_id={uuid.uuid4()}",
            headers=auth_headers(admin, test_settings),
        )

        assert resp.json() == {"suggested": 0, "failed": 0, "remaining": 0}
