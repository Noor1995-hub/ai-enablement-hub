#!/usr/bin/env python3
"""SessionStart hook: tell the session how stale its checkout is.

Fetches origin and reports "main is N commit(s) behind origin/main" and, on a feature branch,
how far behind its upstream it is. Skips entirely under GitHub Actions. Nudges, never blocks:
exit 0 on every path. Set GIT_FRESHNESS_SKIP_FETCH=1 to skip the network call (tests). The
staleness message is emitted both as `systemMessage` (for the human) and as
`hookSpecificOutput.additionalContext` (so the model sees it too).
"""

from __future__ import annotations

import json
import os
import subprocess
import sys


def _git(*args: str, timeout: int = 20) -> tuple[int, str]:
    env = {**os.environ, "GIT_TERMINAL_PROMPT": "0"}
    try:
        proc = subprocess.run(
            ["git", *args], capture_output=True, text=True, env=env, timeout=timeout, check=False
        )
    except (OSError, subprocess.TimeoutExpired):
        return 1, ""
    return proc.returncode, proc.stdout.strip()


def _count(range_spec: str) -> int:
    code, out = _git("rev-list", "--count", range_spec)
    return int(out) if code == 0 and out.isdigit() else 0


def build_message() -> str | None:
    code, _ = _git("rev-parse", "--is-inside-work-tree")
    if code != 0:
        return None
    if os.environ.get("GIT_FRESHNESS_SKIP_FETCH") != "1":
        code, _ = _git("fetch", "--quiet", timeout=25)
        if code != 0:
            return "[git] fetch failed (offline or no credentials) - repo freshness not checked."
    parts: list[str] = []
    has_remote_main = _git("rev-parse", "--verify", "--quiet", "refs/remotes/origin/main")[0] == 0
    has_local_main = _git("rev-parse", "--verify", "--quiet", "refs/heads/main")[0] == 0
    if has_remote_main and has_local_main:
        behind = _count("main..origin/main")
        if behind:
            parts.append(
                f"main is {behind} commit(s) behind origin/main - run: git checkout main && git pull."
            )
        else:
            parts.append("main is up to date.")
    else:
        parts.append("no local main branch - freshness check skipped.")
    _, branch = _git("rev-parse", "--abbrev-ref", "HEAD")
    if branch not in ("", "main", "HEAD"):
        code, upstream = _git("rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}")
        if code == 0 and upstream:
            behind = _count(f"HEAD..{upstream}")
            if behind:
                parts.append(f"Your branch '{branch}' is {behind} behind {upstream}.")
    return "[git] " + " ".join(parts) if parts else None


def main() -> int:
    try:
        sys.stdin.read()  # consume the hook payload; nothing in it is needed
        if os.environ.get("GITHUB_ACTIONS"):
            return 0
        msg = build_message()
        if msg:
            print(
                json.dumps(
                    {
                        "systemMessage": msg,
                        "hookSpecificOutput": {
                            "hookEventName": "SessionStart",
                            "additionalContext": msg,
                        },
                    }
                )
            )
    except Exception:  # noqa: BLE001 - a hook must never block a session
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
