# Interviewer Round-2 Group A Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship the five code-side round-2 fixes for the live AI interviewer: keep the chat input focused, move the "Build playbook" button lower, sanitize em/en dashes out of generated playbooks, have the AI open the conversation, and make the hub JourneyHome "Interview" pill reflect real status.

**Architecture:** Small, additive changes inside the interview feature plus two FE-only tweaks. The one shared-contract touch is adding `interview_status` to `GET /api/me/journey` (hub-owned; no DB migration). The AI opener is a new isolated `POST /api/interview/opener` endpoint (design: `docs/superpowers/specs/2026-07-30-interviewer-opener-design.md`) — no changes to Matthias's shared `chat_service`/`routers/chat.py`/`useChat.ts`.

**Tech Stack:** Backend FastAPI (Python 3.13, `uv`), pytest. Frontend React 18 + TypeScript (Vite), no unit-test harness — verified by the gate.

## Global Constraints

- Backend commands run through uv: `UV_LINK_MODE=copy uv run --all-extras <cmd>` (e.g. `... pytest`, `... ruff check .`). Run from `backend/`.
- Frontend gate (there is **no** Vitest): `npm run typecheck && npm run lint && npm run build`, run from `frontend/`. Runtime behaviour is checked with a Playwright smoke, not unit tests.
- **No Alembic migration in this branch.** Every change here is code or derived status. The single migration chain (head `f9a0b1c2d3e4`) must stay untouched; coordinate with Matthias before ever adding one (not needed for Group A).
- **Do NOT edit `backend/prompts/interview.md` or `interview_playbook.md`.** The two prompt-tuning items (over-probing, em-dash prose rule) are Group B, held pending Matthias / the prompt-editor. Item 5 here is the **code** sanitizer for generated playbook content only.
- English-only. Frontend styling uses the hub design tokens (`--dlw-*`) already in `index.css`.
- Do not merge or deploy without Aaron's explicit go.
- Commit after every task (frequent commits). Branch: `feature/interviewer-feedback-r2`.

---

### Task 1: Chat input keeps focus every turn (item 2)

The `<textarea disabled={chat.loading}>` loses focus on send. Stop disabling it (send is already blocked while streaming), and refocus when streaming ends.

**Files:**
- Modify: `frontend/src/pages/Interview.tsx` (the `ChatScreen` component)

**Interfaces:**
- Consumes: `chat.loading: boolean`, `inputRef: RefObject<HTMLTextAreaElement>` (both already present).
- Produces: nothing new.

- [ ] **Step 1: Remove `disabled` from the textarea**

In `ChatScreen`'s `<textarea>` (currently ends with `maxLength={MAX_INPUT}` and `disabled={chat.loading}`), delete the `disabled={chat.loading}` line. The send button keeps `disabled={chat.loading || !input.trim()}`, and `submit()` already returns early when `chat.loading`, so no message can be sent mid-stream.

- [ ] **Step 2: Refocus the input when streaming ends**

Add this effect alongside the other `useEffect`s in `ChatScreen` (after the auto-grow effect):

```tsx
// Keep the input focused across turns: the textarea stays enabled (so it never
// loses focus on send), and we re-assert focus when a streamed reply finishes.
useEffect(() => {
  if (!chat.loading) inputRef.current?.focus()
}, [chat.loading])
```

- [ ] **Step 3: Run the frontend gate**

Run (from `frontend/`): `npm run typecheck && npm run lint && npm run build`
Expected: all pass, no errors.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/Interview.tsx
git commit -m "fix(interview): keep chat input focused every turn (round-2 item 2)"
```

---

### Task 2: Move the "Build playbook" button lower (item 1)

Move the reveal button out of the top toolbar to a footer row just above the input, keeping the `canBuild` reveal logic unchanged.

**Files:**
- Modify: `frontend/src/pages/Interview.tsx` (the `ChatScreen` component + the `s` style object)

**Interfaces:**
- Consumes: `canBuild`, `modelReady`, `onBuildPlaybook` (already computed/props in `ChatScreen`).
- Produces: nothing new.

- [ ] **Step 1: Remove the button from the top toolbar**

In `ChatScreen`'s `<div style={s.chatToolbar}>`, delete the `{canBuild && (<button ...>Build my playbook</button>)}` block. Leave the `<p style={s.chatToolbarHint}>…</p>` hint in place (the toolbar becomes hint-only).

- [ ] **Step 2: Add a build-footer row above the input form**

Add a style to the `s` object (near `chatForm`):

```ts
buildBar: {
  display: 'flex', justifyContent: 'flex-end', alignItems: 'center', gap: 12,
  padding: '10px 18px 0',
},
```

Then, immediately BEFORE the `<form onSubmit={onSubmit} style={s.chatForm}>` line, add:

```tsx
{canBuild && (
  <div style={s.buildBar}>
    <button
      type="button"
      className="btn-red"
      style={{ ...s.btnPrimary, ...s.btnSmall }}
      onClick={onBuildPlaybook}
    >
      Build my playbook
    </button>
  </div>
)}
```

- [ ] **Step 3: Run the frontend gate**

Run (from `frontend/`): `npm run typecheck && npm run lint && npm run build`
Expected: all pass.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/Interview.tsx
git commit -m "feat(interview): move Build playbook button to a footer by the input (round-2 item 1)"
```

---

### Task 3: Em-dash sanitizer for generated playbooks (item 5)

Strip em/en/horizontal-bar dashes from generated playbook content (shared + internal) before persisting and returning, as a belt-and-suspenders backstop to the prompt rule.

**Files:**
- Modify: `backend/src/services/interview_service.py`
- Test: `backend/tests/unit/test_interview_service.py`

**Interfaces:**
- Produces: `_sanitize_dashes(value: object) -> object` (module-level helper, recursive over str/list/dict).
- `InterviewService.build_playbook` now persists and returns dash-sanitized content.

- [ ] **Step 1: Write the failing test**

Add to `backend/tests/unit/test_interview_service.py` (it already imports `SimpleNamespace`, `FakeLlmClient`, `PlaybookShared`, `_EXTRACTION`, `_service`, `_conversation`, `_user`):

```python
async def test_build_playbook_strips_em_and_en_dashes() -> None:
    import copy

    dirty = copy.deepcopy(_EXTRACTION)
    dirty["shared"]["where_you_are_today"] = "You save time — a lot of it."
    dirty["internal"]["company_context"] = "Finance team – mid-size, inferred."
    llm = FakeLlmClient(chunks=[], structured=dirty)
    service, conversations, messages, _context = _service(llm)
    conversation = _conversation(summary=None)
    conversations.list_for_user.return_value = [conversation]
    messages.list_for_conversation.return_value = []
    user = _user()

    result = await service.build_playbook(user=user)  # ty: ignore[invalid-argument-type]

    assert "—" not in result.where_you_are_today
    assert "–" not in result.where_you_are_today
    assert "-" in result.where_you_are_today
    persisted = conversations.update_summary.await_args.args[1]
    blob = json.dumps(persisted, ensure_ascii=False)
    assert "—" not in blob and "–" not in blob
```

Add `import json` to the test file's imports if not present.

- [ ] **Step 2: Run the test to verify it fails**

Run (from `backend/`): `UV_LINK_MODE=copy uv run --all-extras pytest tests/unit/test_interview_service.py::test_build_playbook_strips_em_and_en_dashes -v`
Expected: FAIL (em dash still present in `result.where_you_are_today`).

- [ ] **Step 3: Add the sanitizer helper**

In `backend/src/services/interview_service.py`, add near the top (after `_READY_MARKER`):

```python
# Belt-and-suspenders to the prompt's no-dash rule: the model still occasionally
# emits em/en dashes. Normalise them to a plain hyphen in generated playbook
# content (both boxes) before persisting/returning. Recurses str/list/dict.
_DASH_CHARS = ("—", "–", "―")  # em dash, en dash, horizontal bar


def _sanitize_dashes(value: object) -> object:
    if isinstance(value, str):
        for ch in _DASH_CHARS:
            value = value.replace(ch, "-")
        return value
    if isinstance(value, list):
        return [_sanitize_dashes(v) for v in value]
    if isinstance(value, dict):
        return {k: _sanitize_dashes(v) for k, v in value.items()}
    return value
```

- [ ] **Step 4: Apply it in `build_playbook`**

Replace the tail of `build_playbook` (from `extraction = await self._generate(system)` onward):

```python
        extraction = await self._generate(system)
        summary = _sanitize_dashes(extraction.model_dump(mode="json"))
        await self._conversations.update_summary(conversation.id, summary)
        return PlaybookShared.model_validate(summary["shared"])
```

(Previously it persisted the raw dump and returned `extraction.shared`; now both come from the sanitized `summary`.)

- [ ] **Step 5: Run the new test + the full interview-service suite**

Run (from `backend/`):
`UV_LINK_MODE=copy uv run --all-extras pytest tests/unit/test_interview_service.py -v`
Expected: PASS (new test + all existing tests, including the idempotent/retry/marker tests).

- [ ] **Step 6: Commit**

```bash
git add backend/src/services/interview_service.py backend/tests/unit/test_interview_service.py
git commit -m "feat(interview): sanitize em/en dashes from generated playbooks (round-2 item 5)"
```

---

### Task 4: AI opener — backend endpoint, service method, schema (item 3)

New isolated endpoint that generates the personalised opener with a synthetic, non-persisted kickoff turn and persists only the assistant greeting.

**Files:**
- Modify: `backend/src/schemas/interview.py` (add `InterviewOpenerResponse`)
- Modify: `backend/src/services/interview_service.py` (add `open_interview`)
- Modify: `backend/src/routers/interview.py` (add `POST /api/interview/opener`)
- Test: `backend/tests/unit/test_interview_service.py`

**Interfaces:**
- Produces: `InterviewOpenerResponse(conversation_id: uuid.UUID, greeting: str)`.
- Produces: `InterviewService.open_interview(*, user: User) -> InterviewOpenerResponse`.
- Consumes: `self._context.build_briefing(user)` (exists on `InterviewContextService`), `self._llm.stream_reply(...)`, `self._conversations.create(user_id=, kind=)`, `self._conversations.touch(id)`, `self._messages.create(conversation_id, role=, content=, metadata=)`, `self._interview_conversation(user_id)` (existing private helper).

- [ ] **Step 1: Add the response schema**

In `backend/src/schemas/interview.py`, add the class (place it with the other API response shapes) and add `"InterviewOpenerResponse"` to `__all__`:

```python
class InterviewOpenerResponse(BaseModel):
    conversation_id: uuid.UUID
    greeting: str
```

- [ ] **Step 2: Write the failing service tests**

Add to `backend/tests/unit/test_interview_service.py` (import `RaisingLlmClient` from `tests.fixtures.llm` and `InterviewOpenerResponse` from `src.schemas.interview`):

```python
async def test_open_interview_fresh_generates_persists_and_returns_greeting() -> None:
    llm = FakeLlmClient(chunks=["Hi Aaron, ", "shall we begin?"])
    service, conversations, messages, context = _service(llm)
    context.build_briefing.return_value = "BRIEFING"
    conversations.list_for_user.return_value = []
    new_conv = _conversation(summary=None)
    conversations.create.return_value = new_conv
    user = _user()

    result = await service.open_interview(user=user)  # ty: ignore[invalid-argument-type]

    assert isinstance(result, InterviewOpenerResponse)
    assert result.conversation_id == new_conv.id
    assert result.greeting == "Hi Aaron, shall we begin?"
    # only the assistant greeting is persisted (no user turn)
    messages.create.assert_awaited_once()
    _pos, kw = messages.create.await_args.args, messages.create.await_args.kwargs
    assert kw["role"] == "assistant"
    assert kw["content"] == "Hi Aaron, shall we begin?"
    # the model saw a synthetic user kickoff and the briefing-grounded system prompt
    call = llm.calls[0]
    assert call["messages"][0]["role"] == "user"
    assert "BRIEFING" in call["system"]


async def test_open_interview_idempotent_returns_existing_greeting() -> None:
    llm = FakeLlmClient(chunks=["should not stream"])
    service, conversations, messages, _context = _service(llm)
    existing = _conversation(summary=None)
    conversations.list_for_user.return_value = [existing]
    messages.list_for_conversation.return_value = [
        SimpleNamespace(role="assistant", content="Hi Aaron, welcome back."),
    ]
    user = _user()

    result = await service.open_interview(user=user)  # ty: ignore[invalid-argument-type]

    assert result.conversation_id == existing.id
    assert result.greeting == "Hi Aaron, welcome back."
    assert llm.calls == []
    conversations.create.assert_not_awaited()
    messages.create.assert_not_awaited()


async def test_open_interview_llm_failure_creates_no_conversation() -> None:
    service, conversations, messages, context = _service(RaisingLlmClient())
    context.build_briefing.return_value = "BRIEFING"
    conversations.list_for_user.return_value = []
    user = _user()

    with pytest.raises(DomainError):
        await service.open_interview(user=user)  # ty: ignore[invalid-argument-type]

    conversations.create.assert_not_awaited()
    messages.create.assert_not_awaited()
```

- [ ] **Step 3: Run the tests to verify they fail**

Run (from `backend/`): `UV_LINK_MODE=copy uv run --all-extras pytest tests/unit/test_interview_service.py -k open_interview -v`
Expected: FAIL with `AttributeError: 'InterviewService' object has no attribute 'open_interview'`.

- [ ] **Step 4: Implement `open_interview`**

In `backend/src/services/interview_service.py`, add near the other module constants:

```python
_OPENER_MAX_TOKENS = 1024
_KICKOFF = "[Begin the interview now: greet me and ask your first question.]"
```

Import `InterviewOpenerResponse` in the schemas import block. Add the method to `InterviewService` (after `get_state`):

```python
    async def open_interview(self, *, user: User) -> InterviewOpenerResponse:
        """Generate the AI's opening greeting for a fresh interview. Idempotent:
        if a conversation already exists, return its first assistant message
        (no LLM call, no new conversation). Otherwise generate the greeting from
        a synthetic, non-persisted kickoff user turn and persist only the
        assistant turn, so the stored transcript starts with the assistant."""
        existing = await self._interview_conversation(user.id)
        if existing is not None:
            rows = await self._messages.list_for_conversation(existing.id)
            greeting = next((m.content for m in rows if m.role == "assistant"), "")
            return InterviewOpenerResponse(conversation_id=existing.id, greeting=greeting)

        system = f"{load_prompt(_KIND)}\n\n{await self._context.build_briefing(user)}"
        try:
            chunks: list[str] = []
            async with self._llm.stream_reply(
                system=system,
                messages=[{"role": "user", "content": _KICKOFF}],
                max_tokens=_OPENER_MAX_TOKENS,
            ) as reply:
                async for text in reply:
                    chunks.append(text)
            greeting = "".join(chunks).strip()
        except Exception as exc:  # noqa: BLE001 - best-effort opener; the UI offers retry
            raise DomainError("Could not start the interview - please try again.") from exc
        if not greeting:
            raise DomainError("Could not start the interview - please try again.")

        conversation = await self._conversations.create(user_id=user.id, kind=_KIND)
        await self._messages.create(
            conversation.id, role="assistant", content=greeting, metadata=None
        )
        await self._conversations.touch(conversation.id)
        return InterviewOpenerResponse(conversation_id=conversation.id, greeting=greeting)
```

Note: `load_prompt(_KIND)` reads `backend/prompts/interview.md` (unchanged — the greet-first instruction already lives there). If `ruff` flags the broad `except`, keep the `# noqa: BLE001` comment as written.

- [ ] **Step 5: Run the tests to verify they pass**

Run (from `backend/`): `UV_LINK_MODE=copy uv run --all-extras pytest tests/unit/test_interview_service.py -k open_interview -v`
Expected: PASS (all three).

- [ ] **Step 6: Add the route**

In `backend/src/routers/interview.py`, import `InterviewOpenerResponse` (add to the existing `from src.schemas.interview import (...)`) and add the route after `get_my_interview_state`:

```python
@router.post("/opener", response_model=InterviewOpenerResponse)
async def open_my_interview(
    current_user: CurrentUserDep,
    interview_service: InterviewServiceDep,
    limiter: RateLimiterDep,
) -> InterviewOpenerResponse:
    if limiter.is_limited(f"interview-opener:{current_user.id}", max_calls=10, window_seconds=600):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many interview starts - please wait a few minutes.",
            headers={"Retry-After": "600"},
        )
    if interview_service is None:
        raise _NOT_CONFIGURED
    return await interview_service.open_interview(user=current_user)
```

- [ ] **Step 7: Run the interview suite + lint/type checks**

Run (from `backend/`):
`UV_LINK_MODE=copy uv run --all-extras pytest tests/unit/test_interview_service.py -v`
`UV_LINK_MODE=copy uv run --all-extras ruff check src/services/interview_service.py src/routers/interview.py src/schemas/interview.py`
Expected: tests PASS; ruff clean (pre-existing repo noise elsewhere is out of scope).

- [ ] **Step 8: Commit**

```bash
git add backend/src/schemas/interview.py backend/src/services/interview_service.py backend/src/routers/interview.py backend/tests/unit/test_interview_service.py
git commit -m "feat(interview): AI opener endpoint POST /api/interview/opener (round-2 item 3)"
```

---

### Task 5: AI opener — frontend wiring (item 3)

Fire the opener once on a fresh start, show a brief typing state, hydrate via the existing `loadConversation`, and offer retry on failure. `useChat.ts` is not touched.

**Files:**
- Modify: `frontend/src/lib/interviewApi.ts` (add `openInterview`)
- Modify: `frontend/src/pages/Interview.tsx` (`Interview` page + `ChatScreen`)

**Interfaces:**
- Consumes (from Task 4): `POST /api/interview/opener -> { conversation_id: string; greeting: string }`.
- Produces: `openInterview(): Promise<{ conversation_id: string; greeting: string }>`.

- [ ] **Step 1: Add the API call**

In `frontend/src/lib/interviewApi.ts`, add (mirrors `buildPlaybook`'s `rawRequest` idiom — the interview endpoints are reached via the escape hatch, so no `gen:api` is needed for this one):

```ts
export async function openInterview(): Promise<{ conversation_id: string; greeting: string }> {
  const { data, error } = await rawRequest<{ conversation_id: string; greeting: string }>(
    'POST',
    '/api/interview/opener',
  )
  if (!data) throw new Error(errorMessage(error, 'Could not start the interview.'))
  return data
}
```

- [ ] **Step 2: Wire the opener into the `Interview` page**

In `frontend/src/pages/Interview.tsx`:

Update the import: `import { buildPlaybook, getInterviewState, openInterview } from '../lib/interviewApi'`.

Add state + a once-latch inside `Interview` (near the other `useState`s):

```tsx
const [opening, setOpening] = useState(false)
const [openError, setOpenError] = useState<string | null>(null)
const openedRef = useRef(false)
```

Add a start handler (define it inside `Interview`, above `return`):

```tsx
function runOpener() {
  setOpening(true)
  setOpenError(null)
  openInterview()
    .then(({ conversation_id }) => chat.loadConversation(conversation_id))
    .catch((e: unknown) =>
      setOpenError(e instanceof Error ? e.message : 'Could not start the interview.'),
    )
    .finally(() => setOpening(false))
}

function handleStart() {
  setPhase('chat')
  if (openedRef.current) return
  openedRef.current = true
  runOpener()
}
```

In the mount effect's resume branch, set the latch so the opener never fires on resume — change the `in_progress` branch to:

```tsx
        } else if (data.status === 'in_progress') {
          openedRef.current = true
          setPhase('chat')
          if (data.conversation_id) void chat.loadConversation(data.conversation_id)
        } else {
```

Change the welcome render to use the handler: `<WelcomeScreen onStart={handleStart} />`.

Pass the new props to `ChatScreen`: `<ChatScreen chat={chat} buildError={buildError} onBuildPlaybook={handleBuildPlaybook} opening={opening} openError={openError} onRetryOpen={runOpener} />`.

- [ ] **Step 3: Show the opening/typing + retry state in `ChatScreen`**

Extend `ChatScreenProps` and the messages area. Add to the interface:

```tsx
interface ChatScreenProps {
  chat: ReturnType<typeof useChat>
  buildError: string | null
  onBuildPlaybook: () => void
  opening: boolean
  openError: string | null
  onRetryOpen: () => void
}
```

Update the destructure: `function ChatScreen({ chat, buildError, onBuildPlaybook, opening, openError, onRetryOpen }: ChatScreenProps) {`.

Replace the empty-state hint block in the messages area:

```tsx
{chat.messages.length === 0 && opening && (
  <p style={s.emptyHint}>Starting the interview…</p>
)}
{chat.messages.length === 0 && !opening && openError && (
  <div style={{ textAlign: 'center', marginTop: 40 }}>
    <p style={s.chatError}>{openError}</p>
    <button type="button" className="btn-red" style={{ ...s.btnPrimary, ...s.btnSmall, marginTop: 12 }} onClick={onRetryOpen}>
      Try again
    </button>
  </div>
)}
{chat.messages.length === 0 && !opening && !openError && (
  <p style={s.emptyHint}>Say hello to begin the interview.</p>
)}
```

(The last line is the graceful fallback if a learner ends up here with no opener in flight.)

- [ ] **Step 4: Run the frontend gate**

Run (from `frontend/`): `npm run typecheck && npm run lint && npm run build`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/lib/interviewApi.ts frontend/src/pages/Interview.tsx
git commit -m "feat(interview): AI opens the conversation on a fresh interview (round-2 item 3)"
```

---

### Task 6: Interview status in the journey aggregate — backend (item 4)

Add `interview_status` to `GET /api/me/journey` so the hub can render the Interview pill. Reuse the existing conversation-based status logic via a lightweight `status_for`.

**Files:**
- Modify: `backend/src/services/interview_service.py` (add `status_for`)
- Modify: `backend/src/schemas/me.py` (add `interview_status`)
- Modify: `backend/src/routers/me.py` (inject interview service, populate the field)
- Test: `backend/tests/unit/test_interview_service.py`, `backend/tests/integration/test_routers/test_me.py`

**Interfaces:**
- Produces: `InterviewService.status_for(*, user: User) -> Literal["not_started", "in_progress", "complete"]`.
- Produces: `JourneyResponse.interview_status: Literal["not_started", "in_progress", "complete"]`.

- [ ] **Step 1: Write the failing unit test for `status_for`**

Add to `backend/tests/unit/test_interview_service.py`:

```python
async def test_status_for_reflects_conversation_state() -> None:
    llm = FakeLlmClient(chunks=[])
    service, conversations, _messages, _context = _service(llm)
    user = _user()

    conversations.list_for_user.return_value = []
    assert await service.status_for(user=user) == "not_started"  # ty: ignore[invalid-argument-type]

    conversations.list_for_user.return_value = [_conversation(summary=None)]
    assert await service.status_for(user=user) == "in_progress"  # ty: ignore[invalid-argument-type]

    conversations.list_for_user.return_value = [_conversation(summary=_EXTRACTION)]
    assert await service.status_for(user=user) == "complete"  # ty: ignore[invalid-argument-type]
```

- [ ] **Step 2: Run it to verify it fails**

Run (from `backend/`): `UV_LINK_MODE=copy uv run --all-extras pytest tests/unit/test_interview_service.py::test_status_for_reflects_conversation_state -v`
Expected: FAIL (`no attribute 'status_for'`).

- [ ] **Step 3: Implement `status_for`**

Add to `InterviewService` (after `get_state`), reusing the same conversation/summary logic without validating the playbook:

```python
    async def status_for(
        self, *, user: User
    ) -> Literal["not_started", "in_progress", "complete"]:
        """The journey-pill status, derived from the same source as get_state
        but without materialising the playbook."""
        conversation = await self._interview_conversation(user.id)
        if conversation is None:
            return "not_started"
        return "in_progress" if conversation.summary is None else "complete"
```

Add `from typing import Literal` if not already imported (currently only `TYPE_CHECKING` is imported from `typing`; change to `from typing import TYPE_CHECKING, Literal`).

- [ ] **Step 4: Run the unit test to verify it passes**

Run (from `backend/`): `UV_LINK_MODE=copy uv run --all-extras pytest tests/unit/test_interview_service.py::test_status_for_reflects_conversation_state -v`
Expected: PASS.

- [ ] **Step 5: Add `interview_status` to the schema**

In `backend/src/schemas/me.py`, add the field to `JourneyResponse`:

```python
class JourneyResponse(BaseModel):
    components: dict[str, ComponentState]
    survey_status: Literal["not_started", "in_progress", "complete"]
    learning_status: Literal["not_started", "in_progress", "complete"]
    interview_status: Literal["not_started", "in_progress", "complete"]
```

- [ ] **Step 6: Update the existing journey integration tests (they will now fail)**

In `backend/tests/integration/test_routers/test_me.py`, `test_defaults_without_project` asserts the full JSON. Add `"interview_status": "not_started",` to that expected dict (alongside `survey_status`/`learning_status`).

Then add a progression test in `class TestJourney` (imports `Conversation` from `src.db.models`, mirroring how `test_project_settings_override_defaults` adds rows via `db_session`):

```python
    async def test_interview_status_progression(
        self, client: AsyncClient, db_session: AsyncSession, test_settings: Settings
    ) -> None:
        from src.db.models import Conversation

        user = await create_user(db_session, email="journey-interview@example.com")
        headers = auth_headers(user, test_settings)

        assert (await client.get("/api/me/journey", headers=headers)).json()[
            "interview_status"
        ] == "not_started"

        conv = Conversation(user_id=user.id, kind="interview")
        db_session.add(conv)
        await db_session.commit()
        assert (await client.get("/api/me/journey", headers=headers)).json()[
            "interview_status"
        ] == "in_progress"

        conv.summary = {"internal": {}, "shared": {}}
        await db_session.commit()
        assert (await client.get("/api/me/journey", headers=headers)).json()[
            "interview_status"
        ] == "complete"
```

If the `Conversation` model requires more non-null fields than `user_id`/`kind` (check `src/db/models.py`), set them on construction; do not add a migration.

- [ ] **Step 7: Wire the endpoint**

In `backend/src/routers/me.py`, inject the interview service and populate the field. Add the import `from src.core.dependencies.interview import get_interview_service` and `from src.services.interview_service import InterviewService`, then update `get_journey`:

```python
@router.get("/journey", response_model=JourneyResponse)
async def get_journey(
    user: CurrentUserDep,
    org_service: Annotated[OrgService, Depends(get_org_service)],
    survey_service: Annotated[SurveyService, Depends(get_survey_service)],
    learning_service: Annotated[LearningService, Depends(get_learning_service)],
    interview_service: Annotated[InterviewService | None, Depends(get_interview_service)],
) -> JourneyResponse:
    components = await org_service.resolve_components(user.project_id)
    survey_status = await survey_service.survey_status(user.id)
    learning_status = await learning_service.learning_status(user.id)
    interview_status = (
        await interview_service.status_for(user=user)
        if interview_service is not None
        else "not_started"
    )
    return JourneyResponse(
        components={comp: ComponentState(**state) for comp, state in components.items()},
        survey_status=survey_status,
        learning_status=learning_status,
        interview_status=interview_status,
    )
```

- [ ] **Step 8: Run the journey tests + interview suite**

Run (from `backend/`):
`UV_LINK_MODE=copy uv run --all-extras pytest tests/integration/test_routers/test_me.py tests/unit/test_interview_service.py -v`
Expected: PASS (updated exact-match test, new progression test, `status_for` test).

- [ ] **Step 9: Commit**

```bash
git add backend/src/services/interview_service.py backend/src/schemas/me.py backend/src/routers/me.py backend/tests/unit/test_interview_service.py backend/tests/integration/test_routers/test_me.py
git commit -m "feat(journey): expose interview_status on /api/me/journey (round-2 item 4)"
```

---

### Task 7: Interview pill reflects status — frontend (item 4)

Add an `interview` branch to JourneyHome's status resolution and regenerate the API types so `interview_status` is available.

**Files:**
- Modify: `frontend/src/pages/JourneyHome.tsx`
- Modify (generated): `frontend/src/api/schema.d.ts` (via `npm run gen:api`)

**Interfaces:**
- Consumes (from Task 6): `GET /api/me/journey` now returns `interview_status`.

- [ ] **Step 1: Regenerate the API types**

The `gen:api` script reads a running backend's `/openapi.json`. With the backend running on `http://localhost:8000` (from `backend/`: `UV_LINK_MODE=copy uv run --all-extras uvicorn src.main:app --port 8000`), run (from `frontend/`): `npm run gen:api`.

Verify `interview_status` now appears on the journey response type:
Run: `git diff frontend/src/api/schema.d.ts` — expect the `/api/me/journey` response schema to gain `interview_status`.

If the backend cannot be started in this environment (DB/Entra unavailable), STOP and flag it — do not hand-edit `schema.d.ts` beyond a clearly-commented interim `interview_status` addition, and note that `gen:api` must be run before merge (mirrors the interviewer's interim-types dance, commit `952717d`).

- [ ] **Step 2: Add the `interview` branch in JourneyHome**

In `frontend/src/pages/JourneyHome.tsx`'s status-resolution loop (currently `assessment` / `learning` / `else`), add an `interview` branch before the final `else`, mirroring `learning`:

```tsx
        } else if (mod.key === 'interview') {
          if (locked) resolved[mod.key] = 'locked'
          else if (data.interview_status === 'complete') resolved[mod.key] = 'done'
          else if (data.interview_status === 'in_progress') resolved[mod.key] = 'in_progress'
          else resolved[mod.key] = 'available'
        } else {
```

- [ ] **Step 3: Run the frontend gate**

Run (from `frontend/`): `npm run typecheck && npm run lint && npm run build`
Expected: all pass (`data.interview_status` is now typed).

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/JourneyHome.tsx frontend/src/api/schema.d.ts
git commit -m "feat(journey): Interview pill reflects real status (round-2 item 4)"
```

---

## Final verification (after all tasks)

- [ ] **Full backend suite:** from `backend/`: `UV_LINK_MODE=copy uv run --all-extras pytest -q` — expect green (baseline was 1233 passed vs the Azure test DB).
- [ ] **Frontend gate:** from `frontend/`: `npm run typecheck && npm run lint && npm run build` — expect clean.
- [ ] **Playwright smoke** (verifies the runtime behaviour the unit tests can't): with the app running, log in as an interview-enabled learner and confirm: (item 3) the AI greets first with no user bubble; (item 2) the input stays focused after each reply; (item 1) the Build button sits by the input; (item 4) after completing an interview the JourneyHome "Interview" pill reads In progress / Completed, not "Not started".
- [ ] **Clean-merge check** against `origin/main`, then STOP for Aaron's go before merge/deploy (coordinate the single alembic chain — none added here — and shared prompt files with Matthias). Group B items 6 & 7 (prompt tuning) remain held.

## Self-Review notes

- **Spec coverage:** items 1 (Task 2), 2 (Task 1), 3 (Tasks 4–5), 4 (Tasks 6–7), 5 (Task 3) — all five Group A items map to tasks. Group B (6, 7) intentionally excluded.
- **Type consistency:** `open_interview -> InterviewOpenerResponse{conversation_id, greeting}` is produced in Task 4 and consumed verbatim by `openInterview()` in Task 5; `status_for -> Literal[...]` (Task 6) feeds `interview_status` on `JourneyResponse` (Task 6) consumed by JourneyHome (Task 7).
- **No migration / no shared-chat edits:** confirmed across all tasks; the only shared contract touched is `/api/me/journey` (hub-owned), regenerated via `gen:api`.
