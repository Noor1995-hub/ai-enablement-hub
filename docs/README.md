# docs/ — what lives where

Orientation for this folder. The repo-wide entrypoint is the root `CLAUDE.md` (agents) /
`README.md` (humans); this file only maps the docs tree.

| Path | What it is | Status |
|---|---|---|
| `superpowers/specs/` | One design spec per feature (`YYYY-MM-DD-<topic>-design.md`). The convention for all feature work. | Living |
| `superpowers/plans/` | The implementation plan for each spec (checkbox tasks, executed by agents). | Living |
| `superpowers/lessons.md` | Dated ledger of traps this repo has already hit (what went wrong / why it bites here / the rule). Append when a new one happens. | Living |
| `reviews/` | Code/DB audits and their remediation programmes. `2026-07-31/` holds the current **pending code/DB work queue**: the independent review + master plan + 5 phase plans (A–E, unexecuted). `2026-09-17/` holds the **way-of-working comparison** against the delaware house pattern (`bta-agents-portal`, `sb-accelerator`) with prioritised process recommendations + the two reference studies. | Living |
| `content/` | Content model, authoring guide (**read before writing lessons**), review lens, process notes. The content itself lives in the DB, not the repo. | Living |
| `db-backup-restore.md` | Operator runbook for the nightly DB backups + restore drills. | Living |
| `ai-agents-plan.md` | AI features design (provider seam §7, key/spend §8b still authoritative). Much of it has shipped — see the status note in its header. | Partly historical |
| `lesson-media-plan.md` | Lesson images/videos design. Shipped 2026-07-13. | Historical, accurate |
| `design/` | The 2026-07-03 rebuild contracts (backend/frontend/database). **Point-in-time**: superseded wherever they conflict with code or CLAUDE.md. Kept in place because source comments cite them by basename — do not rename. | Historical |
| `design-prototypes/` | Static HTML mockups that are the **visual contract** for the admin panel (`option-b.html`) and AI interviewer. Referenced by path from live frontend source — do not move. | Reference |
| `history/` | Superseded point-in-time docs kept for reference (original rebuild plan, session logs). | Historical |

Not docs: `backend/prompts/*.md` are runtime assets baked into the Docker image and loaded by
`services/prompts.py` (DB-overridable via the admin System Prompts page). Never move or rename
them, and treat edits as production changes.
