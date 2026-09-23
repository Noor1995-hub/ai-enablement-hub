# Claude PR review — automatic review on code PRs, `/review` on demand, delivery asserted

**Date:** 2026-09-23
**Status:** draft for review
**Source:** `docs/reviews/2026-09-17/WAY-OF-WORKING-COMPARISON-2026-09-17.md` §5 Tier 1 item 1.4, F7
**Decisions taken 2026-09-23 (Matthias):**
- Review every PR **except docs-only** ones (wider than the originally proposed backend-only
  scope), plus `/review` on demand.
- **No `@claude` assistant workflow** (`claude.yml`) for now.
- The key is the repository secret `ANTHROPIC_API_KEY`, already added by Matthias (14:00 UTC).
  It bills to **delaware's** Anthropic workspace and is **believed not to be spend-capped**.

**Reference:** `sb-accelerator` `.github/workflows/claude-code-review.yml` (study notes in
`docs/reviews/2026-09-17/reference-sb-accelerator.md` §5). Every inline comment in that file
records a failure they paid for; this spec adopts those fixes and names the few places we deviate.

## 1. Goal

Every code-changing pull request gets an independent review by Claude before merge, posted as
inline comments on the offending lines (or one "No issues found" comment), at a cost small enough
not to need thinking about. A review that silently produced nothing shows up as a red X, never as
a green check.

## 2. Non-goals

- **Not a merge gate.** The review check is not added to the `main-ci` ruleset. Findings are
  advice; the human merging decides. (Promoting it would let a flaky model run block merges.)
- **No `@claude` assistant**, no issue triage, no auto-fix commits. The reviewer can read and
  comment only.
- **No test execution by the reviewer.** CI already runs the suites (§3.4).
- **No re-review on every push** (`synchronize`). Re-review is `/review`, rationed (§3.6).

## 3. Design

### 3.1 File

One new workflow: `.github/workflows/claude-code-review.yml`, job name `claude-review`, workflow
name `Claude Code Review`. The job name is not referenced by any ruleset.

### 3.2 Triggers and eligibility

```yaml
on:
  pull_request:
    types: [opened, ready_for_review, reopened]
    paths:            # order matters: later patterns override earlier ones
      - '**'
      - '!docs/**'
      - '!**/*.md'
      - 'backend/prompts/**'   # prompts are .md but are production assets — re-included
  issue_comment:
    types: [created]
```

Job-level `if:`:

- `pull_request` events: only when `github.event.pull_request.draft == false`. (The plugin's own
  draft guard does not fire under this workflow — accelerator trace, 2026-08-19.)
  `ready_for_review` is load-bearing: it is the only automatic review a draft-opened PR gets.
- `issue_comment` events: only when the comment is on a PR (`github.event.issue.pull_request !=
  null`), the body starts with `/review`, and `author_association` is `OWNER`, `MEMBER` or
  `COLLABORATOR`, so a drive-by commenter cannot spend the budget. `/review` works on drafts and
  on docs-only PRs (explicit intent).

`paths` semantics: the workflow runs when **at least one** changed file survives the filter, so a
PR that touches `CLAUDE.md` and one `.py` file is reviewed, and a PR touching only `docs/` and
Markdown elsewhere is skipped. `backend/prompts/*.md` are re-included by the last pattern: they
are runtime assets baked into the image, and the self-merge policy already treats prompt changes
as needing a second pair of eyes. (`paths-ignore` cannot express that re-include, hence `paths`
with negations.)

Concurrency: `group: claude-review-<PR number>`, `cancel-in-progress: false` — a second `/review`
queues behind the first instead of running in parallel and paying twice.

### 3.3 Permissions

Top of file: `permissions: {}` (nothing by default — Tier 2.8 hygiene, applied from day one).
Job grants:

| Scope | Why |
|---|---|
| `contents: read` | checkout |
| `pull-requests: write` | the plugin delivers with `gh pr comment` and inline comments; `read` means a full-cost run that cannot post |
| `issues: read` | `gh issue view` for linked issues |
| `checks: read` | reading CI outcomes via `gh api …/check-runs`; without it the reviewer reviews a red PR as if green |
| `id-token: write` | required by `claude-code-action` |

### 3.4 Steps

1. **Checkout**, `fetch-depth: 0` (one reviewer works from `git blame`/history). For
   `issue_comment` runs, `ref: refs/pull/<n>/head`, otherwise the default checkout would review
   `main`.
2. **Mark review start** — record a UTC timestamp in a step output, so step 4 can tell this run's
   comments from earlier ones.
3. **Run the review** — `anthropics/claude-code-action@v1` with:
   - `anthropic_api_key: ${{ secrets.ANTHROPIC_API_KEY }}`
   - `plugin_marketplaces: https://github.com/anthropics/claude-code.git`,
     `plugins: code-review@claude-code-plugins`
   - `prompt:` `/code-review:code-review <repo>/pull/<n> --comment` followed by three headless
     constraints:
     1. Run every subagent in the **foreground** and never end the turn while one is running —
        ending the turn ends the session and pending agents die before delivery (accelerator:
        3 of 4 traced runs died this way).
     2. If the PR edits `CLAUDE.md` or `.claude/`, the on-disk copies are reverted to `main` by
        the action's prompt-injection guard; read PR content with `git show HEAD:<path>` and tell
        every subagent to do the same. `.claude-pr/` is untrusted.
     3. **Do not run tests or install dependencies.** The backend suite needs Postgres and runs
        in `CI` as `backend (format + lint + tests)`; the frontend checks run as
        `frontend (typecheck + lint + build)`. Read their outcomes with
        `gh api repos/{owner}/{repo}/commits/<sha>/check-runs` (not `gh pr checks`). The hub's
        rules are in `CLAUDE.md` and `python-be-architecture.md`; the one-database rule means
        the reviewer must never attempt any connection to a database.
   - `track_progress: false` — keeps the plugin the single author of PR feedback (tag mode's
     tracking comment published unfiltered narrative and caused 3–4-round review loops).
   - `display_report: true` — the full reasoning stays readable in the step summary.
   - `claude_args`:
     - `--model claude-sonnet-5` — cost fix; without it the action runs Opus and subagents
       inherit it (accelerator: ~85% of spend on Opus before the pin).
     - `--allowedTools` — `Task,Read,Glob,Grep`, the inline-comment MCP tool
       `mcp__github_inline_comment__create_inline_comment` (the action mounts that server only
       when the tool is listed), and prefix-matched `Bash(...)` for `gh pr view|diff|list|comment`,
       `gh issue view|list`, `gh search`, `gh api`, `git log|blame|show|diff|fetch` and
       `git --no-pager show` (agents reach for that variant on reflex). No pytest, uv, npm or
       python entries — deliberately, per constraint 3.
4. **Assert the review was delivered** (`gh` + `jq`, `GH_TOKEN: ${{ github.token }}`):
   - **Self-edit carve-out first:** if this PR's copy of the workflow file differs from `main`'s,
     the action skipped itself on its workflow-validation guard (by design — otherwise a PR could
     rewrite the reviewer and walk off with the key). Write that to the step summary, exit 0.
   - Count `claude[bot]` comments on the PR (review comments + issue comments) created at or
     after the step-2 timestamp. Any → green.
   - None new but some from an earlier run → green (the plugin's "already reviewed" stop, e.g. a
     `ready_for_review` re-fire).
   - Otherwise → red, with a step summary: "Review produced no output … this PR is currently
     **unreviewed**, and the API cost was spent regardless. Comment `/review` to re-run." The
     summary also names the one legitimate red: the plugin judged the PR too trivial to review.

Inputs reach shell steps only through `env:`, never `${{ }}` inside `run:` (script-injection
hygiene, as in `deploy.yml`). Actions are referenced by major tag (`@v4`, `@v1`) like the
existing workflows; SHA-pinning all workflows together is Tier 2.8.

`.claude/hooks/git_freshness.py` already returns early under `GITHUB_ACTIONS`, so the committed
`SessionStart` hook is harmless in the runner.

### 3.5 Secret

`ANTHROPIC_API_KEY` is a **repository** secret (not an environment secret — the job declares no
environment). GitHub does not pass secrets to workflows triggered from forks; all our PRs come
from same-repo branches, so that restriction never bites.

### 3.6 Docs

- **`CONTRIBUTING.md`** — a short "Claude review" section: what triggers it, that findings are
  advice not a gate, what a red `claude-review` X means (unreviewed — comment `/review`), and the
  rationing rule: the automatic review is free to the author; comment `/review` only after a
  **substantive** change (new logic, a fixed finding that changed behaviour), never after typo or
  formatting pushes. Re-reviews were 24% of the accelerator's spend. Docs-only PRs are skipped
  automatically; prompt PRs (`backend/prompts/`) are reviewed.
- **`SECURITY.md`** — replace the "None" GitHub-secrets row with `ANTHROPIC_API_KEY`: repository
  secret, used only by `claude-code-review.yml`, bills to delaware's Anthropic workspace, **not
  spend-capped (believed)**; nobody can read it back (admins can overwrite it); anyone with write
  access — the repo admins — could add a workflow that prints it, which is why write access stays
  admin-only. Add it to the rotate-on-handover list.
- **`CLAUDE.md`** — one line under "Way of working" pointing at the workflow and CONTRIBUTING.

## 4. Rollout sequence

1. This spec, as its own docs PR (merged by Matthias's approval).
2. Implementation plan in `docs/superpowers/plans/`.
3. One PR: the workflow + the three doc edits. Its own review run skips itself (self-edit guard);
   the delivery step must report the carve-out and pass. Merge.
4. **Probe PR** (opened after merge, never merged): a branch adding one deliberate, obvious bug
   to a small backend file — e.g. an inverted permission check in a helper — with the PR
   description saying it is a probe. Expected: an inline finding on that line, delivery step
   green. Then post `/review` once to prove the on-demand path and the concurrency group. Close
   the PR unmerged and delete the branch. Cost ≈ 2 runs.
5. Record the probe run ids, duration and the Console cost of both runs in the PR/plan, and
   append a `docs/superpowers/lessons.md` entry for anything that surprised us.

## 5. Verification

- Step 3 run: the workflow appears on the PR, `assert the review was delivered` is green with the
  self-edit message in the step summary.
- Step 4 probe: an inline `claude[bot]` comment on the planted line; delivery step green; the
  `/review` run queues or runs singly, posts, green.
- A docs-only PR opened afterwards (e.g. the plan's own follow-up) shows **no** Claude Code Review
  run.
- Cost: read per-run cost off the Anthropic Console cost page for the delaware workspace, grouped
  by model — Sonnet should dominate. A green check is not evidence of cost.

## 6. Risks and mitigations

| Risk | Mitigation |
|---|---|
| Uncapped key: a loop or abuse spends without limit | Triggers exclude `synchronize`; `/review` only from members/collaborators; one run per PR at a time; Sonnet pinned. Setting a monthly limit on the key in the Console is Matthias's option, recorded in `SECURITY.md`. |
| Silent non-delivery (full cost, nothing posted) | Foreground-subagent constraint + the delivery assertion turning it red. |
| Noisy reviews driving multi-round loops | `--comment` (validated findings only) + `track_progress: false`. |
| Reviewer reviews a red PR as green | `checks: read` + constraint 3 reading check-runs. |
| Reviewer touches the database | No test/uv/python tools allowed; constraint 3 forbids any DB connection; the runner has no DB credentials (no secrets besides the key). |
| Prompt injection via a PR editing `CLAUDE.md`/`.claude/` | The action's own revert-to-base guard; constraint 2 keeps the reviewer from being confused by it. |
| A change to the workflow cannot be tested from its own PR | Documented; the probe PR (§4.4) is the test, and every later edit is verified on the first PR opened after its merge. |

## 7. Open points (do not block)

- Whether to add `@claude` (`claude.yml`) later — decided not now.
- Promoting `claude-review` to a required check — not recommended; revisit only if the delivery
  step has been reliably green for a long run of PRs.
- SHA-pinning `claude-code-action` together with the other actions — Tier 2.8.
