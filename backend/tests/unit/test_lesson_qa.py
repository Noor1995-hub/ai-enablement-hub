"""The in-app house-style checks (B5) = check_draft.py's checks, one module."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

from src.services.lesson_qa import Finding, check_blocks, check_lesson


def _quiz(correct: list[int], options: list[list[str]] | None = None) -> dict:
    opts = options or [["aa", "bb"] for _ in correct]
    return {
        "id": "quiz",
        "type": "quiz",
        "questions": [
            {"id": f"q{i}", "q": "Q?", "options": o, "correct": c, "explanation": "e"}
            for i, (c, o) in enumerate(zip(correct, opts, strict=True))
        ],
    }


HEADING = {"id": "h", "type": "heading", "level": 2, "text": "Check your understanding"}


def test_a_clean_lesson_has_no_findings() -> None:
    blocks = [
        {"id": "p", "type": "paragraph", "text": "Plain **one** text."},
        HEADING,
        _quiz([0, 1]),
    ]
    assert check_lesson(blocks) == []


@pytest.mark.parametrize(("char", "name"), [("—", "em dash"), ("–", "en dash"), ("…", "ellipsis")])
def test_forbidden_punctuation_names_the_block(char: str, name: str) -> None:
    findings = check_lesson([{"id": "p", "type": "paragraph", "text": f"a {char} b"}])
    assert findings == [Finding("warning", 0, "block 1 · paragraph", f"{name} in [0].text")]


def test_duplicate_ids() -> None:
    blocks = [
        {"id": "x", "type": "paragraph", "text": "a"},
        {"id": "x", "type": "paragraph", "text": "b"},
    ]
    assert any("duplicate ids" in f.message for f in check_lesson(blocks))


def test_quiz_rules() -> None:
    blocks = [_quiz([0, 0], [["long answer", "b"], ["long answer", "b"]])]
    messages = [f.message for f in check_lesson(blocks)]
    assert any("not preceded by a 'Check your understanding' heading" in m for m in messages)
    assert any("correct position never varies" in m for m in messages)
    assert any("correct is the unique longest option" in m for m in messages)


def test_more_than_two_bold_spans_is_a_warning() -> None:
    blocks = [{"id": "p", "type": "paragraph", "text": "**a** **b** **c**"}]
    assert [f.severity for f in check_lesson(blocks)] == ["warning"]


def test_an_empty_image_blob_path_is_info() -> None:
    blocks = [{"id": "i", "type": "image", "blob_path": "", "alt": "x"}]
    findings = check_lesson(blocks)
    assert findings and all(f.severity == "info" for f in findings)


def test_unresolved_sort_and_predict_references() -> None:
    blocks = [
        {
            "id": "s",
            "type": "interactive",
            "mode": "sort",
            "prompt": "p",
            "buckets": [{"id": "b1", "label": "B"}],
            "items": [{"id": "i1", "text": "t", "bucketId": "nope", "reason": "r"}],
        },
        {
            "id": "pr",
            "type": "interactive",
            "mode": "predict",
            "prompt": "p",
            "options": [{"id": "o1", "label": "L", "reason": "r"}],
            "correctOptionId": "zz",
        },
    ]
    messages = [f.message for f in check_lesson(blocks)]
    assert any("unresolved bucketId" in m for m in messages)
    assert any("correctOptionId does not resolve" in m for m in messages)


def test_the_cli_reports_the_same_failures() -> None:
    """Parity: check_draft.py is a thin CLI over check_blocks."""
    path = Path(__file__).resolve().parents[2] / "scripts" / "content_qa" / "check_draft.py"
    spec = importlib.util.spec_from_file_location("check_draft", path)
    assert spec and spec.loader
    cli = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cli)
    blocks = [{"id": "p", "type": "paragraph", "text": "a — b"}, _quiz([0, 0])]
    assert cli.check({"content_blocks": blocks}) == check_blocks(blocks)
