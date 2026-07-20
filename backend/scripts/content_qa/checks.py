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
