"""CLI: python -m evals.interviewer <command> (spec §4.1). Run from backend/."""

from __future__ import annotations

import argparse
import asyncio

from anthropic import AsyncAnthropic

from evals.interviewer import cases, report, runner, simulate
from src.core.configs.settings import Settings
from src.services.llm_service import AnthropicLlmClient

__all__ = ["build_parser", "main"]


def _require_llm(model_override: str | None) -> tuple[AnthropicLlmClient, str]:
    settings = Settings()
    if settings.llm is None:
        raise SystemExit(
            "backend/.env has no LLM__* settings. The eval never starts without a key, "
            "and never logs it - add LLM__PROVIDER / LLM__MODEL / LLM__API_KEY first."
        )
    model = model_override or settings.llm.model
    anthropic_client = AsyncAnthropic(api_key=settings.llm.api_key.get_secret_value())
    client = AnthropicLlmClient(anthropic_client, model=model)
    return client, model


def _cmd_simulate(args: argparse.Namespace) -> None:
    if args.variant is not None:
        if args.case is not None:
            raise SystemExit("pass either --case or --variant, not both")
        llm, model = _require_llm(None)
        asyncio.run(
            simulate.simulate_variant(
                variant=args.variant,
                case_ids=_parse_case_ids(args.cases),
                reps=args.reps,
                max_usd=args.max_usd,
                interviewer_llm=llm,
                learner_llm=llm,
                expected_model=model,
                hard_stop=args.hard_stop,
            )
        )
        print(f"wrote evals/interviewer/runs/{args.variant}/sims/")
        return
    if args.case is None:
        raise SystemExit("simulate needs either --case <id> or --variant <name>")
    llm, _ = _require_llm(None)
    case = cases.load_case(args.case)
    try:
        simulate.ensure_resimulation_allowed(case, force=args.force)
    except ValueError as exc:
        raise SystemExit(str(exc)) from None
    asyncio.run(
        simulate.simulate_case(
            args.case, interviewer_llm=llm, learner_llm=llm, hard_stop=args.hard_stop
        )
    )
    print(
        f"wrote evals/interviewer/cases/{args.case}.json (status: draft) and review/{args.case}.md"
    )


def _cmd_review(args: argparse.Namespace) -> None:
    case_ids = [args.case] if args.case else cases.list_case_ids()
    for case_id in case_ids:
        simulate.write_review_page(cases.load_case(case_id))
    if args.case:
        print(f"wrote evals/interviewer/review/{args.case}.md")
    else:
        print(f"wrote {len(case_ids)} review pages")


def _cmd_approve(args: argparse.Namespace) -> None:
    try:
        simulate.approve_case(args.case)
    except ValueError as exc:
        raise SystemExit(str(exc)) from None
    print(f"{args.case}: approved")


def _parse_case_ids(raw: str | None) -> list[str] | None:
    if not raw:
        return None
    return [stripped for c in raw.split(",") if (stripped := c.strip())]


def _cmd_run(args: argparse.Namespace) -> None:
    llm, model = _require_llm(args.model)
    case_ids = _parse_case_ids(args.cases)
    the_cases = cases.approved_cases(case_ids)
    asyncio.run(
        runner.run(
            variant=args.variant,
            reps=args.reps,
            cases=the_cases,
            inner_llm=llm,
            expected_model=model,
            max_usd=args.max_usd,
        )
    )


def _cmd_report(args: argparse.Namespace) -> None:
    if not (runner.RUNS_DIR / args.variant / "results.jsonl").exists():
        raise SystemExit(f"no results for variant {args.variant!r}; run it first")
    print(f"wrote {report.build_report()}")


def _cmd_chat_report(args: argparse.Namespace) -> None:
    if not (runner.RUNS_DIR / args.variant / "sims").exists():
        raise SystemExit(f"no sims for variant {args.variant!r}; run `simulate --variant` first")
    print(f"wrote {report.build_chat_report(args.variant)}")


def _cmd_compare(args: argparse.Namespace) -> None:
    print(f"wrote {report.compare(args.variant)}")


def _cmd_regrade(args: argparse.Namespace) -> None:
    summary = runner.regrade(args.variant)
    print(
        f"regraded {summary['rows']} rows for variant {args.variant!r}: hard_rules pass "
        f"{summary['hard_rules_before']} -> {summary['hard_rules_after']}"
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m evals.interviewer")
    sub = parser.add_subparsers(dest="command", required=True)

    p_sim = sub.add_parser("simulate", help="run one interview through the real code + a persona")
    p_sim.add_argument(
        "--case", default=None, help="simulate one frozen case (writes cases/+review/)"
    )
    p_sim.add_argument("--force", action="store_true")
    p_sim.add_argument(
        "--variant", default=None, help="simulate a variant's sims (writes runs/<name>/sims/ only)"
    )
    p_sim.add_argument("--cases", default=None, help="with --variant: restrict to these case ids")
    p_sim.add_argument("--reps", type=int, default=1, help="with --variant: repetitions per case")
    p_sim.add_argument(
        "--max-usd",
        type=float,
        default=10.0,
        dest="max_usd",
        help=(
            "with --variant: stop starting new sims once billed spend reaches this (default: 10.0)"
        ),
    )
    p_sim.add_argument(
        "--hard-stop",
        action="store_true",
        dest="hard_stop",
        help=(
            "end each interviewer chat turn at its first question, as "
            "LLM__INTERVIEW_HARD_STOP does in the hub (#96); with --case too, so a frozen "
            "transcript never carries an invented answer"
        ),
    )
    p_sim.set_defaults(func=_cmd_simulate)

    p_rev = sub.add_parser(
        "review", help="rewrite review/<id>.md from the case file on disk (no model calls)"
    )
    rev_group = p_rev.add_mutually_exclusive_group(required=True)
    rev_group.add_argument("--case", default=None)
    rev_group.add_argument("--all", action="store_true")
    p_rev.set_defaults(func=_cmd_review)

    p_app = sub.add_parser("approve", help="mark a reviewed case approved")
    p_app.add_argument("--case", required=True)
    p_app.set_defaults(func=_cmd_approve)

    p_run = sub.add_parser("run", help="turn approved cases into playbooks and grade them")
    p_run.add_argument("--variant", required=True)
    p_run.add_argument("--reps", type=int, default=3)
    p_run.add_argument("--cases", default=None)
    p_run.add_argument("--model", default=None)
    p_run.add_argument(
        "--max-usd",
        type=float,
        default=10.0,
        dest="max_usd",
        help=(
            "stop starting new attempts once billed spend reaches this many USD "
            "(default: 10.0). This key lives in a shared workspace with no separate "
            "spend limit, so there is no unlimited option."
        ),
    )
    p_run.set_defaults(func=_cmd_run)

    p_rep = sub.add_parser(
        "report", help="rebuilds runs/report.html, covering every variant present"
    )
    p_rep.add_argument("--variant", required=True)
    p_rep.set_defaults(func=_cmd_report)

    p_chat_rep = sub.add_parser(
        "chat-report",
        help="writes runs/<name>/chat.md: chat checks over a variant's sims vs. the "
        "frozen set (no model calls)",
    )
    p_chat_rep.add_argument("--variant", required=True)
    p_chat_rep.set_defaults(func=_cmd_chat_report)

    p_cmp = sub.add_parser("compare", help="write the baseline-vs-variant comparison page")
    p_cmp.add_argument("--variant", required=True)
    p_cmp.set_defaults(func=_cmd_compare)

    p_regrade = sub.add_parser(
        "regrade",
        help=(
            "recomputes checks against each row's recorded trace and rewrites "
            "results.jsonl; no model calls"
        ),
    )
    p_regrade.add_argument("--variant", required=True)
    p_regrade.set_defaults(func=_cmd_regrade)

    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
