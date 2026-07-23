# Cascading track/module assignment

**Date:** 2026-07-23
**Author:** Matthias + Claude (brainstormed)
**Status:** design, awaiting review before planning

## Purpose

Today, assigning a track, module, or lesson to a user in the admin panel
(`UserPanel.tsx`) writes to exactly one of three independent tables
(`user_tracks` / `user_modules` / `user_lessons`) — nothing cascades. An admin
who assigns a track sees it appear, but none of its modules or lessons are
assigned; they have to separately expand the track and click "+ add all
modules", then expand each module and click "+ add all lessons" (or toggle
lessons one by one) to make the content actually usable end to end.

This feature makes assigning a track or module **automatically assign
everything underneath it**, so a single click ("assign this track") is enough
to give a user the whole track, all its modules, and all their lessons.
Unassigning cascades the same way, symmetrically.

## Current behaviour (confirmed by reading the code)

- `Track` → `Module` (`track_id` FK) → `Lesson` (`module_id` FK) is the
  content hierarchy (`backend/src/db/models/learning.py`).
- `user_tracks`, `user_modules`, `user_lessons` are three independent
  entitlement tables (`backend/src/db/models/assignment.py`) — none
  references the others; there is no DB-level or application-level link
  between "track assigned" and "its modules/lessons assigned".
- `backend/src/services/admin_user_service.py` — `set_track_assignment`,
  `set_module_assignment`, `set_lesson_assignment` and their bulk siblings
  (`set_track_assignments`, `set_module_assignments`, `set_lesson_assignments`)
  each validate then write to exactly one table via
  `backend/src/repositories/assignment_repository.py`. No cross-table writes
  happen anywhere in this path today.
- This is documented, intentional behaviour as of the 2026-07-06 lesson
  assignment feature (see `CLAUDE.md`'s "Lesson assignment" appendix entry):
  "assigning a module does NOT auto-assign its lessons"; "Unassigning a
  module/track KEEPS the child assignment rows... reassigning restores the
  previous selection." **This spec deliberately supersedes that behaviour.**

## Decisions

- **Cascade both ways.** Assigning a track/module assigns all descendants;
  unassigning a track/module unassigns all descendants too (symmetric).
- **Full resync, not one-time seed.** Every assign of a track/module sets
  *all* of its descendants to `assigned=true`, even ones an admin had
  previously hand-unassigned. "This track is assigned" now always means
  "everything under it is assigned" — there is no partial/customized state
  that survives a toggle-off-then-on of an ancestor.
  - Consequence accepted: an admin can no longer use "assign track" +
    "manually unassign one lesson" as a *stable* customization — reassigning
    the track (or its module) at any point in the future will re-add that
    lesson. Per-lesson/per-module curation only survives if the ancestor is
    never re-toggled.
- **Lesson-level assignment is unchanged** — lessons have no children, so
  `set_lesson_assignment`/`set_lesson_assignments` are untouched by this spec.
- This intentionally changes (supersedes) the "keep rows" / "restore previous
  selection" behaviour documented in `CLAUDE.md`'s 2026-07-06 lesson
  assignment entry; that entry gets an update noting the new behaviour once
  this ships.

## Design

### Backend — cascade in the service layer

`backend/src/services/admin_user_service.py` is the only place that changes.
It already holds both `self._content` (can list modules-by-track and
lessons-by-module) and `self._assignments` (the per-level write methods), so
cascading is just: after writing the target level, compute the wider set of
descendant ids and write those too.

- `set_track_assignment(user_id, track_id, assigned)`:
  1. Existing validation (user exists, track exists) — unchanged.
  2. Existing write: `self._assignments.set_user_track(...)` — unchanged.
  3. **New:** fetch this track's modules, and all lessons under those
     modules; if the module id list is non-empty, call
     `self._assignments.set_user_modules(user_id, module_ids, assigned)`; if
     the lesson id list is non-empty, call
     `self._assignments.set_user_lessons(user_id, lesson_ids, assigned)`.
- `set_module_assignment(user_id, module_id, assigned)`:
  1. Existing validation + write — unchanged.
  2. **New:** fetch this module's lessons; if non-empty, call
     `self._assignments.set_user_lessons(user_id, lesson_ids, assigned)`.
- `set_track_assignments(user_id, track_ids, assigned)` (bulk): same idea,
  but the module/lesson id sets are the union across every track in the
  batch (still a single `set_user_modules` call and a single
  `set_user_lessons` call, not one per track).
- `set_module_assignments(user_id, module_ids, assigned)` (bulk): union of
  lessons across every module in the batch, one `set_user_lessons` call.
- `set_lesson_assignment(s)`: no change.

**Fetching descendants without new repository methods or N+1 queries:**
`ContentRepository.list_modules()` (no `track_id` arg) already returns *all*
modules, and `ContentRepository.list_lesson_summaries()` already returns
*all* lessons with their `module_id`. For a single-track or single-module
call this is one extra query each; for a bulk call across many
tracks/modules it's still exactly one query each (fetch once, filter in
Python by whether `module.track_id` / `lesson.module_id` is in the target id
set). This avoids adding new abstract-repository methods for what is a
small, bounded content set (tens of modules, low hundreds of lessons total).

**Atomicity:** the existing invariant — "an unknown id anywhere in a bulk
request 404s and writes nothing" — is preserved unchanged, because validation
(`count_tracks_by_ids` / `count_modules_by_ids` matching the requested id
count) still happens *before* any write, exactly as today. Cascade-derived
ids (modules of a validated track, lessons of a validated module) are always
real content fetched fresh from the DB, so they can never trigger a 404 —
the cascade adds no new failure mode. Each `set_user_*` repository call still
commits its own transaction (existing pattern, unchanged); a crash between
the track-level commit and the cascade commits is a pre-existing class of
risk in this codebase (no request-scoped transaction wraps multi-call
service methods anywhere today) and is accepted as-is, not newly introduced.

### Frontend — reflect cascaded state

`frontend/src/pages/Admin.tsx`:

- `toggleLearningItem` (single track/module/lesson toggle) and
  `bulkAssignLearningItems` ("+ add all" / "− unassign all") currently
  optimistically patch only the one list field for the toggled kind
  (`assigned_track_ids` *or* `assigned_module_ids` *or* `assigned_lesson_ids`)
  via `LIST_FIELDS`. Once a track/module toggle can also change the *other*
  two arrays, that single-field patch would leave the UI showing stale
  (unassigned-looking) modules/lessons until a manual reload.
- **Change:** on a successful track or module PUT (single or bulk), refetch
  `GET /api/admin/learning` and replace `learningData` wholesale, instead of
  hand-patching one list field. This reuses the exact fetch already done in
  `loadProjectData` and keeps the frontend as a thin reflection of
  server-computed state rather than re-implementing cascade math twice.
  Lesson-level toggles (no cascade) can keep the existing single-field
  optimistic patch, since nothing else changes when a lesson is toggled.
- No component/layout changes: `UserPanel.tsx`'s track/module/lesson
  expanders already read from `assigned_track_ids` / `assigned_module_ids` /
  `assigned_lesson_ids`, so once those arrays are correct after the refetch,
  the existing rendering is correct.

### Out of scope

- No change to `GET /api/admin/learning`'s response shape — it already
  returns all three assignment arrays per user.
- No change to the learner-facing endpoints (`learning_service.py`,
  `/api/learning/graph`, `/api/modules/{id}/lessons`) — they already compute
  `assigned` purely by membership in the (now-cascaded) tables, so they pick
  up the new behaviour automatically with no code change.
- No DB triggers, no new tables, no schema migration — this is pure
  application-layer logic over existing tables.
- No change to lesson-level assignment semantics.
- No "view what would be affected before confirming" preview UI — the
  existing toggle/bulk buttons just do more than they used to.

## Testing

`backend/tests/integration/test_routers/test_admin_users.py::TestAssignments`:

- New: assigning a track also assigns all its modules and all lessons under
  them (single and bulk endpoints).
- New: unassigning a track also unassigns all its modules and lessons.
- New: assigning a module also assigns all its lessons (single and bulk);
  unassigning symmetric.
- New: full-resync — hand-unassign one lesson under an assigned module, then
  reassign the module (or its track) → the lesson is assigned again.
- New: a track/module with zero modules/lessons cascades to an empty set
  without error.
- New: bulk track/module assignment cascades correctly across *every* id in
  the batch (union of descendants), not just the first.
- Regression: the existing "unknown id → 404, nothing written" atomicity
  test still passes with cascading in place.
- Existing tests that assign a module/track directly and only assert that
  level's state (e.g. `test_bulk_assign_and_unassign_modules`) get their
  assertions extended to also check the now-cascaded lesson ids.

Frontend: `npm run typecheck && npm run lint && npm run build`; no new
component logic beyond the refetch-on-success change, so no new frontend
unit tests are planned — manual browser check (assign a track, confirm
modules/lessons show assigned without reload; unassign, confirm they clear).

## Success criteria

- Clicking "assign" on a track in the admin panel results in that user
  having every module and every lesson under that track assigned, visible
  immediately in the UI without a manual refresh.
- Clicking "assign" on a module results in every lesson under it assigned.
- Unassigning a track or module clears all descendants the same way.
- Reassigning a previously-toggled-off track/module always yields "fully
  assigned" again, regardless of any prior manual per-lesson customization.
- The existing bulk atomicity guarantee (bad id → 404, nothing written)
  still holds.
- All backend tests green (`uv run poe format && uv run poe lint && uv run
  poe test`), frontend typecheck/lint/build clean.
