# AI Interviewer — AI opens the conversation (round-2 feedback item 3)

**Date:** 2026-07-30
**Branch:** `feature/interviewer-feedback-r2` (off `main` @ `96fc198`)
**Status:** design approved; part of the round-2 Group A build (items 1–5). See
`docs/history/ai-interviewer-followups.md` and the round-2 triage.

## Problem

On the live interviewer the conversation starts empty: the learner has to type "hallo"
(or similar) before the AI says anything. That is awkward and cold — the interviewer is a
briefed colleague who should open the conversation. `backend/prompts/interview.md` already
mandates a personalised opener ("OPEN by greeting them by name, reflecting the key facts
back, and INVITING CORRECTION"), but nothing triggers that first assistant turn.

## Goal

When a learner starts a fresh interview, the **AI speaks first** with its
prompt-mandated personalised greeting, with **no visible user bubble** and a **clean
stored transcript** that begins with the assistant turn. Resuming an in-progress interview
must not re-fire the opener.

## Constraints / what's fixed

- The opener is a **real, model-generated, personalised** turn (greet by name, reflect the
  assessment facts, invite correction) — **not** a canned string. A static greeting would
  discard the whole opener design in `interview.md`.
- The Anthropic Messages API requires a leading **user** turn. The opener therefore feeds
  the model a **synthetic kickoff user turn that is never persisted and never displayed**;
  the stored transcript's first row is the assistant greeting.
- **Isolation:** all changes live inside the interview feature. Matthias's shared chat code
  (`chat_service.py`, `routers/chat.py`, `useChat.ts`) is **not touched** — no coordination
  needed there. (Decision: chosen over a kickoff flag on the shared `POST /api/chat/{kind}`
  streaming endpoint, which would have modified the shared contract for all chat kinds.)

## Design

### Backend

New endpoint in `src/routers/interview.py`:

```
POST /api/interview/opener   (dependencies=[require_interview_surface])
  -> InterviewOpenerResponse { conversation_id: uuid, greeting: str }
```

Rate-limited with the same idiom as `POST /api/interview/playbook` (a light per-user
limiter, e.g. key `interview-opener:{user_id}`), so it cannot be hammered. Idempotency
already makes repeat calls cheap (see below), but the limiter is belt-and-suspenders.

New schema in `src/schemas/interview.py`: `InterviewOpenerResponse(conversation_id, greeting)`.

New service method `InterviewService.open_interview(*, user) -> InterviewOpenerResponse`:

1. **Idempotency / resume guard (first).** Look up the user's interview conversation. If one
   already exists, return its existing **first assistant message** with **no LLM call and no
   new conversation**. This makes the endpoint safe against a double-fire or a race, and safe
   to call on resume.
2. **Fresh start.** Build the system prompt exactly as a normal interview turn does:
   `system = load_prompt("interview")` + `"\n\n"` + `self._context.build_briefing(user)`
   (reuse of `InterviewContextService.build_briefing`, the same grounding the chat router
   appends via `system_suffix`). Then call `self._llm.stream_reply(system=..., messages=[{
   "role": "user", "content": _KICKOFF}], max_tokens=1024)` and **drain the stream to a
   string** server-side. `_KICKOFF = "[Begin the interview now: greet me and ask your first
   question.]"` — minimal and neutral; the system prompt owns the greeting behaviour.
3. **Generate first, then persist.** Only after generation succeeds: create the conversation
   (`conversations.create(user_id, kind="interview")`) and persist the greeting
   (`messages.create(conversation.id, role="assistant", content=greeting, metadata=...)`),
   then `conversations.touch(...)`. If the model call fails, no conversation is created — no
   empty-conversation litter — and the method raises `DomainError` (same failure surface as
   `build_playbook`).

The opener never emits the `[[READY_TO_BUILD]]` marker (it's a first turn), so no stripping
is required on this path.

### Frontend

- `src/lib/interviewApi.ts`: add
  `openInterview(): Promise<{ conversation_id: string; greeting: string }>` via the existing
  `rawRequest('POST', '/api/interview/opener')` escape hatch.
- `src/pages/Interview.tsx`:
  - On the welcome → chat transition for a **fresh** interview, call `openInterview()` **once**
    (guarded by a `useRef` latch so re-renders / StrictMode double-invoke can't fire it twice).
  - While it runs, show a lightweight "typing…"/spinner state inside the chat shell.
  - On success, hydrate via the **existing** `chat.loadConversation(conversation_id)` — this
    sets `messages` (the greeting) and `conversationId`; normal `chat.send()` streaming
    continues from there. **`useChat.ts` is unchanged.**
  - On failure, show an inline error with a **"Try again"** action, and keep a typed-input
    fallback so a learner is never stuck.
  - **Resume path (`status === 'in_progress'`) is unchanged** — it already calls
    `loadConversation` and shows the greeting; the opener is not fired.
  - The old empty-state hint ("Say hello to begin the interview.") is obsolete on the fresh
    path and only shows as the error/fallback affordance.

### State side effect (intended)

Firing the opener creates the conversation the moment the learner clicks "Start the
interview", so they transition `not_started → in_progress` on start rather than on their
first typed message. This is the correct semantics ("they started") and dovetails with
round-2 **item 4** (wiring interview status through the hub JourneyHome pill).

## Testing

- **Backend unit** (`tests/unit/test_interview_service.py`, stubbed `LlmClient`):
  - fresh start → creates the conversation, persists the assistant greeting, returns it;
  - idempotent → when a conversation already exists, returns the existing first assistant
    message and makes **no** second LLM call and **no** second conversation;
  - LLM failure → **no** conversation is created and `DomainError` is raised.
- **Backend router** (`tests/unit/` interview router tests): `POST /api/interview/opener`
  returns 200 with `{conversation_id, greeting}`; returns 403 without the interview surface.
- **Frontend**: the repo has no Vitest harness (FE is verified by the gate:
  `npm run typecheck && npm run lint && npm run build`). The opener behaviour (fires once on
  a fresh start, renders the greeting, does **not** fire on resume) is verified by the gate
  plus a Playwright smoke against the running app, not a new unit-test framework.

## Non-goals (v1)

- No streaming/token-by-token typing of the greeting (short text; a brief "typing…" pause is
  acceptable). If desired later, that is the shared-chat-endpoint route and a separate change.
- No change to `useChat.ts` or any shared chat code.
- No change to playbook generation, the two-box firewall, or the readiness marker.
