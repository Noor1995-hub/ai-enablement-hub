"""DI for the feedback-driven content-improvement agents.

All parameter annotations are runtime imports on purpose: FastAPI evaluates the
deferred annotations against module globals, and an unresolvable name silently
degrades the parameter to a required query param (see database.py).
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.dependencies.database import get_session
from src.core.dependencies.domain import get_content_repository, get_feedback_repository
from src.core.dependencies.llm import get_llm_service
from src.repositories.calibration_note_repository import CalibrationNoteRepository
from src.repositories.content_repository import ContentRepository
from src.repositories.feedback_repository import FeedbackRepository
from src.repositories.proposal_repository import ProposalRepository
from src.services.calibration_note_service import CalibrationNoteService
from src.services.content_improvement_service import ContentImprovementService
from src.services.feedback_triage_service import FeedbackTriageService
from src.services.llm_service import AnthropicLlmClient

__all__ = [
    "get_calibration_note_repository",
    "get_calibration_note_service",
    "get_content_improvement_service",
    "get_feedback_triage_service",
    "get_proposal_repository",
]


def get_feedback_triage_service(
    feedback: Annotated[FeedbackRepository, Depends(get_feedback_repository)],
    llm: Annotated[AnthropicLlmClient | None, Depends(get_llm_service)],
) -> FeedbackTriageService | None:
    """None when LLM__* is unconfigured — the endpoint 404s (mirrors
    get_chat_service; the feature has no meaning without a model)."""
    if llm is None:
        return None
    return FeedbackTriageService(feedback, llm)


def get_proposal_repository(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ProposalRepository:
    return ProposalRepository(session)


def get_calibration_note_repository(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> CalibrationNoteRepository:
    return CalibrationNoteRepository(session)


def get_calibration_note_service(
    notes: Annotated[CalibrationNoteRepository, Depends(get_calibration_note_repository)],
) -> CalibrationNoteService:
    """Unconditional, unlike the two agent services: curating notes needs no
    model, so it must keep working even when LLM__* is unconfigured."""
    return CalibrationNoteService(notes)


def get_content_improvement_service(
    proposals: Annotated[ProposalRepository, Depends(get_proposal_repository)],
    feedback: Annotated[FeedbackRepository, Depends(get_feedback_repository)],
    content: Annotated[ContentRepository, Depends(get_content_repository)],
    llm: Annotated[AnthropicLlmClient | None, Depends(get_llm_service)],
    calibration_notes: Annotated[
        CalibrationNoteRepository, Depends(get_calibration_note_repository)
    ],
) -> ContentImprovementService | None:
    """None when LLM__* is unconfigured, so the whole section 404s — the design
    doc's "the whole feature no-ops / 404s when Settings.llm is unconfigured".
    With no model there is nothing to draft, so there is nothing to review."""
    if llm is None:
        return None
    return ContentImprovementService(proposals, feedback, content, llm, calibration_notes)
