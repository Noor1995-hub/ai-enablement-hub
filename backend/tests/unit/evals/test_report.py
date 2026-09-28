from __future__ import annotations

import json
from pathlib import Path

import pytest

from evals.interviewer import report


def _write_rows(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")


def test_compare_reports_per_check_rates_and_the_noise_margin(tmp_path: Path) -> None:
    _write_rows(
        tmp_path / "baseline" / "results.jsonl",
        [
            {
                "prompt_id": "cfo-food",
                "rep": 0,
                "status": "ok",
                "grade": {"hard_rules": 1, "use_case_count": 1},
            },
            {
                "prompt_id": "cfo-food",
                "rep": 1,
                "status": "ok",
                "grade": {"hard_rules": 1, "use_case_count": 0},
            },
        ],
    )
    _write_rows(
        tmp_path / "v1" / "results.jsonl",
        [
            {
                "prompt_id": "cfo-food",
                "rep": 0,
                "status": "ok",
                "grade": {"hard_rules": 0, "use_case_count": 1},
            },
            {
                "prompt_id": "cfo-food",
                "rep": 1,
                "status": "ok",
                "grade": {"hard_rules": 1, "use_case_count": 1},
            },
        ],
    )

    out = report.compare("v1", runs_dir=tmp_path)

    text = out.read_text(encoding="utf-8")
    assert "hard_rules" in text
    assert "Noise margin" in text
    assert out == tmp_path / "v1" / "compare.md"


def test_compare_lists_hard_rule_failures_first(tmp_path: Path) -> None:
    _write_rows(
        tmp_path / "baseline" / "results.jsonl",
        [{"prompt_id": "c", "rep": 0, "status": "ok", "grade": {"hard_rules": 1}}],
    )
    _write_rows(
        tmp_path / "v1" / "results.jsonl",
        [
            {
                "prompt_id": "c",
                "rep": 0,
                "status": "ok",
                "grade": {"hard_rules": 0},
                "explanation": {"no_judging": "practitioner"},
            }
        ],
    )

    out = report.compare("v1", runs_dir=tmp_path)

    text = out.read_text(encoding="utf-8")
    assert text.index("Hard-rule failures") < text.index("Per-check rates")


def test_compare_formats_a_score_metric_with_two_decimals_and_no_noise_note(
    tmp_path: Path,
) -> None:
    """F3: workstream_coverage etc. are kind `score` - two decimals, never "within
    noise" (that note only applies to hard/rate percentages)."""
    _write_rows(
        tmp_path / "baseline" / "results.jsonl",
        [{"prompt_id": "c", "rep": 0, "status": "ok", "grade": {"workstream_coverage": 0.5}}],
    )
    _write_rows(
        tmp_path / "v1" / "results.jsonl",
        [{"prompt_id": "c", "rep": 0, "status": "ok", "grade": {"workstream_coverage": 0.5}}],
    )

    out = report.compare("v1", runs_dir=tmp_path)

    text = out.read_text(encoding="utf-8")
    row = next(line for line in text.splitlines() if line.startswith("| workstream_coverage"))
    assert "0.50" in row
    assert "%" not in row
    assert "within noise" not in row


def test_compare_formats_a_signal_metric_as_a_raw_mean_with_no_noise_note(
    tmp_path: Path,
) -> None:
    """F3: the runner's extra grade keys (input_tokens, output_tokens, latency_s,
    attempts, cost_usd) are kind `signal` - a raw mean, never a percentage."""
    _write_rows(
        tmp_path / "baseline" / "results.jsonl",
        [{"prompt_id": "c", "rep": 0, "status": "ok", "grade": {"latency_s": 2.0}}],
    )
    _write_rows(
        tmp_path / "v1" / "results.jsonl",
        [{"prompt_id": "c", "rep": 0, "status": "ok", "grade": {"latency_s": 4.0}}],
    )

    out = report.compare("v1", runs_dir=tmp_path)

    text = out.read_text(encoding="utf-8")
    row = next(line for line in text.splitlines() if line.startswith("| latency_s"))
    assert "2.0" in row
    assert "4.0" in row
    assert "%" not in row
    assert "within noise" not in row


def test_compare_refuses_when_the_baseline_has_no_results(tmp_path: Path) -> None:
    _write_rows(
        tmp_path / "v1" / "results.jsonl",
        [{"prompt_id": "c", "rep": 0, "status": "ok", "grade": {"hard_rules": 1}}],
    )

    with pytest.raises(SystemExit, match="baseline"):
        report.compare("v1", runs_dir=tmp_path)


def test_compare_hard_failure_line_shows_only_the_hard_checks_evidence(tmp_path: Path) -> None:
    """F3: the explanation dict on a result row can carry evidence for non-hard checks
    too (e.g. summary_length); the hard-rule-failures section must show only the hard
    checks' own evidence."""
    _write_rows(
        tmp_path / "baseline" / "results.jsonl",
        [{"prompt_id": "c", "rep": 0, "status": "ok", "grade": {"hard_rules": 1}}],
    )
    _write_rows(
        tmp_path / "v1" / "results.jsonl",
        [
            {
                "prompt_id": "c",
                "rep": 0,
                "status": "ok",
                "grade": {"hard_rules": 0},
                "explanation": {
                    "no_judging": "practitioner",
                    "summary_length": "42 words",
                },
            }
        ],
    )

    out = report.compare("v1", runs_dir=tmp_path)

    text = out.read_text(encoding="utf-8")
    failure_line = next(line for line in text.splitlines() if line.startswith("- `c`"))
    assert "no_judging" in failure_line
    assert "practitioner" in failure_line
    assert "summary_length" not in failure_line
    assert "42 words" not in failure_line
