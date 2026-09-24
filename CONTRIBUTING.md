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
git fetch
git reset --hard origin/main
git switch -c <type>/<short-description>
```
Your local `main` is only ever a copy of `origin/main` — you never commit on it — so resetting
it is safe, and unlike `git pull` it also works after a squash merge (see step 7).
`<type>` is one of `feat`, `fix`, `chore`, `docs`, `refactor`, `test`, `content`.
Example: `git switch -c fix/people-detail-404`.

**2. Work in small commits.** Commit often; a change that is easy to read is easy to review and
easy to undo. Commit titles follow Conventional Commits: `<type>(<area>): <imperative summary>`,
e.g. `fix(admin): show a Maturity badge for the multiplier level`.

**3. Run the checks yourself before you push** (Claude does this for you when asked):
```powershell
cd .\backend;  uv run poe format-check; uv run poe lint-src; uv run poe ty-src; uv run poe test
cd ..\frontend; npm run typecheck; npm run lint; npm run build
```
The backend tests run against the shared Azure test database; a flaky run happens now and then —
rerun once before investigating. PowerShell 5.1 runs the commands on a line one after another
even if an earlier one fails, so read each command's result — a red `format-check` does not stop
`lint-src` from running.

**4. Push and open the pull request:**
```bash
git push -u origin HEAD
gh pr create --fill
```
Fill in the template: what & why, the checklist, and `Closes #<issue>` if there is one.
`--fill` takes the title from the commit when there is one; with several commits it falls back
to the branch name, which then becomes the commit message on `main`. Pass
`--title "<type>(<area>): <summary>"` in that case (or `gh pr edit --title` before merging).

**5. Wait for the checks.** The `CI` workflow (`.github/workflows/ci.yml`) posts two required
checks on the PR: `backend (format + lint + tests)` and `frontend (typecheck + lint + build)`.
A third check, `staged (scripts lint + ty) — not required`, counts the known lint/type debt in
`backend/scripts/` and the whole backend. It is green while the count stays at or below the
baseline in `ci.yml` and turns red only when your change **adds** findings. It does not block,
but a red one means "you made the debt worse": fix it. If you fixed some debt, lower the
baseline in the same PR. The backend check also fails if test coverage of `backend/src/` drops
below 90% — add tests with the code, don't lower the floor. If a required check is red: open the
job log, fix, push again. **Never work around a red check** — there is no bypass, and that is
the point.

**6. Review.** The gate is green CI plus the Claude review (see below) — read its findings and
fix what is real. Repo admins then merge their own PR (`--admin`, step 7); we do **not**
@-mention each other or request reviewers — with a team this size that is overhead, not safety.
Put the risk of a change (auth, migrations, prompts, an AI or learner-facing flow) in the PR
description instead. Non-admin contributors still need one approving review (the `main-review`
ruleset); an admin gives it.

**7. Merge — squash only:**
```bash
gh pr merge --squash --delete-branch
```
(or the green "Squash and merge" button). An admin merging their own PR adds `--admin`; without it GitHub refuses because `main-review` wants
an approval. The PR title becomes the one commit on `main`; the
branch is deleted automatically.

After the squash merge your branch is superseded — the auto-delete removes it on GitHub; delete
it locally with `git branch -D <branch>`, then bring `main` up to date the step 1 way
(`git switch main; git fetch; git reset --hard origin/main`).

## What GitHub enforces (the two rulesets)

Definitions live in `.github/rulesets/`; apply/verify instructions are in that folder's README.

- **`main-ci`** — a pull request is required; both `CI` checks must pass; squash merge only; no
  force-push; `main` cannot be deleted. **No bypass for anyone, admins included.**
- **`main-review`** — one approving review; repo admins may bypass (see the policy in step 6).

## Claude review

Every pull request that changes anything besides docs gets an automatic review by Claude
(`.github/workflows/claude-code-review.yml`) when it is opened, reopened or marked ready for
review. Findings arrive as inline comments on the lines concerned, or as one "No issues found"
comment. They are **advice, not a gate** — the review is not a required check. Docs-only PRs
are skipped; prompt changes under `backend/prompts/` are reviewed.

- **Re-review on demand:** comment `/review` on the PR. Each run costs real money (typically
  $2–5, occasionally $10+, on a key that is not spend-capped), so do it only after a
  **substantive** change — new logic, or a fix that changed behaviour — never after a typo or
  formatting push. A `/review` run is not in the PR's checks list: GitHub attaches
  comment-triggered runs to `main`'s latest commit. Its result is the new `claude[bot]`
  comment on the PR, or the run under **Actions → Claude Code Review**.
- **A red `claude-review` check** means the review posted nothing: the PR is **unreviewed**.
  Comment `/review` to retry. (One legitimate red: the reviewer judged the PR too trivial.) A
  red `claude-review` on `main`'s latest commit is a failed `/review` on some PR, not a broken
  `main`.
- **A PR that edits the review workflow itself** is not reviewed — GitHub-side guard, by
  design. The change takes effect on the next PR opened after merge.
- **Prompt changes** (`backend/prompts/`) are ordinary PRs: regenerate the golden snapshots with
  `UPDATE_GOLDEN=1 uv run pytest tests/golden/ai` from `backend/`
  (PowerShell: `$env:UPDATE_GOLDEN='1'; uv run pytest tests/golden/ai`), read the diff, commit it
  with the change. They go live with the next deploy.

## The backlog lives in GitHub Issues

Anything we mean to do later is an issue, not a line in a doc: bugs, planned work, owed chores.
Labels say which stream it belongs to: `way-of-working`, `fix-programme` (the July review's
phases), `ops`, `security`, plus GitHub's `bug`/`enhancement`. A PR that finishes an issue says
`Closes #N` in its description, so merging closes it. No assignees and no @-mentions (see step 6);
pick up whatever is open. The specs, plans and reviews under `docs/` stay the detailed source — the
issue links to them.

## Dependency updates (Dependabot)

`.github/dependabot.yml` opens update PRs every Monday: one grouped PR per area (frontend, backend,
workflows) for minor and patch releases, and one PR per major release. Releases younger than 7
days are held back. They run the normal CI but get no Claude review (Dependabot PRs have no access
to secrets). Merge a green grouped PR as usual; for a major, read the package's changelog first and
treat it like any behaviour change. Merging does not deploy anything.

## Deploying

Deploying is a button, not a script: GitHub → **Actions** → **Deploy** → **Run workflow** (on
`main`). It builds exactly what the last merged PR put on `main`, runs the database migration
first and stops if that fails, rolls the app, and checks `/api/health` reports the new build.
Takes about 4 minutes (under 2 for a rollback); watch the run's summary. Deploy only merged work — if something must go
live urgently, merge it first. To roll back, run Deploy again and paste a previous commit SHA
into `image_sha` (works from the second CI deploy onward — see CLAUDE.md for the one-off revert
before that). What is live right now: `/api/health` or the Deployment card on the admin
Setup page. The old laptop script is break-glass only (`infra/deploy-legacy.ps1`).

## Working with Claude Code in this repo

`.claude/settings.json` is committed. On session start it tells you if your `main` is behind
`origin/main`; when a file under `frontend/src/`, `backend/prompts/` or `backend/alembic/versions/`
is edited it reminds you what that file needs before it is done; and it asks before force-pushing,
pushing to `main`, running `infra/deploy-legacy.ps1`, starting the migrate job, running
`gh workflow run`, `az containerapp …` or `alembic upgrade`. Your personal
overrides go in the git-ignored `.claude/settings.local.json`.

## Where the deeper docs are

- `CLAUDE.md` — the operational guide for agents and operators (current state, conventions,
  locking semantics, deploy/ops).
- `SECURITY.md` — the secrets inventory and the no-secret-in-the-repo rule.
- `python-be-architecture.md` — mandatory backend conventions.
- `docs/README.md` — map of the docs tree; `db/README.md` — database roles and procedures.
- `docs/reviews/2026-09-17/` — why this workflow exists and what comes next.
