# Un-assessed learning-path signpost Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A learner with no maturity level sees an honest `/learning` page that tells them to take the assessment, instead of being told they are Explorer while Explorer content is padlocked.

**Architecture:** One display flag, `notAssessed = levelCode === null`, gates seven render sites in `frontend/src/pages/LearningPathNew.tsx`, plus one new CTA button routing to `/assessment`. Two pure helpers (`checkpointState`, `groupHeaderState`) hold the non-trivial branching so it is reviewable in isolation; the rest are string/colour swaps. No unlock predicate is modified.

**Tech Stack:** React 18 + TypeScript (Vite), inline style objects (`satisfies Record<string, CSSProperties>`), react-router-dom v6 `useNavigate`.

**Spec:** `docs/superpowers/specs/2026-08-04-unassessed-path-signpost-design.md`

## Global Constraints

- **Display only.** `isUnlocked`, `isTrackLocked`, `introComplete`, `predSatisfied`, `firstCurrent` and `levelIdx` must remain byte-identical. `levelIdx` feeds the below-level free-review rule (`rank < levelIdx`, line 302); changing it would alter access. Verify with `git diff` before each commit.
- **Frontend only, one source file.** No backend, schema, migration, or `schema.d.ts` change. Do NOT run `npm run gen:api`.
- **No em dashes or en dashes in user-facing copy** (sanitizer convention from commit `e19474f`). Hyphens only.
- **Assessed learners must render identically to today.** Every new branch is gated on `notAssessed`.
- **Exact copy strings** (use verbatim, they are approved):
  - Level card headline: `Not assessed yet`
  - Level card tagline: `The assessment sets your level`
  - Overall bar value: `not started yet`
  - Locked lane subtitle: `Take the assessment to unlock`
  - CTA button label: `Take the assessment →`
  - Un-assessed page subtitle: `Your maturity assessment decides which tracks open up and how far along the path you start. Take it first. It takes about 10 minutes.`
- **Exact colours:** neutral grey `#8A8A8A`, headline ink `#101820`, inert ring `#E2E2E2`, inert label `#B6B6B6`, CTA background `#C42828`.
- **Checks after every task** (run inside `frontend/`): `npm run typecheck && npm run lint && npm run build`. All three must be clean before committing.
- **Branch:** `feature/unassessed-path-signpost` (already created off `origin/main`, spec committed as `f6770f9`).

## File Structure

| File | Change | Responsibility |
|------|--------|----------------|
| `frontend/src/pages/LearningPathNew.tsx` | Modify | Everything. Local pure helpers join the existing `groupCode` / `trackRank` / `lighten` cluster near the top; render changes are in-place; one new style key `assessCta`. |

No new files. This page already houses its own pure helpers, so adding a
`lib/` module for two functions used by exactly one consumer would fight the
established pattern.

## Prerequisite: a browser login

Task 4 is the verification task and needs a working login against a local dev
stack. **The dev and prod databases are the same Azure DB** (`ai-enablement-hub`),
so do NOT create, modify, or delete users or survey rows to make testing easier.

Ask the user for either:
- credentials for a disposable account (`t@t.com` and `u@u.com` exist and look
  disposable, both with `maturity_override = practitioner`), or
- confirmation that they will run the browser walkthrough themselves.

Task 4 reproduces the un-assessed state by **intercepting the graph response**
rather than changing data, so any working login is sufficient.

---

### Task 1: The `notAssessed` flag, the progress panel, and the CTA

Covers spec sites 1 (subtitle), 2 (level card), 3 (bar value), 4 (bar fill),
5 (checkpoints), 6 (segment labels), and the new CTA button.

**Files:**
- Modify: `frontend/src/pages/LearningPathNew.tsx` (copy constants + `checkpointState` near line 85; `notAssessed` near line 324; render lines 524-528, 549-555, 557-562, 563-571, 587-601; new style key near line 1001)
- Test: none (no frontend test runner in this repo — see Task 4 for browser verification)

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces: `const notAssessed: boolean` in the component scope (Tasks 2 and 3 both read it); module-scope constants `LOCKED_UNTIL_ASSESSED: string` and `NEUTRAL_LOCK_COLOR: string` (Task 3 reads both); module-scope `function checkpointState(i: number, levelIdx: number, levelFraction: number, notAssessed: boolean): { passed: boolean; current: boolean }`.

- [ ] **Step 1: Make sure the branch and dependencies are current**

```bash
cd frontend
git branch --show-current          # must print feature/unassessed-path-signpost
npm install                        # package.json moved 65 commits; node_modules may be stale
npm run typecheck && npm run lint && npm run build
```

Expected: branch correct, all three checks clean. If they are not clean *before*
you change anything, stop and report — you are on a broken base.

- [ ] **Step 2: Add the copy constants and the `checkpointState` helper**

In `frontend/src/pages/LearningPathNew.tsx`, immediately after the `trackRank`
function (which ends around line 84, just before `function lighten`), insert:

```tsx
/* ── Un-assessed display state ──
   A learner with no completed survey and no admin maturity_override gets
   maturity_level: null from the graph. `levelIdx` deliberately clamps that to
   Explorer (0) because it also drives layout maths and the below-level review
   rule in isUnlocked — so every LEVEL-DERIVED DISPLAY value has to be
   suppressed explicitly instead of being read off levelIdx. Without that, the
   page tells an un-placed learner they are Explorer while padlocking Explorer
   content ("Unlocks at Explorer"). Spec:
   docs/superpowers/specs/2026-08-04-unassessed-path-signpost-design.md */
const NOT_ASSESSED_NAME = 'Not assessed yet'
const NOT_ASSESSED_TAGLINE = 'The assessment sets your level'
const NOT_ASSESSED_PROGRESS = 'not started yet'
const NOT_ASSESSED_SUBTITLE =
  'Your maturity assessment decides which tracks open up and how far along the ' +
  'path you start. Take it first. It takes about 10 minutes.'
/** Unchanged copy, moved from JSX to a constant so the two variants sit side by
    side. JSX was collapsing its whitespace, so it is written pre-collapsed here
    and renders character-for-character as it does today. */
const ASSESSED_SUBTITLE =
  'Based on your maturity assessment, these tracks are tailored to where you ' +
  'are today. Work through them at your own pace each module builds on the last.'
/** Locked-lane subtitle while the learner has no level at all. Wins over
    "Unlocks at {Level}", which wrong-foots someone who was never placed. */
const LOCKED_UNTIL_ASSESSED = 'Take the assessment to unlock'
/** Locked-lane accent while un-assessed: no level colour has been earned. */
const NEUTRAL_LOCK_COLOR = '#8A8A8A'

/** Overall-journey checkpoint state for level `i`. Un-assessed learners have
    nothing passed and nothing current — the bar reads empty, not "Explorer". */
function checkpointState(
  i: number,
  levelIdx: number,
  levelFraction: number,
  notAssessed: boolean,
): { passed: boolean; current: boolean } {
  if (notAssessed) return { passed: false, current: false }
  const passed = i < levelIdx || (i === levelIdx && levelFraction >= 1)
  return { passed, current: !passed && i === levelIdx }
}
```

- [ ] **Step 3: Derive the flag next to `levelIdx`**

Find lines 321-324:

```tsx
  /* ── Level + header math ── */
  // Fallback to Explorer when no completed assessment exposes a level yet.
  const levelIdx = Math.max(0, LEVELS.findIndex(l => l.code === levelCode))
  const level = LEVELS[levelIdx]
```

Replace with (note: `levelIdx` and `level` are unchanged — only a comment is
rewritten and one line added):

```tsx
  /* ── Level + header math ── */
  // levelIdx clamps a missing level to Explorer(0) for layout maths and for the
  // below-level review rule in isUnlocked. `notAssessed` is what the DISPLAY
  // branches on, so an un-placed learner is never rendered as an Explorer.
  const levelIdx = Math.max(0, LEVELS.findIndex(l => l.code === levelCode))
  const level = LEVELS[levelIdx]
  const notAssessed = levelCode === null
```

- [ ] **Step 4: Swap the page subtitle**

Find lines 524-528:

```tsx
            <p style={s.subtitle}>
              Based on your maturity assessment, these tracks are tailored to where
              you are today. Work through them at your own pace each module
              builds on the last.
            </p>
```

Replace with:

```tsx
            <p style={s.subtitle}>
              {notAssessed ? NOT_ASSESSED_SUBTITLE : ASSESSED_SUBTITLE}
            </p>
```

`ASSESSED_SUBTITLE` (Step 2) holds the original text pre-collapsed, which is
what JSX was rendering from the multi-line version. Read the two strings against
each other once before moving on: the assessed variant must be unchanged, and it
contains no dash (the original reads "at your own pace each module builds on the
last", which is already dash-free).

- [ ] **Step 5: Swap the level card and add the CTA**

Find lines 550-555:

```tsx
            <div style={s.panel}>
              <div style={s.levelCard}>
                <p style={s.smallLabel}>current level</p>
                <p style={{ ...s.levelName, color: level.color }}>{level.name}</p>
                <p style={{ ...s.levelTagline, color: level.color }}>{level.tagline}</p>
              </div>
```

Replace with:

```tsx
            <div style={s.panel}>
              <div style={s.levelCard}>
                <p style={s.smallLabel}>current level</p>
                {notAssessed ? (
                  <>
                    <p style={{ ...s.levelName, color: '#101820', fontSize: 24 }}>
                      {NOT_ASSESSED_NAME}
                    </p>
                    <p style={{ ...s.levelTagline, color: '#8A8A8A' }}>
                      {NOT_ASSESSED_TAGLINE}
                    </p>
                    <button
                      type="button"
                      onClick={() => navigate('/assessment')}
                      style={s.assessCta}
                    >
                      Take the assessment →
                    </button>
                  </>
                ) : (
                  <>
                    <p style={{ ...s.levelName, color: level.color }}>{level.name}</p>
                    <p style={{ ...s.levelTagline, color: level.color }}>{level.tagline}</p>
                  </>
                )}
              </div>
```

`navigate` already exists in scope (line 140).

- [ ] **Step 6: Swap the bar value and suppress the fill**

Find lines 559-571:

```tsx
                <div style={s.barHeader}>
                  <span style={s.smallLabel}>overall journey</span>
                  <span style={{ ...s.barValue, color: level.color }}>{overallPct}% of the full path</span>
                </div>
                <div style={s.overallTrack}>
                  {overallPct > 0 && (
                    <div style={{
                      ...s.overallFill,
                      width: `${overallPct}%`,
                      backgroundSize: `${10000 / overallPct}% 100%`,
                    }} />
                  )}
```

Replace with:

```tsx
                <div style={s.barHeader}>
                  <span style={s.smallLabel}>overall journey</span>
                  <span style={{ ...s.barValue, color: notAssessed ? '#8A8A8A' : level.color }}>
                    {notAssessed ? NOT_ASSESSED_PROGRESS : `${overallPct}% of the full path`}
                  </span>
                </div>
                <div style={s.overallTrack}>
                  {!notAssessed && overallPct > 0 && (
                    <div style={{
                      ...s.overallFill,
                      width: `${overallPct}%`,
                      backgroundSize: `${10000 / overallPct}% 100%`,
                    }} />
                  )}
```

- [ ] **Step 7: Route the checkpoints through the helper**

Find lines 571-573:

```tsx
                  {LEVELS.map((l, i) => {
                    const passed = i < levelIdx || (i === levelIdx && levelFraction >= 1)
                    const current = !passed && i === levelIdx
```

Replace with:

```tsx
                  {LEVELS.map((l, i) => {
                    const { passed, current } = checkpointState(i, levelIdx, levelFraction, notAssessed)
```

- [ ] **Step 8: Grey out the segment labels**

Find lines 588-595:

```tsx
                  {LEVELS.map((l, i) => {
                    const reached = i <= levelIdx
                    return (
                      <span key={l.code} style={{
                        ...s.segmentLabel,
                        left: `${12.5 + i * 25}%`,
                        color: reached ? l.color : '#B6B6B6',
                        fontWeight: i === levelIdx ? 800 : 600,
                      }}>
```

Replace with:

```tsx
                  {LEVELS.map((l, i) => {
                    const reached = !notAssessed && i <= levelIdx
                    return (
                      <span key={l.code} style={{
                        ...s.segmentLabel,
                        left: `${12.5 + i * 25}%`,
                        color: reached ? l.color : '#B6B6B6',
                        fontWeight: !notAssessed && i === levelIdx ? 800 : 600,
                      }}>
```

- [ ] **Step 9: Add the `assessCta` style key**

In the `const s = {` object, immediately after the `levelTagline` entry (ends
around line 1001, just before `barsCol`), insert:

```tsx
  /* Un-assessed CTA in the level card. Same treatment as the module popover's
     popCta so the page keeps one button language. */
  assessCta: {
    display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
    marginTop: 14, padding: '9px 15px', border: 'none', borderRadius: 8,
    background: '#C42828', color: '#fff', cursor: 'pointer',
    fontFamily: 'var(--dlw-font-ui)', fontSize: 12.5, fontWeight: 700,
  },
```

- [ ] **Step 10: Run the checks**

```bash
cd frontend
npm run typecheck && npm run lint && npm run build
```

Expected: all clean. A `levelFraction`-unused or `level`-unused error means a
branch was replaced too aggressively — both are still used by the assessed path.

- [ ] **Step 11: Confirm no unlock predicate moved**

```bash
git diff -U0 -- frontend/src/pages/LearningPathNew.tsx | grep -E '^[-+].*(isUnlocked|isTrackLocked|introComplete|predSatisfied|firstCurrent)' || echo "CLEAN: no unlock predicate touched"
```

Expected: `CLEAN: no unlock predicate touched`. Anything else violates the
global constraint — revert that hunk.

- [ ] **Step 12: Commit**

```bash
git add frontend/src/pages/LearningPathNew.tsx
git commit -m "feat(learning): honest progress panel for un-assessed learners

The panel derived everything from levelIdx, which clamps a null level to
Explorer(0) - so a learner with no completed assessment was rendered as a
full Explorer: 'Explorer / AI basics' on the level card, the Explorer
checkpoint marked current, and '0% of the full path' in Explorer red.

Adds notAssessed (levelCode === null) and branches the level card, bar
value, bar fill, checkpoints, segment labels and page subtitle on it, plus
a CTA to /assessment - the first link to the assessment on this page.

levelIdx itself is untouched: it also drives the below-level review rule
in isUnlocked, so access is unchanged.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

### Task 2: Level group headers go inert when un-assessed

Covers spec site 7. Today the Explorer group header renders bold with an open
dot, which reads as "you are here" for someone who has not been placed.

**Files:**
- Modify: `frontend/src/pages/LearningPathNew.tsx` (`groupHeaderState` helper next to `checkpointState` near line 110; render lines 633-648)

**Interfaces:**
- Consumes: `notAssessed` (Task 1, component scope).
- Produces: module-scope `function groupHeaderState(args: { isIntroGroup: boolean; introComplete: boolean; groupIdx: number; levelIdx: number; fraction: number; modulesTotal: number; notAssessed: boolean }): { isCurrent: boolean; contentComplete: boolean; showOpenDot: boolean }`. Nothing later consumes it.

**Note on the return shape:** the existing code computes a local `passed`, but it
is used ONLY to derive `isCurrent` — it never reaches the JSX (verified against
lines 649-676). So `passed` stays internal to the helper and is deliberately NOT
returned; returning it would trip `no-unused-vars` at the call site.

- [ ] **Step 1: Add the `groupHeaderState` helper**

Immediately after `checkpointState` (added in Task 1), insert:

```tsx
/** Level-group header state (dot fill, tick, weight).
    - Introduction keys off its own completion; it is not a maturity level and
      is unaffected by whether the learner has been assessed.
    - Maturity groups go fully inert when un-assessed: no group may read as
      "current" or "passed" when the learner has no level at all. */
function groupHeaderState(args: {
  isIntroGroup: boolean
  introComplete: boolean
  groupIdx: number
  levelIdx: number
  fraction: number
  modulesTotal: number
  notAssessed: boolean
}): { isCurrent: boolean; contentComplete: boolean; showOpenDot: boolean } {
  const { isIntroGroup, introComplete, groupIdx, levelIdx, fraction, modulesTotal, notAssessed } = args
  if (isIntroGroup) {
    return {
      isCurrent: !introComplete,
      contentComplete: introComplete,
      showOpenDot: !introComplete && groupIdx <= levelIdx,
    }
  }
  if (notAssessed) {
    return { isCurrent: false, contentComplete: false, showOpenDot: false }
  }
  // `passed` stays local: it only ever fed isCurrent, never the JSX.
  const passed =
    groupIdx !== -1 && (groupIdx < levelIdx || (groupIdx === levelIdx && fraction >= 1))
  const contentComplete = groupIdx !== -1 && modulesTotal > 0 && fraction >= 1
  return {
    isCurrent: !passed && groupIdx === levelIdx,
    contentComplete,
    showOpenDot: !contentComplete && groupIdx <= levelIdx,
  }
}
```

This is a faithful move of the existing expressions, with one added early
return. Introduction's `showOpenDot` keeps its original `groupIdx <= levelIdx`
term (`groupIdx` is `-1` for the intro group, so it is always true) rather than
being simplified, to keep the move behaviour-preserving.

- [ ] **Step 2: Call the helper from the render**

Find lines 631-648:

```tsx
                const stats = levelStats.get(group.levelCode) ?? EMPTY_LEVEL_STATS
                const groupPct = Math.round(lessonFraction(stats) * 100)
                const passed = isIntroGroup
                  ? introComplete
                  : (groupIdx !== -1 &&
                    (groupIdx < levelIdx || (groupIdx === levelIdx && lessonFraction(stats) >= 1)))
                const isCurrent = isIntroGroup
                  ? !introComplete
                  : (!passed && groupIdx === levelIdx)
                // The header tick means the level's CONTENT is actually finished.
                // A level the learner is past by maturity but hasn't worked
                // through yet (0% with locked lanes) reads as an open ring + dot,
                // like the Introduction and the current level, rather than a tick
                // that wrongly implies it is done.
                const contentComplete = isIntroGroup
                  ? introComplete
                  : (groupIdx !== -1 && stats.modulesTotal > 0 && lessonFraction(stats) >= 1)
                const showOpenDot = !contentComplete && groupIdx <= levelIdx
```

Replace with:

```tsx
                const stats = levelStats.get(group.levelCode) ?? EMPTY_LEVEL_STATS
                const groupPct = Math.round(lessonFraction(stats) * 100)
                // The header tick means the level's CONTENT is actually finished.
                // A level the learner is past by maturity but hasn't worked
                // through yet (0% with locked lanes) reads as an open ring + dot,
                // like the Introduction and the current level, rather than a tick
                // that wrongly implies it is done. An un-assessed learner has no
                // level, so no maturity group reads as current or passed.
                const { isCurrent, contentComplete, showOpenDot } = groupHeaderState({
                  isIntroGroup,
                  introComplete,
                  groupIdx,
                  levelIdx,
                  fraction: lessonFraction(stats),
                  modulesTotal: stats.modulesTotal,
                  notAssessed,
                })
```

- [ ] **Step 3: Check that the old locals are gone and nothing dangles**

```bash
cd frontend && grep -n "const passed = isIntroGroup" src/pages/LearningPathNew.tsx || echo "OK: old group-header locals replaced"
```

Expected: `OK: old group-header locals replaced`. The only remaining
`const passed =` in the file should be the one inside `groupHeaderState`; the
overall-bar checkpoints get theirs from `checkpointState` (Task 1).

- [ ] **Step 4: Run the checks**

```bash
cd frontend
npm run typecheck && npm run lint && npm run build
```

Expected: all clean.

- [ ] **Step 5: Confirm no unlock predicate moved**

```bash
git diff -U0 -- frontend/src/pages/LearningPathNew.tsx | grep -E '^[-+].*(isUnlocked|isTrackLocked|predSatisfied|firstCurrent)' || echo "CLEAN: no unlock predicate touched"
```

Expected: `CLEAN: no unlock predicate touched`. (`introComplete` legitimately
appears here as a *read* — it is passed into the helper. Its definition around
line 262 must be unchanged; confirm with
`git diff -- frontend/src/pages/LearningPathNew.tsx | grep -c 'const introComplete'` returning `0`.)

- [ ] **Step 6: Commit**

```bash
git add frontend/src/pages/LearningPathNew.tsx
git commit -m "feat(learning): level group headers go inert when un-assessed

The Explorer group header rendered bold with an open dot for a learner with
no level, reading as 'you are here' next to a padlocked Explorer lane.

Extracts the header's four state values into a pure groupHeaderState helper
(a faithful move of the existing expressions) and adds one early return: no
maturity group is passed or current while notAssessed. The Introduction
group is unaffected - it is not a maturity level and keeps keying off its
own completion.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

### Task 3: Locked lanes say what actually unlocks them

Covers the spec's locked-lane-subtitle section. Today an un-assessed learner
reads "Unlocks at Explorer" on a page that simultaneously calls them Explorer.

**Files:**
- Modify: `frontend/src/pages/LearningPathNew.tsx` (lines 682-698)

**Interfaces:**
- Consumes: `notAssessed` (Task 1), `LOCKED_UNTIL_ASSESSED` and `NEUTRAL_LOCK_COLOR` (Task 1).
- Produces: nothing.

- [ ] **Step 1: Add the branch to `subtitle` and `lockColor`**

Find lines 682-698:

```tsx
                      // Locked specifically because the Introduction isn't done
                      // yet — this message wins over the maturity "Unlocks at" note.
                      const introBlocked =
                        maturityLocked && !track.is_introduction && !introComplete
                      const done = mods.filter(m => isDone(m.id)).length
                      const next = maturityLocked ? null : firstCurrent(mods)
                      const open = openTrackId === track.id
                      const subtitle = introBlocked
                        ? 'Complete the Introduction first'
                        : maturityLocked
                          ? `Unlocks at ${requiredLevel?.name ?? track.required_level}`
                          : `${done} of ${mods.length} modules` +
                            (next ? ` · next: ${next.title}`
                              : done === mods.length && mods.length > 0 ? ' · track complete' : ' · locked')
                      const lockColor = introBlocked
                        ? INTRODUCTION_LEVEL.color
                        : (requiredLevel?.color ?? '#8A8A8A')
```

Replace with:

```tsx
                      // Locked specifically because the Introduction isn't done
                      // yet — this message wins over the maturity "Unlocks at" note.
                      const introBlocked =
                        maturityLocked && !track.is_introduction && !introComplete
                      const done = mods.filter(m => isDone(m.id)).length
                      const next = maturityLocked ? null : firstCurrent(mods)
                      const open = openTrackId === track.id
                      // Precedence: the Introduction is the one thing an
                      // un-assessed learner can act on, so it still wins. Once it
                      // is done, the real blocker is the assessment — naming a
                      // level ("Unlocks at Explorer") wrong-foots a learner who
                      // was never placed on the ladder. The group header above the
                      // lane still shows which level it belongs to.
                      const subtitle = introBlocked
                        ? 'Complete the Introduction first'
                        : notAssessed && maturityLocked
                          ? LOCKED_UNTIL_ASSESSED
                          : maturityLocked
                            ? `Unlocks at ${requiredLevel?.name ?? track.required_level}`
                            : `${done} of ${mods.length} modules` +
                              (next ? ` · next: ${next.title}`
                                : done === mods.length && mods.length > 0 ? ' · track complete' : ' · locked')
                      const lockColor = introBlocked
                        ? INTRODUCTION_LEVEL.color
                        : notAssessed
                          ? NEUTRAL_LOCK_COLOR
                          : (requiredLevel?.color ?? '#8A8A8A')
```

- [ ] **Step 2: Run the checks**

```bash
cd frontend
npm run typecheck && npm run lint && npm run build
```

Expected: all clean. If `requiredLevel` reports as unused, the assessed branch
was dropped — it must stay.

- [ ] **Step 3: Confirm the lock predicates are untouched**

```bash
git diff -U0 -- frontend/src/pages/LearningPathNew.tsx | grep -E '^[-+].*(const isUnlocked|const isTrackLocked|const introComplete|const predSatisfied|const firstCurrent)' || echo "CLEAN: no unlock predicate touched"
```

Expected: `CLEAN: no unlock predicate touched`. `maturityLocked` is a *read* of
`isTrackLocked(track)` and appearing in the diff is fine; its definition at
line 680 must be unchanged.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/LearningPathNew.tsx
git commit -m "feat(learning): locked lanes name the assessment, not a level

For a learner with no maturity level every non-Introduction lane read
'Unlocks at Explorer/Practitioner/Integrator/Multiplier' - naming a rung
they were never placed on, on a page that also called them Explorer.

While notAssessed, locked lanes read 'Take the assessment to unlock' with a
neutral accent instead of a level colour they have not earned. The level is
still visible from the group header directly above. 'Complete the
Introduction first' keeps precedence: it is the one thing they can act on.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

### Task 4: Browser verification and evidence

No frontend test runner exists in this repo, so this task IS the test. It must
produce screenshots, not assertions of success.

**Deliberate deviation from the spec's Verification section.** The spec suggests
reproducing the state with "a test account … with no `survey_responses` row".
That is not safe here: the dev and prod databases are the same Azure DB, so
creating or stripping survey rows edits live learner data. This task instead
intercepts the graph response in the browser, which drives the component from
exactly the payload the server sends an un-assessed learner and writes nothing.

**Files:**
- Create: `docs/superpowers/plans/2026-08-04-unassessed-path-signpost-verification.md` (findings + screenshot paths)
- Modify: none

**Interfaces:**
- Consumes: the finished UI from Tasks 1-3.
- Produces: nothing consumed by code.

- [ ] **Step 1: Get a login (blocking — ask the user)**

The dev and prod databases are the same Azure DB. Do NOT create or edit users,
survey rows, or lesson progress. Ask the user for disposable-account credentials
(`t@t.com` / `u@u.com` look disposable) or for them to run this walkthrough
themselves. Do not proceed by mutating data.

- [ ] **Step 2: Start the stack**

Two terminals:

```bash
cd backend && uv run poe dev      # → :8000
cd frontend && npm run dev        # → :5173, proxies /api → :8000
```

Expected: `/api/health` returns `{"status":"ok"}`.

- [ ] **Step 3: Capture the assessed baseline (the no-change proof)**

Log in and visit `/learning`. Screenshot the full page. This account has a
level, so the page must look exactly as it does on prod today: coloured level
card, a percentage in the bar value, the current level's checkpoint marked.

- [ ] **Step 4: Simulate the un-assessed state without touching data**

Intercept the graph response and blank the level, mirroring what the server
sends a learner with no survey row: `maturity_level: null`, and
`unlocked_by_maturity: false` on every non-Introduction track (the backend
returns exactly this when `caller_rank` is `None`).

With Playwright, route `**/api/learning/graph`, fetch the real response, then
fulfil with the patched body:

```js
const res = await route.fetch()
const body = await res.json()
body.maturity_level = null
for (const t of body.tracks) if (!t.is_introduction) t.unlocked_by_maturity = false
for (const m of body.modules) if (!m.is_introduction) m.unlocked_by_maturity = false
await route.fulfill({ response: res, json: body })
```

Reload `/learning`.

- [ ] **Step 5: Verify all seven sites plus the CTA**

Screenshot the full page and confirm each one:

1. Subtitle reads "Your maturity assessment decides which tracks open up… It takes about 10 minutes." — no em dashes.
2. Level card reads "Not assessed yet" / "The assessment sets your level" in ink and grey, not a level colour.
3. Bar value reads "not started yet" in grey.
4. No gradient fill in the overall bar.
5. All four checkpoints are plain grey rings; none filled, none dotted.
6. All four segment labels grey at normal weight.
7. Every maturity group header (Explorer, Practitioner, Integrator, Multiplier) has an empty ring and normal-weight name; the Introduction header still has its filled tick.
8. Every locked lane reads "Take the assessment to unlock" in grey.
9. Clicking "Take the assessment →" navigates to `/assessment`.

- [ ] **Step 6: Verify the Introduction-incomplete precedence case**

Extend the interception to also zero the Introduction module's progress
(`completed_lesson_count = 0` on modules where `is_introduction`), reload, and
confirm locked lanes revert to "Complete the Introduction first" while the CTA
stays visible.

- [ ] **Step 7: Verify the operational fix works**

Remove the interception, reload. The account has a `maturity_override`, so the
page must return to the normal assessed rendering — this is the same path as
pinning a level for the stuck learner in the admin panel.

- [ ] **Step 8: Write up the evidence**

Create `docs/superpowers/plans/2026-08-04-unassessed-path-signpost-verification.md`
with, for each of steps 3-7: what was run, what was observed, screenshot path,
and PASS/FAIL. Record failures as failures with the output — do not describe an
unverified step as verified.

- [ ] **Step 9: Commit**

```bash
git add docs/superpowers/plans/2026-08-04-unassessed-path-signpost-verification.md
git commit -m "docs: browser verification for the un-assessed signpost

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

## After the plan

Do NOT deploy. Report back to the user with the verification results and let
them decide on merge and deploy. Relevant repo discipline if they say yes:
`.\deploy.ps1` builds from the working directory, not from git, and this working
directory holds ~31 untracked files of in-progress content work — so a deploy
must be built from a fresh `git worktree` of the pushed commit
(`CLAUDE.md` → Deploy discipline).

Also worth raising with them, deliberately left out of scope by the spec: the
Introduction lesson "Setting the scene" is written as though the assessment has
already happened ("Based on the answers you gave in the maturity assessment you
were given a score…"). The signpost fixes the dead end; whether the assessment
should gate the Introduction, or that copy should stop assuming an order, is a
separate content decision.
