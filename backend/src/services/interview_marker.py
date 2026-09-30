from __future__ import annotations

import re

__all__ = ["READY_MARKER", "has_ready_marker", "strip_ready_marker"]

# The interviewer puts this marker on the first line of the turn where it offers to build
# the playbook (prompts/interview.md; first, so the hard stop at its question never has
# to rescue it, #96); the frontend detects it wherever it appears to reveal the Build button
# (frontend/src/lib/interviewReady.ts READY_MARKER, keep the two in sync). It is a UI
# signal, not conversation: strip it from everything the model or an admin reads.
READY_MARKER = "[[READY_TO_BUILD]]"
# The marker plus any spaces right after it, so an inline "[[...]] With that" leaves no gap.
_MARKER_RE = re.compile(re.escape(READY_MARKER) + r"[ \t]*")


def has_ready_marker(text: str) -> bool:
    return READY_MARKER in text


def strip_ready_marker(text: str) -> str:
    return _MARKER_RE.sub("", text).strip() if READY_MARKER in text else text
