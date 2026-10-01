from __future__ import annotations

from src.services.interview_language import DEFAULT_LANGUAGE, language_directive, resolve_language


def test_dutch_is_named_in_a_fixed_machine_readable_line() -> None:
    assert language_directive("nl").startswith("<interview_language>nl</interview_language>")


def test_english_is_the_default() -> None:
    assert DEFAULT_LANGUAGE == "en"
    assert language_directive(None).startswith("<interview_language>en</interview_language>")


def test_an_unknown_value_falls_back_to_english() -> None:
    # The column is free text: a stray value must never reach the prompt as-is.
    assert resolve_language("fr") == "en"
    assert "fr" not in language_directive("fr")
