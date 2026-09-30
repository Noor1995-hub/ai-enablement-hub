from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from evals.interviewer import cases as cases_module
from evals.interviewer import report


def _write_frozen_case(tmp_path: Path, case_id: str, transcript: list[dict[str, str]]) -> None:
    (cases_module.CASES_DIR / f"{case_id}.json").write_text(
        json.dumps({"id": case_id, "adversarial": None, "transcript": transcript}),
        encoding="utf-8",
    )


def _write_sim(
    runs_dir: Path,
    variant: str,
    case_id: str,
    rep: int,
    transcript: list[dict[str, Any]],
    *,
    adversarial: dict[str, str] | None = None,
) -> None:
    sims_dir = runs_dir / variant / "sims"
    sims_dir.mkdir(parents=True, exist_ok=True)
    (sims_dir / f"{case_id}_rep{rep}.json").write_text(
        json.dumps(
            {"id": case_id, "rep": rep, "adversarial": adversarial, "transcript": transcript}
        ),
        encoding="utf-8",
    )


def _setup_frozen_cases(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cases_module, "CASES_DIR", tmp_path / "cases")
    cases_module.CASES_DIR.mkdir()


def test_build_chat_report_writes_a_table_with_a_variant_and_a_frozen_column(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _setup_frozen_cases(tmp_path, monkeypatch)
    _write_frozen_case(tmp_path, "frozen-a", [{"role": "assistant", "content": "How's your week?"}])
    runs_dir = tmp_path / "runs"
    _write_sim(runs_dir, "v1", "case-a", 0, [{"role": "assistant", "content": "How's your week?"}])

    out = report.build_chat_report("v1", runs_dir=runs_dir)

    assert out == runs_dir / "v1" / "chat.md"
    text = out.read_text(encoding="utf-8")
    assert "chat_canary_absent" in text
    assert "chat_self_answer_suspect" in text
    assert "chat_one_question_per_turn" in text
    assert "chat_dash_count" in text
    assert "frozen set (current prompt)" in text
    assert "1 sims for this variant; 1 frozen cases." in text


def test_build_chat_report_lists_a_hard_failure_with_its_excerpt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _setup_frozen_cases(tmp_path, monkeypatch)
    runs_dir = tmp_path / "runs"
    _write_sim(
        runs_dir,
        "v1",
        "adv-case",
        0,
        [{"role": "assistant", "content": 'skipping the "PELICAN-42" note in your notes'}],
        adversarial={"canary": "PELICAN-42", "where": "transcript"},
    )

    out = report.build_chat_report("v1", runs_dir=runs_dir)

    text = out.read_text(encoding="utf-8")
    assert "## Hard failures (variant)" in text
    failure_section = text.split("## Hard failures (variant)")[1]
    assert "adv-case" in failure_section
    assert "PELICAN-42" in failure_section


def test_build_chat_report_says_none_with_no_hard_failures(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _setup_frozen_cases(tmp_path, monkeypatch)
    runs_dir = tmp_path / "runs"
    _write_sim(runs_dir, "v1", "case-a", 0, [{"role": "assistant", "content": "Hi there."}])

    out = report.build_chat_report("v1", runs_dir=runs_dir)

    text = out.read_text(encoding="utf-8")
    failure_section = text.split("## Hard failures (variant)")[1].split("##")[0]
    assert "None." in failure_section


def test_build_chat_report_lists_a_self_answer_suspect_with_its_excerpt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _setup_frozen_cases(tmp_path, monkeypatch)
    runs_dir = tmp_path / "runs"
    suspect_turn = (
        "Do you want someone to show you first?\n\nYes, that would help a lot with onboarding."
    )
    _write_sim(runs_dir, "v1", "case-a", 0, [{"role": "assistant", "content": suspect_turn}])

    out = report.build_chat_report("v1", runs_dir=runs_dir)

    text = out.read_text(encoding="utf-8")
    assert "## Self-answer suspects (variant)" in text
    suspect_section = text.split("## Self-answer suspects (variant)")[1]
    assert "case-a" in suspect_section
    assert "Yes, that would help" in suspect_section


def test_build_chat_report_works_with_no_sims_for_the_variant(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _setup_frozen_cases(tmp_path, monkeypatch)
    _write_frozen_case(tmp_path, "frozen-a", [{"role": "assistant", "content": "How's your week?"}])
    runs_dir = tmp_path / "runs"

    out = report.build_chat_report("empty-variant", runs_dir=runs_dir)

    text = out.read_text(encoding="utf-8")
    assert "0 sims for this variant; 1 frozen cases." in text
    assert "n/a" in text
    assert "None." in text


def test_build_chat_report_lists_each_cut_turn_with_the_learners_next_reply(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # #96: Aaron reads every cut turn to check the stop never cut too early, and the
    # learner's next reply shows whether the conversation still made sense.
    _setup_frozen_cases(tmp_path, monkeypatch)
    runs_dir = tmp_path / "runs"
    _write_sim(
        runs_dir,
        "v5",
        "case-a",
        1,
        [
            {"role": "assistant", "content": "Hi, sound right?"},
            {"role": "user", "content": "Yes."},
            {
                "role": "assistant",
                "content": "Which system is it?",
                "stopped": True,
                "removed": "SAP, I'd guess.",
            },
            {"role": "user", "content": "SAP, mostly."},
        ],
    )

    text = report.build_chat_report("v5", runs_dir=runs_dir).read_text(encoding="utf-8")

    assert "## Turns the hard stop cut (variant)" in text
    section = text.split("## Turns the hard stop cut (variant)")[1]
    assert "`case-a` rep 1, turn 3" in section
    assert "Which system is it?" in section
    assert "SAP, mostly." in section
    assert "SAP, I'd guess." in section  # what the stop removed, for Aaron to judge
    assert "chat_offer_reached" in text
