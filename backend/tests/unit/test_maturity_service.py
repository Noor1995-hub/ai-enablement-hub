"""MaturityService.effective_level (the live progression ladder) and
set_override. Pure-logic unit tests with mocked repositories (AAA, no DB)."""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from src.db.models import User
from src.repositories.base import (
    AbstractAssignmentRepository,
    AbstractContentRepository,
    AbstractSurveyRepository,
    AbstractUserRepository,
)
from src.services.exceptions import NotFoundError
from src.services.maturity_service import MaturityService

# Three tracks, one per assignable level, and one module in each.
GI_TRACK, GII_TRACK, TOOL_TRACK = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
GI_MOD, GII_MOD, TOOL_MOD = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()

_TRACKS = [
    SimpleNamespace(id=GI_TRACK, required_level="explore"),
    SimpleNamespace(id=GII_TRACK, required_level="practitioner"),
    SimpleNamespace(id=TOOL_TRACK, required_level="integrator"),
]
_MODULES = [
    SimpleNamespace(id=GI_MOD, track_id=GI_TRACK),
    SimpleNamespace(id=GII_MOD, track_id=GII_TRACK),
    SimpleNamespace(id=TOOL_MOD, track_id=TOOL_TRACK),
]


def make_service(
    *,
    override: str | None = None,
    survey_level: str | None = None,
    counts: dict[uuid.UUID, tuple[int, int]] | None = None,
) -> tuple[MaturityService, User, dict[str, AsyncMock]]:
    user = User(
        id=uuid.uuid4(),
        email="m@example.com",
        first_name="M",
        last_name="D",
        maturity_override=override,
    )
    users = AsyncMock(spec=AbstractUserRepository)
    users.get_by_id.return_value = user
    surveys = AsyncMock(spec=AbstractSurveyRepository)
    surveys.get_complete_levels.return_value = (
        {user.id: survey_level} if survey_level is not None else {}
    )
    content = AsyncMock(spec=AbstractContentRepository)
    content.list_tracks.return_value = _TRACKS
    content.list_modules.return_value = _MODULES
    assignments = AsyncMock(spec=AbstractAssignmentRepository)
    assignments.assigned_lesson_counts_by_module.return_value = counts or {}
    service = MaturityService(users, surveys, content, assignments)
    return (
        service,
        user,
        {
            "users": users,
            "surveys": surveys,
            "content": content,
            "assignments": assignments,
        },
    )


DONE = (2, 2)
PARTIAL = (2, 1)


class TestEffectiveLevel:
    async def test_null_base_returns_none(self) -> None:
        service, user, _ = make_service(override=None, survey_level=None)
        assert await service.effective_level(user) is None

    async def test_base_from_complete_survey_when_no_override(self) -> None:
        service, user, _ = make_service(survey_level="practitioner")
        assert await service.effective_level(user) == "practitioner"

    async def test_override_takes_precedence_over_survey(self) -> None:
        service, user, _ = make_service(override="integrator", survey_level="explore")
        assert await service.effective_level(user) == "integrator"

    async def test_progression_advances_when_level_fully_complete(self) -> None:
        # Explorer with General I done but General II not → advances one rung.
        service, user, _ = make_service(
            survey_level="explore", counts={GI_MOD: DONE, GII_MOD: PARTIAL}
        )
        assert await service.effective_level(user) == "practitioner"

    async def test_progression_stops_when_level_incomplete(self) -> None:
        service, user, _ = make_service(survey_level="explore", counts={GI_MOD: PARTIAL})
        assert await service.effective_level(user) == "explore"

    async def test_progression_walks_multiple_rungs(self) -> None:
        service, user, _ = make_service(
            survey_level="explore", counts={GI_MOD: DONE, GII_MOD: DONE, TOOL_MOD: PARTIAL}
        )
        assert await service.effective_level(user) == "integrator"

    async def test_low_override_readvances_cannot_undo_earned(self) -> None:
        # Pinned back to Explorer, but General I is complete → re-advances to
        # Practitioner (the earned level); the pin cannot demote below it.
        service, user, _ = make_service(override="explore", counts={GI_MOD: DONE, GII_MOD: PARTIAL})
        assert await service.effective_level(user) == "practitioner"

    async def test_high_override_jumps_ahead(self) -> None:
        service, user, _ = make_service(override="integrator", counts={TOOL_MOD: PARTIAL})
        assert await service.effective_level(user) == "integrator"

    async def test_empty_assigned_level_does_not_vacuously_advance(self) -> None:
        # No assigned modules at the Explorer level → cannot advance even though
        # a higher level's module happens to be complete.
        service, user, _ = make_service(survey_level="explore", counts={GII_MOD: DONE})
        assert await service.effective_level(user) == "explore"

    async def test_top_of_ladder_advances_to_multiplier(self) -> None:
        service, user, _ = make_service(
            override="integrator", counts={GI_MOD: DONE, GII_MOD: DONE, TOOL_MOD: DONE}
        )
        assert await service.effective_level(user) == "multiplier"


class TestSetOverride:
    async def test_persists_pin_without_assignment_side_effects(self) -> None:
        service, user, mocks = make_service()
        await service.set_override(user.id, "practitioner")
        mocks["users"].set_maturity_override.assert_awaited_once_with(user, "practitioner")
        # Maturity never touches assignments.
        assert mocks["assignments"].mock_calls == []

    async def test_clear_persists_none(self) -> None:
        service, user, mocks = make_service()
        await service.set_override(user.id, None)
        mocks["users"].set_maturity_override.assert_awaited_once_with(user, None)

    async def test_unknown_user_raises_not_found(self) -> None:
        service, _, mocks = make_service()
        mocks["users"].get_by_id.return_value = None
        with pytest.raises(NotFoundError):
            await service.set_override(uuid.uuid4(), "explore")
