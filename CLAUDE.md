# AI Enablement Hub — Azure Rebuild

Greenfield rebuild of the hub (old app lives untouched in `../app/` on Supabase+Vercel until
cutover). Stack: **FastAPI** (Python 3.13, uv) + **React 18 + TypeScript** (Vite) + **Azure
Database for PostgreSQL** (playground server, database `ai-enablement-hub`).

## Read before working

1. `docs/rebuild-plan.md` — the approved plan: decisions, endpoint contract summary, batch
   sequence. Work is executed **batch by batch with user review between batches**.
2. `python-be-architecture.md` — **MANDATORY** backend conventions (delaware template):
   router → service → repository → model layering, `src/` layout, abstract repositories,
   DI in `core/dependencies/`, poe tasks, bcrypt, ruff/ty clean, ≥80% coverage.
   Two approved deviations: asyncpg is a main dependency (dev DB is Azure PG, not SQLite);
   integration tests run against the `ai-enablement-hub-test` PG database, not in-memory
   SQLite (schema uses text[]/JSONB/ON CONFLICT).
3. `docs/design/design-backend.md` — full 29-endpoint contract, auth design, authz matrix,
   scoring-port notes. `design-frontend.md` / `design-database.md` for Batches 4–6.
4. `db/README.md` — database roles, credentials locations, migration/verification procedures.

## Batch status

- **Batch 1 DONE (2026-07-03):** schema (15 tables, Alembic `5cd94241caf6`) + all data on
  Azure, verified. Roles `ai_hub_owner` (DDL) / `ai_hub_app` (app DML) with default
  privileges configured. Users migrated with `password_set=false` — re-invite manually once
  auth exists.
- **Batch 2 DONE (2026-07-03):** auth core — `core/security.py` (bcrypt + HS256 JWT +
  opaque-token helpers), `services/token_service.py` + `user_service.py`, repositories
  (user / auth_token / auth_session), `routers/auth.py` (login / refresh / logout /
  set-password / invite-info), `core/dependencies/auth.py` (`get_current_user`,
  `require_admin`), error-shape handlers (`{"error":{code,message[,fields]}}`).
  73 tests green (unit + integration on the PG test DB), coverage 97%.
  `AUTH__JWT_SECRET` now required in `backend/.env`.
  Deferred to Batch 3 per design build order: rate limiting, CORS, daily token-cleanup task.
- **Batch 3 DONE (2026-07-03):** all remaining routers — `me`, `survey`, `learning` (incl.
  `/learning/graph` aggregate), `admin_org`, `admin_users` (invites/reset wired to the Batch 2
  token service), `admin_content` (module-insert shifting, batch lesson reorder). 37 API
  endpoints + `/api/health` live at `/docs` (design §3 fully covered; its "29 total" line was
  a miscount of its own table). `services/scoring.py` is a pure port of `scoring.js` proven by
  `tests/golden/scoring_golden.json` (582 cases generated from the REAL legacy scorer by
  `tests/golden/generate_scoring_golden.mjs`; re-run only if scoring.js changes). Deferred
  cross-cutting landed: `core/ratelimit.py` (fixed-window port of rateLimit.js; login/set-password/
  invite/reset-link), CORS (`APP__URL`/`APP__ENV` settings), daily auth-cleanup lifespan task.
  Domain errors: services raise `NotFoundError`/`ConflictError`/`DomainError`/`ScoringError`;
  main.py exception handlers map them to 404/409/400/422 in the standard error shape — routers
  stay try/except-free. Re-score parity vs the real Azure data: every legacy-scored row matches
  exactly (`scripts/rescore_parity.py`); one migrated row (16797147…) was `complete` but
  never scored by the old app (completed 2026-06-25 09:42 UTC, hours before scoring shipped
  in old-app commit ae0d2da) — **backfilled on Azure 2026-07-03** (user-approved) via
  `rescore_parity.py --backfill-unscored` → integrator/embedded; parity now compares 2/2 clean.
  The flag only touches rows where every scored column is NULL. The live Supabase DB still
  has the blank (untouched by design — it stays authoritative until cutover), so a re-run of
  the Supabase→Azure migration resurrects the NULLs: re-run the backfill afterwards.
  **Deviation:** `col_offset` (graph nodes + POST /admin/modules in design-backend §3) is
  omitted — the live DB has no such column and the old frontend never reads it
  (design-database.md documents the stale-doc history).
  781 tests green (584 golden/scoring + authz matrix over every endpoint × 3 auth levels +
  flow suites), coverage 98%. The `/api/_test/*` conftest endpoints from Batch 2 are gone —
  authz tests now run against the real routes.
- **Batch 4 DONE (2026-07-03):** frontend foundation + auth spine. `frontend/` scaffolded
  by hand (Vite 6, React **18.3.1 pinned**, react-router-dom **v6**, framer-motion 12,
  openapi-fetch; tsconfig strict with `noUncheckedIndexedAccess` OFF for the port; ESLint 9
  flat config). Vite proxy `/api → :8000` is load-bearing (one origin in dev, no CORS on the
  happy path; old app on 3000, new on 5173 side-by-side). API layer: `npm run gen:api`
  regenerates the **committed** `src/api/schema.d.ts` (backend must be running); `api/tokens.ts`
  is the localStorage pair + `subscribe()` logout broadcast (the MSAL/Entra swap seam);
  `api/client.ts` attaches Bearer and on 401 runs a **single-flight refresh** then one retry
  (refresh tokens rotate on every use — two parallel refreshes would revoke each other into a
  logout loop; browser-proven: 3 concurrent 401s → exactly 1 refresh POST). Everything under
  `/api/auth/*` is middleware-exempt (its 401s are answers, not expiry). lib/ ports done
  (constants, surveyOptions + derived code unions, contentBlocks factories, mdxParser,
  blocksToMdx) over the hand-written `types/contentBlocks.ts` 7-type union. AuthContext keeps
  the old provider shape minus `isRecovery`; login = POST /auth/login → pair + `GET /api/me`
  (contract deviation from design-frontend §2: login returns only the token pair, no user
  object); session restore = stored token + `GET /api/me`. Invite flow: the **URL token is
  the credential** — `InviteRedirect` peeks `GET /api/auth/invite/{token}` (410=expired,
  404=invalid) → `/set-password?token=…` → one atomic `POST /api/auth/set-password` sets the
  password AND returns login tokens. Login page: 401 → old error text; **429 is shown, never
  auto-retried** (5/min/email limit). `JourneyHome` and /admin,/assessment,/learning,
  /interview are placeholders (ComingSoon) until Batches 5–6 — guard semantics are final.
  Bootstrap tool: `uv run python scripts/issue_invite.py <email>` (backend/) mints an invite
  link directly through TokenService — solves the migration chicken-and-egg (all users
  `password_set=false`, but POST /api/admin/invites needs an admin token). All flows verified
  in real Chromium against the live backend (invite→set-password→auto-login, reload restore,
  refresh rotation ×2, single-flight, consumed-link reuse, logout, wrong password, admin
  guard). Frontend checks after changes: `npm run typecheck && npm run lint && npm run build`
  (run inside `frontend/`).
- **Batch 5 DONE (2026-07-03):** learner pages — JourneyHome (one `GET /api/me/journey`;
  survey_status is `'not_started'|'in_progress'|'complete'`, NOT the design doc's `'none'`),
  Assessment (967-line port; `GET/PUT /api/survey/me` + `POST /api/survey/complete`; answers
  typed via the surveyOptions-derived unions, `c5_codes: C5Code[]`), ModulePopup + LearningPath
  (one `GET /api/learning/graph` — the design doc's `/api/learning/path` name is stale; backend
  returns ALL tracks/modules with per-caller `assigned` flags, frontend filters to assigned
  tracks → assigned modules, same joins as the old 7-query chain; `col_offset` never existed in
  this page — nothing to drop), lesson `blocks/*` (7 renderers + renderInline) + LessonView
  (`RENDERERS` map exhaustively keyed on `ContentBlock['type']`) + LessonPage VIEW+PROGRESS
  (one `GET /api/lessons/{id}` aggregate — `next_lesson_id` already resolves the cross-module
  hop server-side; complete = `PUT /api/lessons/{id}/progress {answers}`, NOT `/complete`;
  sidebar = `GET /api/modules/{id}/lessons`). content_blocks crosses the JSONB boundary with
  ONE cast in LessonPage; CardsBlock tolerates the legacy what/useCase/tools card shape found
  in real data. Dead nav style blocks (D2) dropped in JourneyHome AND Assessment (same dead
  class); `let cancelled = false` in every fetch effect (A5). **Deliberate behavior fix over
  the old app:** LessonPage never remounts between lessons, so the old app leaked
  quizDone/completing across navigations (next lesson's quiz gate silently open); the port
  resets per-lesson UI state on lessonId change and memoizes `onQuizComplete` with useCallback
  — the stable identity is load-bearing (an inline arrow makes the still-mounted previous
  quiz's completion effect refire and undo the reset). NOT ported (Batch 6): LearningPath edit
  mode (ModulePanel/AddTrackModal/AddModuleModal), LessonPage edit+MDX modes, `editors/*`.
  tsc gotcha: `current?.type === x` on a loop-carried `let current: T | null` resolves to
  `never` under tsc 5.6 — use `current && current.type === x` (ParagraphBlock). Verified in
  Chromium against the live backend + real Azure data: all three survey states on JourneyHome
  (hidden interview filtered, locked learning, Being-built badge), assessment full flow +
  mid-step reload-resume + c5 multi-select + read-only revisit, graph (19 nodes/20 edges for
  the real dataset), popup continue→first-uncompleted, quiz all-correct gate, complete→next
  lesson, cross-module hop, empty-module popup disabled, reload on every route; completion
  scored practitioner/regular via the admin API. Outstanding: pixel side-by-side vs the old
  app on :3000 needs Matthias's live Supabase login (Azure password ≠ Supabase password);
  `question` blocks exist in no real lesson, so that renderer is type-checked but not
  browser-exercised. Test artifacts left on Azure (flagged to Matthias): matthias's completed
  survey row + 4 lesson_progress rows (What-AI-is ×3, Beyond-chat) — his 2 pre-existing Intro
  rows are untouched.
- **Batch 6 DONE (2026-07-03) — the rebuild is FEATURE-COMPLETE.** Admin pages + edit modes:
  adminStyles.ts (`satisfies Record<string, CSSProperties>`; D3 dead nav/avatar/dropdown styles
  dropped, navBadge/navDivider/navTabs* kept for the AppNav leftExtra tab strip) + adminHelpers.tsx
  (LevelBadge/BandBadge/RungPill typed; unknown level/band strings render nothing, as before);
  Admin.tsx shell (God component kept per A1; both hand-rolled `authH` patterns replaced by the
  typed client — A2 fixed; the old `loadingLearning` state was dead even in the old app — dropped);
  ProjectsView/SetupView/ProjectDetailView/UserPanel/SurveyResults (typed from AdminSurveyOut;
  COMPETENCY_QA key/field narrowed to literal unions so rung/code lookups need no casts);
  AddTrackModal (tracks prop dropped — server assigns sort_order) / AddModuleModal / ModulePanel
  (reorder = ONE batch PUT, fixes B5); LearningPath edit mode restored (banner, +Add Track/Module,
  per-node edit targets, floating toggle; track-zoom + popup targets disabled in edit mode);
  editors/* (7, each typed to its union member, `onChange: (b: XBlock) => void`) + LessonEditor
  (EDITORS map exhaustively keyed like LessonView's RENDERERS; saves via
  `PATCH /api/admin/lessons/{id}`) + LessonPage edit+MDX modes. Batch 5's per-lesson state reset
  and useCallback'd onQuizComplete are untouched; **LessonPage passes a useCallback'd onLiveChange
  to LessonEditor for the same reason** — an inline arrow refires the editor's live-change effect
  every render (each firing setLesson's a fresh object) = infinite loop; the old app passed the
  bare `setLesson`.
  **Admin endpoint drift (design-frontend §3 admin rows are stale, same class as Batch 5's):**
  real contract per schema.d.ts — projects are `POST /api/admin/projects` (NOT a `type:'project'`
  variant of /admin/companies; both creates return the bare row, no `{company}`/`{project}`
  wrapper); components `GET /api/admin/projects/{id}/components` +
  `PUT …/components/{component} {hidden?,locked?}`; invites `POST /api/admin/invites`; reset
  `POST /api/admin/users/{id}/reset-link` (no email body); role `PATCH /api/admin/users/{id}`;
  delete `DELETE /api/admin/users/{id}`; assignment `PUT /api/admin/users/{id}/tracks/{tid}` and
  `…/modules/{mid}` with `{assigned}`; surveys `GET /api/admin/surveys?user_ids=csv` +
  `GET /api/admin/surveys/{user_id}`; content `POST /api/admin/tracks`, `POST /api/admin/modules`
  (NO col_offset — never existed; omitted after_module_id = append, matching the old modal),
  `POST /api/admin/lessons`, `PATCH|DELETE /api/admin/lessons/{id}`,
  `PUT /api/admin/modules/{id}/lessons/order {lesson_ids}`.
  Parity findings: freshly invited users show the **active** badge — `is_active` defaults true in
  BOTH schemas and the old invite handler never set it false, so the `invited` state is unreachable
  via UI in the old app too. Editor **Save exits edit mode** to the learner view (old handleSave
  behavior). Browser-verified in Chromium against live backend + real Azure data using disposable
  ZZ-B6-prefixed entities: setup create company/project; invite → copy link → fresh-context
  redemption → auto-login; consumed-link reuse rejected; maturity badges (real Delaware users,
  read-only) + UserPanel survey results; component toggles persist across reload AND reflect on
  the learner's JourneyHome (learning unlocked, interview hidden); role toggle user↔admin
  (disposable user only); add track via modal (server sort_order=max+1) + 3 modules incl. a
  modal-set prerequisite; **module-insert shifting** verified via API `after_module_id`
  (A,A2,B,C = 0,1,2,3 after inserting A2 after A — no UI control for it, same as old app);
  track/module assignment reflected on the learner's graph (unassigned module filtered, prereq
  edge drawn); ModulePanel add/reorder/delete lessons, reorder survives reload; editor live
  preview + save persistence; MDX round-trip (prefill via blocksToMdx → paste → 5 blocks parsed →
  save as blocks → learner-view render with quiz gate); reset-link generate/copy → fresh-context
  redemption → old password 401; token-expiry spot check (corrupted access token → transparent
  single-flight refresh); reload on every route incl. /admin; logout. Cleanup: disposable user
  (UI confirm flow, cascade) + 2 lessons (`DELETE /api/admin/lessons`) removed — 6 real users
  intact. **Leftovers needing Matthias's DB-level cleanup approval (no DELETE endpoints exist for
  these):** company 'ZZ-B6 Test Co', project 'ZZ-B6 Project' (+3 component-settings rows), track
  'ZZ-B6 Track' (sort_order 7), modules 'ZZ-B6 Mod A/A2/B/C' (+1 prerequisite row A→B).

## Open for cutover

- Pixel side-by-side old app (:3000, live Supabase) vs new (:5173) — blocked on Matthias's
  Supabase password (≠ Azure password).
- Azure test-artifact cleanup (needs approval; direct DB deletes are permission-blocked):
  Batch 5 — matthias's completed survey row (practitioner/regular) + 4 lesson_progress rows;
  Batch 6 — the ZZ-B6 leftovers listed above.
- Real migrated users still have `password_set=false` (all but matthias) — re-invite via the
  admin UI once cutover is scheduled.
- `question` content block: typed + rendered + editable, but exists in no real lesson — never
  browser-exercised end to end.
- Deployment (Azure hosting, CSP incl. `style-src 'unsafe-inline'`, env wiring) was never in
  batch scope.

## Key facts

- Secrets: `db/.env` and `backend/.env` (both git-ignored). `backend/.env.local.example`
  documents keys. Rotate with `db/provision_roles.py --rotate-passwords`.
- Auth model: FastAPI-native JWT (PyJWT HS256, 30-min access + rotating 14-day refresh in
  `auth_sessions`), invite/reset via SHA-256-hashed single-use tokens in `auth_tokens`.
  Designed for a later Entra ID swap: keep token verification inside one dependency and key
  users by internal UUID (`users.external_id` reserved for the Entra OID).
- Authorization iron rule (tests must enforce): **no endpoint outside `/admin/*` accepts a
  user identifier from the request** — ownership comes from the token only.
- Backend checks after changes: `uv run poe format && uv run poe lint && uv run poe test`
  (run inside `backend/`).
- **FastAPI signature gotcha:** any type used in a *parameter* annotation that FastAPI
  inspects (routers, DI providers in `core/dependencies/`) must be imported at runtime,
  not under `TYPE_CHECKING` — with deferred annotations an unresolvable name silently
  degrades the param to a required query param (uniform 422s). Return-type-only imports
  may stay type-only.
- Integration tests derive their DSN from `ALEMBIC_DATABASE_URL` with the database swapped
  to `ai-enablement-hub-test`; schema is created per session from `Base.metadata`, isolation
  is per-test savepoint rollback (`join_transaction_mode="create_savepoint"`).
- The old Supabase project stays live until cutover; refresh + reload data via
  `db/export_supabase_snapshot.py` then `db/migrate_supabase_to_azure.py` (destructive on
  Azure — see db/README.md).
