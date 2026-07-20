# Below-level tracks are freely reviewable

**Date:** 2026-07-20
**Area:** Learning path — module unlock rule (`frontend/src/pages/LearningPathNew.tsx`)

## Problem

A learner whose effective maturity level is above a track's `required_level`
could see the lower-level track (maturity unlocks the whole lane), but the
module **prerequisite path inside that lane still gated sequentially** — only
the first module was open, the rest padlocked. Reported for a test user pinned
to Practitioner (via `maturity_override`) who had finished the Introduction:
the Explorer "General I" lane showed module 1 unlocked and modules 2–5 locked,
forcing them to walk a path through content their level already treats as
mastered.

The progress model already says levels *below* the assessed level count as
complete (the overall bar renders Practitioner at 25% — Explorer done). Access
should agree: below-level content is review material, freely browsable.

## Decision

**Scope:** only tracks at a maturity level **strictly below** the learner's
effective level become fully open. The current level's tracks keep prerequisite
sequencing; higher levels keep their whole-track maturity lock. (User-chosen
over the wider "current level too" option.)

**Change:** one rule added to `isUnlocked`, after the admin bypass, the
`unlocked_by_maturity` check, and the Introduction gate:

```js
const rank = moduleLevelRank.get(id)
if (rank !== undefined && rank < levelIdx) return true
```

`moduleLevelRank` (module → its track's level rank over the full graph) and
`levelIdx` (the learner's effective level) already existed; this reuses them.

**Why this placement is correct:**
- Admin bypass and "finish the Introduction first" still win (they precede it).
- Higher-level tracks never reach this line — `unlocked_by_maturity === false`
  returns earlier.
- Same-level prerequisites still fall through to `predSatisfied` below.
- An un-assessed learner falls back to `levelIdx = 0` (Explorer), so nothing is
  "below level" and behavior is unchanged.
- Consistent with the self-propelling ladder: once a learner clears a level
  server-side and maturity advances, that level's tracks become below-level and
  open up for review automatically on the next graph load.

**Knock-on effects (all intended):**
- Lane dots, node glyphs, and the module popover render below-level modules as
  unlocked (they key off `isUnlocked`).
- The lane subtitle's stale `· locked` branch can no longer trigger for a
  below-level track.
- `firstCurrent` still marks the first not-done below-level module as the
  pulsing "current" / `next: …` hint. Kept deliberately: it's a soft "start
  reviewing here" nudge, not a gate, and doesn't conflict with free access.

## Scope boundaries

- **Frontend only.** Module locks are a visibility filter, not access control —
  the backend already serves any lesson to any authenticated user, and
  `next_lesson_id` resolves correctly regardless. No endpoint, schema, or
  migration change.

## Verification

- `npm run typecheck && npm run lint && npm run build` — clean.
- Browser (pending a Practitioner-pinned login): the Explorer lane opens all
  modules for a pinned Practitioner; an un-assessed Explorer learner is
  unchanged.
