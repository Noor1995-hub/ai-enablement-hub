"""require_completed_assessment: callers who bypass locks skip it (spec
2026-10-01 decision 5); everyone else needs a COMPLETED assessment."""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock

import pytest

from src.core.dependencies.interview import require_completed_assessment
from src.services.exceptions import AssessmentRequiredError
from src.services.survey_service import SurveyService


def _surveys(status: str) -> Any:
    surveys = AsyncMock(spec=SurveyService)
    surveys.survey_status.return_value = status
    return surveys


async def test_bypassing_caller_skips_the_gate() -> None:
    user: Any = SimpleNamespace(id=uuid.uuid4())
    surveys = _surveys("not_started")
    await require_completed_assessment(user=user, surveys=surveys, bypasses_locks=True)
    surveys.survey_status.assert_not_awaited()


async def test_learner_without_a_completed_assessment_is_rejected() -> None:
    user: Any = SimpleNamespace(id=uuid.uuid4())
    with pytest.raises(AssessmentRequiredError):
        await require_completed_assessment(
            user=user, surveys=_surveys("in_progress"), bypasses_locks=False
        )


async def test_learner_with_a_completed_assessment_passes() -> None:
    user: Any = SimpleNamespace(id=uuid.uuid4())
    await require_completed_assessment(
        user=user, surveys=_surveys("complete"), bypasses_locks=False
    )
