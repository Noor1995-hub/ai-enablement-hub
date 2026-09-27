from __future__ import annotations

__all__ = ["READY_MARKER", "has_ready_marker", "strip_ready_marker"]

# The interviewer appends this marker to the turn where it offers to build the playbook
# (prompts/interview.md); the frontend detects it to reveal the Build button
# (frontend/src/pages/Interview.tsx READY_MARKER, keep the two in sync). It is a UI
# signal, not conversation: strip it from everything the model or an admin reads.
READY_MARKER = "[[READY_TO_BUILD]]"


def has_ready_marker(text: str) -> bool:
    return READY_MARKER in text


def strip_ready_marker(text: str) -> str:
    return text.replace(READY_MARKER, "").rstrip() if READY_MARKER in text else text
