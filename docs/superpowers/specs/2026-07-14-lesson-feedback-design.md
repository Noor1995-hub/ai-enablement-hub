# Lesson feedback button + popup — design

**Date:** 2026-07-14
**Status:** approved pending user review of this document
**Scope:** full-stack — new `feedback` table + `POST /api/feedback` (backend) and a
new floating "Feedback" pill + "Share feedback" popup on the lesson learner view
(frontend). No changes to existing endpoints or tables.

## Problem

Learners have no in-app way to tell us something about a lesson — a typo, a
confusing passage, a broken example. Admins get an "Edit content" pill on the
lesson page; learners get nothing. We want a lightweight "Feedback" affordance on
each lesson that captures free-text feedback tied to that lesson and the
submitting user, stored for later review.

## Decision summary (locked with the user 2026-07-14)

1. **Storage: DB only.** Each submission is persisted to a new `feedback` table
   (user + lesson + message + timestamp). No email notification, no admin UI to
   read it yet — read via SQL for now; an admin viewer is a possible follow-up.
2. **Accent color: `--dlw-primary-red` `#C42828`** (the app's primary action red,
   already used by the lesson "Mark as complete" CTA). Everything the mockup drew
   in rose — the popup title, the textarea focus border, the "Send feedback"
   button — uses this red. The floating pill uses it too.
3. **Placement + audience:** a `position: fixed` pill in the **bottom-right** of
   the lesson **learner view only** (not the admin edit/MDX modes). Visible to
   **all authenticated users, admins included** (it does not conflict with the
   header "Edit content" pill).
4. **Popup subtitle = the lesson title** (replacing the mockup's `Page: /learn`).
5. **No character counter** on the textarea — just a server-side length cap.
6. **No rate-limiting in v1** (authenticated, low abuse risk; easy follow-up).

## Architecture

Backend follows the mandatory delaware layering (`python-be-architecture.md`):
router → service → repository → model, with DI in `core/dependencies/`. Each new
unit mirrors the smallest existing analog so an implementer reads one file to copy
the pattern:

| New unit | File | Mirror (read this to copy the pattern) |
|---|---|---|
| Model | `backend/src/db/models/feedback.py` | `db/models/survey.py` (UUID pk + FK CASCADE + `func.now()` default) |
| Model registration | `backend/src/db/models/__init__.py` | add `Feedback` import + `__all__` entry (alphabetical) |
| Abstract repo | `backend/src/repositories/base.py` | `AbstractProgressRepository` (smallest) |
| Concrete repo | `backend/src/repositories/feedback_repository.py` | `repositories/progress_repository.py` |
| Service | `backend/src/services/feedback_service.py` | `services/content_service.py` (thin service, raises `NotFoundError`) |
| Schema | `backend/src/schemas/feedback.py` | `schemas/me.py` (Pydantic request/response models) |
| Router | `backend/src/routers/feedback.py` | `routers/me.py` (auth'd `CurrentUserDep`, `response_model`) |
| Router registration | `backend/src/main.py` (~line 179) | add `from src.routers import feedback` + `app.include_router(feedback.router)` |
| DI providers | `backend/src/core/dependencies/domain.py` | `get_progress_repository` + `get_content_service` |
| Migration | `backend/alembic/versions/<rev>_feedback.py` | `alembic/versions/a3f8c1d2e4b7_user_lessons.py` (create_table) |

Frontend is one new self-contained component plus one line in the lesson page:

| New/changed unit | File | Notes |
|---|---|---|
| Component | `frontend/src/components/LessonFeedback.tsx` | new; owns pill + modal + submit |
| Wiring | `frontend/src/pages/LessonPage.tsx` | render `<LessonFeedback>` in the learner-view branch only |
| API types | `frontend/src/api/schema.d.ts` | regenerate via `npm run gen:api` after the backend endpoint exists |

### Data model — `feedback`

```
id          uuid       PK, server_default gen_random_uuid()
user_id     uuid       FK users.id     ON DELETE CASCADE, NOT NULL
lesson_id   uuid       FK lessons.id   ON DELETE CASCADE, NOT NULL
message     text       NOT NULL
created_at  timestamptz NOT NULL, server_default now()
```

Deleting a user or a lesson removes their feedback (CASCADE), matching how the
rest of the schema handles child rows (see `survey.py`, `lesson_progress`). No
UNIQUE constraint — a user may submit feedback on a lesson many times. Index on
`lesson_id` for future "feedback per lesson" reads (cheap, mirrors the
`e1f2a3b4c5d6` lesson_progress index rationale).

### API — `POST /api/feedback`

- **Auth:** required (`get_current_user`). Iron rule: the user id comes from the
  token only — it is **never** in the request body. `lesson_id` in the body is a
  resource id, not an ownership identifier, so it is allowed (parity with
  `PUT /api/lessons/{id}/progress` taking a lesson id).
- **Request** (`FeedbackCreate`): `{ "lesson_id": UUID, "message": str }` with
  `message` constrained `max_length=4000`. Emptiness is enforced **in the Pydantic
  schema, not the service** — a field validator strips the message and raises
  `ValueError` if the result is empty, so both `""` and whitespace-only bodies
  return **422** (a service-side `DomainError` would map to 400 and contradict the
  test matrix). Store the stripped message.
- **Behavior:** service validates the lesson exists via the existing
  `ContentRepository.get_lesson` (raises `NotFoundError` → **404** through the
  existing `main.py` exception handler); on success inserts one row.
- **Response:** **201** with `FeedbackResponse { id: UUID, created_at: datetime }`
  (minimal — the client only needs success).
- **Errors:** `401` unauthenticated (middleware), `422` empty/oversized message or
  malformed body (Pydantic), `404` unknown `lesson_id`.

### Frontend — `LessonFeedback` component

Props: `{ lessonId: string; lessonTitle: string }`. Self-contained: owns its own
open/close, textarea value, and submit state. Rendered once, only in the
learner-view branch of `LessonPage` (the final `else`), so it never appears in
edit/MDX modes.

**Pill button** (closed state):
- `position: fixed; bottom: 24px; right: 24px; zIndex: 50`.
- `borderRadius: 999`, padding ~`11px 22px`, solid `#C42828` background, `#fff`
  text, `fontWeight: 700/800`, `fontFamily: var(--dlw-font-body)`, label
  `Feedback`, `--dlw-shadow-card` (or a slightly stronger shadow so it floats).
- Hover: reuse an existing class — `.lesson-cta` lightens `#C42828`→`#EF463C` on
  hover; or `.btn-red-dark` darkens →`#941914`. Pick `.lesson-cta`'s lighten to
  match the mockup's lively pill. `aria-label="Share feedback"`.

**Popup** (open state) — matches the mockup, recolored to `#C42828`:
- Full-viewport overlay (`position: fixed; inset: 0`, translucent
  `rgba(16,24,32,.45)`), centered white card (`borderRadius: var(--dlw-radius-xl)`,
  `--dlw-shadow-lg`, `maxWidth ~440px`, padding ~`24px`).
- Header row: title **"Share feedback"** (`#C42828`, weight 700) + a `×` close
  button (top-right, muted grey, `aria-label="Close"`).
- Subtitle: **the lesson title** (`lessonTitle`), muted small-caps or plain muted
  text — the mockup's `Page: /learn` slot.
- `<textarea>` placeholder `"What's on your mind?"`, ~5 rows, resize vertical,
  `1.5px solid #C42828` border (the mockup's rose outline → red), rounded,
  auto-focused on open.
- **"Send feedback"** button: full-width, solid `#C42828`, white text, rounded;
  `disabled` (greyed `#E2E2E2`/muted text, `cursor: default`) when the trimmed
  message is empty or a submit is in flight.
- Close on: `×`, click on the overlay backdrop, and `Escape`.

**Submit states:**
- `idle` → user types → `sending` (button shows "Sending…", disabled) →
  - `sent`: swap the popup body for a short confirmation ("Thanks — your feedback
    was sent.") with a single Close button (no auto-close — it can feel abrupt and
    races the animation). Closing resets state so reopening starts with an empty
    textarea.
  - `error`: inline red message ("Couldn't send feedback. Please try again.")
    **below the textarea, keeping the typed text**; button returns to enabled.
- `401` is handled transparently by `api/client.ts`'s single-flight refresh +
  retry — the component does not special-case it.

**API call:** `client.POST('/api/feedback', { body: { lesson_id: lessonId, message } })`.
Use the generated types (regenerate `schema.d.ts` first).

### Zoom note (do NOT add compensation)

The app renders under a baked-in `:root { zoom: 1.25 }`. Pure CSS `position:
fixed` offsets (`bottom/right: 24px`) scale with that zoom exactly like every
other element — this is correct and matches the rest of the UI. `getRectZoomFactor`
(`lib/uiZoom.ts`) is only for positioning derived from `getBoundingClientRect`
readback (see `project-baked-in-zoom`); this feature has none, so no compensation
is needed.

## Testing

**Backend** (`cd backend && uv run poe format && uv run poe lint && uv run poe test`,
must stay ≥80% coverage, ruff/ty clean):
- Unit: `FeedbackService.submit` — happy path inserts; unknown lesson raises
  `NotFoundError`.
- Integration (PG test DB): `POST /api/feedback` → `201` + row present; `401`
  unauthenticated; `422` empty/whitespace message; `422` message over the cap;
  `404` unknown `lesson_id`.
- Authz matrix: add a `feedback` entry — the endpoint requires auth but is **not**
  admin-only (any authenticated user). Assert admin + user succeed, anonymous
  `401`. Follows the existing `tests/**/test_authz.py` pattern.

**Frontend** (`cd frontend && npm run typecheck && npm run lint && npm run build`):
- Types compile against the regenerated `schema.d.ts`.
- Manual browser check (Phase C): open a lesson as a learner → pill visible
  bottom-right → click → popup shows the lesson title → type → Send → confirmation
  → a row appears in the `feedback` table (SQL check).

## Out of scope (YAGNI)

- Admin UI to browse/read feedback (read via SQL for now).
- Email notification on new feedback.
- Editing/deleting/listing feedback via API.
- A generic per-route feedback widget (this is lesson-specific).
- Rate limiting (revisit only if abused).

---

## Context-window budget & phased implementation (handoffs)

This feature is small enough that a single uninterrupted session could finish it,
but the work spans backend + a DB migration + frontend + browser verification, and
mid-work context summarization is possible. It is therefore split into **three
self-contained phases** with explicit handoff checkpoints. Each phase is
independently verifiable, leaves the tree in a green state, and its handoff note
lists exactly which files a fresh session must read to resume — so no phase
depends on holding another phase's exploration in context.

**Rule for every phase:** start by reading this spec + the "to resume, read"
files for that phase. End by (a) running the phase's verification commands, (b)
recording the handoff checkpoint (below) in the plan/todo or a scratch note, and
(c) stopping for user review before the next phase if context is >~60% consumed or
the phase involves an approval gate.

### Phase A — Backend (persistence + API), no Azure mutation

**Deliverables:** model + registration, abstract + concrete repository, schema,
service, router + registration, DI providers, the Alembic migration **file**
(NOT applied to any DB yet), and all backend tests green.

**Steps:**
1. Read (to copy patterns): `db/models/survey.py`, `repositories/base.py`
   (`AbstractProgressRepository`), `repositories/progress_repository.py`,
   `services/content_service.py`, `services/exceptions.py`, `schemas/me.py`,
   `routers/me.py`, `core/dependencies/domain.py`, `main.py` (router includes),
   and `alembic/versions/a3f8c1d2e4b7_user_lessons.py`.
2. Write the model + register it in `db/models/__init__.py`.
3. Add `AbstractFeedbackRepository` to `base.py` + `feedback_repository.py`.
4. Write schema, service, router; register the router in `main.py`; add
   `get_feedback_repository` + `get_feedback_service` to `domain.py`.
5. Write the migration: `down_revision = "e1f2a3b4c5d6"` (current head — confirm
   with `uv run alembic heads`), `create_table("feedback", …)` with the two FK
   CASCADEs + the `lesson_id` index; a real `downgrade()` that drops the table.
6. Write tests (unit + integration + authz).

**Verify:** `cd backend && uv run poe format && uv run poe lint && uv run poe test`
— all green, coverage ≥80%. Optionally launch the app and confirm
`POST /api/feedback` shows in `/docs`.

**Do NOT:** apply the migration to the Azure dev DB (that is an Azure mutation —
needs user approval; see Phase B step 0). Prod applies it automatically on the
next deploy via `startup.py`'s `alembic upgrade`.

**Handoff checkpoint (record):** files created/modified; test count + result;
migration revision id chosen; note "migration NOT yet applied to any DB".
**To resume Phase B, read:** this spec, the new `routers/feedback.py` +
`schemas/feedback.py` (to know the exact request/response shape),
`frontend/src/pages/LessonPage.tsx`, `frontend/src/api/client.ts`,
`frontend/src/index.css` (color tokens).

### Phase B — Frontend (component + wiring)

**Gate at start (step 0):** the frontend needs the generated types.
`npm run gen:api` requires the backend running against a DB, and starting the dev
backend runs the daily auth-cleanup DELETE against the real Azure dev DB (see the
invite-split entry in `CLAUDE.md`) — **ask the user before running it**, or
hand-patch the two `schema.d.ts` entries for `POST /api/feedback` (mirror how
other defaulted/required fields are typed) and note it must be regenerated for
real later. Also decide with the user whether to **apply the migration to the
Azure dev DB now** (`uv run alembic upgrade head`) so a browser end-to-end works
in Phase C — this is an Azure mutation, **ask first**.

**Deliverables:** `LessonFeedback.tsx` (pill + popup + submit, all states),
wired into `LessonPage.tsx`'s learner-view branch, `schema.d.ts` updated,
frontend checks green.

**Steps:**
1. Regenerate/patch `schema.d.ts` (per step 0).
2. Write `LessonFeedback.tsx` per the component spec above.
3. Render `<LessonFeedback lessonId={lesson.id} lessonTitle={lesson.title} />`
   inside the learner-view branch of `LessonPage.tsx` (the `else` block around
   the `<main>`), NOT in the edit/MDX branches.

**Verify:** `cd frontend && npm run typecheck && npm run lint && npm run build` —
all green.

**Handoff checkpoint (record):** component file + LessonPage edit done; whether
`schema.d.ts` was truly regenerated or hand-patched; whether the migration was
applied to the dev DB (Phase C's browser check needs it applied).
**To resume Phase C, read:** this spec; nothing else strictly required.

### Phase C — End-to-end verification + deploy

**Deliverables:** proof the feature works against a real backend, then a live
deploy.

**Steps:**
1. Ensure the migration is applied to the dev DB (Phase B step 0). Run backend +
   frontend locally.
2. Browser check (use the /run or /verify skill): sign in as a learner, open a
   lesson, confirm the pill is bottom-right, open the popup, confirm the lesson
   title shows, submit, confirm the sent state, and confirm a row landed in the
   `feedback` table (SQL). Also check a non-admin sees it and the popup closes on
   Esc/backdrop.
3. Deploy: `.\deploy.ps1` at the rebuild root (cloud build + container update).
   The prod DB migrates automatically on container start. **Deploy is an
   outward-facing action — ask the user before running it.**

**Verify:** post-deploy health check green; a real submission on the live URL
lands a row.

**Handoff checkpoint (record):** browser results; deploy image tag + revision;
prod migration head after deploy; any follow-ups (e.g. admin viewer).

## Approvals required (flagged, do not do unattended)

- **Applying the migration to the Azure dev DB** (Phase B step 0 / Phase C) —
  Azure mutation, ask first (`feedback-azure-ask-first`).
- **Running the dev backend for `gen:api`** — triggers a real DELETE cleanup on
  the Azure dev DB, ask first.
- **`.\deploy.ps1`** (Phase C) — outward-facing, ask first.

## Open questions

None outstanding. The two soft confirmations (pill visible to admins too; no
character counter) were resolved as defaults in the decision summary; the user can
override during review.
