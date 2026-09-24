import pytest

from src.services import prompts as P


@pytest.fixture(autouse=True)
def _clear():
    P.clear_cache()
    yield
    P.clear_cache()


def test_load_prompt_reads_file_by_default():
    assert P.load_prompt("interview").startswith("You are the AI Opportunity Interviewer")


def test_load_prompt_equals_the_shipped_file():
    assert P.load_prompt("chatbot") == P.read_file("chatbot")


def test_the_cache_cannot_be_written_from_outside():
    # Git is the only source of truth (2026-09-23): no override path may exist.
    assert not hasattr(P, "set_cache")
    assert not hasattr(P, "reset_cache")
