# Review Process — Technical Notes

Split out of `content-review-lens.md` on 2026-07-17: that file is scoped to lesson content
quality specifically. This file is the operational/tooling side of running a live review —
useful for whoever (human or agent) is doing the DB-editing mechanics, not part of the
content checklist itself.

---

- **Fetch fresh before every single edit, no exceptions** — not just at the start of a
  session. The reviewer edits concurrently, sometimes mid-conversation, and a locator-based
  edit against stale text either fails loudly (harmless) or, worse, could match the wrong
  thing. Confirmed necessary repeatedly across the Copilot track review (2026-07-16/17):
  dozens of fetches, never once skipped, and it caught real drift every time.
- **Block ids churn on every admin-UI re-save.** Confirmed repeatedly, not just once. Never
  hold onto an id from a previous turn; match by locator text against a fresh fetch, every
  time.
- **A quiz block (or a card_group) can silently vanish from an unrelated live edit.**
  Confirmed 3+ times in one session, across two different lessons, always framed by the human
  reviewer as *not* intentional ("must be something with the editor"). Treat any missing quiz
  as a structural bug report, not a content decision — ask explicitly whether it was
  deliberate before touching anything, but expect the answer to be "no." Root cause was never
  found in the Copilot track round (deliberately parked, not solved) — worth a dedicated
  investigation before it recurs on another track, since patching it lesson-by-lesson doesn't
  scale.
  **Found and fixed (2026-10-05, #60, B5):** the MDX mode. `blocksToMdx` wrote quiz and card data
  as raw JSON inside single quotes (`<Quiz data='…' />`), and the parser read up to the first
  apostrophe, so any MDX "Save as blocks" on a lesson whose quiz or card text contained one
  ("don't", "it's") dropped those blocks; `question` blocks were never written at all. All three
  are now base64-encoded like the interactive blocks, the old form is still read, and
  `frontend/src/lib/mdxRoundTrip.test.ts` round-trips every block type. The editor also warns
  ("This removes 1 quiz.") before any save that would remove blocks.
- **Production deploys must build from a clean checkout, never the live working directory.**
  A review session accumulates other people's concurrent uncommitted work in the same repo
  (draft reorganizations, untracked exploratory files). `az acr build` (or any
  build-from-source-tree deploy) uploads whatever is physically on disk, tracked or not.
  Commit only the specific file(s) the fix touches (`git commit <pathspec>`, never a blanket
  `git add -A`), push, then build from a fresh `git worktree` of that pushed commit — never
  from the same directory the reviewer is actively working in. On Windows, use a short
  worktree path near the drive root (`C:\tmp\...`) with `-c core.longpaths=true`, since deep
  temp paths combined with this repo's long filenames exceed MAX_PATH.
