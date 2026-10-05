"""Playbook rules enforced in code, not only asked of the model (#149).

The prompt says never to invent a system. The model still sometimes lists a system the person
never mentioned ("Spreadsheet / Excel" for someone who only uses Outlook), and the learner's
playbook screen shows each use case's systems. So every system in the shared box must appear in
the person's own words: their interview answers or their assessment record. Anything else is
dropped before the playbook is saved.

Matching follows the eval's no_invented_systems check: case-insensitive whole words, a bracketed
note ignored ("Excel (source notes)"), a leading vendor word optional ("Microsoft Excel" for
"Excel"), a trailing plural tolerated only on longer names ("SAP" never matches "saps")."""

from __future__ import annotations

import copy
import re
from typing import Any

__all__ = ["drop_unnamed_systems"]

_VENDOR_WORDS = ("microsoft 365", "microsoft", "ms", "sap", "google", "oracle")
# A single word gets plural tolerance only when its singular has at least this many letters.
_MIN_PLURAL_LENGTH = 7


def drop_unnamed_systems(
    extraction: dict[str, Any], sources: list[str]
) -> tuple[dict[str, Any], int]:
    """A copy of `extraction` whose use cases list only systems found in `sources`, and how
    many systems were dropped. The internal box is left as it is: it is consultant-only and
    may name systems as inferences, marked as such."""
    result = copy.deepcopy(extraction)
    haystack = _normalise(" ".join(sources))
    dropped = 0
    for use_case in result["shared"]["use_cases"]:
        kept = [s for s in use_case["systems_involved"] if _named(s, haystack)]
        dropped += len(use_case["systems_involved"]) - len(kept)
        use_case["systems_involved"] = kept
    return result, dropped


def _named(system: str, haystack: str) -> bool:
    core = re.sub(r"\s*\([^)]*\)", "", system).strip() or system
    # "A / B" is two systems in one entry: keep it only if both were named. A slash without
    # spaces is part of a name ("SAP S/4HANA").
    parts = [p for p in re.split(r"\s+/\s+", core) if p.strip()]
    return all(_part_named(_normalise(part), haystack) for part in parts)


def _part_named(name: str, haystack: str) -> bool:
    return any(_said(candidate, haystack) for candidate in {name, _strip_vendor(name)})


def _said(phrase: str, haystack: str) -> bool:
    words = phrase.split()
    if not words:
        return False
    head = [re.escape(w) for w in words[:-1]]
    last = words[-1]
    singular = last[:-1] if last.endswith("s") and len(last) > 1 else last
    if len(words) > 1 or len(singular) >= _MIN_PLURAL_LENGTH:
        head.append(re.escape(singular) + "s?")
    else:
        head.append(re.escape(last))
    # Look-arounds, not \b: a name may start or end with a symbol ("C#", ".NET").
    return re.search(r"(?<!\w)" + r"\s+".join(head) + r"(?!\w)", haystack) is not None


def _strip_vendor(name: str) -> str:
    for vendor in _VENDOR_WORDS:
        prefix = f"{vendor} "
        if name.startswith(prefix) and name[len(prefix) :].strip():
            return name[len(prefix) :].strip()
    return name


def _normalise(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())
