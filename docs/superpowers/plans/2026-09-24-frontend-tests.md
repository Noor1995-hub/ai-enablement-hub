# Plan — frontend tests (spec `../specs/2026-09-24-frontend-tests-design.md`, issue #46)

**Status: done 2026-09-24 — all four tasks and the final review shipped in PR #58 (squash
`c264dad`).** The review's two should-fix findings (render test too weak, check order unpinned)
were fixed before merge; its Docker-stage install nit was accepted.

One PR, four commits, each green on its own.

1. **Runner.** `npm i -D vitest jsdom @testing-library/react @testing-library/dom
   @testing-library/jest-dom`; `test` block in `vite.config.ts` (`environment: 'jsdom'`,
   `setupFiles: ['src/test/setup.ts']`); `src/test/setup.ts` imports jest-dom matchers and runs
   `cleanup` after each test; `"test": "vitest run"`; CI `frontend` job runs `npm test`. Check:
   `npm test` passes with a trivial test, typecheck/lint/build unaffected.
2. **Extract `lib/learningPathLocks.ts`.** Move `isDone`, `introComplete`, `predSatisfied`,
   `isUnlocked` bodies verbatim; context `{ canBypassLocks, moduleById, modulesByTrack, tracks,
   prereqMap, moduleLevelRank, levelIdx }`. Page builds the context once per render (memoised)
   and calls the functions. Check: typecheck, lint, build; diff reviewed side by side.
3. **Tests.** `learningPathLocks.test.ts` (the spec's rule list), `uiZoom.test.ts`,
   `contentBlocks.test.tsx` (map parity + render every factory block).
4. **Docs.** CLAUDE.md "How to run & verify" frontend checks gain `npm test`; CONTRIBUTING step 3
   likewise; PR template frontend line; the Locking section points at `learningPathLocks.ts`.

Final: whole-branch review subagent, then PR with `Closes #46`.
