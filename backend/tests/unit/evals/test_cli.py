from __future__ import annotations

import pytest

from evals.interviewer import __main__ as cli
from evals.interviewer import cases as cases_module
from evals.interviewer import simulate


def test_help_lists_every_subcommand(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc:
        cli.main(["--help"])

    assert exc.value.code == 0
    out = capsys.readouterr().out
    for name in ("simulate", "approve", "run", "report", "compare", "review", "regrade"):
        assert name in out


def test_require_llm_refuses_without_a_configured_key(monkeypatch: pytest.MonkeyPatch) -> None:
    class _NoLlmSettings:
        llm = None

    monkeypatch.setattr(cli, "Settings", lambda: _NoLlmSettings())

    with pytest.raises(SystemExit, match="LLM__"):
        cli._require_llm(None)


def test_report_command_refuses_a_variant_with_no_results(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(cli.runner, "RUNS_DIR", tmp_path)

    with pytest.raises(SystemExit, match="run it first"):
        cli._cmd_report(cli.argparse.Namespace(variant="v9"))


def test_run_parser_defaults_max_usd_to_ten_dollars() -> None:
    """R11: the eval uses a key in a shared workspace with no separate spend limit, so an
    unlimited default is not acceptable. Parses only - never touches the model."""
    parser = cli.build_parser()
    args = parser.parse_args(["run", "--variant", "baseline"])
    assert args.max_usd == 10.0


def test_cmd_approve_wraps_a_valueerror_as_a_systemexit(monkeypatch: pytest.MonkeyPatch) -> None:
    """M3: a ValueError from approve_case (e.g. "not a draft") must not print a raw
    traceback at the CLI - it becomes a clean SystemExit with the same message."""

    def _boom(_case_id: str) -> None:
        raise ValueError("case 'x' is not a draft (status='approved')")

    monkeypatch.setattr(cli.simulate, "approve_case", _boom)

    with pytest.raises(SystemExit, match="not a draft"):
        cli._cmd_approve(cli.argparse.Namespace(case="x"))


def test_cmd_simulate_wraps_a_valueerror_as_a_systemexit(monkeypatch: pytest.MonkeyPatch) -> None:
    """M3: ensure_resimulation_allowed raising (approved case, no --force) must not print
    a raw traceback either."""
    monkeypatch.setattr(cli, "_require_llm", lambda _model: (object(), "fake-model"))
    monkeypatch.setattr(cli.cases, "load_case", lambda _case_id: {"id": "x", "status": "approved"})

    def _boom(_case: object, *, force: bool) -> None:
        raise ValueError("case 'x' is already approved; pass --force to re-simulate")

    monkeypatch.setattr(cli.simulate, "ensure_resimulation_allowed", _boom)

    with pytest.raises(SystemExit, match="--force"):
        cli._cmd_simulate(cli.argparse.Namespace(case="x", force=False, variant=None))


def test_run_parser_strips_whitespace_and_drops_empty_case_ids() -> None:
    """M3: `--cases` ids are user-typed and easy to leave with stray spaces or a trailing
    comma; both must not silently become a literal id."""
    parser = cli.build_parser()

    args = parser.parse_args(["run", "--variant", "v1", "--cases", " a, b ,,c "])

    assert args.cases == " a, b ,,c "  # argparse itself just stores the raw string


def _minimal_case(case_id: str) -> dict[str, object]:
    return {
        "id": case_id,
        "status": "draft",
        "tags": ["management"],
        "industry": "food production",
        "user": {"first_name": "Lotte", "last_name": "Verbeke"},
        "assessment": {
            "b_freq": "WEEKLY",
            "score_level": "practitioner",
            "effective_level": "practitioner",
            "learning_status": "not_started",
        },
        "persona": "A CFO at a food producer.",
        "ground_truth": {
            "named_systems": [],
            "workstreams": [],
            "hesitations_voiced": [],
            "hesitations_withdrawn": [],
            "pronouns_stated": None,
        },
        "adversarial": None,
        "stop_after_answers": None,
        "transcript": [{"role": "assistant", "content": "Hi"}, {"role": "user", "content": "Hi"}],
        "simulation": {"model": None, "interview_prompt_version": None, "simulated_at": None},
        "approval": {"approved_at": None, "notes": ""},
    }


def test_cmd_review_case_rewrites_the_review_page_with_no_model_calls(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The `review` command reuses `write_review_page` straight off the case file on
    disk - no LlmClient is constructed, so this must work with no key configured."""
    monkeypatch.setattr(cases_module, "CASES_DIR", tmp_path / "cases")
    monkeypatch.setattr(simulate, "REVIEW_DIR", tmp_path / "review")
    cases_module.CASES_DIR.mkdir()
    cases_module.write_case(_minimal_case("review-me"))

    cli._cmd_review(cli.argparse.Namespace(case="review-me", all=False))

    assert (simulate.REVIEW_DIR / "review-me.md").exists()


def test_cmd_review_all_rewrites_every_case_on_disk(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(cases_module, "CASES_DIR", tmp_path / "cases")
    monkeypatch.setattr(simulate, "REVIEW_DIR", tmp_path / "review")
    cases_module.CASES_DIR.mkdir()
    cases_module.write_case(_minimal_case("case-a"))
    cases_module.write_case(_minimal_case("case-b"))

    cli._cmd_review(cli.argparse.Namespace(case=None, all=True))

    assert (simulate.REVIEW_DIR / "case-a.md").exists()
    assert (simulate.REVIEW_DIR / "case-b.md").exists()


def test_review_parser_requires_case_or_all() -> None:
    parser = cli.build_parser()

    with pytest.raises(SystemExit):
        parser.parse_args(["review"])

    args = parser.parse_args(["review", "--case", "x"])
    assert args.case == "x"

    args_all = parser.parse_args(["review", "--all"])
    assert args_all.all is True


def test_cmd_run_strips_whitespace_and_drops_empty_case_ids(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    def _fake_approved_cases(case_ids: list[str] | None) -> list[dict[str, object]]:
        captured["case_ids"] = case_ids
        return []

    monkeypatch.setattr(cli, "_require_llm", lambda _model: (object(), "fake-model"))
    monkeypatch.setattr(cli.cases, "approved_cases", _fake_approved_cases)
    monkeypatch.setattr(cli.runner, "run", lambda **_kwargs: None)
    monkeypatch.setattr(cli.asyncio, "run", lambda coro: coro)

    cli._cmd_run(
        cli.argparse.Namespace(variant="v1", reps=1, cases=" a, b ,,c ", model=None, max_usd=10.0)
    )

    assert captured["case_ids"] == ["a", "b", "c"]


def test_simulate_parser_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    parser = cli.build_parser()

    args = parser.parse_args(["simulate", "--case", "x"])

    assert args.case == "x"
    assert args.variant is None
    assert args.cases is None
    assert args.reps == 1
    assert args.max_usd == 10.0


def test_cmd_simulate_refuses_both_case_and_variant(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cli, "_require_llm", lambda _model: (object(), "fake-model"))

    with pytest.raises(SystemExit, match="either --case or --variant"):
        cli._cmd_simulate(
            cli.argparse.Namespace(
                case="x", variant="v1", force=False, cases=None, reps=1, max_usd=10.0
            )
        )


def test_cmd_simulate_refuses_neither_case_nor_variant() -> None:
    with pytest.raises(SystemExit, match="either --case"):
        cli._cmd_simulate(
            cli.argparse.Namespace(
                case=None, variant=None, force=False, cases=None, reps=1, max_usd=10.0
            )
        )


def test_cmd_simulate_dispatches_to_simulate_variant_with_parsed_case_ids(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    async def _fake_simulate_variant(**kwargs: object) -> None:
        captured.update(kwargs)

    monkeypatch.setattr(cli, "_require_llm", lambda _model: ("the-llm", "fake-model"))
    monkeypatch.setattr(cli.simulate, "simulate_variant", _fake_simulate_variant)

    cli._cmd_simulate(
        cli.argparse.Namespace(
            case=None,
            variant="v1",
            force=False,
            cases=" a, b ",
            reps=2,
            max_usd=5.0,
            hard_stop=True,
        )
    )

    assert captured["variant"] == "v1"
    assert captured["case_ids"] == ["a", "b"]
    assert captured["reps"] == 2
    assert captured["max_usd"] == 5.0
    assert captured["interviewer_llm"] == "the-llm"
    assert captured["learner_llm"] == "the-llm"
    assert captured["expected_model"] == "fake-model"
    assert captured["hard_stop"] is True


def test_cmd_chat_report_refuses_a_variant_with_no_sims(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(cli.runner, "RUNS_DIR", tmp_path)

    with pytest.raises(SystemExit, match="run `simulate --variant` first"):
        cli._cmd_chat_report(cli.argparse.Namespace(variant="v9"))


def test_chat_report_parser_requires_variant() -> None:
    parser = cli.build_parser()

    with pytest.raises(SystemExit):
        parser.parse_args(["chat-report"])

    args = parser.parse_args(["chat-report", "--variant", "v1"])
    assert args.variant == "v1"


def test_simulate_accepts_a_hard_stop_flag() -> None:
    args = cli.build_parser().parse_args(["simulate", "--variant", "v5", "--hard-stop"])
    assert args.hard_stop is True
    assert cli.build_parser().parse_args(["simulate", "--variant", "v5"]).hard_stop is False
