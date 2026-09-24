#!/usr/bin/env python3
"""PostToolUse hook: flag edits to production assets whose effect CI cannot see.

Ported from sb-accelerator's ui-change-reminder.py. Reads the Claude Code hook JSON on stdin,
looks at tool_input.file_path, and if it is one of the paths below prints one JSON object with a
systemMessage. It nudges, never blocks: exit 0 on every path, including bad input.
"""

from __future__ import annotations

import json
import sys

RULES: tuple[tuple[str, str], ...] = (
    (
        "frontend/src/",
        "is learner-facing UI. CI type-checks and builds it but cannot see it render: verify "
        "with production-shaped fixtures and a stubbed fetch, assert on getComputedStyle, and "
        "exercise the load window (CLAUDE.md -> 'Verifying without touching live data') before "
        "calling this done.",
    ),
    (
        "backend/prompts/",
        "is a production asset baked into the Docker image, and git is its only source of "
        "truth: it ships with the next deploy. Regenerate the golden snapshots "
        "(UPDATE_GOLDEN=1 uv run pytest tests/golden/ai from backend/) and read their diff "
        "before calling this done.",
    ),
    (
        "backend/alembic/versions/",
        "is a migration: the Deploy workflow runs it unattended in the ai-enablement-hub-migrate "
        "job against the live database before the app rolls, and a rollback keeps the new "
        "schema. It must be additive / expand-first, fast on the live tables, and safe to run "
        "twice.",
    ),
)


def message_for(path: str) -> str | None:
    """Return the nudge for `path`, or None when the file is not a flagged production asset."""
    if not path:
        return None
    rel = path.replace("\\", "/")
    for needle, text in RULES:
        if needle in rel:
            name = rel.rsplit("/", 1)[-1]
            return f"[prod-asset] {name} {text}"
    return None


def main() -> int:
    try:
        payload = json.load(sys.stdin)
        path = (payload.get("tool_input") or {}).get("file_path") or ""
        msg = message_for(str(path))
        if msg:
            print(json.dumps({"systemMessage": msg}))
    except Exception:  # noqa: BLE001 - a hook must never fail the tool call
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
