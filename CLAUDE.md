# AI Enablement Hub

**FastAPI** (Python 3.13, uv) + **React 18 + TypeScript** (Vite) + **Azure Database for
PostgreSQL**, shipped as ONE Azure Container App that serves the API and the built SPA.
This is production — the app real learners use. Content is edited through the admin UI
(`PATCH /api/admin/lessons/{id}`) and written straight to the live DB.

> **THE ONE-DATABASE RULE — read this before anything else.** Dev and prod share the single
> Azure PG database `ai-enablement-hub` (only the integration suite uses
> `ai-enablement-hub-test`). A local `alembic upgrade`, a "test" user, or any script writing
> rows edits **live learner data**. Verify learner-facing changes with production-shaped
> fixtures and a stubbed `fetch`, never by creating users/surveys/progress — see
> "Verifying without touching live data" below.

The old Supabase app is permanently retired (cutover complete 2026-07-08); its repo sits
untouched at `../app/`, historical only. The pre-cutover migration scripts were removed
2026-08-10 (git history has them).

## Current state (2026-09-17)

- **Live:** https://ai-enablement-hub.kindcoast-3b1fe056.swedencentral.azurecontainerapps.io —
  image `ai-enablement-hub:20260917-085533`, revision `--0000038`, built from `main` @ `87a81a7`
  (pre-rewrite SHA `8da7f12` for the `1b7546a`-era note this superseded — **git history was
  rewritten 2026-08-10 to purge learner PII**, so SHAs in older notes/transcripts don't resolve;
  the pre-rewrite mirror lives in `..\_archive\ai-hub-pre-purge-mirror-2026-08-10.git`). `main` ==
  deployed as of this note, no known undeployed behavior changes. The two most recent deploys
  both fix admin-panel bugs found while trying to delete a user through the People screen:
  `1ea39a3` adds `GET /admin/users/{user_id}` — the People detail page used to resolve its
  participant by scanning page 1 (50 users, unfiltered) of the same paginated list PeoplePage
  shows, so anyone past the first page 404'd as "could not be found" and was unreachable for
  edit/delete/role changes (SAP SCM alone had ~68 unreachable users); `87a81a7` adds the missing
  `multiplier` entry to the admin Maturity badge palette, which was keyed on only the 3
  scoring-engine-assignable levels and silently rendered a blank cell for anyone whose
  `effective_maturity` resolved to `multiplier`.
- **This file lags reality by design.** Trust the live system, not this log:
  `az containerapp show -n ai-enablement-hub -g imaginemore-playground --query
  properties.template.containers[0].image -o tsv` and `cd backend && uv run alembic current`.
  Recovering what a past deploy shipped: compare the image tag's timestamp with
  `git log --format=%ci`.
- **DB:** alembic head **`1cd2cc2d05a9`** (prompts table) == code head, single linear chain.
- **Scale:** ~85 endpoints across 19 routers (`backend/src/routers/`); feature-complete, in
  active content + AI-feature iteration. ~104 users as of 2026-08-04.
- **Auth:** password (JWT) live; Entra ID OIDC code-complete but deployed **dark** (no
  `ENTRA__*` env on prod; blocked on one-time IT admin consent).
- **Roles:** `admin`, `user+` (bypasses learning-path locks, no admin powers), `user`.
- **Maturity ladder:** `explore → practitioner → integrator → multiplier`
  (`core/constants.py::LEVEL_ORDER`). The multiplier level holds 4 tracks (General III,
  Copilot II, Claude II, Capstone-only For Developers). Content model:
  `docs/content/README.md`; active content specs: `2026-07-29-general-iii-track-design.md`,
  `2026-07-31-multiplier-level-rewrite-design.md`.
- **Git:** `main` is the only long-lived branch; use `feature/*` for work and fast-forward
  `main`. `deploy.ps1` builds the **working directory, not git** — push after every deploy.
- **Pending work queue:** `docs/reviews/2026-07-31/` — independent code+DB review + 5 fix-phase
  plans (A→B→C→D, E parallel; **phase C owns all new migrations**, chained off `1cd2cc2d05a9`).
  Unexecuted as of 2026-08-10.

## How to run & verify

- **Backend** (inside `backend/`): checks = `uv run poe format && uv run poe lint && uv run poe test`
  (integration tests hit the `ai-enablement-hub-test` Azure PG DB). Dev server: `uv run poe dev`
  (→ :8000, Swagger at `/docs`). Migrations: `uv run poe upgrade`.
- **Frontend** (inside `frontend/`): checks = `npm run typecheck && npm run lint && npm run build`.
  Dev: `npm run dev` (→ :5173, proxies `/api` → :8000). After a backend contract change,
  regenerate the committed API types: `npm run gen:api` (backend must be running).
- **Deploy:** `.\deploy.ps1` at repo root — see "Deployment & operations". **Ask before any
  Azure-mutating command**; read-only `az` queries are fine.
- **Secrets:** `backend/.env` + `db/.env` (git-ignored; keys documented in
  `backend/.env.local.example`). Rotate DB role passwords with
  `db/provision_roles.py --rotate-passwords`.

## Repo map

- `backend/src/` — FastAPI app in delaware layering: `routers/ → services/ → repositories/` +
  `schemas/`, `db/models/`, `core/{configs,dependencies}`. Tests in `backend/tests/`
  (`unit / integration / golden / fixtures`).
- `backend/prompts/` — **runtime assets, not docs**: the AI system prompts, COPY'd into the
  Docker image and loaded by `services/prompts.py`; DB-overridable per prompt via the admin
  System Prompts page. Treat edits as production changes. Never move/rename.
- `backend/alembic/versions/` — migrations. `backend/scripts/` — ops tooling: `content_qa/`
  (content-review toolkit incl. `check_draft.py`, the pre-write drafting gate),
  `issue_invite.py` (bootstrap invite links), `rescore_parity.py`, `read_goldstandard.py`.
- `frontend/src/` — React app: `pages/` (+ `pages/admin2/` = the admin panel), `components/`,
  `api/`, `lib/`, `contexts/`, `styles/`, `types/contentBlocks.ts` (the lesson block union).
- `db/` — `README.md` (roles, credentials, procedures — read before DB work),
  `provision_roles.py`, `content_tools/` (live lesson-edit passes), `baseline/` (frozen
  pre-cutover snapshot, historical only).
- `docs/` — see `docs/README.md` for the map: `superpowers/{specs,plans}` (one per feature),
  `reviews/` (audits + the pending fix programme), `content/`, `design/` + `design-prototypes/`
  (point-in-time/pinned — do not move), `history/`, `db-backup-restore.md` (backup runbook).
- `infra/` — one-time create (`containerapp.yaml`, `deploy-initial.ps1`) + `backup/` (the
  nightly-dump job image). Repo root: `Dockerfile`, `deploy.ps1`, `python-be-architecture.md`.
- Gitignored local dirs you may see: `scratch_review/` (content-authoring workbench),
  `.claude/`, `.superpowers/`, `memory/`.

## Conventions & process

1. `python-be-architecture.md` — **MANDATORY** backend conventions (delaware template):
   router → service → repository → model layering, abstract repositories, DI in
   `core/dependencies/`, poe tasks, ruff/ty clean, ≥80% coverage. Two approved deviations:
   asyncpg is a main dependency, and integration tests run against the Azure PG test DB
   (schema needs text[]/JSONB/ON CONFLICT), not in-memory SQLite.
2. Feature work = design spec in `docs/superpowers/specs/YYYY-MM-DD-<topic>-design.md`, then an
   implementation plan in `docs/superpowers/plans/`, then execution (usually subagent-driven,
   task-by-task with review). Batch-by-batch rebuild process is over; don't follow
   `docs/history/rebuild-plan.md`.
3. **Authorization iron rule (tests must enforce):** no endpoint outside `/admin/*` accepts a
   user identifier from the request — ownership comes from the token only.
4. **FastAPI signature gotcha:** any type in a *parameter* annotation FastAPI inspects
   (routers, DI providers) must be imported at runtime, not under `TYPE_CHECKING` — an
   unresolvable name silently degrades the param to a required query param (uniform 422s).
5. Integration tests derive their DSN from `ALEMBIC_DATABASE_URL` with the database swapped to
   `ai-enablement-hub-test`; per-test savepoint rollback. Flaky `-n auto` runs against the
   shared remote DB happen — rerun before panicking.
6. Frontend renders at CSS zoom 1.25 on `:root`; rect-based positioning must compensate via
   `getRectZoomFactor` (`lib/uiZoom.ts`).
7. Content authoring: read `docs/content/authoring-guide.md` first, gate every draft with
   `backend/scripts/content_qa/check_draft.py` before writing to the DB.

## Feature index → specs

Specs live in `docs/superpowers/specs/` (same-date plans in `…/plans/`). Full build history:
git log + the specs themselves.

- **Auth** — password JWT (30-min access + rotating 14-day refresh in `auth_sessions`),
  SHA-256-hashed single-use invite/reset tokens, ACS invite/reset emails; Entra ID OIDC
  side-by-side (server-side auth-code+PKCE issuing the same native token pair;
  `users.external_id` = Entra OID; invite-gated, never provisions). `routers/auth.py`,
  `auth_entra.py`.
- **Learning path, locks & maturity gating** — see "Locking" below;
  `2026-07-14-learning-path-level-headers-design.md`, `2026-07-20-below-level-free-review-design.md`.
- **Introduction level** — `2026-07-17-introduction-level-design.md`.
- **`user+` role** — `2026-07-22-user-plus-role-design.md`.
- **Cascading track/module assignment** (full resync both ways) —
  `2026-07-23-cascading-track-module-assignment-design.md`; `services/admin_user_service.py`.
- **Admin panel** (`/admin/*` routed shell, `frontend/src/pages/admin2/`) — SHIPPED 2026-07-27:
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
  `docs/ai-agents-plan.md` (§7 provider seam, §8b key/spend — spend cap on the prod key is
  **unverified; ask Matthias**).
- **AI interviewer** — `2026-07-28-ai-interviewer-design.md` (+ round 2:
  `2026-07-30-interviewer-opener-design.md`); `routers/interview.py`, gated by
  `require_interview_surface`.
- **Project AI surface toggles** (per-project, default OFF, 403 until toggled) —
  `2026-07-27-project-ai-surface-toggles-design.md`; `core/dependencies` `require_ai_surface`.
- **System prompts, DB-overridable + admin-editable** —
  `2026-07-30-prompts-page-master-detail-design.md`; `admin2/PromptsPage.tsx`,
  `services/prompt_service.py` (bustable `load_prompt` cache), `prompts` table.
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

## Locking, prerequisites & preview (as-built)

- **Two independent lock systems that never interact:**
  - **Component level** (`assessment`/`learning`/`interview` hub tiles):
    `project_component_settings` over `DEFAULT_LOCKED` (`core/constants.py`), resolved
    server-side, served by `GET /api/me/journey`. `hidden` = card filtered out; `locked` =
    greyed inert card. Unlock is a manual admin toggle (completing the assessment does NOT
    unlock learning, despite the copy). **Hard server-side gate since 2026-07-23:**
    `require_component_unlocked` (`core/dependencies/components.py`) is router-level on
    `survey.py` and `learning.py` — hidden/locked ⇒ 403 `ComponentLockedError`. Project-level
    gate, not a role check: admin and `user+` are NOT exempt.
  - **Module level:** `module_prerequisites` edge table (only DB constraint is `not_self`;
    nothing blocks cross-track or cyclic edges). The unlock rule exists ONLY in
    `frontend/src/pages/LearningPathNew.tsx::isUnlocked`: unlocked ⇔ admin OR user+ OR no
    prereqs OR every prereq module has assigned-lesson `total > 0 && completed === total`.
    Tracks strictly below the learner's effective level are freely reviewable (2026-07-20).
    **Still frontend-only** — no server-side prerequisite check exists.
- **Admin maturity pin** (`users.maturity_override`, `PUT /api/admin/users/{id}/maturity`) is
  **visibility-only**: it sets the base of `effective_level` (the whole-track "Unlocks at
  {Level}" lane lock) and deliberately does NOT assign content (assignment is seeded only on
  survey completion or by an admin — decision 2026-07-17) and does NOT bypass module
  prerequisites. Cross-track gotcha: tool-track first modules have prereqs on the last
  General II module; `predSatisfied()` in `LearningPathNew.tsx` treats a prerequisite pointing
  into a strictly-lower maturity level than the dependent's track as satisfied by maturity
  alone. Same-track/same-level prereqs still gate.
- **Maturity gating, assignment and module prerequisites are visibility filters, NOT access
  control** (component locks are the one exception): `GET /api/lessons/{id}` serves any lesson
  to any authenticated user whose project has `learning` unlocked, and `PUT …/progress`
  accepts unassigned/locked lessons. Closing this needs a server-side port of the
  prerequisite-DAG check plus wiring maturity/assignment into `learning_service.py` — tracked
  in the 2026-07-31 review.
- **No prerequisites between tracks** (the dotted general→tool graph edge is decorative) and
  **none between lessons** (`sort_order` only; the quiz gate blocks "Mark as complete", not
  navigation).
- **Known quirks (accepted 2026-07-06):** a prereq module with 0 assigned lessons locks its
  dependents forever (0/0 also disables the popup start button); an UNASSIGNED prerequisite
  locks dependents with no visible edge; `?edit=true` shows the editor UI to non-admins (saves
  403 server-side); `GET /api/learning/graph` returns ALL track/module titles with `assigned`
  flags. No admin "view as learner" mode.

## Deployment & operations

- **Shape:** ONE container app `ai-enablement-hub` (RG `imaginemore-playground`, env
  `imaginemore-playground-cae`): ACR admin auth, external ingress :8000, 0.5 CPU/1Gi,
  **min=max=1 replica — a design constraint** (rate limiter + daily cleanup are in-process).
  Multi-stage `Dockerfile`: node builds `frontend/` → uv installs backend → `python:3.13-slim`
  runs `startup.py` (**alembic upgrade, then uvicorn** — migrations apply on container start;
  startup probe budgets ~240 s for them) and serves the SPA from `/app/static`.
- **Deploy procedure (the discipline is hard-won):** commit only the specific change (never a
  blanket `git add -A`), push, then build from a **fresh `git worktree` of the pushed commit**
  (short path near the drive root, `-c core.longpaths=true`), because `az acr build` uploads
  the working directory as-is. Run `.\deploy.ps1` from that worktree. After deploying:
  fast-forward `main` and push. Post-deploy checks: `/api/health`, `/api/auth/methods`,
  `latestReadyRevision == latestRevision`, and for frontend changes grep the served
  `/assets/index-*.js` for a new copy string.
- **Gotchas:**
  - **Never pipe `deploy.ps1` through `Tee-Object`/`2>&1`** — `az acr build` writes progress
    to stderr and under PS 5.1 + `$ErrorActionPreference=Stop` the script dies *after* queuing
    the build. Recovery: `az acr task list-runs`, wait, then `az containerapp update --image`.
  - The az CLI on this machine is old and off PATH
    (`C:\Program Files\Microsoft SDKs\Azure\CLI2\wbin\az.cmd`); set `PYTHONIOENCODING=utf-8`
    or its log streaming crashes on Vite's unicode; `infra/containerapp.yaml` must stay pure
    ASCII.
  - **The old az CLI's .dockerignore matcher ignores `dir/` trailing-slash patterns** — every
    ignored dir is listed bare AND with `/**`. Verify any .dockerignore change by re-packing
    with az's own `_pack_source_code` and inspecting the tar. `**/.env` exclusion is
    load-bearing.
- **Secrets** live as Container App secrets (`database-password`, `alembic-database-url`,
  `jwt-secret`, `acr-password`, `acs-connection-string`, `llm-api-key`). Prod
  `AUTH__JWT_SECRET` ≠ dev. `APP__URL` env = public URL (CORS + invite/reset link base).
- **Backups:** nightly logical dump 02:30 UTC via Container Apps Job (separate image from the
  app — `deploy.ps1` never touches it) into the private `db-backups` container; 30-day
  retention; log-based Sev1 alerts (`ai-hub-db-backup-failed`, `-missing`). Restores via the
  manual restore job — **never write a procedure assuming local `pg_restore`**. Runbook:
  `docs/db-backup-restore.md`. Azure PITR stays at the server default 7 days, untouched.
- **Verifying without touching live data:** dump production-shaped fixtures via read-only
  service calls, serve from a temporary `frontend/public/__verify/`, stub `window.fetch` in a
  Playwright `addInitScript` (page context — the MCP host has no `fs`/`fetch`). Assert on
  `getComputedStyle`, not just screenshots, and exercise the load window
  (`waitUntil: 'commit'` + delayed response) — `networkidle` hides first-paint bugs.

## Key facts & open items

- **Re-invite pending:** migrated users still have `password_set=false` (all but matthias) —
  re-invite via the admin UI; sequence AFTER any custom-domain change so links carry the final
  URL.
- **Entra ID:** blocked on one-time tenant admin consent (in the IT ticket). App registration
  "AI Enablement Hub" `ad61703c-684f-4392-b786-8926ba2ab69d`; client secret 'hub-oidc' expires
  July 2028. After the grant: test on :5173, then wire prod env (`az containerapp secret set`
  + `ENTRA__*` — ask first).
- **Hosting move (IT ticket, 2026-07-06):** delaware IT deems the playground not secure enough
  for a client-facing app — new hosting, custom domain `ai-enablement-hub.delaware.pro`, Entra
  consent and an ACS custom email domain are all bundled in one ticket (Matthias's name).
  Until it lands, the playground deployment is the live one. Custom-domain recipe (DNS CNAME +
  TXT `asuid` record, `az containerapp hostname add`/`bind`, `APP__URL` update): git history
  of this file @ `516e40c`, "Open for cutover".
- **LLM spend:** prod carries `llm-api-key` and admin-reachable AI spend is live; whether the
  key is a capped workspace key is **unverified — ask Matthias** (docs/ai-agents-plan.md §8b).
- **Emails:** ACS `imaginemore-playground-acs`, sender `hub@…azurecomm.net`. Local dev `.env`
  carries `EMAIL__*` too → local invites/resets send REAL email (comment out to disable).
- Rate limiting is an in-process fixed window (`core/ratelimit.py`) — another reason for the
  single-replica constraint.
- The dev `AUTH__JWT_SECRET` leaked into a tool transcript 2026-07-06 (dev-only blast radius) —
  rotate when convenient. A storage-account key leaked 2026-07-30 — rotation still owed.
