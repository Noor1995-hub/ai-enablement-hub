from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import anthropic
import httpx2
import pytest

from evals.interviewer import cases as cases_module
from evals.interviewer import runner
from src.services.llm_service import LlmUsage
from tests.fixtures.llm import FakeLlmClient

_EXTRACTION: dict[str, Any] = {
    "internal": {
        "input_quality": {"tier": "RICH", "evidence": "x", "what_to_probe_next": []},
        "person": {
            "role_reality": "x",
            "influence": "x",
            "decision_rights": "x",
            "champion_potential": "x",
            "confidence": "high",
        },
        "pains": [],
        "blockers": {"stated": [], "diagnosed": []},
        "maturity": {
            "placement": "x",
            "behavioural_evidence": "x",
            "vs_self_reported": "x",
            "trajectory": "x",
        },
        "systems_landscape": [],
        "company_context": "x",
        "engagement_notes": {"opportunities": [], "risks": [], "follow_up_questions": []},
    },
    "shared": {
        "where_you_are_today": "x " * 130,
        "use_cases": [
            {
                "rank": 1,
                "start_here": True,
                "name": "Automate the reconciliation",
                "pain_it_kills": "the monthly close",
                "in_practice": "x",
                "before": "x",
                "after": "x",
                "impact": "x",
                "difficulty": "Quick Win",
                "systems_involved": [],
                "assumption_to_check": None,
                "cross_functional": True,
            },
        ],
        "next_moves": [
            {"order": 1, "move": "x", "why_now": "x", "linked_use_case": 1},
            {"order": 2, "move": "x", "why_now": "x", "linked_use_case": 1},
        ],
        "reframes": [
            {"their_hesitation": "x", "the_concern": "x", "reframe": "x", "first_proof": "x"},
            {"their_hesitation": "y", "the_concern": "x", "reframe": "x", "first_proof": "x"},
        ],
        "do_this_today": {"action": "x", "time_required": "10 minutes", "why_this_one": "x"},
    },
}


def _case(case_id: str) -> dict[str, Any]:
    return {
        "id": case_id,
        "tags": ["management"],
        "status": "approved",
        "user": {"first_name": "Alex", "last_name": "Doe"},
        "assessment": {},
        "adversarial": None,
        "ground_truth": {
            "named_systems": [],
            "workstreams": [],
            "hesitations_withdrawn": [],
            "pronouns_stated": None,
        },
        "transcript": [
            {"role": "assistant", "content": "Hi, what do you do?"},
            {"role": "user", "content": "I run the monthly close."},
            {"role": "assistant", "content": "Shall I build it?\n[[READY_TO_BUILD]]"},
        ],
    }


async def test_a_full_run_writes_a_complete_row_and_trace(tmp_path: Path) -> None:
    llm = FakeLlmClient(
        chunks=[],
        structured=_EXTRACTION,
        usage=LlmUsage(10, 20, model="fake-model", stop_reason="tool_use"),
    )

    await runner.run(
        variant="v1",
        reps=1,
        cases=[_case("cfo-food")],
        inner_llm=llm,
        expected_model="fake-model",
        max_usd=None,
        runs_dir=tmp_path,
    )

    rows = [
        json.loads(line)
        for line in (tmp_path / "v1" / "results.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    assert len(rows) == 1
    row = rows[0]
    assert row["prompt_id"] == "cfo-food"
    assert row["rep"] == 0
    assert row["status"] == "ok"
    assert row["model"] == "fake-model"
    assert row["grade"]["hard_rules"] == 1.0
    assert row["grade"]["cost_usd"] > 0
    assert (tmp_path / "v1" / "traces" / "cfo-food_rep0.json").exists()


async def test_a_conflict_error_lands_in_errors_not_results(tmp_path: Path) -> None:
    llm = FakeLlmClient(chunks=[], structured=_EXTRACTION)
    case = _case("thin-case")
    case["transcript"] = [
        {"role": "user", "content": "one answer only"}
    ]  # no offer, below the floor

    await runner.run(
        variant="v1",
        reps=1,
        cases=[case],
        inner_llm=llm,
        expected_model="fake-model",
        max_usd=None,
        runs_dir=tmp_path,
    )

    assert not (tmp_path / "v1" / "results.jsonl").exists()
    errors = [
        json.loads(line)
        for line in (tmp_path / "v1" / "errors.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    assert errors[0]["failure_class"] == "not_ready"


async def test_a_served_model_mismatch_fails_the_attempt(tmp_path: Path) -> None:
    llm = FakeLlmClient(
        chunks=[],
        structured=_EXTRACTION,
        usage=LlmUsage(10, 20, model="claude-other", stop_reason="tool_use"),
    )

    await runner.run(
        variant="v1",
        reps=1,
        cases=[_case("cfo-food")],
        inner_llm=llm,
        expected_model="fake-model",
        max_usd=None,
        runs_dir=tmp_path,
    )

    assert not (tmp_path / "v1" / "results.jsonl").exists()
    errors = [
        json.loads(line)
        for line in (tmp_path / "v1" / "errors.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    assert errors[0]["failure_class"] == "served_model_mismatch"
    # F4: consistency with the other error rows (DomainError, APIError) also carry usage.
    assert errors[0]["usage"] == {"input_tokens": 10, "output_tokens": 20}


async def test_run_refuses_an_unknown_model_before_spending_anything(tmp_path: Path) -> None:
    """F4: an unpriced `expected_model` must fail fast, before any (case, rep) attempt
    starts - not partway through billing, once `_bill` happens to raise."""
    llm = FakeLlmClient(
        chunks=[],
        structured=_EXTRACTION,
        usage=LlmUsage(10, 20, model="not-a-real-model", stop_reason="tool_use"),
    )

    with pytest.raises(SystemExit, match="PRICE_PER_MTOK"):
        await runner.run(
            variant="v1",
            reps=1,
            cases=[_case("cfo-food")],
            inner_llm=llm,
            expected_model="not-a-real-model",
            max_usd=None,
            runs_dir=tmp_path,
        )

    assert not (tmp_path / "v1").exists()


async def test_a_served_model_dated_snapshot_passes(tmp_path: Path) -> None:
    """R4: a dated snapshot of the expected model id (e.g. what the provider serves the
    day after a release) is not a mismatch."""
    llm = FakeLlmClient(
        chunks=[],
        structured=_EXTRACTION,
        usage=LlmUsage(10, 20, model="fake-model-20260101", stop_reason="tool_use"),
    )

    await runner.run(
        variant="v1",
        reps=1,
        cases=[_case("cfo-food")],
        inner_llm=llm,
        expected_model="fake-model",
        max_usd=None,
        runs_dir=tmp_path,
    )

    assert not (tmp_path / "v1" / "errors.jsonl").exists()
    rows = [
        json.loads(line)
        for line in (tmp_path / "v1" / "results.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    assert rows[0]["model"] == "fake-model-20260101"


async def test_resume_skips_finished_pairs_when_reps_increases(tmp_path: Path) -> None:
    llm = FakeLlmClient(
        chunks=[],
        structured=_EXTRACTION,
        usage=LlmUsage(10, 20, model="fake-model", stop_reason="tool_use"),
    )
    case = _case("cfo-food")

    await runner.run(
        variant="v1",
        reps=1,
        cases=[case],
        inner_llm=llm,
        expected_model="fake-model",
        max_usd=None,
        runs_dir=tmp_path,
    )
    await runner.run(
        variant="v1",
        reps=3,
        cases=[case],
        inner_llm=llm,
        expected_model="fake-model",
        max_usd=None,
        runs_dir=tmp_path,
    )

    rows = [
        json.loads(line)
        for line in (tmp_path / "v1" / "results.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    assert sorted(r["rep"] for r in rows) == [0, 1, 2]


async def test_spend_cap_stops_new_work_without_discarding_completed_attempts(
    tmp_path: Path,
) -> None:
    llm = FakeLlmClient(
        chunks=[],
        structured=_EXTRACTION,
        usage=LlmUsage(10, 20, model="fake-model", stop_reason="tool_use"),
    )
    cases = [_case(f"case-{i}") for i in range(6)]

    with pytest.raises(SystemExit, match="spend cap"):
        await runner.run(
            variant="v1",
            reps=1,
            cases=cases,
            inner_llm=llm,
            expected_model="fake-model",
            max_usd=1e-9,
            runs_dir=tmp_path,
        )

    rows = (tmp_path / "v1" / "results.jsonl").read_text(encoding="utf-8").splitlines()
    assert 0 < len(rows) < 6


async def test_spend_cap_accounts_for_cost_already_billed_in_errors_jsonl(
    tmp_path: Path,
) -> None:
    """Regression: a DomainError attempt still calls the LLM and gets billed before it
    fails, but (being an error, not a finished pair) it is retried on the next `run()` -
    `_committed_spend` must count that prior billed cost or the spend cap resets to zero
    on every restart and never actually caps anything."""
    erroring_llm = FakeLlmClient(
        chunks=[],
        structured={"not": "a valid extraction"},
        usage=LlmUsage(10, 20, model="fake-model", stop_reason="tool_use"),
    )
    case_a = _case("cfo-food")

    await runner.run(
        variant="v1",
        reps=1,
        cases=[case_a],
        inner_llm=erroring_llm,
        expected_model="fake-model",
        max_usd=None,
        runs_dir=tmp_path,
    )

    assert not (tmp_path / "v1" / "results.jsonl").exists()
    errors = [
        json.loads(line)
        for line in (tmp_path / "v1" / "errors.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    billed_so_far = errors[0]["cost_usd"]
    assert billed_so_far > 0

    good_llm = FakeLlmClient(
        chunks=[],
        structured=_EXTRACTION,
        usage=LlmUsage(10, 20, model="fake-model", stop_reason="tool_use"),
    )
    case_b = _case("second-case")

    with pytest.raises(SystemExit, match="spend cap"):
        await runner.run(
            variant="v1",
            reps=1,
            cases=[case_a, case_b],
            inner_llm=good_llm,
            expected_model="fake-model",
            max_usd=billed_so_far + 1e-9,  # "just above" what is already billed
            runs_dir=tmp_path,
        )

    # case_a is not a finished pair (it only ever errored), so it is retried here and
    # this time succeeds - that alone (on top of the already-billed cost from the first
    # run) already clears the cap, so case_b must never have started.
    rows = [
        json.loads(line)
        for line in (tmp_path / "v1" / "results.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    assert {r["prompt_id"] for r in rows} == {"cfo-food"}


async def test_a_max_tokens_stop_reason_is_classified_as_truncated_on_the_domain_error_path(
    tmp_path: Path,
) -> None:
    """R5: build_playbook fails after two unusable attempts (invalid structured output),
    and every recorded call reports stop_reason == 'max_tokens' -> failure_class
    'truncated', taking priority over the message-based classification (the DomainError's
    own message here is the generic "Could not generate the playbook" one, which the
    message-based classifier would otherwise call 'generation_failed')."""
    llm = FakeLlmClient(
        chunks=[],
        structured={"not": "a valid extraction"},
        usage=LlmUsage(10, 20, model="fake-model", stop_reason="max_tokens"),
    )

    await runner.run(
        variant="v1",
        reps=1,
        cases=[_case("cfo-food")],
        inner_llm=llm,
        expected_model="fake-model",
        max_usd=None,
        runs_dir=tmp_path,
    )

    assert not (tmp_path / "v1" / "results.jsonl").exists()
    errors = [
        json.loads(line)
        for line in (tmp_path / "v1" / "errors.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    assert errors[0]["failure_class"] == "truncated"
    assert errors[0]["cost_usd"] > 0


async def test_a_successful_row_is_marked_truncated_when_the_last_call_hit_max_tokens(
    tmp_path: Path,
) -> None:
    """R5, success-path half: a usable extraction that nonetheless stopped on
    max_tokens still gets graded, but its row is flagged 'truncated' rather than 'ok'."""
    llm = FakeLlmClient(
        chunks=[],
        structured=_EXTRACTION,
        usage=LlmUsage(10, 20, model="fake-model", stop_reason="max_tokens"),
    )

    await runner.run(
        variant="v1",
        reps=1,
        cases=[_case("cfo-food")],
        inner_llm=llm,
        expected_model="fake-model",
        max_usd=None,
        runs_dir=tmp_path,
    )

    rows = [
        json.loads(line)
        for line in (tmp_path / "v1" / "results.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    assert rows[0]["status"] == "truncated"


def _sdk_error(cls: Any, status: int) -> Exception:
    """A real anthropic status error, built the way the SDK builds one (mirrors
    tests/unit/test_llm_service.py's `_status_error`)."""
    request = httpx2.Request("POST", "https://api.anthropic.com/v1/messages")
    return cls("boom", response=httpx2.Response(status, request=request), body=None)


class _ApiErrorLlmClient:
    """An inner LlmClient whose structured call raises a real (non-transient) anthropic
    SDK error, the way an auth or bad-request failure would, so it escapes
    InterviewService.build_playbook raw (spec: only transient errors get wrapped)."""

    model = "fake-model"

    def __init__(self, exc: Exception) -> None:
        self._exc = exc

    def stream_reply(self, **_: object) -> Any:
        raise NotImplementedError

    async def complete_structured(self, **_: object) -> tuple[dict[str, object], LlmUsage]:
        raise self._exc


async def test_an_escaping_anthropic_api_error_lands_in_errors_as_provider_error(
    tmp_path: Path,
) -> None:
    """R6: a non-transient anthropic.APIError (e.g. AuthenticationError) is not wrapped
    by InterviewService, so it escapes build_playbook raw. The runner must catch it
    itself, write it to errors.jsonl as 'provider_error' with billed usage/cost so far,
    and keep the run alive instead of crashing."""
    exc = _sdk_error(anthropic.AuthenticationError, 401)
    llm = _ApiErrorLlmClient(exc)

    await runner.run(
        variant="v1",
        reps=1,
        cases=[_case("cfo-food"), _case("second-case")],
        inner_llm=llm,
        expected_model="fake-model",
        max_usd=None,
        runs_dir=tmp_path,
    )

    assert not (tmp_path / "v1" / "results.jsonl").exists()
    errors = [
        json.loads(line)
        for line in (tmp_path / "v1" / "errors.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    assert len(errors) == 2
    assert {e["failure_class"] for e in errors} == {"provider_error"}
    assert errors[0]["cost_usd"] == 0.0


def test_regrade_refuses_when_the_variant_has_no_results(tmp_path: Path) -> None:
    with pytest.raises(SystemExit, match="no results"):
        runner.regrade("nope", runs_dir=tmp_path)


def test_regrade_refuses_clearly_when_a_trace_file_is_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(cases_module, "CASES_DIR", tmp_path / "cases")
    cases_module.CASES_DIR.mkdir()
    case = _case("cfo-food")
    case["status"] = "approved"
    cases_module.write_case(case)

    variant_dir = tmp_path / "runs" / "v1"
    (variant_dir / "traces").mkdir(parents=True)  # no trace file written inside
    original_results = json.dumps({"prompt_id": "cfo-food", "rep": 0, "grade": {}}) + "\n"
    (variant_dir / "results.jsonl").write_text(original_results, encoding="utf-8")

    with pytest.raises(SystemExit, match="no trace file"):
        runner.regrade("v1", runs_dir=tmp_path / "runs")

    # results.jsonl must be left exactly as it was - no partial rewrite.
    assert (variant_dir / "results.jsonl").read_text(encoding="utf-8") == original_results


def test_regrade_updates_a_row_whose_playbook_now_passes_and_leaves_signals_alone(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(cases_module, "CASES_DIR", tmp_path / "cases")
    cases_module.CASES_DIR.mkdir()
    case = _case("cfo-food")
    case["status"] = "approved"
    cases_module.write_case(case)

    variant_dir = tmp_path / "runs" / "v1"
    (variant_dir / "traces").mkdir(parents=True)
    good_playbook = {
        "internal": {},
        "shared": {"where_you_are_today": "A clean sentence with no problems at all here."},
    }
    stale_trace = {
        "system_prompt": "x",
        "generate_instruction": "x",
        "raw_output": good_playbook,
        "playbook": good_playbook,
        "evidence": {"no_judging": "practitioner"},  # stale evidence from the old grade
    }
    (variant_dir / "traces" / "cfo-food_rep0.json").write_text(
        json.dumps(stale_trace), encoding="utf-8"
    )

    stale_row = {
        "prompt_id": "cfo-food",
        "rep": 0,
        "status": "ok",
        "grade": {
            "no_judging": 0.0,
            "hard_rules": 0.0,
            "input_tokens": 10,
            "output_tokens": 20,
            "latency_s": 1.5,
            "attempts": 1,
            "cost_usd": 0.05,
        },
        "explanation": {"no_judging": "practitioner"},
    }
    (variant_dir / "results.jsonl").write_text(json.dumps(stale_row) + "\n", encoding="utf-8")

    summary = runner.regrade("v1", runs_dir=tmp_path / "runs")

    assert summary == {"rows": 1, "hard_rules_before": 0, "hard_rules_after": 1}
    rows = [
        json.loads(line)
        for line in (variant_dir / "results.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    assert len(rows) == 1
    row = rows[0]
    assert row["grade"]["no_judging"] == 1.0
    assert row["grade"]["hard_rules"] == 1.0
    # the whole explanation dict is recomputed: the stale hard-rule evidence is gone
    assert "no_judging" not in row["explanation"]
    # signal keys and every other row field untouched
    assert row["grade"]["input_tokens"] == 10
    assert row["grade"]["output_tokens"] == 20
    assert row["grade"]["latency_s"] == 1.5
    assert row["grade"]["attempts"] == 1
    assert row["grade"]["cost_usd"] == 0.05
    assert row["prompt_id"] == "cfo-food"
    assert row["rep"] == 0
    assert row["status"] == "ok"

    updated_trace = json.loads(
        (variant_dir / "traces" / "cfo-food_rep0.json").read_text(encoding="utf-8")
    )
    assert "no_judging" not in updated_trace["evidence"]
    assert updated_trace["evidence"] == row["explanation"]
    assert updated_trace["playbook"] == good_playbook  # untouched


async def test_any_other_exception_still_propagates(tmp_path: Path) -> None:
    """R6: only anthropic.APIError is absorbed; a genuine bug still surfaces."""
    llm = _ApiErrorLlmClient(RuntimeError("bug"))

    with pytest.raises(RuntimeError, match="bug"):
        await runner.run(
            variant="v1",
            reps=1,
            cases=[_case("cfo-food")],
            inner_llm=llm,
            expected_model="fake-model",
            max_usd=None,
            runs_dir=tmp_path,
        )
