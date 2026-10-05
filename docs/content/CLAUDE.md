# Content authoring — scoped guide

Loaded when working under `docs/content/`. **The lessons are not in this repo** — they live in the
production database and are edited through the admin UI (`PATCH /api/admin/lessons/{id}`), which
writes straight to what learners see. This folder is the model and the process.

## Before you write a lesson

1. Read `authoring-guide.md` in full, then read finished lessons written by Matthias (the
   "Claude chat" modules) in full. The style guides alone do not carry the register — drafts
   built only from the rules have shipped the guide's own "before" example three times.
2. Apply `content-review-lens.md`; for General I/II also `general-i-ii-style-guide.md`.
3. Gate every draft with `backend/scripts/content_qa/check_draft.py` before it goes near the DB
   — it catches, among others, the quiz answer-length bias every time. In the website the same
   checks run on **Save** and on the editor's **Check** button (`backend/src/services/lesson_qa.py`);
   `check_draft.py` is the CLI over that module, for drafts written outside the editor.

## House rules that get broken most

- Never assert a fact about the learner's situation or history; say what is on the screen and
  what the tool does. Name the literal thing: where a record lives, what the button is called.
- No imported metaphors as organising devices, no recap openers, no forward teases.
- In a tool-agnostic (General) track: open tool-neutral, then split into a Claude and a Copilot
  section — if that is not possible, it does not belong in the general track.

## Editing live content safely

`review-process-technical-notes.md`: fetch before every edit, block-id churn, the vanishing-quiz
bug. Any tightening of block validation must first be censused against real lessons (66 of 91
lacked nested ids when that was last checked). The AI system prompts that shape generated content
(`backend/prompts/house_style.md`, …) are runtime assets, changed by PR only.
