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

## 2026-09-23 — the "regenerate API types" step needs a running backend, and the backend writes to live data

**What went wrong.** Nothing broke — it was caught while planning 1.9. `npm run gen:api` fetches
`http://localhost:8000/openapi.json`, so the documented way to regenerate `schema.d.ts` was to start
`uv run poe dev`. That server connects to the one shared database, and its lifespan starts a cleanup
loop that **deletes** expired auth sessions — a routine type regeneration would write to production.

**Why it bites here.** The one-database rule: there is no dev database, so "just start the backend"
is never a local-only action. The instruction sat in CLAUDE.md next to the rule it violated.

**The rule.** Generate the OpenAPI document by importing the app (`from src.main import app;
app.openapi()` — imports run no lifespan) and feed the file to `openapi-typescript`. CLAUDE.md
"How to run & verify" carries the exact commands. Never start `poe dev` to regenerate types. (2026-09-24: now built in — `npm run gen:api` imports the app via `backend/scripts/export_openapi.py`, and CI fails when `schema.d.ts` is stale.)

## 2026-09-23 — a test of a CI-only guard ran in CI and failed

**What went wrong.** The golden harness ignores `UPDATE_GOLDEN=1` whenever `CI` is set, so CI can
never regenerate a snapshot. Its own self-test set `UPDATE_GOLDEN=1` and expected a write, and
passed locally — but GitHub runners set `CI=true` for every step, so on the PR it would have been a
red required check. The final branch review caught it by running `CI=true uv run pytest tests/golden`.

**Why it bites here.** Local runs never have `CI` set; anything that branches on it is untested
locally by default.

**The rule.** A test that exercises environment-dependent behaviour sets or clears every variable it
depends on (`monkeypatch.delenv("CI", raising=False)`), and a change touching such code is also run
once with `CI=true` before the PR.

## 2026-09-24 — a green Dependabot major (bcrypt 5) would have locked users out

**What went wrong.** Nothing shipped — caught while triaging Dependabot's first batch. PR #35
(bcrypt 4.3 → 5.0) had both CI checks green. bcrypt 5 raises `ValueError` for passwords over 72
bytes where 4.x truncated silently; `verify_password` swallows `ValueError` as "wrong password".
`SetPasswordRequest` caps at 72 *characters*, so any user whose password is over 72 UTF-8 bytes
(long, non-ASCII) would have been refused at login with the correct password, and setting such a
password would have 500'd. No test used a password over 72 bytes, so CI could not see it.

**Why it bites here.** Dependabot opens majors as ordinary PRs, CI turns them green, and the
admin self-merge flow makes merging one a single command. A green check on a major proves the
suite still passes, not that the library behaves the same on inputs the suite never uses.

**The rule.** Before merging a Dependabot **major**, read the changelog's breaking-changes
section and grep our call sites for each item; if one applies, fix it in our own PR with a test
that fails on the new version (this one: `tests/unit/test_security.py`, the 72-byte cases).

## 2026-09-24 — az.cmd let cmd.exe eat a JMESPath filter, and the idempotency probe went blind

**What went wrong.** The first run of `infra/60-app-alerts.ps1` printed
`-o was unexpected at this time.` before each rule. The probe
`--query "length([?name=='ai-hub-app-5xx'])" -o tsv` never reached az: `az.cmd` is a batch file,
so PowerShell hands its arguments to `cmd.exe`, which parsed the `==`/quotes itself and choked.
The probe returned nothing, so the script treated every rule as missing. The creates were
correct only because the rules really were missing; a re-run would have re-created them instead
of leaving them alone.

**Why it bites here.** The az CLI on this machine is the old `az.cmd` (off PATH), invoked from
PowerShell 5.1. The same filter works in the portal's shell, on Linux and in GitHub Actions, and
simple `--query` paths (`id`, `[].name`) work here too — only filters with `==`, `'` or `|` break.

**The rule.** From PowerShell on this machine, keep `--query` to plain paths and filter the
result in PowerShell (`@(& $AZ ... --query '[].name' -o tsv) -contains $name`). Treat any
`was unexpected at this time` line as a failed command even when the script carries on, and
read back what a mutating script created before trusting it.

## 2026-09-25 — the per-IP rate limits keyed on an IP the client chose

**What went wrong.** Found by the phase B pre-flight, never exploited as far as we know.
`startup.py` runs uvicorn with `proxy_headers=True, forwarded_allow_ips="*"`, so
`request.client.host` is the **leftmost** `X-Forwarded-For` entry, which the client writes. A
probe on prod (`curl -H "X-Forwarded-For: 203.0.113.77" …/api/health`) was logged as coming from
`203.0.113.77`. Every per-IP limit (set-password, Entra callback) could be bypassed by rotating
the header, and anyone could have forged an office's IP to lock that whole office out.

**Why it bites here.** The Container Apps Envoy ingress *appends* the real peer on the right; the
leftmost hop only looks trustworthy because a normal browser sends no header of its own.

**The rule.** Per-IP keys use `src/core/client_ip.py::client_ip` (rightmost hop across all header
lines), never `request.client.host` (`backend/CLAUDE.md` convention 8). If a proxy is ever put in
front of the app (Front Door, App Gateway, the hosting move), re-verify with a forged header: one
extra trusted hop makes every learner share one key (#79).

## 2026-09-28 — a colleague's merge and a squashed base PR turned ready PRs into conflicts

**What went wrong.** Phase B's #76 and #77 were green and mergeable, with #77 stacked on #76.
Aaron then merged #81 and #91, which touched the same interviewer files, and #76 conflicted. After
#76 was squash-merged, #77 conflicted too: a squash commit is a *new* commit, so git no longer
recognised #76's changes inside #77.

**Why it bites here.** Two people are shipping into `interview_service.py`, `chat_service.py`,
`llm_service.py` and `tests/fixtures/llm.py` at once, and squash-merge rewrites the base of any
stacked PR.

**The rule.** Fetch before every merge handoff and re-check `mergeable` on each PR in the queue.
After a stacked base is squashed, merge `main` into the dependent branch; first confirm
`git diff <old base tip> origin/main` is empty, and then resolve every conflict to the branch's
own side (it already contains the base). When a colleague's merged work overlaps, reconcile to
their design and keep only your delta (#76 kept its opener timeout and 502 on top of #81).

## 2026-09-30 — `git stash` is shared by every worktree

**What went wrong.** Two sessions worked in separate worktrees of this repo. One popped or dropped
the other's stash, and an agent's RED/GREEN proof silently lost its `src/` edits.

**Why it bites here.** A stash lives in the repository, not the worktree, so parallel sessions
(fix-programme phases, Aaron's branches) see and can consume each other's entries.

**The rule.** Never use `git stash` while another worktree is active. To prove RED, copy the file
aside, `git checkout -- <file>`, run the test, then copy it back.

## 2026-09-30 — off-VPN, every integration test times out

**What went wrong.** On a phone hotspot (or any network off the VPN) the whole integration suite
failed with `WinError 121` connect timeouts, even though it only targets the test database. It
looked like a mass test failure.

**Why it bites here.** The laptop's egress IP is not on the Azure PG firewall allowlist, so nothing
reaches port 5432, whichever database is named.

**The rule.** Check with `Test-NetConnection <pg host> -Port 5432` before debugging tests. If it
fails, fall back to CI (it has its own postgres). Never add a firewall rule without asking.
