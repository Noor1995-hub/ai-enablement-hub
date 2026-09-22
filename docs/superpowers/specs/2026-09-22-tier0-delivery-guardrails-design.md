# Tier 0 — Delivery guardrails: protected `main`, CI, PR flow, Claude Code hooks

**Date:** 2026-09-22
**Status:** draft for review
**Source:** `docs/reviews/2026-09-17/WAY-OF-WORKING-COMPARISON-2026-09-17.md` §5 Tier 0 (items 0.1–0.7)
**Reference pattern:** `DLW-INT-BTA-BELUX/bta-agents-portal` (rulesets, CI, CONTRIBUTING, hooks) and
`sb-accelerator` (squash-only, `PostToolUse` nudge). Study notes in `docs/reviews/2026-09-17/`.

## 1. Goal

Make the wrong move impossible instead of discouraged, without changing any application behaviour:

- Nothing reaches `main` except through a pull request whose CI checks are green.
- CI runs the six checks the repo already defines (`poe format/lint/test`, `npm run
  typecheck/lint/build`) on every PR and every push to `main`.
- Every change has a written "what & why" and a checklist; history on `main` is linear, one
  squash commit per PR.
- A non-engineer can learn the whole flow from one short `CONTRIBUTING.md`.
- Claude Code sessions in this repo start with a stale-branch warning, get nudged when they touch
  CI-invisible assets, and must ask before force-pushing, pushing to `main`, or deploying.
- Until Tier 1 replaces it, `deploy.ps1` refuses to ship anything that is not the pushed `main`.

## 2. Non-goals (Tier 1+)

CI-driven deploy, OIDC identity, pre-deploy migration job, `BUILD_SHA` in `/api/health`, Claude
PR review workflow, dev database, `SECURITY.md`, `lessons.md`, frontend tests, coverage
threshold, Dependabot, docs-drift test, `CLAUDE.md` split. None of the five open decisions in the
comparison §6 is needed for Tier 0.

## 3. Design

### 3.1 CI workflow — `.github/workflows/ci.yml`

**Triggers:** `pull_request` (any branch → `main`), `push` on `main`, `workflow_dispatch`.
**Permissions:** `contents: read` only. **Concurrency:** group per ref, `cancel-in-progress`
only for PR runs (main runs never cancel — portal rule).

**Job names are load-bearing.** The rulesets in §3.2 require them by exact string; renaming a
job without updating the ruleset blocks every merge. A comment at the top of the file says so.

| Job | Name (status-check context) | Steps |
|---|---|---|
| `backend` | `backend (format + lint + tests)` | `actions/checkout@v4` → `astral-sh/setup-uv@v6` (cache on) → `uv sync --frozen --all-extras` (the `prod` extra is needed: `services/llm_service.py` imports `anthropic` at module level and unit tests import it) → `uv run ruff format --check .` → `uv run ruff check src tests alembic` → `uv run pytest tests -n auto --cov=src --cov-report=xml --cov-report=term` (coverage measured and uploaded as an artifact; **no threshold yet** — that is Tier 2.2) |
| `frontend` | `frontend (typecheck + lint + build)` | `actions/checkout@v4` → `actions/setup-node@v4` (node 22, npm cache keyed on `frontend/package-lock.json`) → `npm ci` → `npm run typecheck` → `npm run lint` (as-is; one pre-existing warning is allowed — tightening to zero warnings is Tier 2) → `npm run build` |
| `staged` | `staged (scripts lint + ty) — not required` | `uv run ruff check scripts` and `uv run poe ty`; `continue-on-error: true`; **not in the ruleset**. Promoted once green (accelerator's staging pattern). Today: 30 ruff findings in `scripts/`, 25 ty diagnostics. |

**Database for the backend job — a throwaway Postgres service container**, not the shared Azure
test DB:

```yaml
services:
  postgres:
    image: postgres:18
    env:
      POSTGRES_USER: hub
      POSTGRES_PASSWORD: hub
      POSTGRES_DB: ai-enablement-hub-test      # conftest asserts the name ends in "-test"
    ports: ["5432:5432"]
    options: >-
      --health-cmd "pg_isready -U hub" --health-interval 5s --health-timeout 5s --health-retries 10
env:
  ALEMBIC_DATABASE_URL: postgresql+asyncpg://hub:hub@localhost:5432/ai-enablement-hub-test
```

Why this works without code changes (verified 2026-09-22 in `tests/conftest.py`): the suite reads
`ALEMBIC_DATABASE_URL`, swaps the database name to `ai-enablement-hub-test`, creates the schema per
session from `Base.metadata`, and forces `email=None, storage=None, llm=None` so no other
service is touched. No secrets are needed in CI. Side benefits: no PG firewall change for GitHub
runners, and the "two concurrent runs interfere" hazard disappears because each run has its own
server. The xdist worker count on a 4-core runner is 2 (conftest leaves two cores free); if the
suite is slow, set `-n 4` explicitly in CI.

Local runs keep using the Azure test DB via `backend/.env` — unchanged.

**Small backend housekeeping in the same PR:** add poe tasks `format-check` (`ruff format --check
.`) and `lint-src` (`ruff check src tests alembic`) so CI and humans run the same words; leave
`lint` (`ruff check .`) as-is for the staged job. `pytest-cov` is already installed.

### 3.2 Branch rulesets on `main`

Two rulesets, same names as the portal so the org pattern is recognisable. Definitions are kept
as JSON in `.github/rulesets/main-ci.json` and `.github/rulesets/main-review.json` and applied
with `gh api repos/{owner}/{repo}/rulesets -X POST --input <file>` — config as code, reviewable in
the PR, and the JSON documents the exact job names.

**`main-ci`** — enforcement `active`, target `~DEFAULT_BRANCH`, **`bypass_actors: []`** (nobody,
admins included):

- `pull_request`: `required_approving_review_count: 0`, `allowed_merge_methods: ["squash"]`,
  `dismiss_stale_reviews_on_push: false`, `require_code_owner_review: false`,
  `required_review_thread_resolution: false`.
- `required_status_checks`: `backend (format + lint + tests)`, `frontend (typecheck + lint +
  build)`; `strict_required_status_checks_policy: false` (no "branch must be up to date" —
  small team, avoids rebase churn; revisit if two PRs ever race).
- `deletion`, `non_fast_forward`.

**`main-review`** — enforcement `active`, target `~DEFAULT_BRANCH`, bypass: repository role
`admin` (`actor_id: 5`, `actor_type: RepositoryRole`, `bypass_mode: always`):

- `pull_request`: `required_approving_review_count: 1`, `dismiss_stale_reviews_on_push: true`,
  `allowed_merge_methods: ["squash"]`.

Written policy (in `CONTRIBUTING.md`, not enforceable by GitHub): admins use the review bypass
only for docs, hotfixes and trivially-green changes; anything touching auth, migrations,
prompts or learner-facing flows waits for the other admin. Pending decision §6.4 of the
comparison may tighten this.

**Repository settings** (one-time, `gh api -X PATCH repos/{owner}/{repo}`):
`allow_squash_merge: true`, `allow_merge_commit: false`, `allow_rebase_merge: false`,
`delete_branch_on_merge: true`, `squash_merge_commit_title: PR_TITLE`,
`squash_merge_commit_message: PR_BODY`.

### 3.3 Pull request template — `.github/pull_request_template.md`

```
## What & why

## Checklist
- [ ] Backend checks pass locally: `uv run poe format-check && uv run poe lint-src && uv run poe test` (in backend/)
- [ ] Frontend checks pass locally: `npm run typecheck && npm run lint && npm run build` (in frontend/)
- [ ] No secret committed (real values live only in git-ignored `.env` files)
- [ ] **Migration** (if any): additive / expand-first, fast on the live tables, idempotent — it runs unattended on container start
- [ ] **Learner-facing change** (if any): verified with production-shaped fixtures and a stubbed fetch, never by creating users/progress (CLAUDE.md "Verifying without touching live data")
- [ ] **Prompt change** (`backend/prompts/**`): treated as a production change; no DB override masks it
- [ ] `CLAUDE.md` / `docs/` updated where this changes how the app is run or operated
- [ ] Verified with evidence, not assumed

## Linked issue
Closes #
```

### 3.4 `CONTRIBUTING.md` (root, ~120 lines, for non-engineers)

Sections, adapted from the portal's file: the golden rule (never commit straight to `main`);
step by step with exact commands (`git switch main && git pull`, `git switch -c
<type>/<short-description>`, small commits, `git push -u origin HEAD`, `gh pr create --fill`, wait
for the two checks, review or admin bypass, `gh pr merge --squash --delete-branch`); branch types
`feat|fix|chore|docs|refactor|test|content`; Conventional Commit titles; "before you open a PR"
(the two check commands); the two rulesets explained in one paragraph each; the admin self-merge
policy; what to do when CI is red (read the job log, fix, push — never bypass); where the deeper
docs are (`CLAUDE.md` for agents, `docs/README.md` map, `db/README.md`). `README.md` gets one
line pointing at it. `CLAUDE.md` "Git" bullet is rewritten to point at `CONTRIBUTING.md` and to
say `main` is protected.

### 3.5 Claude Code configuration — committed `.claude/`

`.gitignore` changes: keep `.claude/settings.local.json` and any scheduled-task state ignored;
**un-ignore** `.claude/settings.json` and `.claude/hooks/**`.

`.claude/settings.json`:

- `hooks.SessionStart` → `python .claude/hooks/git_freshness.py` (30 s timeout): skips under
  `GITHUB_ACTIONS`; `git fetch --quiet`; emits `{"systemMessage": "[git] main is N commit(s)
  behind origin/main - run: git checkout main && git pull."}` and, on a feature branch, how far
  behind its upstream it is. Never blocks; exit 0 always.
- `hooks.PostToolUse` matcher `Edit|Write|MultiEdit` → `python .claude/hooks/prod_asset_nudge.py`:
  reads the hook JSON from stdin; if `tool_input.file_path` is under `frontend/src/`, prints a
  `systemMessage` reminding to verify learner-facing changes with production-shaped fixtures and a
  stubbed fetch (CLAUDE.md rule); under `backend/prompts/`, "this is a production asset baked into
  the image"; under `backend/alembic/versions/`, "runs unattended on container start — additive,
  fast, idempotent". Nudges only; exit 0 always. Ported from the accelerator's
  `ui-change-reminder.py`.
- `permissions.allow`: `Bash(uv run poe:*)`, `Bash(uv run pytest:*)`, `Bash(uv run ruff:*)`,
  `Bash(npm run:*)`, `Bash(gh pr view:*)`, `Bash(gh pr list:*)`, `Bash(gh pr checks:*)`,
  `Bash(gh issue view:*)`, `Bash(gh issue list:*)`, `Bash(gh run list:*)`, `Bash(gh run view:*)`.
- `permissions.ask`: `Bash(git push --force:*)`, `Bash(git push * main)`, `Bash(git push *:main)`,
  `Bash(*deploy.ps1*)`, `Bash(*az containerapp*)`, `Bash(*alembic upgrade*)`.

Hooks are Python (not bash) because the team is on Windows and `python` resolves on every
machine that runs `uv`. Each hook has a docstring stating "nudges, never blocks".

### 3.6 Interim `deploy.ps1` guard (retired by Tier 1.1)

Before queuing the ACR build: `git fetch origin --quiet`; abort if `git status --porcelain` is
non-empty ("working tree is dirty — commit or stash; deploy ships the directory as-is"); abort if
`git rev-parse HEAD` ≠ `git rev-parse origin/main` ("HEAD is not the pushed origin/main"); print
`Shipping <sha> (<subject>)`. A `-Force` switch is deliberately **not** added. The fresh-worktree
procedure in `CLAUDE.md` still applies; the guard just makes forgetting it fail loudly.

### 3.7 Documentation updates in the same PR

- `CLAUDE.md`: "Git" bullet → protected `main`, squash PRs, pointer to `CONTRIBUTING.md`;
  "Deploy procedure" mentions the guard; "How to run & verify" lists the two new poe tasks.
- `docs/README.md`: no change needed (specs folder already mapped).
- `README.md`: one line → `CONTRIBUTING.md`.

## 4. Rollout sequence

1. Branch `feature/tier0-delivery-guardrails` off `main`. Build everything in §3 except applying
   the rulesets and repo settings.
2. Push; open **PR #1** with `gh pr create`. The `ci.yml` in the PR runs on the PR itself — this is
   the proof. Iterate until both jobs are green; note the wall-clock time of the backend job.
3. Tell Aaron: after step 4 his next direct push to `main` is rejected; send him the
   `CONTRIBUTING.md` link.
4. **Ask Matthias, then** apply the repo settings and the two rulesets from the JSON files. Order:
   settings → `main-ci` → `main-review`.
5. Merge PR #1 by squash. It is the first protected merge.
6. Verify (§5). Record the outcome in the PR and in `docs/superpowers/lessons.md` once that file
   exists (Tier 1.7); until then, a line in `CLAUDE.md` "Current state".

## 5. Verification

- `ci.yml`: both required jobs green on PR #1 and on the resulting `main` push; the staged job
  runs and reports (red is fine); coverage artifact present.
- Rulesets: `gh api repos/{owner}/{repo}/rulesets` lists both as `active`; a deliberate
  `git push origin main` from a local branch is rejected with the ruleset message; a PR with a
  failing check shows "Merging is blocked" in the UI.
- Repo settings: `gh repo view --json mergeCommitAllowed,squashMergeAllowed,rebaseMergeAllowed,
  deleteBranchOnMerge` matches §3.2.
- Hooks: start a Claude Code session on a branch behind `origin/main` → the `[git]` message
  appears; edit a file under `frontend/src/` → the nudge appears; `git push --force` prompts.
- `deploy.ps1`: run with an uncommitted file → aborts before `az`; run on a commit not equal to
  `origin/main` → aborts; run clean on `origin/main` → prints the SHA and proceeds (do **not**
  complete a real deploy just to test — abort at the ACR step, or test the guard block in
  isolation with `-WhatIf`-style dry logic if simpler).
- `CONTRIBUTING.md`: Aaron follows it cold for one small docs PR without asking a question.

## 6. Risks and mitigations

| Risk | Mitigation |
|---|---|
| `postgres:18` image behaviour differs from Azure PG 18 in a way the suite notices | Same major version; suite already targets text[]/JSONB/ON CONFLICT. If a test diverges, that is a real finding, not a CI bug. |
| Backend job too slow on a 2-vCPU runner | Measured locally: 4 workers ≈ 210 s. Set `-n 4` explicitly; acceptable under 5 min. |
| `uv sync --all-extras` pulls `httptools`/`anthropic` (prod extra) — fine on Linux | Yes; `--frozen` guarantees the locked set. |
| Two admins, both can bypass the review rule | Written policy now; decision §6.4 may add a second approver later. CI has no bypass. |
| Hook scripts fail on a machine without `python` on PATH | Hooks exit 0 on any exception and Claude Code treats a missing interpreter as a hook error, not a block. Document `uv python install` as the fix. |
| Someone still runs `deploy.ps1` from a dirty tree | Guard aborts; the fresh-worktree procedure remains documented. |
| Ruleset JSON drifts from CI job names after a rename | Comment in `ci.yml` + the future docs-drift test (Tier 2.5) asserts equality. |

## 7. Open points (do not block Tier 0)

- Whether `main-review` should require the *other* admin (no bypass) — comparison decision §6.4.
- Coverage threshold value and whether `scripts/` debt is fixed or excluded — Tier 2.
- Aaron's local setup: he needs `gh` authenticated to the org for `gh pr create`.
