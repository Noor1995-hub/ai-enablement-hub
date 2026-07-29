"""InterviewContextService: composes the caller's own survey + effective
maturity + learning status into a human-readable briefing (system-prompt
block) and a fuller assessment context (wrap-up prompt). Pure-logic unit
tests with mocked services (AAA, no DB)."""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock

from src.services.interview_context import InterviewContextService
from src.services.learning_service import LearningService
from src.services.maturity_service import MaturityService
from src.services.survey_service import SurveyService


def _survey(**overrides: object) -> SimpleNamespace:
    fields: dict[str, object] = {
        "job_title": "Financial Analyst",
        "department": "Finance",
        "b_freq": "WEEKLY",
        "b_tools": ["CHATGPT", "COPILOT"],
        "b_setup": ["WORKSPACE"],
        "b_barriers": ["NO_TIME"],
        "q_timesink": "reformatting reports",
        "q_excitement": "automating client summaries",
        "score_level": "practitioner",
        "usage_band": "regular",
        "c1_code": "HAVE",
        "c2_code": "HAVE",
        "c3_code": "HAVE",
        "c4_code": "PARTIAL",
        "c5_codes": ["APPROVED_PASTE"],
        "c6_code": "HAVE",
    }
    fields.update(overrides)
    return SimpleNamespace(**fields)


def _user() -> SimpleNamespace:
    return SimpleNamespace(id=uuid.uuid4(), first_name="Aaron", last_name="Neuville")


def _service() -> tuple[InterviewContextService, AsyncMock, AsyncMock, AsyncMock]:
    surveys = AsyncMock(spec=SurveyService)
    maturity = AsyncMock(spec=MaturityService)
    learning = AsyncMock(spec=LearningService)
    service = InterviewContextService(surveys, maturity, learning)
    return service, surveys, maturity, learning


async def test_briefing_renders_human_labels() -> None:
    service, surveys, maturity, learning = _service()
    surveys.get_own.return_value = _survey()
    maturity.effective_level.return_value = "practitioner"
    learning.learning_status.return_value = "in_progress"
    user = _user()

    briefing = await service.build_briefing(user)  # ty: ignore[invalid-argument-type]

    assert "ChatGPT" in briefing
    assert "Microsoft Copilot" in briefing
    assert "CHATGPT" not in briefing
    assert "reformatting reports" in briefing
    assert "practitioner" in briefing
    assert "Aaron Neuville" in briefing


async def test_briefing_minimal_when_no_survey() -> None:
    service, surveys, maturity, learning = _service()
    surveys.get_own.return_value = None
    maturity.effective_level.return_value = None
    learning.learning_status.return_value = "not_started"
    user = _user()

    briefing = await service.build_briefing(user)  # ty: ignore[invalid-argument-type]

    assert "Aaron Neuville" in briefing
    assert "no completed assessment" in briefing.lower()


async def test_assessment_context_includes_competencies() -> None:
    service, surveys, maturity, learning = _service()
    surveys.get_own.return_value = _survey()
    maturity.effective_level.return_value = "practitioner"
    learning.learning_status.return_value = "in_progress"
    user = _user()

    context = await service.build_assessment_context(user)  # ty: ignore[invalid-argument-type]

    assert "Add context or examples, or break it into steps, and iterate until it works." in context
