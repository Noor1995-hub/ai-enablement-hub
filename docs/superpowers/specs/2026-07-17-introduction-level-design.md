# Introduction "level" — design

**Date:** 2026-07-17
**Status:** Approved (design), pending implementation plan
**Author:** Matthias + Claude

## Summary

Add a new pseudo-level called **Introduction** that sits *before* Explorer in the learning
path. It contains a single track (tagline: **"Let's get familiar"**) whose module(s) and
lesson(s) give newcomers an orientation to the learning path. Completing the Introduction is
**obligatory for everyone**; until it is complete, every other track is locked. Once it is
complete, the normal maturity gating resumes unchanged — so e.g. a Practitioner then sees both
Explorer and Practitioner unlocked, exactly as today.

Introduction is **not** a maturity level. It does **not** appear in the OVERALL JOURNEY stepper,
the "% of the full path" figure, the CURRENT LEVEL card, or the maturity-assessment graphic. It
appears **only** in the "YOUR TRACKS" section, rendered as its own level group with its own
progress bar so it looks identical to the four real level groups.

## Core framing (why this stays small)

The four maturity levels (`explore`, `practitioner`, `integrator`, `multiplier`) are the single
source of truth for all level math:

- Backend: `LEVEL_ORDER` / `LEVEL_RANK` in `backend/src/core/constants.py:29`.
- Frontend: `LEVELS` in `frontend/src/lib/levels.ts:17`.

Every level-aware UI element iterates one of these: the OVERALL JOURNEY stepper (4 segments at
25%), `overallPct` (divides by `LEVELS.length`), the CURRENT LEVEL card, and the Assessment
maturity graphic (`Assessment.tsx` maps `LEVELS`).

**Decision: Introduction stays OUT of `LEVELS`/`LEVEL_ORDER`.** Because those elements only ever
know the four real levels, they need **no changes at all** — Introduction is invisible to them by
construction. Introduction is modeled instead as (a) a distinguished track and (b) a mandatory
completion gate, and rendered as a synthetic group only in "YOUR TRACKS".

The final unlock rule for any *non-Introduction* track becomes:

```
unlocked = introductionComplete AND unlocked_by_maturity
```

The Introduction track itself is always unlocked and always assigned to everyone.

## Chosen approach: `is_introduction` boolean + implicit assignment

The Introduction track is identified by a new `tracks.is_introduction` boolean (set once by a
migration; never admin-editable). It keeps `track_type='general'` and, crucially,
`required_level='explore'` — a valid, always-unlocked value — so **no CHECK constraint changes**
and **no `LEVEL_ORDER`/rank math is disturbed**.

"Obligatory for everyone" is enforced by **implicit assignment**: the learning-graph service
treats introduction tracks as assigned to every caller regardless of `user_tracks`/`user_modules`/
`user_lessons` rows, and counts *all* their lessons. This makes the requirement **correct by
construction** — no user can escape the gate by lacking an assignment row, there is no backfill
migration, and there is no new-user hook that could be forgotten.

### Alternatives considered and rejected

- **Real per-user assignment** (backfill migration + auto-assign in every user-creation path):
  reuses existing read logic with zero special-casing, but any missed creation path silently lets
  a user skip the gate — trading a contained, provably-correct read change for a fragile
  write-path that can violate the one hard requirement. Rejected.
- **Add `introduction` to `LEVEL_ORDER`/`LEVELS` as a real 0th level:** shifts every rank
  calculation, forces `introduction` to be filtered back *out* of the stepper / assessment /
  `overallPct` divisor, and still needs a separate gate anyway. Maximum blast radius, no benefit.
  Rejected.

## Detailed design

### 1. Data model & migration

- Add column `is_introduction BOOLEAN NOT NULL DEFAULT false` to `tracks` (SQLAlchemy model
  `backend/src/db/models/learning.py`).
- New Alembic migration chained off the current head `d8e9f0a1b2c3`:
  - `op.add_column` the `is_introduction` column.
  - Insert the single **Introduction** track: `name='Introduction'`, `is_introduction=true`,
    `track_type='general'`, `required_level='explore'`, `sort_order=0`, `color='#941914'`.
  - No CHECK constraints are created or altered.
- The track ships **empty** (no modules/lessons). Content is authored afterward via the normal
  admin edit UI (the track is visible to admins because it is implicitly assigned; admins edit it
  in edit mode like any other track). The `sort_order=0` and the frontend's introduction-first
  sort both place it above Explorer.

### 2. Backend — graph, gate, and lesson endpoints

Schema (`backend/src/schemas/learning.py`): `TrackNode` and `ModuleNode` gain
`is_introduction: bool`.

`LearningService.graph` (`backend/src/services/learning_service.py`):

- Emit `is_introduction` on each track node; modules inherit their track's flag.
- For introduction tracks/modules, force `assigned=true`, and set `lesson_count` /
  `completed_lesson_count` over **all** their lessons (not just assigned ones). This needs a small
  scoped repository helper returning total + completed lesson counts for a given set of module ids
  (introduction modules only); non-introduction modules keep using
  `assigned_lesson_counts_by_module` unchanged.
- **Force `unlocked_by_maturity=true` for introduction tracks (and their modules).** This is
  load-bearing: `track_unlocked` returns `false` whenever `caller_rank is None` — i.e. for any
  user who has not completed the survey yet — so an `explore` track is *not* automatically unlocked
  for a no-maturity user. Introduction must always be unlocked regardless of maturity, so the graph
  overrides the flag to `true` for introduction rather than relying on `required_level='explore'`.

`LearningService.module_lessons` and `lesson_detail`: treat lessons belonging to introduction
modules as assigned, so the ModulePopup/sidebar show them as startable and the next-hop resolves
within the Introduction track.

`SurveyService._seed_assignments` (`backend/src/services/survey_service.py`): **skip introduction
tracks** (they are implicit — nothing to seed). This also keeps them out of `advance_level`, so
Introduction never perturbs maturity progression.

**The gate value itself is computed on the frontend** from the introduction group's module
counts, consistent with the app-wide convention that *locks are visibility filters, not access
control* (direct lesson URLs still render; `PUT …/progress` still accepts any lesson). No new
server-side access checks are added.

### 3. Frontend — `frontend/src/pages/LearningPathNew.tsx`

- `trackRank`: introduction tracks (`is_introduction === true`) sort **first**, before the four
  level groups.
- `trackGroups`: pull introduction tracks into their own synthetic group at the top, with a
  hard-coded level def `{ name: 'Introduction', tagline: "Let's get familiar", color: '#941914' }`.
  This reuses the **exact existing group header** (checkpoint dot + name + tagline + per-level
  progress bar) and the per-track `ProgressRing`, so Introduction looks identical to the other
  level groups. The remaining tracks group by `required_level` as today.
- Compute `introductionComplete`:
  - `true` if every introduction module is done (`lesson_count > 0 && completed_lesson_count >=
    lesson_count`).
  - **Guard: if Introduction has zero lessons in total, the gate is OPEN** (`introductionComplete
    = true`). An empty Introduction must lock no one; the gate activates automatically the moment
    lessons are published. (This also avoids the documented "0 assigned lessons locks forever"
    quirk.)
- Gating for non-introduction tracks/modules **only**: extend `isTrackLocked` / `isUnlocked` so a
  non-introduction track is locked when `!introductionComplete` (in addition to the existing
  `!unlocked_by_maturity`). The introduction track itself is **never** subject to the
  `introductionComplete` gate and (given the forced `unlocked_by_maturity=true`) is always
  unlocked; its modules remain subject only to any internal within-track prerequisites. Admins
  bypass, as everywhere.
- Locked-state copy: while `!introductionComplete`, a locked non-introduction track shows the
  greyed lane + lock with the note **"Complete the Introduction first"**. This message takes
  precedence over the maturity "Unlocks at {level}" note. After Introduction is complete,
  maturity-locked tracks fall back to their existing "Unlocks at {level}" copy.
- **No changes** to: the OVERALL JOURNEY stepper, `overallPct` / `levelFraction` / `levelIdx`,
  the CURRENT LEVEL card, `LEVEL_GRADIENT`, or `frontend/src/lib/levels.ts`.

### 4. Admin

- `GET /api/admin/learning`: include `is_introduction` on tracks so the admin UI can identify
  them.
- `frontend/src/pages/admin/UserPanel.tsx`: hide introduction tracks from the per-user assignment
  section (Introduction is mandatory, not per-user managed).
- Regenerate `frontend/src/api/schema.d.ts` after the backend schema changes.

### 5. Rollout

Ships dark and safe:

1. Migration adds the column and an **empty** Introduction track → `introductionComplete` is
   `true` for everyone (0 lessons) → **zero behavior change**; all existing tracks stay unlocked
   exactly as before.
2. When the Introduction module(s)/lesson(s) are authored and published via the admin UI, the gate
   **activates for everyone at once**, existing learners included ("obligatory for everyone"). The
   active-learner population is tiny, so no grandfathering is needed.

### 6. Testing

Backend (`uv run poe format && uv run poe lint && uv run poe test` in `backend/`):

- Graph reports the introduction track as `assigned=true` with counts over **all** its lessons,
  even for a user with no assignment rows.
- Graph reports the introduction track `unlocked_by_maturity=true` even for a user with no
  completed survey (`maturity_level` null / `caller_rank` None) — the force-unlock path.
- Gate-open case: with an empty Introduction, non-introduction tracks report unlocked (respecting
  maturity) — no regression.
- Gate-closed case: with an unfinished Introduction that has lessons, non-introduction tracks are
  reported locked; after completing all Introduction lessons they unlock (still respecting
  maturity — an integrator track stays maturity-locked for an explorer).
- `_seed_assignments` skips introduction tracks (no `user_tracks`/`user_modules`/`user_lessons`
  rows created for them; `advance_level` unaffected).
- Migration sanity: the shipped migration SQL runs against the test DB; existing authz matrix
  unchanged (no new endpoints).

Frontend (`npm run typecheck && npm run lint && npm run build` in `frontend/`):

- `schema.d.ts` regenerated.
- (Manual, if browser automation available) Introduction group renders above Explorer with its
  own progress bar; other tracks greyed with "Complete the Introduction first" before completion,
  unlocked after; stepper / CURRENT LEVEL / assessment graphic unchanged.

## Impact map (files touched)

Backend:
- `backend/src/db/models/learning.py` — add `is_introduction` column.
- `backend/alembic/versions/<new>_introduction_track.py` — new migration (down_revision
  `d8e9f0a1b2c3`).
- `backend/src/schemas/learning.py` — `is_introduction` on `TrackNode`/`ModuleNode`.
- `backend/src/services/learning_service.py` — implicit-assignment handling in `graph`,
  `module_lessons`, `lesson_detail`.
- `backend/src/repositories/` — small scoped total/completed lesson-count helper for introduction
  modules (content or assignment repo, matching existing patterns).
- `backend/src/services/survey_service.py` — `_seed_assignments` skips introduction tracks.
- `backend/src/schemas/` (admin learning) — `is_introduction` on the admin learning response.

Frontend:
- `frontend/src/pages/LearningPathNew.tsx` — `trackRank`, `trackGroups`, `introductionComplete`,
  gating in `isTrackLocked`/`isUnlocked`, locked-state copy.
- `frontend/src/pages/admin/UserPanel.tsx` — hide introduction tracks from assignment UI.
- `frontend/src/api/schema.d.ts` — regenerated.

Explicitly **unchanged**: `frontend/src/lib/levels.ts`, the OVERALL JOURNEY stepper, `overallPct`,
CURRENT LEVEL card, `Assessment.tsx`, `LEVEL_ORDER`/`LEVEL_RANK`, all four CHECK constraints,
`content_service.create_track`.

## Open questions / notes

- Color is `#941914` (dark red), distinct from Explorer's `#EF463C`.
- If more than one introduction track is ever wanted, the boolean already supports it — they would
  all group together under the single "Introduction" header. Current scope: exactly one track.
