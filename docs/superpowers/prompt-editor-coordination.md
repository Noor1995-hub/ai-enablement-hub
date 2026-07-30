# Prompt-editor — coordinate with Matthias (before merge)

Branch `feature/prompt-editor` (off `main` `b430a90`) adds **DB-backed, admin-editable
system prompts** + an admin "System prompts" page. Three things touch Matthias's Plan C/D/E
work or shared infrastructure — please sanity-check before we merge.

## 1. Your Plan C/D/E prompts are now admin-editable
The new admin page + `GET/PUT/DELETE /api/admin/prompts` surface **all 9 prompt kinds**,
including `content_improvement`, `content_improvement_critique`, `house_style`,
`feedback_triage`. An admin can now edit these **live** — a DB row overrides the shipped
`backend/prompts/<kind>.md`, with a reset-to-default that drops the row.

Required-placeholder validation on save applies **only to `interview_playbook`**
(`{first_name}`/`{assessment_json}`/`{company_context}`/`{transcript}`). Your four are
treated **verbatim** (no required tokens) — matching how your services consume them
(verbatim / message-composition, not `.format()`/`.replace()` on the prompt text).
**If any of your prompts actually needs a token preserved, tell me and I'll add it to
`REQUIRED_TOKENS` (`backend/src/services/prompt_service.py`).**

## 2. `load_prompt(kind)` is now DB-overridable
Signature unchanged, **still synchronous** — none of your call sites changed
(`content_improvement_service`, `feedback_triage_service`, plus chat/interview). It now
reads a bustable in-process `_CACHE` primed at lifespan startup and re-primed on every admin
save/reset (`PromptService.refresh_cache()`). The old `@lru_cache` was dropped for the
explicit cache. Single-replica assumption (`min=max=1`); if we ever scale out, switch to a
short TTL on `_CACHE` (noted, out of scope now). The stale
*"`load_prompt` must not be made dynamic / is `@lru_cache`d"* comment in
`content_improvement_service.py` was updated to reflect this.

## 3. Single Alembic head
New migration `1cd2cc2d05a9_add_prompts_table` chains off the current single head
`f9a0b1c2d3e4`. **Before merge, confirm you have NOT landed a second migration off
`f9a0b1c2d3e4`** — we must keep one linear head. Coordinate merge timing so the chain stays
single (same discipline as the interviewer merge).

## Merge notes
- Merge target is **`origin/main` @ `b430a90`**. (The local `main` ref in the worktree is
  stale at `b6dcf16`, a parent of the `b430a90` merge commit — ignore it; use `origin/main`.)
- Same clean-merge-check + explicit-go discipline as the interviewer merge. Not pushed,
  merged, or deployed yet.
