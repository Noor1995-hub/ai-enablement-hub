# Lesson editor: in-app QA checks, no silent overwrites, the vanishing-blocks fix: design (B5)

Issues: #146 (B5 of the admin-roles split) and #60 (quiz/card blocks vanish from unrelated live
edits), which this work closes. Builds on B4 (#145, PR #165), which also changes
`PATCH /api/admin/lessons/{id}` (lesson move via `module_id`); implement after #165 is on `main`.

## Why

- The house-style gate exists only as a CLI script (`backend/scripts/content_qa/check_draft.py`).
  An admin editing in the website gets no warnings.
- When two people save the same lesson, the later save silently overwrites the earlier one.
- Quiz and card blocks have vanished from lessons during unrelated edits, at least three times
  (#60). Manual edits keep no previous version, so a lost block means a full database restore.

Done when:
- the editor shows the same findings as `check_draft.py` on a production-shaped lesson;
- a save from an outdated copy returns 409, and that is tested;
- the #60 cause is proven by a failing test and fixed;
- `docs/content/CLAUDE.md` points to the in-app check.

## Decisions (2026-10-05, Matthias)

1. **Checks run on Save, as a soft gate.** Save runs the checks first. With no findings it saves.
   With findings it shows the list with **Save anyway** and **Keep editing**. A standalone **Check**
   button runs them without saving. Warnings never block: 66 of 91 live lessons predate the
   nested-id rule. Live as-you-type checking was rejected (noisy, a request per pause).
2. **On a conflict the editor offers "Reload their version" or "Overwrite with mine"**, naming
   who changed the lesson and when. Reload-only (loses edits) and a side-by-side merge (too much
   for a rare event) were rejected.

## 1. In-app house-style checks

**Pure module `backend/src/services/lesson_qa.py`.** A port of `check_draft.py`'s checks, reusing
`validate_content_blocks` and `check_house_style` from `content_blocks_validation.py`:

- forbidden punctuation (em dash, en dash, ellipsis) in every text field;
- duplicate block / card / question / step / item ids;
- a quiz's correct answer being the unique longest option;
- correct-answer positions that never vary within a quiz;
- a "Check your understanding" heading immediately before every quiz;
- more than two bold spans in one text field (bullet lead-ins excluded, as in the script);
- sort `bucketId` / predict `correctOptionId` that don't resolve;
- schema errors from `validate_content_blocks`. An empty image `blob_path` is reported as
  `info` ("expected": an image placeholder awaiting upload), exactly as the script's
  `EXPECTED` bucket does.

`check_lesson(blocks) -> list[Finding]`, where
`Finding = {severity: "warning" | "info", block_index: int | None, where: str, message: str}`
(`where` reads like "block 4 · paragraph"). The script's fail/warn split maps to `warning`.
The bold-count warning stays a warning; its EXPECTED bucket becomes `info`.

**`check_draft.py` becomes a thin CLI over `lesson_qa`**, keeping its arguments, output and
`--uuids`. A parity test runs both on one production-shaped fixture, so the CLI and the website
can never disagree.

**`POST /api/admin/lessons/{lesson_id}/check`** (power admin). The body is
`{content_blocks}`: the editor's **unsaved** blocks. It returns `{findings}`, writes nothing, and
gives 404 for an unknown lesson. It has a `_MATRIX` row.

**Editor** (`frontend/src/components/lesson/LessonEditor.tsx` and the MDX pane in
`frontend/src/pages/LessonPage.tsx`):

- **Save** calls `/check` first. With no `warning` findings it saves straight away (`info` alone
  doesn't stop it). Otherwise it opens one panel listing the findings, grouped by block, with
  **Save anyway** and **Keep editing**.
- A **Check** button runs the same call and shows the panel without a save button.
- The same panel serves the MDX "Save as blocks" and adds the block-removal warning (section 3).

## 2. No silent overwrites

**Migration (expand-first):**
- `lessons.updated_at timestamptz NOT NULL`, backfilled to `created_at`, with server default
  `now()`;
- `lessons.updated_by uuid NULL`, an FK to `users.id` with `ON DELETE SET NULL`, indexed.

The running image never reads or writes them, so it keeps working.

**Every lesson write stamps both** (`updated_by` = the caller):
- `PATCH /api/admin/lessons/{id}` (content, title, and B4's move);
- the AI-proposal approval in `content_improvement_service.py`. It already refuses a stale proposal
  by comparing `base_blocks`, and now it also stamps.

Lesson create sets both at insert. A reorder (sort_order only) does not stamp: it's not a content
edit and must not invalidate an open editor.

**`PATCH /api/admin/lessons/{id}` takes an optional `expected_updated_at`:**
- If it's present and differs from the stored `updated_at` → **409** with code `lesson_changed` and
  `{updated_at, updated_by_name}` in the error body (`updated_by_name` is null when unknown).
- If it's absent, the save proceeds unchecked. That's **transitional**, so the frontend that's
  deployed during the deploy window keeps working; the new editor always sends it. Making it
  required is a follow-up.
- Comparison is exact on the stored timestamp (microsecond precision, ISO 8601 on the wire).

**Reads:** `GET /api/lessons/{id}` (`LessonDetailResponse`) and the PATCH response (`LessonOut`)
gain `updated_at`. The editor keeps the base it loaded or last saved.

**Editor on a 409:** "*Aaron Neuville* changed this lesson at 14:32 while you were editing."
- **Reload their version** fetches the lesson, replacing the editor's state (unsaved edits are
  discarded; the dialog says so).
- **Overwrite with mine** re-sends the same save with `expected_updated_at` set to the
  conflicting `updated_at` from the 409. That's a deliberate overwrite, and it's still guarded
  against a *third* change in between.

## 3. Fix #60: blocks vanishing on the MDX round trip

**Cause (by reading the code; the first implementation step proves it with a failing test before any fix):**
- `frontend/src/lib/blocksToMdx.ts` writes `<Quiz data='…json…' />` and
  `<Cards data='…json…' />` inside **single quotes**.
- `frontend/src/lib/mdxParser.ts` matches `data='([^']*)'`, so any apostrophe in quiz or card
  text ("don't", "it's") truncates the JSON and the block is dropped.
- The parser's splitter `<(…)\s[^>]*?\/>` also stops at the first `>` inside the data.
- `question` blocks are serialised as an empty string, so they're always lost.

Opening a lesson in MDX mode, fixing a typo and pressing "Save as blocks" therefore deletes those
blocks. That matches "vanished during an unrelated edit".

**Fix:**
- `blocksToMdx` writes `Cards`, `Quiz` and a new `Question` tag with the same encoding
  `Interactive` and `TryItYourself` already use (`encodeBlock`).
- The parser decodes that form and still accepts the old `data='…'` and `` data={`…`} `` forms,
  so pasted older MDX keeps working.
- The splitter no longer ends a tag at a `>` inside an attribute value.

**Proof:** a round-trip suite over **every block type** in `src/types/contentBlocks.ts`, each text
field carrying apostrophes, double quotes, `>`, `<`, backticks, newlines and emoji. It asserts
`parseMdxToBlocks(blocksToMdx(blocks))` equals `blocks` with ids ignored, and repeats on a
production-shaped lesson fixture. A guard test fails when a block type is added to the union
without round-trip coverage.

**Safety net:** before the MDX "Save as blocks", the editor compares block counts per type between
the lesson as loaded and the parsed result. If the save would remove any, the Save panel
(section 1) leads with "This removes 1 quiz and 1 card group", alongside the house-style
findings: one panel, one decision.

The analysis goes into `docs/content/review-process-technical-notes.md`, where #60 was first
recorded, and the PR closes #60.

## Docs

- `docs/content/CLAUDE.md`: the in-app **Check** (and Save's soft gate) is the drafting gate for
  edits in the website; `check_draft.py` remains for drafts written outside it, and both run the
  same module.
- `docs/content/authoring-guide.md` §11:
  - drop the "**`lessons` has no `updated_at` column**" bullet (no longer true);
  - in the Concurrency bullet, note that the editor now refuses a stale save and offers
    Reload / Overwrite. Scripts writing lessons directly in SQL still bypass it, so the "don't
    write while he edits" rule stands for them.
- `docs/feature-index.md` entry.

## Testing

- **Backend:**
  - `lesson_qa` unit tests, one per check, plus the empty-`blob_path`-is-info case;
  - the parity test against `check_draft.py` on one fixture;
  - `/check`: power only, writes nothing (the lesson is unchanged after), 404 unknown lesson;
  - PATCH with a stale `expected_updated_at` → 409 `lesson_changed` with name and time; a fresh one
    → 200 that stamps `updated_at` and `updated_by`; an omitted one → 200;
  - the approval path stamps both columns;
  - a reorder does not stamp;
  - `_MATRIX` row for `/check`;
  - CI's `migrations` job for the upgrade, `alembic check` and round-trip.
- **Frontend:**
  - the round-trip suite and the union-coverage guard (section 3);
  - editor tests: Save with no findings saves directly; findings open the panel; **Save anyway**
    saves; **Keep editing** doesn't;
  - a 409 shows the name and time, and both buttons do what they say;
  - an MDX save that drops a quiz shows the removal warning.

## Out of scope

- Making `expected_updated_at` required (the release after this one).
- Lesson version history (#49, dropped in favour of fixing #60's cause).
- Live as-you-type checking.
- Running these checks on AI proposals: the pipeline has its own validator.
- Conflict protection for scripts writing lessons straight to the database
  (`db/content_tools/`, SQL).

## Risks

- **The parser change touches every MDX import.** The old forms stay accepted, and the round-trip
  suite plus the fixture are the evidence.
- **Exact timestamp comparison:** a client that rounds the value would always conflict. The editor
  echoes the server's string verbatim, and a test pins that the PATCH response's `updated_at`
  round-trips into the next request.
- **The transitional optional field** means a stale tab with an old frontend can still overwrite,
  until the follow-up makes it required.
