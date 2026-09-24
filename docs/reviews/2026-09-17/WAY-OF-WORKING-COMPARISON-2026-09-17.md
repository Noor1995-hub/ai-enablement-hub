# Way-of-working comparison — AI Enablement Hub vs the delaware house pattern

**Date:** 2026-09-17
**Scope:** how we build, review, test, deploy and collaborate — compared against two repos built by
a more experienced delaware team in the same GitHub org: `bta-agents-portal` (the closest
architectural match: FastAPI + React, one Azure Container App, same Azure resource group and even the
same PostgreSQL server as ours) and `sb-accelerator` (a Claude Code plugin monorepo with a mature
release pipeline). Code-architecture findings are **not** repeated here; they already live in
[`../2026-07-31/CODE-REVIEW-2026-07-31.md`](../2026-07-31/CODE-REVIEW-2026-07-31.md) with five
unexecuted fix plans.
**Audience:** the hub team (Matthias, Aaron, a possible third contributor) — none full-time
engineers. Terms are explained the first time they appear.
**Method:** read-only clones of both reference repos, two independent deep-read studies
(saved next to this file as `reference-bta-agents-portal.md` and `reference-sb-accelerator.md`,
spot-verified against the files), GitHub API queries for the org's actual protection rules and
workflow runs, and measured checks on our own repo (test run, coverage, lint, type-check, audit).
Every number below was measured today, not estimated.

---

## 0. Executive summary

**Our code is in better shape than our process.** Measured today: 1,527 backend tests pass with
96% line coverage, formatting is clean, the frontend type-checks, lints and builds. That is a
stronger test base than either reference repo has (the portal measures no coverage at all). What
we lack is everything that turns habits into mechanisms:

| Guardrail | Hub today | Portal | Accelerator |
|---|---|---|---|
| Pull requests | **0 ever** (359 commits, all direct to `main`) | 238 merged | 124 merged |
| Protected `main` (rulesets) | none | 2 rulesets, CI required, **no admin bypass** | 2 rulesets, squash-only |
| CI on every change | none (no `.github/`) | 4 required checks | 3 required + 3 staged |
| Deploy | laptop script ships the **working directory** | merge to `main` → CI builds by commit SHA → migrates → rolls → verifies | tag → verify by SHA → build → publish → read back |
| Dev vs prod database | **same database** | one prod DB, local Postgres for dev, throwaway DBs for tests | n/a |
| Automated code review | none | Claude review on every PR open | same, plus "review was delivered" assertion |
| Human-readable workflow doc | none (`CLAUDE.md` is the runbook) | `CONTRIBUTING.md`, 112 lines, "for people who are not full-time engineers" | same, 133 lines |
| Session hooks that catch stale branches | none | `SessionStart` git-freshness check | same + `PostToolUse` visual-check nudge |
| Lessons ledger | scattered "Gotchas" in `CLAUDE.md` | `docs/superpowers/lessons.md` | same, 22 entries |

The reference repos are not perfect (no Python lockfile, no linter, no coverage, no backups
documented on the portal — we are ahead on all four), but they have the one thing we lack: **a
pipeline that makes the wrong move impossible instead of merely discouraged.** That is exactly the
gap you described: "harder pipelines enforced by Claude and git so that we don't have to think
about it."

The org already treats the portal as its house pattern (the accelerator's bootstrap brief says
"Engineering conventions are modeled on `bta-agents-portal` — copy-adapt from there, don't
reinvent"). Adopting the same shape means the director's team can review and help us without
learning a second way of working.

**Recommended order (details in §5):**

1. **Week 1 — lock the door.** Branch rulesets, a CI workflow running the checks we already have,
   a PR template, `CONTRIBUTING.md`, squash merges, Claude Code hooks. Zero code risk; everything
   already passes.
2. **Weeks 2–3 — make deploys boring.** CI deploys on merge to `main` (build from the commit, not
   a laptop), migration safety, `BUILD_SHA` in `/api/health`, Claude PR review, a separate dev
   database, `SECURITY.md`, lessons ledger.
3. **Then — raise the floor.** Frontend tests, coverage gate, staged lint/type checks, dependency
   updates, docs-drift guard test, split `CLAUDE.md`.
4. **Only after 1–2 — execute the July fix programme** on top of the new guardrails, where every
   phase is a reviewed, CI-gated PR.

One more finding is about **where data lives** (F13): prompts must have git as their only source
of truth (retire the DB override), lesson content rightly stays in Postgres but needs a revision
history and a nightly export to git, and feedback stays in Postgres with a later promote-to-issue step.

Five decisions need you (§6). Nothing in this document has been changed in the repo yet.

---

## 1. What we measured about ourselves

| Fact | Value | Why it matters |
|---|---|---|
| Commits / authors | 359 / 2 (plus Claude as co-author) | Small team, but all history is direct-to-`main` |
| Pull requests | 0 | No review step, no CI hook point, no record of *why* a change was made beyond the commit |
| Merge commits | 15 | Feature branches were merged by hand into `main`; history is non-linear |
| Branch protection / rulesets | none | Anyone with write access can push or force-push to `main` |
| GitHub Actions | **enabled, all actions allowed** (verified via API) | CI is possible today; no IT ticket needed |
| Backend tests | 1,527 passed, **96% coverage**, 11 auto-reruns needed | Excellent base; the reruns are the shared remote test DB flaking under parallel load |
| Backend lint (ruff) | 30 findings, **all in `backend/scripts/`**; `src/` and `tests/` clean | A CI lint gate on `src/`+`tests/` would be green on day one |
| Backend format | clean (274 files) | Same |
| Type check (ty) | 25 diagnostics; 6 in `src/`, 3 in tests, rest in scripts + alembic env | Small; fixable in one PR, or stage as non-required |
| Frontend | typecheck ✔, lint ✔ (1 warning), build ✔ | Green on day one |
| Frontend tests | **0** (no vitest, no Playwright) | The July review's 4.4; portal has 51 vitest files |
| `npm audit` | 6 high, 3 moderate, all with fixes available | Build-tool CVEs mostly; `react-router` open-redirect is runtime |
| Anthropic SDK | pinned 0.119.0, current 1.6.0 | Unpinned-major risk noted in July (9.9), still open |
| Deploy record | 6 "docs: record deploy" commits editing `CLAUDE.md` by hand | "This file lags reality by design" — the portal stamps `BUILD_SHA` at deploy instead |
| Database | dev == prod (`ai-enablement-hub`), test DB shared by all local runs | The one-database rule is a documented hazard, not a solved one |
| Bundle | one 695 KB JS chunk | Vite warns; not urgent |
| Docs | 22 specs, 19 plans, `docs/README.md` map, 20 KB `CLAUDE.md` | Strong spec discipline; the runbook is agent-facing only |

Two things we do **better** than the references and must keep: nightly logical backups with
Sev-1 alerts and a restore runbook (the portal documents no backup at all), and a locked
dependency set (`uv.lock`, `npm ci`) with a real linter and formatter configured.

---

## 2. How the reference teams work — the parts that matter for us

### 2.1 The portal (`bta-agents-portal`) — our architectural twin

Same shape as the hub: FastAPI gateway + React/Vite frontend built into one image, one Azure
Container App in `imaginemore-playground`, PostgreSQL `bta_portal` on **the same server** as our
`ai-enablement-hub` database. 1,195 commits, 8 contributors, 3 months.

**Protected `main`, two rulesets** (verified via API, not just docs):

- `main-ci` — a pull request is required, four named CI checks must pass, **no bypass for anyone,
  admins included**, no force-push, no deletion.
- `main-review` — one approving review required, bypassable by repo admins. In their words:
  "you cannot merge a red build."

**CI (`.github/workflows/ci.yml`)** on every PR and every push to `main`: `backend (pytest)`,
`frontend (build + test)`, an agents job, and a version guard. The comment in the file is
telling: "Job names below are load-bearing: the `main-ci` ruleset requires the four test jobs as
status-check contexts, so renaming a job here without updating the ruleset blocks every merge."

**Deploy is a consequence of merging, never a laptop action.** On push to `main`, the same
workflow: logs into Azure with **OIDC workload identity** (no stored cloud secret; the identity
`bta-portal-cicd` lives in *our* resource group with a federated credential bound to
`repo:DLW-INT-BTA-BELUX/bta-agents-portal:ref:refs/heads/main`), builds the image tagged with
the **commit SHA**, runs the **database migration as a separate Container Apps Job and fails
closed** if it does not succeed within five minutes, then updates the app and **polls until the
live revision reports the expected image and `Running`**. It stamps `BUILD_SHA` and `BUILD_TIME`
as environment variables so the UI can show "updated N hours ago". Docs-only merges skip the
deploy. Rollback is re-pointing the image tag. Their ops doc adds: "A green pipeline is the
pipeline's own opinion. These three commands are the evidence."

**Claude reviews every PR.** `claude-code-review.yml` runs the official `code-review` plugin on
`opened / ready_for_review / reopened` (deliberately **not** on every push — they measured it:
median $1.63 per run, p90 $5.03) and on demand via a `/review` comment from collaborators only.
`CONTRIBUTING.md` explains when a re-review is worth paying for. A separate `claude.yml` answers
`@claude` mentions in issues and PRs.

**Claude Code is configured in the repo** (`.claude/settings.json`, committed): a `SessionStart`
hook that fetches and says "main is N commit(s) behind origin/main - run: git checkout main &&
git pull", a worktree bootstrap hook, an `allow` list for safe commands and an `ask` list for
`git push --force` and any push to `main`. Four repo-local skills automate routine operations
(daily issue pick, weekly release notes, contributor onboarding), each opening with "Hard rails
(read first)" and "Never execute without an explicit go".

**Docs for humans vs docs for agents are split.** `README.md` (92 lines) is the front door;
`CONTRIBUTING.md` (112 lines) is the workflow contract written for non-engineers;
`SECURITY.md` (81 lines) is a table of every secret, where it lives and the rotate-on-handover
rule; `CLAUDE.md` (541 lines, 40 KB) is the agent manual and is flagged by the team itself as
oversized, with a rule that references should be "one level deep". `docs/README.md` splits
"Read to contribute (current, maintained)" from "Historical / archive — do not treat as current
instructions".

**Tests enforce team rules.** `gateway/tests/test_docs_drift_guard.py` fails if a doc names a
stale count, a retired CI check, or a file path that no longer exists, and asserts the CI job
names in `ci.yml` still match the ruleset. `docs/superpowers/lessons.md` records every real
failure as "the failure it prevents / the check that catches it".

**Where the portal is weaker than us:** no Python lockfile, no ruff/mypy, non-strict TypeScript
with lint not in CI, no coverage measurement, no backups or alerting documented, only one
environment, and a documented squash policy that drifted to merge commits in practice.

### 2.2 The accelerator (`sb-accelerator`) — the release-engineering model

A Claude Code plugin shipped to client machines, so its problem is "never ship something broken
to a client". 132 commits on `main`, **124 of them squash merges**, zero merge commits.

What it adds beyond the portal:

- **Squash-only merges** enforced by the ruleset, so `main` is a linear list of one commit per
  PR, each ending in `(#N)`.
- **Staged CI checks:** new checks start as non-required jobs ("promote it in the ruleset once
  it has proven it does not false-positive"). A low-drama way to add gates.
- **Release by tag, verify by SHA, read back after publish:** the release workflow resolves the
  tag to a commit once, refuses tags not on `main`, builds from that SHA, publishes, then queries
  the destination through the API to confirm what landed. Idempotent re-runs are no-ops.
- **"Assert the review was delivered":** a step after the Claude review counts the bot's
  comments and turns the check red if none appeared, because "the API cost was spent regardless"
  and a silent non-review looks identical to "no findings".
- **`PostToolUse` hook** (`.claude/hooks/ui-change-reminder.py`): when Claude edits a file whose
  effect CI cannot see, it prints "has UI impact that CI cannot see. Verify with /visual-check
  before calling this done". It nudges, never blocks. Our equivalent is the "verify with
  production-shaped fixtures and a stubbed fetch" rule, which today lives only in prose.
- **Client-facing `CHANGELOG.md`** with a rule on what belongs: "something you would say out
  loud to the vault owner". Internal changes stay in git history.
- **Workflow security hygiene:** all inputs pass through `env:` rather than `${{ }}` inside
  scripts (script-injection), `permissions: {}` at the top with per-job grants, third-party
  actions pinned to a commit SHA.
- **A clean-room denylist** of real names the linter must never find in shipped content — the
  mirror image of our PII-in-git purge.

---

## 3. Side-by-side by dimension

Legend: ✅ strong · ⚠️ partial · ❌ missing.

| Dimension | Hub | Portal | Accelerator | What we should take |
|---|---|---|---|---|
| Branching & merging | ⚠️ feature branches, manual merges, 15 merge commits | ✅ typed branches, PRs, (drifted to merge commits) | ✅ typed branches, squash-only | Typed branches + **squash-only PRs** |
| Protection of `main` | ❌ | ✅ 2 rulesets | ✅ 2 rulesets | Copy both rulesets verbatim |
| CI gates | ❌ | ✅ tests + build | ✅ tests + validators + staged | Run our existing 6 checks in CI |
| Static analysis | ✅ ruff + ty configured, ESLint | ❌ | ❌ | Keep ours; put it in CI |
| Coverage | ⚠️ 96% measured today, not enforced | ❌ | ❌ | Enforce a floor (90%) |
| Backend tests | ✅ 1,527, real PG | ✅ 131 files, in-memory fake DB | ✅ 1,614 | Keep real PG; move CI runs to a throwaway Postgres |
| Frontend tests | ❌ | ✅ 51 vitest files | n/a | Add vitest; start with pure logic (`isUnlocked`, `predSatisfied`) |
| Deploy | ❌ laptop, working tree, hand-written log | ✅ CI on merge, SHA-tagged, verified | ✅ tag-based, SHA-verified | CI deploy on merge, OIDC, poll-until-healthy |
| Migrations | ⚠️ auto on container start, no rollback story | ✅ separate job, fail-closed, expand-first rule | ✅ snapshot-first, idempotent, lossy declared | Pre-deploy migration job + expand-first checklist item |
| Environments | ❌ dev == prod DB | ⚠️ one prod, local dev PG | n/a | Create `ai-enablement-hub-dev` |
| Secrets | ⚠️ Container App secrets, no inventory, 2 rotations owed | ✅ Key Vault + MI, `SECURITY.md` | ✅ `SECURITY.md` | Write `SECURITY.md`; do the owed rotations |
| Observability | ⚠️ backups + alerts ✅; app logging ⚠️ (fixed 2026-08-27); no error alerts | ⚠️ App Insights, no alerts | n/a | Later: 5xx alert, `BUILD_SHA` in health |
| AI code review | ❌ | ✅ | ✅ + delivery assertion | Adopt the accelerator's version |
| Claude Code config in repo | ❌ `.claude/` gitignored | ✅ committed settings + hooks + skills | ✅ | Commit `settings.json` with hooks; keep `settings.local.json` ignored |
| Human workflow doc | ❌ | ✅ `CONTRIBUTING.md` | ✅ | Write ours, 100–130 lines |
| Agent manual | ⚠️ 20 KB `CLAUDE.md`, mixes runbook + state log | ⚠️ 40 KB, self-flagged oversize | ✅ 109 lines + scoped `plugin/CLAUDE.md` | Split: short root + scoped `backend/`, `frontend/`, `docs/content/` |
| Lessons ledger | ⚠️ "Gotchas" bullets | ✅ | ✅ | `docs/superpowers/lessons.md` |
| Docs currency | ⚠️ "lags reality by design" | ✅ maintained/historical split + drift test | ✅ canonical-home rules | Two-table `docs/README.md`; guard test |
| Issues / backlog | ❌ none used | ✅ Projects board, auto-triage workflow | ✅ + issue templates | Light: issues + `Closes #N`; board optional |
| Versioning / changelog | ❌ | ⚠️ continuous, weekly release notes | ✅ semver + changelog | Not now; `BUILD_SHA` is enough |
| Dependency updates | ❌ | ❌ | ❌ | Dependabot (we'd be first) |
| Where data lives (git vs DB) | ⚠️ prompts in git **plus a DB override**; content in DB with no revision history; feedback in DB | ✅ agent definitions in git are "the source of truth, not the Console"; feedback in DB, promoted to issues | ✅ skills in git; client feedback to a per-client repo | Git is the only source for prompts; DB stays canonical for content, add history + export |

---

## 4. Findings in detail

### F1 — Nothing stands between a keyboard and production (Critical)

Any of the two current admins can push straight to `main` and run `deploy.ps1`, which uploads
**whatever is on disk**, committed or not. The July review recorded a real un-pushed deploy on
2026-07-22. Both references make this impossible: `main` accepts only PRs whose CI is green, and
the deploy is performed by CI from the merged commit's SHA. The hub's own docs prescribe a
"fresh worktree of the pushed commit" discipline — the references simply automate that
discipline.

### F2 — No CI, although everything needed for CI already exists and is green (High)

We have six well-defined checks (`poe format/lint/test`, `npm run typecheck/lint/build`). Nothing
runs them except memory. GitHub Actions is enabled on the repo. The only real obstacle is that
our integration tests need PostgreSQL: today they hit the shared Azure test DB, which (a) is not
reachable from GitHub's runners without opening the PG firewall and (b) flakes under parallel
load (11 reruns today). The clean fix is a **Postgres service container in the CI job**: the
suite already creates its schema per session from `Base.metadata` and derives its DSN from one
environment variable, so pointing it at `localhost` should be a config change. This also removes
the "two concurrent test runs interfere" hazard from the July review.

### F3 — Dev and prod share one database (High, already known)

Documented as THE ONE-DATABASE RULE, but a rule is a habit. The portal database sits on the same
server as ours, proving that a second database costs nothing. A `ai-enablement-hub-dev` database
restored from the **content and org-structure tables only** (never learner rows) plus a handful
of fictional users gives every local run and every Claude session a safe target. The
accelerator's rule "the fictional cast is load-bearing and stays fictional" applies verbatim.

### F4 — The deploy record is a hand-edited paragraph (Medium)

Six commits in history exist only to write "we deployed X on date Y" into `CLAUDE.md`, and the
file admits it lags. The portal writes `BUILD_SHA` and `BUILD_TIME` into the container at deploy
and reads them back in the UI. We should expose both in `/api/health` and stop editing the log
by hand.

### F5 — No human-facing workflow document (Medium)

A new contributor today must read a 20 KB agent runbook to learn how to ship a change. Both
references have a `CONTRIBUTING.md` whose first paragraph is: "This repo is built by a team that
includes people who are not full-time engineers. The rules below keep `main` always working…
They are simple on purpose." That is our team, described exactly.

### F6 — Claude Code is not configured at repo level (Medium)

`.claude/` is gitignored, so every session and every contributor starts from a blank
configuration. The references commit `.claude/settings.json` with hooks (stale-branch warning,
UI-verify nudge), an `allow` list for the project's own check commands, and an `ask` list for
force-push and push-to-main. That is the cheapest possible form of "enforced by Claude".

### F7 — No automated review (Medium)

With two or three people who are not full-time engineers, the reference teams treat the Claude PR
reviewer as the always-available second pair of eyes and ration it by cost. It requires an
`ANTHROPIC_API_KEY` GitHub secret — a spend decision (§6).

### F8 — Migrations apply at container start with no rehearsal (Medium, already known as 4.6)

The portal runs migrations in a **separate job before** rolling the app and fails the deploy if
the job fails, so a broken migration never takes the app down. Our `startup.py` runs
`alembic upgrade head` inside the app container; a failing migration bricks the new revision.
The PR-template checkbox "migration is backward-compatible (expand-first)" is the human half of
the same control.

### F9 — Frontend has no tests, and the backend has no coverage floor (Medium, already known)

Both are July findings (4.3, 4.4). The portal shows vitest with jsdom is a modest lift; our
unlock logic in `LearningPathNew.tsx` is the obvious first target because the July review calls
it the only place the module-prerequisite rule exists.

### F10 — Static-analysis debt is small and concentrated (Low)

All 30 ruff findings and 15 of 25 ty diagnostics are in `backend/scripts/content_qa/`. Six ty
items in `src/` are the only ones affecting the running app. Either fix them in one PR or exclude
`scripts/` from the CI gate and stage a "scripts lint" job as non-required, the accelerator way.

### F11 — Dependencies drift silently (Low)

Nine npm advisories with fixes available, Anthropic SDK a major behind, no Dependabot on any of
the three repos. Turning on Dependabot for `frontend/`, `backend/` and GitHub Actions would make
us the first in the org to have it.

### F12 — Documentation has no "current vs historical" contract (Low)

`docs/README.md` already carries a Status column, which is most of the way there. The portal
adds a test that fails when a maintained doc points at a file that no longer exists or names a
retired check. Our `CLAUDE.md` today names dead SHAs in several places, which is exactly the
kind of drift that test catches.

### F13 — Behaviour-defining artifacts vs user-produced data: one boundary is blurred (Medium)

Both reference repos follow one principle: **what defines behaviour lives in git** (code, prompts,
agent definitions, rubrics, evals — reviewed, versioned, deployed by CI), and **what people produce
by using the running system lives in the database** (feedback, progress, conversations). The
portal's `agents/README.md` opens: "This directory — not the Console … is the source of truth."
Its raw feedback sits in a Postgres `feedback` table, is triaged by an AI agent, and only
*promoted* items become GitHub issues. The hub already matches this split in most places; three
things differ:

- **Prompts have a DB override.** `backend/prompts/*.md` are in git and baked into the image, but
  `prompt_service.py` overlays a per-prompt DB row edited in the admin System Prompts page. An
  override has no history, no review and no deploy, and it silently masks whatever the next image
  ships — the exact situation with the pending `house_style.md` fix, which "a redeploy ships
  unless a DB override already covers it". The portal's rule is the right one for us: git is the
  only source of truth, edits are PRs, CI deploys them; the admin page becomes a read-only view of
  what is live (later: a UI edit that opens a PR through the GitHub API).
- **Lesson content is in Postgres, correctly, but has no revision history.** Content is relational
  (progress, assignments, feedback and media reference lesson ids), edited by non-developers in
  the rich editor, and written by the feedback-to-AI-diff pipeline. Moving it to files would mean
  rebuilding the editor and turning every content edit into a deploy — not recommended. What it
  lacks is what git would have given: `db/models/proposal.py` states it is "deliberately NOT a
  general content-versioning system". Two additions close the gap without moving anything: a
  content revision table (who changed what, revert), and a nightly export of the content tables
  to Markdown/JSON on a dedicated git branch (diffable, reviewable, restorable independently of
  the full dump — automating what the frozen `db/baseline/data` snapshot once did by hand).
- **Feedback stays in Postgres; the promotion step is missing.** Our learner-feedback → admin
  triage → AI-proposed content fix loop is stronger than the portal's thumbs-up table. Once GitHub
  issues are the backlog (2.7), bug/feature feedback should get a "create issue" action. The
  `feedback` model has no category field today, so that comes first.

Agents: the portal runs Claude Managed Agents for long, tool-using runs; our interviewer and
lesson helper are conversational and fit the in-process Messages API call. Not a reason to
change. The transferable practice is the per-agent bundle in git — prompt, model, parameters and
eval cases together (we have prompts and `tests/golden/`; each AI feature should own eval cases
the way the portal's agents own `evals/`).

---

## 5. Prioritised recommendations

> **Status (2026-09-24):** Tier 0 done (PRs #1–#2). Tier 1 done except 1.5, cancelled by decision
> (no dev database): 1.1–1.3 CI deploy (#4–#7), 1.6 `SECURITY.md` (#8), 1.7 lessons ledger (#9),
> 1.8 docs map (#10), 1.4 Claude PR review (#11–#15), 1.9 prompts git-only (#16, not yet deployed).
> Tier 2 in progress: 2.4 Dependabot config + `npm audit fix` (7 of 9 advisories; the remaining
> two are react-router 6.x, fixed only in 7.18+, a major bump tracked as its own PR — no route in
> the SPA navigates to a user-supplied URL, so the open redirect is not reachable today).
> 2.4 part 2: `anthropic~=1.8` in main deps (#19); bcrypt 5 with explicit 72-byte truncation (#38).
> 2.2: coverage floor 90% in CI (#20).
> 2.3: `ty check src` is clean and runs in the required backend job (ty pinned in the dev extra);
> the `staged` job keeps ruff on `scripts/` and ty on the whole backend.
> **Deferred frontend-tooling upgrade (decided 2026-09-24):** TypeScript 7, ESLint 10 (+ `@eslint/js` 10),
> `@vitejs/plugin-react` 6 and react-router 7 are one planned upgrade (spec → plan → PR), not
> Dependabot merges. Their PRs #27–#30 were closed with `@dependabot ignore this major version`;
> to resume, comment `@dependabot unignore <dependency>` on a Dependabot PR or remove the ignore
> under Insights → Dependency graph → Dependabot. react-router 7 also closes the last two npm advisories.
> Decisions taken since this report: admins self-merge with `--admin` after green CI + the Claude
> review, no @-mentions or review requests (2026-09-24, keeps `main-review` at 1 approval); manual deploy button (not on-merge);
> review scope = every non-docs PR, no `@claude`; prompts edited only by Matthias and Aaron.

Effort: **S** = under half a day, **M** = one to two days, **L** = three to five days. All
estimates assume Claude does the typing and a human reviews.

### Tier 0 — Lock the door (week 1, ~2 days total, no code-behaviour change)

| # | Action | Effort | Copies from |
|---|---|---|---|
| 0.1 | `.github/workflows/ci.yml` with two required jobs: `backend (format + lint + tests)` and `frontend (typecheck + lint + build)`; tests run against a **Postgres service container**; concurrency cancels superseded PR runs | M | portal `ci.yml` |
| 0.2 | Two rulesets on `main`, named `main-ci` and `main-review`: PR required, the two checks required, **no bypass**, no force-push, no deletion, **squash-only**; one approving review, admins may bypass | S | both (via API, we have the JSON) |
| 0.3 | `.github/pull_request_template.md`: what & why; checklist (checks pass, no secret, migration is expand-first, learner-visible change verified with production-shaped fixtures, `CLAUDE.md`/docs updated); `Closes #` | S | portal template |
| 0.4 | `CONTRIBUTING.md` for non-engineers: branch → commit → push → `gh pr create` → green → merge, exact commands, the two rulesets explained, when to ask for review | S | portal, near-verbatim |
| 0.5 | Commit `.claude/settings.json`: `SessionStart` git-freshness hook; `PostToolUse` nudge on `frontend/src/**`, `backend/prompts/**`, `backend/alembic/versions/**` ("verify with production-shaped fixtures / this is a production asset"); `allow` our six check commands; `ask` on `git push --force`, push to `main`, and `deploy.ps1` | S | both |
| 0.6 | `deploy.ps1` interim guard until Tier 1 replaces it: refuse on a dirty tree or when `HEAD` is not on `origin/main`; print the SHA it ships | S | July 4.1 |
| 0.7 | Squash-merge convention: Conventional Commit titles ending `(#N)`; delete branches on merge; `main` becomes linear from here | S | accelerator |

After Tier 0, a mistake requires deliberately bypassing a ruleset, and every change has a PR
with green checks and a written reason.

### Tier 1 — Make deploys boring (weeks 2–3, ~5 days)

| # | Action | Effort | Copies from |
|---|---|---|---|
| 1.1 | **CI deploy on merge to `main`**: OIDC login with a new user-assigned identity `ai-hub-cicd` (federated credential bound to our repo's `main`), `az acr build` or `docker build` tagged with the commit SHA, `az containerapp update`, poll until the live revision reports that image and `Running`, `workflow_dispatch` as the manual redeploy lever; docs-only merges skip; `deploy.ps1` retired to `infra/` as the break-glass path | L | portal `rollout` job |
| 1.2 | **Migrations as a pre-deploy step**: a Container Apps Job (`ai-enablement-hub-migrate`) running `alembic upgrade head` from the new image, polled fail-closed before the app is rolled; `startup.py` keeps `upgrade` as a no-op safety net or drops it | M | portal |
| 1.3 | `BUILD_SHA` + `BUILD_TIME` set at deploy, exposed in `/api/health` and the admin Setup page; stop hand-editing the deploy log in `CLAUDE.md` | S | portal |
| 1.4 | **Claude PR review workflow** with the accelerator's "assert the review was delivered" step and the portal's rationing rule in `CONTRIBUTING.md`; plus `claude.yml` for `@claude` mentions | M | both |
| 1.5 | **Dev database** `ai-enablement-hub-dev` on the same server: content/org tables restored from the nightly dump, fictional users, `backend/.env` defaults to it; prod DSN requires an explicit opt-in variable | M | new; accelerator's fictional-cast rule |
| 1.6 | `SECURITY.md`: table of every secret (Container App secrets, `db/.env`, `backend/.env`, GitHub secrets, the Anthropic key), where each lives, rotate-on-handover rule; schedule the two owed rotations (dev JWT secret, storage key) as issues | S | both |
| 1.7 | `docs/superpowers/lessons.md`: migrate the "Gotchas" bullets from `CLAUDE.md` into dated entries "the failure it prevents / the check that catches it" | S | both |
| 1.8 | `docs/README.md` two-table split (maintained vs historical); date-prefixed files are historical by convention | S | portal |
| 1.9 | **Prompts: git is the only source of truth.** Retire the DB override (migrate any live override back into `backend/prompts/*.md` via PR first, then drop the write path); System Prompts page becomes read-only with a link to the file; add a golden/eval case per AI feature under `tests/golden/` | M | portal `agents/` rule (F13) |

### Tier 2 — Raise the floor (following weeks, pick and choose)

| # | Action | Effort | Copies from |
|---|---|---|---|
| 2.1 | Vitest + Testing Library; first tests on `isUnlocked` / `predSatisfied` (extract to `lib/`), `getRectZoomFactor`, content-block renderer registration; add to the `frontend` CI job | M | portal |
| 2.2 | Coverage floor `--cov-fail-under=90` in the backend job (measured 96 today) | S | July 4.3 |
| 2.3 | Staged non-required jobs: `ty` on `src/`, ruff on `scripts/`; promote to required once clean | S | accelerator |
| 2.4 | Dependabot for npm, uv and GitHub Actions; fix the nine npm advisories; move `anthropic` to a bounded pin in main deps | S | new |
| 2.5 | Docs-drift guard test: every backticked repo path in `CLAUDE.md`, `README.md`, `CONTRIBUTING.md`, `docs/*.md` must exist; CI job names must match the ruleset | S | portal |
| 2.6 | Split `CLAUDE.md`: root ≤ 200 lines (what, how to run, the rules, pointers); scoped `backend/CLAUDE.md`, `frontend/CLAUDE.md`, `docs/content/CLAUDE.md`; move the state log to `docs/history/` | M | accelerator |
| 2.7 | Use GitHub Issues for the backlog with `Closes #N`; optional Projects board + `issue-backlog-defaults.yml` | S | portal |
| 2.8 | Workflow hygiene: `permissions: {}` at top with per-job grants, inputs via `env:`, third-party actions pinned to SHA | S | accelerator |
| 2.9 | Alert on 5xx rate / container restarts in Log Analytics (we already have the alert action group from the backup work) | M | new |
| 2.10 | Playwright smoke run against a preview (login, journey, one lesson) — only after 2.1 and a dev DB exist | L | new |
| 2.11 | **Content revision history**: `lesson_revisions` table written on every content save (who, when, previous `content_blocks`), admin "restore this version"; migration chained after the July phase-C head | M | F13 |
| 2.12 | **Nightly content export to git**: a scheduled job (extend the backup job image) dumps content/org-structure tables as Markdown/JSON and commits to a `content-snapshot` branch; a weekly PR shows the diff for review | M | F13; accelerator "every ops change is a PR" |
| 2.13 | **Feedback → GitHub issue promotion**: add a `category` to feedback (content / bug / feature), and an admin action that files an issue for bug/feature items (with 2.7) | S | portal `triage.py` |

### Deliberately not recommended now

- **Semantic versioning, tags and a changelog** — the hub is continuously deployed to one
  audience; `BUILD_SHA` gives traceability. Revisit if a learner-facing "What's new" is wanted.
- **In-memory fake DB for tests** (portal) — our real-Postgres suite is stronger; keep it.
- **Repo-local operational skills** (daily pick, weekly call) — valuable later, not before the
  pipeline exists.
- **Executing the July fix programme first** — do it *after* Tier 0–1 so each phase lands as a
  reviewed, CI-gated PR instead of a direct push.

---

## 6. Decisions needed from you

1. **Deploy on merge to `main`?** (Tier 1.1) It means every merged PR is live within ~10 minutes
   and the laptop script goes away. With three people and the ruleset in front of it, this is
   the safer option. The alternative is a manual `workflow_dispatch` deploy button in GitHub —
   still CI-built from a SHA, just not automatic.
2. **Azure identity for CI.** Creating `ai-hub-cicd` with a federated credential and role
   assignments (AcrPush on the registry, Contributor on the two container resources) needs
   **Owner or User Access Administrator on the resource group**. Confirm who holds that
   (Michael created `bta-portal-cicd`), or whether to ask him to run the one-time script.
3. **Claude review spend.** The GitHub secret `ANTHROPIC_API_KEY` for the review workflow: use the
   same key the portal uses (ask Michael), or a dedicated capped key. The portal measured a
   median of $1.63 per review.
4. **Review rule for a 2-admin team.** Copying the references exactly (1 approval, admins bypass)
   means you and Aaron could each merge alone. Recommended: keep the bypass so nobody is blocked
   at 22:00, but write in `CONTRIBUTING.md` that admin self-merge is for docs, hotfixes and
   trivially-green changes only; everything else waits for the other person or the Claude review.
5. **Dev database seeding.** Content tables only plus fictional users (recommended), or a full
   anonymised copy? The first is simpler and PII-safe by construction.

---

## 7. Suggested execution shape

Each tier becomes one design spec + plan under `docs/superpowers/` and lands as a series of small
PRs — the first PRs *are* the new workflow, so Tier 0.1 and 0.2 go in first and everything after
them is reviewed and CI-gated by construction. Tier 0 can be done in a single feature branch
opened as the repo's first pull request.

---

## Appendix A — Reference ruleset JSON (portal `main-ci`, as returned by the GitHub API)

```json
{"name":"main-ci","enforcement":"active","bypass_actors":null,
 "conditions":{"ref_name":{"include":["~DEFAULT_BRANCH"],"exclude":[]}},
 "rules":[
  {"type":"pull_request","parameters":{"required_approving_review_count":0,
    "dismiss_stale_reviews_on_push":false,"require_code_owner_review":false,
    "require_last_push_approval":false,"required_review_thread_resolution":false,
    "allowed_merge_methods":["merge","squash","rebase"]}},
  {"type":"required_status_checks","parameters":{"strict_required_status_checks_policy":false,
    "required_status_checks":[{"context":"backend (pytest)"},{"context":"frontend (build + test)"}]}},
  {"type":"deletion"},{"type":"non_fast_forward"}]}
```

(`main-review` is the same target with `required_approving_review_count: 1`,
`dismiss_stale_reviews_on_push: true`. The accelerator's variant sets
`allowed_merge_methods: ["squash"]` and grants the review bypass to the repository admin role.)

## Appendix B — Facts verified via GitHub / Azure APIs today

- `ai-enablement-hub`: Actions enabled, `allowed_actions: all`; 0 PRs; no protection; no rulesets;
  direct collaborators `danneelm_dlwr` (admin), `neuvillea_dlwr` (admin); 12 org members inherit
  read/admin.
- `bta-agents-portal`: 238 merged PRs; rulesets `main-ci` (4 required checks, no bypass) and
  `main-review` (1 approval); GitHub secrets `ANTHROPIC_API_KEY`, `DIST_REPO_TOKEN`,
  `PROJECTS_TOKEN`; CI green on `main` today.
- `sb-accelerator`: 124 merged PRs; rulesets squash-only + 3 required checks; same secret names.
- Resource group `imaginemore-playground`: one user-assigned identity `bta-portal-cicd` with a
  federated credential for `repo:DLW-INT-BTA-BELUX/bta-agents-portal:ref:refs/heads/main`.
- PostgreSQL server `imaginemore-playground-pg` (PG 18, B2s) hosts `bta_portal`,
  `ai-enablement-hub`, `ai-enablement-hub-test` and two unrelated databases.
