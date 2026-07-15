# AI Enablement Hub — Azure Rebuild

Greenfield rebuild of the hub (old app lives untouched in `../app/` on Supabase+Vercel — frozen,
historical only). Stack: **FastAPI** (Python 3.13, uv) + **React 18 + TypeScript** (Vite) +
**Azure Database for PostgreSQL** (playground server, database `ai-enablement-hub`).

**Cutover is complete (confirmed 2026-07-08).** This rebuild is production — the app real
learners use. Content edits via the admin UI (`PATCH /api/admin/lessons/{id}`) write directly to
this Azure DB with no separate export/sync step. The old Supabase project is no longer
authoritative for anything; see `db/README.md` for why its migration scripts must not be re-run.

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

- **Lesson assignment (2026-07-06, post-Batch 6):** per-lesson assignment via new
  `user_lessons` table (mirrors user_modules; migration `a3f8c1d2e4b7` backfills all lessons
  of every existing user↔module assignment, so current learners keep what they see today).
  Semantics: assigning a module does NOT auto-assign its lessons — the admin picks lessons in
  the UserPanel (module row expands to a lesson list) or clicks "+ add all lessons"; tracks
  got "+ add all modules". Every level (tracks section header / track's module list / module's
  lesson list) has BOTH "+ add all" and "− unassign all" buttons (shown only when applicable).
  Bulk = ONE call: `PUT /api/admin/users/{id}/tracks` / `…/modules` /
  `…/lessons` `{track_ids|module_ids|lesson_ids, assigned}` (404 if any id unknown, 422 on
  empty list);
  single lesson toggle = `PUT …/lessons/{lesson_id} {assigned}`. Unassigning a module/track
  KEEPS the child assignment rows (same keep-rows semantics the old track→module pair already
  had — reassigning restores the previous selection). Learner side: graph `lesson_count`/
  `completed_lesson_count` now count ONLY the caller's assigned lessons (one SQL in
  AssignmentRepository.assigned_lesson_counts_by_module); `GET /api/modules/{id}/lessons`
  returns ALL lessons with per-caller `assigned` flags (admin ModulePanel needs all — learner
  sidebar + ModulePopup filter client-side, graph pattern) and `next_lesson_id` = first
  uncompleted ASSIGNED lesson; lesson_detail's next-hop skips unassigned lessons (repo methods
  next_lesson_in_module/first_lesson/lesson_counts_by_module/completed_counts_by_module were
  removed — filtering happens over list_lessons). Assignment stays a visibility filter, not
  access control (direct lesson URLs still render — parity with module semantics).
  `GET /api/admin/learning` gained `lessons[]` + per-user `assigned_lesson_ids`;
  AdminUserOut too. LearningPath's prerequisite unlock (`completed === total`) now means
  "all assigned lessons completed"; a prereq module with 0 assigned lessons keeps its
  dependents locked (0/0 also disables the popup start button, so it's admin-visible).
  794 backend tests green (13 new: authz matrix ×3 new endpoints, bulk/single assignment
  flows, filtered counts/next). **Migration NOT yet applied to the dev Azure DB** (needs
  approval; prod applies it automatically on next deploy via startup.py's alembic upgrade).

- **Invite/reset emails (2026-07-06, post-Batch 6):** POST /api/admin/invites and
  POST /api/admin/users/{id}/reset-link now auto-email the link to the user via **Azure
  Communication Services** (`azure-communication-email`, sync EmailClient in
  `run_in_threadpool`, retry_total=0 + bounded timeouts, LRO poller deliberately not awaited
  — "sent" = ACS 202). Feature-flagged like Entra: `Settings.email: EmailSettings | None`
  (`EMAIL__CONNECTION_STRING` + `EMAIL__SENDER_ADDRESS`, both-or-neither); None = exactly the
  old copy-the-link behavior. `LinkResponse` gained REQUIRED `email_status:
  "sent"|"failed"|"disabled"`; a failed send never fails the endpoint (log + fallback link).
  Invite email offers BOTH sign-in paths — "Sign in with your Microsoft account" →
  `{APP__URL}/login` (rendered only when `settings.entra` is configured) + the set-password
  link; reset email = link + TTL + "current password keeps working". Templates =
  `services/email_templates.py` pure functions (f-strings + html.escape, no engine); service
  seam = `EmailSender` Protocol (stubbed in tests, `tests/fixtures/email.py`); DI
  `get_email_service` returns None (NOT 404 — endpoints exist regardless) when unconfigured.
  conftest `test_settings` pins `email=None` for hermeticity. Frontend: invite card + reset
  row show emailed/failed indicators, link box + copy button stay in all cases
  (`inviteEmailStatus` in ProjectDetailView, `ResetLinkEntry.emailStatus` in Admin.tsx).
  861 backend tests green. Azure infra ALREADY EXISTS (nothing to provision):
  `imaginemore-playground-acs` + `imaginemore-playground-email`/AzureManagedDomain (verified,
  linked); sender `hub@c07b8f9c-80df-4e8a-9fb1-5671cfd049a5.azurecomm.net` (sender username
  `hub`, display name "AI Enablement Hub", created 2026-07-06; the default `DoNotReply`
  username also still exists). Domain part is fixed until a custom email domain is verified
  (delaware DNS — bundle with the cutover custom-domain ticket).
  **Azure config DONE 2026-07-06 (user-approved):** Container App secret
  `acs-connection-string` + `EMAIL__CONNECTION_STRING` (secretref) + `EMAIL__SENDER_ADDRESS`
  are set on the live app — the deployed OLD image ignores them (its Settings has no `email`
  field, `extra="ignore"`), so prod behavior is unchanged until the next `.\deploy.ps1`.
  deploy-initial.ps1 fills the yaml placeholder via `az rest` listKeys for DR parity.
  **Local dev .env now carries EMAIL__* too → local invites/resets send REAL email** via the
  shared playground ACS (remove/comment the two lines to go back to copy-link-only).
  `scripts/issue_invite.py` intentionally does not send email.

- **Entra ID login (2026-07-06, post-Batch 6) — code-complete, BLOCKED on one-time IT admin
  consent.** Runs SIDE-BY-SIDE with password auth (approved plan
  `C:\Users\danneelm\.claude\plans\could-you-create-a-hazy-canyon.md`) — this supersedes the
  design docs' full-MSAL-swap sketch: instead, a **server-side confidential-client OIDC
  authorization-code flow (+ PKCE)** whose end product is the app's EXISTING native token
  pair, so refresh rotation / middleware / `get_current_user` / all prior tests are untouched
  and password login keeps working (externals rely on it — the single-tenant registration
  blocks non-delaware accounts at Microsoft with AADSTS50020 before our code runs).
  Endpoints (`routers/auth_entra.py`): `GET /api/auth/entra/login` → 302 to the tenant
  authorize URL (`prompt=select_account`, scope `openid profile email`, S256 challenge) +
  signed state cookie `entra_oidc` (HS256 JWT `typ:"entra_state"` via the existing
  AUTH__JWT_SECRET, carries state/nonce/code_verifier, 10-min, HttpOnly SameSite=Lax
  `Path=/api/auth/entra`, Secure only when `app.env=prod`); `GET /api/auth/entra/callback` →
  state check → httpx code exchange (`EntraService`, client secret + verifier) → RS256
  id_token validation (`@lru_cache` PyJWKClient run in threadpool — sync urllib, never on the
  loop; iss/aud/exp/nonce, leeway 60 s, identity claim = **`oid`**, never `sub`) →
  invite-gated `resolve_user` → one-time redeem code → 302 `{APP__URL}/auth/callback#code=…`
  (fragment = never in server logs; ALL failures → 302 `/login?error=invalid_state|
  not_invited|entra_denied|entra_failed|rate_limited`, never JSON on a top-level navigation);
  `POST /api/auth/entra/redeem {code}` → `TokenPairResponse` (404 used/unknown, 410 expired,
  429); public `GET /api/auth/methods` `{password, entra}` drives the Login button.
  Feature-flagged like email: `Settings.entra: EntraSettings | None` (`ENTRA__TENANT_ID/
  CLIENT_ID/CLIENT_SECRET`, all-or-nothing → partial config fails startup), `get_entra_service`
  dep 404s when unset. Redeem codes reuse auth_tokens (purpose `entra_login`, 60 s TTL,
  migration `c7d2e9f0a1b3` extends the CHECK); **security-critical:**
  `peek/consume_action_token` are now purpose-filtered (default `("invite","reset")`) so a
  leaked login code can never reach set-password/invite-peek and vice versa — regression
  tests pin this. `resolve_user`: linked oid first (email drift logged, oid wins) → else
  email match (`email` claim FIRST, `preferred_username` fallback — delaware UPN
  `danneelm@delawareconsulting.com` ≠ hub email `matthias.danneel@delaware.pro`) → one-time
  `link_external_id` backfill; same-email-different-oid → reject loudly; NEVER provisions
  (invite-gating preserved — invited users can skip the invite link entirely and onboard via
  the Microsoft button). `/api/me` gained `external_login` (User property on `external_id`);
  frontend gate is now `needsPassword = session && !passwordSet && !externalLogin`.
  Frontend: Login.tsx fetches /methods, shows the Microsoft pill button + "or" divider, maps
  `?error=` codes to friendly text then scrubs the param; new `pages/AuthCallback.tsx` parses
  the fragment code → redeem → `setTokens`+`refreshProfile` (a `useRef` fired-guard is
  load-bearing — StrictMode's dev double-effect would burn the single-use code); public route
  `/auth/callback`. Deps: `httpx` + `cryptography` promoted to main (PyJWT RS256 hard-requires
  cryptography). Tests: `tests/fixtures/entra.py` (module-scope RSA keypair, RS256 id_token
  mint, StubJWKS, FakeTokenEndpoint via httpx.MockTransport) + unit matrix (authorize-URL,
  exchange, id_token incl. HS256 alg-confusion, resolve_user incl. conflict edges) +
  integration flows (full happy path with PKCE round-trip assert, state/cookie failures,
  not-invited leaves no row, rate limits, purpose confusion) — 849 green at feature
  completion (the email entry's 861 is the later combined total). **Azure (all
  user-approved 2026-07-06):** app registration **"AI Enablement Hub"** appId
  `ad61703c-684f-4392-b786-8926ba2ab69d` (SP `f2d141e6-3f33-470a-9456-a123adef4cda`),
  single-tenant, web redirect URIs = prod CA URL + `http://localhost:5173`, each +
  `/api/auth/entra/callback`; client secret **'hub-oidc' expires July 2028** (rotate:
  `az ad app credential reset --append` → CA secret update → revision restart);
  requiredResourceAccess declares delegated openid/profile/email so IT's consent is one
  click. Dev `backend/.env` carries real ENTRA__* values; **prod CA env NOT wired** (needs
  `az containerapp secret set entra-client-secret=…` + `--set-env-vars ENTRA__…` — ask
  first; until then the feature deploys dark). **BLOCKER:** the tenant's
  `microsoft-user-default-low` self-consent policy covers only permissions classified low
  and delaware classified ONLY `profile` → sign-in hits "Beheerdersgoedkeuring vereist";
  fix = one-time tenant-wide admin consent (portal → App registrations → AI Enablement Hub →
  API permissions → Grant admin consent), requested via IT (in the 2026-07-06 hosting
  ticket). Local e2e verified up to Microsoft's consent wall (302 + params + cookie correct
  through the Vite proxy); full flow untested pending the grant. B2B guest sign-in for
  externals would work with this code as-is IF IT allows it (invite policy says members may
  invite guests, but cross-tenant access / domain restrictions / Conditional Access are
  unreadable to members — IT to confirm). Later removal of password auth = delete
  login/set-password/invite-peek + Login form/SetPassword/InviteRedirect; the token-pair
  stack stays.

- **Module delete (2026-07-07):** `DELETE /api/admin/modules/{module_id}` (admin-only, 204;
  404 if unknown) — `ContentService.delete_module` fetches then hands the ORM row to
  `ContentRepository.delete_module`, a plain `session.delete()` + commit; FK `ondelete="CASCADE"`
  on lessons/module_prerequisites(both columns)/user_modules/user_lessons(via lessons)/
  lesson_progress(via lessons) does the rest — no manual cleanup code needed. ModulePanel
  (edit-mode lesson popup) gained a "Delete module" danger-zone button below the lesson list;
  confirmation is an in-panel two-step swap (button → warning text + Cancel/"Yes, delete",
  lesson count in the warning), NOT `window.confirm` — the native browser dialog reads as an
  out-of-app interruption (feedback from browser-testing this feature 2026-07-07). On success
  calls the new `onDeleted` prop, which LearningPath wires to close the panel + `reload()` the
  graph. Backend tests: cascade assertions across all four child tables + 404 + authz-matrix
  entry (`module-delete`), 68 tests green in `test_admin_content.py`/`test_authz.py`. Frontend
  typecheck/lint/build clean; `schema.d.ts` regenerated. Not browser-verified this session (no
  browser automation tool available) — spot-check locally before relying on it.

- **Invite link/email split (2026-07-07):** the single "create invite link →" button on
  ProjectDetailView's add-participant form (which always both created the user AND attempted
  an email when EMAIL__* was configured, despite its label) is now two buttons: "create invite
  link →" (link-only, never emails) and "send email with invite →" (unchanged prior behavior).
  `InviteRequest` gained `send_email: bool = True` (backend default keeps any other caller's
  behavior unchanged); `POST /api/admin/invites` skips `_email_the_link` entirely when
  `send_email` is false and returns the new `EmailStatus` value `"skipped"` — distinct from
  `"disabled"` (EMAIL__* unconfigured) so the two "no email was attempted" reasons stay
  distinguishable in data, though the frontend already defaults both to the same "share the
  link below" copy (no branch change needed). `schema.d.ts` regenerated for real via
  `npm run gen:api` against a locally-launched dev backend (user-approved — its startup
  auth-cleanup DELETE against the real Azure dev DB ran once); the real generated
  `send_email` came out as a **required** field (matching how other defaulted fields like
  `token_type` are already typed in this schema), not optional as a first hand-patch attempt
  guessed. 865 backend tests green (1 new, in `test_admin_email.py::TestInviteEmails`,
  asserting the ACS sender is never invoked). Frontend typecheck/lint/build clean. Deployed
  live 2026-07-07 (see the Deployment section). Not browser-verified this session (no browser
  automation tool available) — spot-check the two buttons on ProjectDetailView before relying
  on it.

## Locking, prerequisites & preview (as-built; reviewed 2026-07-06)

- **Two independent lock systems that never interact:**
  - **Component level** (`assessment`/`learning`/`interview` hub tiles): `project_component_settings`
    over `DEFAULT_LOCKED = {assessment: false, learning: true, interview: true}`
    (`core/constants.py`), resolved server-side (`org_service.resolve_components`), served by
    `GET /api/me/journey`, rendered ONLY on JourneyHome. `hidden` = card filtered out entirely;
    `locked` = greyed inert card (title/description still visible). Completing the assessment
    does NOT unlock learning — despite the "Unlocks after assessment" copy and the
    "Being built" badge, unlock is a manual admin component toggle.
  - **Module level**: explicit `module_prerequisites` edge table (composite PK; only DB
    constraint is `not_self` — nothing blocks cross-track or cyclic edges; the frontend drops
    cross-track predecessors from layout and rank-guards cycles, but such rows would still
    lock dependents invisibly). The unlock rule exists ONLY in
    `LearningPath.tsx::isModuleUnlocked`: unlocked ⇔ admin OR no prereqs OR every prereq has
    assigned-lesson `total > 0 && completed === total` (counts are the caller's ASSIGNED
    lessons since the lesson-assignment feature). Graph layout ranks by prerequisite depth;
    `sort_order` is only a tie-breaker + the "next module in track" hop.
- **No prerequisites between tracks** (the dotted general→tool graph edge is decorative,
  `trackId: null`) and **none between lessons** (`sort_order` only; the sidebar allows
  skipping ahead; the quiz gate blocks "Mark as complete", not navigation).
- **Locks and assignments are visibility filters, NOT access control** (documented design,
  design-backend.md authz matrix): learning endpoints check auth + existence only —
  `GET /api/lessons/{id}` serves `content_blocks` for any lesson to any authenticated user,
  `PUT …/progress` accepts locked/unassigned lessons, and route guards check session only,
  so `/learning` and deep lesson URLs bypass both component and module locks.
- **Lock display:** graph node at 45% opacity + padlock badge; ModulePopup swaps to
  "Complete the required modules first…" with a disabled grey "Locked" button (the `disabled`
  attribute is the only guard — `handleStart` has no lock check); JourneyHome greyed card +
  LockIcon note. There is NO admin "view as learner" mode: admins bypass module locks but
  still see only their own assigned tracks.
- **Known quirks (accepted as-is 2026-07-06):** a prereq module with 0 assigned lessons locks
  its dependents forever (0/0 also disables the popup start button, so it's admin-visible);
  an UNASSIGNED prerequisite locks dependents with no edge drawn to explain why;
  `?edit=true` shows the lesson editor UI to non-admins (saves 403 via the admin-only PATCH);
  `GET /api/learning/graph` returns ALL track/module titles with `assigned` flags.

## Deployment (2026-07-03) — LIVE on Azure Container Apps

- **URL:** https://ai-enablement-hub.kindcoast-3b1fe056.swedencentral.azurecontainerapps.io
  (default domain; custom domain `ai-enablement-hub.delaware.pro` planned — DNS request to
  delaware IT is the blocker, full recipe under "Open for cutover").
- **Shape:** ONE container app (`ai-enablement-hub`, RG `imaginemore-playground`, env
  `imaginemore-playground-cae`, same pattern as siblings bta-portal/dellie: ACR admin auth,
  external ingress :8000, 0.5 CPU/1Gi, min=max=1 replica — single replica is a design
  constraint: rate limiter + daily cleanup are in-process). Image = multi-stage `Dockerfile`
  at repo root: node builds `frontend/` → uv installs backend deps → `python:3.13-slim`
  runs `startup.py` (alembic upgrade + uvicorn) and serves the SPA from `/app/static`.
- **main.py serves the frontend in prod:** SPA catch-all + `/assets` mount activate only
  when `backend/static/index.html` exists (never in dev). Security headers ported from the
  old vercel.json; CSP is skipped for `/docs`/`/redoc` (Swagger loads from jsdelivr);
  top-level `/assets/*` files get `immutable` caching (Vite hashes), subdirs (public/) 1 h.
- **Redeploy:** `.\deploy.ps1` at repo root (cloud build via `az acr build` — no local
  Docker — then `az containerapp update`). One-time create was `infra\deploy-initial.ps1`
  + `infra\containerapp.yaml` (only needed again if the app is deleted; health probes on
  `/api/health`, Startup probe budgets ~240 s because migrations run before the port binds).
- **Secrets** live as Container App secrets (`database-password`, `alembic-database-url`,
  `jwt-secret`, `acr-password`). The prod `AUTH__JWT_SECRET` is NOT the dev one (rotating
  it just logs everyone out). `APP__URL` env var = the public URL (CORS + invite/reset
  link base) — must change with a custom domain.
- **Gotchas:** `az acr build` uploads git-ignored files → `.dockerignore` excludes
  `**/.env` (load-bearing). **The old az CLI's .dockerignore matcher ignores `dir/`
  trailing-slash patterns when packing the upload** (found 2026-07-03: `db/` and
  `frontend/node_modules/` went up in the v1 build — no .env/secrets, but the baseline
  data export incl. invite_tokens.json landed in ACR's internal task storage; `**/.env`
  patterns DID work). Every dir in .dockerignore is now listed bare AND with `/**`.
  Verify any .dockerignore change by re-packing with az's own code and inspecting the
  tar: `_pack_source_code` from `azure.cli.command_modules.acr._archive_utils` (run with
  `C:\Program Files\Microsoft SDKs\Azure\CLI2\python.exe`). The az CLI on this machine is old
  (`C:\Program Files\Microsoft SDKs\Azure\CLI2\wbin\az.cmd`, not on PATH); set
  `PYTHONIOENCODING=utf-8` or its log streaming crashes on Vite's unicode output, and
  `infra/containerapp.yaml` must stay pure ASCII (az parses it with the system codepage).
- Verified live 2026-07-03: health, SPA deep links, headers/CSP, JSON 404 shape, hashed-asset
  caching, wrong-password login 401 (proves container→PG chain), full page load in browser.
- **Redeployed 2026-07-07** (`ai-enablement-hub:20260707-131607`, revision `--0000004`,
  user-approved): shipped everything committed since the 2026-07-03 deploy in one go — the
  lesson-assignment feature (prod DB migrated automatically via `startup.py`'s
  `alembic upgrade` on container start, now at `c7d2e9f0a1b3`), ACS invite/reset emails,
  dormant Entra ID login code (still dark — no `ENTRA__*` env vars set on the Container App),
  module delete, and the invite link/email split (see that feature entry). HEAD support on
  SPA routes rode along too. Health check green post-deploy; not further browser-verified
  this session (no browser automation tool available).
- **NOTE — this section lagged reality:** between 2026-07-07 and 2026-07-15 the app was
  redeployed several times (undocumented here), so maturity-gated learning, the learning-path
  redesign + level headers, lesson media/blob storage, feedback, bulk invite, email templates
  and interactive lesson blocks were all already live before the deploy below. When in doubt
  about what prod is running, query the live image tag, don't trust this log:
  `az containerapp show -n ai-enablement-hub -g imaginemore-playground
  --query properties.template.containers[0].image -o tsv`.
- **Redeployed 2026-07-15** (`ai-enablement-hub:20260715-131259`, revision `--0000012`,
  user-approved): "For Developers" track moved to the **multiplier** level (commit `1128515`).
  Prod was already at `20260715-094341` (built that morning), so the only delta was migration
  `d8e9f0a1b2c3` — widens the `tracks.required_level` CHECK to allow `'multiplier'` and flips
  the For Developers tool track `integrator → multiplier` (applied automatically on container
  start; prod alembic head now `d8e9f0a1b2c3`). Also `SurveyService._seed_assignments` extends
  the auto-assign ceiling to the top of the ladder for integrator scorers, so For Developers
  still auto-assigns on survey completion like the other tool tracks (maturity now gates its
  visibility until a learner closes out integrator). Health + `/api/auth/methods` green on
  `--0000012` (healthy startup ⇒ migration applied cleanly); the under-Multiplier rendering is
  not browser-verified this session (no browser automation + no prod login) — spot-check
  `/learning` as an integrator-level learner/admin.

## Open for cutover

- **HOSTING MOVE (IT meeting 2026-07-06) — changes the cutover picture:** delaware IT deems
  the Imagine More playground not secure enough for a client-facing app; the hub must move to
  a secured environment ("behind a firewall" — but public reachability for external client
  users is a stated requirement, likely WAF-fronted). Matthias is logging the IT ticket
  (drafted 2026-07-06) covering: new hosting location, custom domain
  `ai-enablement-hub.delaware.pro`, the Entra admin-consent grant, Entra for internal +
  external users (B2B guests vs invite flow = IT's call), and an ACS custom email domain
  (SPF/DKIM). Consequences when it lands: redeploy target changes (deploy.ps1 registry/RG/app
  names), app registration redirect URIs + `APP__URL` must be updated, and the playground
  custom-domain recipe below may be superseded. Until the ticket resolves, the playground
  deployment stays the live one.
- **Entra ID login (2026-07-06):** code-complete + dev-configured, BLOCKED on the one-time IT
  admin consent (see feature entry). After the grant: Matthias tests the full sign-in on
  :5173, then prod wiring (`az containerapp secret set` + `--set-env-vars ENTRA__…`, ask
  first) + redeploy — or fold prod wiring into the hosting move.
- **Custom domain `ai-enablement-hub.delaware.pro` (investigated 2026-07-06, not started —
  likely superseded by the hosting move above; recipe kept for the playground fallback):**
  delaware.pro DNS is hosted externally at NSclusters (`ns.nscluster.*`) — NOT Azure DNS, and
  no zone exists in any of our 3 subscriptions — so step 1 is a delaware IT/domain-team request
  for two records (bundle with the ACS custom email domain, see Invite/reset emails feature
  entry): CNAME `ai-enablement-hub.delaware.pro` →
  `ai-enablement-hub.kindcoast-3b1fe056.swedencentral.azurecontainerapps.io` and TXT
  `asuid.ai-enablement-hub.delaware.pro` =
  `0C86501110614A7AC723F46FFA0117AA481151D5B52994A21A2C9E18AFD4CE0C` (the app's
  customDomainVerificationId, subscription-level constant). No CAA records on delaware.pro
  (checked 2026-07-06) → managed-cert issuance unblocked. Once both records resolve
  (`Resolve-DnsName`): `az containerapp hostname add -n ai-enablement-hub -g
  imaginemore-playground --hostname ai-enablement-hub.delaware.pro`, then `... hostname bind`
  (same args + `--environment imaginemore-playground-cae --validation-method CNAME`; provisions
  the free managed cert, takes minutes), then `az containerapp update --set-env-vars
  APP__URL=https://ai-enablement-hub.delaware.pro` (new revision; CORS + invite/reset link base
  follow automatically — the only load-bearing runtime setting) — all Azure mutations, ask
  first. Afterwards update repo refs: `infra/containerapp.yaml` (APP__URL value), `deploy.ps1`
  + `infra/deploy-initial.ps1` (cosmetic printed URL), this file. The default
  azurecontainerapps.io URL keeps working alongside (rollback). Sequence BEFORE re-inviting
  users so invite links carry the final URL.
- ~~Invite/reset emails (2026-07-06): code-complete + tested, Container App secret/env vars
  ALREADY SET — only `.\deploy.ps1` remains, ON HOLD pending Matthias's localhost email
  check.~~ **DONE 2026-07-07** — deployed live (see the Deployment section's 2026-07-07 entry).
- ~~Lesson-assignment feature (2026-07-06) is code-complete + tested but NOT live in prod~~
  **DONE 2026-07-07** — prod DB migrated automatically on deploy, redeployed live (see the
  Deployment section).
- **DONE (2026-07-03):** side-by-side check old app vs new — Matthias reviewed the running
  app on :5173 and signed off.
- **DONE (2026-07-03):** Azure test-artifact cleanup (Batch 5 survey + lesson_progress rows,
  Batch 6 ZZ-B6 leftovers) — marked done by Matthias.
- Real migrated users still have `password_set=false` (all but matthias) — re-invite via the
  admin UI once cutover is scheduled.
- ~~`question` content block: typed + rendered + editable, but exists in no real lesson — never
  browser-exercised end to end.~~ **RESOLVED 2026-07-08** — first real use landed in the General
  track capstone (7.1, "Work through a real recurring task with AI") as a closing reflection
  prompt, alongside two new non-interactive/interactive block types added the same session
  (`interactive`: sort/predict/spot-the-flaw; `try_it_yourself`: card-style hands-on exercise
  box). See `frontend/src/types/contentBlocks.ts`.
- ~~Deployment (Azure hosting, CSP incl. `style-src 'unsafe-inline'`, env wiring) was never in
  batch scope.~~ **DONE 2026-07-03** — see the Deployment section above.

## Key facts

- Secrets: `db/.env` and `backend/.env` (both git-ignored). `backend/.env.local.example`
  documents keys. Rotate with `db/provision_roles.py --rotate-passwords`. The dev
  `AUTH__JWT_SECRET` surfaced in a tool transcript 2026-07-06 (dev-only blast radius) —
  rotate when convenient; prod uses a different secret.
- Auth model: FastAPI-native JWT (PyJWT HS256, 30-min access + rotating 14-day refresh in
  `auth_sessions`), invite/reset via SHA-256-hashed single-use tokens in `auth_tokens`.
  **Entra ID sign-in now exists SIDE-BY-SIDE** (server-side OIDC issuing the same native
  pair — see the feature entry; `users.external_id` = the Entra OID, linked on first
  Microsoft sign-in). The old "later Entra swap" design note is superseded: coexistence was
  chosen deliberately so externals keep the invite/password path.
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
