# AI Interviewer (Batch C) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship the in-hub AI Opportunity Interview — a guided, assessment-grounded chat that produces a two-box (delaware-internal / learner-shared) playbook — building only on Batch A's already-merged chat foundation.

**Architecture:** Reuse Batch A's `ChatService` for the streaming interview turns (with an injected per-user context block); add a small `InterviewContextService` (composes existing survey/maturity/learning services) and an `InterviewService` (wrap-up generation via the existing `LlmClient.complete_structured`), a new `routers/interview.py`, and a frontend journey (welcome → chat → lightweight playbook) plus an admin read section. No database migration (the `conversations.summary` JSONB column and `kind='interview'` already exist).

**Tech Stack:** FastAPI (Python 3.13, uv) + Anthropic SDK 0.119 + React 18 / Vite / React Router v6 / @tanstack/react-query / openapi-fetch.

## Global Constraints

- **Work branch/worktree:** `feature/ai-interviewer` at `C:\tmp\aiiv` (off `origin/main` `9352736`). Never touch the main checkout.
- **NO migration.** `conversations.summary` (JSONB) and `kind='interview'` already exist. Adding a migration is a plan failure.
- **Reuse `LlmClient.complete_structured(*, system, prompt, schema: StructuredSchema, max_tokens) -> tuple[dict, LlmUsage]`** (already on the Protocol + `AnthropicLlmClient` + `FakeLlmClient`). Do NOT add a new LLM method.
- **No direct DB tonight.** Only DB-free checks run now: `ruff format`, `ruff check .`, `uvx ty check .`, and unit tests `pytest -m unit` (or `pytest tests/unit`). Integration tests, `gen:api`, live-model runs, and browser E2E are the **DB-gated runbook** at the end — do NOT attempt them.
- **Frontend builds against interim types.** New endpoints aren't in `schema.d.ts` yet, so call them via the `rawRequest<T>(...)` escape hatch and hand-written types in `src/types/domain.ts`; after tomorrow's `gen:api`, swap those to `components['schemas'][...]` aliases (a zero-drift change). Follow the precedent in `src/pages/admin2/api.ts:30-51` and `src/types/domain.ts:47-88`.
- **The firewall (hard):** the learner-facing endpoints and UI must NEVER receive or render `summary.internal`. `GET /api/interview/me` and `POST /api/interview/playbook` return `shared` only. A unit test must assert this.
- **Iron rule:** no non-admin endpoint accepts a `user_id`; identity comes from the token. Admin endpoints (`/api/admin/*`) take `user_id` and are `require_admin`-gated.
- **Model:** Sonnet 5 via `LLM__MODEL=claude-sonnet-5` (set tomorrow). Code never hardcodes a model.
- **English only** for v1. **Difficulty labels:** exactly `Quick Win` / `Worth a Session` / `Bigger Build`.
- Backend layering per `python-be-architecture.md`; ruff/ty clean; unit tests are `@pytest.mark.unit`-style under `tests/unit/`, mocking repos with `AsyncMock(spec=...)` and stubbing the client with `FakeLlmClient` (see `tests/fixtures/llm.py`). No real Anthropic calls in tests, ever.

Design of record: `docs/superpowers/specs/2026-07-28-ai-interviewer-design.md` (in this branch). Journey/playbook visual contract: `docs/design-prototypes/ai-interviewer/mockup.html`.

---

## File structure

**Backend — create:**
- `backend/src/services/interview_context.py` — `InterviewContextService` + the code→label maps ported from `surveyOptions.ts`.
- `backend/src/services/interview_service.py` — `InterviewService` (wrap-up generation, state, admin read, reset).
- `backend/src/services/interview_schema.py` — the `StructuredSchema` (the `{internal, shared}` tool input_schema) + `PLAYBOOK_SCHEMA`.
- `backend/src/schemas/interview.py` — Pydantic models: `PlaybookShared`, `PlaybookInternal`, `InterviewStateResponse`, `PlaybookResponse`, `AdminInterviewResponse`.
- `backend/src/routers/interview.py` — learner + admin endpoints.
- `backend/src/core/dependencies/interview.py` — DI providers (`get_interview_context_service`, `get_interview_service`).
- `backend/prompts/interview_playbook.md` — the generation prompt (new).
- Tests: `backend/tests/unit/test_interview_context.py`, `test_interview_service.py`, `test_interview_schema.py`.

**Backend — modify:**
- `backend/prompts/interview.md` — replace the placeholder with the real interview prompt (spec §7.1).
- `backend/src/services/chat_service.py` — `send_message` gains optional `system_suffix: str | None = None`, appended to the loaded system prompt.
- `backend/src/repositories/base.py` + `conversation_repository.py` — add `update_summary(conversation_id, summary: dict) -> None`.
- `backend/src/core/dependencies/chat.py` — thread interview context into the `interview` kind send path (see Task 5).
- `backend/src/main.py` — `app.include_router(interview.router)`.

**Frontend — create:**
- `frontend/src/pages/Interview.tsx` — the journey state machine (welcome / resume / playbook).
- `frontend/src/components/interview/Playbook.tsx` — lightweight playbook render.
- `frontend/src/lib/interviewApi.ts` — interim-typed hooks/functions (`getInterviewState`, `buildPlaybook`) via `rawRequest`.
- `frontend/src/pages/admin2/InterviewCard.tsx` — admin per-user interview section.

**Frontend — modify:**
- `frontend/src/App.tsx:89` — swap `/interview` `ComingSoon` for `<Interview />`.
- `frontend/src/types/domain.ts` — interim types (`InterviewState`, `PlaybookShared`, `AdminInterview`).
- `frontend/src/pages/admin2/api.ts` — `useInterview(userId)` hook.
- `frontend/src/pages/admin2/UserDetailPage.tsx` — mount `<InterviewCard>` in the detail grid.

---

## Task 1: `update_summary` repository method

**Files:** Modify `backend/src/repositories/base.py` (`AbstractConversationRepository`), `backend/src/repositories/conversation_repository.py`.

**Interfaces — Produces:** `ConversationRepository.update_summary(self, conversation_id: uuid.UUID, summary: dict[str, Any]) -> None`.

- [ ] **Step 1:** Add the abstract method to `AbstractConversationRepository` (after `touch`):
```python
@abstractmethod
async def update_summary(self, conversation_id: uuid.UUID, summary: dict[str, Any]) -> None:
    """Persist the interviewer's structured extraction into conversations.summary."""
```
- [ ] **Step 2:** Implement in `ConversationRepository` (mirror `touch`'s UPDATE style):
```python
async def update_summary(self, conversation_id: uuid.UUID, summary: dict[str, Any]) -> None:
    await self._session.execute(
        update(Conversation).where(Conversation.id == conversation_id).values(summary=summary)
    )
    await self._session.commit()
```
- [ ] **Step 3:** `cd C:\tmp\aiiv\backend && uv run ruff check . && uvx ty check .` — expect clean. (Its DB behaviour is covered by an integration test in the DB-gated runbook; no unit test here.)
- [ ] **Step 4:** Commit: `feat(interview): add ConversationRepository.update_summary`.

## Task 2: The playbook structured-output schema

**Files:** Create `backend/src/services/interview_schema.py`, `backend/src/schemas/interview.py`, `backend/tests/unit/test_interview_schema.py`.

**Interfaces — Produces:** `PLAYBOOK_SCHEMA: StructuredSchema` (name `"record_playbook"`), and Pydantic models `PlaybookShared`, `PlaybookInternal`, plus a top-level `PlaybookExtraction(internal: PlaybookInternal, shared: PlaybookShared)`.

- [ ] **Step 1:** In `schemas/interview.py` define the Pydantic models mirroring spec §5 exactly — `UseCase` (rank:int, start_here:bool, name:str, pain_it_kills:str, in_practice:str, before:str, after:str, impact:str, difficulty: Literal["Quick Win","Worth a Session","Bigger Build"], systems_involved: list[str], assumption_to_check: str | None, cross_functional: bool), `NextMove` (order:int, move:str, why_now:str, linked_use_case:int), `Reframe` (their_hesitation, the_concern, reframe, first_proof), `DoThisToday` (action, time_required, why_this_one), `PlaybookShared`, `PlaybookInternal` (input_quality/person/pains/blockers/maturity/systems_landscape/company_context/engagement_notes as spec §5), `PlaybookExtraction`.
- [ ] **Step 2:** In `interview_schema.py`, build `PLAYBOOK_SCHEMA = StructuredSchema(name="record_playbook", description="...", input_schema=PlaybookExtraction.model_json_schema())` and set `additionalProperties: False` at the top level (the `test_llm_service.py` structured test shows the SDK expects a plain JSON-schema dict).
- [ ] **Step 3:** Write `test_interview_schema.py` (unit): assert `PLAYBOOK_SCHEMA.input_schema` has exactly top-level keys `{"internal","shared"}` under `properties`, that `difficulty` enum is the three exact labels, and that `PlaybookExtraction.model_validate(<a fixture dict>)` round-trips.
- [ ] **Step 4:** `pytest tests/unit/test_interview_schema.py -v` → PASS; `ruff`/`ty` clean.
- [ ] **Step 5:** Commit: `feat(interview): playbook extraction schema + StructuredSchema`.

## Task 3: `InterviewContextService` + label maps

**Files:** Create `backend/src/services/interview_context.py`, `backend/tests/unit/test_interview_context.py`.

**Interfaces — Consumes:** `SurveyService.get_own(user_id) -> SurveyResponse | None`, `MaturityService.effective_level(user) -> str | None`, `LearningService.learning_status(user_id) -> Literal[...]`.
**Produces:** `InterviewContextService(surveys: SurveyService, maturity: MaturityService, learning: LearningService)` with `async build(self, user: User) -> str` returning the rendered context block (the slot values for the interview prompt), and `async build_for_generation(self, user: User) -> str` returning the `<assessment_record>` context used by the generation prompt.

- [ ] **Step 1:** Port the label maps as module dicts from `surveyOptions.ts` (values quoted verbatim in the plan appendix / spec): `TOOLS`, `BARRIERS`, `SETUP`, `FREQ`, `BREADTH`, and `COMPETENCY` (c1–c6 code→label). Add a `_labels(codes, mapping)` helper.
- [ ] **Step 2:** Implement `build(user)`: fetch survey (`get_own`), effective level, learning status; render a compact human-readable block filling the interview prompt slots ({role},{department},{maturity_level},{usage_frequency}=b_freq label,{ai_tools},{ai_setups},{barriers},{timesink}=q_timesink,{excitement}=q_excitement,{learning_status}). If no survey, return a minimal "no assessment on file" block. Everything token-scoped from the passed `user`.
- [ ] **Step 3:** `build_for_generation(user)`: a fuller structured text dump of the same survey fields for the generation prompt's `<assessment_record>` slot.
- [ ] **Step 4:** Write `test_interview_context.py` (unit): mock the three services (`AsyncMock(spec=...)`), feed a `SurveyResponse`-shaped `SimpleNamespace`, assert the rendered block contains the human labels (e.g. "Microsoft Copilot" not "COPILOT") and the free-text answers, and that a `None` survey yields the minimal block.
- [ ] **Step 5:** `pytest tests/unit/test_interview_context.py -v` → PASS; `ruff`/`ty` clean.
- [ ] **Step 6:** Commit: `feat(interview): InterviewContextService + label maps`.

## Task 4: Real prompts (interview + generation)

**Files:** Modify `backend/prompts/interview.md`; Create `backend/prompts/interview_playbook.md`.

- [ ] **Step 1:** Replace `interview.md` with the spec §7.1 prompt verbatim.
- [ ] **Step 2:** Create `interview_playbook.md` with the spec §7.2 prompt verbatim.
- [ ] **Step 3:** Sanity: `load_prompt("interview")` and a direct read of `interview_playbook.md` both succeed (no unit test needed — files are static; `load_prompt` is `@lru_cache`'d).
- [ ] **Step 4:** Commit: `feat(interview): real interview + generation prompts`.

## Task 5: Context injection into interview turns

**Files:** Modify `backend/src/services/chat_service.py`, `backend/src/core/dependencies/chat.py`; Test `backend/tests/unit/test_chat_service.py` (add a case).

**Interfaces — Produces:** `ChatService.send_message(self, *, conversation, content, system_suffix: str | None = None)`.

- [ ] **Step 1:** Failing test: in `test_chat_service.py`, add `test_send_message_appends_system_suffix` — with a `FakeLlmClient`, call `send_message(..., system_suffix="CONTEXT-X")`, drain the generator, assert `llm.calls[0]["system"].endswith("CONTEXT-X")` and still starts with the loaded prompt.
- [ ] **Step 2:** Run it → FAIL (unexpected kwarg).
- [ ] **Step 3:** Implement: add the param; `system_prompt = load_prompt(conversation.kind)`; `if system_suffix: system_prompt = f"{system_prompt}\n\n{system_suffix}"`. No other behaviour changes.
- [ ] **Step 4:** In `dependencies/chat.py`, inject `InterviewContextService | None` into the send path: when `kind == "interview"` and a current user is available, `_prepare_chat_message` computes `system_suffix = await interview_context.build(user)` and threads it into the streamed `send_message`. For other kinds, `system_suffix=None` (unchanged). (Keep generic chat generic; the branch is the only interview-specific code in the chat pipeline.)
- [ ] **Step 5:** `pytest tests/unit/test_chat_service.py -v` → PASS; `ruff`/`ty` clean.
- [ ] **Step 6:** Commit: `feat(interview): inject assessment context into interview turns`.

## Task 6: `InterviewService` (wrap-up generation, state, admin read, reset)

**Files:** Create `backend/src/services/interview_service.py`, `backend/tests/unit/test_interview_service.py`.

**Interfaces — Consumes:** repos (`AbstractConversationRepository`, `AbstractMessageRepository`), `LlmClient`, `InterviewContextService`, `PLAYBOOK_SCHEMA`. **Produces:**
- `async build_playbook(self, *, user) -> PlaybookShared` — resolves the user's interview conversation (most recent `kind="interview"`); if `summary` already set, returns `summary["shared"]`; else loads transcript (`messages.list_for_conversation`), builds the generation prompt (`interview_playbook.md` + context + transcript), calls `llm.complete_structured(schema=PLAYBOOK_SCHEMA, max_tokens=4096)`, validates via `PlaybookExtraction.model_validate`, on `ValidationError`/`LlmError` retries once, persists both boxes via `conversations.update_summary`, returns the `shared` half.
- `async get_state(self, *, user) -> InterviewStateResponse` — no interview → `not_started`; conversation but no summary → `in_progress` (+conversation_id); summary set → `complete` (+shared).
- `async get_admin_view(self, *, user_id) -> AdminInterviewResponse` — status + full summary (both boxes) + transcript messages.
- `async reset(self, *, user_id) -> None` — delete the user's interview conversation (cascade clears messages).

- [ ] **Step 1:** Failing test `test_build_playbook_persists_and_returns_shared_only` — `FakeLlmClient(structured={"internal": {...}, "shared": {...valid...}})`, mocked repos (conversation with `summary=None`, transcript messages). Assert the result is the `shared` model, `conversations.update_summary` awaited once with a dict having both keys, and the returned object exposes no internal fields.
- [ ] **Step 2:** Failing test `test_build_playbook_is_idempotent` — conversation `summary={"internal":..,"shared":..}` already set → returns `shared`, `complete_structured` NOT called.
- [ ] **Step 3:** Failing test `test_build_playbook_retries_once_on_invalid` — first structured return invalid, second valid → one retry, success. (Use a `FakeLlmClient` variant whose `complete_structured` returns a bad dict then a good one.)
- [ ] **Step 4:** Failing test `test_get_state_transitions` — none/in_progress/complete.
- [ ] **Step 5:** Run all → FAIL. Implement `InterviewService`. Re-run → PASS.
- [ ] **Step 6:** `pytest tests/unit/test_interview_service.py -v` → PASS; coverage of the service ≥80%; `ruff`/`ty` clean.
- [ ] **Step 7:** Commit: `feat(interview): InterviewService generation + state + admin + reset`.

## Task 7: `routers/interview.py` + DI + registration

**Files:** Create `backend/src/routers/interview.py`, `backend/src/core/dependencies/interview.py`; Modify `backend/src/main.py`. (Schemas from Task 2/6.)

**Endpoints (all learner ones gated `dependencies=[Depends(require_ai_surface)]` with a fixed `kind="interview"` shim; admin ones under an admin-gated router):**
- `GET /api/interview/me` → `InterviewStateResponse` (token-scoped; `shared` only).
- `POST /api/interview/playbook` → `PlaybookResponse` (`{playbook: PlaybookShared}`; token-scoped; 404 if no interview conversation exists yet).
- `GET /api/admin/interviews/{user_id}` → `AdminInterviewResponse` (`require_admin`; mirror `get_user_survey`: `admin_user_service.get_user(user_id)` first for 404).
- `DELETE /api/admin/interviews/{user_id}` → 204 (`require_admin`; mirror `delete_user`).
- Interview **turns reuse the existing** `POST /api/chat/interview`.

- [ ] **Step 1:** Write `dependencies/interview.py`: `get_interview_context_service` (compose the three service providers) and `get_interview_service` (repos + llm + context). `require_ai_surface` for interview: reuse the existing dependency; since it reads `kind` from the path and these routes have no `{kind}` segment, add a thin `require_interview_surface(user, org)` wrapper in this module that calls the same `OrgService.resolve_ai_settings` check for `"interview"`.
- [ ] **Step 2:** Write `routers/interview.py` with the four endpoints. Learner endpoints return `shared` only (never `internal`). Admin router segment gated by `require_admin`.
- [ ] **Step 3:** Register in `main.py`: `from src.routers import interview` + `app.include_router(interview.router)`.
- [ ] **Step 4:** Unit-level: `test_interview_service.py` already covers the service; add a small `tests/unit/test_interview_firewall.py` asserting `PlaybookResponse`/`InterviewStateResponse` have no `internal` field and `AdminInterviewResponse` does. (Full endpoint integration + authz-matrix rows are DB-gated → runbook.)
- [ ] **Step 5:** `pytest tests/unit -v` (whole unit suite) → PASS; `ruff format`, `ruff check .`, `uvx ty check .` → clean.
- [ ] **Step 6:** Commit: `feat(interview): interview router (learner + admin) + DI + registration`.

## Task 8: Frontend interim types + api

**Files:** Modify `frontend/src/types/domain.ts`; Create `frontend/src/lib/interviewApi.ts`; Modify `frontend/src/pages/admin2/api.ts`.

- [ ] **Step 1:** In `types/domain.ts`, add hand-written interim types under a clearly-marked `// INTERIM — swap to components['schemas'][...] after gen:api` block: `UseCase`, `NextMove`, `Reframe`, `DoThisToday`, `PlaybookShared`, `InterviewState` (`{status:'not_started'|'in_progress'|'complete'; conversation_id?:string; playbook?:PlaybookShared}`), `AdminInterview` (`{status; tier?; internal?:unknown; shared?:PlaybookShared; transcript:{role:string;content:string}[]}`).
- [ ] **Step 2:** Create `lib/interviewApi.ts`: a local `rawRequest<T>` (copied from `admin2/api.ts:30-51`), `getInterviewState(): Promise<InterviewState>` → `GET /api/interview/me`, `buildPlaybook(): Promise<PlaybookShared>` → `POST /api/interview/playbook` (returns `.playbook`).
- [ ] **Step 3:** In `admin2/api.ts` add `useInterview(userId)` mirroring `useSurvey` (query key `['admin','interview',userId]`, via `rawRequest<AdminInterview>('GET', \`/api/admin/interviews/${userId}\`)`).
- [ ] **Step 4:** `npm run typecheck` → clean. Commit: `feat(interview): frontend interim types + api hooks`.

## Task 9: The `/interview` journey page

**Files:** Create `frontend/src/pages/Interview.tsx`; Modify `frontend/src/App.tsx:89`.

- [ ] **Step 1:** Build `Interview.tsx` using the `const s = {...} satisfies Record<string, CSSProperties>` idiom (match `JourneyHome`), wrapped in `<AppNav backTo="/" title="AI Opportunity Interview" />` + `<main>`. On mount, `getInterviewState()`; render: **welcome** (not_started) → intro copy + transparency notice + Start; **chat** (in_progress or after Start) → `useChat('interview')` in a sized container, plus a persistent "Build my playbook" button that calls `buildPlaybook()` then shows the playbook; **playbook** (complete) → `<Playbook shared={...} />`. Mirror the mockup's welcome/chat framing.
- [ ] **Step 2:** Swap `App.tsx:89` `ComingSoon` → `<Interview />` (keep the `session ? … : <Navigate to="/login">` guard).
- [ ] **Step 3:** `npm run typecheck && npm run lint` → clean. Commit: `feat(interview): interview journey page + route`.

## Task 10: The lightweight playbook render

**Files:** Create `frontend/src/components/interview/Playbook.tsx`.

- [ ] **Step 1:** Build `<Playbook shared={PlaybookShared} />` matching `docs/design-prototypes/ai-interviewer/mockup.html`: where_you_are_today, expandable use-case cards (difficulty badge colours: Quick Win green / Worth a Session amber / Bigger Build orange; Start Here highlight on rank 1), the "Your next moves" list, a reframes accordion, and the do_this_today CTA. Hub styling (`s`-object, brand hexes). v1 interactivity = expand/collapse only.
- [ ] **Step 2:** `npm run typecheck && npm run lint && npm run build` → clean. Commit: `feat(interview): lightweight in-hub playbook render`.

## Task 11: Admin interview section

**Files:** Create `frontend/src/pages/admin2/InterviewCard.tsx`; Modify `frontend/src/pages/admin2/UserDetailPage.tsx`.

- [ ] **Step 1:** `InterviewCard.tsx`: `useInterview(userId)`, render the `isLoading→Spinner / error→ErrorState / data→content / else→empty` ladder (mirror the Assessment card). Content: status + tier badge, the internal analysis (admin-only), the shared playbook (reuse `<Playbook>`), and the transcript as **plain text** (map messages to `<pre>`/escaped text — never `dangerouslySetInnerHTML`).
- [ ] **Step 2:** Mount a `<Card title="AI interview">` (full-width, below the `adm-grid-31`) in `UserDetailPage.tsx` wrapping `<InterviewCard userId={userId} />`.
- [ ] **Step 3:** `npm run typecheck && npm run lint && npm run build` → clean. Commit: `feat(interview): admin per-user interview view`.

---

## DB-gated runbook — for Aaron, tomorrow at the office

These are the ONLY steps that need DB / live-model access. Run in order from a checkout of `feature/ai-interviewer`.

1. **Set the LLM key** in `backend/.env`: `LLM__PROVIDER=anthropic`, `LLM__MODEL=claude-sonnet-5`, `LLM__API_KEY=<the hub/workspace key>`.
2. **Backend full suite (integration + authz vs the Azure test DB):** `cd backend && uv run poe test`. Expect green. This exercises the interview endpoints, the `require_ai_surface` 403, admin `require_admin`, ownership 404s, and `update_summary`. If red, fix before proceeding.
3. **Regenerate API types:** start the backend (`uv run poe dev`), then `cd frontend && npm run gen:api`. Then **swap the interim types** in `src/types/domain.ts` (and the `rawRequest` calls) to `components['schemas'][...]` aliases / typed `client.GET/POST` calls — a pure aliasing change (precedent: `domain.ts:47-88`). Re-run `npm run typecheck && npm run lint && npm run build`.
4. **Enable the surface:** in the admin panel, turn on the `interview` AI-surface toggle (and unlock the `interview` component) for a test project; put a test learner on it who has a completed assessment.
5. **Live interview:** as that learner, do a full interview, then "Build my playbook". Confirm a playbook renders.
6. **Firewall spot-check (critical):** in the browser network tab, confirm `GET /api/interview/me` and `POST /api/interview/playbook` responses contain **only `shared`** — no `internal` field anywhere. Then open the admin user-detail → AI interview card and confirm the internal analysis + tier + transcript render there.
7. **Browser walk:** welcome → chat → build → playbook, plus the admin card.
8. **Deploy:** a separate later decision (coordinate with Matthias; Batch A itself may not be deployed-live yet).

---

## Self-review notes

- **Spec coverage:** journey (T9), context injection (T3/T5), two-box summary + firewall (T2/T6/T7), prompts (T4), guardrails (reused Batch A rate limits + T7 gate + firewall test), admin read (T11), lightweight playbook incl. next_moves (T2/T10), no-migration (Global Constraints) — all mapped.
- **Type consistency:** `PlaybookShared`/`UseCase`/`NextMove`/`Reframe`/`DoThisToday` names identical across backend schema (T2) and frontend interim types (T8). `complete_structured` signature copied from the real Protocol. `update_summary` name identical in T1 and T6.
- **DB split:** every DB-touching verification is in the runbook, never in a tonight step.
