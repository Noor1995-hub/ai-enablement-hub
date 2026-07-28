"""The three /api/admin/calibration-notes endpoints.

Unlike test_admin_content_improvement.py this needs no DI override and no fake
LLM: curating notes takes no model, so the router is NOT None-gated on
Settings.llm. The plain conftest `client` fixture (whose session-scoped
test_settings pins llm=None) therefore exercises the real DI chain end to end —
which is exactly what proves the feature keeps working with LLM__* unset.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

import pytest_asyncio

from src.db.models import LessonContentProposal
from src.repositories.calibration_note_repository import CalibrationNoteRepository
from tests.fixtures.auth import auth_headers
from tests.fixtures.factories import create_lesson, create_module, create_track, create_user

if TYPE_CHECKING:
    from httpx import AsyncClient
    from sqlalchemy.ext.asyncio import AsyncSession

    from src.core.configs.settings import Settings
    from src.db.models import CalibrationNote, User

_URL = "/api/admin/calibration-notes"


class Seeded:
    def __init__(self, admin: User, lesson_title: str, notes: list[CalibrationNote]) -> None:
        self.admin = admin
        self.lesson_title = lesson_title
        self.notes = notes


@pytest_asyncio.fixture
async def seeded(db_session: AsyncSession) -> Seeded:
    """An admin plus two `suggested` notes hanging off a real proposal, so the
    list rows carry the source-lesson context the queue renders."""
    admin = await create_user(db_session, email=f"cal-admin-{uuid.uuid4()}@x.test", role="admin")
    track = await create_track(db_session, f"Cal Track {uuid.uuid4()}")
    module = await create_module(db_session, track, "Cal Module")
    lesson = await create_lesson(db_session, module, "Prompting basics")
    proposal = LessonContentProposal(
        lesson_id=lesson.id,
        proposed_blocks=[],
        base_blocks=[],
        source_feedback_ids=[],
        summary="s",
    )
    db_session.add(proposal)
    await db_session.commit()
    await db_session.refresh(proposal)
    notes = await CalibrationNoteRepository(db_session).create_many(
        source_proposal_id=proposal.id,
        notes=["Prefer inline bullets over a card group.", "Do not pad the intro."],
    )
    return Seeded(admin, lesson.title, notes)


def _headers(seeded: Seeded, test_settings: Settings) -> dict[str, str]:
    return auth_headers(seeded.admin, test_settings)


class TestList:
    async def test_returns_the_notes_with_their_source_lesson(
        self, client: AsyncClient, seeded: Seeded, test_settings: Settings
    ) -> None:
        response = await client.get(_URL, headers=_headers(seeded, test_settings))

        assert response.status_code == 200
        body = response.json()
        assert body["total"] == 2
        assert body["limit"] == 25
        assert body["offset"] == 0
        assert {item["note"] for item in body["items"]} == {
            "Prefer inline bullets over a card group.",
            "Do not pad the intro.",
        }
        first = body["items"][0]
        assert first["status"] == "suggested"
        assert first["source_lesson_title"] == "Prompting basics"
        assert first["source_lesson_id"] is not None
        assert first["reviewed_at"] is None

    async def test_filters_by_status(
        self, client: AsyncClient, seeded: Seeded, test_settings: Settings
    ) -> None:
        headers = _headers(seeded, test_settings)
        await client.post(
            f"{_URL}/{seeded.notes[0].id}/review", json={"decision": "approve"}, headers=headers
        )

        approved = await client.get(_URL, params={"status": "approved"}, headers=headers)
        suggested = await client.get(_URL, params={"status": "suggested"}, headers=headers)

        assert approved.status_code == 200
        assert [item["note"] for item in approved.json()["items"]] == [
            "Prefer inline bullets over a card group."
        ]
        assert approved.json()["total"] == 1
        assert suggested.json()["total"] == 1

    async def test_an_unknown_status_is_rejected(
        self, client: AsyncClient, seeded: Seeded, test_settings: Settings
    ) -> None:
        response = await client.get(
            _URL, params={"status": "graduated"}, headers=_headers(seeded, test_settings)
        )

        assert response.status_code == 422

    async def test_limit_is_bounded(
        self, client: AsyncClient, seeded: Seeded, test_settings: Settings
    ) -> None:
        headers = _headers(seeded, test_settings)

        assert (await client.get(_URL, params={"limit": 0}, headers=headers)).status_code == 422
        assert (await client.get(_URL, params={"limit": 101}, headers=headers)).status_code == 422
        paged = await client.get(_URL, params={"limit": 1, "offset": 1}, headers=headers)
        assert paged.status_code == 200
        assert paged.json()["total"] == 2
        assert len(paged.json()["items"]) == 1


class TestReview:
    async def test_approve_then_a_second_approve_conflicts(
        self, client: AsyncClient, seeded: Seeded, test_settings: Settings
    ) -> None:
        headers = _headers(seeded, test_settings)
        path = f"{_URL}/{seeded.notes[0].id}/review"

        first = await client.post(path, json={"decision": "approve"}, headers=headers)
        second = await client.post(path, json={"decision": "approve"}, headers=headers)

        assert first.status_code == 200
        assert first.json() == {"status": "approved"}
        assert second.status_code == 409
        assert second.json()["error"]["code"] == "conflict"

    async def test_reject_stamps_the_reviewer(
        self, client: AsyncClient, seeded: Seeded, db_session: AsyncSession, test_settings: Settings
    ) -> None:
        note = seeded.notes[1]

        response = await client.post(
            f"{_URL}/{note.id}/review",
            json={"decision": "reject"},
            headers=_headers(seeded, test_settings),
        )

        assert response.status_code == 200
        assert response.json() == {"status": "rejected"}
        await db_session.refresh(note)
        assert note.status == "rejected"
        assert note.reviewed_by == seeded.admin.id
        assert note.reviewed_at is not None

    async def test_an_unknown_decision_is_rejected_by_the_schema(
        self, client: AsyncClient, seeded: Seeded, db_session: AsyncSession, test_settings: Settings
    ) -> None:
        note = seeded.notes[0]

        for decision in ("", "APPROVE", "inject"):
            response = await client.post(
                f"{_URL}/{note.id}/review",
                json={"decision": decision},
                headers=_headers(seeded, test_settings),
            )
            assert response.status_code == 422, decision

        await db_session.refresh(note)
        assert note.status == "suggested"

    async def test_an_unknown_note_is_404(
        self, client: AsyncClient, seeded: Seeded, test_settings: Settings
    ) -> None:
        response = await client.post(
            f"{_URL}/{uuid.uuid4()}/review",
            json={"decision": "approve"},
            headers=_headers(seeded, test_settings),
        )

        assert response.status_code == 404
        assert response.json()["error"]["code"] == "not_found"


class TestGraduate:
    async def test_an_approved_note_retires_and_returns_the_paste_ready_line(
        self, client: AsyncClient, seeded: Seeded, db_session: AsyncSession, test_settings: Settings
    ) -> None:
        headers = _headers(seeded, test_settings)
        note = seeded.notes[0]
        await client.post(f"{_URL}/{note.id}/review", json={"decision": "approve"}, headers=headers)

        response = await client.post(f"{_URL}/{note.id}/graduate", headers=headers)

        assert response.status_code == 200
        assert response.json() == {
            "status": "retired",
            "paste_ready": "- Prefer inline bullets over a card group.",
        }
        await db_session.refresh(note)
        assert note.status == "retired"

    async def test_graduating_a_suggested_note_conflicts(
        self, client: AsyncClient, seeded: Seeded, db_session: AsyncSession, test_settings: Settings
    ) -> None:
        note = seeded.notes[0]

        response = await client.post(
            f"{_URL}/{note.id}/graduate", headers=_headers(seeded, test_settings)
        )

        assert response.status_code == 409
        assert response.json()["error"]["code"] == "conflict"
        await db_session.refresh(note)
        assert note.status == "suggested"

    async def test_an_unknown_note_is_404(
        self, client: AsyncClient, seeded: Seeded, test_settings: Settings
    ) -> None:
        response = await client.post(
            f"{_URL}/{uuid.uuid4()}/graduate", headers=_headers(seeded, test_settings)
        )

        assert response.status_code == 404


async def test_the_whole_router_works_with_no_llm_configured(
    client: AsyncClient, seeded: Seeded, test_settings: Settings
) -> None:
    """The point of the design: CalibrationNoteService takes no LLM, so unlike
    the content-improvement router none of these 404 "not configured" when
    LLM__* is unset. `client` uses the real DI chain, not an override."""
    assert test_settings.llm is None
    headers = _headers(seeded, test_settings)
    note = seeded.notes[0]

    assert (await client.get(_URL, headers=headers)).status_code == 200
    review = await client.post(
        f"{_URL}/{note.id}/review", json={"decision": "approve"}, headers=headers
    )
    assert review.status_code == 200
    graduate = await client.post(f"{_URL}/{note.id}/graduate", headers=headers)
    assert graduate.status_code == 200
