# Copilot Track Enrichment — Plan

**Purpose:** self-contained plan for enriching the Copilot track's content using NotebookLM research gathered 2026-07-16, while preserving the track's existing voice. Written so a fresh session can pick this up with no prior conversation context.

## Goal

Enrich the Copilot track (part of the AI Enablement Hub learning path) using everything gathered from NotebookLM research plus direct review of the live content, without touching content that already works. **Primary focus: gap-fill.** Secondary: light enrichment, only where a gap is genuine. Do not rewrite, restructure, or "improve" lessons that are already strong just because new source material touches the same topic.

## Context a fresh session needs

- Live product: `ai-enablement-hub-rebuild` (FastAPI + React on Azure, Postgres). Content lives in the `lessons` table (`content_blocks` JSONB), plus `modules` and `tracks`. Read the repo's own `CLAUDE.md` first for full architecture/deploy/DB detail — it's authoritative and changes independently of this file.
- Local reference snapshot: `db/baseline/data/{tracks,modules,lessons,module_prerequisites}.json` — dated roughly 2026-07-07, may lag live prod (the repo's own CLAUDE.md notes several undocumented redeploys since). Treat as a reference to plan from, but **verify against live prod before actually applying anything.**
- Copilot track = `track_id` `ba2023f5-a75d-408c-a6a6-d1e841fc7d65`. Currently 4 modules (Get started / Use it well / Copilot Studio / Use case build), 10 lessons.
- The Copilot track sits alongside Claude and other tool tracks; every tool track is gated behind the General track's "From foundation to tools" module, and tool tracks must never re-teach General track content (general AI literacy, prompting, RAG in the abstract).
- NotebookLM source material lives in `docs/external-sources/notebooklm-copilot-*.md` (5 module-level reports + 2 lesson-level reports). **Treat these as fact-source only, never as a style source.** Several specific claims in them are unverified or showed signs of cross-contamination with Claude/Anthropic source material in the same NotebookLM notebook — re-verify anything specific (exact UI paths, exact limits/percentages, named standards) before using it in real content.
- The briefs used to generate those reports (useful for understanding each lesson's intended scope/boundaries): `docs/copilot-track-lesson-briefs.md`.

## Confirmed finding — read this before planning anything further

The existing lesson content is mature and well-voiced, and already covers more than lesson titles suggest. **Before making any changes, read the actual `content_blocks` for all current lessons** (don't assume from titles — this exercise already caught several false "gaps" that turned out to be already covered).

As of this writing, confirmed **already covered — do not re-add**:
- Scheduled prompts (Lesson 1.2)
- Pages / saving a chat response as an editable document (Lesson 1.3)
- The `/` file-reference and `@` agent-mention syntax (Lesson 1.3 — note: real syntax is `/` and `@`, not `/` and `\` as some NotebookLM material claimed)
- Prebuilt Microsoft agents accessible via `@` (Lesson 1.3)
- Agent Builder (no-code) vs. Copilot Studio (low-code) distinction (Copilot Studio, lesson 1) — handled well in one lesson, not split
- MCP connection for Studio agents (Copilot Studio, lesson 1)
- Publishing, channels, and Analytics-based maintenance, with a full worked example — an "IT Onboarding Assistant" agent built end to end (Copilot Studio, lesson 3)

## Confirmed genuine gaps — these are the only things to build

### 1. New Module 3 — Copilot Cowork (structural change)

Insert as a new module between "Use it well" and "Copilot Studio." Copilot Studio and the capstone shift to Modules 4 and 5. This requires updating `modules.sort_order` and the `module_prerequisites` chain (Cowork depends on "Use it well" completing; Copilot Studio's prerequisite edge needs to point at Cowork instead of directly at "Use it well," to keep the chain linear) — not just adding content.

Lessons:
- 3.1 What Copilot Cowork is and when to use it
- 3.2 Working with Copilot Cowork
- 3.3 Connecting Cowork to your tools and data

Source: `notebooklm-copilot-module3-cowork.md` (for 3.1 and 3.3), `notebooklm-copilot-lesson3-2-cowork-delegation.md` (for 3.2).

**Known issue to fix before drafting 3.2:** the lesson-2 report's Section 4 ("The Approval Checkpoint: Your Explicit Go-Ahead") explains *why* approval checkpoints exist and lists specific always-approval actions — that content belongs to 3.3, not 3.2. Trim it from 3.2's draft; don't let 3.3 just repeat it either.

**Known open item:** the lesson-2 report introduces a `/schedule` command for recurring Cowork tasks that no lesson currently owns (scheduling was previously described as a chat-level feature, not a Cowork one). Don't silently adopt this — decide its placement explicitly, or drop it, before it ends up in any lesson.

### 2. New Lesson — Personalizing Copilot

Add as the 4th lesson in the existing "Use it well" module. Covers Custom Instructions and Saved Memories only — confirmed absent from every current lesson. Do not re-cover scheduled prompts (already in 1.2).

Source: `notebooklm-copilot-module1-chat-foundations.md` and `notebooklm-copilot-module2-chat-practitioner.md`, personalization sections only.

### 3. Enrichment edit — existing Grounding lesson (2.2, "Grounding Copilot on your organisation's data")

Add a new section covering Notebooks and the Researcher/Analyst prebuilt agents. **Edit in place — do not fork into a new lesson.** The lesson already has a strong shape (what grounding means here → permission boundary → what this looks like in practice → where answer quality breaks down → what you need for this to work → where this leaves you); the new section needs to fit that shape, not disrupt it.

Source: `notebooklm-copilot-module2-chat-practitioner.md`, grounding/Notebooks/Researcher-Analyst sections.

### 4. Conditional light enrichment — Copilot Studio module

Only add if, on a close re-read of the existing 3 Studio lessons, a sponsor-facing commissioning/governance checklist (ownership, licensing, DLP compliance, publishing approval) is genuinely missing. **Do not restructure** — the existing Agent Builder vs. Studio split inside lesson 1 stays exactly as is. Lesson 3 already partially covers publish/channels/Analytics-based maintenance — check whether that's sufficient before adding anything. If it already covers this adequately, skip this item entirely.

Source: `notebooklm-copilot-lesson4-2-studio-decision-framework.md`.

## Delivery mechanism

Every new/edited lesson gets produced as a JSON file in the app's exact `content_blocks` schema (the same paragraph/heading/callout/card_group/quiz/whitespace block types used in the current live lessons — match field shapes exactly, e.g. `id`/`type`/`text`/`level` for headings). Reviewable, diffable files — **not applied directly to any database.** A human with DB/admin access applies them after review, via the admin UI or a script.

The structural change (new Module 3, renumbering, prerequisite-chain updates) must be reviewed as its own distinct step, separate from content changes — it touches `modules.sort_order` and `module_prerequisites`, and potentially affects `user_modules`/`user_lessons` assignments for any learners already partway through the track.

## Voice bar — non-negotiable

Match the real, current lesson content directly — not the NotebookLM reports, not a written style guide. Concrete scenario-first opener, second person throughout, honest cross-references to specific General track lessons by name (the existing lessons do this consistently, e.g. "(What AI is)", "(How AI works)"), no invented terminology, no fabricated specifics (exact model names/versions, unverifiable percentages, invented UI click-paths) carried over from NotebookLM source material without independent verification.

## Open when resuming

- Exact `sort_order` for the new Personalizing Copilot lesson within "Use it well."
- Whether item 4 (Studio enrichment) is actually needed — re-read the current lessons first.
- Whether any learners are currently assigned to or partway through the Copilot track — check `user_modules`/`user_lessons` before applying the module renumbering, since it may affect what they see mid-progress.
