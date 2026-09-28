"""One-off simulation: the real interviewer loop (InterviewService.open_interview +
ChatService.send_message) against a second model call playing the persona (spec §3.3).
Needs a real LlmClient; only the `simulate` CLI command constructs one."""

from __future__ import annotations

import json
import re
import uuid
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import TYPE_CHECKING, Any

from evals.interviewer import vocabulary
from evals.interviewer.cases import load_case, write_case
from evals.interviewer.fakes import (
    TOOLS,
    InMemoryConversationRepository,
    InMemoryMessageRepository,
    build_context,
)
from src.services.chat_service import ChatService, DoneEvent
from src.services.interview_marker import has_ready_marker
from src.services.interview_service import _MIN_ANSWERS_WITHOUT_OFFER, InterviewService
from src.services.prompts import prompt_version

if TYPE_CHECKING:
    from src.services.llm_service import LlmClient

__all__ = [
    "REVIEW_DIR",
    "approve_case",
    "ensure_resimulation_allowed",
    "simulate_case",
    "write_review_page",
]

REVIEW_DIR = Path(__file__).resolve().parent / "review"
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


async def simulate_case(
    case_id: str, *, interviewer_llm: LlmClient, learner_llm: LlmClient
) -> dict[str, Any]:
    case = load_case(case_id)
    conversations = InMemoryConversationRepository()
    messages = InMemoryMessageRepository()
    context = build_context(case)
    interview_service = InterviewService(conversations, messages, interviewer_llm, context)
    chat_service = ChatService(conversations, messages, interviewer_llm)
    user = SimpleNamespace(
        id=uuid.uuid4(), first_name=case["user"]["first_name"], last_name=case["user"]["last_name"]
    )

    opener = await interview_service.open_interview(user=user)  # ty: ignore[invalid-argument-type]
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
            if not isinstance(event, DoneEvent):
                turn_text += event.text
        ready = has_ready_marker(turn_text)
        question = turn_text

    rows = await messages.list_for_conversation(conversation.id)
    case["status"] = "draft"
    case["transcript"] = [{"role": r.role, "content": r.content} for r in rows]
    case["simulation"] = {
        "model": interviewer_llm.model,
        "interview_prompt_version": prompt_version(_INTERVIEW_KIND),
        "simulated_at": datetime.now(UTC).isoformat(),
    }
    # M2: any prior approval no longer means anything once the transcript has changed.
    case["approval"] = {"approved_at": None, "notes": ""}
    write_case(case)
    write_review_page(case)
    return case


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
