# Reference study — `sb-accelerator` (Second Brain Accelerator)

Supporting material for [`WAY-OF-WORKING-COMPARISON-2026-09-17.md`](WAY-OF-WORKING-COMPARISON-2026-09-17.md).
Read-only study of `github.com/DLW-INT-BTA-BELUX/sb-accelerator` at `main` on 2026-09-17
(132 commits, 2026-08-22 → 2026-09-17, 311 files). Produced by a deep-read subagent and
spot-verified against the files quoted (`.claude/hooks/ui-change-reminder.py`, rulesets via the
GitHub API). Quotes are verbatim; judgements are ours.

**Vital stats:** 132 commits on `main`, **124 of them squash merges with a `(#N)` suffix, 0
merge commits**, 8 direct pushes (all on bootstrap day, before protection was on). Authors on
`main`: Michael Bulthé 127, Xander Verplancke 5. 11 annotated tags `plugin-v0.10.27 … v0.11.3`.
96 remote branches: 54 `claude/*`, 17 `chore/*`, 9 `fix/*`, 6 `feat/*`, 3 `docs/*`. The
bootstrap brief states: "Engineering conventions are modeled on `bta-agents-portal` … copy-adapt
from there, don't reinvent."

---

## 1. Repo layout

One product monorepo with a hard "ships / never ships" boundary drawn at directory level:
`plugin/` (the Claude Code plugin: skills, agents, a stdlib-only Python CLI, migrations, vault
template — ships byte-identical), `fixtures/demo-vault/` (fictional persona content for tests),
`scripts/` + `scripts/tests/` (CI validators, release tooling, 54 test files), `playbooks/`
(delivery runbooks, never ship), `docs/`, `registry.yaml` (one row per deployed vault),
`.claude/` and `.claude-plugin/` (dev-side config; the repo is itself installable).

Layering rule from `README.md`: "L0 ontology → ships / L1 automation → ships, de-personalized /
L2 delaware company knowledge → **never ships** / L3 personal context → never in this repo."
Skills never write files directly: "Every write goes through the deterministic CLI … Each run
prints exactly one JSON object and signals through its exit code" (`plugin/CLAUDE.md`).

**Judgement:** strong — "can this leak to a client?" is answered by path alone and enforced by a
linter.

## 2. Root documents

Five short, non-overlapping docs:
- `CLAUDE.md` (109 lines) — agent conventions; opens with "Pitfalls prior agent sessions hit:
  `docs/superpowers/lessons.md`"; delegates the PR flow: "Full flow: `CONTRIBUTING.md`".
- `README.md` (39 lines) — two sentences, directory table, layer model, pointer to CONTRIBUTING.
- `CONTRIBUTING.md` (133 lines) — "This repo is built by a team that includes people who are not
  full-time engineers. The rules below keep `main` always working and every change validated by
  CI. They are simple on purpose."
- `SECURITY.md` (31 lines) — table of every secret, where it lives, rotation rule; "no secret
  value ever appears in this repo — not in a file, an issue, a PR description, or a workflow log."
- `CHANGELOG.md` (38 KB) — **client-facing release notes only**.
- `plugin/CLAUDE.md` (311 lines) — a deeper agent file scoped to plugin internals.

Rules quoted from `CLAUDE.md`: "`main` is protected: branch → PR → three green checks → squash
merge." / "Any PR touching `plugin/` … must bump the version … CI's version guard enforces it." /
"`CHANGELOG.md` is client-facing release notes, not a work log: a PR gets a line under
`Unreleased` … only if a client would notice … Internal changes stay out; git history is that
record." / "Merging to `main` publishes nothing. A tag push publishes to the **dryrun** channel
only (hardcoded — a tag can never reach clients)."

**Judgement:** very strong — each file has one audience and one job.

## 3. Branching, PR and review

- Branches `<type>/<short-description>`; mechanical sub-families: `chore/release-<version>`
  (one commit turning `## Unreleased` into a dated section), `chore/registry-<deployment>-<v>`
  (a one-line `registry.yaml` bump after a real upgrade — every deployment change is a reviewed
  PR), `claude/*` (auto-named branches from Claude Code cloud sessions, merged by squash).
- Conventional Commits; squash bodies carry `Co-Authored-By: Claude …` trailers (441 lines).
  "Claude" appears as git author only on side branches (a cloud session committing under its own
  identity); squash-merge rewrites the author to the PR opener.
- PR template: "What & why", seven-box checklist (three local checks, no secret/client name,
  changelog-if-client-would-notice, version bump, "any new migration … is idempotent (safe to run
  twice)"), `Closes #`, an HTML comment on the review bot.
- Rulesets (verified via API): `main-ci` — PR required, three named checks, **no bypass actors**,
  **`allowed_merge_methods: ["squash"]`**, no deletion, no force-push. `main-review` — one
  approving review, bypass granted to the repository admin role.
- `gh pr merge --squash --delete-branch`; automated Claude review on open; humans review
  non-admin PRs.

**Judgement:** strong and unusually disciplined — linear history; every client-visible state
change is itself a PR.

## 4. CI/CD

**`ci.yml`** (126 lines): `pull_request`/`push` on `main` + `workflow_dispatch`;
`permissions: contents: read`; concurrency cancels superseded PR runs ("main runs never cancel").
Three **required** jobs (`plugin (skill lint + tests)`, `template (structure validation)`,
`plugin version (not already released)` — PR-only, diffing `HEAD~1..HEAD`) and three **staged,
not-yet-required** jobs (`changelog (new entry cites this PR)`, `runtime floor (python 3.10)`,
`cross-platform (windows)`) with the comment "promote it in the ruleset once it has proven it does
not false-positive."

**`release.yml`** (407 lines, ~40% comments): trigger `push: tags: ['plugin-v*']` (always
`channel=dryrun`) or `workflow_dispatch` with `tag` + `channel`. `permissions: {}` at top, granted
per job. Jobs: `resolve` (regex-validates the tag; all inputs pass via `env:` "rather than
interpolated directly into the script text with `${{ }}` … (classic Actions script-injection)"),
`verify` (checks out the tag, asserts `plugin.json` version == tag, "refuse a tag that is not on
main" via `git merge-base --is-ancestor`, re-runs validators), `build` (checks out **by the SHA
verify pinned** — "a tag can move"; deterministic build, zip + sha256), `publish` (sanity-checks
the artifact, wipes the dist repo except `.git`, copies, commits as a release bot with an
idempotency gate, pushes, then **"API read-back verification (never trust the local clone)"**),
`github_release`. `docs/distribution-channels.md`: "A tag push **cannot** reach the client
channel, however the tag is spelled. That is the safety property the whole arrangement rests on."

**`claude.yml`** — stock `@claude` assistant. **`issue-backlog-defaults.yml`** — adds new issues
to the org board (`actions/add-to-project@<sha> # v2.0.0`, "pinned to commit for supply-chain
safety") and assigns the `Unscheduled` milestone.

**Judgement:** exceptionally strong; verify-by-SHA, idempotency, read-back and injection hygiene,
every non-obvious line explained inline.

## 5. AI-agent integration

**`.claude/settings.json`** (65 lines): enables `superpowers`; `SessionStart` hook (skips under
`GITHUB_ACTIONS`, `git fetch`, emits "main is N commit(s) behind origin/main - run: git checkout
main && git pull"); `PostToolUse` hook on `Edit|Write|MultiEdit` → `ui-change-reminder.py`;
`allow` for the validators, pytest, `gh pr/issue view|list`; `ask` on `git push --force:*`,
`git push * main`, `git push *:main`.

**`.claude/hooks/ui-change-reminder.py`** (45 lines, verified): reads the hook JSON from stdin,
matches `tool_input.file_path` against a tuple of UI-affecting paths and suffixes, prints
`{"systemMessage": "[visual] <file> has UI impact that CI cannot see. Verify with /visual-check …
before calling this done"}`. Docstring: "Emits a systemMessage and always exits 0: this nudges,
it never blocks." and "a convention that depends on remembering is one that gets missed".

**`.claude/commands/visual-check.md`** — the local visual-verification loop as a slash command,
ending "**Read the screenshots** … This is the step that cannot be automated away."
**`.claude/commands/process-upstream.md`** — ports a lab pattern into the product clean-room:
"Present that diff and let the human decide … Do not choose silently."

**`claude-code-review.yml`** (400 lines): triggers `opened, ready_for_review, reopened` ("per-push
review does not fail on price-per-run, it fails on volume") + `/review` from
`OWNER|MEMBER|COLLABORATOR` ("a drive-by commenter should not be able to spend API budget").
`pull-requests: write` ("With read-only the whole run is wasted — it reviews, then silently cannot
deliver"). Uses `code-review@claude-code-plugins` with the same three headless constraints as the
portal. `--model claude-sonnet-5` pinned with measured rationale: "Measured over the 85 billed
runs from 2026-08-22 to 2026-09-03 … $371.00 total, mean $4.36, median $3.49, max $11.88."
**"assert the review was delivered" step:** counts `claude[bot]` comments created after a
timestamp taken before the action; red-Xes with "## Review produced no output … This PR is
currently **unreviewed**, and the API cost was spent regardless." Not a required check, "so a red
X here is a visible signal and not a merge block."

**Judgement:** best-in-class — the reviewer is a paid, fallible colleague: cost measured,
non-delivery asserted, harness lessons encoded in the prompt.

## 6. Testing

Plain pytest, one flat `scripts/tests/` with 54 files / 1,614 test functions, identical locally
and in CI. The CI validators are themselves unit-tested. Contract tests pin SKILL.md ↔ CLI
(`test_skill_contracts.py`). `fixtures/demo-vault/` is a complete fictional vault: "**The
fictional cast is load-bearing and stays fictional.** … never replace its cast with a real
engagement's people or organizations." CI matrix: Ubuntu 3.13 (required), Ubuntu 3.10 floor,
Windows 3.13 (caught a real CRLF hash bug). A local-only visual tier drives a real Obsidian.

## 7. Migrations (of client vault structure, not a DB)

`plugin/migrations/NNN-slug/migrate.py`, each with `TARGET_VERSION` (consecutive; "A gap is
refused rather than silently skipped"), `LOSSY: str | None` (shown before confirming), `apply`,
`verify`. Framework: snapshot the whole vault first (keep 3), apply → verify → bump version, one
log line per attempt, stop on first failure. "Every migration must be safe to run twice." Applied
"on a consultant's own machine — never unattended".

**Judgement:** a model for any "upgrade someone else's data" path: snapshot-first,
verify-per-step, lossy-declared, idempotent, human-confirmed.

## 8. Toolchain

Deliberately minimal: no `pyproject.toml`, no lockfile, no ruff (runtime is stdlib-only at a
Python 3.10 floor). Vendored third-party bytes with sha256 pins, `.gitattributes` `-text` so
CRLF checkouts cannot break pins. `.gitignore` names *why* each entry exists. Adequate for a
stdlib tooling repo; would be too thin for an app.

## 9. Docs

Flat and small `docs/` plus `docs/superpowers/` with 13 specs, 21 plans (every plan opens with
the same "For agentic workers" header and a Global Constraints block) and **`lessons.md`** (900
lines, 22 dated entries: *What went wrong / Why it bites here / The rule*; "Patterns that recur
get promoted into `CLAUDE.md`"; entries correct earlier entries — "all three were deductions
presented as findings"). Canonical-home statements everywhere: "`.github/workflows/release.yml`
— the authority for everything on this page."

## 10. Issues and backlog

Four axes: `type:` labels, `area:` labels, milestones (`Wave 1 … Wave 4`, `Unscheduled`), board
fields. Two inflow issue templates: `upstream-proposal.md` (a lab pattern proven product-worthy,
with the exact source SHA so drift is detectable) and `field-proposal.md` (consultant/client
feedback worth productizing, with deployment context). Client feedback never lands here
directly — each deployment has its own scrubbed feedback repo.

## 11. Release and versioning

SemVer in `plugin.json`, bumped **in the same PR** as any `plugin/` change (CI-enforced). A
release is a separate act: `chore/release-<v>` PR dates the changelog → `scripts/cut_release.sh`
(refuses unless clean, on `main`, equal to `origin/main`, tag absent, changelog section present)
→ annotated tag → dryrun channel + GitHub Release → manual promotion to the client channel.
`registry.yaml` is "hand-stamped at tune-ups and lags reality, so do not read it as live state."

## 12. Other notable practices

- Comments carry measurements, not opinions (dollar figures, PR numbers, run counts).
- "Silent success is the enemy": delivery assertion, artifact sanity checks, skip-vs-pass
  distinctions ("A green run showing `8 skipped` is not evidence; only `8 passed` is").
- Staging new CI checks as non-required, then promoting.
- A clean-room denylist of real names the linter must never find in shipped content.
- Subagent hygiene: "Do not run `git checkout`, `git switch`, `git reset`, `git stash`, or
  `git rebase` in this worktree. Another session commits here concurrently"; "after every
  subagent returns, run `git symbolic-ref -q HEAD` and reattach if it comes back empty."

---

## Top practices worth copying for a 3-person FastAPI + React team on Azure Container Apps

1. Two rulesets: required CI with **no admin bypass** + 1-review bypassable by admins; squash-only.
2. `CONTRIBUTING.md` for non-engineers with exact `git`/`gh` commands; short `CLAUDE.md` that points.
3. Build in CI from a commit SHA, never from a laptop; a rehearsal target before production if one exists.
4. Verify by SHA and read back after publishing; idempotent re-runs are no-ops.
5. Client-facing changelog only for things users would notice (optional for us).
6. A version/asset guard in CI where a shipped artifact has a version.
7. Workflow inputs via `env:`; `permissions: {}` at top; third-party actions pinned to a SHA.
8. Instrumented Claude review: open/ready/reopen + `/review`, model pinned, tools allow-listed,
   **"assert the review was delivered"**.
9. CI-invisible verification as a `CLAUDE.md` obligation backed by a nudging `PostToolUse` hook.
10. `SessionStart` hook reporting "main is N commits behind origin".
11. Stage new CI checks as non-required, promote once proven.
12. `lessons.md` as an append-only incident log, promoted into `CLAUDE.md` when patterns recur.
13. Every ops state change is a reviewed one-line PR (for us: a deployments record, or `BUILD_SHA`).
14. `SECURITY.md` as a table of secrets with rotate-on-handover.
15. Migration contract: snapshot-first, verify-per-step, lossy declared, idempotent, human-confirmed.
