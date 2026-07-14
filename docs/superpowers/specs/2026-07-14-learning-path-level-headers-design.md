# Learning path: level group headers with per-level progress — design

**Date:** 2026-07-14
**Status:** approved pending user review of this document
**Scope:** frontend only — `frontend/src/pages/LearningPathNew.tsx` (+ its style map). No backend, API, or schema changes.

## Problem

Track lanes on `/learning` are colored by their required maturity level
(`resolveTrackColor` maps `required_level` → the level color from `lib/levels.ts`),
and the lane list is already sorted by the maturity ladder (`trackRank`). But the
mapping is never labeled: a learner cannot tell that red = Explorer and
purple = Integrator without cross-referencing the journey bar. Management wants
the level ↔ track association explicit.

Rejected alternative: rotating the overall journey bar vertically next to the
lane list — duplicates the same information at two orientations and cramps the
layout. Also rejected: per-row level chips (repetitive — six consecutive
"Integrator" pills) and a vertical colored rail (busier than headers, reads as a
timeline).

## Decision summary

1. **Group the lane list under per-level section headers.** Tracks are already
   sorted by level; insert a header row whenever `required_level` changes.
2. **Move the current-level progress bar out of the top panel into these
   headers.** Each level group gets its own progress bar; the top panel keeps
   only the level card + the 4-color overall journey bar. This upgrades the old
   bar (which only ever showed the current level) to progress for every level.
3. **Header bars show actual content progress, always** — including levels the
   learner passed via assessment without doing the modules. The header's
   checkpoint dot carries "passed" status (mirroring the journey bar); the bar
   agrees with the lanes below it (e.g. passed Explorer with untouched modules
   shows a passed dot + "0 of 5 modules · 0%"). Chosen over rendering passed
   levels as 100%: that would contradict the lane subtitles one row lower and
   hide that skipped content is available.

## Design

### Grouping

In the render, replace the flat `tracks.map(...)` with grouped rendering:
partition the (already sorted) `tracks` into runs of equal `required_level`,
then render `header + lanes` per group. A track whose level cannot be resolved
by `levelByCode` (should not happen; `trackRank` already sorts these last) falls
into a trailing group with a neutral grey header showing the raw code and no
progress bar.

Levels with no assigned tracks produce no group and therefore no header.

### Header anatomy

One flex row + a slim bar per group, reusing the page's small-caps idiom:

- **Checkpoint dot** (18 px, same visual language as the journey bar's
  checkpoints so the two read as one system). Fill encodes state exactly like
  the journey bar: level-color fill + white check when the level is passed
  (`i < levelIdx`, or `i === levelIdx && levelFraction >= 1`); white fill +
  small inner colored dot for the current level; plain white for future levels.
  **Deviation from the journey bar:** the border is always the level color
  (the bar greys future checkpoints to `#E2E2E2`) — headers exist to carry the
  color ↔ level identity, so the color must survive the locked state.
- **Level name** in small caps in the level color; `fontWeight` 800 for the
  current level, 600 otherwise (the same emphasis rule as the journey bar's
  segment labels).
- **Tagline** after a `·` separator, grey `#8A8A8A` (e.g. "EXPLORER · AI
  basics") — headers explain what a level means, not just its name.
- **Right-aligned value** `"{modulesDone} of {modulesTotal} modules · {pct}%"`
  in the level color, `barValue` style — the same text the removed top bar
  showed, now per level.
- **Progress bar** below the row, replacing a decorative rule: ~5 px track in
  `#F5F5F5`, level-color fill at the level's lesson-based percentage, full
  header width. The bar visually fences the group.

Spacing intent: extra top margin before each header after the first, small gap
between the bar and the group's first lane; exact values tuned in the browser.

### Data / computation

Generalize the existing `currentLevelModules` computation (uncommitted working-
tree change, kept) into a per-level aggregate keyed by level code: for each
level, over assigned modules in assigned tracks at that level —
`lessonsDone / lessonsTotal` (bar percentage, lesson-based) and
`modulesDone / modulesTotal` (header text, module counts). Same semantics the
top bar had. The current level's lesson fraction (`levelFraction`) is read from
this aggregate and feeds `overallPct` exactly as today — the overall journey
bar's math is unchanged.

### Top panel changes

Remove the "{level} progress" `barHeader` row and the `levelTrack`/`levelFill`
bar. Keep the level card, the overall journey bar, its checkpoints and segment
labels. Style entries that become unused are deleted; the header bar gets new
style names (it is not the old bar restyled).

### Locked / future levels

Maturity-locked lanes are non-expandable, so learners naturally show 0% there;
admins bypass locks and see their actual counts. A group whose modules have no
assigned lessons renders "0 of 0 modules · 0%" (rare, admin-visible, matches
the existing 0/0 quirk semantics).

### Untouched

Journey bar math and rendering, level card, lane behavior (expand/collapse,
persisted open lane, edit mode, admin add buttons in the `tracksHeader` row),
module popover, zoom handling (headers are plain flex — no rect math, no
`getRectZoomFactor`).

## Verification

- `npm run typecheck && npm run lint && npm run build` in `frontend/`.
- Browser against the live backend: admin view (all groups colored, actual
  progress everywhere), learner view with locked levels (colored headers over
  grey lanes, "Unlocks at X" copy sitting under its matching header), current-
  level emphasis, and — if reproducible with a test user — the passed-level
  case (checked dot + 0% bar).
