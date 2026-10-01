"""Turns approved cases into playbooks and grades them (spec §4.2). Up to 4 (case, rep)
attempts in flight; resume skips a (case, rep) already in results.jsonl (an errored pair is
not "finished" and is retried); a spend cap stops new attempts from starting once the
running total - every dollar already billed, successful or errored - reaches it."""

from __future__ import annotations

import asyncio
import json
import time
import uuid
from pathlib import Path
from types import SimpleNamespace
from typing import TYPE_CHECKING, Any

import anthropic

from evals.interviewer import cases, checks, pricing
from evals.interviewer.fakes import (
    InMemoryConversationRepository,
    InMemoryMessageRepository,
    build_context,
)
from evals.interviewer.recording import RecordingLlmClient
from src.services.exceptions import ConflictError, DomainError
from src.services.interview_service import InterviewService

if TYPE_CHECKING:
    from src.services.llm_service import LlmClient

__all__ = ["RUNS_DIR", "regrade", "run"]

RUNS_DIR = Path(__file__).resolve().parent / "runs"
_MAX_CONCURRENCY = 4


def _append_jsonl(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def _existing_keys(results_path: Path) -> set[tuple[str, int]]:
    if not results_path.exists():
        return set()
    keys = set()
    for line in results_path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            row = json.loads(line)
            keys.add((row["prompt_id"], row["rep"]))
    return keys


def _served_model_ok(expected: str, served: str | None) -> bool:
    """R4: the provider is allowed to serve a dated snapshot of the requested model id
    (e.g. `claude-sonnet-5-20260615` for a request of `claude-sonnet-5`), not only the
    exact id back."""
    return served is None or served == expected or served.startswith(expected + "-")


def _classify_domain_error(exc: DomainError, calls: list[dict[str, Any]]) -> str:
    """R5: a max_tokens stop on any recorded call means the generation was cut short,
    regardless of which message DomainError happened to carry - that takes priority over
    the message-based classification below."""
    if any(c["usage"].stop_reason == "max_tokens" for c in calls):
        return "truncated"
    message = exc.message.lower()
    if "took too long" in message:
        return "timeout"
    if "busy" in message:
        return "provider_unavailable"
    # A non-transient provider failure (auth, bad request, ...) reaches us as a neutral
    # AiGenerationError whose cause is the SDK error.
    if isinstance(exc.__cause__, anthropic.APIError):
        return "provider_error"
    if "too long" in message:
        return "transcript_too_large"
    return "generation_failed"


def _sum_usage(calls: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "input_tokens": sum(c["usage"].input_tokens for c in calls),
        "output_tokens": sum(c["usage"].output_tokens for c in calls),
    }


def _bill(recorder: RecordingLlmClient, expected_model: str) -> float:
    return pricing.cost_usd(model=expected_model, **_sum_usage(recorder.calls))


async def _run_one(
    case: dict[str, Any],
    rep: int,
    *,
    variant_dir: Path,
    inner_llm: LlmClient,
    expected_model: str,
) -> float | None:
    """Runs one (case, rep) attempt. Returns the USD cost billed (0.0 or more), or None
    when nothing was billed (build_playbook raised ConflictError before any LLM call)."""
    conversations = InMemoryConversationRepository()
    messages = InMemoryMessageRepository()
    # The case's chosen interview language (#83); a case without one is English.
    conversation = conversations.seed(
        user_id=uuid.uuid4(), kind="interview", language=case.get("language", "en")
    )
    messages.seed(conversation.id, case["transcript"])
    context = build_context(case)
    recorder = RecordingLlmClient(inner_llm)
    service = InterviewService(conversations, messages, recorder, context)
    user = SimpleNamespace(
        id=conversation.user_id,
        first_name=case["user"]["first_name"],
        last_name=case["user"]["last_name"],
    )

    started = time.monotonic()
    try:
        await service.build_playbook(user=user)  # ty: ignore[invalid-argument-type]
    except ConflictError as exc:
        _append_jsonl(
            variant_dir / "errors.jsonl",
            {
                "prompt_id": case["id"],
                "rep": rep,
                "failure_class": "not_ready",
                "message": str(exc),
            },
        )
        return None
    except DomainError as exc:
        cost = _bill(recorder, expected_model)
        _append_jsonl(
            variant_dir / "errors.jsonl",
            {
                "prompt_id": case["id"],
                "rep": rep,
                "failure_class": _classify_domain_error(exc, recorder.calls),
                "message": str(exc),
                "usage": _sum_usage(recorder.calls),
                "cost_usd": cost,
            },
        )
        return cost
    except anthropic.APIError as exc:
        # R6: InterviewService wraps every provider error into AiGenerationError (a
        # DomainError, classified above). Kept as a guard: should a raw SDK error ever
        # escape, absorb it so one bad case/rep does not take the whole run down, but
        # bill whatever was actually spent before it failed.
        cost = _bill(recorder, expected_model)
        _append_jsonl(
            variant_dir / "errors.jsonl",
            {
                "prompt_id": case["id"],
                "rep": rep,
                "failure_class": "provider_error",
                "message": str(exc),
                "usage": _sum_usage(recorder.calls),
                "cost_usd": cost,
            },
        )
        return cost
    latency = time.monotonic() - started

    last_usage = recorder.calls[-1]["usage"]
    served_model = last_usage.model or recorder.model
    if not _served_model_ok(expected_model, last_usage.model):
        cost = _bill(recorder, expected_model)
        _append_jsonl(
            variant_dir / "errors.jsonl",
            {
                "prompt_id": case["id"],
                "rep": rep,
                "failure_class": "served_model_mismatch",
                "message": f"asked for {expected_model!r}, served {served_model!r}",
                "usage": _sum_usage(recorder.calls),
                "cost_usd": cost,
            },
        )
        return cost

    cost = _bill(recorder, expected_model)
    reloaded = await conversations.get_by_id(conversation.id)
    assert reloaded is not None
    assert reloaded.summary is not None
    playbook = {"internal": reloaded.summary["internal"], "shared": reloaded.summary["shared"]}
    raw_output = recorder.calls[-1]["raw_output"]

    results = checks.run_all(case, playbook, raw_output)
    grade = {check_id: r.value for check_id, r in results.items()}
    explanation = {check_id: r.evidence for check_id, r in results.items() if r.evidence}
    grade.update(
        {
            **_sum_usage(recorder.calls),
            "latency_s": latency,
            "attempts": reloaded.summary["meta"]["attempts"],
            "cost_usd": cost,
        }
    )

    status = "truncated" if last_usage.stop_reason == "max_tokens" else "ok"
    _append_jsonl(
        variant_dir / "results.jsonl",
        {
            "prompt_id": case["id"],
            "rep": rep,
            "tags": case.get("tags", []),
            "status": status,
            "stop_reason": last_usage.stop_reason,
            "model": served_model,
            "usage": _sum_usage(recorder.calls),
            "latency_s": latency,
            "grade": grade,
            "explanation": explanation,
            "meta": reloaded.summary["meta"],
        },
    )
    trace_dir = variant_dir / "traces"
    trace_dir.mkdir(parents=True, exist_ok=True)
    (trace_dir / f"{case['id']}_rep{rep}.json").write_text(
        json.dumps(
            {
                "system_prompt": recorder.calls[-1]["system"],
                "generate_instruction": recorder.calls[-1]["prompt"],
                "raw_output": raw_output,
                "playbook": playbook,
                "evidence": explanation,
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return cost


def _sum_jsonl_cost(path: Path, *, cost_key_path: tuple[str, ...]) -> float:
    if not path.exists():
        return 0.0
    total = 0.0
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row: Any = json.loads(line)
        for key in cost_key_path:
            row = row.get(key, {})
        total += row if isinstance(row, int | float) else 0.0
    return total


def _committed_spend(variant_dir: Path) -> float:
    """Every dollar already billed for this variant: successful attempts (results.jsonl,
    cost nested under "grade") and errored-but-billed attempts (errors.jsonl, a DomainError
    or anthropic.APIError attempt still calls the LLM and gets billed before it fails - a
    ConflictError attempt never calls the LLM, so its error row has no "cost_usd" key and
    contributes 0). Errored pairs are never written to results.jsonl, so `_existing_keys`
    never skips them and `run()` will re-attempt (and re-bill) them on the next call; that's
    intended (resume only skips *finished* pairs), but the spend total must still count
    what was already spent on them, or a spend cap resets to zero every restart."""
    return _sum_jsonl_cost(
        variant_dir / "results.jsonl", cost_key_path=("grade", "cost_usd")
    ) + _sum_jsonl_cost(variant_dir / "errors.jsonl", cost_key_path=("cost_usd",))


async def run(
    *,
    variant: str,
    reps: int,
    cases: list[dict[str, Any]],
    inner_llm: LlmClient,
    expected_model: str,
    max_usd: float | None,
    runs_dir: Path = RUNS_DIR,
) -> None:
    if expected_model not in pricing.PRICE_PER_MTOK:
        raise SystemExit(
            f"no price on file for {expected_model!r}; add it to "
            "pricing.PRICE_PER_MTOK before running (fails fast, before any attempt "
            "starts, so nothing gets billed against a model this eval cannot price)"
        )
    if not cases:
        raise SystemExit("no approved cases to run (simulate + approve first)")
    variant_dir = runs_dir / variant
    existing = _existing_keys(variant_dir / "results.jsonl")
    pending = [(c, r) for c in cases for r in range(reps) if (c["id"], r) not in existing]
    if not pending:
        return

    spend = {"total": _committed_spend(variant_dir)}
    stop = {"hit": False}
    spend_lock = asyncio.Lock()
    semaphore = asyncio.Semaphore(_MAX_CONCURRENCY)

    async def _worker(case: dict[str, Any], rep: int) -> None:
        async with semaphore:
            async with spend_lock:
                if stop["hit"]:
                    return
                if max_usd is not None and spend["total"] >= max_usd:
                    stop["hit"] = True
                    return
            cost = await _run_one(
                case,
                rep,
                variant_dir=variant_dir,
                inner_llm=inner_llm,
                expected_model=expected_model,
            )
            if cost is not None:
                async with spend_lock:
                    spend["total"] += cost

    await asyncio.gather(*(_worker(c, r) for c, r in pending))
    if stop["hit"]:
        raise SystemExit(
            f"spend cap ${max_usd:.2f} reached at ${spend['total']:.2f}; re-run the same "
            "command to continue (resume skips finished pairs)"
        )


def regrade(variant: str, runs_dir: Path = RUNS_DIR) -> dict[str, int]:
    """Recomputes `checks.run_all` against each row's already-recorded trace (its
    `playbook`/`raw_output`) with no model calls, for tuning the checks/vocabulary after a
    run without re-spending on the LLM. Overwrites every check key in `grade` (including
    `hard_rules`) and the whole `explanation` dict; every other `grade` key (usage,
    latency, attempts, cost) and every other row field is left untouched. Also rewrites
    each trace's `evidence` to match. `results.jsonl` is rewritten atomically (temp file +
    replace) so a crash mid-write cannot corrupt it."""
    variant_dir = runs_dir / variant
    results_path = variant_dir / "results.jsonl"
    if not results_path.exists():
        raise SystemExit(f"no results for variant {variant!r}; nothing to regrade")

    rows = [
        json.loads(line)
        for line in results_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    hard_before = sum(1 for row in rows if row.get("grade", {}).get("hard_rules") == 1.0)

    for row in rows:
        prompt_id, rep = row["prompt_id"], row["rep"]
        case = cases.load_case(prompt_id)
        trace_path = variant_dir / "traces" / f"{prompt_id}_rep{rep}.json"
        if not trace_path.exists():
            raise SystemExit(
                f"no trace file for {prompt_id!r} rep {rep}: {trace_path} "
                "(results.jsonl left untouched)"
            )
        trace = json.loads(trace_path.read_text(encoding="utf-8"))
        results = checks.run_all(case, trace["playbook"], trace["raw_output"])

        row["grade"].update({check_id: r.value for check_id, r in results.items()})
        row["explanation"] = {check_id: r.evidence for check_id, r in results.items() if r.evidence}

        trace["evidence"] = row["explanation"]
        trace_path.write_text(json.dumps(trace, indent=2, ensure_ascii=False), encoding="utf-8")

    hard_after = sum(1 for row in rows if row.get("grade", {}).get("hard_rules") == 1.0)

    tmp_path = results_path.with_suffix(".tmp")
    tmp_path.write_text(
        "\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n", encoding="utf-8"
    )
    tmp_path.replace(results_path)

    return {"rows": len(rows), "hard_rules_before": hard_before, "hard_rules_after": hard_after}
