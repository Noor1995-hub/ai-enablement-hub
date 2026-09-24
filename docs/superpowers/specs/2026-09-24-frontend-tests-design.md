# Frontend tests — Vitest + Testing Library (way-of-working 2.1)

**Date:** 2026-09-24 · **Issue:** #46 · **Source:** `docs/reviews/2026-09-17/WAY-OF-WORKING-COMPARISON-2026-09-17.md` §5 row 2.1

## Problem

The frontend has zero tests. The rules that decide what a learner can open — the module unlock
rule in `LearningPathNew.tsx` — live as closures inside a 1,278-line page component, so they
cannot be tested at all, and CLAUDE.md's "Locking" section is the only statement of what they do.
Every change to that page is verified by eye.

## Scope

1. **Test runner.** Vitest 5 (supports our Vite 6.4) with jsdom, `@testing-library/react` and
   `@testing-library/jest-dom`. `npm test` runs once (`vitest run`); tests live next to the code
   as `*.test.ts(x)`. The `frontend` CI job runs `npm test` after lint, so the required check
   covers it — no ruleset change.
2. **Extract the unlock rule** into `src/lib/learningPathLocks.ts` as pure functions over an
   explicit context: `isModuleDone`, `isIntroComplete`, `isPrereqSatisfied`, `isModuleUnlocked`.
   `LearningPathNew.tsx` builds the context from its state and calls them. **No behaviour
   change**: the function bodies are the current closures moved verbatim, with free variables
   turned into context fields.
3. **Tests for the unlock rule**, one case per rule in CLAUDE.md "Locking, prerequisites &
   preview": admin and `user+` bypass; `unlocked_by_maturity === false` locks; the Introduction
   gate (and an empty Introduction leaves it open); below-level tracks are freely reviewable;
   no prerequisites ⇒ unlocked; same-level prerequisite gates until done; a prerequisite in a
   strictly lower level is satisfied by maturity alone; and the accepted quirk that a
   prerequisite module with 0 lessons locks its dependents forever.
4. **`getRectZoomFactor`** (`lib/uiZoom.ts`): 1 with no zoom, the measured ratio when rects are
   scaled, 1 when the probe measures 0 (jsdom, Safari-like).
5. **Content-block registration**: the renderer map (`LessonView.tsx`), editor map
   (`LessonEditor.tsx`), `BLOCK_LABELS` and `BLOCK_FACTORIES` cover the same set of types; every
   factory-built block renders in `LessonView` without throwing.

## Out of scope

Page-level rendering tests of `LearningPathNew`, Playwright (2.10), coverage thresholds for the
frontend (revisit once there is a body of tests).

## Verification

- The extraction diff shows the logic moved, not rewritten (reviewed side by side).
- `npm test`, `typecheck`, `lint`, `build` green locally and in CI.
- The unlock tests would fail if any rule were dropped (each case asserts the opposite outcome
  of its neighbour).
