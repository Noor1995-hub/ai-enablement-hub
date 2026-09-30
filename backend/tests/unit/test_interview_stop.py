from __future__ import annotations

from src.services.interview_marker import READY_MARKER
from src.services.interview_stop import QuestionCut


def _run(chunks: list[str]) -> tuple[str, QuestionCut]:
    cut = QuestionCut()
    shown = "".join(cut.feed(c) for c in chunks) + cut.finish()
    return shown, cut


def _by_char(text: str) -> list[str]:
    return list(text)


def test_a_turn_without_a_question_and_blank_line_passes_through_unchanged() -> None:
    text = "That helps. Which system is it, by name?"
    shown, cut = _run(_by_char(text))
    assert shown == text
    assert cut.cut is False
    assert cut.removed == ""


def test_real_text_after_the_question_and_a_blank_line_is_cut() -> None:
    shown, cut = _run(_by_char("Which file is it?\n\nI'd guess Excel, honestly."))
    assert shown == "Which file is it?"
    assert cut.cut is True
    assert cut.removed == "\n\nI'd guess Excel, honestly."


def test_a_blank_line_at_the_very_end_is_not_a_cut() -> None:
    # Sonnet 5 writes "?\n\n" before ending almost every turn (v5 eval, #96): not a cut.
    shown, cut = _run(["Which file is it?", "\n\n"])
    assert shown == "Which file is it?"
    assert cut.cut is False


def test_a_question_mark_inside_a_sentence_never_cuts() -> None:
    text = 'Those "did you see this?" chasers, how many a week?'
    shown, cut = _run(_by_char(text))
    assert shown == text
    assert cut.cut is False


def test_a_single_line_break_after_a_question_is_not_a_cut() -> None:
    text = "Sound right?\nIf so, which system first?"
    shown, cut = _run(_by_char(text))
    assert shown == text
    assert cut.cut is False


def test_the_cut_works_whatever_the_chunk_boundaries() -> None:
    shown, cut = _run(["Which file", " is it?", "\n", "\nYes", " it's Excel."])
    assert shown == "Which file is it?"
    assert cut.removed == "\n\nYes it's Excel."


def test_a_marker_after_removed_text_is_dropped_with_it() -> None:
    # v6 eval: "...which could you try today?" + an invented answer + an offer with the
    # marker. The learner never saw that offer, so no Build button for it either.
    shown, cut = _run(
        ["Which could you try today?\n\nChatGPT, I guess.\n\nBuild it?\n\n", READY_MARKER]
    )
    assert shown == "Which could you try today?"
    assert cut.cut is True


def test_a_marker_alone_after_the_question_is_not_a_cut() -> None:
    # The pre-#96 offer shape: nothing real was removed.
    shown, cut = _run(["Shall I build it?\n\n", READY_MARKER])
    assert shown == f"Shall I build it?\n{READY_MARKER}"
    assert cut.cut is False


def test_a_marker_on_the_first_line_is_shown_as_it_streams() -> None:
    shown, cut = _run([f"{READY_MARKER}\n", "That's plenty. Shall I build it?"])
    assert shown == f"{READY_MARKER}\nThat's plenty. Shall I build it?"
    assert cut.cut is False


def test_whitespace_after_a_question_mid_paragraph_is_released() -> None:
    text = "Really? Which one is it?"
    shown, _ = _run(["Really?", " Which one is it?"])
    assert shown == text
