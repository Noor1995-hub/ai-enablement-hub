# Reference study — `bta-agents-portal` (delaware BTA Agents Portal)

Supporting material for [`WAY-OF-WORKING-COMPARISON-2026-09-17.md`](WAY-OF-WORKING-COMPARISON-2026-09-17.md).
Read-only study of `github.com/DLW-INT-BTA-BELUX/bta-agents-portal` at `main` on 2026-09-17
(1,195 commits, 2026-06-17 → 2026-09-17, 8 contributors). Produced by a deep-read subagent and
spot-verified against the files quoted (CONTRIBUTING, PR template, `.claude/settings.json`,
`ci.yml` rollout job, `claude-code-review.yml`, `lessons.md`, `test_docs_drift_guard.py`,
`infra/50-cicd.ps1`). Quotes are verbatim; judgements are ours.

**Vital stats:** Michael Bulthé authored 288 of 315 squash-suffixed commits and 162 of 168
`Merge pull request` commits; Xander Verplancke, Erik Willemse and Laura Debrock have merged
PRs. 0 git tags. Commit-type prefixes: `feat` 320, `fix` 276, `docs` 223, `chore` 62, `test` 54,
`refactor` 14, `ci` 11, `build` 5. 225 of the last 300 commits carry
`Co-Authored-By: Claude <noreply@anthropic.com>`.

---

## 1. Repo layout and module boundaries

A flat monorepo with one deployable container plus three "sidecar" trees deployed by other
mechanisms:

| Dir | Role | Deployed how |
|---|---|---|
| `gateway/` | FastAPI app (`gateway/app/`), tests (`gateway/tests/`, 131 files), `pyproject.toml` | Docker image → Container App |
| `frontend/` | React 18 + Vite + Tailwind + shadcn/ui; `src/{pages,components,hooks,lib,integrations/api,test}` | Built into the same image (`/app/static`) |
| `db/migrations/` | 103 ordered `NNNN_name.sql` + `migrate.py` runner + `test_migrate.py` | Copied into the image; run by a Container Apps Job |
| `agents/` | Managed Agent definitions, `config.json`, tooling | `deploy.py --ci` from CI, changed paths only |
| `plugin/` | Claude plugin (skills + MCP entry) | `scripts/release-plugin.sh` → distribution repo |
| `infra/` | Numbered PowerShell bootstrap scripts `00-prereqs.ps1` … `60-migrate-job.ps1` + `deploy.md` runbook | Run once by hand |
| `scripts/` | Dev helpers (portable Postgres, worktree setup, release, access matrix) | n/a |
| `docs/` | 153 files; index at `docs/README.md` | only `release-notes.md` ships |
| `.claude/` | `settings.json`, `launch.json`, 4 repo-local skills | n/a |

Inside `gateway/app/` the layering is flat-by-concern (`api/*.py` one router per resource,
one `db.py` data-access module, `backends/` protocol seam) rather than router/service/repository.
The one architectural rule enforced in prose is the provider seam: "All Anthropic-specific HTTP
lives behind this interface … Do not leak provider details past this seam." (`CLAUDE.md`).

**Judgement:** strong top-level boundaries with "source of truth" declared per directory;
internal layering pragmatic rather than principled.

## 2. Root documents

Lengths: `CLAUDE.md` 541 lines / 40 KB; `README.md` 92; `CONTRIBUTING.md` 112; `SECURITY.md`
81; scoped `agents/CLAUDE.md` (~70) and `plugin/CLAUDE.md` (~60).

- `README.md` — human front door: what it is, folder table, run/deploy in short, a "Where to go
  next" table, and "See `CONTRIBUTING.md` for the branch → pull request → review flow."
- `CONTRIBUTING.md` — the workflow contract. Opens: "This repo is built by a team that includes
  people who are not full-time engineers. The rules below keep `main` always working and every
  change validated by CI. They are simple on purpose." Golden rule: "`main` is **protected** —
  you cannot push to it directly. All changes go through: branch → commit → open a pull request
  → pass the four CI checks → (contributors: get 1 approval) → merge."
- `SECURITY.md` — secrets inventory table (name / purpose / where it lives), the two auth
  surfaces, the `DEV_AUTH` rule ("It must **never** be set in Azure"), rotate-on-handover rule.
- `CLAUDE.md` — the AI operating manual: stack, run/test, CI/CD summary, per-subsystem "rules if
  you touch this", SDD hard rules, the review-bot rules, commits, secrets. Cross-references:
  "Pitfalls this repo's agent sessions have already hit: `docs/superpowers/lessons.md`."

Workflow rules quoted from `CLAUDE.md`:
- "Conventional Commits (`feat:`, `fix:`, …). Small and frequent. **Every commit message MUST
  end with the trailer:** `Co-Authored-By: Claude <noreply@anthropic.com>`"
- "Pure logic … is built test-first … Setup/infra/deploy/frontend tasks instead end with an
  explicit manual verify step."
- "Use a **Sonnet-class or better** model for any subagent task that commits or touches git
  state"; "The controller **verifies HEAD is on the branch** … and **re-runs the test suite**".
- Anti-drift: "never count or list the agents in prose here or in the contributor docs;
  `gateway/tests/test_docs_drift_guard.py` fails on it, because two docs carried two different
  wrong counts by 2026-09."

Self-awareness about size (stripped HTML comment): "this section was 135 lines until 2026-08-20
— 27% of a CLAUDE.md that is itself 2.5x the 200-line size target … (1) content moved out of the
project-root CLAUDE.md is NOT re-injected after /compact … (2) references should be one level
deep."

**Judgement:** strong split (human docs short and routed; AI manual deep); root `CLAUDE.md` has
grown into a 40 KB institutional memory that the team itself flags as oversized.

## 3. Branching, PR and review conventions

- **Branches:** `git switch -c <type>/<short-description>` with `feat|fix|chore|docs|refactor|test`.
  Observed on merged PRs: `claude/*` 67 (Claude Code's auto-named branches), `fix/*` 28,
  `agent/*` 17 (daily-pick routine), `feat/*` 16, `docs/*` 13, `chore/*` 7, `release-notes/*` 4,
  `ci/*` 3.
- **PR template:** "What & why"; checklist — backend tests pass locally (exact command), frontend
  builds, no secret committed, **migrations expand-first**, agent-package impact, MCP impact,
  ids minted on this branch, evals, "**Verified with evidence, not assumed.**"; "Linked issue —
  Closes #"; an HTML comment explaining the review bot's behaviour.
- **Merge style:** documented as squash (`gh pr merge --squash --delete-branch`), but recent
  history shows merge commits — a documented-vs-actual drift.
- **Protection** (`CONTRIBUTING.md`, verified via API): "**`main-ci`** — requires a pull request
  and the four `CI` workflow checks to pass, with **no bypass** (applies to everyone, admins
  included — you cannot merge a red build). **`main-review`** — requires **1 approving review**,
  bypassed by repo admins/owners." Direct and force pushes to `main` blocked for everyone.

**Judgement:** strong, explicit, non-engineer-friendly rules; reliant on one person as reviewer.

## 4. CI/CD

Files: `.github/workflows/ci.yml` (477 lines), `claude-code-review.yml` (245), `claude.yml`
(50), `issue-backlog-defaults.yml` (41). `azure-pipelines.yml` is retired ("this pipeline is
DISABLED in Azure DevOps (2026-08-17) … Do not edit it to change CI behavior").

**`ci.yml`** — triggers `pull_request` and `push` on `main`, `workflow_dispatch`.
`permissions: contents: read, id-token: write`. Concurrency cancels superseded PR runs.

Required checks: `backend (pytest)` (`pip install "./gateway[dev]"` → `python -m pytest -q`);
`frontend (build + test)` (`npm ci` → `vitest run` → `vite build`); `agents (tooling + skill
tests + offline lint)`; `plugin version (not already released)` (PR-only). "Job names below are
load-bearing: the `main-ci` ruleset requires the four test jobs as status-check contexts, so
renaming a job here without updating the ruleset blocks every merge."

Gates absent: no Python lint (no ruff/mypy), no `npm run lint`/`tsc` job (TS is non-strict), no
coverage threshold, no dependency scan, no Dependabot.

**Deploy (`rollout` job, push to `main` or dispatch on `main` only):**
- `changes`: docs-only detection skips the deploy (exception: `docs/release-notes.md`, baked
  into the image).
- `azure/login@v2` via OIDC — client/tenant/subscription ids as plain env ("identifiers, not
  secrets"); federated credential subject bound to `refs/heads/main`.
- `docker build` tagged `:SHA` and `:latest`, pushed to ACR.
- **Migrate first, fail-closed:** `az containerapp job update … --image $IMAGE:$SHA --command
  python --args db/migrations/migrate.py`, `job start`, poll ≤ 5 min for `Succeeded`; any other
  terminal state fails the deploy.
- `az containerapp update --image … --set-env-vars ADMIN_OIDS ADMIN_EMAILS BUILD_SHA BUILD_TIME`
  ("BUILD_TIME is stamped here rather than baked into the image: it must mean 'when this
  revision went live'"), then poll ≤ 10 min until the latest revision's image equals the expected
  tag and state is `Running`/`Provisioned`.
- `deploy_agents` reads the Anthropic key from Key Vault at run time with `::add-mask::`;
  `release_plugin` publishes idempotently to a distribution repo.

No GitHub Environments, no manual approval; merge to `main` **is** the production deploy.
Rollback = re-point the image tag. Ops doc: "A green pipeline is the pipeline's own opinion.
These three commands are the evidence" (image tag == merge SHA; latest revision running;
migration job's latest execution `Succeeded`).

**Judgement:** very strong deploy pipeline for a small team; weak on static-analysis gates.

## 5. AI-agent integration

**`claude.yml`** — `anthropics/claude-code-action@v1` on `@claude` mentions in issues, PR
comments, reviews; read permissions + `id-token: write`; no custom prompt.

**`claude-code-review.yml`** — official `code-review@claude-code-plugins` plugin. Triggers
`pull_request: [opened, ready_for_review, reopened]` (deliberately **no `synchronize`**; measured
"median $1.63, range $0.55-$10.79, p90 $5.03, $184.10 total" over 78 runs) plus `issue_comment`
starting `/review` from `OWNER|MEMBER|COLLABORATOR`. Drafts excluded. `fetch-depth: 0`; for
comment-triggered runs checks out `refs/pull/N/head`. Installs deps but does not run suites.
Prompt: `/code-review:code-review <repo>/pull/<N> --comment` plus three headless-environment
constraints (run subagents in the foreground and never end the turn early; read PR-head copies of
`CLAUDE.md`/`.claude/` via `git show HEAD:<path>` because the action reverts them as a
prompt-injection guard; read CI outcomes via `gh api …/check-runs`). `track_progress: false`,
`display_report: true`, explicit `--allowedTools` allowlist including
`mcp__github_inline_comment__create_inline_comment`. Rationing rule in `CLAUDE.md`: "Don't
`/review` by default after every fix — ration it. Re-reviews are 24% of all spend."

**`.claude/settings.json`** (committed): enables the `superpowers` plugin; two `SessionStart`
hooks — (1) bash that fetches and emits a `systemMessage` "main is N commit(s) behind
origin/main - run: git checkout main && git pull", (2) `scripts/worktree-setup-hook.sh` that
bootstraps a missing venv/node_modules in a worktree; `permissions.allow` for pytest, npm, the pg
scripts, `gh pr/issue view|list`; `permissions.ask` for `git push --force:*`, `git push * main`,
`git push *:main`.

**`.claude/launch.json`** — named run configs. **`.worktreeinclude`** — gitignored files copied
into Claude-created worktrees (`.env`, `.blobstore/`, deploy env).

**`.claude/skills/`** — four operational routines with "Hard rails (read first)": `daily-pick`
("One issue per day: pick → card → 'go' → PR … **Never execute without an explicit 'go'** …
Never: merge, close issues, push to `main`."), `weekly-product-call` (drafts release notes PR;
"**Never touch `Priority`**"), `onboard-contributor`, `hive-add-user` ("Every write is echoed
and confirmed … per phase", starting from a read-only status script).

**Judgement:** exceptionally well-instrumented; the configuration surface is large and mostly
operated by one person.

## 6. Testing strategy

Backend: pytest + pytest-asyncio, 131 files. `conftest.py` monkeypatches `app.db` with an
in-memory `FakeDB` ("Ensure pure-logic tests never reach Azure/Postgres/Anthropic"); opt-in
integration tiers create a throwaway database per run when `BTA_TEST_DATABASE_URL` is set
(motivation: "That is exactly how a jsonb-decoding bug shipped"). **Guard tests as policy
enforcement:** `test_docs_drift_guard.py` (no hard-coded counts/rosters, CI job names match
`ci.yml`, retired-CI mentions, doc pointers resolve, with a vacuity check so "a glob typo would
[not] silently vacuum the guard"), `test_rename_guard.py`, `test_m365_scope_parity.py`,
`test_skills_sync.py`, `test_mcp_field_types.py`.

Frontend: vitest + jsdom + Testing Library, 51 `*.test.ts(x)` files colocated; no e2e.

No coverage tool or threshold anywhere.

**Judgement:** strong breadth and a novel "tests that enforce team rules" pattern; FakeDB can
drift from real SQL; no coverage.

## 7. Database

Plain SQL migrations `0001_init.sql` … (103 files, duplicate numeric prefixes tolerated because
"each is independently idempotent"), written idempotently. Runner tracks by filename in
`schema_migrations`, one transaction per file. No down migrations ("one-directional by design");
rule "Migrations must be expand-first", enforced via the PR checklist. One Azure PG server
`imaginemore-playground-pg`, database `bta_portal`; local dev uses a portable Postgres
(`scripts/pg-start.ps1` / `.sh`, "You do **not** need Docker on either platform"). **No backup
or DR documentation anywhere.**

## 8. Dependency and toolchain

Python: plain `pip` + venv, PEP 621 `pyproject.toml`, lower-bound-only pins, **no lockfile**.
Node: npm with committed lockfile, `npm ci`, Node 22. ESLint config exists but not in CI; TS
non-strict; no ruff/mypy; no pre-commit/husky. Dockerfile 3-stage, tag-pinned bases.
`actions/add-to-project` pinned to a commit SHA "for supply-chain safety".

## 9. Config, secrets, environments

`.env.example` (151 lines, heavily commented): "In Azure, these are injected from Key Vault via
the Container App managed identity." `pydantic-settings` config with each field commented with
issue number and Key Vault secret name. Local vs prod by env (`DEV_AUTH=1`, filesystem store,
console notifier). CI reads runtime secrets from Key Vault at deploy. GitHub secrets:
`ANTHROPIC_API_KEY`, `DIST_REPO_TOKEN`, `PROJECTS_TOKEN`. One environment (playground == prod).

## 10. Observability

`/healthz`; `_init_logging()` gives the `bta.*` logger INFO + stdout (docstring cites the bug where
INFO was dropped — the same class as our 2026-08-27 logging fix); Azure Monitor via
`configure_azure_monitor`; structured admin-mutation audit records; `BUILD_SHA`/`BUILD_TIME`
surfaced in the UI. No alert rules.

## 11. Docs organisation

`docs/README.md` is a two-table index: "Read to contribute (current, maintained)" vs "Historical /
archive (point-in-time records — do not treat as current instructions)", ending "if it's under
`superpowers/`, `archive/`, or dated in its filename, treat it as historical context." ~60
spec/plan pairs under `docs/superpowers/`. Living docs include `architecture.md`,
`azure-operations.md`, `local-setup.md`, `onboarding-new-builder.md` ("You're the director, not
the typist"), `claude-review.md`, `backlog.md`, `superpowers/lessons.md` (10 lessons, each "the
failure it prevents / the check that catches it"). Currency enforced by the drift-guard test.

## 12. Issues and backlog

No issue templates, no CODEOWNERS. `issue-backlog-defaults.yml` adds every new issue to the org
Projects board and assigns the `Unscheduled` milestone. Board fields `Priority`, `Area`,
`Effort`, `Value`, `Agent status`. Issues closed by `Closes #N` in PR bodies. Portal feedback
auto-files issues.

## 13. Release and versioning

No git tags, no CHANGELOG, no app version bumps. Continuous deployment; identity = `BUILD_SHA` +
`BUILD_TIME`. Weekly user-facing release notes drafted by a skill and published by merging the PR
("Name the thing the user sees, in their words … Never the mechanism").

## 14. Other notable practices

Portable dev Postgres scripts; idempotent worktree bootstrap with marker files; read-only-first
access matrix script; `permissions.ask` on force-push; deploy verification is evidence-based;
onboarding doc written for non-developers with a day-1 access table.

---

## Top practices worth copying for a 3-person team

1. Two-table `docs/README.md` (maintained vs historical).
2. `docs/superpowers/lessons.md` ledger.
3. Guard tests that enforce team rules.
4. Fail-closed migration job before rolling code; expand-first rule in the PR checklist.
5. OIDC workload identity for Azure deploys; runtime secrets read inside the job with masking.
6. Docs-only merges skip deploy, with an explicit exception list for runtime assets.
7. `BUILD_SHA`/`BUILD_TIME` set at deploy time and surfaced in the UI.
8. Branch protection as two rulesets: required checks with no bypass + 1-review bypassable by admins.
9. PR template checklist naming exact commands, ending "Verified with evidence, not assumed."
10. Claude review on open/ready/reopen + on-demand `/review`; measure cost; write the rationing rule down.
11. `SessionStart` hooks for git freshness and worktree bootstrap; `.worktreeinclude`.
12. Scoped `CLAUDE.md` files per subtree with a short root.
13. Issue-defaults workflow so triage is a move, not a form.
14. Release notes as a parsed in-app "What's new".
15. Read-only-first ops skills with confirmed writes.

**Gaps not to copy:** no Python lockfile, no ruff/mypy, non-strict TS with lint not in CI, no
coverage threshold, no backup/alerting documentation, squash policy drifted to merge commits,
single environment doubling as prod.
