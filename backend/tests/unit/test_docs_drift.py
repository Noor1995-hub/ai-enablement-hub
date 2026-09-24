"""Docs-drift guard (way-of-working 2.5): the maintained docs must not point at things that are
gone, the CI job names must match what the `main-ci` ruleset requires, and the API-types
regeneration must never need a running backend."""

from __future__ import annotations

import json
import posixpath
import re
import subprocess
from functools import cache
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]

# The "Read to contribute (current, maintained)" table of docs/README.md, plus that map itself.
# python-be-architecture.md is deliberately absent: it is the generic delaware template, and its
# example paths describe the template, not this repo.
MAINTAINED_DOCS = [
    "README.md",
    "CONTRIBUTING.md",
    "CLAUDE.md",
    "backend/CLAUDE.md",
    "frontend/CLAUDE.md",
    "docs/feature-index.md",
    "SECURITY.md",
    "db/README.md",
    "docs/README.md",
    "docs/superpowers/lessons.md",
    "docs/db-backup-restore.md",
    *sorted(p.relative_to(REPO_ROOT).as_posix() for p in (REPO_ROOT / "docs/content").glob("*.md")),
]
REPO_ROOTED = ("backend/", "frontend/", "docs/", "infra/", "db/", ".github/", ".claude/")
# Paths the docs name on purpose although they are neither tracked nor git-ignored.
NOT_IN_GIT = {"frontend/public/__verify/"}  # a temporary folder the verification recipe creates

_BACKTICKED = re.compile(r"`([^`\s]+)`")


def _repo_paths(text: str) -> list[str]:
    paths = []
    for raw in _BACKTICKED.findall(text):
        path = re.sub(r":\d+(-\d+)?$", "", raw.rstrip(".,;:)").split("::")[0])
        if path.startswith(REPO_ROOTED) and not any(c in path for c in "*<>{}$"):
            paths.append(path)
    return paths


@cache
def _tracked() -> frozenset[str]:
    """Every tracked file and every directory above one. Checking git, not the disk, gives the
    same answer on a laptop (full of git-ignored files) and on a fresh CI checkout."""
    out = subprocess.run(
        ["git", "ls-files"], cwd=REPO_ROOT, capture_output=True, text=True, check=True
    ).stdout
    paths: set[str] = set()
    for line in out.splitlines():
        parts = line.split("/")
        paths.update("/".join(parts[:i]) for i in range(1, len(parts) + 1))
    return frozenset(paths)


def _git_ignored(path: str) -> bool:
    """`backend/.env`, `frontend/node_modules`, ...: named on purpose, never in git."""
    probe = subprocess.run(
        ["git", "check-ignore", "-q", "--no-index", path.rstrip("/")], cwd=REPO_ROOT, check=False
    )
    return probe.returncode == 0


def _exists(path: str) -> bool:
    # CLAUDE.md's repo map names app packages relative to backend/src (`db/models/`, ...).
    path = path.rstrip("/")
    return path in _tracked() or f"backend/src/{path}" in _tracked()


@pytest.mark.parametrize("doc", MAINTAINED_DOCS)
def test_repo_paths_in_maintained_docs_exist(doc: str) -> None:
    text = (REPO_ROOT / doc).read_text(encoding="utf-8")
    missing = [
        p
        for p in _repo_paths(text)
        if p not in NOT_IN_GIT and not _exists(p) and not _git_ignored(p)
    ]
    assert not missing, f"{doc} names paths that do not exist: {missing}"


def test_every_path_in_the_docs_map_exists() -> None:
    text = (REPO_ROOT / "docs/README.md").read_text(encoding="utf-8")
    listed = [
        part
        for cell in re.findall(r"^\| `([^|]+)` \|", text, flags=re.M)
        for part in re.findall(r"[^`,+ ]+", cell)
    ]
    assert len(listed) > 10, "the docs map table format changed; update this test"
    missing = [p for p in listed if not _exists(posixpath.normpath(f"docs/{p}"))]
    assert not missing, f"docs/README.md lists paths that do not exist: {missing}"


def test_ci_job_names_match_the_main_ci_ruleset() -> None:
    """Renaming a required job without updating the ruleset blocks every merge."""
    ruleset = json.loads((REPO_ROOT / ".github/rulesets/main-ci.json").read_text(encoding="utf-8"))
    (checks,) = [r for r in ruleset["rules"] if r["type"] == "required_status_checks"]
    required = {c["context"] for c in checks["parameters"]["required_status_checks"]}
    ci = yaml.safe_load((REPO_ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8"))
    job_names = {job["name"] for job in ci["jobs"].values()}
    assert required <= job_names, (
        f"ruleset requires checks no CI job produces: {required - job_names}"
    )


def test_api_types_regeneration_never_needs_a_running_backend() -> None:
    """`poe dev` writes to the one shared database; regenerating types must import the app."""
    package = json.loads((REPO_ROOT / "frontend/package.json").read_text(encoding="utf-8"))
    gen_api = package["scripts"]["gen:api"]
    assert "localhost" not in gen_api and "export_openapi.py" in gen_api
    assert (REPO_ROOT / "backend/scripts/export_openapi.py").exists()
