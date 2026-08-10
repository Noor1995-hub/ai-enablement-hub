# Backend consistency & cleanup (Batch 9 code items) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the Batch 9 *code* items from `CODE-REVIEW-2026-07-31.md` — resolve the one live contradiction between the code and its own architecture spec (**9.2**), de-duplicate the three copy-defined helpers (**9.4**), restore the abstract-repository contract in the prompt slice (**9.5**), align two divergent conventions (**9.7**), stop logging email addresses (**9.12**), fix the dependency/config nits (**9.9**), and make `ruff` + `ty` genuinely clean repo-wide (**9.10**). Two items get written decisions rather than code: **9.3** and **9.8**.

**Architecture:** Everything here stays inside the existing `routers/ → services/ → repositories/ → db/models` layering; nothing changes a wire contract except where explicitly flagged and declined. The one structural change (Task 1's decision, implemented in Tasks 9–10 if option (a) is chosen) moves the interview briefing from a service that composes three other services into a pure render module plus per-consumer repository fetch — the same shape `core/attention.py` and `core/constants.py:advance_level` already use to keep that rule absolute.

**Tech Stack:** Python 3.13 / uv, FastAPI, async SQLAlchemy 2, Pydantic v2 + pydantic-settings, Anthropic SDK, ruff + ty, pytest + pytest-asyncio (auto mode).

## Global Constraints

- **Layering is strict:** `routers/ → services/ → repositories/ → db/models`. Calls flow downward only, and **services never call other services** — *except* exactly as Task 1 decides. Until Task 1 is decided and recorded, do not add a new service→service dependency anywhere.
- **Verification for every task, run inside `backend/`:**
  ```
  uv run poe format && uv run poe lint && uv run poe test
  ```
- **Integration tests hit the shared remote `ai-enablement-hub-test` Postgres** (an approved deviation from the template's in-memory SQLite): slower than unit tests, auto-retried once (`tests/conftest.py` marks them `flaky(reruns=1)`), and under `-n auto` each xdist worker gets its own schema. `conftest.py` hard-asserts the database name ends in `-test`; never repoint it.
- **FastAPI deferred-annotation gotcha:** every module here has `from __future__ import annotations`, so FastAPI evaluates parameter annotations as *strings* against module globals. Any type appearing in a **parameter annotation of a route function or a `Depends` provider** must be imported at **runtime**, never under `if TYPE_CHECKING:` — an unresolvable name silently degrades the parameter into a required query param and every call 422s. This is live in Tasks 4, 5 and 10 (`AbstractPromptRepository`, `BriefingService`, the three repositories). `core/dependencies/database.py`, `domain.py`, `chat.py` and `interview.py` all carry the warning in their module docstrings — keep it there.
- **No Alembic migration in this plan.** Nothing here needs a schema change; if a task appears to, stop and re-scope it.
- **`__all__` and `from __future__ import annotations` in every module touched** — 100% of `src` has both today.
- **Cross-plan ordering:** `2026-07-31-fix-ai-resilience.md` also edits `src/services/interview_service.py` and `src/services/chat_service.py`. Task 8 below runs `ruff format` over `interview_service.py` (a pre-existing formatting failure), and Tasks 9–10 restructure it. **Run the resilience plan first**, or expect to resolve a small conflict in that one file. Nothing else overlaps.
- **Scope fences — these are owned by other plans, do not touch them here:** the chat conversation `kind` check (2.1), the interview component hidden/locked gate (2.2), Swagger-in-prod (2.3), refresh-token reuse detection (2.5), CSP headers (2.9), the interview briefing's `<assessment_briefing>` DATA envelope (2.8), lesson access control + media SAS (3.1), anything under `frontend/`, every Alembic migration, and all CI/deploy/git items.

---

## File structure

**Backend — create:**
- `backend/src/schemas/_validators.py` — the shared `require_non_blank` field validator (Task 2).
- `backend/src/services/interview_briefing.py` — pure briefing renderers + input gatherer (Task 9, option (a) only).
- `backend/src/services/briefing_service.py` — repository-backed briefing provider for the chat path (Task 10, option (a) only).
- `backend/tests/unit/test_interview_briefing.py` — replaces `test_interview_context.py` (Task 10, option (a) only).

**Repo root — modify:**
- `python-be-architecture.md` — the architecture spec lives at the repo root, **not** under `backend/` (Task 1, and the two decision notes at the end).

**Backend — modify:**
- `backend/src/schemas/admin_content.py`, `admin_org.py`, `admin_users.py` (Task 2)
- `backend/src/core/constants.py`, `src/services/maturity_service.py`, `src/services/admin_user_service.py`, `src/services/dashboard_service.py` (Task 3)
- `backend/src/repositories/base.py`, `src/repositories/prompt_repository.py`, `src/services/prompt_service.py`, `src/core/dependencies/prompt.py` (Task 4)
- `backend/src/routers/chat.py`, `src/core/dependencies/interview.py` (Task 5)
- `backend/src/services/email_service.py`, `src/services/entra_service.py`, `src/routers/admin_users.py` (Task 6)
- `backend/pyproject.toml`, `backend/uv.lock`, `src/core/configs/llm.py` (Task 7)
- `backend/src/services/content_improvement_service.py`, `src/core/dependencies/email.py`, `src/core/dependencies/settings.py`, `src/routers/auth.py`, `src/services/token_service.py`, `src/services/email_template_service.py`, `alembic/env.py`, `backend/tests/unit/test_attention.py` (Task 8)
- `backend/src/services/interview_service.py`, `src/core/dependencies/interview.py`, `src/routers/chat.py` (Task 10, option (a) only)

**Backend — delete:**
- `backend/src/services/interview_context.py` (Task 10, option (a) only)

**Task ordering note:** Task 1 is a decision and comes first, as required. Tasks 2–8 are then ordered smallest-blast-radius-first (three of them touch a single file). The 9.2 *implementation* (Tasks 9–10) is deliberately **last** despite belonging to Task 1: it is the largest blast radius in the plan, it depends on Task 3's helper, and it is the only work that disappears entirely if Matthias picks option (b).

---

## Task 1: DECISION — the interview slice's service→service dependency (review item 9.2)

**This task writes no source code.** It costs both options, records the choice in the architecture spec, and gates Tasks 9–10.

**Files:**
- Modify `python-be-architecture.md` (repo root; the "Non-negotiable rules" list, first bullet: *"A service never imports a router; a repository never imports a service. Services never import other services."*)

**Interfaces:**
- *Consumes:* nothing.
- *Produces:* a recorded decision. If **(a)**, Tasks 9–10 execute as written. If **(b)**, Tasks 9–10 are struck and the spec carries a "composer service" carve-out instead.

### The contradiction, verified in current code

`src/services/interview_context.py:173-181`:
```python
    def __init__(
        self,
        surveys: SurveyService,
        maturity: MaturityService,
        learning: LearningService,
    ) -> None:
```
Three **concrete services**, wired at `src/core/dependencies/interview.py:42-47`. `InterviewService.__init__` (`interview_service.py:70-80`) then takes `InterviewContextService` — a second level. Consumers: `routers/interview.py` (indirectly, via `InterviewService.open_interview`/`build_playbook`) and `routers/chat.py:96,107` (directly).

The same codebase refuses this everywhere else, in writing:
- `services/admin_user_service.py:30-32` — *"Token issuance (invite/reset) is deliberately NOT done here … services never call other services."*
- `services/content_improvement_service.py:601-604` — *"Called at the repository layer because services never call other services (python-be-architecture.md)."*
- `core/attention.py:1-9` — *"Both import `attention_for` directly rather than one service calling the other — services never call services."*
- `core/constants.py:41-52` — `advance_level` exists so `MaturityService` and `AdminUserService` need not import each other.
- `services/dashboard_service.py:29-37` — *"It never calls AdminUserService or any other service — the small duplication of fetch lines is the accepted price."*

So the rule has been enforced four times at real cost, and broken once. Code and spec currently contradict each other, and the next agent copies whichever it reads first.

### Option (a) — extract a pure briefing module, keep the rule absolute

**Shape:** `interview_context.py`'s label maps and two render methods become pure functions in a new `services/interview_briefing.py` (no constructor, no I/O). A module-level `async def gather_briefing_inputs(user, *, surveys, content, assignments)` in the same file does the fetching **through repository ABCs handed to it as arguments** — a free function in the services layer touching repositories it is given, which is exactly what a service constructor does, minus the class. `InterviewService` gains those three repositories and calls both; a small new `BriefingService` (repositories only) serves `routers/chat.py`. `InterviewContextService` is deleted.

**Cost, concretely:**
- Create 2 files (~270 lines, ~250 of them label maps moved verbatim), delete 1, modify 3 (`interview_service.py`, `core/dependencies/interview.py`, `routers/chat.py`).
- Test churn: rewrite `tests/unit/test_interview_context.py` → `test_interview_briefing.py` (its `_service()` helper swaps 3 service mocks for 3 repository mocks; the ~10 assertion bodies are unchanged because the rendered strings are unchanged), and extend `test_interview_service.py::_service` with 3 repository mocks. `tests/unit/test_interview_firewall.py` is schema-only and unaffected.
- Depends on Task 3's `module_level_map` helper.
- **Effort: M.**

**Concrete side-benefits (not speculation — count the awaits):**
- Today one interview chat turn runs 6 queries for the briefing: `get_by_user_id` (1) + `MaturityService.effective_level` → `get_complete_levels` + `list_tracks` + `list_modules` + `assigned_lesson_counts_by_module` (4) + `LearningService.learning_status` → `assigned_lesson_counts_by_module` **again** (1). Consolidated: `get_by_user_id` + `list_tracks` + `list_modules` + `assigned_lesson_counts_by_module` = **4**. The survey row already carries what `get_complete_levels` would return (see Task 9 Step 3 for the proof), and one counts read serves both maturity and learning status.
- The renderers become testable with plain data, no `AsyncMock` at all.

**Cost of the rule staying absolute:** the fetch block would normally be duplicated in `InterviewService` and `BriefingService` (the price `dashboard_service.py` pays). `gather_briefing_inputs` as a shared free function removes that duplication without weakening the rule.

### Option (b) — amend the spec to sanction composer services

**Shape:** add a carve-out to `python-be-architecture.md`, e.g.: *"A **composer service** may depend on other services, provided it (1) performs no repository access of its own, (2) performs no writes, (3) returns primitives or DTOs, and (4) is never depended upon by a non-composer. `InterviewContextService` is the reference example."* Zero code change.

**Cost:** ~15 lines of doc. **Effort: S.**

**Risk:** the rule stops being a rule and becomes a judgement call, made by agents, in a codebase directed by two non-programmers. Every clause above needs enforcing by review, and there is no test that can enforce clause (4). The four places that already paid the duplication price become arguably-wasted effort, and the honest follow-up would be to revisit `DashboardService` too — which is 50 lines of deliberate duplication that (b) would make pointless. It also leaves the 2 duplicate queries per chat turn in place.

### Recommendation: **(a)**

One unambiguous rule is worth more to this project than the ~M of churn, the codebase has already voted for it four times, and (a) is the only option that also removes real duplicate work from the hottest AI path. (b) is defensible and cheap; it is not what this codebase has been built to.

- [ ] **Step 1: Get the decision** — Present the two options above to Matthias. **Do not proceed past this step without an answer**; both branches change the spec, and guessing means writing the wrong sentence into the document that governs every future backend change.

- [ ] **Step 2: Record the decision in `python-be-architecture.md`**

  **If (a)** — strengthen the existing bullet in "Non-negotiable rules" (currently: *"**Calls flow downward only.** Router → service → repository → model. A service never imports a router; a repository never imports a service. Services never import other services."*) by appending:
  ```markdown
    When two use cases need the same composed logic, the shared part becomes a **pure
    module** (no constructor, no I/O) that both call — `core/attention.py::attention_for`,
    `core/constants.py::advance_level`, and `services/interview_briefing.py` are the
    reference examples. Where both also need the same *fetch*, write it as a module-level
    `async` function taking the repository ABCs as arguments
    (`interview_briefing.gather_briefing_inputs`); a free function handed repositories is
    not a service dependency. There is no exception to this rule.
  ```

  **If (b)** — add a new subsection after "Non-negotiable rules":
  ```markdown
  ### Sanctioned exception: composer services

  A **composer service** may take other services in its constructor. It must:
  1. perform no repository access of its own,
  2. perform no writes,
  3. return primitives or DTOs, never DB models, and
  4. never be a dependency of a non-composer service.

  `services/interview_context.py::InterviewContextService` is the reference example.
  Anything that does not meet all four conditions is an ordinary service and the
  downward-only rule applies unchanged. Prefer a pure module
  (`core/attention.py::attention_for`, `core/constants.py::advance_level`) when the
  shared part needs no I/O — a composer is the fallback, not the default.
  ```
  Also, under (b): add a matching class docstring line to `InterviewContextService` naming itself a sanctioned composer, so the file and the spec agree at the point of use, and strike Tasks 9–10 from this plan.

- [ ] **Step 3: Commit**
  ```
  git add python-be-architecture.md
  git commit -m "Record the decision on service-to-service dependencies (review 9.2)

The interview slice composed three concrete services while four other places in
the codebase pay real duplication costs to avoid exactly that, and the spec said
'services never import other services'. Code and spec contradicted each other.

Decision: <(a) the rule is absolute, shared logic becomes a pure module | (b)
composer services are sanctioned under four conditions>."
  ```

---

## Task 2: Hoist `_require_non_blank` into `schemas/_validators.py`

Closes review item **9.4a** (and prior audit 4.6, open since 2026-07-09). Three byte-similar copies.

**Files:**
- Create `backend/src/schemas/_validators.py`
- Modify `backend/src/schemas/admin_content.py` (`_require_non_blank` at `:22-26`; four `field_validator` uses at `:54,63,79,94`)
- Modify `backend/src/schemas/admin_org.py` (`:25-29`; uses at `:54,68`)
- Modify `backend/src/schemas/admin_users.py` (`:38-42`; use at `:106`)
- Modify `backend/tests/unit/` — add `backend/tests/unit/test_schema_validators.py`

**Interfaces:**
- *Produces:* `src/schemas/_validators.py` exporting `require_non_blank(value: str | None) -> str | None`. **One** signature covering both existing variants: `admin_content.py`'s copy is `str | None` (its `Update` schemas allow `None`), `admin_org.py`/`admin_users.py`'s are `str`. The `None`-tolerant version is a strict superset — for a required `str` field Pydantic never passes `None` to the validator, so accepting it changes nothing observable.

- [ ] **Step 1: Write the failing test**

  Create `backend/tests/unit/test_schema_validators.py`:
  ```python
  """The shared blank-string field validator. Three schema modules copy-defined
  this before it lived in one place (review 9.4a / prior audit 4.6)."""

  from __future__ import annotations

  import uuid

  import pytest
  from pydantic import ValidationError

  from src.schemas._validators import require_non_blank
  from src.schemas.admin_content import LessonUpdateRequest, TrackCreateRequest
  from src.schemas.admin_org import CompanyCreateRequest
  from src.schemas.admin_users import InviteRequest


  class TestRequireNonBlank:
      def test_passes_a_real_value(self) -> None:
          assert require_non_blank("Copilot") == "Copilot"

      def test_rejects_whitespace_only(self) -> None:
          with pytest.raises(ValueError, match="must not be blank"):
              require_non_blank("   ")

      def test_rejects_empty(self) -> None:
          with pytest.raises(ValueError, match="must not be blank"):
              require_non_blank("")

      def test_allows_none(self) -> None:
          """Optional fields on the Update schemas pass None through — omitting a
          field is not the same as blanking it."""
          assert require_non_blank(None) is None

      def test_does_not_strip(self) -> None:
          """Validation only; the services own trimming (content_service.py
          `.strip()`s on write), so this must not silently change stored values."""
          assert require_non_blank("  Copilot  ") == "  Copilot  "


  class TestWiredIntoTheSchemas:
      """Behaviour parity guards: each of the three modules must still reject a
      blank on the fields it validated before the hoist."""

      def test_track_name_blank_is_rejected(self) -> None:
          with pytest.raises(ValidationError):
              TrackCreateRequest(name="  ", track_type="general", color=None)

      def test_lesson_title_blank_is_rejected(self) -> None:
          with pytest.raises(ValidationError):
              LessonUpdateRequest(title="  ")

      def test_lesson_title_omitted_is_allowed(self) -> None:
          assert LessonUpdateRequest().title is None

      def test_company_name_blank_is_rejected(self) -> None:
          with pytest.raises(ValidationError):
              CompanyCreateRequest(name=" ")

      def test_invite_names_blank_are_rejected(self) -> None:
          with pytest.raises(ValidationError):
              InviteRequest(
                  email="x@example.com", first_name=" ", last_name="Y", project_id=uuid.uuid4()
              )
  ```
  Before writing, confirm the constructor kwargs against the current schemas (`TrackCreateRequest` at `admin_content.py:49-55`, `LessonUpdateRequest` at `:90-96`, `CompanyCreateRequest` at `admin_org.py:51-55`, `InviteRequest` at `admin_users.py:99-107`) and adjust only the kwargs, never the assertions.

- [ ] **Step 2: Run test to verify it fails**
  ```
  cd backend && uv run pytest tests/unit/test_schema_validators.py -v
  ```
  Expected failure: collection error — `ModuleNotFoundError: No module named 'src.schemas._validators'`.

- [ ] **Step 3: Write minimal implementation**

  Create `backend/src/schemas/_validators.py`:
  ```python
  """Field validators shared across the schema modules.

  Underscore-prefixed because it is internal to `schemas/` — nothing outside this
  package should import it. Kept here rather than in `core/` because it is part of
  the wire-validation layer, not a cross-cutting concern.
  """

  from __future__ import annotations

  __all__ = ["require_non_blank"]


  def require_non_blank(value: str | None) -> str | None:
      """Reject a present-but-whitespace-only string; pass None through.

      `None` is allowed so the one function serves both the required-field schemas
      (where Pydantic never hands a validator None) and the all-optional `Update`
      schemas, where an omitted field is legitimately None and only an explicitly
      blanked one is an error. Deliberately does NOT strip: the services own
      trimming on write (`content_service.update_lesson`, `org_service`), and a
      validator that quietly rewrote values would hide that.
      """
      if value is not None and not value.strip():
          msg = "must not be blank"
          raise ValueError(msg)
      return value
  ```

  In each of the three schema modules: delete the local `_require_non_blank` definition and import the shared one, keeping the existing `field_validator(...)` call sites byte-identical apart from the name.

  `admin_content.py` — delete `:22-26`, add after the `__all__` block:
  ```python
  from src.schemas._validators import require_non_blank
  ```
  and change the four uses to `_non_blank = field_validator("name")(require_non_blank)` / `field_validator("title")(require_non_blank)`.

  `admin_org.py` — delete `:25-29`, same import, update `:54,68`.

  `admin_users.py` — delete `:38-42`, same import, update `:106`.

  Keep the local attribute name `_non_blank` on each model: renaming it would be churn with no benefit, and Pydantic keys the validator off the decorated attribute.

- [ ] **Step 4: Run test to verify it passes**
  ```
  cd backend && uv run pytest tests/unit/test_schema_validators.py -v
  cd backend && uv run poe format && uv run poe lint && uv run poe test
  ```

  **Existing tests likely to break:** none expected. The blank-rejection behaviour is asserted from the HTTP side in `tests/integration/test_routers/test_admin_content.py`, `test_admin_org.py` and `test_admin_users.py` (422 on blank names/titles) — those are the real regression guards for this task and must stay green. If any of them flips from 422 to 201, an import was dropped rather than rewired.

- [ ] **Step 5: Commit**
  ```
  git add backend/src/schemas/_validators.py backend/src/schemas/admin_content.py backend/src/schemas/admin_org.py backend/src/schemas/admin_users.py backend/tests/unit/test_schema_validators.py
  git commit -m "Hoist the non-blank field validator into schemas/_validators.py

Review item 9.4a (prior audit 4.6, open since 2026-07-09): copy-defined in
admin_content.py, admin_org.py and admin_users.py. The shared version takes the
None-tolerant signature, which is a strict superset — Pydantic never passes None
to a required field's validator."
  ```

---

## Task 3: Extract the `module_level` map build next to `advance_level`

Closes review item **9.4b**. Prior audit 4.3's fix went halfway: the ladder walk became the shared pure `advance_level`, but the map it consumes is still built by hand in three services — and the third copy arrived *after* that fix, which is the tell.

**Files:**
- Modify `backend/src/core/constants.py` (module docstring; `__all__` at `:12-19`; new function after `advance_level`)
- Modify `backend/src/services/maturity_service.py` (`:53-63`)
- Modify `backend/src/services/admin_user_service.py` (`:77-87`)
- Modify `backend/src/services/dashboard_service.py` (`:88-97`)
- Modify `backend/tests/unit/` — add cases to a new `backend/tests/unit/test_module_level_map.py`

**Interfaces:**
- *Produces:* `module_level_map(tracks: Sequence[Any], modules: Sequence[Any]) -> dict[uuid.UUID, str]` in `src/core/constants.py` — `module_id → its track's required_level`, skipping modules whose `track_id` is not among `tracks` (the current behaviour of all three copies). Task 9 consumes this exact signature.
- Typing note: the three call sites pass ORM `Track`/`Module` lists, and `core/` must not import `db.models` (it currently imports nothing from `src`). Type the parameters structurally via `Protocol` so `core/` stays dependency-free and `ty` still checks the attribute access.

- [ ] **Step 1: Write the failing test**

  Create `backend/tests/unit/test_module_level_map.py`:
  ```python
  """`module_level_map` — the module_id -> required_level map that `advance_level`
  walks. Copy-defined in three services before it lived here (review 9.4b)."""

  from __future__ import annotations

  import uuid
  from types import SimpleNamespace

  from src.core.constants import advance_level, module_level_map

  GI_TRACK, GII_TRACK = uuid.uuid4(), uuid.uuid4()
  GI_MOD, GII_MOD, ORPHAN_MOD = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()

  _TRACKS = [
      SimpleNamespace(id=GI_TRACK, required_level="explore"),
      SimpleNamespace(id=GII_TRACK, required_level="practitioner"),
  ]
  _MODULES = [
      SimpleNamespace(id=GI_MOD, track_id=GI_TRACK),
      SimpleNamespace(id=GII_MOD, track_id=GII_TRACK),
  ]


  def test_maps_each_module_to_its_tracks_required_level() -> None:
      assert module_level_map(_TRACKS, _MODULES) == {
          GI_MOD: "explore",
          GII_MOD: "practitioner",
      }


  def test_a_module_whose_track_is_absent_is_skipped() -> None:
      """All three copies guarded with `if module.track_id in track_level` rather
      than raising — a module whose track is missing from the list must not blow
      up the admin directory or the dashboard."""
      modules = [*_MODULES, SimpleNamespace(id=ORPHAN_MOD, track_id=uuid.uuid4())]

      result = module_level_map(_TRACKS, modules)

      assert ORPHAN_MOD not in result
      assert len(result) == 2


  def test_empty_inputs_give_an_empty_map() -> None:
      assert module_level_map([], []) == {}
      assert module_level_map(_TRACKS, []) == {}


  def test_the_result_feeds_advance_level_unchanged() -> None:
      """End-to-end on the pure pair: one General I module fully done promotes
      explore -> practitioner, which is the behaviour all three call sites want."""
      counts = {GI_MOD: (3, 3), GII_MOD: (2, 0)}

      assert advance_level("explore", module_level_map(_TRACKS, _MODULES), counts) == "practitioner"
  ```

- [ ] **Step 2: Run test to verify it fails**
  ```
  cd backend && uv run pytest tests/unit/test_module_level_map.py -v
  ```
  Expected failure: collection error — `ImportError: cannot import name 'module_level_map' from 'src.core.constants'`.

- [ ] **Step 3: Write minimal implementation**

  In `backend/src/core/constants.py`, extend the imports and `__all__`, and add the function above `advance_level`:
  ```python
  from typing import TYPE_CHECKING, Protocol

  if TYPE_CHECKING:
      from collections.abc import Sequence

  __all__ = [
      "COMPONENTS",
      "DEFAULT_HIDDEN",
      "DEFAULT_LOCKED",
      "LEVEL_ORDER",
      "LEVEL_RANK",
      "advance_level",
      "module_level_map",
  ]


  class _HasRequiredLevel(Protocol):
      """Structural stand-in for `db.models.Track`. Typed structurally so `core/`
      stays free of any `src.db` import (it imports nothing from src today) while
      `ty` still checks the two attributes this function reads."""

      @property
      def id(self) -> uuid.UUID: ...
      @property
      def required_level(self) -> str: ...


  class _HasTrackId(Protocol):
      """Structural stand-in for `db.models.Module`."""

      @property
      def id(self) -> uuid.UUID: ...
      @property
      def track_id(self) -> uuid.UUID: ...


  def module_level_map(
      tracks: Sequence[_HasRequiredLevel], modules: Sequence[_HasTrackId]
  ) -> dict[uuid.UUID, str]:
      """module_id -> the required_level of the track it belongs to.

      The input `advance_level` walks, and the single definition of it: this was
      copy-defined in MaturityService (the learner graph), AdminUserService (the
      admin directory) and DashboardService (the admin dashboard), which is how the
      third copy got written after prior audit 4.3 shared only the ladder walk.

      A module whose `track_id` is not among `tracks` is SKIPPED, not an error —
      preserving all three copies' `if module.track_id in track_level` guard. Such a
      module simply never gates a level.
      """
      track_level = {track.id: track.required_level for track in tracks}
      return {
          module.id: track_level[module.track_id]
          for module in modules
          if module.track_id in track_level
      }
  ```
  Also update the module docstring to say it now holds the shared **pure progress rules** (level ordering, the ladder walk, and the map it walks), not only constants.

  `maturity_service.py:53-63` becomes:
  ```python
          tracks = await self._content.list_tracks()
          modules = await self._content.list_modules()
          counts = await self._assignments.assigned_lesson_counts_by_module(user.id)

          return advance_level(base, module_level_map(tracks, modules), counts)
  ```
  with `from src.core.constants import advance_level, module_level_map`.

  `admin_user_service.py:77-87` — keep `track_name` and `module_track` (both used further down for track progress and in-progress sets) and replace only the `track_level`/`module_level` pair:
  ```python
          tracks = await self._content.list_tracks()
          modules = await self._content.list_modules()
          track_name = {track.id: track.name for track in tracks}
          module_track = {module.id: module.track_id for module in modules}
          module_level = module_level_map(tracks, modules)
  ```

  `dashboard_service.py:88-97` — same treatment, keeping `track_name`, `module_track` and `modules_by_track`:
  ```python
          tracks = await self._content.list_tracks()
          modules = await self._content.list_modules()
          track_name = {track.id: track.name for track in tracks}
          module_track = {module.id: module.track_id for module in modules}
          module_level = module_level_map(tracks, modules)
  ```
  In both, delete the now-unused local `track_level` — check for other uses in the same function before deleting (in `admin_user_service.list_users` and `dashboard_service.overview` its only consumer is the `module_level` comprehension).

- [ ] **Step 4: Run test to verify it passes**
  ```
  cd backend && uv run pytest tests/unit/test_module_level_map.py tests/unit/test_maturity_service.py -v
  cd backend && uv run poe format && uv run poe lint && uv run poe test
  ```

  **Existing tests likely to break:** this is a pure refactor with no behaviour change, so the correct expectation is *nothing breaks*. The tests that prove it are `tests/unit/test_maturity_service.py` (the ladder, with `SimpleNamespace` tracks/modules — note it already uses exactly the structural shape the Protocols describe), `tests/integration/test_routers/test_maturity.py`, `tests/integration/test_routers/test_admin_users.py` (`effective_maturity` in the directory payload) and `tests/integration/test_routers/test_admin_dashboard.py` (the maturity distribution). Run those four before the full sweep.

- [ ] **Step 5: Commit**
  ```
  git add backend/src/core/constants.py backend/src/services/maturity_service.py backend/src/services/admin_user_service.py backend/src/services/dashboard_service.py backend/tests/unit/test_module_level_map.py
  git commit -m "Extract module_level_map next to advance_level

Review item 9.4b: prior audit 4.3 shared the ladder walk but left the map it
walks copy-defined — and a third copy then appeared in DashboardService, which
is the proof the halfway fix didn't hold.

Typed structurally via Protocol so core/ keeps importing nothing from src.
Pure refactor: no behaviour change, guarded by the existing maturity/dashboard/
admin-users tests."
  ```

---

## Task 4: Give the prompt slice its abstract repository

Closes review item **9.5**. `PromptService` types against the concrete `PromptRepository`; all 14 other repositories have an ABC in `repositories/base.py`, and the spec requires it (*"Services type their constructor arg as the `Abstract<Entity>Repository` ABC … so they can be unit-tested with an `AsyncMock`"*).

**Files:**
- Modify `backend/src/repositories/base.py` (`__all__` at `:37-53`; new ABC at the end of the file, after `AbstractCalibrationNoteRepository`)
- Modify `backend/src/repositories/prompt_repository.py` (41 lines; class declaration at `:16`)
- Modify `backend/src/services/prompt_service.py` (`TYPE_CHECKING` import at `:12`; `__init__` at `:67`)
- Modify `backend/src/core/dependencies/prompt.py`
- Modify `backend/tests/unit/test_prompt_service.py` (the `_svc()` helper at `:18-20`)

**Interfaces:**
- *Produces:* `AbstractPromptRepository(ABC)` in `src/repositories/base.py` with `__init__(self, session: AsyncSession)` plus abstract `list_all() -> list[Prompt]`, `get(kind: str) -> Prompt | None`, `upsert(kind: str, content: str, updated_by: uuid.UUID | None) -> None`, `delete(kind: str) -> None` — the exact four methods `PromptRepository` implements today. `PromptService.__init__(self, repo: AbstractPromptRepository)`.

- [ ] **Step 1: Write the failing test**

  In `backend/tests/unit/test_prompt_service.py`, change the `_svc()` helper to mock the **abstraction** (this is the assertion — the service must be constructible from the ABC alone):
  ```python
  from src.repositories.base import AbstractPromptRepository


  def _svc():
      repo = AsyncMock(spec=AbstractPromptRepository)
      return PromptService(repo), repo
  ```
  and delete the now-unused `from src.repositories.prompt_repository import PromptRepository` import. Then append a contract test:
  ```python
  def test_concrete_repository_implements_the_abstraction() -> None:
      """The ABC is the contract, not decoration: PromptRepository must satisfy it
      or the service's type hint is a lie."""
      assert issubclass(PromptRepository, AbstractPromptRepository)


  def test_the_abstraction_covers_every_method_the_service_calls() -> None:
      """Guards the failure mode this task exists to prevent: a method added to the
      concrete repo and called by the service, but never declared on the ABC — so
      AsyncMock(spec=...) silently stops covering it."""
      for name in ("list_all", "get", "upsert", "delete"):
          assert hasattr(AbstractPromptRepository, name)
  ```
  (keeping a `from src.repositories.prompt_repository import PromptRepository` import for the two new tests).

- [ ] **Step 2: Run test to verify it fails**
  ```
  cd backend && uv run pytest tests/unit/test_prompt_service.py -v
  ```
  Expected failure: collection error — `ImportError: cannot import name 'AbstractPromptRepository' from 'src.repositories.base'`.

- [ ] **Step 3: Write minimal implementation**

  In `backend/src/repositories/base.py`: add `Prompt` to the `TYPE_CHECKING` model import block (`:13-35`, alphabetically between `Project…` and `SurveyResponse`), add `"AbstractPromptRepository"` to `__all__` (alphabetically, after `AbstractProposalRepository`), and append the ABC at the end of the file:
  ```python
  class AbstractPromptRepository(ABC):
      """prompts — one row per admin-overridden system prompt `kind`.

      The rows override the shipped `backend/prompts/<kind>.md` files; the request
      path never reads this table directly, it reads the in-process cache
      `services/prompts.py::load_prompt` that `PromptService.refresh_cache` primes
      from here (lifespan startup + every save/reset).
      """

      def __init__(self, session: AsyncSession) -> None:
          self._session = session

      @abstractmethod
      async def list_all(self) -> list[Prompt]:
          """Every stored override. Unordered — the caller renders in
          `KNOWN_PROMPTS` order, which is the admin-facing grouping."""

      @abstractmethod
      async def get(self, kind: str) -> Prompt | None: ...

      @abstractmethod
      async def upsert(self, kind: str, content: str, updated_by: uuid.UUID | None) -> None:
          """Insert or replace the override for `kind`, stamping `updated_at`/
          `updated_by`. `kind` is the primary key, so this is idempotent."""

      @abstractmethod
      async def delete(self, kind: str) -> None:
          """Drop the override so the prompt falls back to the shipped file.
          A no-op when no row exists (reset is idempotent)."""
  ```

  In `backend/src/repositories/prompt_repository.py`: extend the class and drop the now-inherited `__init__`:
  ```python
  from src.repositories.base import AbstractPromptRepository

  __all__ = ["PromptRepository"]


  class PromptRepository(AbstractPromptRepository):
      """`kind` is the PK, so upsert/delete are both idempotent."""
  ```
  (the four method bodies are unchanged; `__init__` comes from the ABC, matching how the other concrete repositories are written — verify against e.g. `calibration_note_repository.py` and keep whichever convention that file uses.)

  In `backend/src/services/prompt_service.py`, change the `TYPE_CHECKING` import and the constructor annotation:
  ```python
  if TYPE_CHECKING:
      from src.repositories.base import AbstractPromptRepository

  ...

      def __init__(self, repo: AbstractPromptRepository) -> None:
  ```
  This stays under `TYPE_CHECKING` because `PromptService.__init__` is **not** FastAPI-inspected — only the `Depends` provider's parameters are.

  In `backend/src/core/dependencies/prompt.py`: the provider's parameter annotation must keep naming the **concrete** `PromptRepository` at runtime (that is the DI layer's job — choosing the implementation — and the annotation is FastAPI-inspected). Read the file and change nothing unless it currently annotates the abstraction; if it does, switch it to the concrete class.

- [ ] **Step 4: Run test to verify it passes**
  ```
  cd backend && uv run pytest tests/unit/test_prompt_service.py tests/unit/test_prompt_seam.py -v
  cd backend && uv run pytest tests/integration/test_routers/test_admin_prompts.py -v
  cd backend && uv run poe format && uv run poe lint && uv run poe test
  ```

  **Existing tests likely to break:** `tests/unit/test_prompt_service.py` is edited by this task by design. `tests/integration/test_routers/test_admin_prompts.py` exercises the real chain and is the regression guard — if it 422s on every route, the DI provider's annotation was moved under `TYPE_CHECKING` (see Global Constraints). `main.py:118` constructs `PromptService(PromptRepository(session))` in `lifespan`; unchanged, since the concrete class satisfies the ABC.

- [ ] **Step 5: Commit**
  ```
  git add backend/src/repositories/base.py backend/src/repositories/prompt_repository.py backend/src/services/prompt_service.py backend/src/core/dependencies/prompt.py backend/tests/unit/test_prompt_service.py
  git commit -m "Add AbstractPromptRepository and type PromptService against it

Review item 9.5: the prompt slice was the one of fifteen that skipped the
abstract-repository contract python-be-architecture.md requires, so its service
was typed against the concrete class and its unit tests mocked the
implementation rather than the contract."
  ```

---

## Task 5: Drop the redundant chat try/except and align the AI-surface settings read

Closes review item **9.7**. Two small divergences, both one-file-each.

**Files:**
- Modify `backend/src/routers/chat.py` (`get_conversation` at `:165-182`; the `NotFoundError` import at `:25`)
- Modify `backend/src/core/dependencies/interview.py` (`require_interview_surface` at `:62-77`)
- Modify `backend/tests/integration/test_routers/test_chat.py` (assert the 404 still has the standard shape)
- Modify `backend/tests/unit/test_require_ai_surface.py` (add the interview-gate parity case)

**Interfaces:**
- *Consumes:* the `NotFoundError` handler already registered at `main.py:244-246`; `OrgService.resolve_ai_settings(project_id) -> dict[str, bool]` (returns **every** key in `_AI_KINDS`, never a partial dict — see `org_service.py:100-106`).
- *Produces:* no contract change. `GET /api/chat/conversations/{id}` still answers 404 with `{"error":{"code":"not_found","message":"Conversation not found"}}` — via the central handler instead of a hand-rolled `HTTPException`.

- [ ] **Step 1: Write the failing test**

  The routers-are-try/except-free rule has no test today, so add one that pins the *observable* result (so the refactor is provably behaviour-preserving) plus a source-level assertion that the hand-catch is gone. Append to `backend/tests/integration/test_routers/test_chat.py`, in the class covering the GET endpoints:
  ```python
      async def test_unknown_conversation_404s_through_the_central_handler(
          self,
          chat_client: Callable[[FakeLlmClient], AsyncClient],
          db_session: AsyncSession,
          test_settings: Settings,
      ) -> None:
          """Same body either way — the point is that the router no longer needs a
          try/except to produce it (main.py:244 maps NotFoundError)."""
          user = await create_user(db_session, email="chat-404@example.com")
          client = chat_client(FakeLlmClient(chunks=[]))

          response = await client.get(
              f"/api/chat/conversations/{uuid.uuid4()}",
              headers=auth_headers(user, test_settings),
          )

          assert response.status_code == 404
          assert response.json() == {
              "error": {"code": "not_found", "message": "Conversation not found"}
          }


      async def test_the_chat_router_holds_no_try_except(self) -> None:
          """Convention guard (python-be-architecture.md: domain exceptions are
          mapped centrally in main.py). Cheap, and it fails loudly the next time
          someone reaches for a local catch."""
          source = Path(chat_router_module.__file__).read_text(encoding="utf-8")
          assert "except NotFoundError" not in source
  ```
  Add to that file's imports:
  ```python
  from pathlib import Path

  from src.routers import chat as chat_router_module
  from tests.fixtures.factories import create_company, create_project, create_user
  ```
  (`create_user` is already imported; extend the existing line rather than duplicating it.)

  And append to `backend/tests/unit/test_require_ai_surface.py`:
  ```python
  async def test_interview_gate_reads_the_settings_map_like_its_sibling() -> None:
      """require_interview_surface used `.get("interview", False)` while
      require_ai_surface used `settings[kind]`, implying the map might be partial.
      It never is — resolve_ai_settings returns every key in _AI_KINDS — so the two
      gates should read it identically."""
      org = AsyncMock(spec=OrgService)
      org.resolve_ai_settings.return_value = {
          "chatbot": False,
          "assessment": False,
          "lesson": False,
          "interview": False,
      }
      user = type("U", (), {"project_id": uuid.uuid4()})()

      with pytest.raises(HTTPException) as exc_info:
          await require_interview_surface(user=user, org=org)  # ty: ignore[invalid-argument-type]
      assert exc_info.value.status_code == 403

      org.resolve_ai_settings.return_value["interview"] = True
      await require_interview_surface(user=user, org=org)  # ty: ignore[invalid-argument-type]


  async def test_interview_gate_403s_without_a_project() -> None:
      org = AsyncMock(spec=OrgService)
      user = type("U", (), {"project_id": None})()

      with pytest.raises(HTTPException) as exc_info:
          await require_interview_surface(user=user, org=org)  # ty: ignore[invalid-argument-type]
      assert exc_info.value.status_code == 403
      org.resolve_ai_settings.assert_not_awaited()
  ```
  with `from src.core.dependencies.interview import require_interview_surface` added to the imports.

- [ ] **Step 2: Run test to verify it fails**
  ```
  cd backend && uv run pytest tests/integration/test_routers/test_chat.py -k "404 or try_except" -v
  cd backend && uv run pytest tests/unit/test_require_ai_surface.py -v
  ```
  Expected failure: `test_the_chat_router_holds_no_try_except` fails with `assert 'except NotFoundError' not in source`. The 404-body test and the two interview-gate tests pass already — they are the behaviour-preservation guards, and the second interview test is new coverage for a dependency that had none.

- [ ] **Step 3: Write minimal implementation**

  In `backend/src/routers/chat.py`, replace `get_conversation` (`:165-182`) with:
  ```python
  @router.get("/conversations/{conversation_id}", response_model=ConversationDetailResponse)
  async def get_conversation(
      conversation_id: uuid.UUID,
      user: CurrentUserDep,
      chat_service: ChatServiceDep,
  ) -> ConversationDetailResponse:
      """NotFoundError propagates to main.py's handler — same 404 body, no local
      try/except (python-be-architecture.md keeps routers try/except-free)."""
      if chat_service is None:
          raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat is not configured")
      conversation, messages = await chat_service.get_conversation_detail(
          user_id=user.id, conversation_id=conversation_id
      )
      return ConversationDetailResponse(
          conversation=ConversationSummary.model_validate(conversation),
          messages=[MessageResponse.model_validate(m) for m in messages],
      )
  ```
  and drop the now-unused import at `:25`:
  ```python
  from src.services.exceptions import NotFoundError   # DELETE
  ```
  (`ruff`'s F401 will catch it if missed.)

  In `backend/src/core/dependencies/interview.py`, change the settings read at `:72-73` to match `require_ai_surface`:
  ```python
      settings = await org.resolve_ai_settings(user.project_id)
      # `settings["interview"]`, not `.get(...)`: resolve_ai_settings always
      # returns every key in _AI_KINDS (org_service.py), so a `.get` default
      # would only hide a future typo in the kind name. Same read as
      # require_ai_surface.
      if not settings["interview"]:
  ```

- [ ] **Step 4: Run test to verify it passes**
  ```
  cd backend && uv run pytest tests/integration/test_routers/test_chat.py tests/unit/test_require_ai_surface.py -v
  cd backend && uv run poe format && uv run poe lint && uv run poe test
  ```

  **Existing tests likely to break:** `tests/integration/test_routers/test_chat.py`'s existing "unknown conversation is 404" / "someone else's conversation is 404" cases — both must stay green and prove the body is unchanged. Nothing exercises `require_interview_surface` over HTTP today (review item 4.6), so the two new unit tests are the only coverage the `[...]`-vs-`.get` change has; do not skip them.

- [ ] **Step 5: Commit**
  ```
  git add backend/src/routers/chat.py backend/src/core/dependencies/interview.py backend/tests/integration/test_routers/test_chat.py backend/tests/unit/test_require_ai_surface.py
  git commit -m "Drop the redundant chat NotFoundError catch; align the AI-surface read

Review item 9.7: routers/chat.py hand-caught NotFoundError -> 404 that
main.py:244 already maps identically, and require_interview_surface read the
settings map with .get(..., False) while require_ai_surface used settings[kind]
— implying a partial map that resolve_ai_settings never returns.

Same 404 body, now from the central handler; adds the first tests for
require_interview_surface."
  ```

---

## Task 6: Log ids, not email addresses

Closes review item **9.12** (prior audit 7.3d, unchanged since 2026-07-09). These lines land in Log Analytics, which is a different retention and access boundary than the database.

**Files:**
- Modify `backend/src/services/email_service.py` (`:53`)
- Modify `backend/src/services/entra_service.py` (`:132,136,140,145-150,152`)
- Modify `backend/src/routers/admin_users.py` (`:243-251` — verify, see below)
- Modify `backend/tests/unit/test_email_service.py`, `backend/tests/unit/test_entra_service.py`

**Interfaces:**
- *Consumes:* `EmailService.send(to, content) -> bool` keeps its signature; only the log line changes. `EmailSender` protocol unchanged.
- *Produces:* no email address in any log record emitted by `src/`. The Entra `oid` **stays** — it is the opaque identifier the whole invite-gated flow is debugged from, and it is not a contact address.

- [ ] **Step 1: Write the failing test**

  Append to `backend/tests/unit/test_email_service.py`:
  ```python
  class TestLogHygiene:
      """Review item 9.12: these records go to Log Analytics, whose retention and
      access are separate from the database's. The subject is fine; the recipient
      is not."""

      async def test_a_failed_send_does_not_log_the_recipient(
          self, caplog: pytest.LogCaptureFixture
      ) -> None:
          with caplog.at_level(logging.ERROR, logger="src.services.email_service"):
              ok = await _service(RaisingSender()).send("sarah.jones@example.com", CONTENT)

          assert ok is False
          rendered = "\n".join(record.getMessage() for record in caplog.records)
          assert "sarah.jones@example.com" not in rendered
          assert "sarah.jones" not in rendered
          # Still diagnosable: which email failed, and that it failed at all.
          assert "Hello" in rendered
  ```
  with `import logging` and `import pytest` added.

  Append to `backend/tests/unit/test_entra_service.py` (adapt the fixture/helper names to that file's existing conventions — read it first):
  ```python
  class TestLogHygiene:
      async def test_rejected_signin_logs_the_oid_not_the_email(
          self, caplog: pytest.LogCaptureFixture
      ) -> None:
          """The oid is the identifier this flow is debugged from and is not a
          contact address, so it stays. The email must not."""
          users = AsyncMock(spec=AbstractUserRepository)
          users.get_by_external_id.return_value = None
          users.get_by_email.return_value = None
          service = EntraService(TEST_ENTRA, users, _jwks())
          claims = {"oid": "0000-oid-1234", "email": "sarah.jones@example.com"}

          with (
              caplog.at_level(logging.WARNING, logger="src.services.entra_service"),
              pytest.raises(EntraUserNotFoundError),
          ):
              await service.resolve_user(claims)

          rendered = "\n".join(record.getMessage() for record in caplog.records)
          assert "sarah.jones@example.com" not in rendered
          assert "0000-oid-1234" in rendered
  ```

- [ ] **Step 2: Run test to verify it fails**
  ```
  cd backend && uv run pytest tests/unit/test_email_service.py::TestLogHygiene tests/unit/test_entra_service.py::TestLogHygiene -v
  ```
  Expected failure: both fail on `assert "sarah.jones@example.com" not in rendered` — `email_service.py:53` formats `%s` with `to`, and `entra_service.py:140` formats `email=%s`.

- [ ] **Step 3: Write minimal implementation**

  `email_service.py` — the service only ever receives an address, never a user id, so the fix is to drop the recipient rather than substitute an id (adding a `user_id` parameter would change the transport's signature for a log line). Replace `:52-54`:
  ```python
          except Exception:
              # Deliberately no recipient: this line lands in Log Analytics, and
              # the caller already knows who it was sending to (it returns False
              # and reports email_status="failed" per recipient). The subject
              # identifies WHICH email failed, which is what triage needs.
              logger.exception("email %r could not be sent", content.subject)
              return False
  ```

  `entra_service.py` — keep every `oid`, drop every email:
  - `:132` (linked user inactive) already logs only the oid — leave it.
  - `:134-136` (email drift): the whole point of the line is that two addresses differ, so it cannot keep both and stay useful. Reduce it to the fact plus the oid:
    ```python
              if email and user.email != email:
                  # Informational only — oid wins, an Entra email change never locks out.
                  # Neither address is logged (review 9.12): the oid is enough to look
                  # both up, and this line exists only to explain a support question.
                  logger.info("entra email differs from the hub record (oid=%s)", oid)
    ```
  - `:139-141` (no invited user): the email is the *lookup key* that failed, so losing it entirely costs real diagnosability. Log its domain only — enough to tell "wrong tenant" from "not invited", with no individual identified:
    ```python
          if user is None or not user.is_active:
              logger.warning(
                  "entra sign-in rejected: no invited user (oid=%s email_domain=%s)",
                  oid,
                  email.rpartition("@")[2] or "unknown",
              )
              raise EntraUserNotFoundError
    ```
  - `:145-150` (email already linked to another oid): drop the address, keep both oids — the conflicting pair is the diagnosis:
    ```python
              logger.error(
                  "entra sign-in rejected: this hub user is already linked to another oid "
                  "(hub_user=%s incoming_oid=%s)",
                  user.id,
                  oid,
              )
    ```
  - `:152` (first-login link): replace the email with the user id:
    ```python
          logger.info("entra first-login link: user=%s ← oid=%s", user.id, oid)
    ```

  `routers/admin_users.py:243-251` — read this before changing anything. The bulk-invite log line records counts plus `admin=%s project=%s` (ids), which is already clean; the per-row statuses stay in the HTTP response, not the log. **If** it logs no address, leave it untouched and drop it from this task's file list.

- [ ] **Step 4: Run test to verify it passes**
  ```
  cd backend && uv run pytest tests/unit/test_email_service.py tests/unit/test_entra_service.py -v
  cd backend && uv run poe format && uv run poe lint && uv run poe test
  ```

  **Existing tests likely to break:** any existing assertion on the *text* of these log lines. Grep before editing:
  ```
  cd backend && uv run python -c "print()" && grep -rn "caplog" tests --include=*.py
  ```
  `tests/unit/test_entra_service.py` is the likely candidate (it covers the drift/reject/link branches); update message assertions there, never the behaviour.

- [ ] **Step 5: Commit**
  ```
  git add backend/src/services/email_service.py backend/src/services/entra_service.py backend/tests/unit/test_email_service.py backend/tests/unit/test_entra_service.py
  git commit -m "Log ids and domains instead of email addresses

Review item 9.12 (prior audit 7.3d): the ACS failure line logged the recipient
and four Entra lines logged user email addresses at info/warning, all landing in
Log Analytics — a different retention and access boundary than the database.

The Entra oid stays (opaque identifier, not a contact address); the rejected
sign-in keeps the email DOMAIN only, which still separates 'wrong tenant' from
'not invited' without identifying anyone."
  ```

---

## Task 7: Dependency & config hygiene

Closes review item **9.9**. `anthropic` is unpinned *and* in the `prod` extra while being a hard top-level import of `src` — so `uv sync --extra dev` alone cannot boot the app, and a re-lock could pull a breaking major. This is the exact mistake prior audit 11.2 fixed for ACS; it recurred.

**Files:**
- Modify `backend/pyproject.toml` (`dependencies` `:6-30`; `optional-dependencies` `:32-52`)
- Modify `backend/uv.lock` (regenerated, committed)
- Modify `backend/src/core/configs/llm.py`
- Modify `backend/tests/unit/test_llm_settings.py`, `backend/tests/unit/test_llm_dependency.py`

**Interfaces:**
- *Produces:* `anthropic~=0.119` in main dependencies (locked version is **0.119.0** — `uv.lock` L119-120); `httptools~=0.8` pinned (locked **0.8.0** — `uv.lock` L629-630); `httpx~=0.28` declared once; `aiosqlite` gone; `LlmSettings` down to two fields (`model`, `api_key`).

**Verified facts this task rests on:**
- `src/services/llm_service.py:7` is a module-level `import anthropic`, and `main.py` imports it transitively via the routers — so `anthropic` is a hard runtime requirement of `src`, not an optional extra.
- `uv.lock` records it with no specifier and `marker = "extra == 'prod'"` (L49).
- `httpx` is declared twice: main deps (L58 of the lock's metadata: `specifier = "~=0.28"`) and dev extra (L59: `marker = "extra == 'dev'", specifier = "~=0.28"`).
- `aiosqlite~=0.20` is in the dev extra (lock L47) and referenced **nowhere** in `src` or `tests` — the only `sqlite` mentions in the repo are the two dead branches in `core/configs/database.py:11,38`, and the test suite is PG-only by design (`conftest.py`).
- `LlmSettings.provider` is required config that nothing reads: `get_llm_service` (`core/dependencies/llm.py:22-32`) always builds `AnthropicLlmClient`.

- [ ] **Step 1: Write the failing test**

  Create `backend/tests/unit/test_dependency_declarations.py`:
  ```python
  """pyproject.toml invariants. These are cheap and they are the only thing that
  would have caught review item 9.9 twice (prior audit 11.2 fixed the identical
  mistake for azure-communication-email; it recurred with anthropic)."""

  from __future__ import annotations

  import tomllib
  from pathlib import Path

  _PYPROJECT = Path(__file__).resolve().parents[2] / "pyproject.toml"


  def _project() -> dict:
      return tomllib.loads(_PYPROJECT.read_text(encoding="utf-8"))["project"]


  def test_every_main_dependency_has_an_upper_bound() -> None:
      """`~=` or `==` only. `uv.lock` + --frozen makes the container
      deterministic, but a re-lock must not be able to pull a breaking major."""
      unbounded = [
          dep
          for dep in _project()["dependencies"]
          if "~=" not in dep and "==" not in dep and "<" not in dep
      ]
      assert unbounded == []


  def test_every_optional_dependency_has_an_upper_bound() -> None:
      unbounded = [
          dep
          for group in _project()["optional-dependencies"].values()
          for dep in group
          if "~=" not in dep and "==" not in dep and "<" not in dep
      ]
      assert unbounded == []


  def test_anthropic_is_a_main_dependency() -> None:
      """src/services/llm_service.py imports it at module level and main.py pulls
      that in transitively, so `uv sync --extra dev` must be able to start the
      app. An extra cannot express that."""
      assert any(dep.startswith("anthropic") for dep in _project()["dependencies"])


  def test_no_dependency_is_declared_twice() -> None:
      def _name(dep: str) -> str:
          for sep in ("~=", "==", ">=", "<", "["):
              dep = dep.split(sep)[0]
          return dep.strip().lower()

      project = _project()
      names = [_name(d) for d in project["dependencies"]]
      for group in project["optional-dependencies"].values():
          names.extend(_name(d) for d in group)
      duplicates = {n for n in names if names.count(n) > 1}
      assert duplicates == set()
  ```
  And in `backend/tests/unit/test_llm_settings.py`, drop the `provider` argument and its assertion; in `backend/tests/unit/test_llm_dependency.py`, drop `provider=` from the two `LlmSettings(...)` constructions.

- [ ] **Step 2: Run test to verify it fails**
  ```
  cd backend && uv run pytest tests/unit/test_dependency_declarations.py -v
  ```
  Expected failure: `test_every_optional_dependency_has_an_upper_bound` fails with `assert ['httptools', 'anthropic'] == []`; `test_anthropic_is_a_main_dependency` fails with `assert False`; `test_no_dependency_is_declared_twice` fails with `assert {'httpx'} == set()`. `test_every_main_dependency_has_an_upper_bound` passes already (every main dep is `~=` today) and is the guard that keeps it that way.
  `tests/unit/test_llm_settings.py` will additionally fail with a Pydantic `ValidationError` for the missing required `provider` until Step 3 removes the field.

- [ ] **Step 3: Write minimal implementation**

  In `backend/pyproject.toml`, add to `dependencies` (place it next to the other AI/infra deps, with the rationale — this file's existing comments set that standard):
  ```toml
      # Anthropic API client. A MAIN dependency, not a prod extra: it is a
      # module-level import in services/llm_service.py, which main.py pulls in via
      # the routers, so the app cannot start without it in any environment. Bounded
      # like every other dep — an unbounded SDK is how prior audit 11.2 happened.
      "anthropic~=0.119",
  ```
  and rewrite the extras:
  ```toml
  [project.optional-dependencies]
  dev = [
      "pytest~=8.3",
      "pytest-asyncio~=1.0",
      "pytest-cov~=6.0",
      "ruff~=0.11",
      "poethepoet~=0.30",
      "pytest-xdist~=3.8",
      # Auto-retry integration tests once on failure — they hit a real remote
      # Postgres and occasionally see a transient blip under parallel load.
      "pytest-rerunfailures~=15.0",
  ]
  prod = [
      # uvicorn's C HTTP parser, used only by the container entrypoint
      # (startup.py passes http="httptools").
      "httptools~=0.8",
  ]
  ```
  Changes made there, each deliberate:
  - `httpx` removed from `dev` — it stays a main dependency (Entra's server-side code exchange needs it at runtime), and the test client uses that same install.
  - `aiosqlite` removed — unreferenced; the SQLite path was abandoned.
  - `anthropic` moved out of `prod`.
  - `pytest-xdist>=3.8.0` / `pytest-rerunfailures>=15.0` tightened to `~=` so the new invariant test holds for them too.

  In `backend/src/core/configs/llm.py`, delete `provider`:
  ```python
  class LlmSettings(BaseModel):
      """Anthropic API settings; env prefix `LLM__` (see Settings).

      Both fields are required: setting one `LLM__*` variable with the other
      missing must fail startup loudly, never half-enable the feature (mirrors
      EmailSettings).

      There is deliberately no `provider` field. It used to exist, was required,
      and nothing ever read it — `core/dependencies/llm.py` always builds
      `AnthropicLlmClient`. A stale `LLM__PROVIDER` in any environment is
      harmless: pydantic's default `extra="ignore"` drops unknown nested keys.
      The second-provider seam is the `LlmClient` Protocol, not a config string.
      """

      model_config = ConfigDict(frozen=True)

      model: str
      api_key: SecretStr
  ```
  **Why delete rather than make it load-bearing:** the tempting alternative is `provider: Literal["anthropic"]`. Do not do that. Whether the live revision sets `LLM__PROVIDER`, and with what casing, is **unverified** (`infra/containerapp.yaml` contains no `LLM__*` keys at all — the live values were set outside it), so a `Literal` would turn an unknown production string into a **startup failure**. Deletion is inert either way.

  Then re-lock and verify the container's install path still resolves:
  ```
  cd backend && uv lock
  cd backend && uv sync --extra dev
  cd backend && uv run python -c "import anthropic, src.main; print(anthropic.__version__)"
  ```
  The last command is the point of the whole task: it must succeed with **no** `--extra prod`.

- [ ] **Step 4: Run test to verify it passes**
  ```
  cd backend && uv run pytest tests/unit/test_dependency_declarations.py tests/unit/test_llm_settings.py tests/unit/test_llm_dependency.py -v
  cd backend && uv run poe format && uv run poe lint && uv run poe test
  ```
  Also confirm the frozen install the Dockerfile actually runs still resolves (it keeps `--extra prod` for `httptools`):
  ```
  cd backend && uv sync --frozen --no-dev --no-install-project --extra prod
  ```

  **Existing tests likely to break:** `tests/unit/test_llm_settings.py` and `test_llm_dependency.py` are edited here by design (both currently pass `provider="anthropic"`). Nothing else constructs `LlmSettings` — `tests/conftest.py` sets `llm=None`. Grep to confirm before committing:
  ```
  cd backend && grep -rn "LlmSettings(" src tests
  ```

- [ ] **Step 5: Commit**
  ```
  git add backend/pyproject.toml backend/uv.lock backend/src/core/configs/llm.py backend/tests/unit/test_dependency_declarations.py backend/tests/unit/test_llm_settings.py backend/tests/unit/test_llm_dependency.py
  git commit -m "Fix dependency declarations and drop the unread LLM provider field

Review item 9.9. anthropic (locked 0.119.0) was unpinned AND declared in the
prod extra despite being a module-level import of src, so `uv sync --extra dev`
could not start the app and a re-lock could pull a breaking major — the same
mistake prior audit 11.2 fixed for azure-communication-email. Now
anthropic~=0.119 in main deps.

Also: httptools~=0.8 pinned, httpx declared once (main only), dead aiosqlite
dropped, xdist/rerunfailures tightened to ~=, and LlmSettings.provider deleted
(nothing read it; a Literal would risk a startup failure on an unverified prod
value, whereas extra=\"ignore\" makes deletion inert).

Adds tests/unit/test_dependency_declarations.py so the unbounded-dependency
mistake cannot recur a third time."
  ```

---

## Task 8: Make `ruff` and `ty` clean repo-wide

Closes review item **9.10**. Today: `ruff check .` reports **48** violations (all in `scripts/`), `ruff format --check .` reports 1 file, `uvx ty check .` reports **24** diagnostics (15 in `scripts/`, 3 in `tests/`, 6 in `src`/`alembic`).

**Files:**
- Modify `backend/pyproject.toml` (`[tool.ruff]` at `:64-66`; new `[tool.ty.src]`)
- Modify `backend/src/services/interview_service.py` (formatting only)
- Modify `backend/src/services/content_improvement_service.py` (`_record_failure` at `:675-677`)
- Modify `backend/src/core/dependencies/email.py` (`:23`)
- Modify `backend/src/services/token_service.py` (`TokenPurpose`/`_ACTION_PURPOSES` at `:26-31`)
- Modify `backend/src/routers/auth.py` (`:119`)
- Modify `backend/src/services/email_template_service.py` (`ResolvedTemplate` at `:25-30`, `resolve`/`get_templates`)
- Modify `backend/src/core/dependencies/settings.py` (`:13`), `backend/alembic/env.py` (`:37`)
- Modify `backend/tests/unit/test_attention.py` (`:31,45,53`)

**Interfaces:**
- *Produces:* `uv run poe lint`, `uv run ruff format --check .` and `uvx ty check .` all exit 0 from `backend/`. `ActionTokenPurpose = Literal["invite", "reset"]` exported from `src/services/token_service.py`; `ResolvedTemplate.purpose` typed `EmailPurpose`.

- [ ] **Step 1: Record the baseline (this task is a pure-refactor + config task — there is no behaviour to test)**

  Run and record the exact counts, so "clean" is measured rather than asserted:
  ```
  cd backend && uv run ruff check . --output-format=concise | tail -3
  cd backend && uv run ruff format --check .
  cd backend && uvx ty check . 2>&1 | tail -3
  ```
  Expected baseline: `Found 48 errors.` · `1 file would be reformatted, 275 files already formatted` · `Found 24 diagnostics`.

  Then record the behavioural baseline green, since every source edit below must be behaviour-neutral:
  ```
  cd backend && uv run pytest tests/unit/test_attention.py tests/unit/test_content_improvement_service.py tests/unit/test_email_service.py tests/unit/test_email_template_service.py tests/unit/test_token_service.py -v
  cd backend && uv run pytest tests/integration/test_routers/test_auth_flows.py tests/integration/test_routers/test_invite_lifecycle.py tests/integration/test_routers/test_admin_email_templates.py -v
  ```
  All must be green **before** any edit. These are the files whose types this task narrows.

- [ ] **Step 2: Exclude `scripts/` from both tools, with the rationale in the file**

  In `backend/pyproject.toml`:
  ```toml
  [tool.ruff]
  line-length = 100
  target-version = "py313"
  # One-off content-authoring and data-migration scripts, kept for provenance and
  # run by hand at most once each. They are not imported by src or tests (verified:
  # no `from scripts`/`import scripts` anywhere), they never ship — the Dockerfile
  # copies only src/, prompts/, alembic/ and startup.py — and lint-churning ~48
  # findings across throwaway files would rewrite history nobody reads for zero
  # production benefit. Excluded rather than fixed, on purpose. src/, tests/ and
  # alembic/ stay fully linted and type-checked; if a script ever becomes
  # importable by src, delete this line first.
  extend-exclude = ["scripts"]

  [tool.ty.src]
  # Same rationale as ruff's extend-exclude above: 15 of the 24 ty diagnostics are
  # unresolved sibling imports inside scripts/content_qa, which is a package only
  # when run from its own directory.
  exclude = ["scripts"]
  ```
  Verify the `ty` key is actually honoured — `ty` is pre-1.0 and its config surface moves:
  ```
  cd backend && uvx ty check . 2>&1 | grep -c "scripts"
  ```
  Expect `0`. If it still reports `scripts/`, try `[tool.ty] exclude = ["scripts"]`, and if neither works, fall back to `uvx ty check src tests alembic` in a `poe ty` task and say so in a comment — do **not** leave the exclusion silently ineffective.

  **Judgement recorded:** exclusion beats cleaning here. The alternative is ~48 mechanical edits (E501 line wraps, unused imports, `l`→`lesson` renames) across `scripts/content_qa/*` — files that are one-shot artifacts, some of which pair with committed JSON DB dumps (review item 5.2 wants the whole folder relocated anyway). Cleaning them would produce a large diff whose only effect is to make a lint number go down, and it would be thrown away if 5.2 moves the folder.

- [ ] **Step 3: Fix the real `src` findings**

  **(a) `ruff format` on `interview_service.py`** — no manual edit, just:
  ```
  cd backend && uv run ruff format src/services/interview_service.py
  ```
  (If the resilience plan ran first, this may already be clean.)

  **(b) `content_improvement_service.py:317` — `BaseException` vs `Exception`.** `asyncio.gather(..., return_exceptions=True)` hands back `BaseException`, and `_record_failure`'s parameter is `Exception`. Widen the parameter — its body only reads `type(exc).__name__` and `str(exc)`, both valid on `BaseException`:
  ```python
      async def _record_failure(
          self, lesson: Lesson, feedback_items: list[Feedback], exc: BaseException
      ) -> None:
          """Store a `failed` proposal so the lesson leaves the queue and the
          admin can see WHY in the review UI. Rejecting it makes its source
          feedback eligible for a future run again.

          `BaseException`, not `Exception`: gather(return_exceptions=True) hands
          the failure back as a value of that type, and narrowing here would be a
          lie about what the caller can pass.
          """
  ```

  **(c) `core/dependencies/email.py:23` — `from_connection_string` on the SDK's class union.** The classmethod exists only on `azure.communication.email._patch.EmailClient`, so `ty` cannot resolve it on the union. Suppress it narrowly, matching how `services/llm_service.py:101-139` already handles SDK typing gaps:
  ```python
      return EmailClient.from_connection_string(  # ty: ignore[unresolved-attribute]
          connection_string, retry_total=0, connection_timeout=5, read_timeout=10
      )
  ```
  Add a one-line comment above it explaining the union, so the next reader does not "fix" it by casting.

  **(d) `routers/auth.py:119` — the cast is to the wrong Literal.** `InviteInfoResponse.purpose` is `Literal["invite", "reset"]` (`schemas/auth.py:54`) but the code casts to `TokenPurpose`, which is the three-member `Literal["invite", "reset", "entra_login"]`. Give the action subset its own name in `token_service.py` (next to `_ACTION_PURPOSES`, which is exactly this set):
  ```python
  TokenPurpose = Literal["invite", "reset", "entra_login"]
  # The subset reachable via the invite/set-password endpoints. `entra_login` is
  # deliberately excluded: a leaked login code must never be able to set a
  # password. Named so callers that only handle these two can say so in types.
  ActionTokenPurpose = Literal["invite", "reset"]

  _ACTION_PURPOSES: tuple[ActionTokenPurpose, ...] = ("invite", "reset")
  ```
  add `"ActionTokenPurpose"` to that module's `__all__`, and in `routers/auth.py` change the import and the cast:
  ```python
  from src.services.token_service import ActionTokenPurpose, TokenPair, TokenService
  ...
          # The DB CHECK constraint restricts purpose to invite|reset, and
          # peek_action_token filters to _ACTION_PURPOSES, so this narrowing holds.
          purpose=cast("ActionTokenPurpose", auth_token.purpose),
  ```
  Check whether `TokenPurpose` is still used in `auth.py` after this; if not, drop it from the import (F401 will say so).

  **(e) `routers/admin_email_templates.py:44` — `str` where a Literal is expected.** The type that is wrong is `ResolvedTemplate.purpose: str`, not the router. `src/schemas/email_templates.py:15` already defines `EmailPurpose = Literal["invite", "reset"]`; services may depend on schemas, so use it in `src/services/email_template_service.py`:
  ```python
  from src.schemas.email_templates import EmailPurpose

  class ResolvedTemplate(NamedTuple):
      purpose: EmailPurpose
      subject: str
      body_markdown: str
      is_custom: bool

  ...
      _PURPOSES: tuple[EmailPurpose, ...] = ("invite", "reset")

      async def resolve(self, project_id: uuid.UUID | None, purpose: EmailPurpose) -> ResolvedTemplate:
  ```
  Every caller already passes a `Literal["invite", "reset"]` (`admin_email_templates.py:31` `Purpose`, `admin_users.py:93` `purpose: Literal["invite", "reset"]`), so no call site changes. Follow the compiler: if `ty` then flags `DEFAULT_TEMPLATES[purpose]` or `row.purpose`, narrow those the same way rather than reaching for `cast`.

  **(f) Two stale suppressions.** Delete the `# ty: ignore[missing-argument]` comment from `src/core/dependencies/settings.py:13` and `alembic/env.py:37`. Keep the explanatory comment above each (`# auth is populated from AUTH__* env vars at runtime`) — that is still true and still the reason the call looks argument-less.

- [ ] **Step 4: Fix the three `tests/` findings and verify everything is clean**

  `backend/tests/unit/test_attention.py:31,45,53` all unpack `attention_for(...)`, whose return type is `tuple[str, str] | None`. Assert first, unpack second (this is a genuine type-safety improvement — the current form would raise `TypeError` instead of failing an assertion if the rule ever returned `None`):
  ```python
  def test_never_activated_after_nudge_window() -> None:
      result = attention_for(**_base(activated=False, has_survey=False))
      assert result is not None
      kind, _reason = result
      assert kind == "never_activated"


  def test_not_assessed() -> None:
      result = attention_for(
          **_base(has_survey=False, latest_completion=None, assigned_total=0, completed_total=0)
      )
      assert result is not None
      kind, reason = result
      assert kind == "not_assessed"
      assert "assessment not started" in reason


  def test_stalled_with_track_name() -> None:
      result = attention_for(**_base(latest_completion=NOW - timedelta(days=16)))
      assert result is not None
      kind, reason = result
      assert kind == "stalled"
      assert "Copilot" in reason and "16 days" in reason
  ```
  Then verify all three gates:
  ```
  cd backend && uv run ruff check . --output-format=concise
  cd backend && uv run ruff format --check .
  cd backend && uvx ty check .
  cd backend && uv run poe format && uv run poe lint && uv run poe test
  ```
  Expected: `All checks passed!` · `276 files already formatted` (or similar, with 0 to reformat) · `All checks passed!` / `Found 0 diagnostics` · full suite green.

  **Existing tests likely to break:** `test_attention.py` is edited here by design. The Literal narrowings in (d) and (e) are compile-time only, but they are exactly the kind of change that reveals a real mismatch — if `tests/integration/test_routers/test_admin_email_templates.py` or `test_invite_lifecycle.py` goes red, a caller was genuinely passing a non-literal string and that is a finding, not a nuisance. `poe ty` is not part of `poe test`, so add the `uvx ty check .` run to your own loop.

- [ ] **Step 5: Commit**
  ```
  git add backend/pyproject.toml backend/src/services/interview_service.py backend/src/services/content_improvement_service.py backend/src/core/dependencies/email.py backend/src/services/token_service.py backend/src/routers/auth.py backend/src/services/email_template_service.py backend/src/core/dependencies/settings.py backend/alembic/env.py backend/tests/unit/test_attention.py
  git commit -m "Make ruff and ty clean repo-wide

Review item 9.10. Baseline was 48 ruff violations, 1 unformatted file and 24 ty
diagnostics.

Real fixes in src: _record_failure takes BaseException (what gather hands back);
a narrow ty:ignore for the ACS SDK's split EmailClient class; a new
ActionTokenPurpose literal so the invite-info cast matches the schema instead of
including entra_login; ResolvedTemplate.purpose typed EmailPurpose; two stale
ty:ignore comments removed. tests/unit/test_attention.py now asserts non-None
before unpacking, which is a real safety improvement.

scripts/ is excluded from both tools with the rationale written into
pyproject.toml: one-shot artifacts, not imported by src or tests, never shipped,
and review item 5.2 wants the folder relocated anyway — churning 48 findings
there would buy nothing."
  ```

---

## Task 9 [SKIP IF TASK 1 CHOSE OPTION (b)]: Extract the pure briefing renderers and input gatherer

First half of the **9.2** implementation. Pure, additive: nothing is rewired yet, so this task cannot break a running path.

**Depends on:** Task 3 (`module_level_map`).

**Files:**
- Create `backend/src/services/interview_briefing.py`
- Create `backend/tests/unit/test_interview_briefing.py`

**Interfaces:**
- *Consumes:* `advance_level`, `module_level_map` (`src/core/constants.py`); `AbstractSurveyRepository.get_by_user_id`, `AbstractContentRepository.list_tracks`/`list_modules`, `AbstractAssignmentRepository.assigned_lesson_counts_by_module`.
- *Produces:*
  ```python
  class BriefingInputs(NamedTuple):
      first_name: str
      last_name: str
      survey: SurveyResponse | None
      level: str | None
      learning: str  # "not_started" | "in_progress" | "complete"

  async def gather_briefing_inputs(
      user: User, *, surveys: AbstractSurveyRepository,
      content: AbstractContentRepository, assignments: AbstractAssignmentRepository,
  ) -> BriefingInputs: ...

  def render_briefing(inputs: BriefingInputs) -> str: ...
  def render_assessment_context(inputs: BriefingInputs) -> str: ...
  ```
  Task 10 depends on exactly these four names.

- [ ] **Step 1: Write the failing test**

  Create `backend/tests/unit/test_interview_briefing.py` by **copying** `tests/unit/test_interview_context.py` and changing only how the subject is built — the rendered strings must not change, which is the whole safety argument for this task:
  ```python
  """Pure briefing renderers + the repository-backed input gatherer (review 9.2).

  Ported from test_interview_context.py: the assertion bodies are deliberately
  unchanged, because the rendered text must be byte-identical to what
  InterviewContextService produced. What changed is the subject — plain functions
  over a NamedTuple instead of a service composing three services.
  """

  from __future__ import annotations

  import uuid
  from types import SimpleNamespace
  from unittest.mock import AsyncMock

  from src.repositories.base import (
      AbstractAssignmentRepository,
      AbstractContentRepository,
      AbstractSurveyRepository,
  )
  from src.services.interview_briefing import (
      BriefingInputs,
      gather_briefing_inputs,
      render_assessment_context,
      render_briefing,
  )

  # _survey() and _user() are copied verbatim from test_interview_context.py.

  TRACK_ID, MODULE_ID = uuid.uuid4(), uuid.uuid4()


  def _inputs(**overrides: object) -> BriefingInputs:
      fields: dict[str, object] = {
          "first_name": "Aaron",
          "last_name": "Neuville",
          "survey": _survey(),
          "level": "practitioner",
          "learning": "in_progress",
      }
      fields.update(overrides)
      return BriefingInputs(**fields)  # ty: ignore[invalid-argument-type]


  class TestRenderers:
      def test_briefing_renders_human_labels(self) -> None:
          briefing = render_briefing(_inputs())
          assert "Most weeks" in briefing
          assert "ChatGPT, Microsoft Copilot" in briefing
          assert "Aaron Neuville" in briefing

      def test_briefing_without_a_survey_says_so(self) -> None:
          briefing = render_briefing(_inputs(survey=None))
          assert "No completed assessment on file" in briefing
          assert "Aaron Neuville" in briefing

      def test_assessment_context_carries_every_competency(self) -> None:
          context = render_assessment_context(_inputs())
          for label in ("C1", "C2", "C3", "C4", "C5", "C6"):
              assert f"({label})" in context

      def test_renderers_are_pure(self) -> None:
          """No I/O, no awaits — that is the point of the refactor."""
          inputs = _inputs()
          assert render_briefing(inputs) == render_briefing(inputs)


  class TestGatherBriefingInputs:
      async def test_reads_the_counts_once_and_derives_both_level_and_status(self) -> None:
          """The duplicate read is the measurable win: MaturityService.effective_level
          and LearningService.learning_status each called
          assigned_lesson_counts_by_module, so one interview chat turn ran it twice."""
          surveys = AsyncMock(spec=AbstractSurveyRepository)
          content = AsyncMock(spec=AbstractContentRepository)
          assignments = AsyncMock(spec=AbstractAssignmentRepository)
          surveys.get_by_user_id.return_value = _survey(status="complete", score_level="explore")
          content.list_tracks.return_value = [
              SimpleNamespace(id=TRACK_ID, required_level="explore")
          ]
          content.list_modules.return_value = [SimpleNamespace(id=MODULE_ID, track_id=TRACK_ID)]
          assignments.assigned_lesson_counts_by_module.return_value = {MODULE_ID: (4, 2)}
          user = SimpleNamespace(
              id=uuid.uuid4(), first_name="Aaron", last_name="Neuville", maturity_override=None
          )

          inputs = await gather_briefing_inputs(
              user,  # ty: ignore[invalid-argument-type]
              surveys=surveys,
              content=content,
              assignments=assignments,
          )

          assert assignments.assigned_lesson_counts_by_module.await_count == 1
          assert inputs.level == "explore"  # 2 of 4 done -> no promotion
          assert inputs.learning == "in_progress"
          assert inputs.first_name == "Aaron"

      async def test_an_override_beats_the_scored_level(self) -> None:
          surveys = AsyncMock(spec=AbstractSurveyRepository)
          content = AsyncMock(spec=AbstractContentRepository)
          assignments = AsyncMock(spec=AbstractAssignmentRepository)
          surveys.get_by_user_id.return_value = _survey(status="complete", score_level="explore")
          content.list_tracks.return_value = []
          content.list_modules.return_value = []
          assignments.assigned_lesson_counts_by_module.return_value = {}
          user = SimpleNamespace(
              id=uuid.uuid4(),
              first_name="Aaron",
              last_name="Neuville",
              maturity_override="integrator",
          )

          inputs = await gather_briefing_inputs(
              user,  # ty: ignore[invalid-argument-type]
              surveys=surveys,
              content=content,
              assignments=assignments,
          )

          assert inputs.level == "integrator"

      async def test_an_incomplete_survey_yields_no_level(self) -> None:
          """Parity with SurveyRepository.get_complete_levels, which filters
          status == 'complete' AND score_level IS NOT NULL."""
          surveys = AsyncMock(spec=AbstractSurveyRepository)
          content = AsyncMock(spec=AbstractContentRepository)
          assignments = AsyncMock(spec=AbstractAssignmentRepository)
          surveys.get_by_user_id.return_value = _survey(status="in_progress", score_level=None)
          content.list_tracks.return_value = []
          content.list_modules.return_value = []
          assignments.assigned_lesson_counts_by_module.return_value = {}
          user = SimpleNamespace(
              id=uuid.uuid4(), first_name="Aaron", last_name="Neuville", maturity_override=None
          )

          inputs = await gather_briefing_inputs(
              user,  # ty: ignore[invalid-argument-type]
              surveys=surveys,
              content=content,
              assignments=assignments,
          )

          assert inputs.level is None
          assert inputs.learning == "not_started"
  ```
  Note `_survey()` in the source file has no `status` field; add `"status": "complete"` to its defaults dict when copying, since `gather_briefing_inputs` reads it.

- [ ] **Step 2: Run test to verify it fails**
  ```
  cd backend && uv run pytest tests/unit/test_interview_briefing.py -v
  ```
  Expected failure: collection error — `ModuleNotFoundError: No module named 'src.services.interview_briefing'`.

- [ ] **Step 3: Write minimal implementation**

  Create `backend/src/services/interview_briefing.py`. Move `FREQ`, `TOOLS`, `BARRIERS`, `SETUP`, `COMPETENCY_C1`…`COMPETENCY_C6`, `_labels` and `_label` **verbatim** from `interview_context.py` (they are already pure, ~140 lines — do not retype them, and keep the "source of truth: frontend/src/lib/surveyOptions.ts" comment), then:
  ```python
  from __future__ import annotations

  from typing import TYPE_CHECKING, NamedTuple

  from src.core.constants import advance_level, module_level_map

  if TYPE_CHECKING:
      from src.db.models import SurveyResponse, User
      from src.repositories.base import (
          AbstractAssignmentRepository,
          AbstractContentRepository,
          AbstractSurveyRepository,
      )

  __all__ = [
      "BriefingInputs",
      "gather_briefing_inputs",
      "render_assessment_context",
      "render_briefing",
  ]


  class BriefingInputs(NamedTuple):
      """Everything the two renderers need, already fetched.

      Exists so the renderers are pure: `render_briefing`/`render_assessment_context`
      are string builders over this tuple and are testable with plain data, which is
      what lets the interview slice honour "services never call other services"
      (python-be-architecture.md) without a composer.
      """

      first_name: str
      last_name: str
      survey: SurveyResponse | None
      level: str | None
      learning: str


  async def gather_briefing_inputs(
      user: User,
      *,
      surveys: AbstractSurveyRepository,
      content: AbstractContentRepository,
      assignments: AbstractAssignmentRepository,
  ) -> BriefingInputs:
      """Fetch one caller's briefing inputs in four queries.

      A module-level async function taking repository ABCs, not a service: both
      `InterviewService` and `BriefingService` need this exact fetch, and a shared
      free function is how they get it without one importing the other. Strictly
      token-scoped — everything derives from the `User` passed in, never a
      request-supplied user id.

      Was six queries when this lived in `InterviewContextService`:
      `SurveyService.get_own` (1) + `MaturityService.effective_level`
      (get_complete_levels + list_tracks + list_modules + counts = 4) +
      `LearningService.learning_status` (counts AGAIN = 1). Two are gone: one counts
      read serves both the maturity ladder and the learning status, and the survey
      row already carries what `get_complete_levels` would return — that repository
      method filters `status == "complete" AND score_level IS NOT NULL`
      (repositories/survey_repository.py), which is exactly the condition below.
      """
      survey = await surveys.get_by_user_id(user.id)
      counts = await assignments.assigned_lesson_counts_by_module(user.id)
      scored = (
          survey.score_level
          if survey is not None and survey.status == "complete" and survey.score_level is not None
          else None
      )
      base = user.maturity_override or scored
      level: str | None = None
      if base is not None:
          tracks = await content.list_tracks()
          modules = await content.list_modules()
          level = advance_level(base, module_level_map(tracks, modules), counts)
      return BriefingInputs(
          first_name=user.first_name,
          last_name=user.last_name,
          survey=survey,
          level=level,
          learning=_learning_status(counts),
      )


  def _learning_status(counts: dict[uuid.UUID, tuple[int, int]]) -> str:
      """Same rule as `LearningService.learning_status`, over counts already read:
      not_started until the first assigned lesson is done, complete once every
      assigned lesson is done, in_progress between."""
      total = sum(count for count, _ in counts.values())
      done = sum(completed for _, completed in counts.values())
      if total == 0 or done == 0:
          return "not_started"
      if done >= total:
          return "complete"
      return "in_progress"
  ```
  Then move the two render bodies across, converting `self`/`survey`/`level`/`learning`/`name` reads to the tuple's fields and keeping every f-string byte-identical:
  ```python
  def render_briefing(inputs: BriefingInputs) -> str:
      """The 'What you already know' block appended to the interview system prompt."""
      survey = inputs.survey
      name = f"{inputs.first_name} {inputs.last_name}"
      header = (
          "## What you already know about the person (from their assessment — a "
          "briefing, not the truth; never make them repeat it)"
      )
      ...


  def render_assessment_context(inputs: BriefingInputs) -> str:
      """A fuller structured dump of the assessment for the wrap-up generation
      prompt (destined for an `<assessment_record>` block)."""
      ...
  ```
  `uuid` needs a runtime import for `_learning_status`'s annotation only — put it under `TYPE_CHECKING` and keep `from __future__ import annotations` doing the work, or import it plainly; either is fine here because no FastAPI-inspected signature is involved.

  **`interview_context.py` is not touched or deleted in this task** — Task 10 owns that, so this task is additive and independently shippable. `_learning_status` deliberately duplicates six lines of `LearningService.learning_status` rather than importing it (that would be a service dependency); if that bothers a reviewer, the follow-up is to hoist the rule into `core/constants.py` alongside `advance_level` and have both call it.

- [ ] **Step 4: Run test to verify it passes**
  ```
  cd backend && uv run pytest tests/unit/test_interview_briefing.py -v
  cd backend && uv run poe format && uv run poe lint && uv run poe test
  ```
  Then prove the text really is unchanged — build the same inputs through both paths and compare:
  ```
  cd backend && uv run pytest tests/unit/test_interview_briefing.py tests/unit/test_interview_context.py -v
  ```
  Both suites must be green simultaneously; that is the parity evidence for Task 10.

  **Existing tests likely to break:** none — this task adds files only.

- [ ] **Step 5: Commit**
  ```
  git add backend/src/services/interview_briefing.py backend/tests/unit/test_interview_briefing.py
  git commit -m "Add pure interview-briefing renderers and a shared input gatherer

First half of review item 9.2 (option (a)). The label maps and both render
methods move out of InterviewContextService unchanged, and the fetch becomes a
module-level async function taking repository ABCs — the shape that lets both
consumers share it without one service importing another.

Four queries instead of six: one assigned-lesson-counts read now serves both the
maturity ladder and the learning status, and the survey row already carries what
get_complete_levels would return (same status/score_level filter).

Additive: interview_context.py is untouched until the next commit, and both test
suites pass together as parity evidence."
  ```

---

## Task 10 [SKIP IF TASK 1 CHOSE OPTION (b)]: Rewire the interview slice and delete `InterviewContextService`

Second half of **9.2**. Largest blast radius in the plan; ships last.

**Depends on:** Task 9.

**Files:**
- Modify `backend/src/services/interview_service.py` (`__init__` at `:70-80`; `open_interview` at `:120`; `build_playbook` at `:152`; `TYPE_CHECKING` imports at `:21-27`)
- Create `backend/src/services/briefing_service.py`
- Modify `backend/src/core/dependencies/interview.py` (whole file)
- Modify `backend/src/routers/chat.py` (`:13,26,96,107`)
- Delete `backend/src/services/interview_context.py`
- Delete `backend/tests/unit/test_interview_context.py`
- Modify `backend/tests/unit/test_interview_service.py` (`_service()` at `:135-141`)

**Interfaces:**
- *Consumes:* Task 9's four names.
- *Produces:* `InterviewService(conversations, messages, llm, surveys, content, assignments)`; `BriefingService(surveys, content, assignments)` with `async def build_briefing(self, user: User) -> str`; `get_briefing_service` replacing `get_interview_context_service` in `core/dependencies/interview.py`. `get_interview_service` keeps returning `InterviewService | None`, so `routers/interview.py` and `routers/me.py` need **no** change.

- [ ] **Step 1: Record the baseline green (pure refactor — the rendered prompts and every response shape stay identical)**
  ```
  cd backend && uv run pytest tests/unit/test_interview_service.py tests/unit/test_interview_briefing.py tests/unit/test_interview_context.py tests/unit/test_interview_firewall.py tests/unit/test_chat_service.py -v
  cd backend && uv run pytest tests/integration/test_routers/test_chat.py tests/integration/test_routers/test_me.py -v
  ```
  All green before touching anything. `test_me.py` matters because `/api/me/journey` resolves `get_interview_service` for the journey pill (`routers/me.py:39,46-50`) — if the DI rewiring is wrong, that endpoint is where it shows.

- [ ] **Step 2: Confirm the failure mode you are protecting against**

  There is no new behaviour to red-test here; instead, prove the DI wiring is exercised before you change it, so a mistake cannot pass silently:
  ```
  cd backend && uv run pytest tests/integration/test_routers/test_me.py -v -k journey
  ```
  Record that it passes and hits the interview status. Then, after Step 3, the same command is the wiring check. If `core/dependencies/interview.py` ends up with a `TYPE_CHECKING`-only annotation on a provider parameter, this test fails with a 422 about a missing query parameter — that is the deferred-annotation gotcha in Global Constraints, and it is the single most likely way to break this task.

- [ ] **Step 3: Write the implementation**

  **(a) `src/services/interview_service.py`** — swap the context service for the three repositories:
  ```python
  from src.services.interview_briefing import (
      gather_briefing_inputs,
      render_assessment_context,
      render_briefing,
  )

  if TYPE_CHECKING:
      import uuid

      from src.db.models import Conversation, User
      from src.repositories.base import (
          AbstractAssignmentRepository,
          AbstractContentRepository,
          AbstractConversationRepository,
          AbstractMessageRepository,
          AbstractSurveyRepository,
      )
      from src.services.llm_service import LlmClient
  ```
  ```python
      def __init__(
          self,
          conversations: AbstractConversationRepository,
          messages: AbstractMessageRepository,
          llm: LlmClient,
          surveys: AbstractSurveyRepository,
          content: AbstractContentRepository,
          assignments: AbstractAssignmentRepository,
      ) -> None:
          self._conversations = conversations
          self._messages = messages
          self._llm = llm
          self._surveys = surveys
          self._content = content
          self._assignments = assignments

      async def _briefing_inputs(self, user: User) -> BriefingInputs:
          """Repositories, not another service: this slice used to take
          SurveyService/MaturityService/LearningService, which broke the one
          non-negotiable rule (see python-be-architecture.md and review 9.2)."""
          return await gather_briefing_inputs(
              user,
              surveys=self._surveys,
              content=self._content,
              assignments=self._assignments,
          )
  ```
  In `open_interview`, replace `await self._context.build_briefing(user)`:
  ```python
          system = f"{load_prompt(_KIND)}\n\n{render_briefing(await self._briefing_inputs(user))}"
  ```
  In `build_playbook`, replace `await self._context.build_assessment_context(user)`:
  ```python
          assessment = render_assessment_context(await self._briefing_inputs(user))
  ```
  Add `BriefingInputs` to the `TYPE_CHECKING` imports for `_briefing_inputs`'s return annotation.

  **(b) Create `src/services/briefing_service.py`** for the chat path:
  ```python
  """The interview briefing as a service, for the one consumer that needs it
  without needing the rest of InterviewService: `routers/chat.py` appends it to the
  system prompt on every `interview`-kind turn.

  Repositories only — no service dependency (python-be-architecture.md; review
  item 9.2). The fetch and the rendering both live in `interview_briefing.py`, so
  this class is deliberately thin and shares one implementation with
  InterviewService rather than duplicating it.
  """

  from __future__ import annotations

  from typing import TYPE_CHECKING

  from src.services.interview_briefing import gather_briefing_inputs, render_briefing

  if TYPE_CHECKING:
      from src.db.models import User
      from src.repositories.base import (
          AbstractAssignmentRepository,
          AbstractContentRepository,
          AbstractSurveyRepository,
      )

  __all__ = ["BriefingService"]


  class BriefingService:
      def __init__(
          self,
          surveys: AbstractSurveyRepository,
          content: AbstractContentRepository,
          assignments: AbstractAssignmentRepository,
      ) -> None:
          self._surveys = surveys
          self._content = content
          self._assignments = assignments

      async def build_briefing(self, user: User) -> str:
          """Strictly token-scoped: everything derives from the `User` passed in,
          never a request-supplied user id."""
          return render_briefing(
              await gather_briefing_inputs(
                  user,
                  surveys=self._surveys,
                  content=self._content,
                  assignments=self._assignments,
              )
          )
  ```

  **(c) `src/core/dependencies/interview.py`** — keep the module docstring's deferred-annotation warning, replace the two providers. Every parameter annotation below is a **runtime** import:
  ```python
  from src.core.dependencies.auth import get_current_user
  from src.core.dependencies.chat import get_conversation_repository, get_message_repository
  from src.core.dependencies.domain import (
      get_assignment_repository,
      get_content_repository,
      get_org_service,
      get_survey_repository,
  )
  from src.core.dependencies.llm import get_llm_service
  from src.db.models import User
  from src.repositories.assignment_repository import AssignmentRepository
  from src.repositories.content_repository import ContentRepository
  from src.repositories.conversation_repository import ConversationRepository
  from src.repositories.message_repository import MessageRepository
  from src.repositories.survey_repository import SurveyRepository
  from src.services.briefing_service import BriefingService
  from src.services.interview_service import InterviewService
  from src.services.llm_service import AnthropicLlmClient
  from src.services.org_service import OrgService

  __all__ = [
      "get_briefing_service",
      "get_interview_service",
      "require_interview_surface",
  ]


  def get_briefing_service(
      surveys: Annotated[SurveyRepository, Depends(get_survey_repository)],
      content: Annotated[ContentRepository, Depends(get_content_repository)],
      assignments: Annotated[AssignmentRepository, Depends(get_assignment_repository)],
  ) -> BriefingService:
      return BriefingService(surveys, content, assignments)


  def get_interview_service(
      conversations: Annotated[ConversationRepository, Depends(get_conversation_repository)],
      messages: Annotated[MessageRepository, Depends(get_message_repository)],
      llm: Annotated[AnthropicLlmClient | None, Depends(get_llm_service)],
      surveys: Annotated[SurveyRepository, Depends(get_survey_repository)],
      content: Annotated[ContentRepository, Depends(get_content_repository)],
      assignments: Annotated[AssignmentRepository, Depends(get_assignment_repository)],
  ) -> InterviewService | None:
      """None when LLM__* is unconfigured — the router 404s (mirrors get_chat_service)."""
      if llm is None:
          return None
      return InterviewService(conversations, messages, llm, surveys, content, assignments)
  ```
  Drop the now-unused `get_maturity_service`/`get_survey_service`/`get_learning_service` imports and the `MaturityService`/`SurveyService`/`LearningService`/`InterviewContextService` imports. `require_interview_surface` is unchanged (Task 5 already touched its body).

  **(d) `src/routers/chat.py`** — four edits, all renames:
  ```python
  from src.core.dependencies.interview import get_briefing_service
  ...
  from src.services.briefing_service import BriefingService
  ```
  ```python
      briefing: Annotated[BriefingService, Depends(get_briefing_service)],
  ...
      system_suffix = await briefing.build_briefing(user) if kind == "interview" else None
  ```
  `BriefingService` must be imported at **runtime** — it appears in a `Depends` provider's parameter annotation.

  **(e) Delete** `src/services/interview_context.py` and `tests/unit/test_interview_context.py`. Confirm nothing references either first:
  ```
  cd backend && grep -rn "interview_context\|InterviewContextService" src tests
  ```
  Expect no hits before committing.

  **(f) `tests/unit/test_interview_service.py`** — update the `_service()` helper:
  ```python
  def _service(llm: object) -> tuple[InterviewService, AsyncMock, AsyncMock, AsyncMock]:
      conversations = AsyncMock(spec=AbstractConversationRepository)
      messages = AsyncMock(spec=AbstractMessageRepository)
      surveys = AsyncMock(spec=AbstractSurveyRepository)
      content = AsyncMock(spec=AbstractContentRepository)
      assignments = AsyncMock(spec=AbstractAssignmentRepository)
      # No survey on file and nothing assigned: the briefing renders its
      # "no completed assessment" branch, which is all these tests need — the
      # briefing's own content is covered in test_interview_briefing.py.
      surveys.get_by_user_id.return_value = None
      content.list_tracks.return_value = []
      content.list_modules.return_value = []
      assignments.assigned_lesson_counts_by_module.return_value = {}
      service = InterviewService(  # ty: ignore[invalid-argument-type]
          conversations, messages, llm, surveys, content, assignments
      )
      return service, conversations, messages, surveys
  ```
  The helper's fourth return value was the context mock; several tests use it as `context` and set `context.build_briefing.return_value = "BRIEFING"`. Those tests must change: `test_open_interview_fresh_generates_persists_and_returns_greeting` asserts `"BRIEFING" in call["system"]` — replace that with an assertion against the real rendered text, e.g. `assert "No completed assessment on file" in call["system"]`, and delete the `context.build_briefing.return_value = ...` lines. Same for `test_open_interview_llm_failure_creates_no_conversation` and any test in the resilience plan's Tasks 7–8 that sets `context.build_briefing`.

- [ ] **Step 4: Run the baseline suites again and confirm green**
  ```
  cd backend && uv run pytest tests/unit/test_interview_service.py tests/unit/test_interview_briefing.py tests/unit/test_interview_firewall.py -v
  cd backend && uv run pytest tests/integration/test_routers/test_chat.py tests/integration/test_routers/test_me.py -v
  cd backend && uv run poe format && uv run poe lint && uv run poe test
  cd backend && uvx ty check .
  ```
  Then confirm the rule now holds by inspection — this should print nothing:
  ```
  cd backend && grep -rn "Service," src/services/*.py | grep "def __init__" -A6 | grep -E "surveys: SurveyService|maturity: MaturityService|learning: LearningService"
  ```

  **Existing tests likely to break — all of them expected, all of them edited by this task:**
  - `tests/unit/test_interview_service.py` — the `_service()` helper and the three tests that stub `context.build_briefing`.
  - `tests/unit/test_interview_context.py` — deleted (its coverage moved to `test_interview_briefing.py` in Task 9; do not delete it before that file is green).
  - `tests/integration/test_routers/test_chat.py` — only if it constructs `InterviewContextService` directly; grep first.
  - `tests/integration/test_routers/test_me.py` — must **not** break. If `/api/me/journey` starts 422ing, a provider annotation went under `TYPE_CHECKING`.
  - If the resilience plan already landed, its interview tests reference `context` via the same helper — reconcile both in this commit.

- [ ] **Step 5: Commit**
  ```
  git add backend/src/services/interview_service.py backend/src/services/briefing_service.py backend/src/core/dependencies/interview.py backend/src/routers/chat.py backend/tests/unit/test_interview_service.py
  git rm backend/src/services/interview_context.py backend/tests/unit/test_interview_context.py
  git commit -m "Delete InterviewContextService; wire the interview slice to repositories

Second half of review item 9.2 (option (a)). InterviewContextService took three
concrete services and InterviewService took it — two levels of service-to-service
composition, in a codebase that refuses this everywhere else in writing
(admin_user_service.py, content_improvement_service.py, core/attention.py,
core/constants.py:advance_level).

InterviewService now takes the three repositories and calls the pure renderers;
routers/chat.py gets a thin repository-backed BriefingService. Both share
interview_briefing.gather_briefing_inputs, so honouring the rule costs no
duplicated fetch. Rendered prompt text and every response shape are unchanged;
get_interview_service still returns InterviewService | None, so
routers/interview.py and routers/me.py are untouched."
  ```

---

## Decision notes (no tasks)

### 9.3 — Email dispatch in `routers/admin_users.py`

**Status quo (verified):** `_email_the_link` (`routers/admin_users.py:89-117`) plus the inline reminder rendering (`:325-334`) put ~60 lines of use-case logic at the HTTP edge — template resolution, the `EmailStatus` derivation (`"sent"`/`"failed"`/`"disabled"`/`"skipped"`), and the "a failed send never fails the endpoint" fallback — called from three endpoints (`:161`, `:227`, `:290`). It is there *because* of the no-service→service rule: `AdminUserService` cannot call `EmailService` or `EmailTemplateService`. Prior audit 4.2 flagged it; it is now well-commented but still unwritten in the spec.

**Option 1 — document the seam (recommended).** Add a short subsection to `python-be-architecture.md` naming the router as the sanctioned orchestration point when a use case needs two independent services, with `routers/admin_users.py::_email_the_link` as the reference example and the constraint that such a router helper must contain no data access and no branching on domain state beyond the services' own return values. **Effort: S.** This is honest about what the codebase does and gives the next agent a rule instead of a precedent to guess at.

**Option 2 — introduce a `NotificationService`.** A service composed at the DI layer from `EmailService | None` + `EmailTemplateService`… which is itself a service→service dependency, so it only becomes legal under Task 1's option (b). If Task 1 chose **(a)**, Option 2 is unavailable without repeating 9.2's mistake — the alternative would be a `NotificationService` taking the *repositories* (`EmailTemplateRepository`, `OrgRepository`) plus the ACS sender, duplicating `EmailTemplateService.render`'s resolution logic. **Effort: M**, and it trades a documented seam for real duplication.

**Recommendation:** Option 1, and it should be folded into Task 1's spec edit rather than done separately — both are one paragraph in the same document, and Task 1's outcome determines whether Option 2 is even permissible.

### 9.8 — Two bare-array list responses

**Status quo (verified):** `routers/admin_content.py:36` (`GET /api/tracks`, `response_model=list[TrackOut]`) and `:43-46` (`GET /api/tracks/{track_id}/modules`, `response_model=list[TrackModuleOut]`) return bare JSON arrays; every other list endpoint returns a wrapped object (`{items, total, limit, offset}` for feedback/proposals, `{users, total}`, `{templates}`, `{prompts}`, `{conversations}`).

**Recommendation: leave them as they are, and record why.** This is a **wire-contract change**, not a refactor. Changing it means, in one coordinated commit: the two routers, `frontend/src/api/schema.d.ts` (regenerated via `gen:api`), and three frontend call sites — `frontend/src/components/AddModuleModal.tsx:41` (`client.GET('/api/tracks')`), `AddModuleModal.tsx:57` (`client.GET('/api/tracks/{track_id}/modules')`) and `frontend/src/pages/admin2/api.ts:140` (`client.GET('/api/tracks')`). Against that: zero user-visible benefit, zero pagination need (tracks and a track's modules are both small, bounded, admin-authored sets), and a deploy window where a stale SPA talks to a new API and silently renders nothing — the frontend uses `openapi-fetch`, so the shape mismatch is a type error at build time but a `data.map is not a function` at runtime for anyone holding a cached bundle.

Bare arrays for a small fixed collection with no pagination story is a defensible convention; the wrapped envelope exists where `total`/`limit`/`offset` are needed. The right fix is one sentence in `python-be-architecture.md`: *"List endpoints return a wrapped object whenever the response carries pagination or aggregate metadata; a bare array is acceptable for a small, bounded, unpaginated collection (`GET /api/tracks`)."* Fold it into Task 1's spec edit.

**If Matthias wants it changed anyway**, it must be scoped as a single coordinated task covering exactly those five files plus a `gen:api` regeneration, sequenced so the frontend deploys with the backend (they ship in one container image, so that is automatic here) — and it should then take `{tracks: [...]}` / `{modules: [...]}` to match the `{templates}`/`{prompts}` precedent rather than inventing a third shape.
