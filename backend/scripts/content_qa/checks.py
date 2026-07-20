"""Deterministic content checks over a lessons.content_blocks list.

Pure functions: input is a content_blocks list, output is a list of finding
dicts. No I/O, no DB. The Americanism map is a curated allowlist (exact forms)
rather than a broad -ize regex, so it never fires on correct British spellings
or on words like 'size'/'prize' that merely end in -ize.
"""
from __future__ import annotations

import re

from content_qa.blocks import iter_texts

BANNED_PUNCTUATION = {"—": "em-dash", "–": "en-dash", "…": "ellipsis"}

# American -> British. Whole-word, case-insensitive. Includes common inflections.
AMERICANISMS: dict[str, str] = {
    "organize": "organise", "organizes": "organises", "organized": "organised",
    "organizing": "organising", "organization": "organisation",
    "organizations": "organisations",
    "recognize": "recognise", "recognized": "recognised", "recognizing": "recognising",
    "customize": "customise", "customized": "customised", "customizing": "customising",
    "customization": "customisation",
    "personalize": "personalise", "personalized": "personalised",
    "personalizing": "personalising", "personalization": "personalisation",
    "prioritize": "prioritise", "prioritized": "prioritised", "prioritizing": "prioritising",
    "summarize": "summarise", "summarized": "summarised", "summarizing": "summarising",
    "analyze": "analyse", "analyzed": "analysed", "analyzing": "analysing",
    "optimize": "optimise", "optimized": "optimised", "optimizing": "optimising",
    "minimize": "minimise", "maximize": "maximise",
    "realize": "realise", "realized": "realised", "realizing": "realising",
    "emphasize": "emphasise", "apologize": "apologise", "categorize": "categorise",
    "specialize": "specialise", "standardize": "standardise", "utilize": "utilise",
    "capitalize": "capitalise", "initialize": "initialise", "visualize": "visualise",
    "synchronize": "synchronise", "familiarize": "familiarise",
    "color": "colour", "colors": "colours", "colored": "coloured", "coloring": "colouring",
    "behavior": "behaviour", "behaviors": "behaviours",
    "favorite": "favourite", "favorites": "favourites", "favor": "favour",
    "honor": "honour", "labor": "labour", "neighbor": "neighbour",
    "center": "centre", "centered": "centred",
    "catalog": "catalogue", "dialog": "dialogue",
    "artifact": "artefact", "artifacts": "artefacts",
    "defense": "defence", "offense": "offence",
    "gray": "grey", "modeling": "modelling", "traveler": "traveller",
    "canceled": "cancelled", "canceling": "cancelling",
    "fulfill": "fulfil", "enrollment": "enrolment",
    "license": "licence",  # noun; verb form 'license' is BrE too - flag for human check
}

# One case-insensitive pattern with word boundaries over all keys.
_AMERICANISM_RE = re.compile(
    r"\b(" + "|".join(re.escape(k) for k in AMERICANISMS) + r")\b", re.IGNORECASE
)


def _snippet(text: str, start: int, end: int, radius: int = 40) -> str:
    lo = max(0, start - radius)
    hi = min(len(text), end + radius)
    pre = "..." if lo > 0 else ""
    post = "..." if hi < len(text) else ""
    return f"{pre}{text[lo:hi].strip()}{post}"


def find_banned_punctuation(blocks: list[dict]) -> list[dict]:
    findings: list[dict] = []
    for path, text in iter_texts(blocks):
        for ch, name in BANNED_PUNCTUATION.items():
            idx = text.find(ch)
            while idx != -1:
                findings.append(
                    {"kind": "punctuation", "char": name, "path": path,
                     "snippet": _snippet(text, idx, idx + 1)}
                )
                idx = text.find(ch, idx + 1)
    return findings


def find_americanisms(blocks: list[dict]) -> list[dict]:
    findings: list[dict] = []
    for path, text in iter_texts(blocks):
        for m in _AMERICANISM_RE.finditer(text):
            term = m.group(1)
            findings.append(
                {"kind": "americanism", "term": term,
                 "suggestion": AMERICANISMS[term.lower()], "path": path,
                 "snippet": _snippet(text, m.start(), m.end())}
            )
    return findings


CHECK_UNDERSTANDING = "check your understanding"


def check_quiz_conformance(blocks: list[dict]) -> list[dict]:
    """Enforce the house convention around quizzes and whitespace separators.

    For each quiz: walking backward past whitespace blocks, the first
    non-whitespace block must be a heading 'Check your understanding'
    (quiz-heading), and at least one of the skipped whitespace blocks must be
    size 'md' (quiz-separator). Any whitespace of a non-'md' size is flagged
    (whitespace-size). Any whitespace not adjacent to a quiz is flagged
    (whitespace-orphan).
    """
    blocks = blocks or []
    findings: list[dict] = []
    quiz_indices = {i for i, b in enumerate(blocks) if b.get("type") == "quiz"}

    # whitespace-size + whitespace-orphan
    for i, b in enumerate(blocks):
        if b.get("type") != "whitespace":
            continue
        if b.get("size") != "md":
            findings.append({"kind": "whitespace-size", "block_index": i,
                             "detail": f"whitespace size is {b.get('size')!r}, expected 'md'"})
        # orphan = the nearest non-whitespace block AFTER it is not a quiz
        j = i + 1
        while j < len(blocks) and blocks[j].get("type") == "whitespace":
            j += 1
        if not (j < len(blocks) and blocks[j].get("type") == "quiz"):
            findings.append({"kind": "whitespace-orphan", "block_index": i,
                             "detail": "whitespace block is not immediately before a quiz"})

    # quiz-heading + quiz-separator
    for qi in sorted(quiz_indices):
        saw_md_ws = False
        k = qi - 1
        while k >= 0 and blocks[k].get("type") == "whitespace":
            if blocks[k].get("size") == "md":
                saw_md_ws = True
            k -= 1
        prev = blocks[k] if k >= 0 else None
        is_heading = (
            prev is not None
            and prev.get("type") == "heading"
            and (prev.get("text") or "").strip().lower() == CHECK_UNDERSTANDING
        )
        if not is_heading:
            findings.append({"kind": "quiz-heading", "block_index": qi,
                             "detail": "no 'Check your understanding' heading immediately before the quiz"})
        if not saw_md_ws:
            findings.append({"kind": "quiz-separator", "block_index": qi,
                             "detail": "no whitespace(md) separator immediately before the quiz"})
    return findings


def quiz_stats(blocks: list[dict]) -> dict:
    blocks = blocks or []
    questions: list[dict] = []
    quiz_index = 0
    num_quizzes = 0
    for b in blocks:
        if b.get("type") == "quiz":
            num_quizzes += 1
            for q in b.get("questions", []):
                questions.append({
                    "num_options": len(q.get("options", [])),
                    "correct_index": q.get("correct"),
                    "quiz_index": quiz_index,
                })
            quiz_index += 1
    num_whitespace = sum(1 for b in blocks if b.get("type") == "whitespace")
    return {"num_quizzes": num_quizzes, "questions": questions,
            "num_whitespace": num_whitespace}
