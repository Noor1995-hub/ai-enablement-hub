# AI-layer resilience + rate-limit hardening — Implementation Plan

> **Status 2026-09-29: DONE, live since 2026-09-28.** B1 #73 · B2+B3 #74 · B4 #75 · B7+B8 #76 ·
> B9 #77 · **B0 (new)** + B5 + B6 #78. Deviations from the text below, all in the PRs:
> - **B0 was added.** The client IP could be spoofed through the leftmost X-Forwarded-For entry (lessons.md, 2026-09-25).
> - B2 stores a per-key window and evicts with batch headroom.
> - B5 allows 300 per 5 min per IP.
> - B6 counts failed logins only: 100 per 5 min, charged on arrival and refunded on success in the same window.
> - B7/B8 were reconciled with #81: its single 180 s playbook budget stays, and #76 adds the 45 s opener timeout and 502s.
> - B9 gives mid-stream overloads the busy wording.
> Follow-ups: #79, #80.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make every failure path the AI layer can actually hit produce a useful, bounded, standard-shaped response instead of a hung request or a bare 500 — and close the four rate-limiter gaps (`CODE-REVIEW-2026-07-31.md` items **2.4**, **2.6**, **7.1**, **7.2**, **7.3**).

**Architecture:** Four independent seams, all inside existing layers. (1) `main.py` gains a catch-all `Exception` handler so the `{"error":{code,message}}` contract holds on paths no domain handler claims. (2) `core/ratelimit.py` gains `sweep()` + a hard key ceiling, swept once a day from the existing lifespan maintenance task. (3) Two learner-facing POSTs and the login path gain limiter calls at the router edge, where every other limit already lives. (4) `interview_service.py` gets explicit `asyncio.timeout` budgets and consults `is_transient_provider_error` to raise `AiGenerationError` (→502), and `chat_service.send_message` gains a terminal `error` SSE frame for the one case where HTTP status is no longer available.

**Tech Stack:** Python 3.13 / uv, FastAPI, async SQLAlchemy 2, Anthropic SDK (`anthropic~=0.119` per `uv.lock`), pytest + pytest-asyncio (auto mode), httpx `ASGITransport`.

## Global Constraints

- **Layering is strict:** `routers/ → services/ → repositories/ → db/models`. Calls flow downward only, and **services never call other services** (the interview slice's existing violation of this is out of scope here — it is owned by `2026-07-31-fix-backend-consistency.md` Task 1). Routers hold no business logic; repositories hold no business logic.
- **Verification for every task, run inside `backend/`:**
  ```
  uv run poe format && uv run poe lint && uv run poe test
  ```
  Individual-test commands in each task are for the red/green loop; the three-command sweep is what gates the commit.
- **Integration tests hit the shared remote `ai-enablement-hub-test` Postgres** (an approved deviation from the template's in-memory SQLite). They are slower than unit tests, they are marked `flaky(reruns=1)` by `tests/conftest.py`, and under `-n auto` each xdist worker gets its own schema. Never point them anywhere else; `conftest.py` hard-asserts the DB name ends in `-test`.
- **FastAPI deferred-annotation gotcha:** every module here has `from __future__ import annotations`, so FastAPI evaluates parameter annotations as *strings* against module globals. Any type used in a **parameter annotation of a route function or a `Depends` provider** must be imported at **runtime**, never under `if TYPE_CHECKING:` — an unresolvable name silently degrades the parameter into a required query param and the endpoint 422s on every call. This bites Task 5 and Task 6 (`Request`) directly. `src/core/dependencies/database.py` and `src/core/dependencies/interview.py` both carry this warning in their module docstrings; keep it that way.
- **No Alembic migration in this plan.** Persisting rate-limit counters to Postgres would need one (and is entangled with the single-replica decision) — it is explicitly deferred, see "Deferred follow-ups".
- **`__all__` and `from __future__ import annotations` in every module touched** — 100% of `src` currently has both; do not be the first exception.
- **Single replica is load-bearing.** The in-process limiter and the daily maintenance task are correct only because `infra/containerapp.yaml` pins min=max=1. Any change here must keep that assumption written down, not just true.

---

## File structure

**Backend — modify:**
- `backend/src/main.py` — catch-all handler; `_ERROR_CODES[500]`; rename + extend the daily maintenance task.
- `backend/src/core/ratelimit.py` — `sweep()`, key ceiling, eviction, module logger.
- `backend/src/routers/feedback.py` — limiter on `POST /api/feedback`.
- `backend/src/routers/auth.py` — limiter on `POST /api/auth/refresh`; per-IP counter on `POST /api/auth/login`.
- `backend/src/services/interview_service.py` — `asyncio` import, two timeout constants, transient→`AiGenerationError`.
- `backend/src/services/chat_service.py` — `ErrorEvent`, mid-stream provider-failure branch, module logger.
- `backend/src/routers/chat.py` — emit the `error` SSE frame.

**Backend — modify (tests):**
- `backend/tests/unit/test_ratelimit.py`, `test_interview_service.py`, `test_chat_service.py`
- `backend/tests/integration/test_cross_cutting.py`, `test_routers/test_feedback.py`, `test_routers/test_chat.py`

**Nothing in `frontend/` is touched by this plan.** Task 9 adds a *new* SSE event name; unknown event names are ignored by the current client, so it is additive. Wiring the frontend to render it is listed under "Deferred follow-ups".

---

## Task 1: Catch-all 500 handler in the standard error envelope

Closes review item **2.4**. `docs/design/design-backend.md:242` already promises this shape; `main.py` never delivered it.

**Files:**
- Modify `backend/src/main.py` (`_ERROR_CODES` dict at ~L209-221; new handler after `validation_exception_handler`, ~L286-306)
- Modify `backend/tests/integration/test_cross_cutting.py` (append a new test class at the end)

**Interfaces:**
- *Consumes:* `_error_response(status_code, message, headers=None) -> JSONResponse` (already in `main.py`), module `logger` (already at `main.py:68`).
- *Produces:* `unhandled_exception_handler(request, exc) -> JSONResponse` returning `{"error": {"code": "internal_error", "message": "Something went wrong. Please try again."}}` with status 500. Tasks 8 and 9 rely on this being the floor under any provider error they do not classify.

- [ ] **Step 1: Write the failing test**

  Append to `backend/tests/integration/test_cross_cutting.py`. Note the two non-obvious details, both real and both required:
  - Starlette's `ServerErrorMiddleware` **sends** the handler's response and then **re-raises** the original exception so the ASGI server logs it. Under `httpx.ASGITransport` that re-raise reaches the test unless the transport is built with `raise_app_exceptions=False`. In production (uvicorn) the client gets the JSON body. So this test needs its own client.
  - The failure is injected by overriding a real DI provider, so the assertion exercises the real middleware/handler stack rather than a synthetic route.

  ```python
  class TestUnhandledErrorEnvelope:
      """A bug no domain handler claims must still answer in the standard shape.

      `raise_app_exceptions=False` is required, not cosmetic: Starlette's
      ServerErrorMiddleware sends the 500 response and then re-raises so the ASGI
      server can log it, and httpx's ASGITransport surfaces that re-raise to the
      caller by default. Uvicorn swallows it after logging, so a real browser sees
      the JSON body this test asserts on.
      """

      async def test_unexpected_exception_returns_the_error_envelope(
          self, db_session: AsyncSession, test_settings: Settings
      ) -> None:
          class _ExplodingFeedbackService:
              async def submit(self, *_args: object, **_kwargs: object) -> None:
                  msg = "database went away"
                  raise RuntimeError(msg)

          async def _override_session() -> AsyncGenerator[AsyncSession]:
              yield db_session

          user = await create_user(db_session, email="envelope-500@example.com")
          app.dependency_overrides[get_session] = _override_session
          app.dependency_overrides[get_settings] = lambda: test_settings
          app.dependency_overrides[get_feedback_service] = _ExplodingFeedbackService
          transport = ASGITransport(app=app, raise_app_exceptions=False)
          try:
              async with AsyncClient(transport=transport, base_url="http://testserver") as client:
                  response = await client.post(
                      "/api/feedback",
                      json={"lesson_id": str(uuid.uuid4()), "message": "boom"},
                      headers=auth_headers(user, test_settings),
                  )
          finally:
              app.dependency_overrides.clear()

          assert response.status_code == 500
          assert response.json() == {
              "error": {
                  "code": "internal_error",
                  "message": "Something went wrong. Please try again.",
              }
          }

      async def test_the_message_never_leaks_the_exception(
          self, db_session: AsyncSession, test_settings: Settings
      ) -> None:
          """The client gets a fixed sentence; the cause goes to the log only."""
          class _ExplodingFeedbackService:
              async def submit(self, *_args: object, **_kwargs: object) -> None:
                  msg = "connection to db-secret-host:5432 failed"
                  raise RuntimeError(msg)

          async def _override_session() -> AsyncGenerator[AsyncSession]:
              yield db_session

          user = await create_user(db_session, email="envelope-500b@example.com")
          app.dependency_overrides[get_session] = _override_session
          app.dependency_overrides[get_settings] = lambda: test_settings
          app.dependency_overrides[get_feedback_service] = _ExplodingFeedbackService
          transport = ASGITransport(app=app, raise_app_exceptions=False)
          try:
              async with AsyncClient(transport=transport, base_url="http://testserver") as client:
                  response = await client.post(
                      "/api/feedback",
                      json={"lesson_id": str(uuid.uuid4()), "message": "boom"},
                      headers=auth_headers(user, test_settings),
                  )
          finally:
              app.dependency_overrides.clear()

          assert "db-secret-host" not in response.text
  ```

  Add the imports this needs to the top of `test_cross_cutting.py` (it already imports `ASGITransport`, `AsyncClient`, `get_session`, `get_settings`, `app`, `create_user`, and `AsyncGenerator` under `TYPE_CHECKING`):
  ```python
  import uuid

  from src.core.dependencies.domain import get_feedback_service
  from tests.fixtures.auth import auth_headers
  ```

- [ ] **Step 2: Run test to verify it fails**
  ```
  cd backend && uv run pytest tests/integration/test_cross_cutting.py::TestUnhandledErrorEnvelope -v
  ```
  Expected failure: both tests fail. Without a registered `Exception` handler, `ServerErrorMiddleware` has no `handler`, so it re-raises immediately without sending anything and `raise_app_exceptions=False` leaves httpx to synthesise nothing — you will see either `RuntimeError: database went away` or a plain-text 500 whose body is `Internal Server Error`, so `response.json()` raises `json.JSONDecodeError`. Any of those three is the expected red.

- [ ] **Step 3: Write minimal implementation**

  In `backend/src/main.py`, add `500` to the code map (keep the dict's existing ascending order, insert before `502`):
  ```python
      429: "rate_limited",
      500: "internal_error",
      502: "bad_gateway",
  ```

  Then add the handler immediately after `validation_exception_handler` (i.e. after `main.py:306`, before `@app.get("/api/health")`):
  ```python
  @app.exception_handler(Exception)
  async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
      """Last resort, so the {"error":{code,message}} contract holds even on a
      path no domain handler claims — an Anthropic 529, a bare `LlmError`, a
      dropped DB connection.

      The message is a fixed sentence on purpose: `exc` can carry a hostname, a
      SQL fragment or a provider payload, and the frontend renders
      `error.message` verbatim. The detail goes to the log via
      `logger.exception` and nowhere else.

      Starlette's ServerErrorMiddleware re-raises after this returns, so uvicorn
      still records the traceback — registering this handler suppresses nothing.
      """
      logger.exception("unhandled error on %s %s", request.method, request.url.path)
      return _error_response(500, "Something went wrong. Please try again.")
  ```
  No new imports: `Request`, `JSONResponse` and `logger` are already in scope at `main.py:9`, `:12` and `:68`.

- [ ] **Step 4: Run test to verify it passes**
  ```
  cd backend && uv run pytest tests/integration/test_cross_cutting.py -v
  ```
  All of `TestUnhandledErrorEnvelope`, `TestTokenCleanup`, `TestLoginRateLimit`, `TestSetPasswordRateLimit`, `TestCors` and `TestContentSecurityPolicy` must be green. Then the gate:
  ```
  cd backend && uv run poe format && uv run poe lint && uv run poe test
  ```

  **Existing tests likely to break:** none expected. The one theoretical risk is a test that *relies* on an exception escaping the app (asserting `pytest.raises` around a client call); grep confirms there is none — no test file calls `ASGITransport` with `raise_app_exceptions` today, and no test wraps a `client.` call in `pytest.raises`. If `tests/integration/test_routers/test_authz.py` (the endpoint × auth-level sweep) turns red, it means a route was raising an unhandled error that previously surfaced as a test error and now returns 500 — that is a genuine finding, not a regression of this task.

- [ ] **Step 5: Commit**
  ```
  git add backend/src/main.py backend/tests/integration/test_cross_cutting.py
  git commit -m "Add catch-all 500 handler in the standard error envelope

Review item 2.4: main.py mapped nine domain exceptions but nothing else, so an
Anthropic 529, a bare LlmError or a DB failure returned Starlette's plain-text
500 and broke the {\"error\":{code,message}} contract the frontend parses.
design-backend.md already promised this handler.

The message is fixed text; the cause goes to logger.exception only."
  ```

---

## Task 2: Bound the rate-limiter store

Closes the "store never evicts" half of review items **2.6** / **7.3**. Pure module, no I/O, no callers changed — smallest possible blast radius.

**Files:**
- Modify `backend/src/core/ratelimit.py` (whole file is 41 lines; `_store` at `:22`, `is_limited` at `:24-32`)
- Modify `backend/tests/unit/test_ratelimit.py` (append to `TestRateLimiter`, add a new class)

**Interfaces:**
- *Consumes:* nothing new.
- *Produces:* `RateLimiter.sweep(*, older_than: float = _MAX_TRACKED_WINDOW_SECONDS) -> int` — drops counters whose window started more than `older_than` seconds ago, returns how many were removed. Task 3 calls exactly this signature. `RateLimiter.is_limited` keeps its current signature `(key: str, *, max_calls: int = 5, window_seconds: float = 60.0) -> bool`.

- [ ] **Step 1: Write the failing test**

  Append to `backend/tests/unit/test_ratelimit.py`:
  ```python
  class TestSweep:
      """`sweep` is what keeps the process-global store from growing forever.
      It must be loss-free: a counter is only droppable once its window can no
      longer affect a decision."""

      def test_sweep_drops_counters_past_the_longest_window(self) -> None:
          clock = FakeClock()
          limiter = RateLimiter(clock=clock)
          limiter.is_limited("stale-key")
          clock.now += 86_401  # one second past the longest window in use (chat-daily)

          assert limiter.sweep() == 1

      def test_sweep_keeps_a_counter_that_can_still_bite(self) -> None:
          """A chat-daily counter is 24h wide; sweeping it early would hand back
          an AI-spend allowance the caller already used up."""
          clock = FakeClock()
          limiter = RateLimiter(clock=clock)
          for _ in range(200):
              limiter.is_limited("chat-daily:u1", max_calls=200, window_seconds=86_400)
          clock.now += 3_600  # an hour later, still inside the daily window

          assert limiter.sweep() == 0
          assert limiter.is_limited("chat-daily:u1", max_calls=200, window_seconds=86_400) is True

      def test_a_swept_key_starts_from_zero(self) -> None:
          clock = FakeClock()
          limiter = RateLimiter(clock=clock)
          for _ in range(6):
              limiter.is_limited("k")
          clock.now += 86_401
          limiter.sweep()

          assert limiter.is_limited("k") is False

      def test_sweep_honours_an_explicit_window(self) -> None:
          clock = FakeClock()
          limiter = RateLimiter(clock=clock)
          limiter.is_limited("k")
          clock.now += 120

          assert limiter.sweep(older_than=60) == 1


  class TestCapacityCeiling:
      """The store is a plain dict in a single-replica process. A flood of unique
      keys (spoofed X-Forwarded-For, enumerated emails) is the only realistic way
      to grow it, and an unbounded dict is a worse failure than a reset counter."""

      def test_new_keys_cannot_grow_the_store_without_limit(
          self, monkeypatch: pytest.MonkeyPatch
      ) -> None:
          monkeypatch.setattr(ratelimit, "_MAX_KEYS", 10)
          monkeypatch.setattr(ratelimit, "_EVICTION_BATCH", 2)
          clock = FakeClock()
          limiter = RateLimiter(clock=clock)
          for i in range(50):
              clock.now += 1  # distinct window starts, so "oldest" is well-defined
              limiter.is_limited(f"flood-{i}")

          assert len(limiter._store) <= 10

      def test_stale_counters_are_evicted_before_live_ones(
          self, monkeypatch: pytest.MonkeyPatch
      ) -> None:
          monkeypatch.setattr(ratelimit, "_MAX_KEYS", 3)
          monkeypatch.setattr(ratelimit, "_EVICTION_BATCH", 1)
          clock = FakeClock()
          limiter = RateLimiter(clock=clock)
          limiter.is_limited("ancient")
          clock.now += 86_401
          limiter.is_limited("live-a")
          limiter.is_limited("live-b")
          limiter.is_limited("live-c")  # trips the ceiling; "ancient" is the free win

          assert "ancient" not in limiter._store
          assert {"live-a", "live-b", "live-c"} <= set(limiter._store)

      def test_evicting_a_live_counter_is_logged(
          self, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
      ) -> None:
          """Reaching this branch means someone is manufacturing keys — it must
          leave a signal, not silently forgive them."""
          monkeypatch.setattr(ratelimit, "_MAX_KEYS", 2)
          monkeypatch.setattr(ratelimit, "_EVICTION_BATCH", 1)
          clock = FakeClock()
          limiter = RateLimiter(clock=clock)
          with caplog.at_level(logging.WARNING, logger="src.core.ratelimit"):
              for i in range(5):
                  clock.now += 1
                  limiter.is_limited(f"k{i}")

          assert any("ceiling" in record.message for record in caplog.records)
  ```
  Add to the imports at the top of the file (it currently imports only `RateLimiter`):
  ```python
  import logging

  import pytest

  from src.core import ratelimit
  from src.core.ratelimit import RateLimiter
  ```
  (`limiter._store` is read directly in two assertions. That is deliberate: the ceiling is an internal-memory invariant with no public read, and inventing a `__len__` just for the test would be worse. Note it in the test class docstring if ruff's private-access rules are ever widened.)

- [ ] **Step 2: Run test to verify it fails**
  ```
  cd backend && uv run pytest tests/unit/test_ratelimit.py -v
  ```
  Expected failure: `AttributeError: 'RateLimiter' object has no attribute 'sweep'` on the four `TestSweep` tests, and `AttributeError: module 'src.core.ratelimit' has no attribute '_MAX_KEYS'` from `monkeypatch.setattr` on the three `TestCapacityCeiling` tests. The seven pre-existing `TestRateLimiter` tests stay green.

- [ ] **Step 3: Write minimal implementation**

  Rewrite `backend/src/core/ratelimit.py` as follows (the module docstring's honesty about per-replica counters is kept and extended):
  ```python
  """In-process fixed-window rate limiter — port of the legacy rateLimit.js.

  Same semantics as the original: one counter per key, window restarts when the
  previous one is stale, attempts past the limit still count (a hammering client
  never escapes the window). Honest limitation, unchanged from the JS version:
  counters live in process memory, so they reset on restart and are per-replica.
  Fine for a single local process / one Container Apps replica; move the
  counters to a PG table if the app ever scales out.

  The store is bounded two ways, because a dict keyed by client-supplied values
  (an email, an X-Forwarded-For hop) is otherwise a memory leak with a public
  trigger: `sweep()` drops counters whose window can no longer affect a decision
  (called daily from main.py's maintenance task), and `_MAX_KEYS` caps the dict
  outright.
  """

  from __future__ import annotations

  import logging
  import time
  from collections.abc import Callable

  __all__ = ["RateLimiter", "rate_limiter"]

  logger = logging.getLogger(__name__)

  # The widest window any caller uses today (`chat-daily`, 86400s in
  # routers/chat.py). A counter whose window started longer ago than this can
  # never change an answer again, so dropping it is loss-free. Raise this if a
  # caller ever passes a window_seconds larger than it.
  _MAX_TRACKED_WINDOW_SECONDS = 86_400.0
  # Hard ceiling on distinct keys (~100k entries is single-digit MB). Normal
  # traffic is nowhere near it: keys are per-user or per-IP.
  _MAX_KEYS = 100_000
  # How many extra keys to reclaim once the ceiling is hit, so the eviction sort
  # runs once per batch instead of once per request.
  _EVICTION_BATCH = 1_000


  class RateLimiter:
      def __init__(self, clock: Callable[[], float] = time.monotonic) -> None:
          self._clock = clock
          self._store: dict[str, tuple[float, int]] = {}

      def is_limited(self, key: str, *, max_calls: int = 5, window_seconds: float = 60.0) -> bool:
          """Record one attempt for `key`; True when the attempt exceeds the limit."""
          now = self._clock()
          existing = self._store.get(key)
          if existing is None and len(self._store) >= _MAX_KEYS:
              self._make_room()
          window_start, count = existing if existing is not None else (now, 0)
          if now - window_start > window_seconds:
              window_start, count = now, 0
          count += 1
          self._store[key] = (window_start, count)
          return count > max_calls

      def sweep(self, *, older_than: float = _MAX_TRACKED_WINDOW_SECONDS) -> int:
          """Drop counters whose window started more than `older_than` seconds
          ago and return how many went. Loss-free at the default: such a counter
          is already outside every caller's window, so it could only ever have
          answered False.

          Called once a day from main.py's maintenance loop, which means a stale
          counter can linger for up to ~48h before collection. That is fine —
          this is a memory bound, not a correctness mechanism.
          """
          cutoff = self._clock() - older_than
          stale = [key for key, (window_start, _) in self._store.items() if window_start < cutoff]
          for key in stale:
              del self._store[key]
          return len(stale)

      def _make_room(self) -> None:
          """Reclaim space for a new key once `_MAX_KEYS` is reached.

          Stale counters go first and cost nothing. If the store is still full
          after that, the OLDEST windows are dropped, which DOES forgive a live
          counter — potentially a `chat-daily` AI-spend allowance. That is the
          deliberate trade: an unbounded dict in a single-replica process is the
          worse failure. Reaching this branch means someone is manufacturing
          keys, so it logs; that log line is the signal to add a real store.
          """
          self.sweep()
          if len(self._store) < _MAX_KEYS:
              return
          overflow = len(self._store) - _MAX_KEYS + _EVICTION_BATCH
          oldest = sorted(self._store.items(), key=lambda item: item[1][0])[:overflow]
          for key, _counter in oldest:
              del self._store[key]
          logger.warning(
              "rate-limiter store hit its %d-key ceiling; evicted %d live counter(s)",
              _MAX_KEYS,
              len(oldest),
          )

      def reset(self) -> None:
          """Clear all counters (tests)."""
          self._store.clear()


  # Single shared instance; injected via core.dependencies.ratelimit.get_rate_limiter.
  rate_limiter = RateLimiter()
  ```

- [ ] **Step 4: Run test to verify it passes**
  ```
  cd backend && uv run pytest tests/unit/test_ratelimit.py -v
  cd backend && uv run poe format && uv run poe lint && uv run poe test
  ```

  **Existing tests likely to break:** none. All seven `TestRateLimiter` tests use one or two keys and the default 60s window, far below `_MAX_KEYS`; `is_limited`'s observable behaviour is unchanged (the refactor from `self._store.get(key, (now, 0))` to an explicit `existing` local is behaviour-identical). `tests/conftest.py`'s autouse `_reset_rate_limiter` still works — `reset()` is untouched.

- [ ] **Step 5: Commit**
  ```
  git add backend/src/core/ratelimit.py backend/tests/unit/test_ratelimit.py
  git commit -m "Bound the rate-limiter store (sweep + key ceiling)

Review items 2.6/7.3: the limiter's dict is keyed by client-supplied values
(submitted email, client IP) and never evicted, so key growth was unbounded with
a public trigger.

sweep() drops counters whose window can no longer affect a decision (loss-free);
_MAX_KEYS caps the dict outright, preferring stale keys and logging when it has
to forgive a live counter. No caller changes; is_limited's behaviour is
unchanged."
  ```

---

## Task 3: Sweep the limiter from the daily maintenance task

Wires Task 2's `sweep()` to a clock. Also renames the lifespan task, which now does two jobs rather than one.

**Files:**
- Modify `backend/src/main.py` (`_auth_cleanup_loop` at `:77-99`; `lifespan` call site at `:119`)
- Modify `backend/tests/integration/test_cross_cutting.py` (extend `TestTokenCleanup`)

**Interfaces:**
- *Consumes:* `RateLimiter.sweep()` (Task 2), `TokenService.purge_expired() -> tuple[int, int]` (unchanged).
- *Produces:* `_run_daily_maintenance(engine: AsyncEngine, auth_settings: AuthSettings) -> tuple[int, int, int]` returning `(tokens_deleted, sessions_deleted, limiter_keys_swept)`, and `_daily_maintenance_loop(engine, auth_settings) -> None` which calls it forever. Extracting the body is what makes the work testable at all — the current `while True: ... await asyncio.sleep(86400)` shape has no seam.

- [ ] **Step 1: Write the failing test**

  Append to the existing `TestTokenCleanup` class in `backend/tests/integration/test_cross_cutting.py`:
  ```python
      async def test_daily_maintenance_purges_tokens_and_sweeps_the_limiter(
          self, engine: AsyncEngine, test_settings: Settings
      ) -> None:
          """The maintenance pass does two jobs now. The limiter half is asserted
          exactly; the DB half is asserted loosely on purpose — this function
          opens its OWN AsyncSession on the engine and commits outside the
          `db_session` fixture's rolled-back transaction, so it must not depend on
          rows another test planted. Row-level purge behaviour is pinned by
          test_purge_expired_removes_only_dead_rows above.
          """
          rate_limiter.is_limited("maintenance-probe")
          # Backdate the counter past the longest tracked window so the sweep is
          # entitled to collect it (the store holds monotonic timestamps).
          window_start, count = rate_limiter._store["maintenance-probe"]
          rate_limiter._store["maintenance-probe"] = (window_start - 86_401, count)

          tokens, sessions, swept = await _run_daily_maintenance(engine, test_settings.auth)

          assert swept >= 1
          assert "maintenance-probe" not in rate_limiter._store
          assert tokens >= 0
          assert sessions >= 0
  ```
  Add to `test_cross_cutting.py`'s imports:
  ```python
  from src.core.ratelimit import rate_limiter
  from src.main import _run_daily_maintenance
  ```
  (`AsyncEngine` is already imported under `TYPE_CHECKING`; `app` is already imported from `src.main`, so extend that line rather than adding a second import.)

- [ ] **Step 2: Run test to verify it fails**
  ```
  cd backend && uv run pytest "tests/integration/test_cross_cutting.py::TestTokenCleanup::test_daily_maintenance_purges_tokens_and_sweeps_the_limiter" -v
  ```
  Expected failure: collection fails at import time with `ImportError: cannot import name '_run_daily_maintenance' from 'src.main'`.

- [ ] **Step 3: Write minimal implementation**

  In `backend/src/main.py`, replace `_auth_cleanup_loop` (`:77-99`) with:
  ```python
  async def _run_daily_maintenance(
      engine: AsyncEngine, auth_settings: AuthSettings
  ) -> tuple[int, int, int]:
      """One maintenance pass: purge expired invite/reset tokens and dead refresh
      sessions (fixes DB2), then drop rate-limiter counters that can no longer
      affect a decision.

      Returns (tokens_deleted, sessions_deleted, limiter_keys_swept). Split out
      of the loop below so it can be tested without waiting 24 hours.
      """
      async with AsyncSession(engine, expire_on_commit=False) as session:
          token_service = TokenService(
              UserRepository(session),
              AuthTokenRepository(session),
              AuthSessionRepository(session),
              auth_settings,
          )
          tokens_deleted, sessions_deleted = await token_service.purge_expired()
      # In-process and per-replica by design (see core/ratelimit.py) — safe to do
      # here precisely because the app runs a single replica.
      swept = rate_limiter.sweep()
      return tokens_deleted, sessions_deleted, swept


  async def _daily_maintenance_loop(engine: AsyncEngine, auth_settings: AuthSettings) -> None:
      """Runs one maintenance pass at startup, then every 24 h. No pg_cron
      dependency. A failure is logged and retried next interval — this task must
      never be the reason the app goes down."""
      while True:
          try:
              tokens_deleted, sessions_deleted, swept = await _run_daily_maintenance(
                  engine, auth_settings
              )
              logger.info(
                  "daily maintenance: deleted %d expired tokens, %d dead sessions, "
                  "swept %d rate-limiter keys",
                  tokens_deleted,
                  sessions_deleted,
                  swept,
              )
          except Exception:
              logger.exception("daily maintenance failed; retrying next interval")
          await asyncio.sleep(_CLEANUP_INTERVAL_SECONDS)
  ```
  Add the runtime import near the other `src.` imports (this is *not* a parameter annotation, so `TYPE_CHECKING` would also work — but the module already imports `rate_limiter`'s siblings at runtime and the value is used at runtime):
  ```python
  from src.core.ratelimit import rate_limiter
  ```
  Update the `lifespan` call site (`main.py:119`):
  ```python
      cleanup_task = asyncio.create_task(_daily_maintenance_loop(engine, settings.auth))
  ```
  `AsyncEngine` and `AuthSettings` are already imported under `TYPE_CHECKING` (`main.py:61,63`) and both are used only in this function's *own* annotations — not a FastAPI-inspected parameter — so leaving them there is correct.

- [ ] **Step 4: Run test to verify it passes**
  ```
  cd backend && uv run pytest tests/integration/test_cross_cutting.py -v
  cd backend && uv run poe format && uv run poe lint && uv run poe test
  ```

  **Existing tests likely to break:** none — grep confirms no test references `_auth_cleanup_loop` (only `purge_expired`, which is unchanged). The rename is safe because the symbol is private and used at exactly one call site. Note for the implementer: `docs/design/design-backend.md` and `CLAUDE.md` may name `_auth_cleanup_loop`; update any prose hit in the same commit rather than leaving a dangling reference.

- [ ] **Step 5: Commit**
  ```
  git add backend/src/main.py backend/tests/integration/test_cross_cutting.py
  git commit -m "Sweep the rate limiter from the daily maintenance task

Gives Task 2's sweep() a clock. Extracts the loop body into
_run_daily_maintenance so the pass is testable without waiting 24h, and renames
_auth_cleanup_loop -> _daily_maintenance_loop now that it does two jobs.

Safe only under the documented single-replica design; the log line now reports
all three counts."
  ```

---

## Task 4: Rate-limit `POST /api/feedback`

Closes the first half of review item **2.6**. Feedback is 4000 chars/row (`schemas/feedback.py`) feeding the admin AI-triage queue, so it is also an amplification path into AI spend — and it is the only learner-facing write with no limit at all.

**Files:**
- Modify `backend/src/routers/feedback.py` (27 lines today)
- Modify `backend/tests/integration/test_routers/test_feedback.py` (append a class to the end)

**Interfaces:**
- *Consumes:* `get_rate_limiter` from `src/core/dependencies/ratelimit.py`, `RateLimiter.is_limited(key, *, max_calls, window_seconds)`.
- *Produces:* `POST /api/feedback` answering 429 with `{"error":{"code":"rate_limited",...}}` and `Retry-After: 600` past 10 submissions per user per 10 minutes.

- [ ] **Step 1: Write the failing test**

  Append to `backend/tests/integration/test_routers/test_feedback.py`:
  ```python
  class TestSubmitFeedbackRateLimit:
      """Mirrors the TestLoginRateLimit / chat convention: hammer N+1 times on one
      key and assert the over-limit call is 429 + Retry-After. `rate_limiter` is a
      process-global reset by conftest's autouse `_reset_rate_limiter`, so this is
      deterministic."""

      async def test_eleventh_submission_in_the_window_is_429(
          self, client: AsyncClient, db_session: AsyncSession, test_settings: Settings
      ) -> None:
          track = await create_track(db_session)
          module = await create_module(db_session, track)
          lesson = await create_lesson(db_session, module, "Rate limited lesson")
          user = await create_user(db_session, email="fb-flood@example.com")
          headers = auth_headers(user, test_settings)
          body = {"lesson_id": str(lesson.id), "message": "more examples please"}

          for _ in range(10):
              response = await client.post("/api/feedback", json=body, headers=headers)
              assert response.status_code == 201

          response = await client.post("/api/feedback", json=body, headers=headers)
          assert response.status_code == 429
          assert response.json()["error"]["code"] == "rate_limited"
          assert response.headers["Retry-After"] == "600"

      async def test_the_limit_is_per_user(
          self, client: AsyncClient, db_session: AsyncSession, test_settings: Settings
      ) -> None:
          """One learner spamming must not silence their colleagues."""
          track = await create_track(db_session)
          module = await create_module(db_session, track)
          lesson = await create_lesson(db_session, module, "Shared lesson")
          noisy = await create_user(db_session, email="fb-noisy@example.com")
          quiet = await create_user(db_session, email="fb-quiet@example.com")
          body = {"lesson_id": str(lesson.id), "message": "a note"}

          for _ in range(11):
              await client.post("/api/feedback", json=body, headers=auth_headers(noisy, test_settings))

          response = await client.post(
              "/api/feedback", json=body, headers=auth_headers(quiet, test_settings)
          )
          assert response.status_code == 201
  ```

- [ ] **Step 2: Run test to verify it fails**
  ```
  cd backend && uv run pytest tests/integration/test_routers/test_feedback.py::TestSubmitFeedbackRateLimit -v
  ```
  Expected failure: `test_eleventh_submission_in_the_window_is_429` fails with `assert 201 == 429` (the 11th POST is still accepted). `test_the_limit_is_per_user` passes already — it is the regression guard for the fix, not a red test.

- [ ] **Step 3: Write minimal implementation**

  Rewrite `backend/src/routers/feedback.py`:
  ```python
  from __future__ import annotations

  from typing import Annotated

  from fastapi import APIRouter, Depends, HTTPException, status

  from src.core.dependencies.auth import get_current_user
  from src.core.dependencies.domain import get_feedback_service
  from src.core.dependencies.ratelimit import get_rate_limiter
  from src.core.ratelimit import RateLimiter
  from src.db.models import User
  from src.schemas.feedback import FeedbackCreate, FeedbackResponse
  from src.services.feedback_service import FeedbackService

  __all__ = ["router"]

  router = APIRouter(prefix="/api/feedback", tags=["feedback"])

  CurrentUserDep = Annotated[User, Depends(get_current_user)]
  RateLimiterDep = Annotated[RateLimiter, Depends(get_rate_limiter)]

  # 10 per 10 minutes per learner. A learner reading a lesson files one or two
  # notes; ten is generous. The cap matters because every accepted row becomes an
  # LLM call on the admin's triage run, so this endpoint is an amplification path
  # into AI spend, not just a table that can be filled.
  _MAX_SUBMISSIONS = 10
  _WINDOW_SECONDS = 600

  _RATE_LIMITED = HTTPException(
      status_code=status.HTTP_429_TOO_MANY_REQUESTS,
      detail="Too much feedback at once — try again shortly",
      headers={"Retry-After": "600"},
  )


  @router.post("", response_model=FeedbackResponse, status_code=status.HTTP_201_CREATED)
  async def submit_feedback(
      user: CurrentUserDep,
      body: FeedbackCreate,
      feedback_service: Annotated[FeedbackService, Depends(get_feedback_service)],
      limiter: RateLimiterDep,
  ) -> FeedbackResponse:
      """Keyed by user id, not IP: the caller is always authenticated here, and a
      shared office IP must not let one learner's burst silence the floor."""
      if limiter.is_limited(
          f"feedback:{user.id}", max_calls=_MAX_SUBMISSIONS, window_seconds=_WINDOW_SECONDS
      ):
          raise _RATE_LIMITED
      feedback = await feedback_service.submit(user.id, body.lesson_id, body.message)
      return FeedbackResponse.model_validate(feedback)
  ```
  `RateLimiter` and `User` are imported at **runtime** on purpose — both appear in FastAPI-inspected parameter annotations via the `Annotated` aliases (see Global Constraints).

- [ ] **Step 4: Run test to verify it passes**
  ```
  cd backend && uv run pytest tests/integration/test_routers/test_feedback.py -v
  cd backend && uv run poe format && uv run poe lint && uv run poe test
  ```

  **Existing tests likely to break:** watch `tests/integration/test_routers/test_feedback.py::TestSubmitFeedback` and `tests/integration/test_routers/test_authz.py`. Neither should break — the existing feedback tests post once or twice per test and the autouse limiter reset runs between tests — but `test_authz.py` sweeps every endpoint × auth level and may POST feedback several times in one test. If it turns red with 429, raise `_MAX_SUBMISSIONS`, do **not** reach for `rate_limiter.reset()` inside a test.

- [ ] **Step 5: Commit**
  ```
  git add backend/src/routers/feedback.py backend/tests/integration/test_routers/test_feedback.py
  git commit -m "Rate-limit POST /api/feedback (10 per 10 min per learner)

Review item 2.6: the only learner-facing write with no limiter at all, at 4000
chars a row, feeding the admin AI-triage queue — so an amplification path into
AI spend as well as an unbounded table.

Keyed by user id rather than IP so one learner's burst can't silence colleagues
behind the same office NAT."
  ```

---

## Task 5: Rate-limit `POST /api/auth/refresh`

Second half of **2.6**. Refresh is unauthenticated (the token *is* the credential) and today completely unmetered.

**Files:**
- Modify `backend/src/routers/auth.py` (`refresh` at `:87-97`)
- Modify `backend/tests/integration/test_cross_cutting.py` (new class)

**Interfaces:**
- *Consumes:* `get_rate_limiter` (already wired into this router at `:9,37` for login/set-password), `starlette.requests.Request`.
- *Produces:* `POST /api/auth/refresh` answering 429 + `Retry-After: 60` past 30 attempts per client IP per 5 minutes.

- [ ] **Step 1: Write the failing test**

  Append to `backend/tests/integration/test_cross_cutting.py`:
  ```python
  class TestRefreshRateLimit:
      """Refresh is unauthenticated — the presented token IS the credential — so
      the only key available is the client IP. All httpx test requests share one,
      which is exactly what TestSetPasswordRateLimit relies on."""

      async def test_thirty_first_attempt_is_429(self, client: AsyncClient) -> None:
          for _ in range(30):
              response = await client.post(
                  "/api/auth/refresh", json={"refresh_token": "not-a-real-token"}
              )
              assert response.status_code == 401

          response = await client.post(
              "/api/auth/refresh", json={"refresh_token": "not-a-real-token"}
          )
          assert response.status_code == 429
          assert response.json()["error"]["code"] == "rate_limited"
          assert response.headers["Retry-After"] == "60"
  ```

- [ ] **Step 2: Run test to verify it fails**
  ```
  cd backend && uv run pytest tests/integration/test_cross_cutting.py::TestRefreshRateLimit -v
  ```
  Expected failure: `assert 401 == 429` on the final assertion — the 31st call still returns 401 because nothing counts.

- [ ] **Step 3: Write minimal implementation**

  In `backend/src/routers/auth.py`, add the constants next to the existing `_RATE_LIMITED` block (after `:47`):
  ```python
  # Refresh is legitimately frequent: access tokens live 30 minutes
  # (AuthSettings.access_token_minutes), so one active session refreshes twice an
  # hour. 30 per 5 minutes per IP leaves ample room for a whole office behind one
  # NAT hop while still bounding a scripted replay flood. Keyed by IP because the
  # endpoint is unauthenticated and keying by the presented token would be
  # useless — the attacker picks the token.
  _REFRESH_MAX_CALLS = 30
  _REFRESH_WINDOW_SECONDS = 300


  def _client_ip(request: Request) -> str:
      """Resolved from X-Forwarded-For by uvicorn (startup.py sets
      proxy_headers=True), so this is the real client behind ACA ingress."""
      return request.client.host if request.client is not None else "unknown"
  ```
  Replace `refresh` (`:87-97`) with:
  ```python
  @router.post("/refresh", response_model=TokenPairResponse)
  async def refresh(
      body: RefreshRequest,
      request: Request,
      token_service: TokenServiceDep,
      limiter: RateLimiterDep,
  ) -> TokenPairResponse:
      if limiter.is_limited(
          f"refresh:{_client_ip(request)}",
          max_calls=_REFRESH_MAX_CALLS,
          window_seconds=_REFRESH_WINDOW_SECONDS,
      ):
          raise _RATE_LIMITED
      try:
          pair = await token_service.refresh_pair(body.refresh_token)
      except InvalidSessionError as exc:
          raise HTTPException(
              status_code=status.HTTP_401_UNAUTHORIZED,
              detail="Invalid or expired refresh token",
              headers={"WWW-Authenticate": "Bearer"},
          ) from exc
      return _pair_response(pair)
  ```
  Then refactor `set_password` (`:135`) to use the new helper instead of its inline copy:
  ```python
      client_ip = _client_ip(request)
  ```
  `Request` is already imported at runtime (`auth.py:5`) — required, since it is a route parameter annotation.

- [ ] **Step 4: Run test to verify it passes**
  ```
  cd backend && uv run pytest tests/integration/test_cross_cutting.py -v
  cd backend && uv run pytest tests/integration/test_routers/test_auth_flows.py tests/integration/test_routers/test_invite_lifecycle.py -v
  cd backend && uv run poe format && uv run poe lint && uv run poe test
  ```

  **Existing tests likely to break:** `tests/integration/test_routers/test_auth_flows.py` and `test_invite_lifecycle.py` both exercise refresh. Both should stay green — 30 attempts per test is far above what any single test makes, and the autouse limiter reset isolates tests. `tests/integration/test_routers/test_authz.py` also hits `/api/auth/refresh`; same reasoning.

- [ ] **Step 5: Commit**
  ```
  git add backend/src/routers/auth.py backend/tests/integration/test_cross_cutting.py
  git commit -m "Rate-limit POST /api/auth/refresh (30 per 5 min per IP)

Review item 2.6: refresh was completely unmetered. Keyed by client IP because
the endpoint is unauthenticated and the attacker chooses the token, so a
per-token key would bound nothing. 30/5min leaves room for an office NAT hop
given 30-minute access tokens.

Also de-duplicates the client-IP read that set-password had inline."
  ```

---

## Task 6: Per-IP login counter alongside the per-email one

Closes the last part of **2.6**: `routers/auth.py:74` keys only on the submitted email, so password spraying across many accounts from one host is unmetered (and, symmetrically, an attacker can 429-lock one named victim out).

**Files:**
- Modify `backend/src/routers/auth.py` (`login` at `:67-84`)
- Modify `backend/tests/integration/test_cross_cutting.py` (extend `TestLoginRateLimit`)

**Interfaces:**
- *Consumes:* `_client_ip(request)` (Task 5), `RateLimiterDep` (already in the module).
- *Produces:* two independent counters on login — `login:{email}` (unchanged, 5/60s) and `login-ip:{ip}` (new, 30/300s).

- [ ] **Step 1: Write the failing test**

  Append to the existing `TestLoginRateLimit` class in `backend/tests/integration/test_cross_cutting.py`:
  ```python
      async def test_spraying_many_accounts_from_one_host_is_limited(
          self, client: AsyncClient, db_session: AsyncSession
      ) -> None:
          """Per-email keying alone lets one host try 5 passwords against every
          account in the directory for free. The per-IP counter is what bounds the
          spray; it is set well above the per-email limit so a shared office NAT
          hop can't lock out a floor of legitimate users."""
          await create_user(db_session, email="sprayed-target@example.com", password="right-pass-1")
          for i in range(30):
              response = await client.post(
                  "/api/auth/login",
                  json={"email": f"victim-{i}@example.com", "password": "guess"},
              )
              assert response.status_code == 401

          # A fresh email with the CORRECT password: the per-email counter is at
          # zero, so only the per-IP counter can produce a 429 here.
          response = await client.post(
              "/api/auth/login",
              json={"email": "sprayed-target@example.com", "password": "right-pass-1"},
          )
          assert response.status_code == 429
          assert response.headers["Retry-After"] == "60"
  ```

- [ ] **Step 2: Run test to verify it fails**
  ```
  cd backend && uv run pytest tests/integration/test_cross_cutting.py::TestLoginRateLimit -v
  ```
  Expected failure: `assert 200 == 429` — the 31st login succeeds today because only the per-email counter exists.
  Note this test costs 31 bcrypt verifications (the dummy-hash path keeps unknown emails constant-cost). At cost 12 that is a few seconds; it is the price of asserting the real limit rather than mocking it.

- [ ] **Step 3: Write minimal implementation**

  In `backend/src/routers/auth.py`, add next to the Task 5 constants:
  ```python
  # A whole office can sit behind one ACA ingress hop, so the per-IP login
  # counter is deliberately ~6x the per-email one: it exists to bound a spray
  # across many accounts, not to police one person's typing. The per-email
  # counter (5/60s) still does the per-account work.
  _LOGIN_IP_MAX_CALLS = 30
  _LOGIN_IP_WINDOW_SECONDS = 300
  ```
  Replace `login` (`:67-84`) with:
  ```python
  @router.post("/login", response_model=TokenPairResponse)
  async def login(
      body: LoginRequest,
      request: Request,
      user_service: UserServiceDep,
      token_service: TokenServiceDep,
      limiter: RateLimiterDep,
  ) -> TokenPairResponse:
      """Two independent counters: per-email bounds attempts against one account,
      per-IP bounds a spray across many. Both are recorded before authentication
      so a correct password never resets an attacker's budget."""
      if limiter.is_limited(f"login:{body.email.strip().lower()}"):
          raise _RATE_LIMITED
      if limiter.is_limited(
          f"login-ip:{_client_ip(request)}",
          max_calls=_LOGIN_IP_MAX_CALLS,
          window_seconds=_LOGIN_IP_WINDOW_SECONDS,
      ):
          raise _RATE_LIMITED
      try:
          user = await user_service.authenticate(body.email, body.password)
      except InvalidCredentialsError as exc:
          raise HTTPException(
              status_code=status.HTTP_401_UNAUTHORIZED,
              detail="Invalid email or password",
              headers={"WWW-Authenticate": "Bearer"},
          ) from exc
      return _pair_response(await token_service.issue_pair(user))
  ```

- [ ] **Step 4: Run test to verify it passes**
  ```
  cd backend && uv run pytest tests/integration/test_cross_cutting.py -v
  cd backend && uv run poe format && uv run poe lint && uv run poe test
  ```

  **Existing tests likely to break — read this before running:**
  - `TestLoginRateLimit::test_limit_is_per_email` makes **7** login calls from the one shared test IP. With `_LOGIN_IP_MAX_CALLS = 30` it stays green. Do not lower that constant below ~10 without also rewriting that test.
  - `tests/integration/test_routers/test_auth_flows.py` and `test_invite_lifecycle.py` log in repeatedly; each individual test is well under 30 and the autouse `_reset_rate_limiter` isolates them.
  - The whole suite runs `-n auto`, but the limiter is per-process and each xdist worker has its own, so parallelism cannot pool these counters.

- [ ] **Step 5: Commit**
  ```
  git add backend/src/routers/auth.py backend/tests/integration/test_cross_cutting.py
  git commit -m "Add a per-IP login counter alongside the per-email one

Review item 2.6: keying login only on the submitted email left password
spraying across many accounts from one host unmetered. Adds login-ip:{ip} at
30/300s — deliberately well above the per-email 5/60s so a shared office NAT
hop can't lock out legitimate users, while still bounding a spray.

Both counters are recorded before authenticate(), so a correct password never
resets an attacker's budget."
  ```

---

## Task 7: Explicit timeouts on the interview opener and playbook calls

Closes review item **7.1**. Both interview LLM calls currently rely on the Anthropic SDK's default (~10 minutes) while every sibling service bounds itself.

**Files:**
- Modify `backend/src/services/interview_service.py` (imports at `:1-19`; constants at `:31-40`; `open_interview` at `:108-141`; `_generate` at `:166-179`)
- Modify `backend/tests/unit/test_interview_service.py` (append two tests)

**Interfaces:**
- *Consumes:* `asyncio.timeout` (stdlib).
- *Produces:* module constants `_OPENER_TIMEOUT_SECONDS = 45.0` and `_GENERATE_TIMEOUT_SECONDS = 90.0`, both monkeypatchable by name from tests. Task 8 changes what the resulting `TimeoutError` maps to; this task only bounds the wait.

- [ ] **Step 1: Write the failing test**

  Append to `backend/tests/unit/test_interview_service.py`:
  ```python
  class _SlowStructuredLlmClient:
      """complete_structured never returns in time."""

      def __init__(self) -> None:
          self.calls = 0

      async def complete_structured(self, **_: object) -> tuple[dict[str, object], LlmUsage]:
          self.calls += 1
          await asyncio.sleep(1)
          return _EXTRACTION, LlmUsage(input_tokens=10, output_tokens=10)


  class _SlowStreamManager:
      async def __aenter__(self) -> _SlowStreamManager:
          return self

      async def __aexit__(self, *_exc: object) -> None:
          return None

      async def __aiter__(self) -> AsyncIterator[str]:
          await asyncio.sleep(1)
          yield "too late"

      async def usage(self) -> LlmUsage:
          return LlmUsage(input_tokens=0, output_tokens=0)


  class _SlowStreamingLlmClient:
      def stream_reply(self, **_: object) -> _SlowStreamManager:
          return _SlowStreamManager()


  async def test_playbook_generation_is_bounded_by_its_own_timeout(
      monkeypatch: pytest.MonkeyPatch,
  ) -> None:
      """A hung provider call must not keep the server working long after the
      browser gave up at the 240s ingress timeout."""
      monkeypatch.setattr(interview_service, "_GENERATE_TIMEOUT_SECONDS", 0.01)
      llm = _SlowStructuredLlmClient()
      service, conversations, messages, _context = _service(llm)
      conversation = _conversation(summary=None)
      conversations.list_for_user.return_value = [conversation]
      messages.list_for_conversation.return_value = []
      user = _user()

      with pytest.raises((TimeoutError, DomainError)):
          await service.build_playbook(user=user)  # ty: ignore[invalid-argument-type]

      conversations.update_summary.assert_not_awaited()


  async def test_opener_is_bounded_by_its_own_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
      monkeypatch.setattr(interview_service, "_OPENER_TIMEOUT_SECONDS", 0.01)
      service, conversations, messages, context = _service(_SlowStreamingLlmClient())
      context.build_briefing.return_value = "BRIEFING"
      conversations.list_for_user.return_value = []
      user = _user()

      with pytest.raises(DomainError):
          await service.open_interview(user=user)  # ty: ignore[invalid-argument-type]

      conversations.create.assert_not_awaited()
      messages.create.assert_not_awaited()
  ```
  Add to that file's imports:
  ```python
  import asyncio
  from collections.abc import AsyncIterator

  from src.services import interview_service
  ```
  (`pytest`, `uuid`, `DomainError`, `LlmUsage` and the `_service`/`_conversation`/`_user`/`_EXTRACTION` helpers are already there. `pytest.raises((TimeoutError, DomainError))` is deliberately tolerant of both because Task 8 changes which one surfaces — this test asserts the *bound*, not the mapping.)

- [ ] **Step 2: Run test to verify it fails**
  ```
  cd backend && uv run pytest tests/unit/test_interview_service.py -k timeout -v
  ```
  Expected failure: `AttributeError: module 'src.services.interview_service' has no attribute '_GENERATE_TIMEOUT_SECONDS'` raised by `monkeypatch.setattr` in both tests. (Without a timeout the tests would otherwise just hang for a second and then pass, which is exactly why the constants are monkeypatched by name rather than injected.)

- [ ] **Step 3: Write minimal implementation**

  In `backend/src/services/interview_service.py`, add the import (the module has no `asyncio` today):
  ```python
  import asyncio
  ```
  Add the constants next to `_MAX_TOKENS` (`:32`):
  ```python
  # Sized like the sibling AI services against the 240s Azure Container Apps
  # ingress default (nothing sets ingress.requestTimeout): feedback triage uses
  # 30s per item, content improvement 180s for one lesson-sized draft. The
  # playbook is ONE structured call that `_generate` retries once, so its budget
  # has to cover BOTH attempts inside the ingress window — hence 90s each, not
  # 180. The opener is a single short streamed greeting.
  _OPENER_TIMEOUT_SECONDS = 45.0
  _GENERATE_TIMEOUT_SECONDS = 90.0
  ```
  In `open_interview`, wrap the streaming block (currently `:121-130`) so the existing `try` still owns the failure translation:
  ```python
          try:
              chunks: list[str] = []
              async with asyncio.timeout(_OPENER_TIMEOUT_SECONDS):
                  async with self._llm.stream_reply(
                      system=system,
                      messages=[{"role": "user", "content": _KICKOFF}],
                      max_tokens=_OPENER_MAX_TOKENS,
                  ) as reply:
                      async for text in reply:
                          chunks.append(text)
              greeting = "".join(chunks).strip()
  ```
  In `_generate`, wrap each attempt:
  ```python
      async def _generate(self, system: str) -> PlaybookExtraction:
          last_error: Exception | None = None
          for _attempt in range(2):
              try:
                  async with asyncio.timeout(_GENERATE_TIMEOUT_SECONDS):
                      result, _usage = await self._llm.complete_structured(
                          system=system,
                          prompt=_GENERATE_PROMPT,
                          schema=PLAYBOOK_SCHEMA,
                          max_tokens=_MAX_TOKENS,
                      )
                  return PlaybookExtraction.model_validate(result)
              except (ValidationError, LlmError) as exc:
                  last_error = exc
          raise DomainError("Could not generate the playbook — please try again.") from last_error
  ```
  A `TimeoutError` is **not** added to the retry tuple, deliberately: `is_transient_provider_error` classifies timeouts as terminal (`llm_service.py:39-49`, and `content_improvement_service.py:333-345` documents the same choice), so it propagates out of `_generate` and Task 8 maps it.

- [ ] **Step 4: Run test to verify it passes**
  ```
  cd backend && uv run pytest tests/unit/test_interview_service.py -v
  cd backend && uv run poe format && uv run poe lint && uv run poe test
  ```

  **Existing tests likely to break:** none. All existing `test_interview_service.py` fakes return immediately, so a 45s/90s budget is never approached. Note for the implementer: `ruff format` currently reports `src/services/interview_service.py` as needing reformatting (a pre-existing finding, review item **9.10**) — `poe format` will rewrite parts of this file you did not touch. That is fine and expected; the other plan's Task 8 owns the finding, and whichever plan runs first absorbs the diff.

- [ ] **Step 5: Commit**
  ```
  git add backend/src/services/interview_service.py backend/tests/unit/test_interview_service.py
  git commit -m "Bound the interview opener and playbook LLM calls with timeouts

Review item 7.1: both calls relied on the Anthropic SDK default (~10 min) while
every sibling bounds itself (triage 30s/item, content improvement 180s, Entra
10s). A hung playbook build kept the server working ~20 minutes after the
browser already got a 504 at the 240s ACA ingress.

Opener 45s; playbook 90s per attempt, so both retried attempts fit inside the
ingress window. TimeoutError is deliberately not retried — is_transient_provider_error
classifies it terminal."
  ```

---

## Task 8: Map transient provider errors to 502 in the interview service

Closes the first half of review item **7.2**. `is_transient_provider_error` exists and the content pipeline uses it carefully; the interview path never consults it, so an Anthropic 529 leaves `build_playbook` unclassified.

**Files:**
- Modify `backend/src/services/interview_service.py` (imports; `open_interview` `except` at `:131`; `_generate` from Task 7)
- Modify `backend/tests/unit/test_interview_service.py` (append tests)

**Interfaces:**
- *Consumes:* `is_transient_provider_error(exc) -> bool` and `AiGenerationError` (already mapped to **502** at `main.py:264-266`); Task 1's catch-all as the floor for anything still unclassified.
- *Produces:* `POST /api/interview/playbook` and `POST /api/interview/opener` answer **502** `{"error":{"code":"bad_gateway",...}}` on a provider failure or timeout, instead of a bare 500 (playbook) / a misleading 400 (opener).

- [ ] **Step 1: Write the failing test**

  Append to `backend/tests/unit/test_interview_service.py`:
  ```python
  def _overloaded() -> Exception:
      """A real anthropic 529, built the way the SDK builds one (same helper
      shape as tests/unit/test_llm_service.py)."""
      request = httpx.Request("POST", "https://api.anthropic.com/v1/messages")
      return anthropic.OverloadedError(
          "overloaded", response=httpx.Response(529, request=request), body=None
      )


  class _OverloadedStructuredLlmClient:
      def __init__(self) -> None:
          self.calls = 0

      async def complete_structured(self, **_: object) -> tuple[dict[str, object], LlmUsage]:
          self.calls += 1
          raise _overloaded()


  class _OverloadedStreamManager:
      async def __aenter__(self) -> _OverloadedStreamManager:
          raise _overloaded()

      async def __aexit__(self, *_exc: object) -> None:
          return None


  class _OverloadedStreamingLlmClient:
      def stream_reply(self, **_: object) -> _OverloadedStreamManager:
          return _OverloadedStreamManager()


  async def test_playbook_provider_overload_is_a_502_not_a_500() -> None:
      """A 529 says nothing about whether this playbook can be generated, so it
      must not read as a bad request — and it must not escape unclassified into
      the catch-all 500 either."""
      llm = _OverloadedStructuredLlmClient()
      service, conversations, messages, _context = _service(llm)
      conversation = _conversation(summary=None)
      conversations.list_for_user.return_value = [conversation]
      messages.list_for_conversation.return_value = []
      user = _user()

      with pytest.raises(AiGenerationError) as exc_info:
          await service.build_playbook(user=user)  # ty: ignore[invalid-argument-type]

      assert "busy" in str(exc_info.value).lower() or "unavailable" in str(exc_info.value).lower()
      # Not retried: retrying an overloaded provider inside one request just
      # spends the caller's patience twice.
      assert llm.calls == 1
      conversations.update_summary.assert_not_awaited()


  async def test_playbook_unknown_failure_is_also_a_502() -> None:
      """Anything the provider throws is still "the model call failed" from here
      — the one thing it must not be is an unhandled 500."""
      service, conversations, messages, _context = _service(RaisingLlmClient())
      conversation = _conversation(summary=None)
      conversations.list_for_user.return_value = [conversation]
      messages.list_for_conversation.return_value = []
      user = _user()

      with pytest.raises(AiGenerationError):
          await service.build_playbook(user=user)  # ty: ignore[invalid-argument-type]


  async def test_playbook_still_retries_a_bad_shaped_response() -> None:
      """Regression guard: the transient branch must not swallow the
      retry-once-on-unusable-output behaviour the feature was built with."""
      llm = _FlakyLlmClient([{}, _EXTRACTION])
      service, conversations, messages, _context = _service(llm)
      conversation = _conversation(summary=None)
      conversations.list_for_user.return_value = [conversation]
      messages.list_for_conversation.return_value = []
      user = _user()

      result = await service.build_playbook(user=user)  # ty: ignore[invalid-argument-type]

      assert isinstance(result, PlaybookShared)
      assert llm.calls == 2


  async def test_opener_provider_overload_is_a_502() -> None:
      service, conversations, messages, context = _service(_OverloadedStreamingLlmClient())
      context.build_briefing.return_value = "BRIEFING"
      conversations.list_for_user.return_value = []
      user = _user()

      with pytest.raises(AiGenerationError):
          await service.open_interview(user=user)  # ty: ignore[invalid-argument-type]

      conversations.create.assert_not_awaited()
      messages.create.assert_not_awaited()
  ```
  Add to that file's imports:
  ```python
  import anthropic
  import httpx

  from src.services.exceptions import AiGenerationError, DomainError
  ```

- [ ] **Step 2: Run test to verify it fails**
  ```
  cd backend && uv run pytest tests/unit/test_interview_service.py -k "502 or overload or unknown_failure" -v
  ```
  Expected failure: `test_playbook_provider_overload_is_a_502_not_a_500`, `test_playbook_unknown_failure_is_also_a_502` and `test_opener_provider_overload_is_a_502` all fail with `DID NOT RAISE AiGenerationError` — the first two because the raw `anthropic.OverloadedError` / `RuntimeError` propagates untouched, the third because `open_interview`'s broad `except Exception` currently converts everything to `DomainError` (400). `test_playbook_still_retries_a_bad_shaped_response` passes already; it is the regression guard.

- [ ] **Step 3: Write minimal implementation**

  In `backend/src/services/interview_service.py`, extend the imports:
  ```python
  from src.services.exceptions import AiGenerationError, DomainError, NotFoundError
  from src.services.llm_service import LlmError, is_transient_provider_error
  ```
  Add a shared message helper below `_strip_ready_marker`:
  ```python
  _BUSY_MESSAGE = "The model is busy right now - please try again in a moment."


  def _provider_failure(exc: BaseException, fallback: str) -> AiGenerationError:
      """Every provider failure reaching a caller becomes a 502 (see
      AiGenerationError), but a transient one gets the "try again" wording
      because trying again is genuinely the right advice — that is the whole
      point of `is_transient_provider_error`, which the content pipeline already
      leans on and this service did not."""
      return AiGenerationError(_BUSY_MESSAGE if is_transient_provider_error(exc) else fallback)
  ```
  Replace `open_interview`'s `except` clause (`:131-132`) with:
  ```python
          except Exception as exc:  # noqa: BLE001 - any provider failure is a 502 here
              raise _provider_failure(
                  exc, "Could not start the interview - please try again."
              ) from exc
  ```
  Leave the `if not greeting:` guard below it raising `DomainError` — an empty greeting is a genuinely bad result, not a provider outage.

  In `_generate` (as written by Task 7), add the classifying branch **after** the retryable one:
  ```python
      async def _generate(self, system: str) -> PlaybookExtraction:
          last_error: Exception | None = None
          for _attempt in range(2):
              try:
                  async with asyncio.timeout(_GENERATE_TIMEOUT_SECONDS):
                      result, _usage = await self._llm.complete_structured(
                          system=system,
                          prompt=_GENERATE_PROMPT,
                          schema=PLAYBOOK_SCHEMA,
                          max_tokens=_MAX_TOKENS,
                      )
                  return PlaybookExtraction.model_validate(result)
              except (ValidationError, LlmError) as exc:
                  # An unusable SHAPE is worth one more try: the same prompt can
                  # produce a valid extraction next time.
                  last_error = exc
              except Exception as exc:  # noqa: BLE001 - transport/provider/timeout -> 502
                  # Not retried here. A 529 means the provider is busy, so an
                  # immediate second call inside the same request just doubles the
                  # caller's wait; a TimeoutError means this input is too slow.
                  # Either way the honest answer is 502 + "try again".
                  raise _provider_failure(
                      exc, "Could not generate the playbook - please try again."
                  ) from exc
          raise DomainError("Could not generate the playbook — please try again.") from last_error
  ```

- [ ] **Step 4: Run test to verify it passes**
  ```
  cd backend && uv run pytest tests/unit/test_interview_service.py -v
  cd backend && uv run poe format && uv run poe lint && uv run poe test
  ```
  **Then run this frontend check before committing** (read-only — this plan changes no frontend file):
  ```
  cd .. && grep -rn "opener\|playbook" frontend/src/lib/interviewApi.ts frontend/src/pages 2>/dev/null | grep -in "status\|502\|400"
  ```
  This task changes `/api/interview/opener`'s transient-failure status from **400 to 502** and `/api/interview/playbook`'s from **500 to 502**. Both keep the same `{"error":{code,message}}` body, so a client that renders `error.message` is unaffected. If the grep shows the interview UI branching on a numeric status, stop and hand that finding to whoever owns the frontend plan rather than editing it here.

  **Existing tests likely to break:**
  - `test_open_interview_llm_failure_creates_no_conversation` expects `DomainError` from a `RaisingLlmClient` (a bare `RuntimeError`). It will now get `AiGenerationError`. **`AiGenerationError` subclasses `DomainError`** (`services/exceptions.py:143`), so `pytest.raises(DomainError)` still passes — verify this rather than assuming, and if it fails, tighten the existing test to `AiGenerationError` instead of loosening the implementation.
  - No integration tests cover `/api/interview/*` today (review item 4.6) — so nothing there can break, and nothing there proves this works over HTTP either. Adding router tests for the interview slice is a known gap owned elsewhere; note it, do not fix it here.

- [ ] **Step 5: Commit**
  ```
  git add backend/src/services/interview_service.py backend/tests/unit/test_interview_service.py
  git commit -m "Map interview provider failures to 502 via is_transient_provider_error

Review item 7.2: interview_service._generate retried only (ValidationError,
LlmError), so an Anthropic 529 propagated out of build_playbook with no handler
at all -> bare 500. open_interview converted every provider failure to a 400,
which reads as 'your request was wrong'.

Both now raise AiGenerationError (mapped to 502 in main.py) and consult
is_transient_provider_error for the wording. Retry-once on an unusably shaped
response is preserved; a transient error is deliberately NOT retried inside one
request."
  ```

---

## Task 9: Terminal `error` SSE frame when the provider fails mid-stream

Closes the second half of review item **7.2**. Once `text/event-stream` headers are committed there is no HTTP status left to change, so today a provider failure mid-reply leaves the learner watching a dead stream.

**Files:**
- Modify `backend/src/services/chat_service.py` (imports; `ChatStreamEvent` union at `:35`; `send_message` at `:78-121`)
- Modify `backend/src/routers/chat.py` (imports at `:24`; the event loop at `:124-148`)
- Modify `backend/tests/unit/test_chat_service.py` (append tests)
- Modify `backend/tests/integration/test_routers/test_chat.py` (append one test)

**Interfaces:**
- *Consumes:* `is_transient_provider_error` (`services/llm_service.py`).
- *Produces:* `ErrorEvent(message: str)` exported from `src/services/chat_service.py` and added to `ChatStreamEvent`; the router emits `event: error` with `data: {"message": "..."}`. The partial-reply persistence and `truncated` semantics are unchanged.

- [ ] **Step 1: Write the failing test**

  Append to `backend/tests/unit/test_chat_service.py`:
  ```python
  class _FailsMidStream:
      """Yields one chunk, then the provider falls over — the case that cannot be
      an HTTP error because the 200 is already on the wire."""

      def __init__(self, exc: BaseException) -> None:
          self._exc = exc

      def stream_reply(self, **_: object) -> _FailsMidStream:
          return self

      async def __aenter__(self) -> _FailsMidStream:
          return self

      async def __aexit__(self, *_exc: object) -> None:
          return None

      async def __aiter__(self) -> AsyncIterator[str]:
          yield "Par"
          raise self._exc

      async def usage(self) -> LlmUsage:  # pragma: no cover - never reached
          return LlmUsage(input_tokens=0, output_tokens=0)


  def _overloaded() -> Exception:
      request = httpx.Request("POST", "https://api.anthropic.com/v1/messages")
      return anthropic.OverloadedError(
          "overloaded", response=httpx.Response(529, request=request), body=None
      )


  async def test_provider_failure_mid_stream_yields_a_terminal_error_event() -> None:
      service, _, messages = _service(_FailsMidStream(_overloaded()))  # ty: ignore[invalid-argument-type]
      conversation = SimpleNamespace(id=uuid.uuid4(), user_id=uuid.uuid4(), kind="chatbot")

      events = [
          e
          async for e in service.send_message(
              conversation=conversation,  # ty: ignore[invalid-argument-type]
              content="hi",
          )
      ]

      assert [type(e).__name__ for e in events] == ["TokenEvent", "ErrorEvent"]
      assert isinstance(events[1], ErrorEvent)
      assert "try again" in events[1].message.lower()
      # The partial reply is still persisted and still marked truncated — the
      # existing disconnect behaviour must survive this change untouched.
      assert messages.create.await_count == 2
      _user_call, assistant_call = messages.create.await_args_list
      assert assistant_call.kwargs["content"] == "Par"
      assert assistant_call.kwargs["metadata"]["truncated"] is True


  async def test_no_done_event_follows_a_failure() -> None:
      """A `done` frame after an `error` frame would tell the client the reply
      finished cleanly."""
      service, _, _ = _service(_FailsMidStream(RuntimeError("boom")))  # ty: ignore[invalid-argument-type]
      conversation = SimpleNamespace(id=uuid.uuid4(), user_id=uuid.uuid4(), kind="chatbot")

      events = [
          e
          async for e in service.send_message(
              conversation=conversation,  # ty: ignore[invalid-argument-type]
              content="hi",
          )
      ]

      assert not any(isinstance(e, DoneEvent) for e in events)
      assert isinstance(events[-1], ErrorEvent)
  ```
  Add to that file's imports:
  ```python
  import anthropic
  import httpx
  from collections.abc import AsyncIterator

  from src.services.chat_service import ChatService, DoneEvent, ErrorEvent, TokenEvent
  from src.services.llm_service import LlmUsage
  ```

  And append to `backend/tests/integration/test_routers/test_chat.py`, inside the existing streaming test class (the one holding `test_21st_call_in_window_is_429_with_retry_after`):
  ```python
      async def test_provider_failure_mid_stream_sends_an_error_frame(
          self,
          chat_client: Callable[[FakeLlmClient], AsyncClient],
          db_session: AsyncSession,
          test_settings: Settings,
      ) -> None:
          """End-to-end proof that the frame reaches the wire: the response is
          still 200 (headers were committed before the failure), and the last SSE
          event is `error`, not `done`."""

          class _FailsMidStream:
              def stream_reply(self, **_: object) -> _FailsMidStream:
                  return self

              async def __aenter__(self) -> _FailsMidStream:
                  return self

              async def __aexit__(self, *_exc: object) -> None:
                  return None

              async def __aiter__(self):
                  yield "Par"
                  msg = "provider fell over"
                  raise RuntimeError(msg)

          company = await create_company(db_session, "Chat Error Co")
          project = await create_project(db_session, company, "Chat Error Project")
          user = await create_user(
              db_session,
              email="chat-stream-error@example.com",
              company_id=company.id,
              project_id=project.id,
          )
          await _enable_ai(db_session, project.id, "chatbot")

          client = chat_client(_FailsMidStream())  # ty: ignore[invalid-argument-type]
          async with client.stream(
              "POST",
              "/api/chat/chatbot",
              json={"content": "hi"},
              headers=auth_headers(user, test_settings),
          ) as response:
              assert response.status_code == 200
              raw = "".join([chunk async for chunk in response.aiter_text()])

          events = _parse_sse(raw)
          assert [e for e, _ in events] == ["token", "error"]
          assert "message" in events[1][1]
  ```

- [ ] **Step 2: Run test to verify it fails**
  ```
  cd backend && uv run pytest tests/unit/test_chat_service.py -v
  ```
  Expected failure: collection fails with `ImportError: cannot import name 'ErrorEvent' from 'src.services.chat_service'`. After adding the dataclass but before the `except` branch, the two tests fail differently — the provider exception propagates out of the generator, so `pytest` reports `anthropic.OverloadedError` / `RuntimeError` instead of collecting events.

- [ ] **Step 3: Write minimal implementation**

  In `backend/src/services/chat_service.py`, extend the imports and add a logger:
  ```python
  import logging

  from src.services.exceptions import NotFoundError
  from src.services.llm_service import is_transient_provider_error
  from src.services.prompts import load_prompt

  ...

  __all__ = ["ChatService", "ChatStreamEvent", "DoneEvent", "ErrorEvent", "TokenEvent"]

  logger = logging.getLogger(__name__)
  ```
  Note `is_transient_provider_error` must be a **runtime** import (it is called), unlike the `LlmClient`/`LlmUsage` types which stay under `TYPE_CHECKING`.

  Add the event and extend the union (after `DoneEvent`, `:28-35`):
  ```python
  @dataclass(frozen=True)
  class ErrorEvent:
      """Terminal frame for a failure the HTTP layer can no longer express.

      By the time the model is streaming, a 200 and the text/event-stream headers
      are already on the wire, so a provider failure cannot become a 4xx/5xx —
      the only way to tell the learner anything is in-band. Mutually exclusive
      with DoneEvent: a `done` frame after this would claim the reply finished.
      """

      message: str


  ChatStreamEvent = TokenEvent | DoneEvent | ErrorEvent
  ```
  Rewrite the body of `send_message` from the `try` (`:90`) to the end:
  ```python
          chunks: list[str] = []
          truncated = False
          usage: LlmUsage | None = None
          failure: str | None = None
          try:
              async with self._llm.stream_reply(
                  system=system_prompt, messages=history, max_tokens=_MAX_TOKENS
              ) as reply:
                  async for text in reply:
                      chunks.append(text)
                      yield TokenEvent(text)
                  usage = await reply.usage()
          except (GeneratorExit, asyncio.CancelledError):
              # Both a client disconnect (GeneratorExit, injected by aclose()) and an
              # ASGI-level task cancellation (asyncio.CancelledError) mid-stream mean
              # the reply is incomplete -> mark it truncated before persisting.
              truncated = True
              raise
          except Exception as exc:  # noqa: BLE001 - reported in-band, see ErrorEvent
              # Listed AFTER the cancellation clause for readability only: both
              # GeneratorExit and CancelledError derive from BaseException, not
              # Exception, so this branch could never shadow them.
              truncated = True
              failure = (
                  "The assistant is busy right now - please try again in a moment."
                  if is_transient_provider_error(exc)
                  else "Something went wrong generating the reply - please try again."
              )
              logger.exception("chat stream failed for conversation %s", conversation.id)
          finally:
              accumulated = "".join(chunks)
              if accumulated:
                  metadata: dict[str, Any] = {"truncated": truncated}
                  if usage is not None:
                      metadata["usage"] = {
                          "input_tokens": usage.input_tokens,
                          "output_tokens": usage.output_tokens,
                      }
                  await asyncio.shield(
                      self._messages.create(
                          conversation.id, role="assistant", content=accumulated, metadata=metadata
                      )
                  )
                  await asyncio.shield(self._conversations.touch(conversation.id))

          if failure is not None:
              yield ErrorEvent(failure)
          elif not truncated:
              yield DoneEvent(conversation_id=conversation.id, truncated=False, usage=usage)
  ```
  The `asyncio.shield`ed persistence and the `truncated` flag are untouched by design — a failed stream persists its partial reply exactly like a disconnect does.

  In `backend/src/routers/chat.py`, extend the import (`:24`) and add the branch:
  ```python
  from src.services.chat_service import ChatService, DoneEvent, ErrorEvent, TokenEvent
  ```
  ```python
          elif isinstance(event, ErrorEvent):
              # Terminal: the generator yields nothing after this.
              yield ServerSentEvent(data={"message": event.message}, event="error")
  ```
  Place it after the existing `DoneEvent` branch, inside the same `async for`.

- [ ] **Step 4: Run test to verify it passes**
  ```
  cd backend && uv run pytest tests/unit/test_chat_service.py -v
  cd backend && uv run pytest tests/integration/test_routers/test_chat.py -v
  cd backend && uv run poe format && uv run poe lint && uv run poe test
  ```

  **Existing tests likely to break:**
  - `test_chat_service.py::test_send_message_persists_partial_on_disconnect` and `::test_send_message_persists_partial_on_cancellation` are the two that matter — they pin exactly the behaviour this task must preserve. If either goes red, the new `except Exception` has captured a cancellation path it must not; re-check that `GeneratorExit`/`CancelledError` are still handled first and still re-raised.
  - `tests/integration/test_routers/test_chat.py`'s happy-path test asserts `["token", "token", "done"]`; unchanged, since no failure occurs there.
  - `frontend/src/lib/useChat.ts` ignores unknown SSE event names, so shipping this before the frontend handles `error` degrades to today's behaviour (a stream that simply stops) rather than breaking anything.

- [ ] **Step 5: Commit**
  ```
  git add backend/src/services/chat_service.py backend/src/routers/chat.py backend/tests/unit/test_chat_service.py backend/tests/integration/test_routers/test_chat.py
  git commit -m "Emit a terminal error SSE frame when the provider fails mid-stream

Review item 7.2: send_message handled disconnects well (GeneratorExit /
CancelledError with asyncio.shield'ed persistence) but a provider exception
propagated AFTER the 200 + text/event-stream headers were committed, so there
was no status left to change and no error frame — the learner just saw a dead
stream.

Adds ErrorEvent, consulted via is_transient_provider_error for the wording, and
emits it as `event: error`. Disconnect handling and partial-reply persistence
are unchanged; done and error are mutually exclusive."
  ```

---

## Deferred follow-ups (explicitly out of scope here)

- **Persist rate-limit counters to Postgres.** Would need an Alembic migration (not permitted in this plan) and is entangled with the single-replica decision: today's in-process counters reset on every container restart, so the 200/day chat cap is only as durable as the revision. Until then, the provider-side spend cap (review item **1.1**) is the real backstop — that is an operational task, not a code one. `core/ratelimit.py`'s docstring already names the trigger for revisiting this ("move the counters to a PG table if the app ever scales out"), and Task 2 adds the log line that fires when the ceiling is hit.
- **Frontend rendering of the new `error` SSE frame** (`frontend/src/lib/useChat.ts`) — additive and harmless without it, but the learner sees a stopped stream rather than the message until it lands. Owned by the frontend plan.
- **Router/integration tests for `/api/interview/*`** (review item **4.6**) — the interview slice is the one backend feature with no HTTP-level tests, so Tasks 7 and 8 are proven by unit tests only.
- **Refresh-token reuse detection** (review item **2.5**) — adjacent to Task 5 and deliberately not bundled with it; owned by the security plan.
