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
cd .\backend;  uv run poe format-check; uv run poe lint-src; uv run poe test
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

After the squash merge your branch is superseded — the auto-delete removes it on GitHub; delete
it locally with `git branch -D <branch>`. If you ever had commits on your local `main` that went
in through the PR, reset it with `git fetch && git branch -f main origin/main` rather than
`git pull` (the squash commit replaces them, so a pull would not fast-forward).

## What GitHub enforces (the two rulesets)

Definitions live in `.github/rulesets/`; apply/verify instructions are in that folder's README.

- **`main-ci`** — a pull request is required; both `CI` checks must pass; squash merge only; no
  force-push; `main` cannot be deleted. **No bypass for anyone, admins included.**
- **`main-review`** — one approving review; repo admins may bypass (see the policy in step 6).

## Deploying

Deploying is a button, not a script: GitHub → **Actions** → **Deploy** → **Run workflow** (on
`main`). It builds exactly what the last merged PR put on `main`, runs the database migration
first and stops if that fails, rolls the app, and checks `/api/health` reports the new build.
Takes about 6–8 minutes; watch the run's summary. Deploy only merged work — if something must go
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
