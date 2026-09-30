# Feature index → specs

Where each shipped feature is designed and where its code starts. Specs live in
`docs/superpowers/specs/` (same-date plans in `docs/superpowers/plans/`); a spec is the record of
*why*, the code is the truth. Full build history: git log + the specs themselves. Add a line when
a feature ships.

- **Auth** — password JWT (30-min access + rotating 14-day refresh in `auth_sessions`),
  SHA-256-hashed single-use invite/reset tokens, ACS invite/reset emails; Entra ID OIDC
  side-by-side (server-side auth-code+PKCE issuing the same native token pair;
  `users.external_id` = Entra OID; invite-gated, never provisions). `routers/auth.py`,
  `auth_entra.py`. Passwords are truncated to bcrypt's 72 bytes explicitly (`core/security.py`).
- **Learning path, locks & maturity gating** — `CLAUDE.md` "Locking"; rule in
  `frontend/src/lib/learningPathLocks.ts`; `2026-07-14-learning-path-level-headers-design.md`,
  `2026-07-20-below-level-free-review-design.md`.
- **Introduction level** — `2026-07-17-introduction-level-design.md`.
- **`user+` role** — `2026-07-22-user-plus-role-design.md`.
- **Cascading track/module assignment** (full resync both ways) —
  `2026-07-23-cascading-track-module-assignment-design.md`; `services/admin_user_service.py`.
- **Admin panel** (`/admin/*` routed shell, `frontend/src/pages/admin2/`) — shipped 2026-07-27:
  Dashboard, People, user detail, Assignments matrix + project defaults + `assigned_via`
  provenance, Feedback triage, Projects, Email templates, Setup, System Prompts —
  `2026-07-23-admin-panel-redesign-design.md`.
- **Lesson feedback** — `2026-07-14-lesson-feedback-design.md`; `routers/feedback.py`.
- **Feedback-driven content improvement** — accepted feedback → AI-proposed content_blocks
  diffs, admin-approved; + calibration notes queue —
  `2026-07-27-feedback-driven-content-improvement-design.md` (plans a–e);
  `routers/admin_content_improvement.py`, `admin_calibration_notes.py`.
- **AI chat foundation** — `conversations`/`messages`/`project_ai_settings`, provider =
  Anthropic API direct — `2026-07-23-ai-chat-foundation-design.md`; `services/llm_service.py`,
  `docs/ai-agents-plan.md` (§7 provider seam, §8b key/spend — spend cap: issue #44).
- **AI interviewer** — `2026-07-28-ai-interviewer-design.md` (+ round 2:
  `2026-07-30-interviewer-opener-design.md`); `routers/interview.py`, gated by
  `require_interview_surface` + the `interview` component lock
  (`require_component_unlocked`, and `require_chat_kind_unlocked` on chat).
- **AI interviewer eval (tranche 1 + 2)** — run stamping, generation hardening, assessment
  gate (`2026-09-26-interviewer-evaluation-design.md`); frozen test set + automatic
  checks (`2026-09-27-interviewer-eval-tranche-2-design.md`); `backend/evals/interviewer/`,
  `docs/guides/interviewer-evals-learning-guide.md`.
- **Project AI surface toggles** (per-project, default OFF, 403 until toggled) —
  `2026-07-27-project-ai-surface-toggles-design.md`; `core/dependencies` `require_ai_surface`.
- **System prompts — git-only** (2026-09-23): `backend/prompts/*.md`, read-only admin page
  `admin2/PromptsPage.tsx`, golden cases in `backend/tests/golden/ai/` —
  `2026-09-23-prompts-git-only-design.md` (supersedes the editor half of
  `2026-07-29-prompt-editor-design.md`). The `prompts` table and its model were dropped in phase C
  (C8b, migration `e5f6a7b8c9d0`).
- **Nightly DB backups** — `2026-07-29-database-backups-design.md`; runbook
  `docs/db-backup-restore.md` (job `ai-enablement-hub-db-backup`, 02:30 UTC, 30-day retention,
  log-based alerts; **no Postgres client tools on the dev machine** — restores run via the
  manual restore job).
- **Bulk CSV invite** — `2026-07-14-bulk-csv-invite-design.md`; `services/invite_csv.py`.
- **Quiz = completion-gated, not score-gated** — `2026-07-17-quiz-completion-not-score-gated-design.md`.
- **Lesson media / blob storage** — `docs/lesson-media-plan.md`; `services/media_service.py`,
  `routers/admin_media.py`.
- **Per-project email templates** — `routers/admin_email_templates.py`.
- **Interactive lesson blocks** (`interactive`, `try_it_yourself`, `question`) —
  `frontend/src/types/contentBlocks.ts`.
- **Un-assessed learning-path signpost** — `2026-08-04-unassessed-path-signpost-design.md`.
- **Content QA review** — `2026-07-20-admin-assigned-content-qa-review-design.md`;
  `backend/scripts/content_qa/`.
- **Delivery pipeline** (way-of-working) — `docs/reviews/2026-09-17/`; CI `.github/workflows/ci.yml`,
  Deploy `.github/workflows/deploy.yml`, Claude review `2026-09-23-claude-pr-review-design.md`,
  frontend tests `2026-09-24-frontend-tests-design.md`.
