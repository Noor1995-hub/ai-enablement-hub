# Prompts: git is the only source of truth — retire the DB override, read-only page, golden cases

**Date:** 2026-09-23
**Status:** approved to build (Matthias, 2026-09-23: "it will stay only us so let's go ahead")
**Source:** `docs/reviews/2026-09-17/WAY-OF-WORKING-COMPARISON-2026-09-17.md` §5 Tier 1 item 1.9, F13
**Supersedes:** the write half of `2026-07-29-prompt-editor-design.md` (DB-backed prompts + admin
editor). The page layout of `2026-07-30-prompts-page-master-detail-design.md` stays.

**Decisions and facts (2026-09-23):**
- Only Matthias and Aaron will ever edit system prompts. Both work through Claude Code and PRs,
  so the editor's reason — "live, without a redeploy" at a time when a deploy was a laptop
  script — no longer pays for its costs (no history, no review, silently masks the next file
  change).
- **Live census:** the production `prompts` table holds **0 rows** (read-only `SELECT`,
  2026-09-23). Every prompt already runs on its `backend/prompts/*.md` file, so removing the
  overlay changes no live behaviour and no override needs folding back into git first.

## 1. Goal

A system prompt can change only through a pull request: the file in `backend/prompts/` is what
runs, the Claude review sees the change (the review workflow re-includes `backend/prompts/**`),
and the Deploy button ships it. The admin System Prompts page shows what is live and where to
change it. Every AI feature has a golden case that makes any change to what it sends the model
visible as a diff in the PR.

## 2. Non-goals

- **No table drop in this change.** The `prompts` table and its model stay (expand-first: an
  older image rolled back onto this schema still works). Dropping it is a migration for the July
  fix programme's phase C, which owns all new migrations (`docs/reviews/2026-07-31/`).
- **No "edit via PR from the UI"** (GitHub API). Later, if ever wanted.
- **No live-model evals.** Golden cases pin what we *send*, not what the model answers; they run
  with a fake client, cost nothing, and are deterministic.
- No change to prompt *content*.

## 3. Design

### 3.1 Backend — file-only prompts

- `services/prompts.py`: `load_prompt(kind)` reads `backend/prompts/<kind>.md` (cached in-process
  after first read; the cache can no longer be written from outside). Remove `set_cache` and
  `reset_cache`; keep `read_file` and `clear_cache` (tests).
- `services/prompt_service.py`: file-backed, no repository. `list_all()` and `get(kind)` read the
  files. Remove `update`, `reset`, `refresh_cache`, `missing_tokens`, and the constructor
  dependency on `PromptRepository`. `KNOWN_PROMPTS` and `REQUIRED_TOKENS` stay (the latter now
  backs a test, §3.4).
- `schemas/prompt.py`: `PromptSummary` = `kind, label, group, path`; `PromptDetail` = `kind,
  label, content, path`. `path` is the repo-relative file path, e.g.
  `backend/prompts/interview.md`. `source`, `updated_at`, `required_tokens` and
  `PromptUpdateRequest` go.
- `routers/admin_prompts.py`: keep `GET /api/admin/prompts` and `GET /api/admin/prompts/{kind}`
  (admin-only, unknown kind → 404). Remove `PUT` and `DELETE` — they become 405 by FastAPI's
  routing.
- `core/dependencies/prompt.py`: provider returns `PromptService()` with no session.
- `main.py` lifespan: remove the `refresh_cache()` priming (and its imports).
- Delete `repositories/prompt_repository.py`. Keep `db/models/prompt.py` with a one-line note:
  "Retired 2026-09-23 (prompts are git-only); table kept for rollback safety, dropped in the
  July phase C."

### 3.2 Frontend — read-only page

- `pages/admin2/PromptsPage.tsx`: same master–detail layout. Left: grouped list, no
  Edited/Default chip. Right: the prompt text in a read-only, monospace, scrollable block; a
  line "Source of truth: `backend/prompts/<kind>.md` in git. Change it with a pull request, then
  deploy." with two links — **View live version** (`…/blob/<build_sha>/<path>` from
  `/api/health`; when `build_sha` is `dev` or unavailable, fall back to `…/blob/main/<path>`) and
  **Edit on GitHub** (`…/edit/main/<path>`, which opens GitHub's editor and proposes a branch +
  PR). No textarea, no save, no reset, no `window.confirm`.
- `pages/admin2/api.ts`: remove `useUpdatePrompt` and `useResetPrompt`; `usePrompts`/`usePrompt`
  unchanged apart from types. Reuse the health query hook the Setup page already uses.
- `src/api/schema.d.ts` regenerated **without starting the backend**: the dev server's lifespan
  connects to the live database and its cleanup loop deletes expired sessions. Generate
  `openapi.json` by importing `src.main.app` and calling `app.openapi()` (imports run no
  lifespan), then `npx openapi-typescript <file> -o src/api/schema.d.ts`.
- `types/domain.ts` `PromptSummary` (and any detail type) follows the schema.

### 3.3 Hooks and docs

- `.claude/hooks/prod_asset_nudge.py`: the `backend/prompts/` message drops "can be masked by a
  DB override on the admin System Prompts page" and says: git is the only source of truth; the
  change ships on the next deploy; the golden snapshots must be regenerated and their diff read.
  Its unit test fragment follows.
- `CLAUDE.md`: every "DB-overridable" / "admin-editable" prompt mention becomes git-only (the
  `backend/prompts/` repo-map line, the System prompts feature-index line, the admin-panel
  feature list); one line on the golden cases.
- `docs/README.md` "Not docs" note: drop "DB-overridable via the admin System Prompts page".
- `CONTRIBUTING.md`: one sentence under the Claude review / deploy area — prompt changes are PRs;
  regenerate the golden snapshots with `UPDATE_GOLDEN=1`.

### 3.4 Tests

- **Prompt integrity (unit):** every `KNOWN_PROMPTS` kind has a non-empty file; every
  `REQUIRED_TOKENS` entry is present in its file (the check the editor used to do on save now
  runs in CI on every PR).
- **Golden cases (one per AI feature):** `backend/tests/golden/ai/`, one JSON snapshot per
  feature, produced by driving the real service with `tests/fixtures/llm.py`'s `FakeLlmClient`
  and fixed fixtures, and recording exactly what reaches the client: `system`, then `messages`
  (chat) or `prompt` (structured), plus `max_tokens` and the structured schema name. A shared
  helper compares against the committed file, and with `UPDATE_GOLDEN=1` rewrites it instead.
  Features (8 snapshots): `chatbot`, `assessment`, `lesson` (chat surfaces), `interview`
  (conversation turn, system includes the briefing), `interview_playbook` (all four tokens
  substituted), `content_improvement` (draft: house style + drafting prompt + calibration
  notes), `content_improvement_critique`, `feedback_triage`. Fixtures are fictional (no real
  learner names). A missing snapshot fails the test with the regenerate instruction.
- Existing tests: `test_prompt_seam.py` loses the set/reset cases; `test_prompt_service.py` is
  rewritten for the file-backed service; `tests/integration/test_routers/test_admin_prompts.py`
  keeps list/detail/404/non-admin-403 and asserts `PUT`/`DELETE` return 405.

## 4. Rollout

1. This spec + the plan, then one feature PR (backend + frontend + tests + docs). CI green; the
   Claude review runs on it (non-docs PR) — read its findings before merging.
2. Deploy is deliberate and separate: until the next Deploy run, production keeps the old editor.
   Since the table is empty, deploying changes no AI behaviour; after it, the page is read-only
   and `PUT`/`DELETE` return 405.
3. Later (phase C): drop the `prompts` table and its model.

## 5. Verification

- Backend: `poe format-check`, `lint-src`, full `poe test` green; the integrity test fails when a
  required token is removed from a copy of the file (checked by hand once).
- Golden: `UPDATE_GOLDEN=1` generates 8 files; a second plain run passes; editing one prompt file
  locally makes exactly its snapshot test fail with a readable diff (checked once, reverted).
- Frontend: `typecheck`, `lint`, `build` green; the page rendered against a stubbed `fetch` with
  production-shaped fixtures (CLAUDE.md "Verifying without touching live data"): list, text
  block, both links with the right URLs, no textarea/buttons.

## 6. Risks

| Risk | Mitigation |
|---|---|
| An override appears between the census and the deploy | Only the two admins can create one, and both know; the deploy note in the PR says to re-check the page before pressing Deploy. |
| Snapshots churn and get regenerated blindly | The nudge hook and CONTRIBUTING say to read the diff; the Claude review sees it too. |
| Rollback to a pre-change image | Works: the table and its columns are untouched; the old image simply finds 0 rows. |
