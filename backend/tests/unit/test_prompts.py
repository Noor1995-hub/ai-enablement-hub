from __future__ import annotations

from src.services import prompts as P


def test_prompt_version_is_a_stable_short_hash() -> None:
    first = P.prompt_version("interview")
    assert len(first) == 12
    assert all(c in "0123456789abcdef" for c in first)
    assert P.prompt_version("interview") == first


def test_prompt_version_differs_per_prompt() -> None:
    assert P.prompt_version("interview") != P.prompt_version("interview_playbook")
