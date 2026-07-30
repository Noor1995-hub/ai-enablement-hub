import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from src.repositories.prompt_repository import PromptRepository
from src.services import prompts as P
from src.services.exceptions import DomainError, NotFoundError
from src.services.prompt_service import KNOWN_PROMPTS, PromptService, missing_tokens


@pytest.fixture(autouse=True)
def _clear():
    P.clear_cache()
    yield
    P.clear_cache()


def _svc():
    repo = AsyncMock(spec=PromptRepository)
    return PromptService(repo), repo


async def test_list_all_labels_source():
    svc, repo = _svc()
    repo.list_all.return_value = [
        SimpleNamespace(kind="interview", content="X", updated_at=None, updated_by=None)
    ]
    out = {p.kind: p.source for p in await svc.list_all()}
    assert out["interview"] == "db" and out["chatbot"] == "file"


async def test_update_rejects_missing_token():
    svc, repo = _svc()
    with pytest.raises(DomainError):
        await svc.update(kind="interview_playbook", content="no slots", user_id=uuid.uuid4())
    repo.upsert.assert_not_awaited()


async def test_update_persists_and_caches():
    svc, repo = _svc()
    body = "{first_name}{assessment_json}{company_context}{transcript}"
    await svc.update(kind="interview_playbook", content=body, user_id=None)
    repo.upsert.assert_awaited_once()
    assert P.load_prompt("interview_playbook") == body


async def test_reset_deletes_and_busts_cache():
    svc, repo = _svc()
    P.set_cache("interview", "OVERRIDE")
    await svc.reset(kind="interview")
    repo.delete.assert_awaited_once()
    assert P.load_prompt("interview").startswith("You are the AI Opportunity Interviewer")


async def test_refresh_cache_overlays_rows():
    svc, repo = _svc()
    repo.list_all.return_value = [
        SimpleNamespace(kind="chatbot", content="DBVAL", updated_at=None, updated_by=None)
    ]
    await svc.refresh_cache()
    assert P.load_prompt("chatbot") == "DBVAL"


async def test_unknown_kind_404s():
    svc, _ = _svc()
    with pytest.raises(NotFoundError):
        await svc.get(kind="does_not_exist")


async def test_reset_unknown_kind_404s():
    svc, repo = _svc()
    with pytest.raises(NotFoundError):
        await svc.reset(kind="does_not_exist")
    repo.delete.assert_not_awaited()


def test_missing_tokens_flags_dropped_playbook_slot():
    body = "no slots here"
    assert set(missing_tokens("interview_playbook", body)) == {
        "{first_name}",
        "{assessment_json}",
        "{company_context}",
        "{transcript}",
    }


def test_missing_tokens_ok_when_all_present():
    body = "{first_name} {assessment_json} {company_context} {transcript}"
    assert missing_tokens("interview_playbook", body) == []


def test_verbatim_prompt_has_no_required_tokens():
    assert missing_tokens("house_style", "anything") == []


def test_known_prompts_covers_the_nine():
    kinds = {p.kind for p in KNOWN_PROMPTS}
    assert kinds == {
        "interview",
        "interview_playbook",
        "chatbot",
        "assessment",
        "lesson",
        "content_improvement",
        "content_improvement_critique",
        "house_style",
        "feedback_triage",
    }
