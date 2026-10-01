"""Is a piece of text Dutch or English? A deterministic function-word count, no model
call (spec 2026-09-30, Dutch level 1). Good enough to grade the interviewer's and the
playbook's language; not a general language detector. Words both languages share
("in", "is", "over") are left out of both lists."""

from __future__ import annotations

import re
from typing import Literal

__all__ = ["detect_language", "dutch_word_count"]

Language = Literal["nl", "en", "unknown"]

_DUTCH = frozenset(
    [
        "de",
        "het",
        "een",
        "en",
        "van",
        "ik",
        "u",
        "uw",
        "je",
        "jij",
        "jouw",
        "niet",
        "dat",
        "wat",
        "voor",
        "op",
        "te",
        "zijn",
        "er",
        "ook",
        "maar",
        "dan",
        "bij",
        "om",
        "naar",
        "hoe",
        "welk",
        "welke",
        "wordt",
        "heb",
        "heeft",
        "hebben",
        "dit",
        "deze",
        "nog",
        "wel",
        "kan",
        "kunt",
        "moet",
        "zou",
        "dank",
        "uit",
        "elke",
        "elk",
        "wie",
        "waar",
        "waarom",
        "wanneer",
        "veel",
        "eigenlijk",
        "gewoon",
        "meestal",
        "soms",
        "echt",
        "zo",
        "nu",
        "al",
        "hetzelfde",
        "dezelfde",
        "opnieuw",
        "vanuit",
        "altijd",
        "nooit",
        "geen",
        "meer",
        "minder",
        "alle",
        "alles",
        "zelf",
        "omdat",
        "zodat",
        "tussen",
        "worden",
        "kunnen",
        "moeten",
        "maken",
        "doen",
        "dus",
        "want",
        "toen",
        "daar",
        "hier",
        "hebt",
    ]
)
_ENGLISH = frozenset(
    [
        "the",
        "a",
        "an",
        "and",
        "of",
        "to",
        "i",
        "you",
        "your",
        "not",
        "that",
        "this",
        "what",
        "which",
        "for",
        "with",
        "on",
        "it",
        "are",
        "do",
        "does",
        "did",
        "how",
        "have",
        "has",
        "be",
        "can",
        "could",
        "would",
        "they",
        "my",
        "so",
        "but",
        "or",
        "if",
        "about",
        "from",
        "then",
        "every",
        "when",
        "where",
        "who",
        "why",
        "there",
        "their",
        "just",
        "really",
        "into",
        "before",
        "after",
        "all",
        "same",
        "again",
        "without",
        "always",
        "never",
        "more",
        "less",
        "because",
        "between",
        "other",
    ]
)
_WORD_RE = re.compile(r"[a-zà-ÿ']+")
# Fewer function words than this and the text is too short to call.
_MIN_HITS = 3


def detect_language(text: str) -> Language:
    words = _WORD_RE.findall(text.lower())
    dutch = sum(1 for w in words if w in _DUTCH)
    english = sum(1 for w in words if w in _ENGLISH)
    if dutch + english < _MIN_HITS or dutch == english:
        return "unknown"
    return "nl" if dutch > english else "en"


def dutch_word_count(text: str) -> int:
    """How many Dutch function words the text has: 0 means a whole message in English
    (the prompt's condition for switching back from Dutch)."""
    return sum(1 for w in _WORD_RE.findall(text.lower()) if w in _DUTCH)
