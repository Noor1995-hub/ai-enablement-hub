# Review Fixes — Master Plan (code + database)

> **For agentic workers:** REQUIRED SUB-SKILL: use superpowers:subagent-driven-development (recommended)
> or superpowers:executing-plans to execute the phase plans task-by-task. Steps use checkbox (`- [ ]`)
> syntax for tracking. **Do not execute this master file** — it is an index and an ordering contract.
> Execute the five phase plans in the order given in §4.

**Goal:** close every **code** and **database** finding of `CODE-REVIEW-2026-07-31.md` (this folder) in five
independently shippable phases, without changing any user-visible feature except the two deliberate
access-control tightenings called out in §6.

**Architecture:** each phase is a self-contained plan file with its own TDD tasks and its own commits;
phases are ordered so that no two consecutive phases rewrite the same file. All Alembic migrations live
in exactly one phase (Database) as a single linear chain off head `1cd2cc2d05a9`, so no executor can
create a second head. The frontend phase touches no backend file and may run in parallel with any
backend phase.

**Tech Stack:** FastAPI (Python 3.13, uv) · SQLAlchemy 2 async + asyncpg · Alembic · Azure Postgres ·
React 18.3.1 + TypeScript (Vite 6) · react-router v6 (`BrowserRouter`, **not** a data router) ·
openapi-fetch over a committed generated `schema.d.ts` · Anthropic API direct.

## Global Constraints

These apply to every task in every phase.

- **Backend layering is mandatory** (`python-be-architecture.md`): `routers/ → services/ →
  repositories/ → models`. **Services never call other services** — the one exception in the codebase
  today is the subject of a decision in §5.1, and until that is resolved no new service→service
  dependency may be introduced.
- **Backend verification gate:** `uv run poe format && uv run poe lint && uv run poe test`, run inside
  `backend/`. Migrations: `uv run poe upgrade`.
- **Frontend verification gate:** `npm run typecheck && npm run lint && npm run build`, run inside
  `frontend/`. **There is no frontend test framework** (no vitest, no playwright, zero `*.test.*`) and
  standing one up is out of scope here — every frontend task therefore also carries a concrete manual
  browser check.
- **Integration tests run against the shared remote `ai-enablement-hub-test` Azure PG database**, with
  the schema created per session from `Base.metadata`. Two consequences: a model change and its
  migration must agree or the tests stop resembling prod, and a second concurrent test run can
  interfere with the first.
- **Prod runs `alembic upgrade head` automatically on container start, before the port binds.** Every
  migration must be fast, additive, and must never lock a large table. A migration that raises blocks
  the whole release.
- **FastAPI deferred-annotation gotcha:** any type used in a *parameter* annotation (routers, DI
  providers in `core/dependencies/`) must be imported at runtime, never under `TYPE_CHECKING` — with
  deferred annotations an unresolvable name silently degrades the parameter to a required query
  param and every request 422s.
- **`api/schema.d.ts` is generated** by `npm run gen:api` against a running backend and is committed.
  Never hand-edit it. No task in this plan changes a wire contract (see §5.5), so no regeneration
  should be needed; if one becomes necessary, regenerate rather than patch.
- **Frontend invariants:** the app renders at CSS `zoom: 1.25` on `:root`, so any new rect-based
  positioning must divide by `getRectZoomFactor()` (`lib/uiZoom.ts`); the `useCallback` identities for
  `onQuizComplete` and `onLiveChange` in `LessonPage` must not become inline arrows (documented
  infinite-loop and stale-reset hazards); `types/contentBlocks.ts`'s union drives the exhaustive
  `RENDERERS`/`EDITORS` maps and a new block type must stay a compile error until registered;
  destructive actions use in-app confirmation UI, never `window.confirm`.
- **One commit per task**, and every task must leave the tree green and shippable. A phase may be
  stopped partway.

---

## 1. Scope

**In scope — code and database only.** Batches 2, 3, 6, 7, 8 and the code items of Batch 9 from
`CODE-REVIEW-2026-07-31.md`.

**Explicitly out of scope** (agreed: "way of working is next week"): the Anthropic spend cap, storage
and JWT key rotations, provisioning a dev database, CI / pre-commit / coverage enforcement, the
`deploy.ps1` dirty-tree guard, Playwright/E2E, logging and alerting configuration, PII removal from git
history, Docker base-image pinning, and CLAUDE.md / design-doc drift.

Two adjacent items **are** included because they are ordinary code changes: the unpinned `anthropic`
dependency (verified: `prod = ["httptools", "anthropic"]`, both unbounded, locked at 0.119.0 / 0.8.0 —
and because `services/llm_service.py` imports it at module level, `uv sync --extra dev` currently cannot
start the app), and making `ruff`/`ty` clean (the *fixes*, not the CI that would enforce them).

## 2. Phase plans

| # | Phase | File | Tasks | Effort |
|---|-------|------|-------|--------|
| A | Security hardening | [`2026-07-31-fix-security-hardening.md`](2026-07-31-fix-security-hardening.md) | 10 | 8×S, 2×M |
| B | AI-layer resilience | [`2026-07-31-fix-ai-resilience.md`](2026-07-31-fix-ai-resilience.md) | 9 | 6×S, 3×M |
| C | Database robustness | [`2026-07-31-fix-database-robustness.md`](2026-07-31-fix-database-robustness.md) | 14 | 7×S, 5×M, 1×L, 1 decision |
| D | Backend consistency | [`2026-07-31-fix-backend-consistency.md`](2026-07-31-fix-backend-consistency.md) | 10 | 6×S, 3×M, 1 decision |
| E | Frontend robustness | [`2026-07-31-fix-frontend-robustness.md`](2026-07-31-fix-frontend-robustness.md) | 20 (+2 optional) | 9×S, 9×M, 2×L optional |

**63 mandatory tasks + 2 optional (E11b, E21). This is 3–4 days of work, not one day** — see §7 for a
realistic same-day slice. (Verified counts: A 10 · B 9 · C 14 · D 10 · E 22 headings incl. the two
optional ones. D9/D10 additionally drop out if decision §5.1 lands as option (b).)

## 3. Finding → task coverage

Every in-scope finding is claimed by exactly one phase.

| Finding | Phase · task |
|---|---|
| 2.1 chat `kind` check | A2 |
| 2.2 interview component gate | A6 |
| 2.3 Swagger in prod | A5 |
| 2.4 catch-all 500 handler | B1 |
| 2.5 refresh reuse detection | A3 |
| 2.6 + 7.3 rate limiting & store eviction | B2, B3, B4, B5, B6 |
| 2.7 URL-scheme allowlist | A7, A8 (backend) · E3 (frontend) |
| 2.8 briefing DATA envelope | A4 |
| 2.9 CSP + `?edit=true` | A1 (CSP) · E2 (edit gate) |
| Batch 3 lesson access + SAS | A9, A10 |
| 6.1a survey guard regression | C1 |
| 6.1b unit-of-work seam | C13 |
| 6.2 FK indexes | C2 |
| 6.3 messages tiebreaker | C3 |
| 6.4 prompts / ai-settings drift | C8 |
| 6.5 concurrency guards | C6, C9, C10, C11 |
| 6.6 prerequisite cycles | C12 |
| 6.7 dialogue retention | C — decision only (§5.4) |
| 6.8 admin lesson validation | C14 (decision, §5.2) |
| 6.9 query efficiency | C4, C5, C6, C7 |
| 7.1 interview timeouts | B7 |
| 7.2 transient errors + SSE error frame | B8, B9 |
| 8.1 error boundary | E9 |
| 8.2 typed-client swap | E13–E18 |
| 8.3 unsaved-changes guard | E11 (+E11b optional) |
| 8.4 code-splitting | E10 |
| 8.5 matrix memoization | E5 |
| 8.6 MDX reparse | E1 |
| 8.7 assorted frontend | E2, E4, E6, E7, E8, E12 |
| 9.1 dead code + admin straddle | E19, E20 (+E21 optional) |
| 9.2 service→service | D1 (decision), D9, D10 |
| 9.3 email-in-router | D — decision only (§5.6) |
| 9.4 duplication | D2, D3 |
| 9.5 prompt repository ABC | D4 |
| 9.7 chat try/except + gate read | D5 |
| 9.8 bare-array responses | D — decision only (§5.5) |
| 9.9 dependency hygiene | D7 |
| 9.10 ruff / ty clean | D8 |
| 9.12 PII in logs | D6 |

**Deliberately not planned** (state these rather than let them go quiet):
- **9.11 audit log + project-scoped admin** — needs a product decision *and* a new table; carry to the
  way-of-working session. Today any admin can silently mint a reset link for any user in any project.
- **9.6 auth routers not try/except-free** — the deviation is justified (WWW-Authenticate headers, Entra
  302s) but undocumented; fold the note into D1's spec edit if that decision goes ahead.
- **Deferred follow-ups named inside the phase plans:** Postgres-backed rate-limit counters (needs a
  migration, entangled with the single-replica decision), frontend rendering of B9's new `error` SSE
  frame, `/api/interview/*` router tests beyond the ones A6 introduces, the four-styling-system
  convergence, and the suppressed `exhaustive-deps` in `LearningPathNew.tsx`.

## 4. Execution order and file conflicts

**Order: A → B → C → D.** E (frontend) may run in parallel with any of them.

The order is driven by shared files, not by importance:

| File | Touched by | Consequence |
|---|---|---|
| `src/main.py` | A1, A5 (CSP, docs) · B1 (500 handler) | A before B |
| `src/services/interview_context.py` | A4 (envelope) · D9, D10 (restructure/delete) | **A before D**, or the envelope is written into a file D deletes |
| `src/services/interview_service.py` | B7, B8 (timeouts, 529) · D8 (reformat), D9/D10 (restructure) | **B before D** |
| `src/services/chat_service.py` | A2 (`kind`) · B9 (SSE error frame) · D5 | A → B → D |
| `src/services/learning_service.py` | A9 (lesson gate) · C4, C6 (graph dedupe, scoping) | A before C |
| `src/services/maturity_service.py` | C4 (graph dedupe) · D3 (`module_level_map`) | C before D |
| `src/services/survey_service.py` | C1, C9, C13 | within C |
| `frontend/src/pages/LessonPage.tsx` | E1, E2 | within E |

**One cross-stack sequencing note:** A9 makes lesson fetches able to return **403**, and E2 is what
stops the lesson page rendering every failure as "Lesson not found". Land E2 before or with A9's
deploy, or an out-of-level learner sees a misleading message.

## 5. Decisions needed from Matthias

### Blocking — a task cannot start without the answer

**5.1 · The interview slice's service→service dependency (gates D9, D10).**
`InterviewContextService` takes three concrete services, which the rest of the codebase refuses on
principle (`admin_user_service.py` and `content_improvement_service.py` both say "services never call
other services" in comments, and `core/attention.py` + `advance_level` exist specifically to avoid it).
Options: **(a)** extract the briefing into a pure render module + a shared
`gather_briefing_inputs(...)` free function — cost M, and it also cuts the interview chat turn from
**6 queries to 4** (one read currently runs twice, and the survey row already carries what a second
repo call returns); or **(b)** amend `python-be-architecture.md` to sanction "composer services" —
~15 lines, zero code, but it converts the one hard rule into a judgement call.
**Recommendation: (a).** D1 costs both; D2–D8 proceed either way.

**5.2 · Admin lesson-write validation (gates C14).**
Human lesson saves bypass `validate_content_blocks` while AI-proposal saves are gated by it.
**(A)** document the asymmetry and add only a 1 MiB request ceiling (S), or **(B)** validate but reject
only *regressions* against the stored blocks (M). This is blocking because **66 of 91 live lessons fail
the strict validator** — a naive hard gate would make real lessons unsavable.
**Recommendation: (A) now, (B) after the nested-id backfill.** Also confirm 1 MiB is the right ceiling.

**5.3 · `sort_order` uniqueness (gates C11 and its conditional migration).**
Could not be proven safe statically (creation uses `max+1`, reorder writes 0-based indices, and two
past migrations planted fixed values), so C11 ships a **read-only pre-flight query** instead of a
migration. Even if it comes back clean, the constraint must be `DEFERRABLE INITIALLY DEFERRED` because
`reorder_lessons` passes through colliding intermediate states. Need a go/no-go.

**5.4 · Lesson access-control semantics (gates A9 — the largest single behaviour change).**
Access = admin/`user+` **OR** Introduction track **OR** explicitly assigned **OR** track at/below the
learner's effective maturity. So an *assigned but above-level* lesson stays reachable (an admin's grant
outranks the maturity calculation) and an *unassigned but at/below-level* lesson stays reachable
(below-level free review shipped 2026-07-20). Only "unassigned **and** above level" starts returning
403. A learner with no completed assessment keeps their assigned lessons plus Introduction.
**Net: nobody loses access to anything the learning path currently offers them.** Confirm that is the
intent rather than a stricter "assigned only" rule. Note A9 rewrites six existing tests that encode
today's accepted behaviour (2 authz-matrix rows + 4 in `test_lesson_media_stamping.py`, one of which
says so in its name).

**5.5 · Unsaved-changes scope (gates E11b).**
`useBlocker` **cannot** be used as originally specified: react-router 6.30.4 implements it via
`useDataRouterContext`, which throws unless the app is mounted by `createBrowserRouter`, and
[`App.tsx:97`](frontend/src/App.tsx#L97) uses `<BrowserRouter>` (verified). So E11 ships a
`beforeunload` guard — covering tab close, reload and leaving the site — while in-app sidebar/back
navigation stays unguarded. E11b sketches the data-router migration that would close that gap, but it
re-declares every route, redirect and auth gate in an app with no automated frontend tests.
**Recommendation: ship E11 only.**

### Confirm-or-drop — optional tasks, each independently removable

**5.6 ·** A10 halves the media SAS TTL (48 h → 26 h): media URLs rotate daily instead of every other
day, slightly more cache misses. Drop if unwanted.
**5.7 ·** A8 applies the new URL-scheme check to admin lesson PATCH saves — narrow (scheme only, never
the structural validator) but it is a new way an admin save can 400.
**5.8 ·** E21 ports the four legacy-styled admin surfaces to `adm-*` classes. **Recommendation: defer**
— E20 already deletes `pages/admin/`; E21 only removes the leftover inline-style dictionary, is purely
visual, and is exactly the class of change no check in this plan can catch.
**5.9 ·** D — leave the two bare-array list responses (`routers/admin_content.py`) as they are and
write the wrapped-object convention into the spec instead. Changing them is a wire-contract change
across 5 files with a cached-bundle window where a stale SPA hits `data.map is not a function`.
**Recommendation: leave alone.**
**5.10 ·** D — document the router as the sanctioned place for email orchestration (rather than
building a `NotificationService`, which is only legal if 5.1 lands as **(b)**).
**Recommendation: document.**
**5.11 ·** C — dialogue retention: "how long may we keep a learner's chat/interview transcript?" is a
product/legal call, not code. **Recommendation:** cap the history read now, decide the window before
the `chatbot` surface is enabled for any project.

### For information — deviations already made deliberately

**5.12 ·** C8's `prompts.kind` CHECK means a future prompt kind needs a migration alongside its
`KNOWN_PROMPTS` entry — the same cost every other enum in the schema already pays.
*Superseded 2026-09-23: C8 now drops `prompts` instead (prompts are git-only).*
**5.13 ·** D7 **deletes** the unused `LlmSettings.provider` rather than tightening it to
`Literal["anthropic"]`: `infra/containerapp.yaml` carries no `LLM__*` keys, so the live value and its
casing are unverified and a `Literal` would turn an unknown prod string into a startup failure.
Deletion is inert (`extra="ignore"`).
**5.14 ·** E7 does **not** use `kit/ConfirmButton` for `ModulePanel`'s lesson delete — that component is
styled by `adm-*` classes from `styles/admin.css`, which only loads inside the admin shell (and after
E10 lives in the admin-only chunk), so on the learner-facing `/learning` page it would render
unstyled. It reuses ModulePanel's own two-step pattern instead.

## 6. Pre-deploy gates

Both are **data** conditions, not code — check them before the phase that needs them reaches prod.

1. **A6 will 403 a live feature.** `interview` defaults to `locked=True` in
   `core/constants.py DEFAULT_LOCKED`, so every live project currently offering the interview needs a
   `project_component_settings` row with `locked=false, hidden=false` **before** A6 deploys, or its
   learners lose the interview. Verify per project first.
2. **A4's envelope will not reach an overridden prompt.** Prompts are DB-overridable since 2026-07-30;
   a saved `interview` override in the `prompts` table keeps its old text. Reset or re-save that prompt
   after A4 deploys. *Resolved 2026-09-23: prompts are git-only (PR #16) — no override can exist, so
   this check is no longer needed.*
3. **C10 may find duplicate interview conversations.** The plan deliberately refuses to auto-delete —
   each row is a real learner's transcript. If the pre-flight returns rows, it stops for a decision on
   which one survives.

## 7. Suggested same-day slice

If today is one working day, do **Phase A + Phase B** (19 tasks, mostly Small): that is every security
fix, the lesson-access gate, the AI timeout/529/SSE resilience, and all rate limiting — i.e. the entire
risk-reducing core. Answer 5.4 first, since A9 is the one task in that slice with real behaviour change.

Then: **C** (database, needs 5.2 + 5.3 answered), **D** (needs 5.1 answered), **E** (frontend, needs
5.5 answered — and can be run in parallel by a second worker at any point, since it shares no files
with A–D).
