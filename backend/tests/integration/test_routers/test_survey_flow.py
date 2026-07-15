"""Survey flow: draft upsert → complete → scored persistence (design §3/§7)."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest_asyncio

from src.repositories.assignment_repository import AssignmentRepository
from src.services.scoring import score_response
from tests.fixtures.auth import auth_headers
from tests.fixtures.factories import (
    VALID_ANSWERS,
    assign_track,
    create_lesson,
    create_module,
    create_track,
    create_user,
)

if TYPE_CHECKING:
    from httpx import AsyncClient
    from sqlalchemy.ext.asyncio import AsyncSession

    from src.core.configs.settings import Settings
    from src.db.models import User


@pytest_asyncio.fixture
async def learner(db_session: AsyncSession) -> User:
    return await create_user(db_session, email="survey-learner@example.com")


class TestDraft:
    async def test_get_returns_null_before_any_draft(
        self, client: AsyncClient, learner: User, test_settings: Settings
    ) -> None:
        response = await client.get("/api/survey/me", headers=auth_headers(learner, test_settings))
        assert response.status_code == 200
        assert response.json() is None

    async def test_put_creates_an_in_progress_row(
        self, client: AsyncClient, learner: User, test_settings: Settings
    ) -> None:
        response = await client.put(
            "/api/survey/me",
            json={"job_title": "Consultant", "current_step": 2},
            headers=auth_headers(learner, test_settings),
        )
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "in_progress"
        assert body["job_title"] == "Consultant"
        assert body["current_step"] == 2
        assert body["user_id"] == str(learner.id)

    async def test_partial_put_keeps_other_fields(
        self, client: AsyncClient, learner: User, test_settings: Settings
    ) -> None:
        headers = auth_headers(learner, test_settings)
        await client.put(
            "/api/survey/me", json={"job_title": "Dev", "c1_code": "HAVE"}, headers=headers
        )
        response = await client.put("/api/survey/me", json={"c2_code": "PARTIAL"}, headers=headers)
        body = response.json()
        assert body["job_title"] == "Dev"
        assert body["c1_code"] == "HAVE"
        assert body["c2_code"] == "PARTIAL"

    async def test_explicit_null_clears_a_field(
        self, client: AsyncClient, learner: User, test_settings: Settings
    ) -> None:
        headers = auth_headers(learner, test_settings)
        await client.put("/api/survey/me", json={"job_title": "Dev"}, headers=headers)
        response = await client.put("/api/survey/me", json={"job_title": None}, headers=headers)
        assert response.json()["job_title"] is None

    async def test_open_answers_capped_at_2000_chars(
        self, client: AsyncClient, learner: User, test_settings: Settings
    ) -> None:
        response = await client.put(
            "/api/survey/me",
            json={"q_excitement": "x" * 2001},
            headers=auth_headers(learner, test_settings),
        )
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "validation_error"


class TestComplete:
    async def test_complete_without_draft_is_409_with_clear_message(
        self, client: AsyncClient, learner: User, test_settings: Settings
    ) -> None:
        response = await client.post(
            "/api/survey/complete", headers=auth_headers(learner, test_settings)
        )
        assert response.status_code == 409
        assert "no in-progress survey" in response.json()["error"]["message"].lower()

    async def test_complete_with_missing_answers_is_422(
        self, client: AsyncClient, learner: User, test_settings: Settings
    ) -> None:
        headers = auth_headers(learner, test_settings)
        await client.put("/api/survey/me", json={"c1_code": "HAVE"}, headers=headers)
        response = await client.post("/api/survey/complete", headers=headers)
        assert response.status_code == 422
        assert response.json()["error"]["message"] == "Missing answer for c2"

    async def test_happy_path_persists_all_scored_fields(
        self, client: AsyncClient, learner: User, test_settings: Settings
    ) -> None:
        headers = auth_headers(learner, test_settings)
        await client.put("/api/survey/me", json=VALID_ANSWERS, headers=headers)

        response = await client.post("/api/survey/complete", headers=headers)
        assert response.status_code == 200
        expected = score_response(VALID_ANSWERS)
        assert response.json() == {
            "score_level": expected["score_level"],
            "usage_band": expected["usage_band"],
            "mandatory_modules": expected["mandatory_modules"],
        }

        stored = (await client.get("/api/survey/me", headers=headers)).json()
        assert stored["status"] == "complete"
        assert stored["completed_at"] is not None
        assert stored["scored_at"] is not None
        for field in (
            "score_level",
            "c1_rung",
            "c2_rung",
            "c3_rung",
            "c4_rung",
            "c5_rung",
            "c6_rung",
            "have_count",
            "adv_count",
            "safety_flag",
            "mandatory_modules",
            "usage_band",
        ):
            assert stored[field] == expected[field], field

    async def test_complete_twice_is_409(
        self, client: AsyncClient, learner: User, test_settings: Settings
    ) -> None:
        headers = auth_headers(learner, test_settings)
        await client.put("/api/survey/me", json=VALID_ANSWERS, headers=headers)
        assert (await client.post("/api/survey/complete", headers=headers)).status_code == 200
        assert (await client.post("/api/survey/complete", headers=headers)).status_code == 409

    async def test_draft_after_complete_is_409(
        self, client: AsyncClient, learner: User, test_settings: Settings
    ) -> None:
        headers = auth_headers(learner, test_settings)
        await client.put("/api/survey/me", json=VALID_ANSWERS, headers=headers)
        await client.post("/api/survey/complete", headers=headers)
        response = await client.put("/api/survey/me", json={"job_title": "X"}, headers=headers)
        assert response.status_code == 409
        assert response.json()["error"]["code"] == "conflict"

    async def test_null_c5_rung_survey_completes(
        self, client: AsyncClient, learner: User, test_settings: Settings
    ) -> None:
        """NO_USE alone → c5_rung null end-to-end (the JS/Python trap, §5)."""
        headers = auth_headers(learner, test_settings)
        answers = {**VALID_ANSWERS, "c5_codes": ["NO_USE"]}
        await client.put("/api/survey/me", json=answers, headers=headers)
        response = await client.post("/api/survey/complete", headers=headers)
        assert response.status_code == 200
        stored = (await client.get("/api/survey/me", headers=headers)).json()
        assert stored["c5_rung"] is None
        assert "safe-use" not in (stored["mandatory_modules"] or [])


# A full answer set that scores to integrator (all four capabilities HAVE, two
# advanced, safe c5, trustworthy c6) — the top level the scorer ever emits.
INTEGRATOR_ANSWERS = {
    "c1_code": "ADV_D",
    "c2_code": "ADV_D",
    "c3_code": "HAVE",
    "c4_code": "HAVE",
    "c5_codes": ["KEPT_OUT"],
    "c6_code": "HAVE",
    "b_freq": "WEEKLY",
    "b_breadth": "SEVERAL",
}


class TestAutoAssignOnComplete:
    """Completing the assessment seeds track/module/lesson assignments for every
    track at or below the scored level (VALID_ANSWERS scores to practitioner). An
    integrator scorer additionally seeds the aspirational multiplier track ("For
    Developers"), which the scoring engine never emits on its own."""

    async def test_assigns_tracks_at_or_below_level_with_modules_and_lessons(
        self, client: AsyncClient, learner: User, test_settings: Settings, db_session: AsyncSession
    ) -> None:
        explore = await create_track(db_session, "General I", required_level="explore")
        practitioner = await create_track(
            db_session, "General II", required_level="practitioner", sort_order=1
        )
        integrator = await create_track(
            db_session, "Tool", track_type="tool", required_level="integrator", sort_order=2
        )
        multiplier = await create_track(
            db_session,
            "For Developers",
            track_type="tool",
            required_level="multiplier",
            sort_order=3,
        )
        explore_module = await create_module(db_session, explore, "E-mod")
        practitioner_module = await create_module(db_session, practitioner, "P-mod")
        integrator_module = await create_module(db_session, integrator, "I-mod")
        explore_lesson = await create_lesson(db_session, explore_module, "E-lesson")
        integrator_lesson = await create_lesson(db_session, integrator_module, "I-lesson")

        headers = auth_headers(learner, test_settings)
        await client.put("/api/survey/me", json=VALID_ANSWERS, headers=headers)
        assert (await client.post("/api/survey/complete", headers=headers)).status_code == 200

        assignments = AssignmentRepository(db_session)
        # Above the scored level (integrator, and the aspirational multiplier) stays out.
        assert await assignments.track_ids_for_user(learner.id) == {explore.id, practitioner.id}
        assert await assignments.module_ids_for_user(learner.id) == {
            explore_module.id,
            practitioner_module.id,
        }
        # Only the eligible tracks' lessons — the integrator lesson stays out.
        assigned_lessons = await assignments.lesson_ids_for_user(learner.id)
        assert explore_lesson.id in assigned_lessons
        assert integrator_lesson.id not in assigned_lessons
        assert integrator_module.id not in await assignments.module_ids_for_user(learner.id)
        assert multiplier.id not in await assignments.track_ids_for_user(learner.id)

    async def test_integrator_scorer_seeds_multiplier_track_too(
        self, client: AsyncClient, learner: User, test_settings: Settings, db_session: AsyncSession
    ) -> None:
        # The scoring engine never emits 'multiplier', so a multiplier-gated track
        # would never be seeded by a plain rank comparison. An integrator scorer
        # gets it alongside the integrator tool tracks — assignment grants it,
        # maturity still gates its visibility until integrator is closed out.
        assert score_response(INTEGRATOR_ANSWERS)["score_level"] == "integrator"

        integrator = await create_track(
            db_session, "Tool", track_type="tool", required_level="integrator", sort_order=2
        )
        multiplier = await create_track(
            db_session,
            "For Developers",
            track_type="tool",
            required_level="multiplier",
            sort_order=3,
        )
        multiplier_module = await create_module(db_session, multiplier, "M-mod")
        multiplier_lesson = await create_lesson(db_session, multiplier_module, "M-lesson")

        headers = auth_headers(learner, test_settings)
        await client.put("/api/survey/me", json=INTEGRATOR_ANSWERS, headers=headers)
        assert (await client.post("/api/survey/complete", headers=headers)).status_code == 200

        assignments = AssignmentRepository(db_session)
        tracks = await assignments.track_ids_for_user(learner.id)
        assert integrator.id in tracks
        assert multiplier.id in tracks
        assert multiplier_module.id in await assignments.module_ids_for_user(learner.id)
        assert multiplier_lesson.id in await assignments.lesson_ids_for_user(learner.id)

    async def test_does_not_seed_when_user_already_has_an_assignment(
        self, client: AsyncClient, learner: User, test_settings: Settings, db_session: AsyncSession
    ) -> None:
        explore = await create_track(db_session, "General I", required_level="explore")
        integrator = await create_track(
            db_session, "Tool", track_type="tool", required_level="integrator", sort_order=1
        )
        # An admin already assigned a track — the seeder must leave it untouched.
        await assign_track(db_session, learner, integrator)

        headers = auth_headers(learner, test_settings)
        await client.put("/api/survey/me", json=VALID_ANSWERS, headers=headers)
        assert (await client.post("/api/survey/complete", headers=headers)).status_code == 200

        assignments = AssignmentRepository(db_session)
        assert await assignments.track_ids_for_user(learner.id) == {integrator.id}
        assert explore.id not in await assignments.track_ids_for_user(learner.id)

    async def test_completes_cleanly_when_no_tracks_exist(
        self, client: AsyncClient, learner: User, test_settings: Settings, db_session: AsyncSession
    ) -> None:
        headers = auth_headers(learner, test_settings)
        await client.put("/api/survey/me", json=VALID_ANSWERS, headers=headers)
        assert (await client.post("/api/survey/complete", headers=headers)).status_code == 200
        assert await AssignmentRepository(db_session).track_ids_for_user(learner.id) == set()
