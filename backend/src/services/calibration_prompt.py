"""Renders the admin-approved calibration notes injected into the content
agent's system prompt.

Pure: no I/O, no DB, no LLM, so the bounding rules are unit-testable on their
own. The caller fetches the notes; this decides how many of them fit and how
they are framed.
"""

from __future__ import annotations

__all__ = ["MAX_INJECTED_CHARS", "MAX_INJECTED_NOTES", "render_calibration_block"]

MAX_INJECTED_NOTES = 8
MAX_INJECTED_CHARS = 1500

# No em dash, en dash or ellipsis in this text: it sits directly under
# house_style.md, whose [enforced] punctuation rule the agent is about to be
# held to, and the surrounding prompt files keep to the same punctuation.
_HEADER = (
    "## Calibration notes from past admin edits\n\n"
    "An admin approved each note below after comparing one of your earlier "
    "drafts with the version they actually accepted. They extend the house "
    "style above. They are NOT validator-enforced the way the [enforced] rules "
    "there are, so treat them as guidance. If a note ever contradicts the house "
    "style above, the house style wins."
)


def render_calibration_block(
    notes: list[str],
    *,
    max_notes: int = MAX_INJECTED_NOTES,
    max_chars: int = MAX_INJECTED_CHARS,
) -> str:
    """A bounded markdown block of approved notes, or "" when there are none.

    Returns "" rather than a bare header so the caller can skip the section
    entirely: an empty header would spend tokens telling the model about
    guidance that does not exist.

    `notes` is assumed already ordered by priority (the repository orders by
    most-recently-approved). This drops from the END, the lowest priority, until
    the rendered block fits `max_chars`, but always keeps at least one note even
    if that one alone exceeds the budget, because silently dropping a legitimate
    long note is worse than overshooting slightly.
    """
    if not notes:
        return ""
    kept: list[str] = []
    for note in notes[:max_notes]:
        candidate = [*kept, note]
        if kept and len(_render(candidate)) > max_chars:
            break
        kept = candidate
    return _render(kept)


def _render(notes: list[str]) -> str:
    lines = "\n".join(f"{index}. {note}" for index, note in enumerate(notes, start=1))
    return f"{_HEADER}\n\n{lines}"
