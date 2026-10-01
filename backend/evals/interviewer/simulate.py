"""One-off simulation: the real interviewer loop (InterviewService.open_interview +
ChatService.send_message) against a second model call playing the persona (spec §3.3).
Needs a real LlmClient; only the `simulate` CLI command constructs one."""

from __future__ import annotations

import asyncio
import json
import re
import uuid
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import TYPE_CHECKING, Any

import anthropic

from evals.interviewer import cases, pricing, vocabulary
from evals.interviewer.cases import load_case, write_case
from evals.interviewer.fakes import (
    TOOLS,
    InMemoryConversationRepository,
    InMemoryMessageRepository,
    build_context,
)
from evals.interviewer.recording import RawTextRecordingLlmClient, UsageCapturingLlmClient
from src.services.chat_service import ChatService, ErrorEvent, TokenEvent
from src.services.exceptions import DomainError
from src.services.interview_marker import has_ready_marker
from src.services.interview_service import _MIN_ANSWERS_WITHOUT_OFFER, InterviewService
from src.services.interview_stop import QuestionCut
from src.services.prompts import prompt_version

if TYPE_CHECKING:
    from src.services.llm_service import LlmClient, LlmUsage

__all__ = [
    "REVIEW_DIR",
    "RUNS_DIR",
    "approve_case",
    "ensure_resimulation_allowed",
    "simulate_case",
    "simulate_variant",
    "write_review_page",
]

REVIEW_DIR = Path(__file__).resolve().parent / "review"
RUNS_DIR = Path(__file__).resolve().parent / "runs"
_MAX_CONCURRENCY = 4
_MAX_ANSWERS = 20
# Same "kind" InterviewService stamps interview_prompt_version with (its _KIND).
_INTERVIEW_KIND = "interview"
# What the API rejects (an empty user message) becomes this instead (M1); the review page
# notes how many times it happened so a reviewer can tell a genuinely terse persona from a
# model that just produced nothing.
_EMPTY_ANSWER_PLACEHOLDER = "(no answer)"
# Told to the persona model on its last allowed turn (F1(a)): the persona has no idea
# `stop_after_answers` exists, so left alone it just keeps answering normally and the
# interviewer usually never gets a chance to offer to build before the loop cuts it off.
_WRAP_UP_INSTRUCTION = (
    "\n\n[This is your last answer: answer briefly, then say you have to leave for a meeting now.]"
)


def _persona_system_prompt(case: dict[str, Any]) -> str:
    return (
        "You are playing a person in a workplace interview about how they use AI at "
        "work. Stay in character; answer only what is asked; match this person's style, "
        "level of detail and stopping point exactly.\n\n"
        f"## Who you are\n{case['persona']}"
    )


async def _learner_reply(
    llm: LlmClient,
    case: dict[str, Any],
    question: str,
    history: list[dict[str, str]],
    *,
    is_last_answer: bool = False,
) -> str:
    content = question + _WRAP_UP_INSTRUCTION if is_last_answer else question
    chunks: list[str] = []
    async with llm.stream_reply(
        system=_persona_system_prompt(case),
        messages=[*history, {"role": "user", "content": content}],
        max_tokens=512,
    ) as reply:
        async for text in reply:
            chunks.append(text)
    return "".join(chunks).strip()


def ensure_resimulation_allowed(case: dict[str, Any], *, force: bool) -> None:
    if case["status"] == "approved" and not force:
        raise ValueError(f"case {case['id']!r} is already approved; pass --force to re-simulate")


async def _run_simulation(
    case: dict[str, Any],
    *,
    interviewer_llm: LlmClient,
    learner_llm: LlmClient,
    hard_stop: bool = False,
) -> dict[str, Any]:
    """The interview loop itself (spec §3.3): the real InterviewService/ChatService
    against a second model call playing the persona. Mutates and returns `case` with
    `status`/`transcript`/`simulation`/`approval` updated; writes nothing to disk - callers
    (`simulate_case` for the frozen set, `simulate_variant` for a variant's sims) decide
    where the result goes."""
    conversations = InMemoryConversationRepository()
    messages = InMemoryMessageRepository()
    context = build_context(case)
    # Raw replies in call order (opener first), so each cut turn can show what it lost.
    raw = RawTextRecordingLlmClient(interviewer_llm)
    interview_service = InterviewService(conversations, messages, raw, context)
    chat_service = ChatService(conversations, messages, raw, interview_hard_stop=hard_stop)
    user = SimpleNamespace(
        id=uuid.uuid4(), first_name=case["user"]["first_name"], last_name=case["user"]["last_name"]
    )

    # The language the learner would pick on the welcome screen (#83); English if unset.
    opener = await interview_service.open_interview(
        user=user,  # ty: ignore[invalid-argument-type]
        language=case.get("language", "en"),
    )
    conversation = await conversations.get_by_id(opener.conversation_id)
    assert conversation is not None

    # From the persona model's point of view, the interviewer's questions are its own
    # `user` turns and its prior answers are its own `assistant` turns (R7). This is the
    # reverse of the interviewer's own transcript, which is built by ChatService/
    # InterviewService below with the persona's answers as `user` turns.
    learner_history: list[dict[str, str]] = []
    question = opener.greeting
    answers = 0
    ready = False
    cap = case.get("stop_after_answers")

    while not ready and answers < _MAX_ANSWERS and (cap is None or answers < cap):
        is_last_answer = cap is not None and answers == cap - 1
        answer = await _learner_reply(
            learner_llm, case, question, learner_history, is_last_answer=is_last_answer
        )
        if not answer:
            answer = _EMPTY_ANSWER_PLACEHOLDER
        learner_history += [
            {"role": "user", "content": question},
            {"role": "assistant", "content": answer},
        ]
        answers += 1
        turn_text = ""
        async for event in chat_service.send_message(
            conversation=conversation,
            content=answer,
            system_suffix=await context.build_briefing(user),  # ty: ignore[invalid-argument-type]
        ):
            if isinstance(event, TokenEvent):
                turn_text += event.text
            elif isinstance(event, ErrorEvent):
                # ChatService reports a failed turn in-band; a simulation must not carry
                # on with half a transcript, so fail loudly. A DomainError, so
                # `simulate --variant` bills and logs it like any other provider failure.
                msg = f"interviewer turn failed: {event.message}"
                raise DomainError(msg)
        ready = has_ready_marker(turn_text)
        question = turn_text

    rows = await messages.list_for_conversation(conversation.id)
    case["status"] = "draft"
    raw_replies = iter(raw.texts)
    case["transcript"] = [
        _transcript_turn(r, next(raw_replies, "") if r.role == "assistant" else "") for r in rows
    ]
    case["simulation"] = {
        "model": interviewer_llm.model,
        "interview_prompt_version": prompt_version(_INTERVIEW_KIND),
        "simulated_at": datetime.now(UTC).isoformat(),
        "hard_stop": hard_stop,
    }
    # M2: any prior approval no longer means anything once the transcript has changed.
    case["approval"] = {"approved_at": None, "notes": ""}
    return case


def _transcript_turn(row: Any, raw_reply: str) -> dict[str, Any]:
    """One stored message as a transcript turn. A turn the hard stop cut (#96) is marked
    `stopped` and carries `removed`, the text the learner never saw (recomputed from the
    raw reply with the same QuestionCut the hub uses), for chat-report to list."""
    turn: dict[str, Any] = {"role": row.role, "content": row.content}
    if (row.metadata_ or {}).get("stopped_at_question"):
        cut = QuestionCut()
        cut.feed(raw_reply)
        cut.finish()
        turn["stopped"] = True
        turn["removed"] = cut.removed
    return turn


async def simulate_case(
    case_id: str,
    *,
    interviewer_llm: LlmClient,
    learner_llm: LlmClient,
    hard_stop: bool = False,
) -> dict[str, Any]:
    case = await _run_simulation(
        load_case(case_id),
        interviewer_llm=interviewer_llm,
        learner_llm=learner_llm,
        hard_stop=hard_stop,
    )
    write_case(case)
    write_review_page(case)
    return case


def _price(usages: list[LlmUsage], expected_model: str) -> float:
    return pricing.cost_usd(
        model=expected_model,
        input_tokens=sum(u.input_tokens for u in usages),
        output_tokens=sum(u.output_tokens for u in usages),
    )


class _SimulationFailed(Exception):
    """A simulation raised partway through; carries what was already billed so the spend
    cap still counts it (PR #95 review)."""

    def __init__(self, cost: float, cause: BaseException) -> None:
        super().__init__(f"{type(cause).__name__}: {cause}")
        self.cost = cost
        self.cause = cause


async def _simulate_and_cost(
    case: dict[str, Any],
    *,
    interviewer_llm: LlmClient,
    learner_llm: LlmClient,
    expected_model: str,
    hard_stop: bool = False,
) -> tuple[dict[str, Any], float]:
    """Runs one simulation, billing every model call made along the way (both the
    interviewer's stream calls and the persona's own) against `expected_model` - the same
    price list `run` uses, so `simulate --variant` fails fast on an unpriced model too.
    If the simulation raises, the calls already made are still priced and reported via
    `_SimulationFailed`, so a failed sim never spends money the cap does not see."""
    usages: list[LlmUsage] = []
    try:
        result = await _run_simulation(
            case,
            interviewer_llm=UsageCapturingLlmClient(interviewer_llm, usages),
            learner_llm=UsageCapturingLlmClient(learner_llm, usages),
            hard_stop=hard_stop,
        )
    except Exception as exc:
        raise _SimulationFailed(_price(usages, expected_model), exc) from exc
    return result, _price(usages, expected_model)


def _sim_path(runs_dir: Path, variant: str, case_id: str, rep: int) -> Path:
    return runs_dir / variant / "sims" / f"{case_id}_rep{rep}.json"


_SIM_ERRORS_FILE = "sim_errors.jsonl"


def _committed_sim_spend(variant_dir: Path) -> float:
    """Every dollar already billed for this variant: finished sims (cost in each sim file)
    plus failed sims (cost in sim_errors.jsonl), so a fail-and-resume loop cannot spend
    past the cap unseen."""
    total = 0.0
    sims_dir = variant_dir / "sims"
    if sims_dir.exists():
        for path in sims_dir.glob("*.json"):
            data = json.loads(path.read_text(encoding="utf-8"))
            total += data.get("simulation", {}).get("cost_usd", 0.0)
    errors = variant_dir / _SIM_ERRORS_FILE
    if errors.exists():
        for line in errors.read_text(encoding="utf-8").splitlines():
            if line.strip():
                total += json.loads(line).get("cost_usd", 0.0)
    return total


async def simulate_variant(
    *,
    variant: str,
    case_ids: list[str] | None,
    reps: int,
    max_usd: float | None,
    interviewer_llm: LlmClient,
    learner_llm: LlmClient,
    expected_model: str,
    runs_dir: Path = RUNS_DIR,
    hard_stop: bool = False,
) -> None:
    """Runs the same simulation loop as `simulate_case` for every (case, rep) pair, but
    writes each result to `runs/<variant>/sims/<case>_rep<k>.json` - never to `cases/` or
    `review/` (spec 2026-09-28). Resumable (skips a (case, rep) file that already exists);
    a spend cap stops starting new sims once the running total - every sim already on disk
    for this variant, plus every sim started this run - reaches it, mirroring `runner.run`."""
    if expected_model not in pricing.PRICE_PER_MTOK:
        raise SystemExit(
            f"no price on file for {expected_model!r}; add it to pricing.PRICE_PER_MTOK "
            "before simulating (fails fast, before any sim starts, so nothing gets billed "
            "against a model this eval cannot price)"
        )
    ids = case_ids if case_ids is not None else cases.list_case_ids()
    if not ids:
        raise SystemExit("no cases to simulate")

    variant_dir = runs_dir / variant
    pending = [
        (case_id, rep)
        for case_id in ids
        for rep in range(reps)
        if not _sim_path(runs_dir, variant, case_id, rep).exists()
    ]
    if not pending:
        return

    spend = {"total": _committed_sim_spend(variant_dir)}
    stop = {"hit": False}
    spend_lock = asyncio.Lock()
    semaphore = asyncio.Semaphore(_MAX_CONCURRENCY)

    async def _worker(case_id: str, rep: int) -> None:
        async with semaphore:
            async with spend_lock:
                if stop["hit"]:
                    return
                if max_usd is not None and spend["total"] >= max_usd:
                    stop["hit"] = True
                    return
            try:
                case, cost = await _simulate_and_cost(
                    load_case(case_id),
                    interviewer_llm=interviewer_llm,
                    learner_llm=learner_llm,
                    expected_model=expected_model,
                    hard_stop=hard_stop,
                )
            except _SimulationFailed as failed:
                # Record the billed cost first, so the cap and a later resume both count it;
                # the message is the exception type + text only, never interview content.
                variant_dir.mkdir(parents=True, exist_ok=True)
                error_row = {
                    "case_id": case_id,
                    "rep": rep,
                    "cost_usd": failed.cost,
                    "error": type(failed.cause).__name__,
                    "message": str(failed.cause)[:300],
                }
                with (variant_dir / _SIM_ERRORS_FILE).open("a", encoding="utf-8") as f:
                    f.write(json.dumps(error_row) + "\n")
                async with spend_lock:
                    spend["total"] += failed.cost
                if isinstance(failed.cause, DomainError | anthropic.APIError):
                    return  # provider/service failure: logged and billed; the rest carry on
                raise failed.cause from failed
            case["simulation"]["cost_usd"] = cost
            case["rep"] = rep
            path = _sim_path(runs_dir, variant, case_id, rep)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(case, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            async with spend_lock:
                spend["total"] += cost

    await asyncio.gather(*(_worker(c, r) for c, r in pending))
    if stop["hit"]:
        raise SystemExit(
            f"spend cap ${max_usd:.2f} reached at ${spend['total']:.2f}; re-run the same "
            "command to continue (resume skips finished pairs)"
        )


def _missing_named_systems(case: dict[str, Any]) -> list[str]:
    """spec §3.2: ground truth is reconciled against the simulated transcript at review,
    not auto-edited. Returns every `named_systems` entry not found (case-insensitive
    substring) in the person's own (`user`) turns, for a human to remove if it really
    was never said."""
    named = case.get("ground_truth", {}).get("named_systems", [])
    own_text = " ".join(
        t["content"].lower() for t in case.get("transcript", []) if t.get("role") == "user"
    )
    return [system for system in named if system.lower() not in own_text]


def _own_turns(case: dict[str, Any]) -> list[str]:
    return [t["content"] for t in case.get("transcript", []) if t.get("role") == "user"]


def _known_system_texts(case: dict[str, Any]) -> list[str]:
    named = case.get("ground_truth", {}).get("named_systems", [])
    tool_codes = case.get("assessment", {}).get("b_tools") or []
    tool_labels = [TOOLS.get(code, code) for code in tool_codes]
    return [*named, *tool_labels]


def _is_whole_word_substring(needle: str, haystack: str) -> bool:
    return bool(needle) and re.search(r"\b" + re.escape(needle) + r"\b", haystack) is not None


def _already_known_system(word: str, known: list[str]) -> bool:
    """Case-insensitive *whole-word* substring either way (spec review, 2026-09-27):
    "Excel" is already known via "Microsoft Excel" and vice versa. Whole-word, not a
    bare `in` check - a bare substring check would wrongly swallow "WhatsApp" as
    "already known" whenever "SAP" is in named_systems, since "sap" is a literal
    (non-word-boundary) substring of "whatsapp"."""
    lowered = word.lower()
    return any(
        _is_whole_word_substring(lowered, k.lower()) or _is_whole_word_substring(k.lower(), lowered)
        for k in known
        if k
    )


_SENTENCE_SPLIT_RE = re.compile(r"[.!?\n]+")
_PUNCTUATION_STRIP = ".,!?;:\"'()[]{}“”‘’"


def _split_sentences(text: str) -> list[str]:
    return [s for s in _SENTENCE_SPLIT_RE.split(text) if s.strip()]


def _is_camel_case(word: str) -> bool:
    """WorkOrder, SuccessFactors, MasterControl, ServicePro: a capital, a lowercase run,
    then another capital."""
    return bool(re.match(r"^[A-Z][a-z]+[A-Z][A-Za-z]*$", word))


def _has_capital_and_digit_or_slash(word: str) -> bool:
    """P6, S/4HANA: starts with a capital and has at least one digit or slash in it."""
    return bool(word) and word[0].isupper() and any(c.isdigit() or c == "/" for c in word[1:])


def _is_allcaps_run(word: str) -> bool:
    return len(word) >= 2 and word.isalpha() and word.isupper()


def _is_capitalised_mid_sentence(word: str, position: int) -> bool:
    return position > 0 and word.isalpha() and word[0].isupper() and word[1:].islower()


def _looks_like_a_product(word: str, position: int) -> bool:
    return (
        _is_camel_case(word)
        or _has_capital_and_digit_or_slash(word)
        or _is_allcaps_run(word)
        or _is_capitalised_mid_sentence(word, position)
    )


def _possible_systems(case: dict[str, Any]) -> list[str]:
    """Heuristic hint for a human, not a hard rule (spec 2026-09-27 review): scans the
    person's own words for product-like tokens not already covered by named_systems or
    the assessment tool labels. Noisy is acceptable - it only needs to save a reviewer
    from re-reading the whole transcript by hand."""
    known = _known_system_texts(case)
    found: list[str] = []
    seen: set[str] = set()
    for turn in _own_turns(case):
        for sentence in _split_sentences(turn):
            words = sentence.split()
            for position, raw in enumerate(words):
                word = raw.strip(_PUNCTUATION_STRIP)
                if not word or not _looks_like_a_product(word, position):
                    continue
                lowered = word.lower()
                if lowered in vocabulary.POSSIBLE_SYSTEM_STOPWORDS:
                    continue
                if _already_known_system(word, known):
                    continue
                if lowered not in seen:
                    seen.add(lowered)
                    found.append(word)
    return found


def _workstreams_missing_all_keywords(case: dict[str, Any]) -> list[str]:
    """A workstream whose keywords do not appear anywhere in the person's own words
    almost certainly has keywords that need fixing (or the workstream needs dropping) -
    see `_own_turns`/spec 2026-09-27 review."""
    own_text = " ".join(t.lower() for t in _own_turns(case))
    return [
        ws["name"]
        for ws in case.get("ground_truth", {}).get("workstreams", [])
        if not any(kw.lower() in own_text for kw in ws.get("keywords", []))
    ]


def _will_build_line(case: dict[str, Any]) -> str:
    """spec review F1(b): mirrors InterviewService's own `_ensure_ready` rule exactly (the
    same threshold, imported rather than repeated) so this line never drifts from what
    `run` will actually accept."""
    transcript = case.get("transcript", [])
    offered = any(
        t.get("role") == "assistant" and has_ready_marker(t.get("content", "")) for t in transcript
    )
    answers = sum(1 for t in transcript if t.get("role") == "user")
    if offered:
        return "yes (offer present)"
    if answers >= _MIN_ANSWERS_WITHOUT_OFFER:
        return f"yes ({answers} answers)"
    return f"NO ({answers} answers, no offer)"


def _canary_present_line(case: dict[str, Any]) -> str | None:
    """F5: `where: transcript` means the canary should show up in one of the person's own
    turns; `where: assessment` means it should show up in their assessment free text
    (mirrors checks._own_text_sources' choice of fields)."""
    adversarial = case.get("adversarial")
    if not adversarial:
        return None
    canary = adversarial["canary"]
    if adversarial["where"] == "transcript":
        present = any(
            t.get("role") == "user" and canary in t.get("content", "")
            for t in case.get("transcript", [])
        )
    else:
        assessment = case.get("assessment", {})
        free_text = f"{assessment.get('q_timesink') or ''} {assessment.get('q_excitement') or ''}"
        present = canary in free_text
    return f"Canary present where planted: {'yes' if present else 'NO'}"


def write_review_page(case: dict[str, Any]) -> None:
    REVIEW_DIR.mkdir(parents=True, exist_ok=True)
    missing = _missing_named_systems(case)
    possible = _possible_systems(case)
    unmatched_workstreams = _workstreams_missing_all_keywords(case)
    placeholder_count = sum(
        1
        for t in case["transcript"]
        if t.get("role") == "user" and t["content"] == _EMPTY_ANSWER_PLACEHOLDER
    )
    lines = [
        f"# Review: {case['id']}",
        "",
        f"Tags: {', '.join(case.get('tags', []))}",
        "",
        "## Assessment",
        "```json",
        _json(case["assessment"]),
        "```",
        "",
        "## Persona (simulator brief, not shown to the interviewer)",
        case["persona"],
        "",
        "## Transcript",
    ]
    for turn in case["transcript"]:
        lines += [f"**{turn['role']}:** {turn['content']}", ""]
    lines += [
        "## Ground truth (reconciled against the transcript)",
        "```json",
        _json(case["ground_truth"]),
        "```",
        "",
        "Named systems not found in the person's answers (remove at review if really "
        f"unsaid): {', '.join(missing) if missing else 'none'}",
        "",
        "Possible systems the person named that are not in named_systems (add at review "
        f"if they are systems): {', '.join(possible) if possible else 'none'}",
        "",
        "Workstreams whose keywords never appear in the person's answers (fix keywords "
        "or remove at review): "
        f"{', '.join(unmatched_workstreams) if unmatched_workstreams else 'none'}",
        "",
        f"Empty learner replies replaced with the placeholder: {placeholder_count or 'none'}",
        "",
        f"Will build at run time: {_will_build_line(case)}",
    ]
    checklist = [
        "- [ ] No real names, companies or identifying details anywhere above.",
        "- [ ] Every `named_systems` entry was actually said in the transcript.",
        "- [ ] Every system the person named in the transcript is listed in named_systems "
        "(add any missing).",
        "- [ ] Every 'possible system' above that really is a system has been added to "
        "named_systems (or dismissed as not a system).",
        "- [ ] Every workstream with no keyword hits above has been fixed or removed.",
        "- [ ] The transcript reads like this persona, not a generic interview.",
        "- [ ] The stop point matches the persona's stated stop rule.",
        "- [ ] The 'Will build at run time' line says yes.",
    ]
    canary_line = _canary_present_line(case)
    if canary_line is not None:
        lines += ["", canary_line]
        checklist.append("- [ ] The 'Canary present where planted' line says yes.")
    lines += ["", "## Checklist before approving", *checklist]
    (REVIEW_DIR / f"{case['id']}.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _json(value: object) -> str:
    return json.dumps(value, indent=2, ensure_ascii=False)


def approve_case(case_id: str) -> dict[str, Any]:
    case = load_case(case_id)
    if case["status"] != "draft":
        raise ValueError(f"case {case_id!r} is not a draft (status={case['status']!r})")
    case["status"] = "approved"
    case["approval"]["approved_at"] = datetime.now(UTC).isoformat()
    write_case(case)
    return case
