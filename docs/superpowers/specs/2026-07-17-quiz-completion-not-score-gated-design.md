# Quiz completion no longer gated on score

**Date:** 2026-07-17
**Scope:** frontend-only, one component

## Problem

Today a lesson quiz blocks completion until the learner answers **every question
correctly**. `QuizBlock` only fires its `onComplete` callback when the results screen is
reached *and* `allCorrect` is true; that callback is the only thing that flips `quizDone` in
`LessonPage`, which is the only thing that reveals the "Mark as complete →" button. On a
partial score the results screen offers only a "Retake quiz" button and the copy "Retake the
quiz to continue" — there is no way forward short of a perfect score.

This is a worse experience than intended. The quiz should stay obligatory (you must go
through it), but a wrong answer should not trap the learner in the lesson.

## Desired behavior

- The quiz remains **obligatory**: a lesson containing a quiz still shows "Complete the quiz
  above to continue" until the learner reaches the results screen (i.e. has answered every
  question once).
- Reaching the results screen unlocks completion **regardless of score**. 2/5 unlocks
  "Mark as complete →" exactly as 5/5 does.
- "Retake quiz" stays available on a partial score, but is now framed as an **optional** way
  to improve, not a requirement.

## Changes

Both edits are in `frontend/src/components/lesson/blocks/QuizBlock.tsx`.

### 1. Fire `onComplete` on results, regardless of score

The completion effect drops its `allCorrect` guard:

```js
useEffect(() => {
  if (phase === 'results') onComplete?.()
}, [phase, onComplete])
```

This flips `quizDone` in `LessonPage` the moment results are shown, revealing the existing
"Mark as complete →" button. No change is needed in `LessonPage` — the per-lesson state
reset and the stable `useCallback` `onQuizComplete` identity
(`LessonPage.tsx` lines ~106-110) remain load-bearing for the same navigation reason and are
untouched.

### 2. Rework the partial-score results screen

- **All-correct case:** unchanged. Green score, "You answered everything correctly. Scroll
  down to continue.", green "✓ All correct — scroll down to continue" footer, no retake
  button.
- **Partial case:**
  - Score number rendered in **amber** (`#B45309`, adjustable) instead of red `#C42828` —
    a partial score is now a passing outcome, so it warns rather than alarms.
  - Copy changes from the blocking "You got {score} out of {n} right. Retake the quiz to
    continue." to a non-blocking message, e.g. "You got {score} out of {n} right. You can
    continue below, or retake the quiz to improve your score."
  - Keep the "Retake quiz" button as an optional action.
  - Add a "scroll down to continue" affordance so the path forward is discoverable (parallel
    to the all-correct footer).
- **Per-question review list** (green ✓ / red ✗ per item): unchanged — it still correctly
  shows which individual answers were right or wrong.

## Explicitly out of scope / unchanged

- **Backend:** `PUT /api/lessons/{id}/progress` already accepts completion regardless of
  quiz score. No API, schema, migration, or test changes on the backend.
- **Multi-quiz lessons:** a lesson with more than one quiz already unlocks completion when
  the first quiz reaches results (single `quizDone` boolean). This design does not change
  that pre-existing behavior.
- **Locking / assignment / access control:** untouched.

## Verification

- Frontend checks: `npm run typecheck && npm run lint && npm run build` (inside `frontend/`).
- Manual: open a lesson with a quiz; confirm "Mark as complete →" stays hidden until results;
  answer with at least one wrong; confirm results show amber score + non-blocking copy +
  retake button + a discoverable way to continue; confirm "Mark as complete →" now appears
  and completes the lesson; confirm retaking still works and does not re-lock.
