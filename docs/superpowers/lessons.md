# Lessons

Traps this repo has actually fallen into. Append an entry when one happens: the date, what went
wrong, why it bites here in particular, and the rule that prevents it. Oldest first. A trap that
recurs, or that every session needs to know, gets promoted into `CLAUDE.md` as a one-line rule
pointing back here.

---

## 2026-07-03 — the old az CLI ignored `dir/` patterns in `.dockerignore`

**What went wrong.** The first `az acr build` upload included `db/` (the baseline export, with
`invite_tokens.json`), `frontend/node_modules` and `backend/tests`: 36.6 MiB and 8,927 entries
where 6.3 MiB and 178 were intended. No `.env` went up — the `**/.env` patterns worked.

**Why it bites here.** The az CLI on the dev machine is old
(`C:\Program Files\Microsoft SDKs\Azure\CLI2\wbin\az.cmd`, not on PATH), and its build-context
packer skips trailing-slash directory patterns that Docker itself honours. The file looked
correct to anyone who knows Docker.

**The rule.** Every ignored directory is listed twice in `.dockerignore`, bare and with `/**`.
Verify any `.dockerignore` change by re-packing with az's own `_pack_source_code` and inspecting
the tar, not by reading the file. The `**/.env` exclusion is load-bearing — never loosen it. (The
CI deploy builds with `docker build` on a GitHub runner; this applies to `infra/deploy-legacy.ps1`
and anything else that runs `az acr build` from the laptop.)

## 2026-07-03 — the old az CLI reads and prints with the Windows codepage

**What went wrong.** During the first deploy, az's log streaming crashed on Vite's unicode build
output. The same codepage is what az uses to parse `infra/containerapp.yaml`, so one non-ASCII
character there would break the one-time create.

**Why it bites here.** az runs on Windows under cp1252, so both its input files and its console
output go through the system codepage instead of UTF-8.

**The rule.** Set `PYTHONIOENCODING=utf-8` before any az call that streams logs.
`infra/containerapp.yaml` (and any file az parses) stays pure ASCII — check with a byte scan
before committing.

## 2026-07-07 — `2>&1` on az under PowerShell 5.1 kills the script after the work is queued

**What went wrong.** `deploy.ps1` died partway through a deploy. az writes progress and warnings
to stderr; under PowerShell 5.1 with `$ErrorActionPreference = 'Stop'`, redirecting native stderr
(`2>&1`) turns each line into a terminating error even when az exits 0. Separately, the streamer
crashed in a non-interactive session despite `PYTHONIOENCODING`. The fix: queue the build with
`--no-wait`, poll `az acr task list-runs`, and never `2>&1` the az call.

**It happened again on 2026-08-04.** Piping the script through `Tee-Object` to keep a log
reintroduced the same failure from outside: the script died *after* `az acr build` had queued the
build, so the build carried on with nobody rolling the app.

**Why it bites here.** PowerShell 5.1 is the default shell on the dev machine and in Claude Code
sessions here, and `2>&1 | Tee-Object` is the reflex for "keep a log of this".

**The rule.** Never redirect or pipe native stderr under PowerShell 5.1 — not `2>&1`, not
`Tee-Object`. If a legacy deploy dies mid-way, don't assume nothing happened: check
`az acr task list-runs`, wait for the build, then `az containerapp update --image`.

## 2026-09-23 — a PowerShell probe named `$job` destroyed the `$JOB` constant

**What went wrong.** The first run of `infra/50-cicd.ps1` failed at the migration-job step with
`argument --name/-n: expected one argument`. The idempotency probe assigned
`$job = az containerapp job show …`, which returned `$null` because the job didn't exist yet.
PowerShell variable names are case-insensitive, so this also overwrote
`$JOB = 'ai-enablement-hub-migrate'`, and `create` ran with an empty name. Fixed in #5.

**Why it bites here.** Our scripts use UPPERCASE names for constants and lowercase for probes,
which is a safe convention in bash and a silent collision in PowerShell. Nothing warns you: the
parser accepts it and the variable is simply reassigned.

**The rule.** In PowerShell, never give a probe or loop variable the same name as a constant in
a different case. Name probes for what they hold (`$existingJob`). When a script depends on a
name constant, assert it is non-empty right before the call that uses it.

## 2026-09-23 — GitHub sent the immutable OIDC subject, and Azure rejected the plain one

**What went wrong.** The first Deploy run failed at `azure/login` with `AADSTS700213: No matching
federated identity record found`. The federated credential on `ai-hub-cicd` was bound to the
documented subject `repo:DLW-INT-BTA-BELUX/ai-enablement-hub:ref:refs/heads/main`, but GitHub
presented the immutable form, which embeds the numeric org and repo ids:
`repo:DLW-INT-BTA-BELUX@298414563/ai-enablement-hub@1329831650:ref:refs/heads/main`. Nothing was
built or migrated — the run stopped at the first Azure step. Fixed in #6.

**Why it bites here.** The subject format is chosen by GitHub, not by us, and it can change
without any change on our side. Reference setups and older docs (including `bta-portal-cicd`,
which the portal's deploy uses) show only the plain form.

**The rule.** An Azure identity trusted by GitHub Actions carries **both** subject forms as
separate federated credentials (`infra/50-cicd.ps1` creates `github-ai-hub-main` and
`github-ai-hub-main-immutable`), so a GitHub-side toggle in either direction can't break a deploy.
When `azure/login` fails with `AADSTS700213`, compare the subject the error presents with
`az identity federated-credential list` before changing anything else.

## 2026-09-23 — the `*deploy.ps1*` guard glob did not match `deploy-legacy.ps1`

**What went wrong.** When `deploy.ps1` moved to `infra/deploy-legacy.ps1`, the CI-deploy spec
(§3.5) said the existing `.claude/settings.json` ask pattern `*deploy.ps1*` "already covers the
new path". It doesn't: `deploy-legacy.ps1` does not contain the substring `deploy.ps1`. Left
alone, the break-glass script — which ships the working directory — would have run without the
confirmation prompt.

**Why it bites here.** The guardrails in `.claude/settings.json` are pattern matches, and a
pattern that reads as though it should cover a name is easy to accept without testing. Renaming
a guarded file silently removes its guard.

**The rule.** When a guarded file, command or path is renamed, add an explicit entry for the new
name and test it: check the literal string against the pattern, don't reason about it. The fix
added explicit entries for `deploy-legacy.ps1`, `migrate.py`, `containerapp job start` and
`gh workflow run`.

## 2026-09-23 — a committed hook with a relative path blocked every edit after a `cd`

**What went wrong.** `.claude/settings.json` ran its hooks as `python .claude/hooks/<hook>.py`.
Claude Code runs a hook command in the session's current directory, so once a shell call had
`cd`'ed into `backend/` (routine for `uv run …`), every Edit and Write reported
`PostToolUse:Write hook blocking error … can't open file '…\backend\.claude\hooks\prod_asset_nudge.py'`.
The edits themselves landed; the hook, meant to nudge and never block, turned every tool call
into an error.

**Why it bites here.** Half of this repo's commands run from `backend/` or `frontend/`, and the
unit tests for the hooks ran them with `cwd=REPO_ROOT`, so they could never see it.

**The rule.** Hook commands are anchored to the project dir and quoted, because the repo path
contains spaces: `python "$CLAUDE_PROJECT_DIR/.claude/hooks/<hook>.py"`.
`backend/tests/unit/test_claude_hooks.py::test_hook_commands_are_anchored_to_the_project_dir`
enforces it.

## 2026-09-23 — Git Bash turned `/review` into a Windows path

**What went wrong.** `gh pr comment 14 --body "/review"` from the Bash tool posted
`C:/Users/…/AppData/Local/…/review` instead. MSYS (Git Bash) converts any argument that looks
like an absolute POSIX path into a Windows path before handing it to a native `.exe`, and
`/review` looks like one. The Claude review workflow correctly ignored it — so it looked as
though `/review` did nothing — and the comment leaked a local path onto the PR.

**Why it bites here.** Claude Code on this machine drives `gh` through Git Bash, and this repo
now has a slash command (`/review`) that people and agents type as a `gh` argument.

**The rule.** Prefix `gh` calls whose arguments start with `/` with `MSYS_NO_PATHCONV=1`
(`MSYS_NO_PATHCONV=1 gh pr comment <n> --body "/review"`), or post the comment in the browser.
After posting, read the comment back before concluding the workflow ignored it.

## 2026-09-23 — `gh pr create --fill` on a multi-commit branch titled the PR after the branch

**What went wrong.** PR #13 had four commits; `--fill` took the title from the branch name, and
the squash merge put `feat/claude pr review (#13)` on `main` for good — protected `main` cannot
be rewritten. With one commit, `--fill` uses that commit's subject, which is why #1–#12 looked
fine.

**Why it bites here.** Squash-merge makes the PR title *the* commit message on `main`, and our
flow uses `--fill` by default.

**The rule.** For a branch with more than one commit, pass `--title "<type>(<area>): <summary>"`
to `gh pr create`, or fix the title with `gh pr edit --title` before merging.
