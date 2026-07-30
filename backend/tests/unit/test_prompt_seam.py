import pytest

from src.services import prompts as P


@pytest.fixture(autouse=True)
def _clear():
    P.clear_cache()
    yield
    P.clear_cache()


def test_load_prompt_reads_file_by_default():
    assert P.load_prompt("interview").startswith("You are the AI Opportunity Interviewer")


def test_set_cache_overrides_file():
    P.set_cache("interview", "OVERRIDDEN")
    assert P.load_prompt("interview") == "OVERRIDDEN"


def test_reset_cache_restores_file():
    P.set_cache("interview", "OVERRIDDEN")
    P.reset_cache("interview")
    assert P.load_prompt("interview").startswith("You are the AI Opportunity Interviewer")
