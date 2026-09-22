"""The committed Claude Code hooks (.claude/hooks/*.py) must nudge, never block:
exit 0 on every path and print at most one JSON object with a systemMessage."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
HOOKS = REPO_ROOT / ".claude" / "hooks"
NUDGE = HOOKS / "prod_asset_nudge.py"
FRESHNESS = HOOKS / "git_freshness.py"

pytestmark = pytest.mark.unit


def _run(script: Path, stdin: str, env_extra: dict[str, str] | None = None) -> tuple[int, str]:
    env = {**os.environ, **(env_extra or {})}
    proc = subprocess.run(
        [sys.executable, str(script)],
        input=stdin,
        capture_output=True,
        text=True,
        env=env,
        cwd=REPO_ROOT,
        timeout=60,
        check=False,
    )
    return proc.returncode, proc.stdout


@pytest.mark.parametrize(
    ("path", "fragment"),
    [
        ("C:/x/AI enablement hub/frontend/src/pages/LessonPage.tsx", "production-shaped fixtures"),
        ("/repo/backend/prompts/house_style.md", "production asset"),
        ("/repo/backend/alembic/versions/abc123_add_table.py", "container start"),
    ],
)
def test_nudge_flags_production_assets(path: str, fragment: str) -> None:
    code, out = _run(NUDGE, json.dumps({"tool_input": {"file_path": path}}))
    assert code == 0
    payload = json.loads(out)
    assert fragment in payload["systemMessage"]
    assert Path(path).name in payload["systemMessage"]


@pytest.mark.parametrize(
    "path",
    ["/repo/backend/src/services/x.py", "/repo/docs/README.md", "/repo/frontend/package.json", ""],
)
def test_nudge_is_silent_elsewhere(path: str) -> None:
    code, out = _run(NUDGE, json.dumps({"tool_input": {"file_path": path}}))
    assert code == 0
    assert out.strip() == ""


def test_nudge_survives_garbage_stdin() -> None:
    code, out = _run(NUDGE, "not json")
    assert code == 0
    assert out.strip() == ""


def test_freshness_is_silent_under_github_actions() -> None:
    code, out = _run(FRESHNESS, "{}", {"GITHUB_ACTIONS": "true"})
    assert code == 0
    assert out.strip() == ""


def test_freshness_reports_without_network() -> None:
    # GIT_FRESHNESS_SKIP_FETCH lets the test avoid the network while exercising the report path.
    code, out = _run(FRESHNESS, "{}", {"GIT_FRESHNESS_SKIP_FETCH": "1", "GITHUB_ACTIONS": ""})
    assert code == 0
    payload = json.loads(out)
    assert payload["systemMessage"].startswith("[git] ")
