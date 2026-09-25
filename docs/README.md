# docs/ — what lives where

Orientation for this folder. The repo-wide entrypoint is the root `CLAUDE.md` (agents) /
`README.md` (humans). The rule is simple: **if a doc is in the first table, it is kept current —
trust it and fix it when it's wrong. If it's in the second, it's a record of a point in time —
read it for the why, never follow it as an instruction.** Where a historical doc and the code
disagree, the code wins.

## Read to contribute (current, maintained)

| Doc | What it's for |
|---|---|
| `../README.md` | Front door: what the hub is, quickstart, where to look. |
| `../CONTRIBUTING.md` | The branch → PR → green CI → squash-merge workflow, the rulesets, deploying. **Humans start here.** |
| `../CLAUDE.md` | Operational guide: current state, the repo-wide rules, locking semantics, deploy/ops. **Agents start here.** Scoped guides load per folder: `../backend/CLAUDE.md`, `../frontend/CLAUDE.md`, `content/CLAUDE.md`. |
| `feature-index.md` | Every shipped feature → its spec and the code it starts in. Add a line when a feature ships. |
| `../SECURITY.md` | Every secret, where it lives, who can read it, rotations owed, rotate-on-handover. |
| `../python-be-architecture.md` | Mandatory backend conventions (delaware template). |
| `../db/README.md` | Database roles, credentials, procedures — read before any DB work. |
| `superpowers/lessons.md` | Dated ledger of traps this repo has already hit (what went wrong / why it bites here / the rule). Append when a new one happens. |
| `db-backup-restore.md` | Operator runbook for the nightly DB backups and restore drills. |
| `app-alerts.md` | Runbook for the three app health alerts (down, 5xx, restarts): what fired, first checks, fixes. |
| `content/` | Content model (`README.md`), authoring guide (**read before writing lessons**), review lens, style guide, review-tooling notes. The content itself lives in the DB, not the repo. |
| `reviews/2026-09-17/` | The **way-of-working programme**: comparison with the delaware house pattern, Tier 0/1/2 tables, open decisions, the two reference studies. |
| `reviews/2026-07-31/` | The **pending code/DB work queue**: independent review + master plan + 5 phase plans (A–E, unexecuted). Current until executed, then it moves to the table below. |
| `ai-agents-plan.md` | Only §7 (provider seam) and §8b (key/spend) are current; the rest is the original AI-features design, largely shipped — see its header. |
| `design-prototypes/` | Static HTML mockups that are the **visual contract** for the admin panel (`option-b.html`) and the AI interviewer. Referenced by path from live frontend source — pinned, do not move. |

## Historical / reference (point-in-time — do not treat as current instructions)

| Path | What it is |
|---|---|
| `superpowers/specs/` + `superpowers/plans/` | One design spec + implementation plan per feature (`YYYY-MM-DD-<topic>-design.md`), as designed at the time. A spec is live only while its plan is being executed; after that it is the record of *why*. The feature index in `CLAUDE.md` points at the right one. Later corrections go in an amendments section, not a rewrite. |
| `reviews/2026-07-09-code-review.md` | The first full code/DB review. Superseded by `reviews/2026-07-31/`. |
| `design/` | The 2026-07-03 rebuild contracts (backend/frontend/database). Superseded wherever they conflict with code or `CLAUDE.md`. Kept in place because source comments cite them by basename — do not rename. |
| `lesson-media-plan.md` | Lesson images/videos design. Shipped 2026-07-13; still accurate. |
| `content-enrichment-game-plan.md` | 2026-07-10 content-enrichment decisions from the fit-gap analysis. |
| `copilot-track-enrichment-plan.md`, `copilot-track-lesson-briefs.md` | 2026-07-16 Copilot-track enrichment plan and its NotebookLM briefs. |
| `external-sources/` | Raw source material gathered for content work (fit-gap analysis, course inventories, NotebookLM outputs). Input, not guidance. |
| `history/` | Superseded docs kept for reference: the original rebuild plan, the 2026-07-29 interviewer follow-ups, and `state-log-2026.md` (the dated state notes that used to open `CLAUDE.md`). |

**Conventions.** Date-prefixed files and folders are historical by default; the only exception
is a review folder that still holds an unexecuted programme, listed above. A new doc that must
stay current goes in the first table, in the same PR that adds it.

Not docs: `backend/prompts/*.md` are runtime assets baked into the Docker image and loaded by
`services/prompts.py` (git is their only source of truth; the admin System Prompts page is
read-only). Never move or rename them, and treat edits as production changes.
