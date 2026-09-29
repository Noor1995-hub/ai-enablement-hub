"""results.jsonl -> report.html (via the vendored lite report builder) and compare.md
(pure Python, spec §4.4); chat.md, the chat-level counterpart over sims/ vs. the frozen
cases/ transcripts (spec 2026-09-28) - also pure Python, no model calls."""

from __future__ import annotations

import json
import math
import subprocess
from pathlib import Path
from typing import Any

from evals.interviewer import cases, chat_checks, checks
from evals.interviewer.checks import CheckResult
from evals.interviewer.runner import RUNS_DIR

__all__ = ["build_chat_report", "build_report", "compare"]

_BUILD_SCRIPT = Path(__file__).resolve().parent / "report" / "build-report-lite.mjs"
# Grade keys the runner stamps onto every row that are not one of `checks.ALL_CHECKS`
# (see runner._run_one): all raw, non-rate numbers, so kind `signal`.
_RUNNER_SIGNAL_KEYS = ("input_tokens", "output_tokens", "latency_s", "attempts", "cost_usd")


def build_report(runs_dir: Path = RUNS_DIR) -> Path:
    """Rebuilds runs/report.html from every variant directory present under runs_dir.
    Requires `node` on PATH."""
    subprocess.run(["node", str(_BUILD_SCRIPT), str(runs_dir)], check=True)
    return runs_dir / "report.html"


def _load_rows(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [
        json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
    ]


def _mean(rows: list[dict[str, Any]], check_id: str) -> float:
    values = [
        r["grade"][check_id]
        for r in rows
        if r.get("status") == "ok" and check_id in r.get("grade", {})
    ]
    return sum(values) / len(values) if values else 0.0


def _noise_margin(n_cases: int, reps: int) -> float:
    n = n_cases * reps
    return 1 / math.sqrt(n) if n > 0 else 1.0


def _metric_kinds() -> dict[str, str]:
    """id -> kind ("hard" | "rate" | "score" | "signal") for every key `compare` might see
    in a row's `grade` dict: every check in `checks.ALL_CHECKS` (plus the `hard_rules`
    roll-up run_all adds) reports its own kind on its CheckResult; calling run_all with
    empty case/playbook/raw_output is safe (every check degrades to its "nothing here"
    result rather than raising) and avoids a second, driftable copy of that mapping. The
    runner's own extra columns (usage, latency, cost) are not checks, so they are not in
    that result and are declared here instead (F3)."""
    kinds: dict[str, str] = {}
    for check_id, result in checks.run_all({}, {}, {}).items():
        kinds[check_id] = result.kind
    kinds.update(dict.fromkeys(_RUNNER_SIGNAL_KEYS, "signal"))
    return kinds


def _format_metric(value: float, kind: str) -> str:
    if kind in ("hard", "rate"):
        return f"{value:.0%}"
    if kind == "score":
        return f"{value:.2f}"
    return f"{value:.1f}"  # signal: raw mean, sensible rounding


def _format_diff(diff: float, kind: str) -> str:
    if kind in ("hard", "rate"):
        return f"{diff:+.0%}"
    if kind == "score":
        return f"{diff:+.2f}"
    return f"{diff:+.1f}"


def compare(variant: str, runs_dir: Path = RUNS_DIR) -> Path:
    baseline_rows = _load_rows(runs_dir / "baseline" / "results.jsonl")
    if not baseline_rows:
        raise SystemExit(
            f"no baseline results at {runs_dir / 'baseline' / 'results.jsonl'}; "
            "run the baseline variant first"
        )
    variant_rows = _load_rows(runs_dir / variant / "results.jsonl")
    check_ids = sorted({k for r in baseline_rows + variant_rows for k in r.get("grade", {})})
    kinds = _metric_kinds()
    n_cases = len({r["prompt_id"] for r in baseline_rows}) or 1
    reps = max((r.get("rep", 0) + 1 for r in baseline_rows), default=1)
    margin = _noise_margin(n_cases, reps)

    lines = [f"# Compare: baseline vs {variant}", "", f"Noise margin: about ±{margin:.0%}", ""]

    hard_failures = [r for r in variant_rows if r.get("grade", {}).get("hard_rules") == 0]
    lines += ["## Hard-rule failures (variant)", ""]
    if hard_failures:
        for r in hard_failures:
            hard_evidence = {
                k: v for k, v in r.get("explanation", {}).items() if k in checks.HARD_CHECK_IDS
            }
            lines.append(f"- `{r['prompt_id']}` rep {r.get('rep', 0)}: {hard_evidence}")
    else:
        lines.append("None.")
    lines.append("")

    lines += [
        "## Per-check rates",
        "",
        "| check | baseline | variant | diff | note |",
        "|---|---|---|---|---|",
    ]
    for check_id in check_ids:
        kind = kinds.get(check_id, "signal")
        base_value, var_value = _mean(baseline_rows, check_id), _mean(variant_rows, check_id)
        diff = var_value - base_value
        note = "within noise" if kind in ("hard", "rate") and abs(diff) <= margin else ""
        lines.append(
            f"| {check_id} | {_format_metric(base_value, kind)} | "
            f"{_format_metric(var_value, kind)} | {_format_diff(diff, kind)} | {note} |"
        )

    out = runs_dir / variant / "compare.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out


def _load_sims(variant_dir: Path) -> list[dict[str, Any]]:
    sims_dir = variant_dir / "sims"
    if not sims_dir.exists():
        return []
    return [json.loads(p.read_text(encoding="utf-8")) for p in sorted(sims_dir.glob("*.json"))]


def _load_frozen_cases() -> list[dict[str, Any]]:
    return [cases.load_case(case_id) for case_id in cases.list_case_ids()]


def _chat_results_by_check(rows: list[dict[str, Any]]) -> dict[str, list[CheckResult]]:
    by_check: dict[str, list[CheckResult]] = {
        check.__name__: [] for check in chat_checks.ALL_CHECKS
    }
    for row in rows:
        for check_id, result in chat_checks.run_all(row, row.get("transcript", [])).items():
            by_check[check_id].append(result)
    return by_check


def _format_chat_column(results: list[CheckResult]) -> str:
    if not results:
        return "n/a"
    kind = results[0].kind
    if kind == "signal":
        total = sum(r.value for r in results)
        mean = total / len(results)
        return f"{mean:.2f} avg ({total:.0f} total / {len(results)})"
    if kind == "rate":
        passed = sum(r.value for r in results)
    else:
        passed = sum(1 for r in results if r.value == 1.0)
    return f"{passed / len(results):.0%} ({passed:.0f}/{len(results)})"


def build_chat_report(variant: str, runs_dir: Path = RUNS_DIR) -> Path:
    """Writes runs/<variant>/chat.md: the chat-level checks (chat_checks.py) computed
    over every sim `simulate --variant` wrote for this variant, next to the same checks
    computed over the frozen cases/ transcripts (labelled "frozen set (current prompt)"
    since those were simulated against whatever prompt was live when they were frozen).
    Also lists every hard-check failure and every self-answer suspect with its excerpt,
    for a human to read. No model calls - everything here comes from recorded
    transcripts."""
    variant_dir = runs_dir / variant
    sim_rows = _load_sims(variant_dir)
    frozen_rows = _load_frozen_cases()
    variant_by_check = _chat_results_by_check(sim_rows)
    frozen_by_check = _chat_results_by_check(frozen_rows)

    lines = [
        f"# Chat checks: {variant}",
        "",
        f"{len(sim_rows)} sims for this variant; {len(frozen_rows)} frozen cases.",
        "",
        "| check | kind | variant | frozen set (current prompt) |",
        "|---|---|---|---|",
    ]
    for check in chat_checks.ALL_CHECKS:
        check_id = check.__name__
        variant_results = variant_by_check[check_id]
        frozen_results = frozen_by_check[check_id]
        kind = (variant_results or frozen_results or [CheckResult(check_id, "signal", 0.0, "")])[
            0
        ].kind
        lines.append(
            f"| {check_id} | {kind} | {_format_chat_column(variant_results)} | "
            f"{_format_chat_column(frozen_results)} |"
        )
    lines.append("")

    lines += ["## Hard failures (variant)", ""]
    hard_failures = [
        (row.get("id", "?"), row.get("rep", 0), result)
        for row in sim_rows
        for check_id, result in chat_checks.run_all(row, row.get("transcript", [])).items()
        if check_id in chat_checks.CHAT_HARD_CHECK_IDS and result.value == 0.0
    ]
    if hard_failures:
        for case_id, rep, result in hard_failures:
            lines.append(f"- `{case_id}` rep {rep} [{result.id}]: {result.evidence}")
    else:
        lines.append("None.")
    lines.append("")

    lines += ["## Self-answer suspects (variant)", ""]
    suspects = [
        (row.get("id", "?"), row.get("rep", 0), result)
        for row in sim_rows
        for result in [chat_checks.chat_self_answer_suspect(row, row.get("transcript", []))]
        if result.value > 0
    ]
    if suspects:
        for case_id, rep, result in suspects:
            lines.append(f"- `{case_id}` rep {rep}: {result.evidence}")
    else:
        lines.append("None.")

    out = variant_dir / "chat.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out
