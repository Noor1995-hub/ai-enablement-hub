from content_qa.checks import (
    check_quiz_conformance,
    find_americanisms,
    find_banned_punctuation,
    quiz_stats,
)


def _para(text):
    return [{"id": "p", "type": "paragraph", "text": text}]


def test_flags_em_en_dash_and_ellipsis():
    found = find_banned_punctuation(_para("A long thought — really … you know – yes"))
    chars = {f["char"] for f in found}
    assert chars == {"em-dash", "en-dash", "ellipsis"}
    assert all(f["snippet"] for f in found)


def test_clean_text_has_no_punctuation_findings():
    assert find_banned_punctuation(_para("A normal sentence, with a comma.")) == []


def test_flags_american_spellings():
    found = find_americanisms(_para("Organize the color of your behavior and analyze it."))
    terms = {f["term"].lower() for f in found}
    assert {"organize", "color", "behavior", "analyze"} <= terms
    for f in found:
        assert f["suggestion"]  # every hit carries a British suggestion


def test_does_not_flag_correct_british_forms():
    found = find_americanisms(_para(
        "Organise the colour of your behaviour, summarise the Artefact, and centre it."
    ))
    assert found == []


def test_americanism_word_boundaries_no_false_positives():
    # 'size', 'prize', 'maize' end in -ize but are not American -ise words;
    # 'parameter' contains 'meter'; none should fire.
    found = find_americanisms(_para("The size of the prize parameter in the maize field."))
    assert found == []


def test_flags_nested_quiz_option_text():
    blocks = [{"id": "q", "type": "quiz", "questions": [
        {"id": "1", "q": "Pick", "options": ["Organize files", "Leave them"],
         "correct": 0, "explanation": "ok"}]}]
    found = find_americanisms(blocks)
    assert any(f["path"].endswith("options[0]") for f in found)


HEADING = {"id": "h", "type": "heading", "level": 2, "text": "Check your understanding"}
WS_MD = {"id": "w", "type": "whitespace", "size": "md"}
QUIZ = {"id": "q", "type": "quiz", "questions": [
    {"id": "1", "q": "Q", "options": ["a", "b", "c"], "correct": 1, "explanation": "e"}]}


def test_conformant_quiz_heading_then_ws_has_no_findings():
    blocks = [{"id": "p", "type": "paragraph", "text": "body"}, HEADING, WS_MD, QUIZ]
    assert check_quiz_conformance(blocks) == []


def test_conformant_quiz_ws_then_heading_has_no_findings():
    # the dominant real pattern: whitespace(md) sits BEFORE the CYU heading
    blocks = [{"id": "p", "type": "paragraph", "text": "body"}, WS_MD, HEADING, QUIZ]
    assert check_quiz_conformance(blocks) == []


def test_missing_check_understanding_heading_is_flagged():
    blocks = [WS_MD, QUIZ]  # md separator present, but no CYU heading
    kinds = {f["kind"] for f in check_quiz_conformance(blocks)}
    assert "quiz-no-cyu-heading" in kinds
    assert "quiz-no-md-separator" not in kinds


def test_missing_md_separator_is_flagged():
    blocks = [HEADING, QUIZ]  # CYU heading present, but no whitespace(md) in the window
    kinds = {f["kind"] for f in check_quiz_conformance(blocks)}
    assert "quiz-no-md-separator" in kinds
    assert "quiz-no-cyu-heading" not in kinds


def test_wrong_whitespace_size_is_flagged():
    blocks = [HEADING, {"id": "w", "type": "whitespace", "size": "sm"}, QUIZ]
    kinds = {f["kind"] for f in check_quiz_conformance(blocks)}
    assert "whitespace-size" in kinds


def test_mid_lesson_whitespace_separator_is_not_flagged():
    # a plain section separator, not near any quiz, must NOT be an error
    blocks = [{"id": "p", "type": "paragraph", "text": "x"}, WS_MD,
              {"id": "p2", "type": "paragraph", "text": "y"}]
    assert check_quiz_conformance(blocks) == []


def test_quiz_stats_counts_questions_options_positions():
    blocks = [HEADING, WS_MD, QUIZ]
    stats = quiz_stats(blocks)
    assert stats["num_quizzes"] == 1
    assert stats["questions"] == [{"num_options": 3, "correct_index": 1, "quiz_index": 0}]
    assert stats["num_whitespace"] == 1
