"""The four /api/admin/content-improvement endpoints.

test_settings.llm is None (conftest keeps LLM__* out of the hermetic test
settings), so the real DI chain resolves get_content_improvement_service to
None and every route 404s "not configured" — that is the feature flag working.
`improvement_client` overrides it with a real service (repositories bound to
db_session) wired to a fake LLM, mirroring test_chat.py's `chat_client` and
Plan B's `triage_client` factory-fixture pattern.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

import anthropic
import httpx2
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from src.core.dependencies.content_ai import get_content_improvement_service
from src.core.dependencies.database import get_session
from src.core.dependencies.settings import get_settings
from src.db.models import CalibrationNote, Feedback, Lesson, LessonContentProposal
from src.main import app
from src.repositories.calibration_note_repository import CalibrationNoteRepository
from src.repositories.content_repository import ContentRepository
from src.repositories.feedback_repository import FeedbackRepository
from src.repositories.proposal_repository import ProposalRepository
from src.schemas.admin_proposals import MAX_LESSONS_PER_RUN
from src.services.content_improvement_service import ContentImprovementService
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

_BASE_BLOCKS = [{"id": "b1", "type": "paragraph", "text": "Old text."}]
_GOOD_RESULT = {
    "proposed_blocks": [
        {"id": "b1", "type": "paragraph", "text": "New, clearer text."},
        {"id": "b2", "type": "paragraph", "text": "Here is a worked example."},
    ],
    "summary": "Reworded the opening and added the example the learner asked for.",
}
_CRITIQUE_RESULT = {
    "what_agent_got_wrong": "I added a second paragraph where one would have covered it.",
    "what_admin_preferred": "A single tightened paragraph.",
    "calibration_notes": ["Prefer one tightened paragraph over splitting a short point in two."],
}


class FakeImprovementLlm:
    """`result` scripts the drafting call; `critique_result`, when given, scripts
    the learn-card call. The two are told apart by the schema's tool name
    (`propose_lesson_revision` vs `critique_own_draft`), so one fake serves both
    endpoints instead of needing a second class."""

    def __init__(
        self, result: dict[str, Any], critique_result: dict[str, Any] | None = None
    ) -> None:
        self.result = result
        self.critique_result = critique_result
        self.calls = 0
        self.critique_calls = 0

    async def complete_structured(
        self, *, system: str, prompt: str, schema: Any, max_tokens: int
    ) -> tuple[dict[str, Any], LlmUsage]:
        if getattr(schema, "name", None) == "critique_own_draft":
            assert self.critique_result is not None, "critique called without a scripted result"
            self.critique_calls += 1
            return dict(self.critique_result), LlmUsage(input_tokens=500, output_tokens=200)
        self.calls += 1
        return dict(self.result), LlmUsage(input_tokens=800, output_tokens=400)


@pytest_asyncio.fixture
async def improvement_client(
    db_session: AsyncSession, test_settings: Settings
) -> AsyncGenerator[Callable[[FakeImprovementLlm], AsyncClient]]:
    clients: list[AsyncClient] = []

    def _make(fake_llm: FakeImprovementLlm) -> AsyncClient:
        async def _override_session() -> AsyncGenerator[AsyncSession]:
            yield db_session

        service = ContentImprovementService(
            ProposalRepository(db_session),
            FeedbackRepository(db_session),
            ContentRepository(db_session),
            fake_llm,  # ty: ignore[invalid-argument-type]
            CalibrationNoteRepository(db_session),
        )
        app.dependency_overrides[get_session] = _override_session
        app.dependency_overrides[get_settings] = lambda: test_settings
        app.dependency_overrides[get_content_improvement_service] = lambda: service
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
    lesson = await create_lesson(
        db_session, module, f"{prefix} Lesson", content_blocks=list(_BASE_BLOCKS)
    )
    feedback = Feedback(
        user_id=learner.id,
        lesson_id=lesson.id,
        message="Please add a worked example",
        status="accepted",
    )
    db_session.add(feedback)
    await db_session.commit()
    await db_session.refresh(feedback)
    return admin, lesson, feedback


def _run_body(*lessons: Any) -> dict[str, list[str]]:
    """The picker's payload: draft exactly these lessons and nothing else."""
    return {"lesson_ids": [str(lesson.id) for lesson in lessons]}


class TestRun:
    async def test_creates_a_pending_proposal(
        self,
        improvement_client: Callable[[FakeImprovementLlm], AsyncClient],
        db_session: AsyncSession,
        test_settings: Settings,
    ) -> None:
        admin, lesson, feedback = await _seed(db_session, "ci-run")
        client = improvement_client(FakeImprovementLlm(_GOOD_RESULT))

        resp = await client.post(
            "/api/admin/content-improvement/run",
            headers=auth_headers(admin, test_settings),
            json=_run_body(lesson),
        )

        assert resp.status_code == 200
        assert resp.json() == {
            "proposed": 1,
            "skipped": 0,
            "deferred": 0,
            "not_queued": 0,
        }
        row = (await db_session.execute(select(LessonContentProposal))).scalars().one()
        assert row.status == "pending"
        assert row.lesson_id == lesson.id
        assert row.base_blocks == _BASE_BLOCKS
        assert row.proposed_blocks == _GOOD_RESULT["proposed_blocks"]
        assert row.source_feedback_ids == [str(feedback.id)]
        # Drafting must not have touched the live lesson.
        live = (await db_session.execute(select(Lesson).where(Lesson.id == lesson.id))).scalar_one()
        assert live.content_blocks == _BASE_BLOCKS

    async def test_a_second_run_is_idempotent(
        self,
        improvement_client: Callable[[FakeImprovementLlm], AsyncClient],
        db_session: AsyncSession,
        test_settings: Settings,
    ) -> None:
        admin, lesson, _feedback = await _seed(db_session, "ci-idem")
        llm = FakeImprovementLlm(_GOOD_RESULT)
        client = improvement_client(llm)
        headers = auth_headers(admin, test_settings)

        await client.post(
            "/api/admin/content-improvement/run", headers=headers, json=_run_body(lesson)
        )
        second = await client.post(
            "/api/admin/content-improvement/run", headers=headers, json=_run_body(lesson)
        )

        assert second.json() == {
            "proposed": 0,
            "skipped": 0,
            "deferred": 0,
            "not_queued": 1,
        }
        assert llm.calls == 1

    async def test_new_and_dismissed_feedback_is_never_drafted(
        self,
        improvement_client: Callable[[FakeImprovementLlm], AsyncClient],
        db_session: AsyncSession,
        test_settings: Settings,
    ) -> None:
        admin, lesson, feedback = await _seed(db_session, "ci-status")
        feedback.status = "new"
        db_session.add(
            Feedback(
                user_id=feedback.user_id,
                lesson_id=lesson.id,
                message="off topic",
                status="dismissed",
            )
        )
        await db_session.commit()
        llm = FakeImprovementLlm(_GOOD_RESULT)
        client = improvement_client(llm)

        resp = await client.post(
            "/api/admin/content-improvement/run",
            headers=auth_headers(admin, test_settings),
            json=_run_body(lesson),
        )

        assert resp.json() == {
            "proposed": 0,
            "skipped": 0,
            "deferred": 0,
            "not_queued": 1,
        }
        assert llm.calls == 0

    async def test_too_many_lessons_in_one_run_is_422(
        self,
        improvement_client: Callable[[FakeImprovementLlm], AsyncClient],
        db_session: AsyncSession,
        test_settings: Settings,
    ) -> None:
        # The cap is the run's time budget, so it has to be refused at the edge
        # rather than truncated silently: an admin who ticked ten lessons must
        # not have four of them silently dropped from the batch.
        admin, _lesson, _feedback = await _seed(db_session, "ci-422")
        client = improvement_client(FakeImprovementLlm(_GOOD_RESULT))

        resp = await client.post(
            "/api/admin/content-improvement/run",
            headers=auth_headers(admin, test_settings),
            json={"lesson_ids": [str(uuid.uuid4()) for _ in range(MAX_LESSONS_PER_RUN + 1)]},
        )

        assert resp.status_code == 422

    async def test_an_empty_selection_is_422(
        self,
        improvement_client: Callable[[FakeImprovementLlm], AsyncClient],
        db_session: AsyncSession,
        test_settings: Settings,
    ) -> None:
        admin, _lesson, _feedback = await _seed(db_session, "ci-422empty")
        llm = FakeImprovementLlm(_GOOD_RESULT)
        client = improvement_client(llm)

        resp = await client.post(
            "/api/admin/content-improvement/run",
            headers=auth_headers(admin, test_settings),
            json={"lesson_ids": []},
        )

        assert resp.status_code == 422
        assert llm.calls == 0

    async def test_an_unqueued_lesson_is_reported_not_404(
        self,
        improvement_client: Callable[[FakeImprovementLlm], AsyncClient],
        db_session: AsyncSession,
        test_settings: Settings,
    ) -> None:
        # Two admins with the picker open: the other one already drafted it.
        # Failing the whole batch over that would be worse than reporting it.
        admin, lesson, _feedback = await _seed(db_session, "ci-gone")
        llm = FakeImprovementLlm(_GOOD_RESULT)
        client = improvement_client(llm)
        headers = auth_headers(admin, test_settings)

        resp = await client.post(
            "/api/admin/content-improvement/run",
            headers=headers,
            json={"lesson_ids": [str(lesson.id), str(uuid.uuid4())]},
        )

        assert resp.status_code == 200
        assert resp.json()["proposed"] == 1
        assert resp.json()["not_queued"] == 1
        assert llm.calls == 1

    async def test_404_when_llm_unconfigured(
        self, client: AsyncClient, db_session: AsyncSession, test_settings: Settings
    ) -> None:
        # The plain conftest `client` uses the real DI chain with llm=None.
        admin, lesson, _feedback = await _seed(db_session, "ci-off")

        resp = await client.post(
            "/api/admin/content-improvement/run",
            headers=auth_headers(admin, test_settings),
            json=_run_body(lesson),
        )

        assert resp.status_code == 404
        assert resp.json()["error"]["code"] == "not_found"


class FakeOverloadedLlm:
    """Anthropic at capacity. Raises the real SDK exception rather than a stand-in
    so the run's transient/terminal split is exercised through
    `is_transient_provider_error`, not through a shape the SDK never produces."""

    def __init__(self) -> None:
        self.calls = 0

    async def complete_structured(
        self, *, system: str, prompt: str, schema: Any, max_tokens: int
    ) -> tuple[dict[str, Any], LlmUsage]:
        self.calls += 1
        request = httpx2.Request("POST", "https://api.anthropic.com/v1/messages")
        raise anthropic.OverloadedError(
            "Overloaded", response=httpx2.Response(529, request=request), body=None
        )


class TestProviderOverloaded:
    async def test_a_529_writes_no_proposal_and_keeps_the_lesson_queued(
        self,
        improvement_client: Callable[[Any], AsyncClient],
        db_session: AsyncSession,
        test_settings: Settings,
    ) -> None:
        # The regression this whole shape exists for. Before, a 529 stored a
        # `failed` proposal, which covered the lesson's feedback and forced the
        # admin to click "Dismiss and retry later" on every card. Now it writes
        # nothing, so the lesson is still in the picker and a retry just works.
        admin, lesson, feedback = await _seed(db_session, "ci-529")
        llm = FakeOverloadedLlm()
        client = improvement_client(llm)
        headers = auth_headers(admin, test_settings)

        resp = await client.post(
            "/api/admin/content-improvement/run", headers=headers, json=_run_body(lesson)
        )

        assert resp.status_code == 200
        assert resp.json() == {
            "proposed": 0,
            "skipped": 0,
            "deferred": 1,
            "not_queued": 0,
        }
        assert llm.calls == 1
        # No row of ANY status — a `failed` one here is the bug.
        assert (await db_session.execute(select(LessonContentProposal))).scalars().all() == []
        # And the lesson is still offered, with its feedback still uncovered.
        queue = (await client.get("/api/admin/content-improvement/queue", headers=headers)).json()
        assert [item["lesson_id"] for item in queue["items"]] == [str(lesson.id)]
        assert queue["items"][0]["feedback_count"] == 1
        await db_session.refresh(feedback)
        assert feedback.status == "accepted"


class TestDraftQueue:
    """`GET /queue` is the picker's option list, so it has to agree with what
    `POST /run` will actually accept — a lesson listed here must be draftable,
    and a lesson already covered must not appear."""

    async def test_lists_a_lesson_awaiting_a_draft_with_its_context(
        self,
        improvement_client: Callable[[FakeImprovementLlm], AsyncClient],
        db_session: AsyncSession,
        test_settings: Settings,
    ) -> None:
        admin, lesson, _feedback = await _seed(db_session, "ci-queue")
        client = improvement_client(FakeImprovementLlm(_GOOD_RESULT))

        body = (
            await client.get(
                "/api/admin/content-improvement/queue",
                headers=auth_headers(admin, test_settings),
            )
        ).json()

        assert body["total"] == 1
        item = body["items"][0]
        assert item["lesson_id"] == str(lesson.id)
        assert item["lesson_title"] == lesson.title
        assert item["module_title"] == "ci-queue Module"
        assert item["track_name"] == "ci-queue Track"
        assert item["feedback_count"] == 1

    async def test_a_drafted_lesson_leaves_the_queue(
        self,
        improvement_client: Callable[[FakeImprovementLlm], AsyncClient],
        db_session: AsyncSession,
        test_settings: Settings,
    ) -> None:
        # The picker must not keep offering work that is already done, or the
        # admin spends a click discovering it via not_queued.
        admin, lesson, _feedback = await _seed(db_session, "ci-queue-drained")
        client = improvement_client(FakeImprovementLlm(_GOOD_RESULT))
        headers = auth_headers(admin, test_settings)

        before = (await client.get("/api/admin/content-improvement/queue", headers=headers)).json()
        await client.post(
            "/api/admin/content-improvement/run", headers=headers, json=_run_body(lesson)
        )
        after = (await client.get("/api/admin/content-improvement/queue", headers=headers)).json()

        assert before["total"] == 1
        assert after["total"] == 0

    async def test_the_queue_route_is_not_shadowed_by_the_detail_route(
        self,
        improvement_client: Callable[[FakeImprovementLlm], AsyncClient],
        db_session: AsyncSession,
        test_settings: Settings,
    ) -> None:
        # `/queue` sits next to `GET /{proposal_id}`, so declaration order is
        # load-bearing: reordered, "queue" parses as a uuid and this 422s.
        admin, _lesson, _feedback = await _seed(db_session, "ci-queue-route")
        client = improvement_client(FakeImprovementLlm(_GOOD_RESULT))

        resp = await client.get(
            "/api/admin/content-improvement/queue", headers=auth_headers(admin, test_settings)
        )

        assert resp.status_code == 200
        assert "items" in resp.json()


class TestQueueReads:
    async def test_list_carries_context_and_filters_by_status(
        self,
        improvement_client: Callable[[FakeImprovementLlm], AsyncClient],
        db_session: AsyncSession,
        test_settings: Settings,
    ) -> None:
        admin, lesson, _feedback = await _seed(db_session, "ci-list")
        client = improvement_client(FakeImprovementLlm(_GOOD_RESULT))
        headers = auth_headers(admin, test_settings)
        await client.post(
            "/api/admin/content-improvement/run", headers=headers, json=_run_body(lesson)
        )

        body = (await client.get("/api/admin/content-improvement", headers=headers)).json()

        assert body["total"] == 1
        item = body["items"][0]
        assert item["lesson_id"] == str(lesson.id)
        assert item["lesson_title"] == lesson.title
        assert item["module_title"] == "ci-list Module"
        assert item["track_name"] == "ci-list Track"
        assert item["status"] == "pending"
        assert item["source_feedback_count"] == 1
        assert item["summary"] == _GOOD_RESULT["summary"]
        # The list is a queue, not the diff — heavy block arrays stay out of it.
        assert "proposed_blocks" not in item

        empty = await client.get("/api/admin/content-improvement?status=approved", headers=headers)
        assert empty.json()["total"] == 0

    async def test_detail_carries_both_block_arrays_and_the_source_feedback(
        self,
        improvement_client: Callable[[FakeImprovementLlm], AsyncClient],
        db_session: AsyncSession,
        test_settings: Settings,
    ) -> None:
        admin, lesson, feedback = await _seed(db_session, "ci-detail")
        client = improvement_client(FakeImprovementLlm(_GOOD_RESULT))
        headers = auth_headers(admin, test_settings)
        await client.post(
            "/api/admin/content-improvement/run", headers=headers, json=_run_body(lesson)
        )
        proposal_id = (await client.get("/api/admin/content-improvement", headers=headers)).json()[
            "items"
        ][0]["id"]

        detail = (
            await client.get(f"/api/admin/content-improvement/{proposal_id}", headers=headers)
        ).json()

        assert detail["lesson_title"] == lesson.title
        assert detail["base_blocks"] == _BASE_BLOCKS
        assert detail["proposed_blocks"] == _GOOD_RESULT["proposed_blocks"]
        assert [f["message"] for f in detail["source_feedback"]] == [feedback.message]

    async def test_unknown_detail_id_is_404(
        self,
        improvement_client: Callable[[FakeImprovementLlm], AsyncClient],
        db_session: AsyncSession,
        test_settings: Settings,
    ) -> None:
        admin, lesson, _feedback = await _seed(db_session, "ci-detail404")
        client = improvement_client(FakeImprovementLlm(_GOOD_RESULT))

        resp = await client.get(
            f"/api/admin/content-improvement/{uuid.uuid4()}",
            headers=auth_headers(admin, test_settings),
        )

        assert resp.status_code == 404


class TestReview:
    async def _draft(self, client: AsyncClient, headers: dict[str, str], lesson: Any) -> str:
        await client.post(
            "/api/admin/content-improvement/run", headers=headers, json=_run_body(lesson)
        )
        body = (await client.get("/api/admin/content-improvement", headers=headers)).json()
        return body["items"][0]["id"]

    async def test_approve_writes_the_lesson(
        self,
        improvement_client: Callable[[FakeImprovementLlm], AsyncClient],
        db_session: AsyncSession,
        test_settings: Settings,
    ) -> None:
        admin, lesson, _feedback = await _seed(db_session, "ci-approve")
        client = improvement_client(FakeImprovementLlm(_GOOD_RESULT))
        headers = auth_headers(admin, test_settings)
        proposal_id = await self._draft(client, headers, lesson)

        resp = await client.post(
            f"/api/admin/content-improvement/{proposal_id}/review",
            json={"decision": "approve"},
            headers=headers,
        )

        assert resp.status_code == 200
        assert resp.json() == {"status": "approved"}
        # expire_all() + re-querying by lesson.id would touch the now-expired PK
        # attribute synchronously while building the WHERE clause, which raises
        # sqlalchemy.exc.MissingGreenlet on an AsyncSession. refresh() is the
        # async-safe way to pull the row's current DB state onto this object.
        await db_session.refresh(lesson)
        assert lesson.content_blocks == _GOOD_RESULT["proposed_blocks"]
        row = (await db_session.execute(select(LessonContentProposal))).scalars().one()
        assert row.status == "approved"
        assert row.reviewed_by == admin.id
        assert row.reviewed_at is not None

    async def test_reject_leaves_the_lesson_alone_and_frees_the_feedback(
        self,
        improvement_client: Callable[[FakeImprovementLlm], AsyncClient],
        db_session: AsyncSession,
        test_settings: Settings,
    ) -> None:
        admin, lesson, _feedback = await _seed(db_session, "ci-reject")
        llm = FakeImprovementLlm(_GOOD_RESULT)
        client = improvement_client(llm)
        headers = auth_headers(admin, test_settings)
        proposal_id = await self._draft(client, headers, lesson)

        resp = await client.post(
            f"/api/admin/content-improvement/{proposal_id}/review",
            json={"decision": "reject"},
            headers=headers,
        )

        assert resp.json() == {"status": "rejected"}
        await db_session.refresh(lesson)
        assert lesson.content_blocks == _BASE_BLOCKS
        # A rejected proposal no longer covers its feedback, so a later run can
        # try again (design doc, "Applying an approved proposal").
        again = await client.post(
            "/api/admin/content-improvement/run", headers=headers, json=_run_body(lesson)
        )
        assert again.json()["proposed"] == 1
        assert llm.calls == 2

    async def test_a_lesson_edited_underneath_supersedes_and_409s(
        self,
        improvement_client: Callable[[FakeImprovementLlm], AsyncClient],
        db_session: AsyncSession,
        test_settings: Settings,
    ) -> None:
        admin, lesson, _feedback = await _seed(db_session, "ci-stale")
        client = improvement_client(FakeImprovementLlm(_GOOD_RESULT))
        headers = auth_headers(admin, test_settings)
        proposal_id = await self._draft(client, headers, lesson)

        edited = [{"id": "b1", "type": "paragraph", "text": "An admin edited this."}]
        lesson.content_blocks = edited
        db_session.add(lesson)
        await db_session.commit()

        resp = await client.post(
            f"/api/admin/content-improvement/{proposal_id}/review",
            json={"decision": "approve"},
            headers=headers,
        )

        assert resp.status_code == 409
        await db_session.refresh(lesson)
        assert lesson.content_blocks == edited
        row = (await db_session.execute(select(LessonContentProposal))).scalars().one()
        assert row.status == "superseded"

    async def test_reviewing_twice_is_409_and_bad_decision_is_422(
        self,
        improvement_client: Callable[[FakeImprovementLlm], AsyncClient],
        db_session: AsyncSession,
        test_settings: Settings,
    ) -> None:
        admin, lesson, _feedback = await _seed(db_session, "ci-twice")
        client = improvement_client(FakeImprovementLlm(_GOOD_RESULT))
        headers = auth_headers(admin, test_settings)
        proposal_id = await self._draft(client, headers, lesson)

        await client.post(
            f"/api/admin/content-improvement/{proposal_id}/review",
            json={"decision": "reject"},
            headers=headers,
        )
        second = await client.post(
            f"/api/admin/content-improvement/{proposal_id}/review",
            json={"decision": "reject"},
            headers=headers,
        )
        assert second.status_code == 409

        bad = await client.post(
            f"/api/admin/content-improvement/{proposal_id}/review",
            json={"decision": "publish"},
            headers=headers,
        )
        assert bad.status_code == 422

    async def test_unknown_proposal_is_404(
        self,
        improvement_client: Callable[[FakeImprovementLlm], AsyncClient],
        db_session: AsyncSession,
        test_settings: Settings,
    ) -> None:
        admin, lesson, _feedback = await _seed(db_session, "ci-404")
        client = improvement_client(FakeImprovementLlm(_GOOD_RESULT))

        resp = await client.post(
            f"/api/admin/content-improvement/{uuid.uuid4()}/review",
            json={"decision": "approve"},
            headers=auth_headers(admin, test_settings),
        )

        assert resp.status_code == 404

    async def test_accepting_with_edits_applies_the_admin_version(
        self,
        improvement_client: Callable[[FakeImprovementLlm], AsyncClient],
        db_session: AsyncSession,
        test_settings: Settings,
    ) -> None:
        admin, lesson, _feedback = await _seed(db_session, "ci-edited")
        client = improvement_client(FakeImprovementLlm(_GOOD_RESULT))
        headers = auth_headers(admin, test_settings)
        proposal_id = await self._draft(client, headers, lesson)
        admin_blocks = [{"id": "b1", "type": "paragraph", "text": "My own wording."}]

        resp = await client.post(
            f"/api/admin/content-improvement/{proposal_id}/review",
            json={"decision": "approve", "edited_blocks": admin_blocks},
            headers=headers,
        )

        assert resp.status_code == 200
        assert resp.json() == {"status": "approved"}
        await db_session.refresh(lesson)
        assert lesson.content_blocks == admin_blocks
        row = (await db_session.execute(select(LessonContentProposal))).scalars().one()
        assert row.edited_blocks == admin_blocks
        # The agent's own draft is preserved for the comparison.
        assert row.proposed_blocks == _GOOD_RESULT["proposed_blocks"]

    async def test_accepting_untouched_leaves_no_delta(
        self,
        improvement_client: Callable[[FakeImprovementLlm], AsyncClient],
        db_session: AsyncSession,
        test_settings: Settings,
    ) -> None:
        admin, lesson, _feedback = await _seed(db_session, "ci-untouched")
        client = improvement_client(FakeImprovementLlm(_GOOD_RESULT))
        headers = auth_headers(admin, test_settings)
        proposal_id = await self._draft(client, headers, lesson)

        await client.post(
            f"/api/admin/content-improvement/{proposal_id}/review",
            json={"decision": "approve"},
            headers=headers,
        )

        await db_session.refresh(lesson)
        assert lesson.content_blocks == _GOOD_RESULT["proposed_blocks"]
        row = (await db_session.execute(select(LessonContentProposal))).scalars().one()
        assert row.edited_blocks is None

    async def test_invalid_admin_edits_are_refused_and_nothing_lands(
        self,
        improvement_client: Callable[[FakeImprovementLlm], AsyncClient],
        db_session: AsyncSession,
        test_settings: Settings,
    ) -> None:
        admin, lesson, _feedback = await _seed(db_session, "ci-badedit")
        client = improvement_client(FakeImprovementLlm(_GOOD_RESULT))
        headers = auth_headers(admin, test_settings)
        proposal_id = await self._draft(client, headers, lesson)

        resp = await client.post(
            f"/api/admin/content-improvement/{proposal_id}/review",
            json={
                "decision": "approve",
                "edited_blocks": [{"id": "b1", "type": "banner", "text": "x"}],
            },
            headers=headers,
        )

        assert resp.status_code == 409
        await db_session.refresh(lesson)
        assert lesson.content_blocks == _BASE_BLOCKS
        row = (await db_session.execute(select(LessonContentProposal))).scalars().one()
        assert row.status == "pending"


class TestBadModelOutputNeverPublishes:
    async def test_an_invented_media_block_is_recorded_as_failed(
        self,
        improvement_client: Callable[[FakeImprovementLlm], AsyncClient],
        db_session: AsyncSession,
        test_settings: Settings,
    ) -> None:
        admin, lesson, _feedback = await _seed(db_session, "ci-media")
        client = improvement_client(
            FakeImprovementLlm(
                {
                    "proposed_blocks": [
                        {"id": "b1", "type": "paragraph", "text": "New text."},
                        {
                            "id": "b2",
                            "type": "image",
                            "blob_path": "images/made-up.png",
                            "alt": "x",
                        },
                    ],
                    "summary": "s",
                }
            )
        )
        headers = auth_headers(admin, test_settings)

        resp = await client.post(
            "/api/admin/content-improvement/run", headers=headers, json=_run_body(lesson)
        )

        assert resp.json() == {
            "proposed": 0,
            "skipped": 1,
            "deferred": 0,
            "not_queued": 0,
        }
        row = (await db_session.execute(select(LessonContentProposal))).scalars().one()
        assert row.status == "failed"
        assert "made-up.png" in row.summary
        await db_session.refresh(lesson)
        assert lesson.content_blocks == _BASE_BLOCKS


class TestLearnCard:
    async def _accept_with_edits(
        self,
        client: AsyncClient,
        headers: dict[str, str],
        lesson: Any,
        edited_blocks: list[dict[str, Any]],
    ) -> str:
        await client.post(
            "/api/admin/content-improvement/run", headers=headers, json=_run_body(lesson)
        )
        body = (await client.get("/api/admin/content-improvement", headers=headers)).json()
        proposal_id = body["items"][0]["id"]
        await client.post(
            f"/api/admin/content-improvement/{proposal_id}/review",
            json={"decision": "approve", "edited_blocks": edited_blocks},
            headers=headers,
        )
        return proposal_id

    async def _accept_untouched(
        self, client: AsyncClient, headers: dict[str, str], lesson: Any
    ) -> str:
        await client.post(
            "/api/admin/content-improvement/run", headers=headers, json=_run_body(lesson)
        )
        body = (await client.get("/api/admin/content-improvement", headers=headers)).json()
        proposal_id = body["items"][0]["id"]
        await client.post(
            f"/api/admin/content-improvement/{proposal_id}/review",
            json={"decision": "approve"},
            headers=headers,
        )
        return proposal_id

    async def test_a_learn_card_is_generated_and_persisted(
        self,
        improvement_client: Callable[[FakeImprovementLlm], AsyncClient],
        db_session: AsyncSession,
        test_settings: Settings,
    ) -> None:
        admin, lesson, _feedback = await _seed(db_session, "ci-learn")
        client = improvement_client(FakeImprovementLlm(_GOOD_RESULT, _CRITIQUE_RESULT))
        headers = auth_headers(admin, test_settings)
        admin_blocks = [{"id": "b1", "type": "paragraph", "text": "My own wording."}]
        proposal_id = await self._accept_with_edits(client, headers, lesson, admin_blocks)

        resp = await client.post(
            f"/api/admin/content-improvement/{proposal_id}/critique", headers=headers
        )

        assert resp.status_code == 200
        body = resp.json()
        assert body["critique_agent_wrong"] == _CRITIQUE_RESULT["what_agent_got_wrong"]
        assert body["critique_admin_preferred"] == _CRITIQUE_RESULT["what_admin_preferred"]
        assert [n["note"] for n in body["calibration_notes"]] == _CRITIQUE_RESULT[
            "calibration_notes"
        ]
        assert all(n["status"] == "suggested" for n in body["calibration_notes"])

        row = (await db_session.execute(select(LessonContentProposal))).scalars().one()
        assert row.critique_agent_wrong == _CRITIQUE_RESULT["what_agent_got_wrong"]
        assert row.critique_admin_preferred == _CRITIQUE_RESULT["what_admin_preferred"]
        assert row.critiqued_at is not None
        # The notes are queryable as `suggested` rows tied back to this proposal.
        notes = (await db_session.execute(select(CalibrationNote))).scalars().all()
        assert len(notes) == 1
        assert notes[0].status == "suggested"
        assert notes[0].source_proposal_id == uuid.UUID(proposal_id)
        assert notes[0].note == _CRITIQUE_RESULT["calibration_notes"][0]

    async def test_accepted_untouched_has_nothing_to_critique(
        self,
        improvement_client: Callable[[FakeImprovementLlm], AsyncClient],
        db_session: AsyncSession,
        test_settings: Settings,
    ) -> None:
        admin, lesson, _feedback = await _seed(db_session, "ci-learn-untouched")
        client = improvement_client(FakeImprovementLlm(_GOOD_RESULT, _CRITIQUE_RESULT))
        headers = auth_headers(admin, test_settings)
        proposal_id = await self._accept_untouched(client, headers, lesson)

        resp = await client.post(
            f"/api/admin/content-improvement/{proposal_id}/critique", headers=headers
        )

        assert resp.status_code == 409
        notes = (await db_session.execute(select(CalibrationNote))).scalars().all()
        assert notes == []

    async def test_a_second_critique_is_409_and_does_not_duplicate_notes(
        self,
        improvement_client: Callable[[FakeImprovementLlm], AsyncClient],
        db_session: AsyncSession,
        test_settings: Settings,
    ) -> None:
        admin, lesson, _feedback = await _seed(db_session, "ci-learn-twice")
        client = improvement_client(FakeImprovementLlm(_GOOD_RESULT, _CRITIQUE_RESULT))
        headers = auth_headers(admin, test_settings)
        admin_blocks = [{"id": "b1", "type": "paragraph", "text": "My own wording."}]
        proposal_id = await self._accept_with_edits(client, headers, lesson, admin_blocks)

        first = await client.post(
            f"/api/admin/content-improvement/{proposal_id}/critique", headers=headers
        )
        second = await client.post(
            f"/api/admin/content-improvement/{proposal_id}/critique", headers=headers
        )

        assert first.status_code == 200
        assert second.status_code == 409
        notes = (await db_session.execute(select(CalibrationNote))).scalars().all()
        assert len(notes) == 1

    async def test_the_learn_card_appears_on_a_later_get(
        self,
        improvement_client: Callable[[FakeImprovementLlm], AsyncClient],
        db_session: AsyncSession,
        test_settings: Settings,
    ) -> None:
        admin, lesson, _feedback = await _seed(db_session, "ci-learn-get")
        client = improvement_client(FakeImprovementLlm(_GOOD_RESULT, _CRITIQUE_RESULT))
        headers = auth_headers(admin, test_settings)
        admin_blocks = [{"id": "b1", "type": "paragraph", "text": "My own wording."}]
        proposal_id = await self._accept_with_edits(client, headers, lesson, admin_blocks)
        await client.post(f"/api/admin/content-improvement/{proposal_id}/critique", headers=headers)

        detail = (
            await client.get(f"/api/admin/content-improvement/{proposal_id}", headers=headers)
        ).json()

        assert detail["edited_blocks"] == admin_blocks
        assert detail["critique_agent_wrong"] == _CRITIQUE_RESULT["what_agent_got_wrong"]
        assert detail["critique_admin_preferred"] == _CRITIQUE_RESULT["what_admin_preferred"]
        assert detail["critiqued_at"] is not None
        assert [n["note"] for n in detail["calibration_notes"]] == _CRITIQUE_RESULT[
            "calibration_notes"
        ]
