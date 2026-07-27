# Feedback-driven lesson content improvement

**Date:** 2026-07-27
**Author:** Matthias + Claude (brainstormed)
**Status:** design, awaiting review before planning

## Purpose

Turn learner feedback on lessons into concrete, human-approved content
improvements, with the LLM doing the reading and drafting and an admin making
every publish decision.

Two AI touchpoints, both gated by a human:

1. **AI-assisted triage** — when feedback comes in, an agent reads it against
   the lesson it targets and pre-fills a *suggested* accept/dismiss + a
   one-line reason, so the admin confirms a recommendation instead of starting
   from a blank queue.
2. **Content improvement agent** — for each lesson that has *accepted*
   feedback, an agent reads the current lesson content plus that feedback and
   proposes a revised version (reworded and/or restructured). The proposal is
   stored as a draft and shown to an admin as a block-by-block diff (old vs.
   new); the admin approves (apply to the live lesson) or rejects (discard).

This is a **pipeline, not a closed loop** — there is no impact measurement or
automatic re-iteration. The name "feedback loop" refers to the human workflow
(feedback → improvement → publish), not a control loop.

## Scope

**In (v1):**

- Triage suggestions on `new` feedback (suggested disposition + rationale).
- A content improvement agent that proposes full-lesson `content_blocks`
  revisions for lessons with accepted, not-yet-incorporated feedback.
- The agent may change **both wording and layout** (reword/expand text, change
  block types, split/merge/reorder blocks) — see Decisions.
- A draft store for proposals + an admin review UI (block-by-block diff,
  approve/reject) as a new `admin2` section.
- Admin-triggered runs ("Run improvement pass"); no scheduler in v1.

**Out (v1):**

- **Internet research branch** — dropped. The signal is user feedback; a
  research agent is the highest-risk, least-obvious-value input and is
  explicitly deferred (would need its own review gate + a search provider +
  citation handling if it ever returns).
- **A separate "tone of voice" agent** — folded into the content agent's
  system prompt (house style is a section of the prompt, not a second LLM
  pass).
- **Loop closure / impact measurement** (did the change reduce negative
  feedback / improve completion?) — not built.
- **A real scheduler / weekly cron** — v1 is admin-triggered; a weekly
  in-process task is a documented later add (see Deferred).
- **Per-block substance guarantees** beyond structural validation — the admin
  diff review is the correctness gate, not an automated fact-checker.

## Dependencies & sequencing (read first)

- **This feature builds on the AI-chat foundation (Batch A of
  `docs/ai-agents-plan.md`), which is already merged to `main`** (verified
  2026-07-27: `main` and `feature/ai-chat-foundation` both point at commit
  `12213a6`, ahead/behind `0 0`; the `LlmClient` seam, `chat_service.py`,
  `core/configs/llm.py`, the chat router, and migration `12bf5f54a1e4` are all
  on `main`). This work therefore branches off `main` normally — no
  cross-branch dependency. It reuses `LlmSettings` (`core/configs/llm.py`), the
  `get_llm_service` DI provider (`core/dependencies/llm.py`), the `anthropic`
  dependency, and the `LlmClient` seam (`services/llm_service.py`).
- **The LLM seam is streaming-text-only today.** `LlmClient.stream_reply`
  streams free text; there is no non-streaming or structured-output method,
  and no `tool_use` path (`services/llm_service.py`). Both agents here need
  *structured* output. This design **extends the seam** (see "LLM seam
  extension") — that extension is part of this feature's work.
- **Single-replica constraint.** The container app is pinned `min=max=1`
  (rate limiter + the auth-cleanup loop are in-process). Batch runs and any
  future scheduled task run in that single process; if the app ever scales
  out, a scheduled run needs a leader-lock. In-process is fine for v1.

## Current behaviour (confirmed by reading the code)

- **Feedback** — `backend/src/db/models/feedback.py::Feedback`:
  `id`, `user_id` FK, `lesson_id` FK (hard link to the lesson), `message`,
  `status` (`'new'|'accepted'|'dismissed'`, check-constrained), `reviewed_at`,
  `reviewed_by` FK, `created_at`. Triage columns came from migration
  `c6d7e8f9a0b1`. Triage is a single `PATCH /api/admin/feedback/{id}` setting
  `status` (`routers/admin_feedback.py` → `services/feedback_service.py::set_status`,
  which stamps/clears `reviewed_by`/`reviewed_at`). The admin list query
  (`repositories/feedback_repository.py::_admin_query`) already resolves
  lesson → module → track context.
- **Lesson content** — `backend/src/db/models/learning.py::Lesson.content_blocks`
  is a single `JSONB` column, treated as **opaque `list[Any]`** on the backend
  (schemas in `schemas/admin_content.py` type it as `list[dict[str, Any]]`).
  The block union is only enforced on the frontend
  (`frontend/src/types/contentBlocks.ts`: `heading`, `paragraph`, `callout`,
  `kicker`, `card_group`, `quiz`, `question`, `whitespace`, `interactive`
  [`sort`/`predict`/`spot_the_flaw`], `try_it_yourself`, `image`, `video`).
- **Editing content** — `PATCH /api/admin/lessons/{id}`
  (`routers/admin_content.py` → `services/content_service.py::update_lesson` →
  `repositories/content_repository.py::update_lesson`) does a **whole-array
  overwrite** of `content_blocks`, writing straight to the live row. There is
  **no draft / version / staging concept anywhere**. `update_lesson` runs
  `strip_ephemeral(...)` so image/video blocks persist only `blob_path`, never
  ephemeral SAS URLs (`services/media_blocks.py`).
- **Admin UI** — `frontend/src/pages/admin2/` is a routed shell
  (`AdminShell.tsx`) with sections registered in `nav.ts` + `App.tsx`, a
  `kit/` component library, and a TanStack Query data layer (`api.ts`). The
  existing `FeedbackPage.tsx` is the closest sibling to what we're adding.
  Endpoints not yet in the generated `schema.d.ts` go through `rawRequest<T>`.
- **Background work** — no scheduler / cron / `BackgroundTasks`. The only
  pattern is a hand-rolled asyncio task in `main.py::lifespan`
  (`_auth_cleanup_loop`, 24h interval). A future weekly run would copy that
  pattern.

## Decisions

- **Feedback-scoped, not catalog-wide.** A run only touches lessons that have
  at least one accepted feedback item not yet incorporated. No whole-catalog
  regeneration.
- **Consume accepted feedback only.** Triage stays the human gate for what's
  actionable; the content agent never reads `new` or `dismissed` feedback. AI
  triage only *suggests* a disposition — it never changes `status` itself.
- **Content + layout edits.** The agent may reword/expand text and restructure
  (change block types, split/merge/reorder). This is the useful option (it can
  act on "this was confusing" / "add an example"); the larger blast radius is
  covered by the mandatory admin diff-approval gate, which is also the agreed
  prompt-injection mitigation.
- **Propose a diff, never auto-publish.** Every content change is a stored
  proposal reviewed by an admin before it reaches the live lesson.
- **One content agent, house style in its prompt.** No separate tone pass.
- **Bias triage toward keeping feedback.** The triage agent leans
  `accept` / needs-review when uncertain, so its failure mode is a false
  *keep* (cheap: admin dismisses it) rather than a false *dismiss* (expensive:
  useful feedback silently never reaches the content agent). Its rationale is
  always shown so the human check is a 2-second read.
- **Admin-triggered, no scheduler (v1).** An admin clicks "Run improvement
  pass"; triage suggestions are generated lazily for `new` feedback lacking
  one. Weekly automation is deferred.
- **Draft store is net-new but small.** A single `lesson_content_proposals`
  table (below). Not a general content-versioning system — just enough to hold
  a proposed `content_blocks` array until a human decides.

## Design

### Data model changes

**1. Triage suggestion columns on `feedback`** (migration, additive; nullable
so existing rows are unaffected):

- `ai_suggested_status` `text` nullable — `'accepted'|'dismissed'` (the
  suggestion; never written to the real `status`).
- `ai_rationale` `text` nullable — one-line reason shown to the admin.
- `ai_suggested_at` `timestamptz` nullable — set when a suggestion is
  generated; `NULL` means "not yet suggested" (drives lazy generation).

**2. New `lesson_content_proposals` table** (migration):

- `id` UUID PK.
- `lesson_id` UUID FK → `lessons.id` ON DELETE CASCADE, indexed.
- `proposed_blocks` `JSONB` NOT NULL — the full proposed `content_blocks`
  array (same shape as `Lesson.content_blocks`).
- `base_blocks` `JSONB` NOT NULL — a snapshot of the lesson's `content_blocks`
  at generation time, so the review diff is stable even if the live lesson is
  edited meanwhile, and stale proposals can be detected.
- `source_feedback_ids` `JSONB` (array of UUIDs) NOT NULL — the accepted
  feedback rows that drove this proposal (for provenance + marking them
  incorporated on apply).
- `summary` `text` NOT NULL — the agent's short description of what it changed
  and why (surfaced in the review UI).
- `status` `text` NOT NULL default `'pending'` —
  `'pending'|'approved'|'rejected'|'superseded'`, check-constrained.
- `created_at` / `reviewed_at` `timestamptz`; `reviewed_by` UUID FK →
  `users.id` ON DELETE SET NULL.

"Not-yet-incorporated" feedback = accepted feedback whose id does not appear in
any `source_feedback_ids` of a `pending`/`approved` proposal for its lesson.
This keeps a run idempotent (re-running doesn't re-draft the same feedback) and
avoids a second status column on `feedback`.

### LLM seam extension (structured output)

Add a non-streaming, structured method to the `LlmClient` Protocol and its
`AnthropicLlmClient` implementation (`services/llm_service.py`):

- `complete_structured(*, system: str, prompt: str, schema: <json schema>,
  max_tokens: int) -> tuple[dict, LlmUsage]` — returns validated JSON matching
  `schema` plus token usage.
- Implemented for Anthropic via a **forced `tool_use`** call
  (`client.messages.create(..., tools=[{name, input_schema}],
  tool_choice={type:"tool", name})`), reading the tool-call input as the
  structured result. Anthropic has no native JSON mode; forced tool use is the
  supported path. This mirrors the seam discipline already in
  `docs/ai-agents-plan.md §7` (provider-agnostic Protocol; Anthropic is the
  only adapter).

This is a general capability (the interviewer surface in the agents plan will
also want structured extraction), so it belongs on the shared seam, not in this
feature's service.

### Component A — AI-assisted triage

A new `FeedbackTriageService` (or a method group on `FeedbackService`) that,
given a `new` feedback row lacking a suggestion:

1. Loads the target lesson's `content_blocks` (context) + the feedback message.
2. Calls `complete_structured` with a triage schema
   `{suggested_status: 'accepted'|'dismissed', rationale: string}` and a system
   prompt that defines "actionable feedback about this lesson's content" vs.
   "spam / off-topic / not about content", biased toward `accepted` when
   unsure. It may note likely duplicates of other feedback on the same lesson
   (dedupe is best-effort, not enforced).
3. Writes `ai_suggested_status`, `ai_rationale`, `ai_suggested_at`.

**Trigger:** lazy + admin-driven, not on the learner submit path (keeps a
learner's `POST /api/feedback` free of LLM latency/cost). When the admin opens
the Feedback queue (or clicks a "suggest triage" action), a new endpoint
generates suggestions for `new` items where `ai_suggested_at IS NULL`, bounded
per call. The `FeedbackPage` renders the suggestion + rationale as a hint on
each `new` card, with the existing Accept/Dismiss buttons pre-highlighted to
match the suggestion. The human still clicks.

**Endpoint:** `POST /api/admin/feedback/suggest-triage` (admin-only) → generates
+ returns updated rows; `AdminFeedbackOut` gains the three `ai_*` fields.

### Component B — Content improvement agent

A new `ContentImprovementService`:

1. **Select lessons:** all lessons with ≥1 accepted, not-yet-incorporated
   feedback item (join through the existing feedback → lesson relation).
   Bounded per run (a `max_lessons` cap; log when the cap truncates a run — no
   silent limiting).
2. **Per lesson:** build a prompt from the current `content_blocks` + the
   accepted feedback messages, call `complete_structured` with a schema
   `{proposed_blocks: <content_blocks array>, summary: string}`. System prompt
   carries: the house style, the allowed block types + their shapes, the
   content+layout mandate, and hard rules (see Guardrails).
3. **Validate** `proposed_blocks` (see below). On failure, skip the lesson and
   record the failure (no proposal); do not write malformed blocks.
4. **Store** a `lesson_content_proposals` row (`proposed_blocks`, `base_blocks`
   = the current live blocks, `source_feedback_ids`, `summary`,
   `status='pending'`).

**Trigger:** `POST /api/admin/content-improvement/run` (admin-only) kicks off a
pass. Given the single replica and a bounded lesson count, v1 runs it as an
in-process background task (asyncio, same pattern family as
`_auth_cleanup_loop`) and the admin polls a lightweight status, OR — if a run
is small enough — runs inline and returns the created proposal ids. The review
queue is the durable surface either way; the exact sync/async choice is an
implementation detail for the plan.

### content_blocks validation

Because the backend stores blocks as opaque JSONB, add a **block-shape
validator** (`services/content_blocks_validation.py` or similar) used at
proposal-creation time and again at apply time:

- Each block is a dict with a known `type` from the frontend union and the
  required fields for that type (mirrors `frontend/src/types/contentBlocks.ts`;
  keep the two in sync, documented).
- Reject unknown types, missing required fields, or malformed nested shapes
  (e.g. `quiz.questions[].correct` out of range).
- **Media rule:** the agent must not invent `image`/`video` blocks or alter
  existing ones' `blob_path`. Validation carries existing media blocks through
  unchanged and rejects any new/edited media locator. Apply still runs the
  existing `strip_ephemeral`.

This validator is the guard that a confused/injected model can't publish blocks
that break the learner renderer.

### Admin review UI (new `admin2` section)

Follow the `FeedbackPage` pattern exactly:

- `nav.ts`: add a `content-improvement` nav item (+ a `NavIconKey` + SVG in
  `AdminShell`).
- `App.tsx`: add `<Route path="content-improvement" element={<ContentImprovementPage/>}>`
  under the `/admin` shell.
- `api.ts`: `useProposals({status, page})` query + `useReviewProposal()`
  mutation (approve/reject), via `rawRequest` until `schema.d.ts` is
  regenerated; query key `['admin','content-improvements', ...]`.
- `ContentImprovementPage.tsx`: a queue of `pending` proposals (scoped via
  `useScope()`), each expandable to a **block-by-block diff** of `base_blocks`
  vs. `proposed_blocks` rendered as **plain text** (chat/agent output is
  untrusted — same rule as the admin conversation viewer in the agents plan),
  the agent's `summary`, and the linked feedback. Actions: **Approve** (apply)
  / **Reject** (discard). A "Run improvement pass" button triggers Component B.
- Optional sidebar badge (count of `pending`), mirroring `FeedbackNavBadge`.

A rendered rich-diff of `content_blocks` is a real piece of frontend work; v1
can start with a readable per-block textual diff and improve fidelity later.

### Applying an approved proposal

`POST /api/admin/content-improvement/{id}/review {decision: 'approve'|'reject'}`
(admin-only):

- **approve:** re-validate `proposed_blocks`; if `base_blocks` no longer
  matches the lesson's current `content_blocks`, mark the proposal
  `superseded` and refuse (the lesson changed under it — regenerate). Else
  write `proposed_blocks` to the lesson via the **existing**
  `ContentService.update_lesson` path (whole-array overwrite + `strip_ephemeral`),
  set the proposal `approved` (stamp `reviewed_by`/`reviewed_at`), and the
  `source_feedback_ids` become "incorporated" (they now appear in an
  `approved` proposal, so they drop out of future runs).
- **reject:** set `rejected` (+ reviewer stamp); the source feedback stays
  accepted and — because it's no longer covered by a `pending`/`approved`
  proposal — is eligible for a future run again. (If that causes churn, a
  later tweak can exclude rejected-source feedback; out of scope for v1.)

### Guardrails & safety

- **Human gate on every publish** — nothing reaches a live lesson without an
  admin approving the diff. This is the primary control and the agreed
  injection mitigation.
- **Structural validation** — malformed blocks never get stored/applied.
- **Media immutability** — the agent cannot add/alter image/video locators.
- **Bounded runs** — `max_lessons` per run; `max_tokens` per call; reuse the
  existing per-user rate-limit infrastructure (`core/ratelimit.py`) on the
  admin trigger endpoints. Model cost at internal volume is negligible (per
  `ai-agents-plan.md §8b`), but caps prevent a runaway pass.
- **Triage bias** — toward keeping feedback (false-keep over false-dismiss).
- **Feature-flagged** — the whole feature no-ops / 404s when `Settings.llm` is
  unconfigured (same all-or-nothing seam as chat, email, Entra).

## Testing

Backend (`uv run poe format && uv run poe lint && uv run poe test`):

- Authz matrix: the new `/api/admin/*` endpoints (suggest-triage, run,
  review, proposal list) reject non-admins — extend the existing endpoint × 3
  auth-levels matrix.
- LLM client stubbed (like the chat tests stub the seam): triage suggestion
  writes the three `ai_*` fields; content run creates a proposal with correct
  `source_feedback_ids` and `base_blocks` snapshot.
- Idempotency: a second run over the same accepted feedback creates no new
  proposal (feedback already covered by a `pending` proposal).
- Validation: a proposal with an unknown block type / missing field / a new
  media locator is rejected (no row / no apply).
- Apply: approve writes `proposed_blocks` to the lesson via `update_lesson`;
  stale `base_blocks` → `superseded` + refusal, lesson unchanged.
- Reject leaves the lesson unchanged and re-eligibilizes the feedback.
- Triage never mutates `feedback.status`.

Frontend (`npm run typecheck && npm run lint && npm run build`): the new page
follows `kit/` + TanStack patterns; manual browser check of the queue, diff
render, approve/reject, and the triage hints on the Feedback page.

## Success criteria

- An admin opens the Feedback queue and sees an AI-suggested accept/dismiss +
  reason on each new item; confirming is one click.
- An admin clicks "Run improvement pass" and, for each lesson with accepted
  feedback, gets a `pending` proposal showing a block-by-block old-vs-new diff
  and a summary of the change.
- Approving a proposal updates the live lesson's `content_blocks`; rejecting
  discards it; neither can publish malformed blocks or touch media locators.
- Re-running the pass does not re-draft feedback already covered by a proposal.
- The whole feature no-ops cleanly when `Settings.llm` is unset, and all
  backend checks + frontend typecheck/lint/build are green.

## Deferred / open

- **Weekly scheduled run** — an in-process `asyncio` task mirroring
  `_auth_cleanup_loop`, gated on the single-replica constraint (needs a
  leader-lock if the app ever scales out).
- **Model split** — v1 reuses the single configured `LLM__MODEL` for both
  agents. A cheaper tier for triage (Haiku) + a stronger tier for content
  (Sonnet/Opus) would mean an optional per-role model override on
  `LlmSettings` — deferred, ties into the same open question in
  `ai-agents-plan.md §10`.
- **Impact measurement / closing the loop** — deliberately out; revisit only
  if there's appetite to measure whether changes helped.
- **Per-project gating** — `ProjectAiSetting` / `require_ai_surface` already
  exist if this should be enabled per project later.
- **Richer diff rendering** — v1 is a readable per-block textual diff;
  higher-fidelity structural diffs can follow.
- **Internet research branch** — parked; would return only behind its own
  human gate + a search provider + citation handling.
