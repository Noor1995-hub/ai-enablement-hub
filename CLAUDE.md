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

**Scoped guides** load when you work in their folder: `backend/CLAUDE.md` (checks, conventions,
prompts, migrations), `frontend/CLAUDE.md` (checks, API types, zoom, lesson blocks),
`docs/content/CLAUDE.md` (lesson authoring). Features → specs: `docs/feature-index.md`. Dated
history that used to live here: `docs/history/state-log-2026.md`.

## Current state

- **Live:** https://ai-enablement-hub.kindcoast-3b1fe056.swedencentral.azurecontainerapps.io —
  **ask the app, never this file**: `curl .../api/health` returns `build_sha` (the deployed
  commit) and `build_time`; the admin Setup page shows the same as a Deployment card. Running
  image (read-only): `az containerapp show -n ai-enablement-hub -g imaginemore-playground --query
  properties.template.containers[0].image -o tsv`. DB schema: `cd backend && uv run alembic
  current` (code head `c1d2e3f4a5b6`, single linear chain).
- **Backlog = GitHub Issues** (labels `way-of-working`, `fix-programme`, `ops`, `security`).
  Way-of-working Tier 2 is complete (`docs/reviews/2026-09-17/` §5). **July fix programme**
  (issues #52–#56, plans in `docs/reviews/2026-07-31/`; master plan §5 decisions all taken
  2026-09-25): **A (#52) and B (#53) are done and live; C (#54) done and live 2026-09-30**
  (build `189348d`, five migrations `a1b2c3d4e5f6 → b2c3d4e5f6a7 → d4e5f6a7b8c9 → c3d4e5f6a7b8 →
  e5f6a7b8c9d0`). **Rollback floor `f84fded`:** the `prompts` table is dropped, so images from
  before PR #16 won't start. E (#56) is in progress. D (#55) is in progress: D1–D3 and D6–D8
  are PRs #130–#135, D4 is obsolete, and D5/D9/D10 wait on Aaron. Follow-ups: #79 (raise the
  set-password limit so one office NAT can't block itself), #80.
- **Aaron is actively shipping interviewer work** (#81, #91, #95) in the same files as the fix
  programme (`interview_service.py`, `chat_service.py`, `llm_service.py`, `tests/fixtures/llm.py`,
  `useChat.ts`): fetch before branching, and expect to merge `main` into open branches.
- **Scale:** ~88 endpoints, 20 routers (`backend/src/routers/`); ~104 users as of 2026-08-04.
- **Auth:** password (JWT) live; Entra ID OIDC code-complete but **dark** (no `ENTRA__*` on prod;
  blocked on IT admin consent). Roles: `admin` (**power admin**: everything) and `user`; a `user` with
  `project_admins` rows is a **project admin** for those projects only (user management, assignments,
  project settings). Every `/api/admin/*` route declares one guard from
  `core/dependencies/admin_scope.py` (out-of-scope ⇒ 404); spec
  `docs/superpowers/specs/2026-10-01-project-scoped-admin-design.md`.
- **Maturity ladder:** `explore → practitioner → integrator → multiplier`
  (`core/constants.py::LEVEL_ORDER`). The multiplier level holds 4 tracks (General III, Copilot
  II, Claude II, Capstone-only For Developers). Content model: `docs/content/README.md`; active
  content specs: `2026-07-29-general-iii-track-design.md`, `2026-07-31-multiplier-level-rewrite-design.md`.
- **The old Supabase app** is permanently retired (cutover 2026-07-08); its repo at `../app/` is
  historical only; the pre-cutover migration scripts were removed 2026-08-10 (git history has
  them). **Git history was rewritten 2026-08-10** to purge learner PII — older SHAs don't resolve.

## How we work

- **Git:** `main` is the only long-lived branch and is **protected** (`.github/rulesets/`): every
  change is a `<type>/<topic>` branch → pull request → both `CI` checks green → **squash merge**.
  No direct pushes, no force-pushes, admins included. Admins merge their own PR after reading the
  Claude review; nobody @-mentions or requests reviewers. Full flow: `CONTRIBUTING.md`. **Agents
  cannot merge** (`gh pr merge --admin` and ruleset edits are blocked by the permission classifier,
  by Matthias's choice) — hand an admin the merge-ready PRs, in order.
- **Checks:** backend `uv run poe format-check && uv run poe lint-src && uv run poe ty-src &&
  uv run poe test`; frontend `npm run typecheck && npm run lint && npm test && npm run build`
  (details in the scoped guides). A non-required CI `migrations` job runs every migration on a
  throwaway Postgres. CI also enforces coverage ≥ 90%, fresh API types, and the
  docs-drift test (`backend/tests/unit/test_docs_drift.py`: paths named in the maintained docs
  must exist).
- **Claude review** runs on every non-docs PR: advice, not a required check; a red
  `claude-review` means nothing was posted (the PR is unreviewed). `/review` re-runs it and costs
  real money — rationing rule in `CONTRIBUTING.md` → Claude review.
- **Feature work:** design spec in `docs/superpowers/specs/YYYY-MM-DD-<topic>-design.md` → plan in
  `docs/superpowers/plans/` → execution with a review per task and a final whole-branch review.
  Don't follow `docs/history/rebuild-plan.md`.
- **Traps already hit** are dated entries in `docs/superpowers/lessons.md` — read before touching
  `infra/`, `.github/`, `.claude/`, `.dockerignore`. When you hit a new one, append an entry in the
  same PR as the fix.
- **Ask before any Azure-mutating command**; read-only `az` queries are fine. Deploying is a
  deliberate press of the Deploy button by an admin — an agent never triggers it on its own.

## Rules that span the whole repo

1. **Authorization iron rule (tests must enforce):** no endpoint outside `/admin/*` accepts a user
   identifier from the request — ownership comes from the token only.
2. **Never start `uv run poe dev`** to check something or to regenerate types — it writes to the
   live DB. `npm run gen:api` imports the app instead.
3. **`backend/prompts/` are runtime assets**, not docs: git is their only source of truth; an edit
   is a production change (golden snapshots in the same PR). Never move or rename them.
4. **`docs/design/` and `docs/design-prototypes/`** are pinned (source comments cite them by
   path) — do not move them.
5. **Lesson content** (any write, from any folder — admin API, `db/content_tools/`, scripts): read
   `docs/content/authoring-guide.md` and finished lessons first, and gate every draft with
   `backend/scripts/content_qa/check_draft.py` before it touches the DB (`docs/content/CLAUDE.md`). Structure
   (tracks, modules, order, prerequisites, assigning new lessons) is edited in **Admin → Content**.
6. **Secrets:** never in the repo. Local ones in git-ignored `backend/.env` + `db/.env`; the full
   inventory, who can read what and rotation recipes are in `SECURITY.md`.

## Repo map

- `backend/src/` — FastAPI app in delaware layering: `routers/ → services/ → repositories/` +
  `schemas/`, `db/models/`, `core/{configs,dependencies}`. Tests in `backend/tests/`
  (`unit / integration / golden / fixtures`). `backend/alembic/versions/` — migrations.
  `backend/scripts/` — ops tooling (see `backend/CLAUDE.md`).
- `frontend/src/` — React app: `pages/` (+ `pages/admin2/` = the admin panel), `components/`,
  `api/`, `lib/`, `contexts/`, `styles/`, `types/contentBlocks.ts` (the lesson block union).
- `db/` — `README.md` (roles, credentials, procedures — read before DB work),
  `provision_roles.py`, `content_tools/` (live lesson-edit passes), `baseline/` (frozen
  pre-cutover snapshot, historical only).
- `docs/` — map in `docs/README.md`: `superpowers/{specs,plans,lessons.md}`, `reviews/` (audits
  + the pending fix programme), `content/`, `design/` + `design-prototypes/`, `history/`,
  `db-backup-restore.md` (backup runbook), `feature-index.md`.
- `infra/` — one-time create (`containerapp.yaml`, `deploy-initial.ps1`, `50-cicd.ps1`) +
  `deploy-legacy.ps1` (break-glass) + `backup/` (the nightly-dump job image). Repo root:
  `Dockerfile`, `python-be-architecture.md`, `SECURITY.md`, `CONTRIBUTING.md`.
- Gitignored local dirs you may see: `scratch_review/` (content-authoring workbench),
  `.superpowers/`, `memory/`, and everything under `.claude/` except `settings.json` + `hooks/`.

## Locking, prerequisites & preview (as-built)

- **Two independent lock systems that never interact:**
  - **Component level** (`assessment`/`learning`/`interview` hub tiles):
    `project_component_settings` over `DEFAULT_LOCKED` (`core/constants.py`), resolved
    server-side, served by `GET /api/me/journey`. `hidden` = card filtered out; `locked` =
    greyed inert card. Unlock is a manual admin toggle (completing the assessment does NOT
    unlock learning, despite the copy). **Hard server-side gate since 2026-07-23:**
    `require_component_unlocked` (`core/dependencies/components.py`) is router-level on
    `survey.py`, `learning.py` and `interview.py` (not its `admin_router`); `chat.py` applies the
    same gate to `kind=interview` only (`require_chat_kind_unlocked`) — hidden/locked ⇒ 403
    `ComponentLockedError`. `hidden` applies to everyone; `locked` is bypassed by callers who
    bypass locks (power admins, and project admins on their own project —
    `AdminScopeService.bypasses_locks`, exposed as `bypasses_locks` on `GET /api/me`).
  - **Interview assessment gate (2026-09-26):** `require_completed_assessment`
    (`core/dependencies/interview.py`) on `POST /api/interview/opener`, `/playbook` and
    `POST /api/chat/interview`: learners need `survey_status == "complete"` (a draft does not
    count) ⇒ else 403 `AssessmentRequiredError`. Callers who bypass locks are exempt.
    `GET /api/interview/me` is deliberately ungated so an existing playbook stays readable.
    Frontend twin: `frontend/src/lib/interviewAccess.ts` ("Assessment first" tile).
  - **Module level:** `module_prerequisites` edge table (only DB constraint is `not_self`;
    nothing blocks cross-track or cyclic edges). The unlock rule exists ONLY in
    `frontend/src/lib/learningPathLocks.ts::isModuleUnlocked` (pure, unit-tested next to it):
    unlocked ⇔ bypasses_locks OR no prereqs OR every prereq module has assigned-lesson
    `total > 0 && completed === total`. Tracks strictly below the learner's effective level are
    freely reviewable (2026-07-20). **Still frontend-only** — no server-side prerequisite check.
    Admin → Content refuses prerequisite cycles server-side (`core/prerequisites.py`).
- **Admin maturity pin** (`users.maturity_override`, `PUT /api/admin/users/{id}/maturity`) is
  **level-only**: it sets the base of `effective_level` (the whole-track "Unlocks at
  {Level}" lane lock and the lesson access gate below) and deliberately does NOT assign content (assignment is seeded only on
  survey completion or by an admin — decision 2026-07-17) and does NOT bypass module
  prerequisites. Cross-track gotcha: tool-track first modules have prereqs on the last
  General II module; `isPrereqSatisfied()` in `lib/learningPathLocks.ts` treats a prerequisite
  pointing into a strictly-lower maturity level than the dependent's track as satisfied by
  maturity alone. Same-track/same-level prereqs still gate.
- **Lesson access gate (server-side, since the 2026-07-31 review fix):** `GET /api/lessons/{id}`
  and `PUT …/progress` allow a lesson iff the caller bypasses locks OR Introduction
  track OR assigned to the caller OR its track's `required_level` ≤ the caller's
  `effective_level` (so the maturity pin now opens tracks server-side too); only "unassigned
  AND above level" ⇒ 403 `LessonNotAccessibleError`. A caller with neither a completed
  assessment nor a maturity pin has no effective level: assigned + Introduction only. Unknown
  lesson still 404s first. The rule
  lives in `backend/src/services/learning_service.py::_is_accessible`; the router resolves
  maturity. **Module prerequisites are still a visibility filter only** (frontend, above), and
  `GET /api/modules/{id}/lessons` + `GET /api/learning/graph` stay ungated discovery surfaces.
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
  **min=max=1 replica — a design constraint** (rate limiter `core/ratelimit.py` + daily cleanup
  are in-process). Multi-stage `Dockerfile`: node builds `frontend/` → uv installs backend →
  `python:3.13-slim` runs `startup.py` (**uvicorn only** — migrations run in the
  `ai-enablement-hub-migrate` job before each deploy, never in the container) and serves the SPA
  from `/app/static`.
- **Deploy:** GitHub → Actions → **Deploy** → "Run workflow" on `main` (admins).
  `.github/workflows/deploy.yml` builds the merged commit, pushes `ai-enablement-hub:<sha>`, runs
  `alembic upgrade head` in the migrate job and **stops if it fails**, rolls the app with
  `APP__BUILD_SHA`/`APP__BUILD_TIME`, polls until `Running`, and asserts `/api/health` reports the
  SHA. **Rollback:** run it again with `image_sha` = a previous commit on `main` (no rebuild;
  migrations are expand-first). Azure side: identity `ai-hub-cicd` (OIDC, no stored secret,
  both GitHub subject forms), created by `infra/50-cicd.ps1`. **Break-glass** (Actions down):
  `infra/deploy-legacy.ps1` builds the **working directory, not git**, and refuses unless the tree
  is clean and `HEAD == origin/main` — read its header first. Never keep a deploy log here.
- **az CLI on this machine:** old and off PATH
  (`C:\Program Files\Microsoft SDKs\Azure\CLI2\wbin\az.cmd`); set `PYTHONIOENCODING=utf-8`. Its
  traps (codepage, `.dockerignore` matching, `2>&1`/`Tee-Object` under PS 5.1) are in
  `docs/superpowers/lessons.md`.
- **Runtime config:** Container App and job secrets (inventory in `SECURITY.md`). Prod
  `AUTH__JWT_SECRET` ≠ dev. `APP__URL` env = public URL (CORS + invite/reset link base).
- **Backups:** nightly logical dump 02:30 UTC via a Container Apps Job (separate image; neither
  deploy path touches it) into the private `db-backups` container; 30-day retention; log-based
  Sev1 alerts (`ai-hub-db-backup-failed`, `-missing`). Restores via the manual restore job —
  **never write a procedure assuming local `pg_restore`**. Runbook: `docs/db-backup-restore.md`.
  Azure PITR stays at the server default 7 days.
- **Health alerts:** app down (Sev1), 3+ 5xx in 15 min, container restarts (Sev2) → action group
  `ai-hub-app-alerts` (Matthias only; backup alerts keep `ai-hub-backup-alerts`, Matthias + Aaron).
  What each means and first checks: `docs/app-alerts.md` (`infra/60-app-alerts.ps1`).
- **Dependabot:** monthly minor/patch PRs only (majors are planned issues, e.g. #45); **alerts +
  security updates are ON** (2026-09-28), so a security PR can arrive any time. `CONTRIBUTING.md`.
- **Verifying without touching live data:** dump production-shaped fixtures via read-only
  service calls, serve from a temporary `frontend/public/__verify/`, stub `window.fetch` in a
  Playwright `addInitScript` (page context — the MCP host has no `fs`/`fetch`). Assert on
  `getComputedStyle`, not just screenshots, and exercise the load window
  (`waitUntil: 'commit'` + delayed response) — `networkidle` hides first-paint bugs.

## Key facts & open items

- **Re-invite done:** the migrated users have been re-invited (Matthias, confirmed 2026-09-30).
  A learner who can't log in (invite link unused after its 14 days, or a forgotten password) gets
  a fresh link from **Re-send invite / reset** on the admin People page; its **Invited** filter
  lists everyone who hasn't set a password. A hosting or domain move needs no re-invite, because
  passwords live in the DB: learners just get the new address.
- **Entra ID:** blocked on one-time tenant admin consent (in the IT ticket). App registration
  "AI Enablement Hub" `ad61703c-684f-4392-b786-8926ba2ab69d`; client secret 'hub-oidc' expires
  July 2028. After the grant: test on :5173, then wire prod env (`az containerapp secret set` +
  `ENTRA__*` — ask first).
- **Hosting move (IT ticket, 2026-07-06):** delaware IT deems the playground not secure enough for
  a client-facing app — new hosting, custom domain `ai-enablement-hub.delaware.pro`, Entra consent
  and an ACS custom email domain are bundled in one ticket (Matthias's name). Until it lands, the
  playground deployment is the live one. Custom-domain recipe: `docs/history/state-log-2026.md`.
- **LLM spend:** prod carries `llm-api-key` and admin-reachable AI spend is live; whether the key
  is capped is unverified — issue #44.
- **Emails:** ACS `imaginemore-playground-acs`; local `.env` sends REAL email (`backend/CLAUDE.md`).
- **Owed rotations** (deliberately unscheduled): dev `AUTH__JWT_SECRET`, leaked 2026-07-06 (#42),
  and the `aienablementhubmedia` storage key, leaked 2026-07-30 (#43) — `SECURITY.md` → Rotations owed.
