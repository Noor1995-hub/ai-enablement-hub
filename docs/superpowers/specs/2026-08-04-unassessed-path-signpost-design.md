# Un-assessed learners get signposted to the assessment

**Date:** 2026-08-04
**Area:** Learning path — un-assessed display state (`frontend/src/pages/LearningPathNew.tsx`)

## Problem

A learner who finishes the Introduction but has not completed the maturity
assessment is stuck on `/learning` with no way to find out why, and the page
actively misleads them.

Reported live: `axl.tanghe@delaware.pro` (created 2026-07-30, project Delaware)
completed both Introduction lessons on 2026-08-03 and could not reach General I.
Assignments were correct (8 tracks / 31 modules / 106 lessons, General I
included). What he was missing was a `survey_responses` row — he has none, and
no `maturity_override`.

The lock is working as designed. The chain:

1. `MaturityService.effective_level` returns `None` — no override, no complete
   survey (`backend/src/services/maturity_service.py:46-51`).
2. `LearningService.graph` therefore has `caller_rank = None`, so
   `track_unlocked()` is `False` for **every** level including `explore`
   (`backend/src/services/learning_service.py:55-58`).
3. Introduction is force-unlocked; every other track ships
   `unlocked_by_maturity: false` (`…/learning_service.py:84-87`).
4. `isTrackLocked` padlocks them (`LearningPathNew.tsx:313-319`).

This is deliberate — `2026-07-17-introduction-level-design.md:101-103` calls out
that an `explore` track is *not* auto-unlocked for an un-surveyed user, which is
exactly why Introduction needed its own force-unlock flag.

**The defect is the display.** Because `levelIdx` clamps a null level to index 0
(`Math.max(0, LEVELS.findIndex(…))`, line 323), the page renders an un-assessed
learner as a full Explorer:

- CURRENT LEVEL card reads **"Explorer / AI basics"**.
- General I's lane reads **"Unlocks at Explorer"** — telling them to reach a
  level the same page claims they already hold.
- The overall bar reads "0% of the full path" in Explorer red with the Explorer
  checkpoint marked *current*.
- The page subtitle says "Based on your maturity assessment, these tracks are
  tailored to where you are today" — citing an assessment that never happened.
- Nothing anywhere links to `/assessment`.

Since the Introduction *is* complete, the existing `introBlocked` branch (which
would at least have said "Complete the Introduction first") does not fire.

**Scale:** 51 of 104 users currently have no effective maturity. Axl is the only
one who has finished the Introduction, so he hit the wall first; the rest reach
the same wall the moment they finish those two lessons.

## Decision

Add an explicit **un-assessed display state**, driven by one flag:

```js
const notAssessed = levelCode === null
```

`levelCode` is already state, set from the graph's `maturity_level` (line 232).
No new fetch, no backend change.

**Iron rule for this change: display only.** `isUnlocked`, `isTrackLocked`,
`introComplete`, `predSatisfied`, `firstCurrent` and `levelIdx` itself are **not
touched**. `levelIdx` feeds the below-level free-review rule at line 302
(`rank < levelIdx`), which is already inert when un-assessed (`rank < 0` is never
true — noted in `2026-07-20-below-level-free-review-design.md`). Leaving the
predicates alone means this change cannot alter who can access what.

### The seven display sites

| # | Site | Today (un-assessed) | With `notAssessed` |
|---|------|---------------------|--------------------|
| 1 | Page subtitle, line 524 | "Based on your maturity assessment, these tracks are tailored to where you are today…" | "Your maturity assessment decides which tracks open up and how far along the path you start. Take it first. It takes about 10 minutes." |
| 2 | CURRENT LEVEL card, lines 553-554 | "Explorer" / "AI basics", both in `#EF463C` | "Not assessed yet" (`#101820`, 24px) / "The assessment sets your level" (`#8A8A8A`) |
| 3 | Overall bar value, line 561 | "0% of the full path" in `#EF463C` | "not started yet" in `#8A8A8A` |
| 4 | Overall bar fill, lines 564-568 | rendered when `overallPct > 0` | never rendered |
| 5 | Bar checkpoints, lines 572-573 | Explorer marked `current` (coloured ring + dot) | `passed` and `current` both false for all four — plain `#E2E2E2` rings |
| 6 | Segment labels, lines 589-595 | "Explorer" in `#EF463C` at weight 800 | all four `#B6B6B6` at weight 600 |
| 7 | Level group headers, lines 633-648 | Explorer group bold (800) + open dot ("you are here") | `passed` / `isCurrent` / `showOpenDot` all false for **maturity** groups, so the name falls to weight 600 and the dot renders as an empty ring. Group colour and the honest "0 of 5 modules · 0%" stay. |

All user-facing strings above avoid em/en dashes, per the sanitizer convention
introduced for generated copy in `e19474f`.

The Introduction group keeps its own logic untouched — it is genuinely complete
and keeps its filled check dot.

### Locked lane subtitles

A new branch between the existing two, preserving current precedence:

```js
const subtitle = introBlocked
  ? 'Complete the Introduction first'
  : notAssessed && maturityLocked
    ? 'Take the assessment to unlock'
    : maturityLocked
      ? `Unlocks at ${requiredLevel?.name ?? track.required_level}`
      : /* unchanged progress copy */
```

`lockColor` gains the matching case: `notAssessed` → `#8A8A8A` (neutral), so a
locked lane no longer wears a level colour it hasn't earned.

**Why "Take the assessment to unlock" replaces the level name on every locked
lane, rather than appending to it:** the group header above each run of lanes
already names the level (Explorer / Practitioner / Integrator / Multiplier), so
no information is lost; and "Unlocks at Explorer" is actively wrong-footing for
someone who has not been placed on the ladder at all. `"Unlocks at Integrator ·
take the assessment"` was considered and rejected — it ellipsises on narrow
lanes (`laneSubtitle` is `white-space: nowrap` with `text-overflow: ellipsis`).

**Why `introBlocked` still wins:** when the Introduction is incomplete *and* the
learner is un-assessed, both are real blockers, but the Introduction is the one
they can act on immediately. The assessment CTA is visible in the level card the
whole time either way, so nothing is hidden.

### The one new element

A CTA button in the level card routing to `/assessment`, reusing the existing
`#C42828` treatment from the module popover's `popCta`:

```
[ Take the assessment → ]
```

New style key `assessCta`; navigation via the page's existing `navigate`.

## Scope boundaries

- **Frontend only, one file.** `maturity_level: null` is already in the graph
  payload; no endpoint, schema, migration or API-type change. `npm run gen:api`
  is not needed.
- **Assessed learners see no change at all.** Every branch above is gated on
  `notAssessed`, which is false whenever a level resolves.
- **An admin pinning `maturity_override` resolves the state**, because the
  override feeds `effective_level` ahead of the survey — so the immediate
  operational fix for Axl (pin a level in the admin panel) drops him straight
  into the normal UI, with no survey row needed.
- **Admin / `user+` keep their lock bypass.** Nothing is locked for them, so the
  lane-subtitle branch never fires; if such an account has no survey the level
  card does show "Not assessed yet", which is true. Deliberately not
  special-cased.
- **JourneyHome is out of scope.** It already surfaces the assessment card as
  `available` for these users — the gap was only on `/learning`.
- **The "No tracks assigned yet" empty state is out of scope.** The panel is not
  rendered at all when `tracks.length === 0`, and Introduction is implicitly
  assigned to everyone, so a real learner always has at least one lane.
- **Not attempted: enforcing the order.** The Introduction lesson "Setting the
  scene" is written assuming the assessment already happened ("Based on the
  answers you gave in the maturity assessment you were given a score…"). Making
  the assessment a hard precondition for the Introduction, or reordering the
  content, is a separate content/flow decision.

## Verification

- `npm run typecheck && npm run lint && npm run build` (in `frontend/`) — clean.
- Browser, un-assessed learner: all seven sites render the un-assessed state and
  the CTA reaches `/assessment`. Reproduce locally by pointing a test account at
  a project with `learning` unlocked and no `survey_responses` row.
- Browser, assessed learner: `/learning` is pixel-identical to today.
- Browser, un-assessed **and** Introduction incomplete: locked lanes still read
  "Complete the Introduction first"; the CTA is still present.
- Regression, the reported case: pin `maturity_override` on the account and
  confirm the page returns to the normal assessed rendering.
