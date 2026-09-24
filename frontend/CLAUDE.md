# Frontend — scoped guide

Loaded when working under `frontend/`. The root `CLAUDE.md` rules still apply — above all **the
one-database rule** and "Verifying without touching live data" (never verify a learner-facing
change by creating users, surveys or progress).

## Checks (what CI runs)

`npm run typecheck && npm run lint && npm test && npm run build`

- Tests: Vitest + Testing Library + jsdom, `*.test.ts(x)` next to the code, setup in
  `src/test/setup.ts`. Logic worth testing goes into a pure module in `src/lib/` first (the
  pattern of `lib/learningPathLocks.ts`), not into a page component.
- Dev: `npm run dev` (→ :5173, proxies `/api` → :8000). The backend behind it is `poe dev`, which
  talks to the live DB — see `backend/CLAUDE.md`.

## API types

After a backend contract change, run `npm run gen:api` and commit `src/api/schema.d.ts`. It
imports the app via `backend/scripts/export_openapi.py` and **never starts the backend**. CI
regenerates the file on every PR and fails when the committed one is stale.

## Rules

1. **CSS zoom 1.25 on `:root`.** Rect-based positioning must compensate via `getRectZoomFactor`
   (`lib/uiZoom.ts`) — rects are scaled in Chrome/Edge/Firefox, not in Safari.
2. **The learning-path unlock rule** lives only in `lib/learningPathLocks.ts` (pure, tested). It is
   a visibility rule, not access control — see root `CLAUDE.md` "Locking". Change it there, with
   a test per rule.
3. **Lesson blocks** are the union in `src/types/contentBlocks.ts`; the renderer map
   (`components/lesson/LessonView.tsx`), editor map (`LessonEditor.tsx`), `BLOCK_LABELS` and
   `BLOCK_FACTORIES` (`lib/contentBlocks.ts`) must all cover a new type —
   `lib/contentBlocks.test.tsx` checks it. `content_blocks` is JSONB: tolerate unknown types.
4. **No `window.confirm`** for destructive actions — use in-app confirmation UI (modal or a
   two-step button).
5. The admin panel is `src/pages/admin2/`; its visual contract is the pinned mockups in
   `docs/design-prototypes/` (referenced by path from source — do not move them).
6. Deferred on purpose (issue #45): TypeScript 7, ESLint 10, plugin-react 6 and react-router 7 are
   one planned upgrade, not Dependabot merges.
