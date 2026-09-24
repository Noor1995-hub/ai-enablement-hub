from pathlib import Path

import pytest

from src.services.exceptions import NotFoundError
from src.services.prompt_service import KNOWN_PROMPTS, PromptService, prompt_path

REPO_ROOT = Path(__file__).resolve().parents[3]


def test_list_all_returns_every_known_kind_with_its_path():
    summaries = PromptService().list_all()
    assert [s.kind for s in summaries] == [m.kind for m in KNOWN_PROMPTS]
    for s in summaries:
        assert s.path == f"backend/prompts/{s.kind}.md"
        assert (REPO_ROOT / s.path).is_file()


def test_get_returns_the_file_content():
    detail = PromptService().get("interview")
    assert (
        detail.content
        == (REPO_ROOT / "backend/prompts/interview.md").read_text(encoding="utf-8").strip()
    )
    assert detail.path == prompt_path("interview")
    assert detail.label == "Interview — conversation"


def test_get_unknown_kind_is_not_found():
    with pytest.raises(NotFoundError):
        PromptService().get("does_not_exist")


def test_the_service_has_no_write_path():
    for name in ("update", "reset", "refresh_cache"):
        assert not hasattr(PromptService, name)
