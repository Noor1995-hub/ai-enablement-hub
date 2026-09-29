from __future__ import annotations

import json

import anthropic
import httpx2
import pytest

from evals.interviewer import cases, simulate
from src.services.llm_service import LlmUsage
from tests.fixtures.llm import FakeLlmReplyStream


class _ConstantLlmClient:
    """Always streams the same reply with the same usage, regardless of call count or
    order - deterministic under the concurrent workers `simulate_variant` runs."""

    model = "fake-model"

    def __init__(self, text: str, usage: LlmUsage, calls: list[None] | None = None) -> None:
        self._text = text
        self._usage = usage
        self.calls = calls if calls is not None else []

    def stream_reply(self, **_: object) -> FakeLlmReplyStream:
        self.calls.append(None)
        return FakeLlmReplyStream([self._text], self._usage)

    async def complete_structured(self, **_: object) -> tuple[dict[str, object], LlmUsage]:
        raise AssertionError("simulate.py must not call complete_structured")


def _interviewer() -> _ConstantLlmClient:
    return _ConstantLlmClient("Tell me about your day?", LlmUsage(input_tokens=5, output_tokens=5))


def _learner() -> _ConstantLlmClient:
    return _ConstantLlmClient("Just a normal day.", LlmUsage(input_tokens=3, output_tokens=3))


def _draft_case(case_id: str, **overrides: object) -> dict[str, object]:
    case = {
        "id": case_id,
        "status": "approved",
        "tags": ["management"],
        "industry": "food production",
        "user": {"first_name": "Lotte", "last_name": "Verbeke"},
        "assessment": {
            "b_freq": "WEEKLY",
            "score_level": "practitioner",
            "effective_level": "practitioner",
            "learning_status": "not_started",
        },
        "persona": "A CFO at a food producer. Clear, detailed answers.",
        "ground_truth": {
            "named_systems": [],
            "workstreams": [],
            "hesitations_voiced": [],
            "hesitations_withdrawn": [],
            "pronouns_stated": None,
        },
        "adversarial": None,
        # A single-turn case keeps every simulation's call count (and so cost) identical
        # and small, regardless of the (deterministic) reply text - one interviewer call
        # for the opener, one for the single chat turn, one learner call.
        "stop_after_answers": 1,
        "transcript": [],
        "simulation": {"model": None, "interview_prompt_version": None, "simulated_at": None},
        "approval": {"approved_at": None, "notes": ""},
    }
    case.update(overrides)
    return case


def _write_cases(tmp_path, monkeypatch: pytest.MonkeyPatch, *case_ids: str) -> None:
    monkeypatch.setattr(cases, "CASES_DIR", tmp_path / "cases")
    monkeypatch.setattr(simulate, "REVIEW_DIR", tmp_path / "review")
    cases.CASES_DIR.mkdir()
    for case_id in case_ids:
        cases.write_case(_draft_case(case_id))


async def test_simulate_variant_writes_only_under_runs_variant_sims(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_cases(tmp_path, monkeypatch, "case-a")
    original_case_bytes = (cases.CASES_DIR / "case-a.json").read_bytes()

    await simulate.simulate_variant(
        variant="v1",
        case_ids=["case-a"],
        reps=1,
        max_usd=None,
        interviewer_llm=_interviewer(),
        learner_llm=_learner(),
        expected_model="fake-model",
        runs_dir=tmp_path / "runs",
    )

    sim_path = tmp_path / "runs" / "v1" / "sims" / "case-a_rep0.json"
    assert sim_path.exists()
    sim = json.loads(sim_path.read_text(encoding="utf-8"))
    assert sim["id"] == "case-a"
    assert sim["rep"] == 0
    assert sim["transcript"]
    assert sim["simulation"]["cost_usd"] > 0

    # never writes to cases/ or review/
    assert (cases.CASES_DIR / "case-a.json").read_bytes() == original_case_bytes
    assert not simulate.REVIEW_DIR.exists() or not any(simulate.REVIEW_DIR.iterdir())


async def test_simulate_variant_resume_skips_a_finished_pair(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_cases(tmp_path, monkeypatch, "case-a")
    interviewer_calls: list[None] = []
    learner_calls: list[None] = []
    interviewer = _ConstantLlmClient(
        "Tell me about your day?", LlmUsage(5, 5), calls=interviewer_calls
    )
    learner = _ConstantLlmClient("Just a normal day.", LlmUsage(3, 3), calls=learner_calls)
    runs_dir = tmp_path / "runs"

    await simulate.simulate_variant(
        variant="v1",
        case_ids=["case-a"],
        reps=1,
        max_usd=None,
        interviewer_llm=interviewer,
        learner_llm=learner,
        expected_model="fake-model",
        runs_dir=runs_dir,
    )
    calls_after_first_run = (len(interviewer_calls), len(learner_calls))

    await simulate.simulate_variant(
        variant="v1",
        case_ids=["case-a"],
        reps=2,
        max_usd=None,
        interviewer_llm=interviewer,
        learner_llm=learner,
        expected_model="fake-model",
        runs_dir=runs_dir,
    )

    assert (runs_dir / "v1" / "sims" / "case-a_rep0.json").exists()
    assert (runs_dir / "v1" / "sims" / "case-a_rep1.json").exists()
    # rep 0 was not re-simulated: only rep 1's calls were added the second time.
    assert len(interviewer_calls) == calls_after_first_run[0] * 2
    assert len(learner_calls) == calls_after_first_run[1] * 2


async def test_simulate_variant_returns_with_nothing_to_do_when_everything_is_finished(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_cases(tmp_path, monkeypatch, "case-a")
    runs_dir = tmp_path / "runs"
    await simulate.simulate_variant(
        variant="v1",
        case_ids=["case-a"],
        reps=1,
        max_usd=None,
        interviewer_llm=_interviewer(),
        learner_llm=_learner(),
        expected_model="fake-model",
        runs_dir=runs_dir,
    )

    # no exception, no error - just nothing left to do
    await simulate.simulate_variant(
        variant="v1",
        case_ids=["case-a"],
        reps=1,
        max_usd=None,
        interviewer_llm=_interviewer(),
        learner_llm=_learner(),
        expected_model="fake-model",
        runs_dir=runs_dir,
    )


async def test_simulate_variant_stops_starting_new_sims_once_the_cap_is_reached(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # More cases than the worker concurrency (4), like runner's own spend-cap test: the
    # first batch starts before any cost lands, so the cap can only bite on a later one.
    case_ids = [f"case-{i}" for i in range(6)]
    _write_cases(tmp_path, monkeypatch, *case_ids)

    with pytest.raises(SystemExit, match="spend cap"):
        await simulate.simulate_variant(
            variant="v1",
            case_ids=case_ids,
            reps=1,
            max_usd=1e-9,
            interviewer_llm=_interviewer(),
            learner_llm=_learner(),
            expected_model="fake-model",
            runs_dir=tmp_path / "runs",
        )

    sims_dir = tmp_path / "runs" / "v1" / "sims"
    written = list(sims_dir.glob("*.json")) if sims_dir.exists() else []
    assert 0 < len(written) < 6


async def test_simulate_variant_spend_cap_counts_sims_already_on_disk(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Regression (mirrors runner._committed_spend): the cap must account for the cost of
    sims already written for this variant, or restarting the same command resets the
    running total to zero and never actually caps anything."""
    _write_cases(tmp_path, monkeypatch, "case-a", "case-b")
    runs_dir = tmp_path / "runs"

    await simulate.simulate_variant(
        variant="v1",
        case_ids=["case-a"],
        reps=1,
        max_usd=None,
        interviewer_llm=_interviewer(),
        learner_llm=_learner(),
        expected_model="fake-model",
        runs_dir=runs_dir,
    )
    committed = json.loads(
        (runs_dir / "v1" / "sims" / "case-a_rep0.json").read_text(encoding="utf-8")
    )["simulation"]["cost_usd"]
    assert committed > 0

    with pytest.raises(SystemExit, match="spend cap"):
        await simulate.simulate_variant(
            variant="v1",
            case_ids=["case-a", "case-b"],
            reps=1,
            max_usd=committed,  # already met by case-a alone
            interviewer_llm=_interviewer(),
            learner_llm=_learner(),
            expected_model="fake-model",
            runs_dir=runs_dir,
        )

    assert not (runs_dir / "v1" / "sims" / "case-b_rep0.json").exists()


async def test_simulate_variant_refuses_an_unpriced_model_before_anything_runs(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_cases(tmp_path, monkeypatch, "case-a")

    with pytest.raises(SystemExit, match="PRICE_PER_MTOK"):
        await simulate.simulate_variant(
            variant="v1",
            case_ids=["case-a"],
            reps=1,
            max_usd=None,
            interviewer_llm=_interviewer(),
            learner_llm=_learner(),
            expected_model="not-a-real-model",
            runs_dir=tmp_path / "runs",
        )

    assert not (tmp_path / "runs" / "v1").exists()


async def test_simulate_variant_uses_every_case_on_disk_when_cases_not_given(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_cases(tmp_path, monkeypatch, "case-a", "case-b")

    await simulate.simulate_variant(
        variant="v1",
        case_ids=None,
        reps=1,
        max_usd=None,
        interviewer_llm=_interviewer(),
        learner_llm=_learner(),
        expected_model="fake-model",
        runs_dir=tmp_path / "runs",
    )

    sims_dir = tmp_path / "runs" / "v1" / "sims"
    assert {p.stem for p in sims_dir.glob("*.json")} == {"case-a_rep0", "case-b_rep0"}


async def test_simulate_variant_refuses_with_no_cases_at_all(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(cases, "CASES_DIR", tmp_path / "cases")
    cases.CASES_DIR.mkdir()

    with pytest.raises(SystemExit, match="no cases to simulate"):
        await simulate.simulate_variant(
            variant="v1",
            case_ids=None,
            reps=1,
            max_usd=None,
            interviewer_llm=_interviewer(),
            learner_llm=_learner(),
            expected_model="fake-model",
            runs_dir=tmp_path / "runs",
        )


def _auth_error() -> Exception:
    request = httpx2.Request("POST", "https://api.anthropic.com/v1/messages")
    return anthropic.AuthenticationError(
        "boom", response=httpx2.Response(401, request=request), body=None
    )


class _FailingForPersonaLearner(_ConstantLlmClient):
    """Raises `exc` on the learner call for the case whose persona contains `marker`; every
    other case gets a normal reply. The interviewer's opener has already been billed by
    then, so the failed sim has a real, nonzero cost."""

    def __init__(self, marker: str, exc: Exception) -> None:
        super().__init__("Just a normal day.", LlmUsage(input_tokens=3, output_tokens=3))
        self._marker = marker
        self._exc = exc

    def stream_reply(self, **kwargs: object) -> FakeLlmReplyStream:
        if self._marker in str(kwargs.get("system", "")):
            raise self._exc
        return super().stream_reply(**kwargs)


def _write_failing_and_ok_cases(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cases, "CASES_DIR", tmp_path / "cases")
    monkeypatch.setattr(simulate, "REVIEW_DIR", tmp_path / "review")
    cases.CASES_DIR.mkdir()
    cases.write_case(_draft_case("case-fail", persona="FAILME persona"))
    cases.write_case(_draft_case("case-ok"))


async def test_a_failed_sim_is_billed_logged_and_the_rest_carry_on(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_failing_and_ok_cases(tmp_path, monkeypatch)

    await simulate.simulate_variant(
        variant="v1",
        case_ids=["case-fail", "case-ok"],
        reps=1,
        max_usd=None,
        interviewer_llm=_interviewer(),
        learner_llm=_FailingForPersonaLearner("FAILME", _auth_error()),
        expected_model="fake-model",
        runs_dir=tmp_path / "runs",
    )

    variant_dir = tmp_path / "runs" / "v1"
    assert (variant_dir / "sims" / "case-ok_rep0.json").exists()
    assert not (variant_dir / "sims" / "case-fail_rep0.json").exists()
    errors = [
        json.loads(line)
        for line in (variant_dir / "sim_errors.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    assert [(e["case_id"], e["rep"], e["error"]) for e in errors] == [
        ("case-fail", 0, "AuthenticationError")
    ]
    assert errors[0]["cost_usd"] > 0


async def test_the_spend_cap_counts_cost_billed_by_earlier_failed_sims(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_cases(tmp_path, monkeypatch, "case-a")
    variant_dir = tmp_path / "runs" / "v1"
    variant_dir.mkdir(parents=True)
    (variant_dir / "sim_errors.jsonl").write_text(
        json.dumps({"case_id": "case-a", "rep": 0, "cost_usd": 1.0, "error": "X", "message": ""})
        + "\n",
        encoding="utf-8",
    )

    with pytest.raises(SystemExit, match="spend cap"):
        await simulate.simulate_variant(
            variant="v1",
            case_ids=["case-a"],
            reps=1,
            max_usd=0.5,
            interviewer_llm=_interviewer(),
            learner_llm=_learner(),
            expected_model="fake-model",
            runs_dir=tmp_path / "runs",
        )

    assert not (variant_dir / "sims").exists()


async def test_an_unexpected_error_is_still_billed_before_it_propagates(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_failing_and_ok_cases(tmp_path, monkeypatch)

    with pytest.raises(RuntimeError, match="bug"):
        await simulate.simulate_variant(
            variant="v1",
            case_ids=["case-fail"],
            reps=1,
            max_usd=None,
            interviewer_llm=_interviewer(),
            learner_llm=_FailingForPersonaLearner("FAILME", RuntimeError("bug")),
            expected_model="fake-model",
            runs_dir=tmp_path / "runs",
        )

    errors = (tmp_path / "runs" / "v1" / "sim_errors.jsonl").read_text(encoding="utf-8")
    assert '"error": "RuntimeError"' in errors
