# AI Enablement Hub — Full Independent Code & DB Review

**Date:** 2026-07-31
**Scope:** the live Azure rebuild (`AI ENABLEMENT HUB REBUILD/`) — backend (`backend/src`, ~14.7k LoC,
135 files, 20 routers / 82 route decorators), frontend (`frontend/src`, 109 TS/TSX files), database
(17 Alembic migrations + models + `db/` scripts), and config/deploy/infra. The retired Supabase app
(`../app/`) is out of scope.
**Baseline:** `main` @ `91c1ac7`; prod image `20260730-144052`, revision `--0000033`, alembic head
`1cd2cc2d05a9`.
**Method:** five parallel read-only reviews (security · database · backend architecture · frontend ·
cohesion/delivery), each also re-verifying every finding of the 2026-07-09 audit (`CODE-REVIEW.md`)
against current code. Headline claims were spot-checked independently. No files were modified.

---

## Headline

The codebase is in **genuinely good health** — better than most human-built projects of this age.
The layered backend architecture has *strengthened* under 2.5× growth, two authors building in
parallel converged on near-identical conventions, type discipline is exceptional (zero `any` in the
frontend, fully annotated backend, `__all__` + `from __future__ import annotations` in 100% of src
modules), and most 2026-07-09 debt was genuinely paid down — **6 of that audit's 8 priority items are
verifiably fixed**.

**No critical code vulnerability was found.** The largest risks are not in the code but in the
process around it: development is documented to run against the **production** database, deploys ship
the working directory with no guard, there is no CI or test gate anywhere, and the AI spend cap on
the prod Anthropic key is unverified.

## Priority summary

| # | Batch | Theme | Sev | Effort |
|---|-------|-------|-----|--------|
| 1 | Operational | Spend cap · key rotations · dev DB | Critical/High | S–M |
| 2 | Code | Security quick-wins (9 small fixes) | High | S |
| 3 | Code | Lesson access control + media SAS leak | High | M |
| 4 | Process | CI · dirty-tree guard · coverage gate · smoke test · logging | High | M |
| 5 | Repo | Real-user PII tracked in git | Medium | S–M |
| 6 | DB | Unit-of-work seam · survey guard regression · indexes | Medium | M |
| 7 | Code | AI-layer resilience (timeouts, 529s, SSE errors) | Medium | S–M |
| 8 | Code | Frontend robustness (error boundary, typed client, lazy) | Medium | S–M |
| 9 | Code | Consistency & cleanup | Low | S–M |

---

## Batch 1 — Operational (no code)

**1.1 (Critical-adjacent) — Verify/apply a hard spend cap on the prod Anthropic key** (`llm-api-key`).
Admin- *and* learner-reachable AI spend is live. Per-user rate limits exist and are decent
(`core/ratelimit.py`) but live in a plain in-process dict, so **every counter — including the 200/day
chat cap — resets on each container restart**, and there is no aggregate/global ceiling in code. The
provider-side cap is the only real backstop. Per `docs/ai-agents-plan.md` §8b it should be a
dedicated workspace key with a monthly cap; whether that swap happened is unverified.

**1.2 (High) — Rotate the `aienablementhubmedia` storage account key.** Leaked into a 2026-07-30
transcript; rotation deferred and still owed. `docs/db-backup-restore.md`'s health-check snippet also
pulls this key, contradicting the job's otherwise key-less managed-identity design.

**1.3 (Low) — Rotate the dev `AUTH__JWT_SECRET`** (surfaced in a 2026-07-06 transcript; dev-only
blast radius, prod uses a different secret).

**1.4 (Critical) — Provision a real dev database.** `backend/.env.local.example:9` sets
`DATABASE__NAME=ai-enablement-hub` — the **production** database — and `db/README.md`'s environment
table lists only main + test DBs. Only the test suite is isolated (`ai-enablement-hub-test`, guarded
by name in `conftest.py`). A mistake made while developing mutates real learner data; the nightly
dump (30-day retention) and 7-day PITR are the only net. Fix: provision `ai-enablement-hub-dev` +
a seed/clone script, repoint the example env.

---

## Batch 2 — Security quick-wins (code, all Small)

**2.1 (Medium) — Chat conversation resolved by id without a `kind` check.**
`services/chat_service.py:53-64` verifies `conversation.user_id != user_id` but never `kind`, and
`send_message` derives the system prompt from the *stored* row (`:82`
`system_prompt = load_prompt(conversation.kind)`). The AI-surface gate is per-kind and keyed off the
**path** segment (`routers/chat.py:120-123`, `core/dependencies/chat.py:52`). So a learner who posts
their existing *interview* `conversation_id` to `POST /api/chat/chatbot` passes the `chatbot` gate and
appends turns to the interview conversation under the interview prompt — even if the project's
`interview` surface is switched off. Those turns are what admins read in `admin2/InterviewCard.tsx`
and what feeds `interview_playbook` generation.
**Fix:** add `or conversation.kind != kind` to the guard.

**2.2 (Medium) — Interview endpoints skip the component hidden/locked gate.**
`routers/interview.py:26` gates the router with `require_interview_surface` only; that dependency
(`core/dependencies/interview.py:62-77`) reads `resolve_ai_settings` and never consults the
component's `hidden`/`locked` flags. Assessment and learning *are* hard-gated
(`routers/survey.py:23`, `routers/learning.py:28` via `require_component_unlocked`). Interview is
itself one of the three gated components (`core/constants.py DEFAULT_LOCKED`), so a project whose
Interview tile an admin hid or locked still serves the interview API.
**Fix:** add `Depends(require_component_unlocked("interview"))` to the router (or document
single-gating as deliberate).

**2.3 (Medium) — Swagger anonymously browsable in prod, and CSP-exempt.** `main.py:127` constructs
`FastAPI(title=..., lifespan=...)` with no doc-URL suppression (zero matches for
`docs_url|redoc_url|openapi_url` in the backend), and the security-headers middleware deliberately
skips CSP for `/docs`/`/redoc` (`main.py:168-175`). `/docs`, `/redoc`, `/openapi.json` expose the
full 82-endpoint surface incl. every `/api/admin/*` path and schema to anonymous visitors. Open since
2026-07-09 (prior 7.1).
**Fix:** `docs_url=None, redoc_url=None, openapi_url=None` when `settings.app.env == "prod"`; the CSP
exemption branch then becomes dead.

**2.4 (Medium) — No catch-all 500 handler, so unexpected errors break the JSON error contract.**
`main.py:239-306` registers handlers for nine specific exception types; anything else (incl. Anthropic
`OverloadedError`, `LlmError`, DB errors) falls through to Starlette's plain-text 500.
`docs/design/design-backend.md:242` explicitly promises a catch-all 500 in the standard shape.
**Fix:** `@app.exception_handler(Exception)` returning `{"error":{code:"internal_error",message:…}}`
+ `logger.exception`.

**2.5 (Medium) — No refresh-token reuse detection.** The rotation race *is* fixed (atomic conditional
`revoke()` honoured at `token_service.py:89`), but `:78-83` lumps `revoked_at is not None` in with
unknown/expired and just raises `InvalidSessionError`. `revoke_all_for_user` exists (`:153`) and is
used after set-password, but never on reuse. A stolen 14-day refresh token replayed after rotation
logs the victim out once; nothing detects or kills the thief's family of sessions.
**Fix:** distinguish revoked from unknown; on a revoked presentation call
`revoke_all_for_user(auth_session.user_id)` and log it.

**2.6 (Low) — Unrate-limited learner writes.** `POST /api/feedback` (`routers/feedback.py:20-27`)
takes no limiter at all — 4000 chars/row (`schemas/feedback.py:22`) feeding the admin AI-triage queue,
so it is also an amplification path into AI spend. Also unlimited: `POST /api/auth/refresh`
(`routers/auth.py:87`), survey draft saves, lesson progress. Prior 7.3b.
Additionally the limiter store never evicts (`core/ratelimit.py:22`) and login keys on the submitted
email only (`routers/auth.py:74`) — so unbounded key growth, unlimited password spraying across
accounts, and targeted 429-lockout of one victim are all possible. (Credit: user enumeration *is*
properly closed via the constant-cost dummy bcrypt in `user_service.py:33-35`.)
**Fix:** limiter on feedback/refresh; a per-IP login counter alongside per-email; bound the store.

**2.7 (Medium) — `renderInline` has no link-protocol allowlist, and the risk premise changed.**
`frontend/src/components/lesson/blocks/renderInline.tsx:10-11` turns any `[text](anything)` into
`<a href={link[2]}>` verbatim, and 8 block components use it. Prior 7.3e rated this Low because
content was admin-authored — **that premise no longer holds**: `content_improvement_service` now
drafts `content_blocks` from learner-submitted feedback text, and `validate_content_blocks`
(`services/content_blocks_validation.py:110-142`) validates structure only, never URL schemes. Chain:
learner feedback → AI draft → admin approves a diff in `ProposalDiff.tsx` → live for all learners.
React 18 warns on `javascript:` hrefs but still renders them.
**Fix:** allowlist `https:`/`http:`/`mailto:`/relative in `renderInline`, render others as text;
optionally also reject schemes server-side in `validate_content_blocks`.
(Related and *clean*: video embeds go through a real allowlist in `lib/videoEmbeds.ts:49`, re-normalised
at render, backed by CSP `frame-src`.)

**2.8 (Low) — Learner text reaches system prompts without structural delimiters.**
`services/interview_context.py:183-213` interpolates the learner's own survey free-text (up to 2000
chars/field) into the briefing, appended straight onto the system prompt
(`chat_service.py:82-84`, `interview_service.py:120`). The hard paths *are* defended —
`prompts/interview_playbook.md` wraps untrusted input in tags with explicit
"DATA, not instructions" handling, as do `prompts/content_improvement.md:14` and
`feedback_triage_service.py:149` — but the briefing block has no tag wrapper.
**Fix:** wrap it in the same `<assessment_briefing>…</assessment_briefing>` DATA envelope.

**2.9 (Low) — CSP gaps + `?edit=true`.** `main.py:146-156` lacks `base-uri` and `form-action` (not
fallback-covered by `default-src`; `object-src` *is* covered, so that half of prior 7.3c is moot).
`frontend/src/pages/LessonPage.tsx:22` initialises `editMode` from the query param with no `isAdmin`
check, so the editor pane renders for non-admins (saves still 403 server-side — cosmetic, prior 8.2).
Also `startup.py:26` `forwarded_allow_ips="*"` trusts `X-Forwarded-For` from any peer (prior 7.2,
near-non-issue behind ACA ingress).

---

## Batch 3 — Lesson access control + media SAS leak (High, Medium effort)

**3.1 — Any authenticated learner can fetch/complete any lesson by UUID, and thereby mint media SAS
URLs for it.** `services/learning_service.py:183-242` (`lesson_detail`) and `:244-249`
(`save_progress`) look the lesson up and return `content_blocks` with **no** assignment, maturity or
prerequisite check on the requested lesson (`is_assigned` is used only to pick the next hop). The only
gate is router-level `require_component_unlocked("learning")`, a per-project flag.

This gap is documented in CLAUDE.md and was accepted — but it now has a consequence the prior review
did not cover: `routers/learning.py:75` stamps fresh SAS URLs onto the returned blocks
(`media.stamp_blocks(...)`), and `services/media_service.py:130` issues a read SAS valid for
`sas_ttl_hours` (default 48, floor 25 — `core/configs/storage.py:11`). So any authenticated learner
can walk lesson UUIDs and extract SAS URLs that **any unauthenticated third party** can fetch
directly from Blob storage for up to two days.

**Verified mitigating fact:** completing unassigned lessons does *not* inflate maturity —
`MaturityService.effective_level` feeds `advance_level` from `assigned_lesson_counts_by_module`, which
counts assigned lessons only. There is no self-promotion path.

**Fix:** reject in `lesson_detail`/`save_progress` when the lesson is neither assigned to the caller
nor maturity-unlocked (all inputs already computed in that service); admin/`user+` bypass. Consider
shortening `sas_ttl_hours` and/or proxying media behind an authenticated route. The
prerequisite-DAG half of a full port is genuinely Large; the assignment+maturity half is S/M and
closes the SAS leak.

---

## Batch 4 — Delivery pipeline (process)

**4.1 (High) — Deploys ship the working directory, not a commit, with nothing guarding it.**
`deploy.ps1:25` runs `az acr build ... $PSScriptRoot`; CLAUDE.md:305 admits "modulo anything
uncommitted" and :345-350 that the safer worktree procedure is "**not yet baked into deploy.ps1**".
Prod has run un-pushed commits before (2026-07-22). Two people work in the same tree.
**Fix:** abort on a dirty tree (or auto-build from a fresh worktree of HEAD) and print the shipped SHA.

**4.2 (High) — No CI, no pre-commit, no test gate.** Verified: no `.github/`, no
`.pre-commit-config.yaml`, no husky; `deploy.ps1` runs zero checks. Nothing but habit stops a
regression reaching production.

**4.3 (Medium) — The mandated ≥80% coverage floor is neither enforced nor measured.**
`python-be-architecture.md` requires it and references `tests/pytest.ini` + `.coveragerc` — neither
exists; `pyproject.toml:55` `poe test` runs pytest without `--cov`; `pytest-cov` is installed and idle.

**4.4 (High) — Zero frontend tests, zero E2E, and a growing never-browser-verified surface.**
No test script in `frontend/package.json`, no vitest/playwright, no `*.test.*` under `frontend/src`.
Per CLAUDE.md the unverified list now includes multiplier-track rendering, below-level free review,
the whole `user+` flow, the admin redesign's spec §7 five-flow walk, and the entire 2026-07-30 wave
(interview UI, System Prompts page).

**4.5 (Medium) — Interview is the one backend feature tested below house standard.** No router or
integration tests for `/api/interview/*` or `/api/admin/interviews/*` (unit-only); every comparable
feature has router tests. Consequently `require_interview_surface` — and 2.2's missing gate — is
never exercised over HTTP.

**4.6 (Medium) — Migrations auto-apply on container start with no staging and no rollback story.**
`startup.py:17-18` + a ~240 s startup probe budget (`infra/containerapp.yaml:66-76`). Rolling back the
image does not roll back the schema; recovery is a manual restore. Residual risks: a failing migration
bricks the new revision (whether ACA keeps the old one serving is unverified), and any future
large-table rewrite could exceed the probe budget. All 17 migrations so far are small and additive.

**4.7 (Medium) — No logging/observability configuration at all.** Zero matches for
`basicConfig|dictConfig|structlog|opentelemetry|applicationinsights|sentry` in `backend/`. Bare module
loggers under default config likely never emit INFO. When prod breaks the only signals are uvicorn
access lines plus the two backup alert rules — nothing alerts on app errors, 5xx rates, or LLM spend.

**4.8 (Low) — Base images float on mutable tags** (`Dockerfile:7,17,29`); dependency layers *are*
reproducible (`npm ci` + committed lockfile, `uv sync --frozen`). **4.9 (Low) —** `deploy.ps1:12`
hardcodes this machine's az path and identifies "the just-queued build" as `list-runs --top 1`, which
can poll someone else's concurrent run.

---

## Batch 5 — PII & repo hygiene (Medium)

**5.1 — Real employee PII is git-tracked.** `git ls-files` confirms `db/baseline/data/users.json`
(7 real records: names, emails, roles) and `survey_responses.json` (real free-text answers about
people's own work) are tracked, along with `lesson_progress.json`, `user_tracks/`, `user_modules.json`.
No password hashes (the export nulls them). `invite_tokens.json` *is* correctly git-ignored — but it
sits on disk in the folder that the buggy az packer once uploaded to ACR task storage
(CLAUDE.md:199-204; guarded now by `.dockerignore:42-43`).
**Fix:** move the people-tables out of git (keep content tables if migrations' hardcoded UUIDs need
them), scrub history if policy requires, delete the stale token file.

**5.2 (Low) — Misplaced artifacts.** Committed JSON DB dumps in `backend/scripts/`
(`foundation_to_tools_DBBACKUP.json` etc.), Node `.js` workflow scripts inside the Python backend
(`backend/scripts/content_qa/*.js`), `infra/backup/__pycache__/` on disk. `scratch_review/` is
git-ignored yet contains `general_iii/check_draft.py`, the documented gate for all content authoring —
it exists on one machine only.

---

## Batch 6 — Database robustness (Medium)

**6.1 (Medium) — Repos commit internally, so no multi-step operation is atomic — and the survey
mitigation has regressed.** `services/survey_service.py:71-128`: `complete()` commits the survey, then
`_seed_assignments` issues three more commits (`assignment_repository.py:193,221,249`). Worse than the
2026-07-09 description: the seed guard `if await self._assignments.track_ids_for_user(user_id): return`
(`:90-91`) means a crash *between* the tracks-commit and the modules-commit leaves the user with
tracks but **no modules or lessons, permanently** — the survey is already `complete` so `complete()`
can't re-run, and any retry exits at the guard. The prior "retry-safe" mitigation no longer holds.
Same shape on proposal approval: `content_improvement_service.py:604-607` (`update_lesson` commit,
then `set_approved` commit) — a crash between leaves the lesson rewritten while the proposal reads
`pending`, and re-approving mis-reports "superseded".
**Fix:** flush-only repository variants + service-owned `commit()` (the unit-of-work seam). If the full
seam is too big now, at minimum fix the survey guard so a partial seed is repairable.

**6.2 (Low) — Missing indexes on FK columns.** `feedback.user_id` has none
(`db/models/feedback.py:28-30`; migration `f1a2b3c4d5e6` creates only `ix_feedback_lesson_id`) — user
deletes and the project-scoped feedback queue (which joins via `User.project_id`) seq-scan feedback.
Also unindexed `ON DELETE SET NULL` columns: `feedback.reviewed_by`,
`lesson_content_proposals.reviewed_by`, `calibration_notes.reviewed_by`, `prompts.updated_by`.
Everything else is covered (user-side FKs are leading columns of their UNIQUE constraints).
Also still open from prior 10.2b: no index on `auth_tokens/auth_sessions.expires_at` (mitigated —
the daily purge keeps both tiny).

**6.3 (Low) — `messages` ordering has no tiebreaker.** `message_repository.py:44-61` orders by
`created_at` alone, while the same codebase treats this hazard as load-bearing elsewhere
(`calibration_note_repository.py:62-70` adds `id DESC` with a comment). Timestamps are per-row
client-generated, so ties are unlikely but would flip turn order.

**6.4 (Low) — Newer-table drift vs the house pattern.** `prompts` has **no CHECK on `kind`** (only
service-level `_META_BY_KIND` validation) and no `created_at` (`db/models/prompt.py:15-25`) — every
other enum-as-text column in the schema has a CHECK. `project_ai_settings` has neither `created_at`
nor `updated_at` (`company.py:113-133`) while its sibling `project_component_settings` has
`updated_at`. `curricula.created_at` is the only nullable `created_at` (prior 10.2c).

**6.5 (Low) — Concurrency gaps without DB-level guards.** `sort_order` has no
`UNIQUE (module_id, sort_order)` and creation is a racy `max(...)+1`
(`content_service.py:40-41,77-81,94-96`); "one interview conversation per user" is convention only
(`interview_service.py:82-84,114-141` check-then-create, no partial unique index); survey first-draft
is get-then-create so a concurrent double-submit surfaces as a raw 500 IntegrityError
(`survey_service.py:40-46`). Also prior 10.2a: next-lesson uses strict `sort_order >` and so skips ties
(`learning_service.py:204-210`).

**6.6 (Medium, carried) — `module_prerequisites` still allows cyclic and cross-track edges.** Only
`ck_module_prerequisites_not_self` exists in the DB (`db/models/learning.py:102`);
`content_service.create_module:62-68` checks existence only. Such rows lock dependents invisibly
(the frontend drops cross-track predecessors from layout and rank-guards cycles). Prior 10.1.

**6.7 (Low) — No retention story for `conversations`/`messages`.** The daily cleanup purges only auth
tokens/sessions (`main.py:77-99`); dialogue grows unbounded by design, and `list_for_user`
(`conversation_repository.py:45-51`) is unbounded — fine for `interview` (one row), open-ended for
`chatbot` once real ChatPanels mount. Needs a decision, not necessarily code.

**6.8 (Low) — Admin lesson writes bypass `validate_content_blocks` and have no size cap.**
`routers/admin_content.py:107-120` → `content_service.update_lesson` persists `content_blocks` after
only stripping ephemeral SAS URLs; the strict validator is wired **only** into the AI-proposal path.
Plausibly deliberate (66/91 live lessons fail the strict validator) — but then the asymmetry (AI gated,
humans not) should be a written decision. No request-size ceiling on the lesson PATCH either, unlike
media and CSV.

**6.9 (Low) — Assorted efficiency carryovers.** `/learning/graph` still runs three duplicate queries
per request (prior 2.2 — `routers/learning.py:46-47`: `maturity_service.effective_level` and
`learning_service.graph` each run `list_tracks`/`list_modules`/`assigned_lesson_counts_by_module`);
admin pagination slices **in Python after a full enriched fetch** (`admin_user_service.py:176-177,
465-466`); `content_repository.py:171-176` `set_lesson_orders` loops M UPDATEs;
`learning_service.py:159,196` pull all assigned lesson ids to test one module's membership;
`bulk_assign`/`apply_project_defaults` write per user in a loop; `list_queue` over-fetches
`content_blocks` just to show titles. `pool_recycle` is absent (mitigated by `pool_pre_ping=True`).

---

## Batch 7 — AI-layer resilience (Medium)

**7.1 (Medium) — Interview LLM calls have no explicit timeout.** `interview_service.py:120-134`
(opener stream) and `:166-179` (playbook `_generate`, retried once, up to 8192 tokens) rely on the
Anthropic SDK default (~10 min). Every sibling does better: triage wraps each call in
`asyncio.timeout(30)` + a 120 s run budget; content improvement uses `asyncio.timeout(180)` sized
against the 240 s ACA ingress; Entra exchange 10 s. A hung playbook can keep the server working ~20
minutes after the browser already got a 504.

**7.2 (Medium) — Transient provider errors (529/429) escape as unstructured 500s.**
`interview_service.py:_generate:177` retries only `(ValidationError, LlmError)`, so an
`anthropic.OverloadedError` propagates out of `build_playbook`, and `main.py` has no handler for it
(see 2.4) → raw 500. The `is_transient_provider_error` helper (`llm_service.py:39-49`) that content
improvement uses carefully (`:302-311`, with a well-designed deferred bucket) is simply not consulted
here. For chat streaming, `chat_service.send_message:90-103` handles disconnects well
(`GeneratorExit`/`CancelledError` with `asyncio.shield`ed persistence) but a provider exception
mid-stream propagates *after* the 200 + `text/event-stream` headers are committed and there is no
`error` SSE event — the learner just sees a dead stream.

**7.3 (Low) — Rate-limit counters are in-process and non-persistent** (see 2.6 / 1.1): daily caps
reset on restart, the store never evicts, and a scale-out past one replica would multiply every limit.

---

## Batch 8 — Frontend robustness (Medium)

**8.1 (High) — No React error boundary anywhere.** No `componentDidCatch`/`getDerivedStateFromError`
in the tree (`admin2/kit/ErrorState.tsx` is a fetch-state UI, not a boundary). `LessonView.tsx:63`
tolerates *unknown* block types, but a known type with malformed fields (a quiz with `options: null`)
throws — and content now arrives from hand edits *and* the AI proposal pipeline. Result: white page,
no message, no recovery.

**8.2 (Medium) — A stale escape hatch un-types ~25 admin/interview calls.**
`pages/admin2/api.ts:44-65` and `lib/interviewApi.ts:1-22` each build
`const raw = client as unknown as RawClient` (the only `as unknown as` casts in the codebase) with
comments claiming these endpoints are "not yet regenerated into the schema" / "After tomorrow's
`gen:api`, these swap to typed calls". Verified: `api/schema.d.ts` **does** contain every one of those
paths (`/api/admin/dashboard`, `/api/admin/feedback`, `/api/admin/assignments/bulk`, defaults,
reminder, all content-improvement + calibration routes, `/api/interview/*`), and `types/domain.ts`
already aliases the response types onto it. A typo'd URL or a backend rename now compiles cleanly and
fails only at runtime, in production, for admins.

**8.3 (Medium) — No unsaved-changes guard on any editor.** Zero `beforeunload`/`useBlocker` in the
tree; `LessonEditor.tsx:180`'s `dirty` state only drives a label. Closing the tab, pressing Back, or
clicking a sidebar link mid-edit silently loses work (lesson editor, `PromptsPage.tsx:186`,
`ContentImprovementPage.tsx:250-273`).

**8.4 (Medium) — Zero code-splitting.** `App.tsx:5-25` eagerly imports all 10 admin2 pages; no
`React.lazy` or dynamic `import()` anywhere. `@tanstack/react-query`, `styles/admin.css` (857 lines)
and every admin screen ship in the single bundle every learner downloads to read a lesson.
(Framer-motion is *not* overused — only two importers.)

**8.5 (Medium) — Assignment matrix does unmemoized O(users × columns × content) work on an
unpaginated list.** `admin2/Matrix.tsx:57-71,297-322` runs `modules.filter(...)`/`lessons.filter(...)`
per cell per render with no `useMemo`, and `/api/admin/learning` returns **all** users of the scope
(`api.ts:108-117`) unlike PeoplePage's 50-row pages. Every optimistic cell click re-renders the whole
table. Fine at dozens of users; visibly laggy after the re-invite wave.

**8.6 (Medium, carried) — Per-keystroke MDX reparse.** `pages/LessonPage.tsx:47` runs the full
162-line regex parser on every render, i.e. every keystroke in MDX mode. One `useMemo` fixes it
(prior 6.4).

**8.7 (Low) — Assorted.** Five suppressed `exhaustive-deps` remain, each documented but load-bearing
(`LearningPathNew.tsx:391,466` where the lock/progress helpers are still plain closures, `:253-308`);
three `window.confirm` calls despite the in-repo rule and the existing `ConfirmButton`
(`ModulePanel.tsx:63`, `admin2/InterviewCard.tsx:81`, `PromptsPage.tsx:192,198`); SSE chat stream has
no `AbortController` so navigating away mid-reply leaves it running (`lib/useChat.ts:79-135`); the
prompt editor reseeds `content` on background refetch and can clobber a colleague-era draft
(`PromptsPage.tsx:160-162`); any failed lesson GET reads as "Lesson not found"
(`LessonPage.tsx:69-77`); `Modal.tsx:13-42` has no focus trap/restore and `Table.tsx:75-84` rows are
mouse-only (`<tr onClick>`, no `tabIndex`); `AuthContext.tsx:121-132` value object is unmemoized
(negligible blast radius today); two hand-kept response shapes can drift (`api/upload.ts:9-16`,
`api/bulkInvite.ts:10-35`).

---

## Batch 9 — Consistency & cleanup (Low)

**9.1 — The admin/admin2 straddle.** Ten `admin2/` files import from the superseded `pages/admin/`:
`formatDate`/`LevelBadge` (`adminHelpers`), the legacy inline-style dict `s` (`adminStyles`, used
inside `admin2/InterviewCard.tsx`), and three whole components (`BulkInviteModal`,
`EmailTemplatesCard`, `SurveyResults`). So one admin screen mixes `adm-*` CSS classes with the old
inline-style system, and neither tree can be deleted.
**Dead files:** `pages/admin/SetupView.tsx` (170 lines, imported by nothing — `admin2/SetupPage.tsx`
re-implemented it), `admin2/Placeholder.tsx` (all nine nav routes now render real pages),
`types/domain.ts:36-40` `ResetLinkEntry` (zero users). `/dev-chat` (`App.tsx:79-86`) is still routed
and self-labelled "Delete once Batch B mounts ChatPanel for real".

**9.2 — The interview slice breaks the one hard architecture rule.**
`services/interview_context.py:173-181` takes three **concrete services**
(`SurveyService`, `MaturityService`, `LearningService`); `interview_service.py:70-79` then takes
`InterviewContextService` — two levels of service→service composition, wired in
`core/dependencies/interview.py:42-59`, used by both `routers/interview.py` and `routers/chat.py:107`.
The same codebase refuses this everywhere else, explicitly: `admin_user_service.py:30-32` ("services
never call other services"), `content_improvement_service.py:602-604` (same phrase), and
`core/attention.py` + `core/constants.py:advance_level` exist *specifically* to avoid it.
**Decide:** extract the briefing into a pure helper taking pre-fetched rows (the `attention_for`
pattern), or amend `python-be-architecture.md` to sanction composer services. Code and spec currently
contradict, and the next agent will copy whichever it reads first.

**9.3 — Email dispatch still lives in the router** (prior 4.2, now well-commented as the deliberate
seam forced by 9.2's rule, but still ~60 lines of use-case logic at the HTTP edge, copied across three
endpoints + the bulk loop): `routers/admin_users.py:89-117,161,227,290,325-334`. Either document it as
the sanctioned orchestration point or introduce a `NotificationService` composed at the DI layer.

**9.4 — Duplication.** `_require_non_blank` copy-defined 3× (`schemas/admin_content.py:22`,
`admin_org.py:25`, `admin_users.py:38` — prior 4.6); the `module_level` map construction now
copy-defined 3× (`maturity_service.py:56-61`, `admin_user_service.py:80-86`,
`dashboard_service.py:91-97` — prior 4.3's fix went halfway: the ladder walk was shared, the map build
wasn't), plus `dashboard_service.py:109-157` re-implements `admin_user_service.py:91-128`'s enrichment
loop ("the accepted price of services never call services"). Two response-conversion styles persist
(`me.py:29-30`/`survey.py` raw-ORM + `response_model` vs `model_validate` elsewhere — prior 4.5).
`admin2/api.ts` is now **1158 lines** (every admin feature's hooks) and `repositories/base.py` **807**
(all 14 ABCs) — both merge-conflict magnets for two-author work.

**9.5 — Prompt slice skips the abstract-repository contract.** `services/prompt_service.py:12,67`
types against the **concrete** `PromptRepository`; there is no `AbstractPromptRepository` in
`repositories/base.py`, unlike all 14 others.

**9.6 — Auth routers still aren't try/except-free** (prior 4.4): `routers/auth.py:76,89,111,138`,
`routers/auth_entra.py:131,137,146,171` — the `AuthError` family still has no `main.py` handler.
Partly justified (WWW-Authenticate headers, Entra 302s), still undocumented as a deviation.
**9.7 —** `routers/chat.py:173-178` hand-catches `NotFoundError`→404 that `main.py:244-246` already
handles; `require_ai_surface` reads `settings[kind]` while `require_interview_surface` uses
`.get("interview", False)`. **9.8 —** Two bare-array list responses
(`routers/admin_content.py:36,43-46`) vs wrapped objects everywhere else.

**9.9 — Dependency & config nits.** `anthropic` is **unpinned** *and* declared in the `prod` extra
while being a hard top-level import of `src` (`services/llm_service.py:7`), so the app cannot start
from a plain `uv sync --extra dev` and a future re-lock could pull a breaking major — the exact class
of problem prior 11.2 fixed for ACS. `httpx~=0.28` is declared in both main and dev (prior 11.3);
`aiosqlite~=0.20` is dead weight (the suite is PG-only); `LlmSettings.provider`
(`core/configs/llm.py:18`) is required config nothing reads (`get_llm_service` always builds
`AnthropicLlmClient`).

**9.10 — Quality gates aren't clean repo-wide.** `src/` and `tests/` are ruff-clean, but `scripts/`
carries all **48** ruff violations (E501/F401/I001/E741…) and 15 of the 24 `ty` diagnostics
(unresolved sibling imports in `scripts/content_qa`); `src/services/interview_service.py` fails
`ruff format --check`; real `ty` items in `src/`: `content_improvement_service.py:317`
(`BaseException` vs `Exception`), `core/dependencies/email.py:23`, `routers/auth.py:119`,
`routers/admin_email_templates.py:44`, plus 2 stale `# ty: ignore`s.

**9.11 — Admin is global, and privileged actions leave no audit trail.**
`core/dependencies/auth.py:86-91` checks role equality only; every admin router takes `project_id` as
a **filter**, not a constraint (`admin_users.py:123`, `admin_dashboard.py:25`), so any admin of any
project can read and mutate every project's users, surveys, feedback, templates and system prompts
(4 companies / 5 projects in the baseline). Compounding: `POST /api/admin/users/{id}/reset-link` with
`send_email: false` returns a working reset link and never notifies the user
(`admin_users.py:289-306`), and there is no audit table among the 14 model modules (only bulk invite
logs anything, `:243`). **Decide:** whether admin should be project-scoped; independently, add an
append-only audit row for reset-link issuance, role change, user delete, prompt edit, proposal
approval.

**9.12 — PII in logs** (prior 7.3d, unchanged): `email_service.py:53` (recipient),
`entra_service.py:136,140,152` (user email + Entra oid) at info/warning, landing in Log Analytics.

**9.13 — Docs drift.** CLAUDE.md contradicts itself on load-bearing facts: the feature index (:73-74)
says the admin redesign is "NOT merged to `main`, NOT deployed" while its own deploy log (:274-300)
records it live 2026-07-27; :123 says "`interview` has no live endpoint yet, so nothing to gate there"
while :307-309 and `routers/interview.py` say otherwise. `docs/design/design-backend.md` still
describes a "29-endpoint contract" against ~86 today. For a team of non-programmers the doc *is* the
operating manual.

---

## Prior-audit scorecard (2026-07-09 → today)

**Fixed (verified in code):** 1.1 bcrypt on the event loop (`user_service.py:34,36,42` threadpooled,
dummy-hash timing equalization retained) · 2.1 admin-users N+1 (batched
`assigned_lesson_counts_by_module_for_users`, `last_used_by_user`, `latest_completion_by_user`,
`user_ids_with_survey`; `_effective_maturity_map` now takes pre-fetched maps) · 2.3
`lesson_progress.lesson_id` index (migration `e1f2a3b4c5d6`) · 3.1 token-consume TOCTOU (conditional
UPDATE + `rowcount==1` honoured) · 3.2a refresh-rotation race (atomic `revoke`, "Rotation must win
exactly once") · 4.1 service→service in `AdminUserService` (repositories-only ctor, seam documented,
routers mint tokens) · 5 dead code (`Base.to_dict`, `next_level` in `__all__`) · 6.1 duplicate
LearningPath page + ModulePopup (deleted 2026-07-09; one DAG, one zoom site, correctly compensated) ·
6.2 `loadProjectData` cancellation (Admin.tsx gone; react-query with `cancelQueries` in every
optimistic `onMutate`) · 6.3 inline styles rebuilt per render (moot) · 7.3a JWT secret min-length
validator (≥32) · 9.1 `migrate_supabase_to_azure.py` TRUNCATE (now requires
`--i-understand-this-truncates-prod` **and** refuses if any `users.password_set=true`) · 9.2
`sync_content_from_supabase.py --apply` (refuses when a `General II` track exists) · 11.1 silent
SQLite default (defaults to POSTGRESQL, raises on missing password) · 11.2 unbounded ACS dep
(`~=1.1`) · plus frontend Theme-5 items (QuizBlock CustomEvent, unused domain aliases, 3 Spinner
copies).

**Partially fixed:** 2.4 pagination (params + scoped assignment maps landed; slicing still in Python
after a full fetch) · 4.3 effective-maturity duplication (ladder walk shared; map build now 3×) ·
7.3c CSP/limiter (`object-src` moot; `base-uri`/`form-action` and store eviction still open).

**Still present:** 2.2 `/learning/graph` duplicate queries · 2.5 survey multi-transaction write
(**and its retry-safety mitigation regressed**) · 2.6 minor query cleanups · 3.2b refresh reuse
detection · 4.2 email logic in router (now sanctioned) · 4.4 auth routers not try/except-free · 4.5
two response-conversion styles · 4.6 `_require_non_blank` ×3 · 6.4 MDX reparse + suppressed deps ·
7.1 Swagger in prod · 7.2 `forwarded_allow_ips` · 7.3b refresh/login rate limits · 7.3d PII in logs ·
7.3e `renderInline` allowlist (**risk raised** — now AI-fed) · 8.1 localStorage tokens (accepted;
mitigations verified — zero `dangerouslySetInnerHTML` in the tree) · 8.2 `?edit=true` · 10.1
prerequisite cycles · 10.2a-d schema nits.

**11.2's lesson did not stick:** the same unbounded-dependency mistake recurred with `anthropic`
(9.9).

---

## Confirmed-clean areas (checked, no action)

**Authorization.** The iron rule holds: all 20 routers / 82 route decorators read; no endpoint outside
`/api/admin/*` accepts a user identifier from body, path or query. Every admin router is guarded
(router-level `dependencies=[Depends(require_admin)]`, per-route on the two mixed routers
`admin_content`/`admin_media`); none of the new routers is unguarded. Role escalation via token is
impossible by design — `create_access_token` carries no role claim, `get_current_user` reloads the row
every request, so a demotion takes effect on the next request. No mass assignment: every request
schema is explicit-field Pydantic; the two `setattr` loops receive only
`model_dump(exclude_unset=True)` from schemas with no `status`/ownership fields; `RoleUpdateRequest`
is a `Literal`. Chat/conversation ownership IDOR is closed on both read paths (the gap is `kind`, 2.1).

**Injection.** No raw SQL in application code — every `text()` is a column `server_default`; all
queries are ORM constructs with bound parameters; `hide_parameters=True`. Email templates are the
best-hardened corner: `MarkdownIt("commonmark", {"html": False})`, Markdown-escaped token values,
URL tokens as autolinks via an explicit allowlist, `validate_template` rejecting unknown tokens at
save time. CSV invite parsing: 1 MiB cap enforced twice, 200-row cap, XLSX/OLE magic-byte detection,
BOM handling, delimiter sniffing, per-row error isolation, never persisted. Media upload: content-type
allowlist *before* reading bytes (415 first), extensions derived from content-type never the client
filename, SVG deliberately excluded, size checked against the parser's own byte count, blob names
`{kind}s/{uuid4().hex}{ext}`, streamed off spool, `overwrite=False`. Frontend XSS surface is small —
zero `dangerouslySetInnerHTML`/`innerHTML`/`eval`/`document.write`; AI output renders as plain JSX text
nodes. SPA catch-all is traversal-safe (`is_relative_to`), unknown `/api/*` 404s as JSON.

**Auth flows.** HS256 pinned on decode, audience + issuer verified, `require: [exp, iat, sub]`, and a
`typ` discriminator checked symmetrically so an access token can never stand in for Entra state.
bcrypt with per-password salt, `max_length=72` (bcrypt truncation), threadpooled both ways. Opaque
tokens: 256-bit, stored only as SHA-256, purpose-allowlisted so a leaked Entra login code can never
reach set-password. Set-password revokes all other tokens *and* sessions. Invite minting is admin-only.
Entra OIDC is textbook: PKCE S256, state + nonce, signed short-lived state in an HttpOnly path-scoped
SameSite=Lax cookie (Secure in prod), `compare_digest`, redirect_uri from config only, one-time code
in the URL **fragment**, failures 302 to a friendly error. Frontend refresh is single-flight with
`/api/auth/*` exempted from the 401-retry path.

**Secrets.** No committed secrets: one env-shaped tracked file (`backend/.env.local.example`,
placeholders only); no `sk-ant-*`, no live `AccountKey=`, no JWT anywhere. `.dockerignore` excludes
`**/.env` first, lists every dir bare *and* with `/**` (az matcher bug), with a targeted
`!backend/prompts/**` re-include. `infra/containerapp.yaml` is a placeholder template; every secret is
a `secretRef`; `deploy-initial.ps1` mints a fresh prod JWT secret and cleans up in a `finally`.
**The frontend bundles nothing** — zero `import.meta.env`/`VITE_` references; the API client is
same-origin relative. Docker runs as non-root `appuser`.

**Database.** 17 migrations, linear, single head, every downgrade implemented and data-aware (e.g.
`e2f3a4b5c6d7` demotes `user+` rows before narrowing the CHECK); the one documented re-parent leaves
no second head; no data migration touches a large table. Models match migrations column-for-column
and CHECK-for-CHECK on every spot-checked table. FK `ondelete` design is coherent throughout (content
tree CASCADE, `users.company_id` RESTRICT, `users.project_id` SET NULL, audit columns SET NULL); no
orphan paths. CHECK/UNIQUE coverage is broad (role, maturity, track_type, token purpose, feedback +
AI-suggested status, proposal/calibration status, conversation kind, message role, per-project
uniqueness). Concurrency-safe writes where it matters: atomic token consume + session revoke, ON
CONFLICT upserts for assignments/progress/settings/templates/prompts, single-transaction module
shift-and-insert. Engine: `pool_pre_ping`, session-per-request via DI, engine owned by lifespan, no
leaked sessions, echo off. Alembic env uses the owner role + NullPool with `%`-escaping.

**Async & AI layer.** All repositories async; ACS email, PyJWKClient, blob upload and bcrypt all
threadpooled; `httpx.AsyncClient` with a 10 s timeout for Entra; the one background task is guarded,
logged and cancelled on shutdown; chat disconnects persist partial replies under `asyncio.shield`;
content-improvement drafts run concurrently via `gather(return_exceptions=True)` with DB writes kept
sequential on the shared session. No `time.sleep`, no sync `requests`, no `print` in `src`.
`is_transient_provider_error` is deliberately narrow with a written rationale; the deferred/failed/
not_queued accounting is honest by construction; triage has per-item timeout + run budget + attempt
stamping so no row can wedge the queue. `max_tokens` is capped on every call path; history windowed
at 20; input capped at 4000 chars; admin batches capped at 3 lessons. Prompt editing is admin-only
over a closed `KNOWN_PROMPTS` allowlist with required-token validation. The Anthropic key is
`SecretStr` in an `lru_cache`'d client, never logged or returned; no AI logger call emits prompt
content or responses. The content pipeline is genuinely human-gated — drafts land `pending`, approval
re-validates and refuses to blank a lesson, triage only writes `ai_*` columns. Prompt-injection
defenses (DATA-not-instructions envelopes) exist on the playbook, content-improvement and triage
paths.

**Backups.** Separate image, managed identity (no keys in the job), `pg_dump -Fc --compress=9` +
globals, verify-before-upload (size floor + `TABLE DATA` count), `overwrite=False`, and a prune that
**cannot** touch lesson media (regex-anchored on the dump-artifact name, "unrecognised → leave alone",
listing scoped to `ai-enablement-hub/`), unit-tested, with a runbook that matches the code. One
nuance: `restore.py:78-88` has no `--clean`/`--create`, so a whole-DB restore needs an empty target.

**Hygiene.** 866 backend test functions across 93 files (≈1:1 unit/integration), **zero** skips or
xfails, tests LoC (17.3k) exceeding src LoC (14.7k), including an authz sweep over every endpoint ×
auth level and dedicated component-lock/AI-surface tests. Zero TODO/FIXME in `src`. `prompts/` matches
the `KNOWN_PROMPTS` registry exactly. Frontend: zero `any`, the `RENDERERS`/`EDITORS` exhaustive-map
pattern still compiler-enforced over the 12-member union, load-bearing `useCallback` identities intact
with their warning comments, `let cancelled` in every learner fetch effect, every listener/timeout
cleaned up, optimistic-update rollback correctness verified including the rapid-double-toggle fix,
zoom compensation applied at both `getBoundingClientRect` sites, App.tsx routes matching `nav.ts` 1:1.

**Explicitly unverified** (not determinable statically): whether the prod Anthropic key is capped;
whether the dev JWT secret and storage key were rotated; live Container Apps secret values; ACA
revision-mode behaviour on a failed migration; runtime log visibility; actual test coverage
percentage. Nothing was executed.

---

## Verdict

For a system built almost entirely by AI agents under non-programmer direction, this is a
**disciplined, coherent codebase** — the dangerous seams (token refresh, optimistic cache updates, the
JSONB content boundary, SSE streaming, media SAS) are not merely correct but annotated with *why*
they're shaped that way, and the previous audit's debt was largely paid down properly rather than
papered over. The modular goal holds on the backend and has strengthened; the frontend's one real
structural break is the admin/admin2 straddle.

The work that matters most next is **not** more code review. It is the safety net around the code:
a dev database so development can't touch production, a spend cap so AI usage can't run away, a
dirty-tree guard and CI so nothing unreviewed ships, and one smoke test so the growing
never-browser-verified surface stops growing. After that, the code items in Batches 2, 3, 6, 7 and 8
are each a small, well-scoped PR.
