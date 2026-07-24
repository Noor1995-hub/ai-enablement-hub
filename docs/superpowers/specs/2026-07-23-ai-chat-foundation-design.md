# AI chat foundation ("Batch A" plumbing) — design

**Date:** 2026-07-23
**Status:** approved pending user review of this document
**Scope:** backend-heavy — new `LlmClient`/`ChatService` seam, `conversations`/`messages`/
`project_ai_settings` tables, streaming `POST /api/chat/{kind}` + conversation history endpoints,
a per-project AI enablement gate (backend + a small admin UI addition), and a reusable
`useChat`/`<ChatPanel>` frontend pair mounted only on a temporary dev-only route. **Not in scope:**
the four features' real system prompts/content, mounting the panel anywhere in the real app, the
interviewer's structured-summary extraction, the tool-call loop, an admin conversation viewer —
all deferred to Batches B/C per `docs/ai-agents-plan.md`, which this spec implements the
foundation for.

## Problem

Four planned AI surfaces (chatbot, assessment deep-dive, lesson helper, interviewer — see
`docs/ai-agents-plan.md`) share one chat capability. Before any of the four can be built, the
capability itself needs to exist: a place to configure the LLM client, persist every message,
stream a response, and — newly identified during this design — a way to ensure only projects that
have actually paid for "the AI-enabled way of working" can use any of it. This spec is the
foundation ("the piping and plumbing") the four features will be built on top of in later batches.

## Decision summary (locked with the user 2026-07-23)

1. **Provider:** Anthropic API direct (`AsyncAnthropic`), decided and recorded in
   `docs/ai-agents-plan.md` §7 — not re-litigated here.
2. **Streaming transport:** structured SSE via `EventSourceResponse`/`ServerSentEvent`
   (`event="token"`/`"done"`/`"error"`), not the plan doc's plain-text-chunk sketch — needed to
   convey a new conversation's id and completion metadata (truncated flag, usage) inline.
3. **Per-project AI enablement gate (new — added during this design):**
   - **Real server-side enforcement**, not the existing visibility-only pattern the 3 hub
     components use (`assessment`/`learning`/`interview` — documented in root `CLAUDE.md` as
     "visibility filters, NOT access control"). This is a paywall; uncontrolled access means
     uncontrolled Anthropic spend, unlike a merely-ungated hub tile.
   - **All 4 chat surfaces gated** (chatbot, assessment, lesson, interview) — lesson helper is
     not a free exception.
   - **4 independent per-surface toggles** per project, not one umbrella flag — mirrors the
     granularity of the existing 3-component system, in case surfaces are ever sold separately.
   - **Default `enabled=false`** for every project (deny-by-default) — safe because nothing is
     live yet, no existing usage to disrupt.
   - Viewing conversation **history stays ungated** even after a project is disabled — the gate
     stops new spend, it doesn't retroactively hide a user's own past conversations or block
     admin review.
4. **Batch A frontend isn't mounted anywhere real** — `<ChatPanel>` is verified via a temporary
   dev-only route, not wired into `App.tsx`/`AppNav`/lesson pages (that's Batch B).
5. **One placeholder system prompt** (`backend/prompts/chatbot.md`, generic content) so the
   pipeline is genuinely end-to-end verifiable against a real model in this batch. The other
   three kinds get trivial placeholder files too (so nothing is broken-by-design), but only
   `chatbot` is manually smoke-tested this batch.
6. **Local dev uses Matthias's existing personal Anthropic key** (`backend/.env`, `LLM__API_KEY`)
   — the dedicated workspace + spend-cap key is only needed before this is ever wired into the
   Container App / prod (see `docs/ai-agents-plan.md` §8b step 1).

## Architecture

Backend follows the mandatory delaware layering (`python-be-architecture.md`). Each new unit
mirrors the smallest existing analog:

| New unit | File | Mirror (read this to copy the pattern) |
|---|---|---|
| LLM settings | `core/configs/llm.py` — `LlmSettings` | `core/configs/email.py` |
| `LlmClient` Protocol + `AnthropicLlmClient` | `services/llm_service.py` | `services/email_service.py`'s `EmailSender` Protocol |
| LLM client DI | `core/dependencies/llm.py` — `get_llm_service` (`None` if unconfigured) | `core/dependencies/email.py` |
| Models: `Conversation`, `Message` | `db/models/conversation.py` (both in one file) | `db/models/assignment.py` (already groups 3 related models) |
| Model: `ProjectAiSetting` | added to `db/models/company.py`, alongside `ProjectComponentSetting` | `ProjectComponentSetting` in the same file |
| Model registration | `db/models/__init__.py` | add `Conversation`, `Message`, `ProjectAiSetting` (alphabetical) |
| Abstract repos | `repositories/base.py`: `AbstractConversationRepository`, `AbstractMessageRepository` | existing ABCs there |
| Concrete repos | `repositories/conversation_repository.py`, `repositories/message_repository.py` | `repositories/feedback_repository.py` |
| Org repo/service extension | `AbstractOrgRepository`/`OrgRepository`/`OrgService` gain `resolve_ai_settings`/`set_ai_surface`, parallel to `resolve_components`/`set_component` | `org_service.py`'s existing component methods |
| Service | `services/chat_service.py` — `ChatService` (persist user turn → call model → stream → persist assistant turn) | shape-wise closest to `services/survey_service.py` (multi-repo orchestration) |
| DI wiring | **new file** `core/dependencies/chat.py` — repos, `get_chat_service`, and `require_ai_surface` | `core/dependencies/email.py`/`entra.py` (own file, not folded into the `domain.py` grab-bag) |
| Schemas | `schemas/chat.py`, additions to `schemas/admin_org.py` for the AI-settings admin endpoints | `schemas/feedback.py`, `schemas/admin_org.py` |
| Router | `routers/chat.py`; AI-settings admin endpoints added to `routers/admin_org.py` | `routers/feedback.py`, `routers/admin_org.py`'s components endpoints |
| Router registration | `main.py` | add `from src.routers import chat` + `app.include_router(chat.router)` |
| Prompts | `backend/prompts/{chatbot,assessment,lesson,interview}.md` | new convention, no existing analog |
| Migration | one Alembic revision creating all 3 tables | `a3f8c1d2e4b7_user_lessons.py` |

Frontend:

| New/changed unit | File | Notes |
|---|---|---|
| Hook | `frontend/src/lib/useChat.ts` | POST + parse the SSE stream (manual `fetch` + `ReadableStream` reader — **not** the browser's native `EventSource`, since this is a Bearer-token API with a POST body, same reasoning as the rest of `api/client.ts`) |
| Component | `frontend/src/components/ChatPanel.tsx` | message list, input, history list, the GDPR transparency notice — self-contained, takes `kind` as a prop |
| Dev-only verification route | `frontend/src/pages/DevChat.tsx` + a route entry | mounts `<ChatPanel kind="chatbot" />`; deleted once Batch B mounts the real thing |
| Admin AI-toggle UI | addition to `frontend/src/pages/admin/ProjectDetailView.tsx` | 4 toggle switches next to the existing 3 component toggles |
| API types | `frontend/src/api/schema.d.ts` | regenerate via `npm run gen:api` once the backend endpoints exist |

## Data model

```
conversations
  id           uuid        PK, gen_random_uuid()
  user_id      uuid        FK users.id ON DELETE CASCADE, NOT NULL, index
  kind         text        NOT NULL, CHECK kind IN ('chatbot','assessment','lesson','interview')
  context_ref  text        NULL   -- lesson_id or survey question id; text because it's
                                  -- polymorphic across kinds, not a single-target FK
  summary      jsonb       NULL   -- interviewer's structured extraction (Batch C, unused here)
  created_at   timestamptz NOT NULL, server_default now()
  updated_at   timestamptz NOT NULL, server_default now(), onupdate now()

messages
  id               uuid        PK, gen_random_uuid()
  conversation_id  uuid        FK conversations.id ON DELETE CASCADE, NOT NULL, index
  role             text        NOT NULL, CHECK role IN ('user','assistant','system','tool')
  content          text        NOT NULL
  metadata         jsonb       NULL   -- token counts, model id, truncated flag
  created_at       timestamptz NOT NULL, server_default now()

project_ai_settings
  id          uuid    PK, gen_random_uuid()
  project_id  uuid    FK projects.id ON DELETE CASCADE, NOT NULL
  kind        text    NOT NULL, CHECK kind IN ('chatbot','assessment','lesson','interview')
  enabled     boolean NOT NULL, server_default false
  UNIQUE(project_id, kind)
```

Deleting a user cascades their conversations/messages; deleting a conversation cascades its
messages; deleting a project cascades its AI settings — all matching how the rest of the schema
handles child rows. No row in `project_ai_settings` for a (project, kind) pair resolves to
`enabled=false` (deny-by-default fallback, same pattern as `resolve_components`'s
`DEFAULT_HIDDEN`/`DEFAULT_LOCKED` fallback) — nothing needs to backfill rows for existing
projects.

Naming deviation from `docs/ai-agents-plan.md`: that doc says `created_on`/`updated_on`; every
real table in this repo (`users`, `feedback`) uses `created_at`/`updated_at`, which this spec
follows instead.

## API

### Chat endpoints (`routers/chat.py`)

- **`POST /api/chat/{kind}`** — `kind: Literal["chatbot","assessment","lesson","interview"]`.
  Body `ChatMessageCreate {content: str (max_length=4000), conversation_id: UUID | None}`.
  Auth: `get_current_user`. **Gated by `require_ai_surface`** (see below) — runs on every call,
  not just conversation creation, so disabling a project mid-conversation stops it immediately.
  Response: `EventSourceResponse` (`text/event-stream`):
  - `event="token"` — `{text}` deltas as they stream from Anthropic.
  - `event="done"` — `{conversation_id, truncated, usage}`. This is also how the client learns
    the id of a brand-new conversation (the row is created before the model call starts).
  - `event="error"` — `{message}` for a clean mid-stream failure signal.
  Rate-limited (see Guardrails) before any DB/model work.
- **`GET /api/chat/conversations?kind=`** — the caller's conversations for that kind, token-scoped
  (no user id ever accepted from the request — iron rule). NOT gated by `require_ai_surface`
  (history stays viewable regardless of current enablement).
- **`GET /api/chat/conversations/{id}`** — one conversation + its messages; 404 if it doesn't
  belong to the caller (never a distinct "not yours" error — same non-disclosure pattern as
  every other ownership check in this app). Also not gated.

### `require_ai_surface` dependency (`core/dependencies/chat.py`)

Mirrors `require_admin`'s shape (a reusable authz-style dependency raising `HTTPException`
directly) but adds a DB check via `OrgService`, closer to how `get_current_user` itself does a
lookup:

```python
async def require_ai_surface(
    kind: Literal["chatbot", "assessment", "lesson", "interview"],
    user: Annotated[User, Depends(get_current_user)],
    org: Annotated[OrgService, Depends(get_org_service)],
) -> None:
    settings = await org.resolve_ai_settings(user.project_id) if user.project_id else {}
    if not settings.get(kind, False):
        raise HTTPException(status_code=403, detail="AI feature not enabled for your project")
```

A user with no `project_id` is treated as disabled (can't verify a payment status without a
project). Attached to the route as `dependencies=[Depends(require_ai_surface)]`; FastAPI binds
`kind` from the same path segment the endpoint function uses.

### Admin AI-settings endpoints (added to `routers/admin_org.py`)

- **`GET /api/admin/projects/{project_id}/ai`** → `{settings: {kind: {enabled: bool}}}` for all
  4 kinds — mirrors `GET .../components` exactly.
- **`PUT /api/admin/projects/{project_id}/ai/{kind}`** `{enabled: bool}` → 204 — mirrors
  `PUT .../components/{component}`.

## Guardrails

- **`max_tokens=1024`** on every Anthropic call (per `docs/ai-agents-plan.md`'s own sketch) —
  doubles as the output-length guardrail.
- **Per-user short-window rate limit**, checked in the router exactly like `auth.py`'s
  `limiter.is_limited(...)` pattern, before any DB/model work:
  `limiter.is_limited(f"chat:{user.id}", max_calls=20, window_seconds=300)` → 429 with
  `Retry-After` header on trip.
- **Daily turn cap**, same mechanism, wider window:
  `limiter.is_limited(f"chat-daily:{user.id}", max_calls=200, window_seconds=86400)`.
- Both numbers are placeholders picked to catch runaway/abusive usage without constraining normal
  use — they're plain constants, trivially tunable later; not a locked product decision.

## Disconnect-safe persistence

If the client disconnects mid-stream, FastAPI cancels the streaming generator. `ChatService`
must still persist whatever assistant text was generated so far, marked `metadata.truncated =
true` — via a `finally` block around the accumulation, or shielding the final DB write from
cancellation (`asyncio.shield`). **Open technical risk, flagged honestly rather than assumed
solved:** simulating a genuine mid-stream client disconnect in an integration test is non-trivial
with `httpx.AsyncClient`/`ASGITransport` (it drives the app in-process, not over a real socket).
The implementation phase needs to find/confirm a working test technique (possibly driving the
ASGI app callable more directly) — if none is found cheaply, this becomes a manually-verified
behavior (kill the dev-route request mid-stream, confirm the DB row) rather than an automated
test, and that tradeoff should be called out explicitly rather than silently skipped.

## Prompt loading

`backend/prompts/<kind>.md`, loaded by `ChatService`/`LlmService` (read at request time, fine to
cache after first read — content is static per the plan doc's design). All 4 files exist as of
this batch (placeholders for 3, real minimal content for `chatbot`) so no kind hits a missing-file
error by construction. A genuinely missing file (future mistake) should raise a clear internal
error, not silently send an empty system prompt.

## Frontend

`useChat` owns the `fetch` + manual SSE-line parsing (reading `token`/`done`/`error` events) and
exposes streaming text + loading/error state. `<ChatPanel kind={...}>` renders the message list,
input, a history list (`GET /api/chat/conversations?kind=`, click to load one via
`GET /api/chat/conversations/{id}` and continue it), and a fixed, non-dismissible transparency
line: *"Conversations are stored and may be reviewed by hub admins to improve the hub."* (per
`docs/ai-agents-plan.md` §6) — living inside `ChatPanel` itself so it appears wherever the panel
is later mounted, not something Batch B has to remember to add.

The temporary `DevChat` page/route mounts `<ChatPanel kind="chatbot" />` with nothing else around
it — purely a harness to click through streaming, history, and the transparency notice in a real
browser before Batch B exists. Deleted once Batch B mounts the panel for real.

Admin `ProjectDetailView` gets 4 additional toggle switches (chatbot/assessment/lesson/interview)
next to the existing 3 component toggles, wired to the new admin AI-settings endpoints.

## Testing

**Backend** (`cd backend && uv run poe format && uv run poe lint && uv run poe test`, ≥80%
coverage, ruff/ty clean):
- Unit: `ChatService` with `AsyncMock` repositories and a stubbed `LlmClient` (mirroring
  `tests/fixtures/email.py`'s `RecordingSender`/`RaisingSender` pattern) — **no real Anthropic
  calls in automated tests**, ever.
- Integration: `POST /api/chat/{kind}` end-to-end through the stubbed client — new conversation
  creation, continuing an existing one, 403 when the project's AI setting is off, 429 on both
  rate-limit tiers, 404 for someone else's `conversation_id`.
- Authz matrix: add `chat-send`/`chat-list`/`chat-detail`/admin-AI-settings entries to the
  existing `test_authz.py` pattern.
- **"No cross-user data" guarantee, reinterpreted for this batch** (the tool-call loop is
  deferred, so there are no agent data tools yet to test in the sense the plan doc originally
  meant): assert the iron rule holds for the chat endpoints themselves — no schema accepts a
  `user_id`, and `GET /api/chat/conversations/{id}` 404s (not 403, no disclosure) for a
  conversation owned by a different user.
- Disconnect-safe persistence: attempt an automated test per the note above; if no clean
  technique is found, document it as manually verified instead.

**Frontend** (`cd frontend && npm run typecheck && npm run lint && npm run build`):
- Types compile against the regenerated `schema.d.ts`.
- Manual browser check via the `DevChat` route: streaming renders token-by-token, a new
  conversation's id is picked up from the `done` event, history list shows past conversations,
  clicking one resumes it, the transparency notice is visible, and the admin toggle actually
  gates the endpoint (403 when off, works when on).

## Out of scope (YAGNI)

- Real system prompts for assessment/lesson/interview (Batch B/C content work).
- Mounting `<ChatPanel>` anywhere in the real app (Batch B).
- The tool-call loop / any agent data tools (deliberately deferred, per `docs/ai-agents-plan.md`).
- Interviewer structured-summary extraction, admin conversation viewer (Batch C).
- `cache_control` prompt caching (available bonus on Anthropic, not needed yet).
- The Foundry (`AnthropicLlmClient` alternative) adapter — not built, `LlmClient` seam keeps it
  possible later.
- Selling AI surfaces at different price tiers / any admin UI beyond a flat on/off toggle.

## Context-window budget & phased implementation (handoffs)

This is substantially bigger than a typical single-session feature (new settings/DI seam, 3 new
tables, ~2 new services, a streaming endpoint, a new authz-style dependency, an admin extension,
and a frontend pair) — more phases than the lesson-feedback precedent, each independently
verifiable and leaving the tree green.

### Phase 1 — Schema + settings/DI seam, no live model, no Azure mutation

**Deliverables:** `LlmSettings`, `LlmClient` Protocol + `AnthropicLlmClient`, `get_llm_service`;
`Conversation`/`Message`/`ProjectAiSetting` models + registration; the Alembic migration **file**
(NOT applied to any DB — confirm the current head with `uv run alembic heads` before setting
`down_revision`, don't assume it from this doc); abstract + concrete repositories.
**To resume, read:** this spec; `services/email_service.py`, `core/configs/email.py`,
`core/dependencies/email.py`; `db/models/assignment.py`, `db/models/company.py`;
`repositories/base.py`, `repositories/feedback_repository.py`.

### Phase 2 — Service + router + gate + guardrails, automated tests only

**Deliverables:** `ChatService`, `OrgService`/`OrgRepository` AI-settings methods,
`require_ai_surface`, `routers/chat.py` (all 3 endpoints, structured SSE), admin AI-settings
endpoints, rate limiting wired, `main.py` registration, `backend/prompts/*.md` (placeholders +
real `chatbot.md`), full test suite (stubbed `LlmClient`, no real API calls).
**Verify:** `uv run poe format && uv run poe lint && uv run poe test`, all green, coverage ≥80%.
**Do NOT:** apply the migration to any real DB yet.

### Phase 3 — Local live-model manual verification

**Gate at start:** ask the user before running the dev backend against a real DB and before
applying the migration anywhere (Azure-mutation-adjacent — `feedback-azure-ask-first` applies to
any Azure DB, confirm which DB this phase targets first). Set `LLM__*` in local `backend/.env`
with Matthias's existing personal key. Apply the migration locally. Curl/Swagger-verify
`POST /api/chat/chatbot` streams a real response, a row lands in `conversations`/`messages`, and
killing the request mid-stream still persists a `truncated` row.

### Phase 4 — Frontend

**Deliverables:** `useChat`, `ChatPanel` (transparency notice, history list), `DevChat` dev-only
route, `ProjectDetailView` AI-toggle additions, regenerated `schema.d.ts`.
**Gate:** regenerating `schema.d.ts` needs the dev backend running against a DB (triggers the
daily auth-cleanup DELETE on whichever DB it points at) — ask first, same as every prior feature.
**Verify:** `npm run typecheck && npm run lint && npm run build`.

### Phase 5 — End-to-end browser verification

Browser check via `/dev-chat` (or whatever route Phase 4 lands on): full streaming flow, history
resume, transparency notice visible, admin toggle actually gates access (403 off → works on).
**No deploy in this batch** — Batch A ships dark/unmounted; decide with the user separately when
(or whether) to deploy Batch A's code before Batch B exists.

## Approvals required (flagged, do not do unattended)

- Applying the migration to any shared/Azure DB (Phase 3) — ask first.
- Running the dev backend for `gen:api` (Phase 4) — triggers a real DB cleanup DELETE, ask first.
- Any `.\deploy.ps1` — not part of this batch's plan at all; a separate later decision.

## Open questions

- Exact rate-limit numbers (20/5min, 200/day) are placeholders — revisit once real usage exists.
- Whether the disconnect-safe-persistence behavior ends up automated-tested or only
  manually-verified depends on what Phase 2's implementation actually finds feasible with
  `httpx`/`ASGITransport` — not resolved here, called out as a real risk instead of assumed away.
