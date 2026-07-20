# Content QA Review — all lessons assigned to `admin admin`

**Date:** 2026-07-20
**Author:** Matthias + Claude (brainstormed)
**Status:** design, awaiting review before Phase 1

## Purpose

Run a structured quality-assurance pass over **every module and lesson currently assigned to
the `admin admin` account** (`a@a.com`, `587f5667-2ddc-4b95-827c-09bcb92c5b7c`). This account
has the full curriculum assigned, so the scope is effectively the whole live hub: **13 tracks,
38 modules, 108 lessons** (280 quiz questions, 20 interactive blocks).

Two review workstreams, run over one shared read of the content:

- **A — Copy & layout:** spelling/typos, British-English consistency, and spacing/heading
  uniformity.
- **B — Quiz review:** whether each quiz adds value, whether ~3 questions could be fewer, and
  whether a quiz should become a `predict`/`sort`/`spot-the-flaw` interactive for variety.

This phase produces **review reports only.** No lesson content is edited here. Applying any
finding is a separate, separately-approved phase (house rule: draft → confirm → apply, never
blind-edit live content).

## The standard

The target standard is the existing house authoring guide
(`scratch_review/claude_cowork/authoring_guide.md`), applied **hub-wide** — older tool tracks
likely predate it, and measuring them against it is exactly what defines "uniform." The
relevant, checkable conventions:

- **Spelling:** British/EU — colour, organisation, summarise, behaviour, and **"Artefact"**;
  **"interface"** not "surface" for Chat/Cowork/Code/Design.
- **Punctuation (hard rule):** no em dashes (—), en dashes (–) or ellipsis (…) anywhere in a
  text field.
- **Spacing:** `whitespace` is `md` size, used as a separator, usually immediately before a
  closing quiz.
- **Heading before quiz:** a `heading` "Check your understanding" immediately precedes each
  quiz (Matthias's convention, confirmed 2026-07-17).
- **Quiz:** optional per lesson (skip on light/curiosity/decision lessons); when used → 3
  questions, 3–4 options, a teaching explanation each; **the correct answer must never be the
  longest option** (a confirmed systemic bug — ~87% of questions violate this); vary which
  position is correct; distractors must be plausible; a `sort` interactive can *replace* a
  quiz on a decision lesson.

Where a convention itself looks wrong or contested for a given lesson, it is flagged for
Matthias's decision rather than silently marked as a deviation (the guide is "draft v1", and
"I wonder if…" findings are discussion prompts, not instructions — per
`content_review_lens.md`).

The reusable review lens (`scratch_review/content_review_lens.md`) and its 4-bucket triage
(wording / structural / factual / cross-lesson-dedup) apply on top of the mechanical checks.

## Architecture

One data pull feeds two analyses. Split by *what tool fits*, not by workstream — much of A is
mechanical and needs no LLM.

```
Live Azure DB
   │  (one read-only fetch, all 108 assigned lessons)
   ▼
lessons snapshot JSON  (track → module → lesson → sort_order → content_blocks)
   │
   ├── Phase 1: deterministic sweeps (scripts, run once, centrally)
   │      → deterministic_findings.json  (per-lesson: punctuation, americanisms,
   │        spacing/heading conformance, quiz answer-length/position stats)
   │
   └── Phase 2: editorial workflow fan-out (one agent per module, ~38)
          input per agent: its module's lessons + the standard + Phase-1
                            findings for those lessons (so it adds judgement,
                            not re-finds mechanical hits)
          → structured findings per module (copy/layout + quiz assessments)
   │
   ▼
Synthesis → two reports in scratch_review/:
   copy_layout_review_2026-07-20.md
   quiz_review_2026-07-20.md
```

### Phase 0 — Shared data pull

A read-only script (asyncpg, pattern of `backend/scripts/read_foundation_to_tools.py`) joins
`user_lessons → lessons → modules → tracks` for the admin user and dumps, ordered by
track/module/lesson `sort_order`:

```
{ track_name, track_level, module_title, module_id, lesson_id, lesson_title,
  lesson_sort_order, content_blocks }
```

Written to the scratchpad as one JSON, plus one per-module JSON file (so Phase-2 agents each
Read a small file rather than receiving huge prompts). This is a *snapshot for reporting*; the
fetch-fresh-before-every-edit discipline applies at apply time, not here.

### Phase 1 — Deterministic sweeps

Pure functions over the snapshot JSON, walking every text-bearing field of every block
(`text`, `prompt`, `q`, `options[]`, `explanation`, card `title`/`body`, `caption`, `alt`,
interactive `reason`/`label`, try-it-yourself fields):

1. **Punctuation ban** — locate `—`, `–`, `…`; report lesson + block + exact surrounding text.
2. **British-English scan** — regex list of common Americanisms (`organiz`, `color`,
   `behavior`, `customiz`, `personaliz`, `analyz`, `\bcenter\b`, `catalog\b`, `favorite`,
   `traveler`, `modeling`, `-ize`/`-ization` endings, `license` as a verb, `Artifact`) plus
   `\bsurface\b` in the four chat/tool contexts. Per-lesson hit list with the matched word in
   context. (Known-good en-GB words like "organisation", "summarise", "Artefact" must *not*
   fire — the regex targets the American forms only.)
3. **Spacing/heading conformance** — for every `quiz` block: is the immediately-preceding
   non-whitespace block a `heading` reading "Check your understanding"? Is there a
   `whitespace(md)` between them (or directly before the quiz)? Flag: missing heading, missing
   separator, `whitespace` of size other than `md`, `whitespace` not adjacent to a quiz, and
   the whitespace-count distribution per lesson.
4. **Quiz data checks** — per quiz question: is the correct option the (unique) longest? record
   the correct option's position; count options (flag ≠ 3–4); count questions per quiz (flag
   ≠ 3 as a "fewer?" candidate for Phase 2). Aggregate per track and hub-wide.

Output: `deterministic_findings.json` keyed by lesson_id, plus a short human summary. These are
high-confidence, exhaustive findings that Phase 2 does **not** need to re-discover.

### Phase 2 — Editorial workflow fan-out

A `Workflow` (explicit opt-in given) with **one agent per module** (~38). Rationale for module
granularity: quiz *variety* is a module-level property — an agent seeing a whole module can
recommend a *mix* (not "convert every quiz to predict"). `parallel`/`pipeline` over the module
list, capped by the runtime's concurrency limit.

Each agent receives (via prompt + a Read of its per-module JSON):
- its module's lessons (all blocks),
- the standard (the conventions above, inline),
- the Phase-1 deterministic findings for those lessons (so it focuses on judgement).

Each agent returns **structured output** (schema-validated) with two arrays:

- `copy_layout[]` — `{ lesson_id, lesson_title, block_locator (exact quote), issue_type
  (typo|en-gb|layout|spacing|opener-weight), severity, quote, suggestion, triage_bucket }`
  — residual typos, subtle en-GB the grep misses, skipped heading levels, empty blocks,
  opener-card weight (guide §4), and any spacing oddity beyond the mechanical check.
- `quiz[]` — one entry per quiz in the module: `{ lesson_id, lesson_title, verdict
  (keep|trim-questions|convert-to-interactive|fix-quality|drop), value_rationale,
  suggested_question_count, suggested_interactive_mode (predict|sort|spot_the_flaw|none),
  variety_note, quality_flags[] }` — value-add judgement, the 3→fewer question call,
  the convert-for-variety call with a module-level variety view, and distractor/quality notes.

A lightweight completeness check (one extra agent, or a synthesis review) confirms every module
was covered and flags any module the fan-out skipped.

### Synthesis — two reports

Assemble from Phase-1 JSON + Phase-2 structured returns into two plain-markdown files in
`scratch_review/` (not Artifacts — rendering has been unreliable on this project):

- **`copy_layout_review_2026-07-20.md`** — grouped by track → module → lesson; every finding
  carries an **exact quote**, the deviation, the triage bucket, and a recommendation. Mechanical
  (Phase 1) and editorial (Phase 2) findings merged per lesson, deterministic ones marked as
  high-confidence.
- **`quiz_review_2026-07-20.md`** — per quiz: verdict + reasoning; a per-module variety summary;
  a hub-wide section for the systemic patterns (answer-length bias, position skew, question
  counts).

Each report ends with a triaged action list so the follow-up apply phase has a clear worklist.

## Out of scope (this phase)

- **Applying any fix.** Edits to live content are a separate phase, each write preceded by a
  fresh fetch (block ids churn on every admin-UI re-save; a quiz/card_group can silently vanish
  from an unrelated live edit — treat any missing block as a bug, not a decision).
- **Lessons not assigned to `admin admin`** (there are none of consequence — the account has the
  full curriculum — but any unassigned/orphan lesson is not fetched).
- **Deep cross-lesson dedup** (review-lens §5 bucket 4): flagged where obvious, but a full
  read-the-sequence-as-one-arc dedup pass is a candidate follow-up, not part of this pass.
- **Factual-accuracy verification** beyond flagging: any factual claim a reviewer doubts is
  logged "please verify", not resolved here.

## Success criteria

- Every one of the 108 assigned lessons appears in both reports (or is explicitly noted as
  clean).
- Phase-1 mechanical findings are exhaustive for their known patterns (punctuation, listed
  Americanisms, quiz answer-length/position, spacing/heading adjacency).
- Every finding is actionable: exact quote or block locator, the specific deviation, and a
  recommendation.
- Quiz verdicts include a module-level variety view, not just isolated per-quiz calls.
- Reports are plain markdown in `scratch_review/`; nothing in the live DB is touched.

## Execution notes

- Phase 0 + Phase 1 are read-only and cheap — run directly.
- Phase 2 is the `Workflow`; module-granular fan-out; structured output per agent.
- Follow-up apply phase (not designed here) will re-fetch each lesson fresh, edit via
  `PATCH /api/admin/lessons/{id}` or the admin UI, and deploy from a clean worktree if a deploy
  is needed.
