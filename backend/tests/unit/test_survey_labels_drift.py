"""The backend's assessment labels (src/core/survey_labels.py) must match the
frontend's source of truth, frontend/src/lib/surveyOptions.ts, code for code and
word for word. Both the interviewer briefing and the project data export print
these labels, so a change to the question wording must land in both files."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from src.core import survey_labels

_TS = Path(__file__).resolve().parents[3] / "frontend" / "src" / "lib" / "surveyOptions.ts"

# A JS string literal in either quote style (the file uses both).
_STR = r"""'(?:[^'\\]|\\.)*'|"(?:[^"\\]|\\.)*\""""
_ENTRY = re.compile(rf"code:\s*(?P<code>{_STR}|\d+)\s*,\s*label:\s*(?P<label>{_STR})")

_PAIRS = {
    "C1_OPTIONS": survey_labels.COMPETENCY_C1,
    "C2_OPTIONS": survey_labels.COMPETENCY_C2,
    "C3_OPTIONS": survey_labels.COMPETENCY_C3,
    "C4_OPTIONS": survey_labels.COMPETENCY_C4,
    "C5_OPTIONS": survey_labels.COMPETENCY_C5,
    "C6_OPTIONS": survey_labels.COMPETENCY_C6,
    "FREQ_OPTIONS": survey_labels.FREQ,
    "BREADTH_OPTIONS": survey_labels.BREADTH,
    "TOOLS_OPTIONS": survey_labels.TOOLS,
    "ATTITUDE_OPTIONS": survey_labels.ATTITUDE,
    "READINESS_OPTIONS": survey_labels.READINESS,
    "BARRIERS_OPTIONS": survey_labels.BARRIERS,
    "SETUP_OPTIONS": survey_labels.SETUP,
}


def _literal(token: str) -> str | int:
    if token.isdigit():
        return int(token)
    return re.sub(r"\\(.)", r"\1", token[1:-1])


def _source() -> str:
    return _TS.read_text(encoding="utf-8")


def _options(name: str) -> dict[str | int, str]:
    match = re.search(rf"export const {name} = \[(.*?)\] as const", _source(), re.DOTALL)
    assert match, f"{name} not found in surveyOptions.ts"
    return {_literal(m["code"]): str(_literal(m["label"])) for m in _ENTRY.finditer(match.group(1))}


def test_every_frontend_option_list_is_mirrored() -> None:
    declared = set(re.findall(r"export const (\w+_OPTIONS) = \[", _source()))
    assert declared == set(_PAIRS), "add the new option list to survey_labels.py and _PAIRS"


@pytest.mark.parametrize("name", sorted(_PAIRS))
def test_option_labels_match_the_frontend(name: str) -> None:
    assert _PAIRS[name] == _options(name)


def test_competency_questions_match_the_frontend() -> None:
    block = _source().split("export const COMPETENCY_QA", 1)[1]
    entries = re.findall(
        rf"key:\s*'(c\d)'.*?label:\s*(?P<label>{_STR}).*?question:\s*(?P<question>{_STR})",
        block,
        re.DOTALL,
    )
    frontend = [(key, _literal(label), _literal(question)) for key, label, question in entries]
    backend = [(c.key, c.label, c.question) for c in survey_labels.COMPETENCIES]
    assert backend == frontend
    multi = re.findall(r"key:\s*'(c\d)'[^}]*multi:\s*true", block)
    assert [c.key for c in survey_labels.COMPETENCIES if c.multi] == multi
