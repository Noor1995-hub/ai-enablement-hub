# Content model & editorial reference

This folder documents the **learning content** (tracks / modules / lessons) — its data model,
how it's gated, and the editorial reference used when reviewing it.

> **Important:** the content itself is **not in this repo.** It lives in the Azure Postgres DB
> and is edited through the admin UI (`PATCH /api/admin/lessons/{id}`), which writes straight to
> prod. This folder is the *model and process* documentation, not the content.

## Files here

- **[content-review-lens.md](content-review-lens.md)** — the reusable content-quality checklist
  (voice/tone tells, structural patterns, factual-accuracy traps). Apply to any track.
- **[general-i-ii-style-guide.md](general-i-ii-style-guide.md)** — the General I/II-specific
  style guide produced by applying the lens to those tracks.
- **[review-process-technical-notes.md](review-process-technical-notes.md)** — operational
  notes for editing live content safely (fetch-before-every-edit, block-id churn, the
  vanishing-quiz bug, and the **build-from-clean-checkout** deploy rule).

## Data model (source of truth: code, not this doc)

- **Hierarchy:** `track → module → lesson`. A lesson's body is a JSONB array of typed
  `content_blocks` (see `frontend/src/types/contentBlocks.ts` for the block union).
- **Track kinds:** `kind ∈ {general, tool}` plus the special **Introduction** gate. "General"
  tracks are the tool-agnostic path (General I / II / III); "tool" tracks each cover one tool
  (Copilot, Claude, Confluence, Lovable, Obsidian, Power Automate/Apps, …).
- **Maturity ladder** (`backend/src/core/constants.py::LEVEL_ORDER`):
  `explore → practitioner → integrator → multiplier`. The scorer only ever *assigns* the first
  three; `multiplier` is admin-pin/aspirational. Each track has a `required_level`; a track's
  modules stay maturity-locked until the learner's effective level reaches it (see the
  "Locking, prerequisites & preview" section of the root `CLAUDE.md`).
- **Assignment** (`user_tracks` / `user_modules` / `user_lessons`): per-learner visibility
  filter, **not** access control. Assigning a module does not auto-assign its lessons. Survey
  completion auto-assigns via `SurveyService._seed_assignments`.

## Getting the authoritative *current* lineup

This doc deliberately does **not** enumerate every module/lesson — that drifts the moment
content is edited in the admin UI. For the live inventory:

- Query the Azure DB directly, or run `backend/scripts/content_qa/fetch_scope.py` /
  `backup_live.py` (read the live tracks/modules/lessons).
- `db/baseline/data/lessons.json` is a **historical** pre-cutover snapshot — useful for
  structure, **not** current content.

## Notable structural changes (memory-derived — verify against the DB before relying on IDs)

These are content-only DB edits (no migration, no deploy) unless noted:

- **2026-07-17 — "What AI is" rewrite** (General I) to house voice; live. 3 placeholder diagrams
  awaiting art.
- **2026-07-19 — General II rewrites**: "Integrating AI into your work" (3 lessons),
  "From foundation to tools" closer, and the "Apply it" capstone (callback-driven,
  `try_it_yourself`) — all rewritten to house style; live. Placeholder diagrams outstanding.
- **2026-07-20 — Tips & Tricks module** added to **General II**, inserted between "Apply it" and
  "From foundation to tools" (finale prereq rewired to Tips & Tricks). 3 lessons
  (voice / challenge / plan-act-review), no quizzes, `try_it_yourself`-driven; assigned to the
  24 learners who had the old starter lesson. 3 placeholder diagrams outstanding.
- **2026-07-20 — "For Developers" split.** 5 of its 6 modules were redistributed into 3 **new
  multiplier-level tracks**: **General III** (Agentic engineering practices), **Copilot II**
  (Get started with GitHub Copilot, Copilot Studio), **Claude II** (Claude Code in depth →
  Building on Claude → Managed Agents [empty placeholder]). "For Developers" now holds only the
  **Capstone** module. **The multiplier level now has 4 tracks, not just For Developers** — any
  older doc calling For Developers the sole multiplier track is stale on that point.
- **2026-07-20 — Content-QA sweep** across the 9 admin-assigned tracks: em-dashes → 0, en-GB
  spelling, 17 quizzes fixed, 11 quiz→interactive conversions, capstone cross-refs. Tooling in
  `backend/scripts/content_qa/`. One factual contradiction (Scheduled-tasks facts) was flagged
  for Matthias.

**Outstanding across the recent content work:** several lessons ship a **placeholder image
block** (empty `blob_path`) whose alt text is the paste-ready diagram-generator prompt — art
must be generated and uploaded via the editor's "Choose image…" before those render as real
figures.
