# Tier 0 Delivery Guardrails Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Put a protected `main`, a CI workflow, a PR flow, committed Claude Code hooks and an interim deploy guard in place — the repo's first pull request — without changing any application behaviour.

**Architecture:** Everything lands on one feature branch and is opened as PR #1; the CI workflow in the PR proves itself on that PR. Rulesets and repository settings are stored as JSON in `.github/rulesets/` and applied through the GitHub API only after PR #1 is green and Matthias has said go (Task 10). The backend CI job runs the existing pytest suite against a throwaway Postgres 18 service container; no code in `backend/src` changes.

**Tech Stack:** GitHub Actions (`actions/checkout@v4`, `astral-sh/setup-uv@v6`, `actions/setup-node@v4`, `actions/upload-artifact@v4`, `postgres:18` service), GitHub rulesets API via `gh`, Python 3.13 hook scripts, PowerShell 5.1 (`deploy.ps1`), uv + poethepoet, npm.

**Spec:** `docs/superpowers/specs/2026-09-22-tier0-delivery-guardrails-design.md` — read it first; every task below argues from it.

## Global Constraints

- **No application behaviour changes.** Nothing under `backend/src/`, `backend/alembic/versions/`, `backend/prompts/` or `frontend/src/` is modified by this plan, except adding one new test file under `backend/tests/unit/`.
- **Work on branch `feature/tier0-delivery-guardrails`**, created from an up-to-date `main`. One commit per task, Conventional Commit titles, every commit message ends with the trailer `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>`.
- **Do not push to `main`, do not apply rulesets or repository settings, do not run `deploy.ps1` for real** anywhere in Tasks 1–9. Task 10 is the only task that touches GitHub settings and it has an explicit ask-Matthias gate.
- **Job names are load-bearing.** The two required status-check contexts are exactly `backend (format + lint + tests)` and `frontend (typecheck + lint + build)`. They appear in `ci.yml`, in `.github/rulesets/main-ci.json` and in `CONTRIBUTING.md`; all three must match byte-for-byte.
- **Backend verification gate** (inside `backend/`): `uv run poe format-check && uv run poe lint-src && uv run poe test`. Integration tests locally still use the Azure test DB via `backend/.env`; flaky `-n auto` runs happen — rerun before panicking.
- **Frontend verification gate** (inside `frontend/`): `npm run typecheck && npm run lint && npm run build`.
- **Hooks nudge, never block:** every hook script exits 0 on every path, including exceptions.
- **Windows dev machines:** hook commands invoke `python` (not `python3`, not bash). Files written by tasks use LF line endings (git normalises on commit; warnings about CRLF are expected and harmless).
- Repository: `DLW-INT-BTA-BELUX/ai-enablement-hub`. Default branch `main`.

---

## File structure

| Path | Responsibility | Task |
|---|---|---|
| `backend/pyproject.toml` | two new poe tasks `format-check`, `lint-src` | 1 |
| `.github/workflows/ci.yml` | the CI workflow: `backend`, `frontend`, `staged` jobs | 2 |
| `.github/rulesets/main-ci.json`, `main-review.json`, `README.md` | ruleset definitions + how to apply them | 3 |
| `.github/pull_request_template.md` | PR template | 4 |
| `CONTRIBUTING.md`, `README.md` | human workflow contract + pointer | 5 |
| `.claude/hooks/git_freshness.py`, `.claude/hooks/prod_asset_nudge.py`, `.claude/settings.json`, `.gitignore`, `backend/tests/unit/test_claude_hooks.py` | Claude Code repo config + tests | 6 |
| `deploy.ps1` | interim dirty-tree / not-origin-main guard | 7 |
| `CLAUDE.md` | Git, run/verify and deploy-procedure bullets | 8 |
| (GitHub) PR #1 | open, iterate to green | 9 |
| (GitHub) repository settings + rulesets | apply after gate, merge, verify | 10 |

---

### Task 0: Branch

**Files:** none.

- [ ] **Step 1: Create the branch from fresh `main`**

```bash
cd "/c/Users/danneelm/projects/AI enablement hub"
git switch main && git pull --ff-only
git switch -c feature/tier0-delivery-guardrails
git branch --show-current   # expect: feature/tier0-delivery-guardrails
```

---

### Task 1: Backend poe tasks `format-check` and `lint-src`

**Files:**
- Modify: `backend/pyproject.toml:52-62` (the `[tool.poe.tasks]` block)

**Interfaces:**
- Produces: `uv run poe format-check` (exit 0 iff `ruff format --check .` passes) and `uv run poe lint-src` (exit 0 iff `ruff check src tests alembic` passes). Used by Task 2 (CI), Task 4 (PR template), Task 5 (CONTRIBUTING), Task 8 (CLAUDE.md).

- [ ] **Step 1: Confirm the tasks do not exist yet**

Run (in `backend/`): `uv run poe format-check`
Expected: error mentioning an unknown task / "Unrecognised task".

- [ ] **Step 2: Add the two tasks**

In `backend/pyproject.toml`, replace

```toml
format = "ruff format ."
lint = "ruff check ."
```

with

```toml
format = "ruff format ."
# CI-facing variants: format-check never writes; lint-src scopes to the app, tests and
# migrations (backend/scripts carries pre-existing findings owned by the 2026-07-31 fix
# programme and is linted by the non-required "staged" CI job instead).
format-check = "ruff format --check ."
lint = "ruff check ."
lint-src = "ruff check src tests alembic"
```

- [ ] **Step 3: Run both and confirm they pass today**

Run (in `backend/`): `uv run poe format-check && uv run poe lint-src && echo OK`
Expected: `274 files already formatted` (count may differ), `All checks passed!`, `OK`.

- [ ] **Step 4: Commit**

```bash
git add backend/pyproject.toml
git commit -m "chore(backend): add poe format-check and lint-src for CI

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 2: CI workflow

**Files:**
- Create: `.github/workflows/ci.yml`

**Interfaces:**
- Consumes: `uv run poe format-check`, `uv run poe lint-src` (Task 1).
- Produces: status-check contexts `backend (format + lint + tests)` and `frontend (typecheck + lint + build)` (required by Task 3's `main-ci.json`), and a non-required `staged (scripts lint + ty)`.

- [ ] **Step 1: Write the workflow**

Create `.github/workflows/ci.yml`:

```yaml
# CI for the AI Enablement Hub — runs on every pull request and every push to main.
#
# JOB NAMES ARE LOAD-BEARING. The `main-ci` ruleset (.github/rulesets/main-ci.json) requires
# the `name:` of the backend and frontend jobs as status-check contexts. Renaming a job here
# without updating the ruleset blocks every merge. The `staged` job is deliberately NOT required
# (continue-on-error) — promote it in the ruleset once it has been green for a while.
#
# The backend job runs the real pytest suite against a throwaway Postgres 18 service container
# (not the shared Azure test DB): tests/conftest.py derives its DSN from ALEMBIC_DATABASE_URL,
# swaps the database name to ai-enablement-hub-test, creates the schema from Base.metadata and
# forces email/storage/llm settings to None — so no secrets are needed here.
name: CI

on:
  pull_request:
    branches: [main]
  push:
    branches: [main]
  workflow_dispatch:

permissions:
  contents: read

concurrency:
  # Superseded PR runs are cancelled; pushes to main never are.
  group: ci-${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: ${{ github.event_name == 'pull_request' }}

jobs:
  backend:
    name: backend (format + lint + tests)
    runs-on: ubuntu-latest
    timeout-minutes: 20
    defaults:
      run:
        working-directory: backend
    services:
      postgres:
        image: postgres:18
        env:
          POSTGRES_USER: hub
          POSTGRES_PASSWORD: hub
          POSTGRES_DB: ai-enablement-hub-test
        ports:
          - 5432:5432
        options: >-
          --health-cmd "pg_isready -U hub -d ai-enablement-hub-test"
          --health-interval 5s
          --health-timeout 5s
          --health-retries 10
    env:
      # conftest asserts the database name ends in "-test" before it drops/creates the schema.
      ALEMBIC_DATABASE_URL: postgresql+asyncpg://hub:hub@localhost:5432/ai-enablement-hub-test
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v6
        with:
          enable-cache: true
          cache-dependency-glob: backend/uv.lock
      - name: Install (locked, all extras — llm_service imports anthropic at module level)
        run: uv sync --frozen --all-extras
      - name: Format check
        run: uv run poe format-check
      - name: Lint (src, tests, alembic)
        run: uv run poe lint-src
      - name: Tests with coverage
        # -n 4 rather than -n auto: the runner has 4 vCPUs and conftest's auto rule would leave
        # only 2 workers. Coverage is measured and uploaded; no threshold yet (Tier 2).
        run: uv run pytest tests -n 4 --cov=src --cov-report=xml --cov-report=term
      - uses: actions/upload-artifact@v4
        if: always()
        with:
          name: backend-coverage
          path: backend/coverage.xml
          retention-days: 14

  frontend:
    name: frontend (typecheck + lint + build)
    runs-on: ubuntu-latest
    timeout-minutes: 15
    defaults:
      run:
        working-directory: frontend
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: 22
          cache: npm
          cache-dependency-path: frontend/package-lock.json
      - run: npm ci
      - run: npm run typecheck
      - run: npm run lint
      - run: npm run build

  staged:
    # Not required by the ruleset. Runs the checks that are not clean yet (30 ruff findings in
    # backend/scripts, ~25 ty diagnostics) so the debt is visible on every PR without blocking.
    name: staged (scripts lint + ty) — not required
    runs-on: ubuntu-latest
    timeout-minutes: 15
    continue-on-error: true
    defaults:
      run:
        working-directory: backend
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v6
        with:
          enable-cache: true
          cache-dependency-glob: backend/uv.lock
      - run: uv sync --frozen --all-extras
      - name: Lint scripts
        run: uv run ruff check scripts
      - name: Type check
        run: uv run poe ty
```

- [ ] **Step 2: Validate the YAML parses and the job names are exact**

Run (repo root):

```bash
python - <<'EOF'
import yaml, io
d = yaml.safe_load(io.open('.github/workflows/ci.yml', encoding='utf-8'))
names = [j['name'] for j in d['jobs'].values()]
print(names)
assert names[:2] == ['backend (format + lint + tests)', 'frontend (typecheck + lint + build)']
print("OK")
EOF
```

If `yaml` is missing: `cd backend && uv run --with pyyaml python - <<'EOF' ... EOF` with the same body and path `../.github/workflows/ci.yml`.
Expected: the two names printed exactly, then `OK`.

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/ci.yml
git commit -m "ci: add GitHub Actions workflow (backend, frontend, staged)

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 3: Ruleset definitions as JSON

**Files:**
- Create: `.github/rulesets/main-ci.json`
- Create: `.github/rulesets/main-review.json`
- Create: `.github/rulesets/README.md`

**Interfaces:**
- Consumes: the two job names from Task 2.
- Produces: files applied verbatim in Task 10 with `gh api … --input`.

- [ ] **Step 1: Write `main-ci.json`**

```json
{
  "name": "main-ci",
  "target": "branch",
  "enforcement": "active",
  "bypass_actors": [],
  "conditions": {
    "ref_name": { "include": ["~DEFAULT_BRANCH"], "exclude": [] }
  },
  "rules": [
    { "type": "deletion" },
    { "type": "non_fast_forward" },
    {
      "type": "pull_request",
      "parameters": {
        "required_approving_review_count": 0,
        "dismiss_stale_reviews_on_push": false,
        "require_code_owner_review": false,
        "require_last_push_approval": false,
        "required_review_thread_resolution": false,
        "allowed_merge_methods": ["squash"]
      }
    },
    {
      "type": "required_status_checks",
      "parameters": {
        "strict_required_status_checks_policy": false,
        "do_not_enforce_on_create": false,
        "required_status_checks": [
          { "context": "backend (format + lint + tests)" },
          { "context": "frontend (typecheck + lint + build)" }
        ]
      }
    }
  ]
}
```

- [ ] **Step 2: Write `main-review.json`**

```json
{
  "name": "main-review",
  "target": "branch",
  "enforcement": "active",
  "bypass_actors": [
    { "actor_id": 5, "actor_type": "RepositoryRole", "bypass_mode": "always" }
  ],
  "conditions": {
    "ref_name": { "include": ["~DEFAULT_BRANCH"], "exclude": [] }
  },
  "rules": [
    {
      "type": "pull_request",
      "parameters": {
        "required_approving_review_count": 1,
        "dismiss_stale_reviews_on_push": true,
        "require_code_owner_review": false,
        "require_last_push_approval": false,
        "required_review_thread_resolution": false,
        "allowed_merge_methods": ["squash"]
      }
    }
  ]
}
```

(`actor_id: 5` + `RepositoryRole` is GitHub's built-in **admin** role — the same actor the
`sb-accelerator` `main-review` ruleset grants bypass to.)

- [ ] **Step 3: Write `.github/rulesets/README.md`**

````markdown
# Branch rulesets for `main`

These two files are the source of truth for how `main` is protected. Apply or re-apply them
with the GitHub CLI (repo admin required). They mirror the delaware house pattern
(`bta-agents-portal`, `sb-accelerator`).

| File | What it enforces | Bypass |
|---|---|---|
| `main-ci.json` | changes reach `main` only via a pull request; the two `CI` checks `backend (format + lint + tests)` and `frontend (typecheck + lint + build)` must be green; squash merge only; no force-push, no deletion | **nobody** — admins included |
| `main-review.json` | one approving review | repository admins |

## Apply (first time)

```bash
gh api repos/DLW-INT-BTA-BELUX/ai-enablement-hub/rulesets -X POST --input .github/rulesets/main-ci.json
gh api repos/DLW-INT-BTA-BELUX/ai-enablement-hub/rulesets -X POST --input .github/rulesets/main-review.json
```

## Update an existing ruleset

```bash
gh api repos/DLW-INT-BTA-BELUX/ai-enablement-hub/rulesets --jq '.[] | "\(.id) \(.name)"'
gh api repos/DLW-INT-BTA-BELUX/ai-enablement-hub/rulesets/<id> -X PUT --input .github/rulesets/<name>.json
```

## Verify

```bash
gh api repos/DLW-INT-BTA-BELUX/ai-enablement-hub/rulesets --jq '.[] | "\(.name) \(.enforcement)"'
```

**If you rename a CI job** in `.github/workflows/ci.yml`, update the `context` strings in
`main-ci.json` in the same PR and re-apply with `PUT` right after merging — otherwise every
merge is blocked waiting for a check that no longer exists.
````

- [ ] **Step 4: Validate the JSON and the contexts match `ci.yml`**

```bash
python - <<'EOF'
import json, io, yaml
ci = yaml.safe_load(io.open('.github/workflows/ci.yml', encoding='utf-8'))
required = {j['name'] for k, j in ci['jobs'].items() if k in ('backend', 'frontend')}
rs = json.load(io.open('.github/rulesets/main-ci.json', encoding='utf-8'))
ctx = {c['context'] for r in rs['rules'] if r['type'] == 'required_status_checks' for c in r['parameters']['required_status_checks']}
json.load(io.open('.github/rulesets/main-review.json', encoding='utf-8'))
assert required == ctx, (required, ctx)
print("contexts match:", sorted(ctx))
EOF
```

Expected: `contexts match: ['backend (format + lint + tests)', 'frontend (typecheck + lint + build)']`.

- [ ] **Step 5: Commit**

```bash
git add .github/rulesets
git commit -m "ci: store main-ci and main-review rulesets as JSON with apply instructions

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 4: Pull request template

**Files:**
- Create: `.github/pull_request_template.md`

- [ ] **Step 1: Write the template**

```markdown
## What & why

<!-- One or two sentences: what changes for a learner, an admin, or an operator, and why. -->

## Checklist

- [ ] Backend checks pass locally (in `backend/`): `uv run poe format-check && uv run poe lint-src && uv run poe test`
- [ ] Frontend checks pass locally (in `frontend/`): `npm run typecheck && npm run lint && npm run build`
- [ ] No secret is committed — real values live only in the git-ignored `backend/.env` / `db/.env`
- [ ] **Migration** (if this adds one under `backend/alembic/versions/`): additive / expand-first, fast on the live tables, safe to run twice — it runs unattended on container start against the production database
- [ ] **Learner-facing change** (if any): verified with production-shaped fixtures and a stubbed `fetch`, never by creating users, surveys or progress (see CLAUDE.md → "Verifying without touching live data")
- [ ] **Prompt change** (`backend/prompts/**`): treated as a production change; confirmed no DB override on the admin System Prompts page masks it
- [ ] `CLAUDE.md` / `docs/` updated where this changes how the app is run or operated
- [ ] Verified with evidence, not assumed

## Linked issue

Closes #

<!--
Merging: `main` is protected. Both CI checks must be green (no bypass, admins included) and the
PR needs one approving review unless a repo admin merges it. Squash merge only:
`gh pr merge --squash --delete-branch`. Flow and policy: CONTRIBUTING.md.
-->
```

- [ ] **Step 2: Commit**

```bash
git add .github/pull_request_template.md
git commit -m "docs: add pull request template

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 5: `CONTRIBUTING.md` and README pointer

**Files:**
- Create: `CONTRIBUTING.md`
- Modify: `README.md:32-34` ("Where to look" list)

- [ ] **Step 1: Write `CONTRIBUTING.md`**

````markdown
# Contributing

This repo is built by a small team of people who are not full-time engineers, mostly by driving
Claude Code. The rules below keep `main` always working and every change validated by CI. They
are simple on purpose, and GitHub enforces the important ones so nobody has to remember them.

## The golden rule: never commit straight to `main`

`main` is **protected** — you cannot push to it directly, and you cannot merge a red build. All
changes go through:

**branch → commit → push → open a pull request → both CI checks green → (review) → squash merge.**

## Step by step

**1. Start from the latest `main`:**
```bash
git switch main
git pull
git switch -c <type>/<short-description>
```
`<type>` is one of `feat`, `fix`, `chore`, `docs`, `refactor`, `test`, `content`.
Example: `git switch -c fix/people-detail-404`.

**2. Work in small commits.** Commit often; a change that is easy to read is easy to review and
easy to undo. Commit titles follow Conventional Commits: `<type>(<area>): <imperative summary>`,
e.g. `fix(admin): show a Maturity badge for the multiplier level`.

**3. Run the checks yourself before you push** (Claude does this for you when asked):
```powershell
cd backend;  uv run poe format-check; uv run poe lint-src; uv run poe test
cd ..\frontend; npm run typecheck; npm run lint; npm run build
```
The backend tests run against the shared Azure test database; a flaky run happens now and then —
rerun once before investigating.

**4. Push and open the pull request:**
```bash
git push -u origin HEAD
gh pr create --fill
```
Fill in the template: what & why, the checklist, and `Closes #<issue>` if there is one.

**5. Wait for the checks.** The `CI` workflow (`.github/workflows/ci.yml`) posts two required
checks on the PR: `backend (format + lint + tests)` and `frontend (typecheck + lint + build)`.
A third check, `staged (scripts lint + ty) — not required`, reports known debt and may be red;
it does not block. If a required check is red: open the job log, fix, push again. **Never work
around a red check** — there is no bypass, and that is the point.

**6. Review.** Non-admin contributors need one approving review. Repo admins may merge their own
PR without a review, **but the policy is:** admin self-merge is for docs, hotfixes and
trivially-green changes only. Anything touching authentication, migrations, prompts or a
learner-facing flow waits for the other admin. Ask for a review in the PR with `@<login>`.

**7. Merge — squash only:**
```bash
gh pr merge --squash --delete-branch
```
(or the green "Squash and merge" button). The PR title becomes the one commit on `main`; the
branch is deleted automatically.

## What GitHub enforces (the two rulesets)

Definitions live in `.github/rulesets/`; apply/verify instructions are in that folder's README.

- **`main-ci`** — a pull request is required; both `CI` checks must pass; squash merge only; no
  force-push; `main` cannot be deleted. **No bypass for anyone, admins included.**
- **`main-review`** — one approving review; repo admins may bypass (see the policy in step 6).

## Deploying

Deploying is still a manual step (`.\deploy.ps1`, see `CLAUDE.md` → "Deployment & operations").
The script refuses to run unless your working tree is clean **and** your `HEAD` is exactly the
pushed `origin/main` — so: merge the PR, `git switch main && git pull`, then deploy. Moving the
deploy into CI is the next step of the roadmap (`docs/reviews/2026-09-17/`, Tier 1).

## Working with Claude Code in this repo

`.claude/settings.json` is committed. On session start it tells you if your `main` is behind
`origin/main`; when a file under `frontend/src/`, `backend/prompts/` or `backend/alembic/versions/`
is edited it reminds you what that file needs before it is done; and it asks before force-pushing,
pushing to `main`, running `deploy.ps1`, `az containerapp …` or `alembic upgrade`. Your personal
overrides go in the git-ignored `.claude/settings.local.json`.

## Where the deeper docs are

- `CLAUDE.md` — the operational guide for agents and operators (current state, conventions,
  locking semantics, deploy/ops).
- `python-be-architecture.md` — mandatory backend conventions.
- `docs/README.md` — map of the docs tree; `db/README.md` — database roles and procedures.
- `docs/reviews/2026-09-17/` — why this workflow exists and what comes next.
````

- [ ] **Step 2: Add the README pointer**

In `README.md`, inside "## Where to look", insert as the **first** bullet (before the CLAUDE.md
bullet):

```markdown
- **[CONTRIBUTING.md](CONTRIBUTING.md)** — how to make a change: branch → PR → green CI → squash
  merge. `main` is protected. **Humans: read this first.**
```

- [ ] **Step 3: Check every command in CONTRIBUTING exists**

Run (in `backend/`): `uv run poe format-check && uv run poe lint-src` → both pass.
Run (repo root): `gh pr create --help >/dev/null && gh pr merge --help >/dev/null && echo gh-ok` → `gh-ok`.

- [ ] **Step 4: Commit**

```bash
git add CONTRIBUTING.md README.md
git commit -m "docs: add CONTRIBUTING.md (branch -> PR -> green CI -> squash) and README pointer

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 6: Committed Claude Code configuration with tested hooks

**Files:**
- Create: `.claude/hooks/git_freshness.py`
- Create: `.claude/hooks/prod_asset_nudge.py`
- Create: `.claude/settings.json`
- Modify: `.gitignore` (the `.claude/` line)
- Test: `backend/tests/unit/test_claude_hooks.py`

**Interfaces:**
- Produces: two scripts that read the Claude Code hook JSON on stdin and print at most one JSON object `{"systemMessage": "<text>"}` on stdout, always exit 0. `prod_asset_nudge.py` exposes `message_for(path: str) -> str | None` for tests.

- [ ] **Step 1: Un-ignore the committed parts of `.claude/`**

In `.gitignore`, replace the line `.claude/` with:

```gitignore
.claude/*
!.claude/settings.json
!.claude/hooks/
.claude/hooks/__pycache__/
```

Check: `git check-ignore -v .claude/settings.local.json .claude/scheduled_tasks.lock` → both
listed as ignored; `git check-ignore .claude/settings.json; echo "exit=$?"` → `exit=1` (not ignored).

- [ ] **Step 2: Write the failing tests**

Create `backend/tests/unit/test_claude_hooks.py`:

```python
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
```

- [ ] **Step 3: Run the tests to verify they fail**

Run (in `backend/`): `uv run pytest tests/unit/test_claude_hooks.py -q`
Expected: failures — the scripts do not exist (`FileNotFoundError` / non-zero exit).

- [ ] **Step 4: Write `prod_asset_nudge.py`**

```python
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
        "is a production asset: the system prompts are baked into the Docker image and can be "
        "masked by a DB override on the admin System Prompts page. Treat the edit as a "
        "production change and check no override hides it.",
    ),
    (
        "backend/alembic/versions/",
        "is a migration that runs unattended on container start against the live database. It "
        "must be additive / expand-first, fast on the live tables, and safe to run twice.",
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
```

- [ ] **Step 5: Write `git_freshness.py`**

```python
#!/usr/bin/env python3
"""SessionStart hook: tell the session how stale its checkout is.

Fetches origin and reports "main is N commit(s) behind origin/main" and, on a feature branch,
how far behind its upstream it is. Skips entirely under GitHub Actions. Nudges, never blocks:
exit 0 on every path. Set GIT_FRESHNESS_SKIP_FETCH=1 to skip the network call (tests).
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
            print(json.dumps({"systemMessage": msg}))
    except Exception:  # noqa: BLE001 - a hook must never block a session
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 6: Run the tests to verify they pass**

Run (in `backend/`): `uv run pytest tests/unit/test_claude_hooks.py -q`
Expected: all pass (`8 passed`).

- [ ] **Step 7: Write `.claude/settings.json`**

```json
{
  "$schema": "https://json.schemastore.org/claude-code-settings.json",
  "hooks": {
    "SessionStart": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python .claude/hooks/git_freshness.py",
            "timeout": 30,
            "statusMessage": "Checking how far behind origin/main this checkout is..."
          }
        ]
      }
    ],
    "PostToolUse": [
      {
        "matcher": "Edit|Write|MultiEdit",
        "hooks": [
          {
            "type": "command",
            "command": "python .claude/hooks/prod_asset_nudge.py",
            "timeout": 10
          }
        ]
      }
    ]
  },
  "permissions": {
    "allow": [
      "Bash(uv run poe:*)",
      "Bash(uv run pytest:*)",
      "Bash(uv run ruff:*)",
      "Bash(npm run:*)",
      "Bash(gh pr view:*)",
      "Bash(gh pr list:*)",
      "Bash(gh pr checks:*)",
      "Bash(gh issue view:*)",
      "Bash(gh issue list:*)",
      "Bash(gh run list:*)",
      "Bash(gh run view:*)"
    ],
    "ask": [
      "Bash(git push --force:*)",
      "Bash(git push -f:*)",
      "Bash(git push * main)",
      "Bash(git push *:main)",
      "Bash(*deploy.ps1*)",
      "Bash(*az containerapp*)",
      "Bash(*alembic upgrade*)"
    ]
  }
}
```

- [ ] **Step 8: Smoke-test the hooks by hand the way Claude Code calls them**

Run (repo root):

```bash
echo '{"tool_input":{"file_path":"frontend/src/App.tsx"}}' | python .claude/hooks/prod_asset_nudge.py
echo '{}' | python .claude/hooks/git_freshness.py
```

Expected: first prints a `[prod-asset] App.tsx …` JSON line; second prints `{"systemMessage": "[git] main is up to date."}` or a "behind" message. Both exit 0 (`echo $?`).

- [ ] **Step 9: Backend gate still green, then commit**

Run (in `backend/`): `uv run poe format-check && uv run poe lint-src` → pass (the new test file is linted).

```bash
git add .gitignore .claude/settings.json .claude/hooks/git_freshness.py .claude/hooks/prod_asset_nudge.py backend/tests/unit/test_claude_hooks.py
git status --short   # must NOT list .claude/settings.local.json or scheduled_tasks.lock
git commit -m "chore(claude): commit repo-level Claude Code settings with freshness and prod-asset hooks

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 7: Interim `deploy.ps1` guard

**Files:**
- Modify: `deploy.ps1` (insert after `$ErrorActionPreference = "Stop"`, before the `$env:PYTHONIOENCODING` line)

- [ ] **Step 1: Add the guard**

Insert into `deploy.ps1` directly after the line `$ErrorActionPreference = "Stop"`:

```powershell
# --- Interim guard (Tier 0, 2026-09-22): ship only the pushed origin/main. -------------------
# `az acr build` uploads this directory as-is, so an uncommitted edit or an un-pushed commit
# would go live untraceably (it has happened: 2026-07-22). Refuse both. Retired when the
# CI-driven deploy lands (Tier 1); no -Force switch on purpose.
& git -C $PSScriptRoot fetch origin --quiet
if ($LASTEXITCODE -ne 0) { throw "deploy guard: 'git fetch origin' failed - are you online and authenticated?" }
$dirty = & git -C $PSScriptRoot status --porcelain
if ($dirty) {
    throw "deploy guard: working tree is dirty - commit or stash first. deploy.ps1 ships the directory as-is.`n$($dirty -join "`n")"
}
$head = (& git -C $PSScriptRoot rev-parse HEAD).Trim()
$originMain = (& git -C $PSScriptRoot rev-parse origin/main).Trim()
if ($head -ne $originMain) {
    throw "deploy guard: HEAD ($($head.Substring(0,7))) is not origin/main ($($originMain.Substring(0,7))). Merge the PR, then: git switch main; git pull; and deploy from there."
}
$subject = (& git -C $PSScriptRoot log -1 --format=%s).Trim()
Write-Host "deploy guard: shipping $($head.Substring(0,7)) - $subject" -ForegroundColor Green
# ------------------------------------------------------------------------------------------
```

- [ ] **Step 2: Test the guard without deploying — dirty tree**

With `deploy.ps1` itself modified and uncommitted, run in PowerShell from the repo root:

```powershell
.\deploy.ps1 -BuildOnly
```

Expected: the script throws `deploy guard: working tree is dirty …` **before** any `az` output. (`-BuildOnly` is just belt-and-braces; the throw happens first.)

- [ ] **Step 3: Test the guard — clean tree but not origin/main**

Commit the change (Step 5 below, then come back), so the tree is clean but `HEAD` is the feature branch:

```powershell
.\deploy.ps1 -BuildOnly
```

Expected: `deploy guard: HEAD (…) is not origin/main (…)`, again before any `az` call.

- [ ] **Step 4: Confirm the script still parses**

```powershell
[void][System.Management.Automation.Language.Parser]::ParseFile("$PWD\deploy.ps1", [ref]$null, [ref]$errors); $errors.Count
```

Expected: `0`.

- [ ] **Step 5: Commit**

```bash
git add deploy.ps1
git commit -m "chore(deploy): refuse to ship a dirty tree or anything but origin/main

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

(Then run Step 3.)

---

### Task 8: `CLAUDE.md` updates

**Files:**
- Modify: `CLAUDE.md:51-52` (Git bullet), `CLAUDE.md:59-61` (Backend checks bullet), `CLAUDE.md:219-225` (Deploy procedure bullet)

- [ ] **Step 1: Rewrite the Git bullet**

Replace

```markdown
- **Git:** `main` is the only long-lived branch; use `feature/*` for work and fast-forward
  `main`. `deploy.ps1` builds the **working directory, not git** — push after every deploy.
```

with

```markdown
- **Git:** `main` is the only long-lived branch and is **protected** (rulesets in
  `.github/rulesets/`): every change is a `<type>/<topic>` branch → pull request → both `CI`
  checks green → **squash merge**. No direct pushes, no force-pushes, admins included. Flow and
  policy: `CONTRIBUTING.md`. `deploy.ps1` builds the **working directory, not git**, and since
  2026-09-22 refuses to run unless the tree is clean and `HEAD == origin/main`.
```

- [ ] **Step 2: Rewrite the Backend checks bullet**

Replace

```markdown
- **Backend** (inside `backend/`): checks = `uv run poe format && uv run poe lint && uv run poe test`
  (integration tests hit the `ai-enablement-hub-test` Azure PG DB). Dev server: `uv run poe dev`
  (→ :8000, Swagger at `/docs`). Migrations: `uv run poe upgrade`.
```

with

```markdown
- **Backend** (inside `backend/`): checks = `uv run poe format-check && uv run poe lint-src &&
  uv run poe test` — the same three CI runs (`poe format` rewrites, `poe lint` also covers
  `scripts/`, which carries known findings and is linted by the non-required `staged` CI job).
  Locally the integration tests hit the `ai-enablement-hub-test` Azure PG DB; in CI they run
  against a throwaway `postgres:18` service container. Dev server: `uv run poe dev`
  (→ :8000, Swagger at `/docs`). Migrations: `uv run poe upgrade`.
```

- [ ] **Step 3: Amend the Deploy procedure bullet**

Replace

```markdown
- **Deploy procedure (the discipline is hard-won):** commit only the specific change (never a
  blanket `git add -A`), push, then build from a **fresh `git worktree` of the pushed commit**
  (short path near the drive root, `-c core.longpaths=true`), because `az acr build` uploads
  the working directory as-is. Run `.\deploy.ps1` from that worktree. After deploying:
  fast-forward `main` and push. Post-deploy checks: `/api/health`, `/api/auth/methods`,
  `latestReadyRevision == latestRevision`, and for frontend changes grep the served
  `/assets/index-*.js` for a new copy string.
```

with

```markdown
- **Deploy procedure (the discipline is hard-won):** merge the PR (squash), then
  `git switch main && git pull`, then run `.\deploy.ps1`. The script's guard (2026-09-22)
  refuses a dirty tree or any `HEAD` other than `origin/main`, because `az acr build` uploads
  the working directory as-is. Building from a **fresh `git worktree` of `origin/main`** (short
  path near the drive root, `-c core.longpaths=true`) remains the safest way to satisfy it.
  Post-deploy checks: `/api/health`, `/api/auth/methods`, `latestReadyRevision ==
  latestRevision`, and for frontend changes grep the served `/assets/index-*.js` for a new copy
  string. CI-driven deploy is Tier 1 of `docs/reviews/2026-09-17/`.
```

- [ ] **Step 4: Add a "Current state" line**

Directly under the `- **Pending work queue:**` bullet in "Current state", add:

```markdown
- **Way of working (2026-09-22):** Tier 0 guardrails shipped as PR #1 — protected `main`,
  `CI` workflow, PR template, `CONTRIBUTING.md`, committed `.claude/settings.json` hooks,
  `deploy.ps1` guard. Roadmap and open decisions: `docs/reviews/2026-09-17/`.
```

- [ ] **Step 5: Check the three referenced commands/paths exist**

`uv run poe format-check` and `uv run poe lint-src` pass (Task 1); `.github/rulesets/` and `CONTRIBUTING.md` exist (Tasks 3, 5).

- [ ] **Step 6: Commit**

```bash
git add CLAUDE.md
git commit -m "docs(claude): protected main, CI-facing checks, deploy guard

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 9: Open PR #1 and drive it to green

**Files:** none (GitHub).

- [ ] **Step 1: Run both local gates one last time**

In `backend/`: `uv run poe format-check && uv run poe lint-src && uv run poe test` → green.
In `frontend/`: `npm run typecheck && npm run lint && npm run build` → green.

- [ ] **Step 2: Push the branch and open the PR**

```bash
git push -u origin feature/tier0-delivery-guardrails
gh pr create --title "chore: Tier 0 delivery guardrails (protected main, CI, PR flow, hooks)" --body-file - <<'EOF'
## What & why

The repo's first pull request. Adds the mechanisms the 2026-09-17 way-of-working comparison
(`docs/reviews/2026-09-17/`) put in Tier 0: a CI workflow running the checks we already have
(backend against a throwaway Postgres 18 container), the two `main` rulesets as JSON, a PR
template, `CONTRIBUTING.md` for non-engineers, committed Claude Code hooks, and a `deploy.ps1`
guard that refuses to ship anything but the pushed `origin/main`. No application behaviour
changes. Spec: `docs/superpowers/specs/2026-09-22-tier0-delivery-guardrails-design.md`.

Rulesets and repository merge settings are applied **after** this PR is green (see the spec
§4 rollout) — this PR only adds the files.

## Checklist

- [x] Backend checks pass locally: `uv run poe format-check && uv run poe lint-src && uv run poe test`
- [x] Frontend checks pass locally: `npm run typecheck && npm run lint && npm run build`
- [x] No secret is committed
- [x] Migration: none
- [x] Learner-facing change: none
- [x] Prompt change: none
- [x] `CLAUDE.md` / `docs/` updated
- [x] Verified with evidence, not assumed — CI runs on this very PR

## Linked issue

n/a

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
```

- [ ] **Step 3: Watch the checks**

```bash
gh pr checks --watch --interval 20
```

Expected: `backend (format + lint + tests)` and `frontend (typecheck + lint + build)` pass; `staged (…) — not required` may fail (that is its job). Note the backend job duration in the PR as a comment.

- [ ] **Step 4: If the backend job is red, diagnose from the log, not by guessing**

```bash
gh run list --branch feature/tier0-delivery-guardrails --limit 3
gh run view <run-id> --log-failed | head -200
```

Likely first-run issues and their fixes (each a small follow-up commit on the branch):
- `asyncpg` refuses `ssl` — the URL in `ci.yml` has no `?ssl=` param, so this should not occur; if `conftest` appends one, set `ALEMBIC_DATABASE_URL=…?ssl=disable`.
- Postgres not ready — the health check gates the job; if a connection is refused, raise `--health-retries`.
- `uv sync --all-extras` fails on `httptools` wheels — pin the Python via `astral-sh/setup-uv` `python-version: "3.13"`.
- Runtime over 10 min — reduce to `-n 3` or split integration/unit into two steps.

- [ ] **Step 5: Confirm the check names GitHub recorded match the ruleset**

```bash
gh api repos/DLW-INT-BTA-BELUX/ai-enablement-hub/commits/$(git rev-parse HEAD)/check-runs --jq '.check_runs[].name'
```

Expected output includes exactly `backend (format + lint + tests)` and `frontend (typecheck + lint + build)`. If GitHub shows different strings, fix `ci.yml`/`main-ci.json` so they match — **do not proceed to Task 10 until they do.**

---

### Task 10: Apply repository settings and rulesets, merge, verify — **ASK-MATTHIAS GATE**

**Files:** none (GitHub settings). Uses `.github/rulesets/*.json` from the branch (same content
as what will be on `main` after merge).

- [ ] **Step 1: STOP and ask Matthias**

Report: PR #1 is green, the check names match, and the next command makes direct pushes to `main`
impossible for everyone including Aaron. Ask for an explicit go, and ask him to tell Aaron.
**Do not continue without it.**

- [ ] **Step 2: Repository merge settings**

```bash
gh api -X PATCH repos/DLW-INT-BTA-BELUX/ai-enablement-hub \
  -F allow_squash_merge=true -F allow_merge_commit=false -F allow_rebase_merge=false \
  -F delete_branch_on_merge=true -F squash_merge_commit_title=PR_TITLE -F squash_merge_commit_message=PR_BODY \
  --jq '{allow_squash_merge, allow_merge_commit, allow_rebase_merge, delete_branch_on_merge, squash_merge_commit_title, squash_merge_commit_message}'
```

Expected: the six fields echo back with the requested values.

- [ ] **Step 3: Apply `main-ci`, then `main-review`**

```bash
gh api repos/DLW-INT-BTA-BELUX/ai-enablement-hub/rulesets -X POST --input .github/rulesets/main-ci.json --jq '{id, name, enforcement}'
gh api repos/DLW-INT-BTA-BELUX/ai-enablement-hub/rulesets -X POST --input .github/rulesets/main-review.json --jq '{id, name, enforcement}'
gh api repos/DLW-INT-BTA-BELUX/ai-enablement-hub/rulesets --jq '.[] | "\(.name) \(.enforcement)"'
```

Expected: two ids returned; the list shows `main-ci active` and `main-review active`.

- [ ] **Step 4: Merge PR #1 — the first protected merge**

```bash
gh pr merge --squash --delete-branch
git switch main && git pull --ff-only
git log --oneline -1   # the squash commit, title = PR title
```

Expected: merge succeeds (author is an admin, so `main-review` is bypassed; `main-ci` is satisfied by the green checks). The remote branch is deleted.

- [ ] **Step 5: Verify the protection actually bites**

```bash
git switch -c chore/protection-probe
echo "# probe" >> README.md && git commit -am "chore: probe (never merged)"
git push origin HEAD:main
```

Expected: **rejected** with a message naming the ruleset (e.g. "Changes must be made through a pull request"). Then clean up:

```bash
git switch main && git branch -D chore/protection-probe
```

- [ ] **Step 6: Verify CI ran on the `main` push and the hooks work**

```bash
gh run list --branch main --limit 2      # the post-merge CI run: success
```

Start a new Claude Code session in the repo: the `[git] main is up to date.` message appears. Edit any file under `frontend/src/` in that session (then revert): the `[prod-asset]` nudge appears.

- [ ] **Step 7: Record the outcome**

Add to the "Way of working (2026-09-22)" line in `CLAUDE.md` (via a small PR — `main` is protected now): "Rulesets applied <date>; PR #1 merged as `<sha>`; backend CI job ≈ N min." Also update the memory note `project-way-of-working-comparison-2026-09-17.md`: Tier 0 done.

---

## Self-review against the spec

- §3.1 CI → Task 2 (jobs, names, service container, concurrency, permissions, coverage artifact, staged job) + Task 1 (poe tasks). ✔
- §3.2 rulesets + repo settings → Task 3 (JSON + README) + Task 10 (apply). ✔
- §3.3 PR template → Task 4. ✔
- §3.4 CONTRIBUTING + README pointer → Task 5. ✔
- §3.5 `.claude/` config, hooks, gitignore → Task 6 (with tests). ✔
- §3.6 deploy guard → Task 7. ✔
- §3.7 CLAUDE.md updates → Task 8. ✔
- §4 rollout order (PR first, rulesets after green + ask) → Tasks 9–10; Aaron heads-up in Task 10 Step 1. ✔
- §5 verification → Tasks 9 Step 5, 10 Steps 5–6. ✔
- Names: `format-check` / `lint-src` used identically in Tasks 1, 2, 4, 5, 8. Job names identical in Tasks 2, 3, 5, 9. Hook filenames identical in Tasks 6 and 5/8 prose. ✔
