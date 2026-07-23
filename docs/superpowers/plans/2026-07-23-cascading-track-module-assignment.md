# Cascading Track/Module Assignment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Assigning a track or module to a user in the admin panel automatically assigns every module and lesson underneath it (and unassigning removes them too), instead of requiring the admin to separately toggle every level by hand.

**Architecture:** Add cascade logic to `AdminUserService` in `backend/src/services/admin_user_service.py` — the layer that already has access to both the content repository (to list a track's modules / a module's lessons) and the assignment repository (to write `user_modules`/`user_lessons` rows). No new tables, no new endpoints, no repository interface changes. The frontend (`Admin.tsx`) switches its track/module toggle handlers from a single-field optimistic patch to a refetch of `GET /api/admin/learning`, since a track/module toggle can now change more than one assignment array at once.

**Tech Stack:** FastAPI + SQLAlchemy (async) backend, pytest + httpx integration tests against the `ai-enablement-hub-test` Postgres DB; React 18 + TypeScript frontend (openapi-fetch client).

## Global Constraints

- Cascade is **full resync, both ways**: assigning a track/module sets *all* descendants to `assigned=true` every time (even ones previously hand-unassigned); unassigning a track/module sets *all* descendants to `assigned=false`. (Design spec, "Decisions".)
- Lesson-level assignment (`set_lesson_assignment`/`set_lesson_assignments`) is unchanged — lessons have no children.
- The existing bulk atomicity invariant must keep holding: an unknown id anywhere in a bulk request → 404, nothing written. Validation happens before any write, unchanged.
- No new repository methods, no schema/migration changes, no changes to `GET /api/admin/learning`'s response shape.
- Backend checks (run inside `backend/`): `uv run poe format && uv run poe lint && uv run poe test`.
- Frontend checks (run inside `frontend/`): `npm run typecheck && npm run lint && npm run build`.
- Spec: `docs/superpowers/specs/2026-07-23-cascading-track-module-assignment-design.md`.

---

### Task 1: Cascade helper + single track assignment (`set_track_assignment`)

**Files:**
- Modify: `backend/src/services/admin_user_service.py:167-174` (method `set_track_assignment`); add a new private helper method to the class.
- Test: `backend/tests/integration/test_routers/test_admin_users.py` (add to `class TestAssignments`, which starts at line 301).

**Interfaces:**
- Consumes (already exist, no changes): `ContentRepository.list_modules() -> list[Module]` (no arg = all modules; `Module.id`, `Module.track_id`), `ContentRepository.list_lesson_summaries() -> list[Lesson]` (all lessons; `Lesson.id`, `Lesson.module_id`), `AssignmentRepository.set_user_modules(user_id, module_ids, assigned) -> None`, `AssignmentRepository.set_user_lessons(user_id, lesson_ids, assigned) -> None`.
- Produces: `AdminUserService._cascade_module_and_lesson_ids(self, track_ids: list[uuid.UUID]) -> tuple[list[uuid.UUID], list[uuid.UUID]]` — returns `(module_ids, lesson_ids)` for every module/lesson under the given tracks. Used again by Task 2.

- [ ] **Step 1: Write the failing tests**

Add these three tests inside `class TestAssignments` in
`backend/tests/integration/test_routers/test_admin_users.py` (e.g. right after
`test_assign_and_unassign_track`, which ends at line 324):

```python
    async def test_assign_track_cascades_to_modules_and_lessons(
        self, client: AsyncClient, db_session: AsyncSession, org: Org
    ) -> None:
        user = await create_user(db_session, email="cascade-track@example.com")
        track = await create_track(db_session, "Cascade Track")
        module = await create_module(db_session, track, "Cascade Module")
        lesson = await create_lesson(db_session, module, "Cascade Lesson")

        response = await client.put(
            f"/api/admin/users/{user.id}/tracks/{track.id}",
            json={"assigned": True},
            headers=org.headers,
        )
        assert response.status_code == 204

        overview = (await client.get("/api/admin/learning", headers=org.headers)).json()
        entry = next(u for u in overview["users"] if u["id"] == str(user.id))
        assert entry["assigned_track_ids"] == [str(track.id)]
        assert entry["assigned_module_ids"] == [str(module.id)]
        assert entry["assigned_lesson_ids"] == [str(lesson.id)]

    async def test_unassign_track_cascades_to_modules_and_lessons(
        self, client: AsyncClient, db_session: AsyncSession, org: Org
    ) -> None:
        user = await create_user(db_session, email="cascade-track-off@example.com")
        track = await create_track(db_session, "Cascade Off Track")
        module = await create_module(db_session, track, "Cascade Off Module")
        await create_lesson(db_session, module, "Cascade Off Lesson")
        url = f"/api/admin/users/{user.id}/tracks/{track.id}"
        assert (
            await client.put(url, json={"assigned": True}, headers=org.headers)
        ).status_code == 204

        response = await client.put(url, json={"assigned": False}, headers=org.headers)
        assert response.status_code == 204

        overview = (await client.get("/api/admin/learning", headers=org.headers)).json()
        entry = next(u for u in overview["users"] if u["id"] == str(user.id))
        assert entry["assigned_track_ids"] == []
        assert entry["assigned_module_ids"] == []
        assert entry["assigned_lesson_ids"] == []

    async def test_assign_track_with_no_modules_does_not_error(
        self, client: AsyncClient, db_session: AsyncSession, org: Org
    ) -> None:
        user = await create_user(db_session, email="cascade-empty-track@example.com")
        track = await create_track(db_session, "Empty Cascade Track")

        response = await client.put(
            f"/api/admin/users/{user.id}/tracks/{track.id}",
            json={"assigned": True},
            headers=org.headers,
        )
        assert response.status_code == 204
        overview = (await client.get("/api/admin/learning", headers=org.headers)).json()
        entry = next(u for u in overview["users"] if u["id"] == str(user.id))
        assert entry["assigned_track_ids"] == [str(track.id)]
        assert entry["assigned_module_ids"] == []
```

- [ ] **Step 2: Run the tests to verify they fail**

Run (inside `backend/`): `uv run pytest tests/integration/test_routers/test_admin_users.py -k cascade_track -v`
Expected: `test_assign_track_cascades_to_modules_and_lessons` and
`test_unassign_track_cascades_to_modules_and_lessons` FAIL on
`assert entry["assigned_module_ids"] == [...]` (actual is `[]`, since no cascade
exists yet); `test_assign_track_with_no_modules_does_not_error` PASSES already
(nothing to cascade) — that's fine, it's a regression guard for Step 3.

- [ ] **Step 3: Implement the cascade helper + wire it into `set_track_assignment`**

In `backend/src/services/admin_user_service.py`, replace the current
`set_track_assignment` method (lines 167-174):

```python
    async def set_track_assignment(
        self, user_id: uuid.UUID, track_id: uuid.UUID, assigned: bool
    ) -> None:
        if await self._users.get_by_id(user_id) is None:
            raise NotFoundError("User")
        if await self._content.get_track(track_id) is None:
            raise NotFoundError("Track")
        await self._assignments.set_user_track(user_id, track_id, assigned)
```

with:

```python
    async def set_track_assignment(
        self, user_id: uuid.UUID, track_id: uuid.UUID, assigned: bool
    ) -> None:
        if await self._users.get_by_id(user_id) is None:
            raise NotFoundError("User")
        if await self._content.get_track(track_id) is None:
            raise NotFoundError("Track")
        await self._assignments.set_user_track(user_id, track_id, assigned)
        await self._cascade_to_modules_and_lessons(user_id, [track_id], assigned)

    async def _cascade_module_and_lesson_ids(
        self, track_ids: list[uuid.UUID]
    ) -> tuple[list[uuid.UUID], list[uuid.UUID]]:
        """All module ids under the given tracks, and all lesson ids under those modules."""
        track_id_set = set(track_ids)
        modules = [m for m in await self._content.list_modules() if m.track_id in track_id_set]
        module_ids = [m.id for m in modules]
        module_id_set = set(module_ids)
        lessons = [
            le for le in await self._content.list_lesson_summaries() if le.module_id in module_id_set
        ]
        return module_ids, [le.id for le in lessons]

    async def _cascade_to_modules_and_lessons(
        self, user_id: uuid.UUID, track_ids: list[uuid.UUID], assigned: bool
    ) -> None:
        module_ids, lesson_ids = await self._cascade_module_and_lesson_ids(track_ids)
        if module_ids:
            await self._assignments.set_user_modules(user_id, module_ids, assigned)
        if lesson_ids:
            await self._assignments.set_user_lessons(user_id, lesson_ids, assigned)
```

Put both new methods directly below `set_track_assignment` (before
`set_module_assignment`).

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest tests/integration/test_routers/test_admin_users.py -k cascade_track -v`
Expected: all three PASS.

- [ ] **Step 5: Run the full assignment test class to check for regressions**

Run: `uv run pytest tests/integration/test_routers/test_admin_users.py::TestAssignments -v`
Expected: all PASS (existing tests use tracks/modules with no shared
module/lesson fixtures that this change would disturb).

- [ ] **Step 6: Commit**

```bash
git add backend/src/services/admin_user_service.py backend/tests/integration/test_routers/test_admin_users.py
git commit -m "Cascade single track assignment to its modules and lessons"
```

---

### Task 2: Bulk track assignment cascade (`set_track_assignments`)

**Files:**
- Modify: `backend/src/services/admin_user_service.py:194-203` (method `set_track_assignments`).
- Test: `backend/tests/integration/test_routers/test_admin_users.py::TestAssignments`.

**Interfaces:**
- Consumes: `AdminUserService._cascade_to_modules_and_lessons(user_id, track_ids, assigned)` from Task 1 (already handles unions correctly since it's given the full `unique_ids` list).
- Produces: nothing new — `set_track_assignments` now behaves like `set_track_assignment` for every id in the batch at once.

- [ ] **Step 1: Write the failing test**

Add to `class TestAssignments`:

```python
    async def test_bulk_assign_tracks_cascades_to_modules_and_lessons(
        self, client: AsyncClient, db_session: AsyncSession, org: Org
    ) -> None:
        user = await create_user(db_session, email="cascade-bulk-tracks@example.com")
        track_a = await create_track(db_session, "Cascade Bulk A", sort_order=0)
        track_b = await create_track(db_session, "Cascade Bulk B", sort_order=1)
        module_a = await create_module(db_session, track_a, "Cascade Bulk Module A")
        module_b = await create_module(db_session, track_b, "Cascade Bulk Module B")
        lesson_a = await create_lesson(db_session, module_a, "Cascade Bulk Lesson A")
        lesson_b = await create_lesson(db_session, module_b, "Cascade Bulk Lesson B")

        response = await client.put(
            f"/api/admin/users/{user.id}/tracks",
            json={"track_ids": [str(track_a.id), str(track_b.id)], "assigned": True},
            headers=org.headers,
        )
        assert response.status_code == 204

        overview = (await client.get("/api/admin/learning", headers=org.headers)).json()
        entry = next(u for u in overview["users"] if u["id"] == str(user.id))
        assert sorted(entry["assigned_module_ids"]) == sorted(
            [str(module_a.id), str(module_b.id)]
        )
        assert sorted(entry["assigned_lesson_ids"]) == sorted(
            [str(lesson_a.id), str(lesson_b.id)]
        )
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `uv run pytest tests/integration/test_routers/test_admin_users.py -k bulk_assign_tracks_cascades -v`
Expected: FAIL on the `assigned_module_ids`/`assigned_lesson_ids` assertions (both empty today).

- [ ] **Step 3: Wire the cascade into `set_track_assignments`**

Replace (lines 194-203):

```python
    async def set_track_assignments(
        self, user_id: uuid.UUID, track_ids: list[uuid.UUID], assigned: bool
    ) -> None:
        """Bulk assign/unassign ("Add/unassign all tracks"); 404 if ANY id is unknown."""
        if await self._users.get_by_id(user_id) is None:
            raise NotFoundError("User")
        unique_ids = list(set(track_ids))
        if await self._content.count_tracks_by_ids(unique_ids) != len(unique_ids):
            raise NotFoundError("Track")
        await self._assignments.set_user_tracks(user_id, unique_ids, assigned)
```

with:

```python
    async def set_track_assignments(
        self, user_id: uuid.UUID, track_ids: list[uuid.UUID], assigned: bool
    ) -> None:
        """Bulk assign/unassign ("Add/unassign all tracks"); 404 if ANY id is unknown."""
        if await self._users.get_by_id(user_id) is None:
            raise NotFoundError("User")
        unique_ids = list(set(track_ids))
        if await self._content.count_tracks_by_ids(unique_ids) != len(unique_ids):
            raise NotFoundError("Track")
        await self._assignments.set_user_tracks(user_id, unique_ids, assigned)
        await self._cascade_to_modules_and_lessons(user_id, unique_ids, assigned)
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `uv run pytest tests/integration/test_routers/test_admin_users.py -k bulk_assign_tracks_cascades -v`
Expected: PASS.

- [ ] **Step 5: Run the full assignment test class + existing bulk-track tests**

Run: `uv run pytest tests/integration/test_routers/test_admin_users.py::TestAssignments -v`
Expected: all PASS, including `test_bulk_assign_and_unassign_tracks` (unaffected —
its tracks have no modules).

- [ ] **Step 6: Commit**

```bash
git add backend/src/services/admin_user_service.py backend/tests/integration/test_routers/test_admin_users.py
git commit -m "Cascade bulk track assignment to modules and lessons"
```

---

### Task 3: Cascade helper + single module assignment (`set_module_assignment`)

**Files:**
- Modify: `backend/src/services/admin_user_service.py:176-183` (method `set_module_assignment`); add a new private helper.
- Test: `backend/tests/integration/test_routers/test_admin_users.py::TestAssignments`.

**Interfaces:**
- Consumes: `ContentRepository.list_lesson_summaries() -> list[Lesson]` (existing).
- Produces: `AdminUserService._cascade_lesson_ids(self, module_ids: list[uuid.UUID]) -> list[uuid.UUID]` — used again by Task 4.

- [ ] **Step 1: Write the failing tests**

Add to `class TestAssignments`:

```python
    async def test_assign_module_cascades_to_lessons(
        self, client: AsyncClient, db_session: AsyncSession, org: Org
    ) -> None:
        user = await create_user(db_session, email="cascade-module@example.com")
        track = await create_track(db_session, "Cascade Module Track")
        module = await create_module(db_session, track, "Cascade Module")
        lesson = await create_lesson(db_session, module, "Cascade Module Lesson")

        response = await client.put(
            f"/api/admin/users/{user.id}/modules/{module.id}",
            json={"assigned": True},
            headers=org.headers,
        )
        assert response.status_code == 204

        overview = (await client.get("/api/admin/learning", headers=org.headers)).json()
        entry = next(u for u in overview["users"] if u["id"] == str(user.id))
        assert entry["assigned_module_ids"] == [str(module.id)]
        assert entry["assigned_lesson_ids"] == [str(lesson.id)]

    async def test_unassign_module_cascades_to_lessons(
        self, client: AsyncClient, db_session: AsyncSession, org: Org
    ) -> None:
        user = await create_user(db_session, email="cascade-module-off@example.com")
        track = await create_track(db_session, "Cascade Module Off Track")
        module = await create_module(db_session, track, "Cascade Module Off")
        await create_lesson(db_session, module, "Cascade Module Off Lesson")
        url = f"/api/admin/users/{user.id}/modules/{module.id}"
        assert (
            await client.put(url, json={"assigned": True}, headers=org.headers)
        ).status_code == 204

        response = await client.put(url, json={"assigned": False}, headers=org.headers)
        assert response.status_code == 204

        overview = (await client.get("/api/admin/learning", headers=org.headers)).json()
        entry = next(u for u in overview["users"] if u["id"] == str(user.id))
        assert entry["assigned_module_ids"] == []
        assert entry["assigned_lesson_ids"] == []

    async def test_assign_module_with_no_lessons_does_not_error(
        self, client: AsyncClient, db_session: AsyncSession, org: Org
    ) -> None:
        user = await create_user(db_session, email="cascade-empty-module@example.com")
        track = await create_track(db_session, "Empty Cascade Module Track")
        module = await create_module(db_session, track, "Empty Cascade Module")

        response = await client.put(
            f"/api/admin/users/{user.id}/modules/{module.id}",
            json={"assigned": True},
            headers=org.headers,
        )
        assert response.status_code == 204
        overview = (await client.get("/api/admin/learning", headers=org.headers)).json()
        entry = next(u for u in overview["users"] if u["id"] == str(user.id))
        assert entry["assigned_module_ids"] == [str(module.id)]
        assert entry["assigned_lesson_ids"] == []
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/integration/test_routers/test_admin_users.py -k cascade_module -v`
Expected: `test_assign_module_cascades_to_lessons` and
`test_unassign_module_cascades_to_lessons` FAIL on the `assigned_lesson_ids`
assertion; `test_assign_module_with_no_lessons_does_not_error` PASSES already.

- [ ] **Step 3: Implement the lesson-cascade helper + wire it into `set_module_assignment`**

Replace (lines 176-183):

```python
    async def set_module_assignment(
        self, user_id: uuid.UUID, module_id: uuid.UUID, assigned: bool
    ) -> None:
        if await self._users.get_by_id(user_id) is None:
            raise NotFoundError("User")
        if await self._content.get_module(module_id) is None:
            raise NotFoundError("Module")
        await self._assignments.set_user_module(user_id, module_id, assigned)
```

with:

```python
    async def set_module_assignment(
        self, user_id: uuid.UUID, module_id: uuid.UUID, assigned: bool
    ) -> None:
        if await self._users.get_by_id(user_id) is None:
            raise NotFoundError("User")
        if await self._content.get_module(module_id) is None:
            raise NotFoundError("Module")
        await self._assignments.set_user_module(user_id, module_id, assigned)
        await self._cascade_to_lessons(user_id, [module_id], assigned)

    async def _cascade_lesson_ids(self, module_ids: list[uuid.UUID]) -> list[uuid.UUID]:
        """All lesson ids under the given modules."""
        module_id_set = set(module_ids)
        lessons = [
            le for le in await self._content.list_lesson_summaries() if le.module_id in module_id_set
        ]
        return [le.id for le in lessons]

    async def _cascade_to_lessons(
        self, user_id: uuid.UUID, module_ids: list[uuid.UUID], assigned: bool
    ) -> None:
        lesson_ids = await self._cascade_lesson_ids(module_ids)
        if lesson_ids:
            await self._assignments.set_user_lessons(user_id, lesson_ids, assigned)
```

Put both new methods directly below `set_module_assignment` (before
`set_lesson_assignment`). Also update `_cascade_module_and_lesson_ids` (from
Task 1) to reuse `_cascade_lesson_ids` instead of duplicating the lesson
filter — replace its body:

```python
    async def _cascade_module_and_lesson_ids(
        self, track_ids: list[uuid.UUID]
    ) -> tuple[list[uuid.UUID], list[uuid.UUID]]:
        """All module ids under the given tracks, and all lesson ids under those modules."""
        track_id_set = set(track_ids)
        modules = [m for m in await self._content.list_modules() if m.track_id in track_id_set]
        module_ids = [m.id for m in modules]
        return module_ids, await self._cascade_lesson_ids(module_ids)
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest tests/integration/test_routers/test_admin_users.py -k cascade_module -v`
Expected: all three PASS.

- [ ] **Step 5: Run the full assignment test class (and Task 1/2 tests) to check for regressions**

Run: `uv run pytest tests/integration/test_routers/test_admin_users.py::TestAssignments -v`
Expected: all PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/src/services/admin_user_service.py backend/tests/integration/test_routers/test_admin_users.py
git commit -m "Cascade single module assignment to its lessons"
```

---

### Task 4: Bulk module assignment cascade (`set_module_assignments`)

**Files:**
- Modify: `backend/src/services/admin_user_service.py:205-214` (method `set_module_assignments`).
- Test: `backend/tests/integration/test_routers/test_admin_users.py::TestAssignments`.

**Interfaces:**
- Consumes: `AdminUserService._cascade_to_lessons(user_id, module_ids, assigned)` from Task 3.

- [ ] **Step 1: Write the failing test**

Add to `class TestAssignments`:

```python
    async def test_bulk_assign_modules_cascades_to_lessons(
        self, client: AsyncClient, db_session: AsyncSession, org: Org
    ) -> None:
        user = await create_user(db_session, email="cascade-bulk-modules@example.com")
        track = await create_track(db_session, "Cascade Bulk Modules Track")
        module_a = await create_module(db_session, track, "Cascade Bulk Mod A", sort_order=0)
        module_b = await create_module(db_session, track, "Cascade Bulk Mod B", sort_order=1)
        lesson_a = await create_lesson(db_session, module_a, "Cascade Bulk Mod Lesson A")
        lesson_b = await create_lesson(db_session, module_b, "Cascade Bulk Mod Lesson B")

        response = await client.put(
            f"/api/admin/users/{user.id}/modules",
            json={"module_ids": [str(module_a.id), str(module_b.id)], "assigned": True},
            headers=org.headers,
        )
        assert response.status_code == 204

        overview = (await client.get("/api/admin/learning", headers=org.headers)).json()
        entry = next(u for u in overview["users"] if u["id"] == str(user.id))
        assert sorted(entry["assigned_lesson_ids"]) == sorted(
            [str(lesson_a.id), str(lesson_b.id)]
        )
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `uv run pytest tests/integration/test_routers/test_admin_users.py -k bulk_assign_modules_cascades -v`
Expected: FAIL — `assigned_lesson_ids` is empty today.

- [ ] **Step 3: Wire the cascade into `set_module_assignments`**

Replace (lines 205-214):

```python
    async def set_module_assignments(
        self, user_id: uuid.UUID, module_ids: list[uuid.UUID], assigned: bool
    ) -> None:
        """Bulk assign/unassign ("Add all modules"); 404 if ANY id is unknown."""
        if await self._users.get_by_id(user_id) is None:
            raise NotFoundError("User")
        unique_ids = list(set(module_ids))
        if await self._content.count_modules_by_ids(unique_ids) != len(unique_ids):
            raise NotFoundError("Module")
        await self._assignments.set_user_modules(user_id, unique_ids, assigned)
```

with:

```python
    async def set_module_assignments(
        self, user_id: uuid.UUID, module_ids: list[uuid.UUID], assigned: bool
    ) -> None:
        """Bulk assign/unassign ("Add all modules"); 404 if ANY id is unknown."""
        if await self._users.get_by_id(user_id) is None:
            raise NotFoundError("User")
        unique_ids = list(set(module_ids))
        if await self._content.count_modules_by_ids(unique_ids) != len(unique_ids):
            raise NotFoundError("Module")
        await self._assignments.set_user_modules(user_id, unique_ids, assigned)
        await self._cascade_to_lessons(user_id, unique_ids, assigned)
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `uv run pytest tests/integration/test_routers/test_admin_users.py -k bulk_assign_modules_cascades -v`
Expected: PASS.

- [ ] **Step 5: Run the full assignment test class**

Run: `uv run pytest tests/integration/test_routers/test_admin_users.py::TestAssignments -v`
Expected: all PASS, including `test_bulk_assign_and_unassign_modules` and
`test_bulk_with_unknown_id_is_404_and_writes_nothing` (the latter is the
atomicity regression guard — its module/lesson ids never reach the cascade
because validation 404s first).

- [ ] **Step 6: Commit**

```bash
git add backend/src/services/admin_user_service.py backend/tests/integration/test_routers/test_admin_users.py
git commit -m "Cascade bulk module assignment to lessons"
```

---

### Task 5: Full-resync regression tests

**Files:**
- Test only: `backend/tests/integration/test_routers/test_admin_users.py::TestAssignments`.

**Interfaces:**
- Consumes: the endpoints from Tasks 1–4 (no production code changes in this task — it's a pure verification task for the "full resync, not one-time seed" design decision).

- [ ] **Step 1: Write the tests**

Add to `class TestAssignments`:

```python
    async def test_reassigning_module_resyncs_previously_unassigned_lesson(
        self, client: AsyncClient, db_session: AsyncSession, org: Org
    ) -> None:
        user = await create_user(db_session, email="cascade-resync-module@example.com")
        track = await create_track(db_session, "Resync Track")
        module = await create_module(db_session, track, "Resync Module")
        lesson_keep = await create_lesson(db_session, module, "Resync Lesson Keep", sort_order=0)
        lesson_drop = await create_lesson(db_session, module, "Resync Lesson Drop", sort_order=1)

        assert (
            await client.put(
                f"/api/admin/users/{user.id}/modules/{module.id}",
                json={"assigned": True},
                headers=org.headers,
            )
        ).status_code == 204
        # admin hand-picks: unassign just one lesson
        assert (
            await client.put(
                f"/api/admin/users/{user.id}/lessons/{lesson_drop.id}",
                json={"assigned": False},
                headers=org.headers,
            )
        ).status_code == 204
        overview = (await client.get("/api/admin/learning", headers=org.headers)).json()
        entry = next(u for u in overview["users"] if u["id"] == str(user.id))
        assert entry["assigned_lesson_ids"] == [str(lesson_keep.id)]

        # toggling the module off and back on is a full resync: both lessons return
        assert (
            await client.put(
                f"/api/admin/users/{user.id}/modules/{module.id}",
                json={"assigned": False},
                headers=org.headers,
            )
        ).status_code == 204
        assert (
            await client.put(
                f"/api/admin/users/{user.id}/modules/{module.id}",
                json={"assigned": True},
                headers=org.headers,
            )
        ).status_code == 204

        overview = (await client.get("/api/admin/learning", headers=org.headers)).json()
        entry = next(u for u in overview["users"] if u["id"] == str(user.id))
        assert sorted(entry["assigned_lesson_ids"]) == sorted(
            [str(lesson_keep.id), str(lesson_drop.id)]
        )

    async def test_reassigning_track_resyncs_previously_unassigned_module(
        self, client: AsyncClient, db_session: AsyncSession, org: Org
    ) -> None:
        user = await create_user(db_session, email="cascade-resync-track@example.com")
        track = await create_track(db_session, "Resync Track 2")
        module_keep = await create_module(db_session, track, "Resync Module Keep", sort_order=0)
        module_drop = await create_module(db_session, track, "Resync Module Drop", sort_order=1)

        assert (
            await client.put(
                f"/api/admin/users/{user.id}/tracks/{track.id}",
                json={"assigned": True},
                headers=org.headers,
            )
        ).status_code == 204
        assert (
            await client.put(
                f"/api/admin/users/{user.id}/modules/{module_drop.id}",
                json={"assigned": False},
                headers=org.headers,
            )
        ).status_code == 204
        overview = (await client.get("/api/admin/learning", headers=org.headers)).json()
        entry = next(u for u in overview["users"] if u["id"] == str(user.id))
        assert entry["assigned_module_ids"] == [str(module_keep.id)]

        assert (
            await client.put(
                f"/api/admin/users/{user.id}/tracks/{track.id}",
                json={"assigned": False},
                headers=org.headers,
            )
        ).status_code == 204
        assert (
            await client.put(
                f"/api/admin/users/{user.id}/tracks/{track.id}",
                json={"assigned": True},
                headers=org.headers,
            )
        ).status_code == 204

        overview = (await client.get("/api/admin/learning", headers=org.headers)).json()
        entry = next(u for u in overview["users"] if u["id"] == str(user.id))
        assert sorted(entry["assigned_module_ids"]) == sorted(
            [str(module_keep.id), str(module_drop.id)]
        )
```

- [ ] **Step 2: Run the tests**

Run: `uv run pytest tests/integration/test_routers/test_admin_users.py -k resync -v`
Expected: both PASS (Tasks 1–4 already implement the behaviour these verify —
this task is confirmation, not new production code).

- [ ] **Step 3: Run the full backend test suite**

Run (inside `backend/`): `uv run poe format && uv run poe lint && uv run poe test`
Expected: all green.

- [ ] **Step 4: Commit**

```bash
git add backend/tests/integration/test_routers/test_admin_users.py
git commit -m "Add full-resync regression tests for cascading assignment"
```

---

### Task 6: Frontend — reflect cascaded state after track/module toggles

**Files:**
- Modify: `frontend/src/pages/Admin.tsx` (functions `toggleLearningItem` at line 198 and `bulkAssignLearningItems` at line 236).

**Interfaces:**
- Consumes: `client.GET('/api/admin/learning')` (existing, already used in `loadProjectData`), `AdminLearning` type (existing, `frontend/src/types/domain.ts`).
- Produces: new local helper `refetchLearningData()` used by both toggle functions.

- [ ] **Step 1: Add the refetch helper**

In `frontend/src/pages/Admin.tsx`, immediately after the `LIST_FIELDS` constant
(lines 192-196), add:

```typescript
  async function refetchLearningData() {
    const { data } = await client.GET('/api/admin/learning')
    if (data) setLearningData(data)
  }
```

- [ ] **Step 2: Switch `toggleLearningItem`'s track/module branch to refetch**

Replace the success branch of `toggleLearningItem` (currently lines 217-230):

```typescript
      if (error) {
        setActionError(errorMessage(error, `Failed to update ${action} assignment.`))
      } else {
        setLearningData(prev => ({
          ...prev,
          users: prev.users.map(u => {
            if (u.id !== userId) return u
            const ids = currentlyAssigned
              ? u[listField].filter(id => id !== itemId)
              : [...u[listField], itemId]
            return { ...u, [listField]: ids }
          }),
        }))
      }
```

with:

```typescript
      if (error) {
        setActionError(errorMessage(error, `Failed to update ${action} assignment.`))
      } else if (action === 'lesson') {
        setLearningData(prev => ({
          ...prev,
          users: prev.users.map(u => {
            if (u.id !== userId) return u
            const ids = currentlyAssigned
              ? u[listField].filter(id => id !== itemId)
              : [...u[listField], itemId]
            return { ...u, [listField]: ids }
          }),
        }))
      } else {
        // Track/module toggles now cascade to modules/lessons server-side —
        // refetch rather than re-deriving the cascade client-side.
        await refetchLearningData()
      }
```

- [ ] **Step 3: Switch `bulkAssignLearningItems`'s track/module branch to refetch**

Replace the success branch of `bulkAssignLearningItems` (currently lines
256-269):

```typescript
      if (error) {
        setActionError(errorMessage(error, `Failed to update ${kind} assignments.`))
      } else {
        setLearningData(prev => ({
          ...prev,
          users: prev.users.map(u => {
            if (u.id !== userId) return u
            const next = assigned
              ? Array.from(new Set([...u[listField], ...ids]))
              : u[listField].filter(id => !ids.includes(id))
            return { ...u, [listField]: next }
          }),
        }))
      }
```

with:

```typescript
      if (error) {
        setActionError(errorMessage(error, `Failed to update ${kind} assignments.`))
      } else if (kind === 'lessons') {
        setLearningData(prev => ({
          ...prev,
          users: prev.users.map(u => {
            if (u.id !== userId) return u
            const next = assigned
              ? Array.from(new Set([...u[listField], ...ids]))
              : u[listField].filter(id => !ids.includes(id))
            return { ...u, [listField]: next }
          }),
        }))
      } else {
        // Track/module bulk toggles now cascade to modules/lessons server-side —
        // refetch rather than re-deriving the cascade client-side.
        await refetchLearningData()
      }
```

- [ ] **Step 4: Run frontend checks**

Run (inside `frontend/`): `npm run typecheck && npm run lint && npm run build`
Expected: all clean (no new types needed — `refetchLearningData` reuses the
existing `AdminLearning` shape already returned by `client.GET('/api/admin/learning')`).

- [ ] **Step 5: Manual browser check**

Run `npm run dev` (frontend) and the backend dev server (`uv run poe dev`,
inside `backend/`), open `/admin`, open a project, open a user's panel:
- Assign a track that has modules/lessons → confirm the track shows assigned
  AND expanding it shows all modules assigned AND expanding a module shows
  all lessons assigned, with no manual page reload.
- Unassign that track → confirm modules/lessons clear the same way.
- Assign a single module → confirm its lessons show assigned.
- Hand-unassign one lesson under an assigned module, then toggle the module
  off and on again → confirm the lesson comes back (full resync, matches
  Task 5's backend test).

- [ ] **Step 6: Commit**

```bash
git add frontend/src/pages/Admin.tsx
git commit -m "Refetch learning data after track/module assignment toggles"
```

---

### Task 7: Update documentation

**Files:**
- Modify: `CLAUDE.md` (Feature index list around line 62-70; appendix entry at lines 488-509).

- [ ] **Step 1: Add a Feature index line**

In `CLAUDE.md`, in the "## Feature index → specs" section, immediately after
the existing line:

```markdown
- **Learning path, locks & maturity gating** — "Locking, prerequisites & preview" below;
  specs `2026-07-14-learning-path-level-headers-design.md`, `2026-07-20-below-level-free-review-design.md`.
```

add:

```markdown
- **Cascading track/module assignment** — assigning a track/module now auto-assigns
  everything under it (full resync, both ways) —
  `specs/2026-07-23-cascading-track-module-assignment-design.md`; `services/admin_user_service.py`.
```

- [ ] **Step 2: Mark the superseded semantics in the 2026-07-06 appendix entry**

In `CLAUDE.md`, find this sentence inside the "Lesson assignment (2026-07-06,
post-Batch 6)" appendix entry (around line 491):

```markdown
  Semantics: assigning a module does NOT auto-assign its lessons — the admin picks lessons in
  the UserPanel (module row expands to a lesson list) or clicks "+ add all lessons"; tracks
  got "+ add all modules". Every level (tracks section header / track's module list / module's
  lesson list) has BOTH "+ add all" and "− unassign all" buttons (shown only when applicable).
```

replace it with:

```markdown
  Semantics (as of 2026-07-06; **superseded 2026-07-23, see the Cascading
  track/module assignment entry below**): assigning a module does NOT auto-assign its lessons —
  the admin picks lessons in the UserPanel (module row expands to a lesson list) or clicks
  "+ add all lessons"; tracks got "+ add all modules". Every level (tracks section header /
  track's module list / module's lesson list) has BOTH "+ add all" and "− unassign all" buttons
  (shown only when applicable).
```

Then find (around line 498-500):

```markdown
  single lesson toggle = `PUT …/lessons/{lesson_id} {assigned}`. Unassigning a module/track
  KEEPS the child assignment rows (same keep-rows semantics the old track→module pair already
  had — reassigning restores the previous selection). Learner side: graph `lesson_count`/
```

replace it with:

```markdown
  single lesson toggle = `PUT …/lessons/{lesson_id} {assigned}`. ~~Unassigning a module/track
  KEEPS the child assignment rows (same keep-rows semantics the old track→module pair already
  had — reassigning restores the previous selection).~~ **Superseded 2026-07-23:** unassigning
  now cascades to child rows too, and reassigning is a full resync (see below). Learner side:
  graph `lesson_count`/
```

- [ ] **Step 3: Add a new appendix entry**

In `CLAUDE.md`, find the end of the "Invite link/email split (2026-07-07)"
appendix entry (the last entry in the file) and add a new entry after it:

```markdown

- **Cascading track/module assignment (2026-07-23):** assigning a track or module to a user
  now auto-assigns every module/lesson underneath it; unassigning cascades the same way.
  Full resync semantics — reassigning a track/module always sets *all* its descendants back
  to assigned, even ones an admin had previously hand-unassigned (there is no stable
  "assign track, then hand-curate one lesson off" customization across a toggle of the
  ancestor). `AdminUserService.set_track_assignment(s)`/`set_module_assignment(s)`
  (`backend/src/services/admin_user_service.py`) compute the descendant module/lesson ids via
  two new private helpers (`_cascade_module_and_lesson_ids`, `_cascade_lesson_ids`) built on
  the existing `ContentRepository.list_modules()`/`list_lesson_summaries()` reads, then bulk-write
  `user_modules`/`user_lessons` alongside the target level. No schema change, no new endpoints,
  no repository interface change. Lesson-level assignment is unchanged (lessons have no
  children). `Admin.tsx`'s track/module toggle handlers (`toggleLearningItem`,
  `bulkAssignLearningItems`) now refetch `GET /api/admin/learning` on success instead of
  optimistically patching one assignment array, since a single toggle can change three arrays
  at once; lesson toggles keep the prior optimistic patch (no cascade there). Spec:
  `docs/superpowers/specs/2026-07-23-cascading-track-module-assignment-design.md`.
```

- [ ] **Step 4: Commit**

```bash
git add CLAUDE.md
git commit -m "Document cascading track/module assignment"
```

---

## Final verification

- [ ] Run (inside `backend/`): `uv run poe format && uv run poe lint && uv run poe test` — all green.
- [ ] Run (inside `frontend/`): `npm run typecheck && npm run lint && npm run build` — all clean.
- [ ] Manual browser check from Task 6, Step 5, re-confirmed against the final state.

Deployment is **out of scope for this plan** — per project convention, ask
before any deploy or Azure-mutating step; `.\deploy.ps1` is a separate,
explicitly-approved action once this is merged.
