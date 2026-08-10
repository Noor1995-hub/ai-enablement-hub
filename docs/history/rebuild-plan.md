# Rebuild AI Enablement Hub: Supabase+Vercel → Azure (FastAPI + React/TS + Azure PostgreSQL)

## Context

The AI Enablement Hub (delaware internal tool: assessment survey, learning paths, lesson content, admin panel; ~6 users, 4 companies, ~200 DB rows) runs on Vercel (React 18 JS + Vite, Node serverless API) with Supabase (Postgres 17 + Auth). Goal: move to Azure. This plan rebuilds **database, backend, frontend**; Azure Container Apps hosting comes later (out of scope — local dev processes now).

**Decisions made with the user (2026-07-03):**
- **Backend:** Python FastAPI — replaces both the 13 Vercel endpoints AND the ~35 direct browser→Supabase queries (currently guarded only by RLS; the rewrite moves all authorization server-side, fixing issue S3 in `context.md`).
- **Auth:** FastAPI-native (email+password, hashes in own DB, self-issued JWTs), designed so **Entra ID can replace it later** (~30 changed lines in 2 functions + 1 router deleted + MSAL on frontend — see seam below).
- **Data:** migrate **everything**; users **re-invited manually** (admin copies link — same UX as today); **no automatic emailing**.
- **Location:** `AI ENABLEMENT HUB REBUILD/` (repo root, exists, empty) → `backend/`, `frontend/`, `db/`. Old app at `app/` stays untouched until cutover.
- **Dev DB:** Azure PG Flexible Server `imaginemore-playground-pg.postgres.database.azure.com` (PG 18), empty DB `ai-enablement-hub`, sslmode=require. Matthias is Entra admin (AAD-token psql for admin tasks); app uses dedicated password-auth PG roles.

**Supersedes** `migration-plan.md` (2026-07-02, strangler-fig in-place approach). Carried over: baseline export as rollback artifact.

**Verified live facts (this session, against Supabase project `tbeogvbjbaxgfwaoebfj`):** 14 tables; row counts: companies 4, projects 5, project_component_settings 8, users 6, invite_tokens 13, survey_responses 2, tracks 7, curricula 7, modules 27, module_prerequisites 23, lessons 25, user_tracks 18, user_modules 53, lesson_progress 4. 38 RLS policies extracted. `context.md` is stale in three places: **`modules.col_offset` does not exist** (live code doesn't use it either — graph layout uses `module_prerequisites`), `lesson_progress.answers` JSONB exists, content blocks have **7** types (incl. `question`). Only Postgres + Auth are used — no storage/realtime/edge functions. Full inventories: `...\Temp\claude\...\tasks\w6gij5bmr.output` (code) and `...\scratchpad\design-{backend,frontend,database}.md` (detailed designs this plan synthesizes).

## Governing convention: `AI ENABLEMENT HUB REBUILD/python-be-architecture.md` (MANDATORY for backend)

The delaware FastAPI template skill supplied by the user. Read it in full before writing backend code; apply every relevant rule:
- **Stack:** uv + Python ~3.13, FastAPI ~0.135, async SQLAlchemy 2.0 (`Mapped`/`mapped_column`), **asyncpg** (prod) / aiosqlite, Alembic (async env, autogenerate), pydantic-settings (frozen, `__` nesting, `SecretStr` computed DB URL with `?ssl=<mode>`), **bcrypt** in `core/security.py`, ruff + ty, pytest + pytest-asyncio(auto) + httpx ASGI client, poethepoet tasks, `startup.py` entrypoint.
- **Layering (downward-only):** router → service → repository → model. Pydantic `Create`/`Update`/`Response` schemas cross the HTTP boundary; services depend on `Abstract<Entity>Repository` ABCs; DI wiring in `core/dependencies/`; one AsyncSession per request from lifespan-owned engine on `app.state.db_engine`.
- **Layout:** `backend/src/{main.py, core/{configs,dependencies,security.py}, db/{base.py,models/}, repositories/, services/, routers/, schemas/}`, `backend/alembic/`, `backend/tests/{conftest.py,fixtures,unit,integration}`.
- Module conventions: `from __future__ import annotations`, `TYPE_CHECKING` imports, `__all__`, full type hints; `poe format` / `poe ty` / `poe test` green after changes. Coverage ≥80%.

**Documented deviations (justified):**
1. **Integration tests run against Postgres, not in-memory SQLite** — schema uses `text[]` (survey_responses ×5), JSONB, and `ON CONFLICT` upserts that SQLite can't represent faithfully. Keep the skill's fixture/DI-override structure exactly, but point the test engine at a disposable PG database (`ai-enablement-hub-test` on the playground server, or local Docker PG), with per-test truncate/rollback. Unit tests (services + AsyncMock repos) unchanged per skill.
2. Docker/distroless/CI sections deferred to the hosting phase; keep `startup.py` + poe tasks from day one so nothing restructures later.

## Entra-later seam (answers "how hard is the later swap?")

| Piece | Now | Entra later |
|---|---|---|
| `core/security.py` token decode | PyJWT HS256 self-issued | PyJWT + `PyJWKClient` vs `login.microsoftonline.com/{tenant}/discovery/v2.0/keys` (~20 lines) |
| `core/dependencies` `get_current_user` | claims `sub` → `users.id` | claims `oid` → `users.external_id`, first-login email-match backfill (~10 lines) |
| `routers/auth.py` | login/refresh/logout/set-password | deleted (MSAL owns login); invite degrades to "create user row" |
| Frontend `api/tokens.ts` + Login | localStorage tokens | MSAL `acquireTokenSilent`; Login page → redirect |
| Everything else | — | zero changes; roles stay in `users.role` |

---

# Workstream 0 — Baseline + DB provisioning (do first, ~½ day)

1. **Baseline snapshot** into `AI ENABLEMENT HUB REBUILD/db/baseline/` (needs PG17+ client tools; use the Supabase **session pooler** DSN — direct host is IPv6-only): `pg_dump --schema=public --schema-only --no-owner --no-privileges`, `--data-only --column-inserts`, and `-Fc` binary dump. Commit all three. This is the rollback record (Supabase project also stays live untouched).
2. **Provision roles on Azure PG** (as Entra admin via psql + AAD token; script in `db/provision_roles.sql`):
   - `ai_hub_owner` (LOGIN, runs Alembic + data migration, owns objects) and `ai_hub_app` (LOGIN, DML only).
   - GRANT USAGE/CONNECT + table/sequence privileges, **and** `ALTER DEFAULT PRIVILEGES FOR ROLE ai_hub_owner IN SCHEMA public GRANT ... TO ai_hub_app` — the `FOR ROLE ai_hub_owner` form is critical (default privileges are per-grantor; Alembic runs as owner). This permanently fixes the past "new tables lack grants" pain.
   - Verify with a probe: owner creates `_grant_probe`, app role SELECTs it without explicit grant, drop.
   - DB name has hyphens — double-quote `"ai-enablement-hub"` in SQL.

# Workstream 1 — Database schema + data migration (~1–2 days)

**Schema-as-code:** SQLAlchemy 2.0 models in `backend/src/db/models/` (one module per aggregate) are the source of truth; single hand-audited Alembic initial migration (`alembic revision --autogenerate` then hand-edit — autogenerate drops CHECK constraints; set `MetaData(naming_convention=...)` first). Alembic connects as `ai_hub_owner` (env override `ALEMBIC_DATABASE_URL`), app as `ai_hub_app`.

**Tables:** 12 tables 1:1 with live Supabase (keep UUID PKs `gen_random_uuid()`, JSONB, `text[]`, all CHECK/UNIQUE constraints, FK CASCADE per live DDL; promote survey_responses' unique *index* on `user_id` to a named UNIQUE constraint — the app upserts on it). Plus redesigns:
- **`users`**: drop `auth_id`; add `password_hash text NULL`, `external_id text NULL UNIQUE`; `updated_at` NOT NULL (SQLAlchemy `onupdate=func.now()` on users/survey_responses/project_component_settings — no DB trigger; all writes now flow through the app). `company_id` FK → RESTRICT, `project_id` → SET NULL.
- **`auth_tokens`** (replaces `invite_tokens`): `id, user_id FK CASCADE, purpose CHECK ('invite','reset'), token_hash UNIQUE (sha256 — raw token never stored), expires_at (7d invite / 24h reset), consumed_at, created_at`. Issuing a new token soft-invalidates older same-purpose tokens; expired rows deleted opportunistically (fixes DB2, no pg_cron).
- **`auth_sessions`** (refresh tokens): `id, user_id FK CASCADE, token_hash UNIQUE, expires_at, revoked_at, created_at, last_used_at`. Kept (vs. 24h-token-only alternative) to preserve today's persistent-session UX; dead code when Entra lands — acceptable.
- No RLS, no `is_admin()` on Azure — authorization is application-level only.

**Data migration:** idempotent Python script `db/migrate_supabase_to_azure.py` (psycopg3, runs as owner): TRUNCATE-and-reload in one transaction, FK-safe order (companies → projects → pcs → users → tracks → curricula → modules → prereqs → lessons → user_tracks → user_modules → survey_responses → lesson_progress), explicit column lists. Transforms: users get `password_hash=NULL, external_id=NULL, password_set=false`, lowercased email, coalesced updated_at; **invite_tokens not migrated** (13 stale Supabase links). Built-in verification gates: exact row counts (13 tables), PK-set md5 checksums per table, `sum(jsonb_array_length(content_blocks))` equality, survey field spot-checks, zero-orphan FK queries; non-zero exit on failure. Re-run once to prove idempotency.

# Workstream 2 — Backend (FastAPI, ~7–8 days)

Structure per the skill (see governing convention). Feature slices: `users/auth`, `org` (companies/projects/component settings), `content` (tracks/modules/prereqs/lessons), `learning` (assignments/progress/graph), `survey`. Pure logic in `services/scoring_service.py` (zero I/O) and token logic in `services/token_service.py`. Libraries: PyJWT (not python-jose — unmaintained; PyJWT has `PyJWKClient` for Entra later), bcrypt per skill, in-process rate limiter (~30-line port of `rateLimit.js` as a dependency; correct on a single process, PG-table fallback documented for multi-replica later).

**Auth endpoints (all public, rate-limited 5/60s):**
| Endpoint | Behavior |
|---|---|
| `POST /api/auth/login` | verify bcrypt; reject `password_hash IS NULL` or `is_active=false`; → `{access_token, refresh_token, user}` |
| `POST /api/auth/refresh` | sha256 lookup, unrevoked+unexpired, **rotate**, fresh access token |
| `POST /api/auth/logout` | revoke session row → 204 |
| `GET /api/auth/invite/{token}` | validate **without consuming** → `{purpose, email, first_name}`; 410 expired / 404 unknown-or-used |
| `POST /api/auth/set-password` | `{token, password}` → consume token, set hash + `password_set=true`, revoke other tokens/sessions, **auto-login** (replaces Supabase updateUser + complete-password-setup two-step) |

JWT: HS256, `sub`=internal user UUID, 30-min access / 14-day refresh, `iss`/`aud` claims. Invite link format: `{APP_URL}/invite/{raw_token}`, raw = `secrets.token_urlsafe(32)`.

**Full contract (29 endpoints; OpenAPI at `/docs` is the frontend's source of truth).** U=user, A=admin:
- `GET /api/me` (U) — profile (replaces AuthContext users-select). `GET /api/me/journey` (U) — `{components{hidden,locked} with server-side DEFAULT_LOCKED/HIDDEN fallback, survey_status}` (replaces JourneyHome's 2 queries; kills constant duplication D4).
- `GET /api/survey/me` (U) resume; `PUT /api/survey/me` (U) draft upsert on user_id, `max_length=2000` on free-text (fixes S5), 409 if complete; `POST /api/survey/complete` (U) scores + persists, 409 with clear message if no draft (fixes B3).
- `GET /api/learning/graph` (U) — **one aggregate** replacing LearningPath's 7-query chain: tracks(+assigned), modules(+assigned, lesson_count, completed_count), prerequisites. `GET /api/modules/{id}/lessons` (U) — lessons+completed+next (serves ModulePopup + sidebar). `GET /api/lessons/{id}` (U) — lesson + module + siblings + my_answers + next-lesson/next-module targets (fixes B4). `PUT /api/lessons/{id}/progress` (U) — upsert `{answers}`.
- Admin org: `GET/POST /api/admin/companies`, `POST /api/admin/projects` (+3 default component rows in same tx), `GET /api/admin/projects/{id}/components`, `PUT .../components/{component}`.
- Admin users: `GET /api/admin/users?project_id=`, `POST /api/admin/invites` → `{link}`, `POST /api/admin/users/{id}/reset-link` → `{link}`, `PATCH /api/admin/users/{id}` (role), `DELETE /api/admin/users/{id}` (FK cascades fix B2's atomicity by construction), `PUT /api/admin/users/{id}/tracks/{track_id}` + `.../modules/{module_id}` (`{assigned: bool}`), `GET /api/admin/learning`, `GET /api/admin/surveys?user_ids=` (DISTINCT ON, preserves B1 fix), `GET /api/admin/surveys/{user_id}`.
- Content: `GET /api/tracks` (U), `GET /api/tracks/{id}/modules` (U); admin writes: `POST /api/admin/tracks` (server-computed sort_order, fixes A4), `POST /api/admin/modules` (`{track_id, title, after_module_id?, prerequisite_ids?}` — server computes sort_order, shifts successors fixing DB6, inserts prereqs atomically; **no col_offset — doesn't exist**), `POST /api/admin/lessons`, `PATCH /api/admin/lessons/{id}` (title/content_blocks), `DELETE /api/admin/lessons/{id}`, `PUT /api/admin/modules/{id}/lessons/order` (`{lesson_ids}`, set-equality validated, one tx — fixes B5).
- `curricula`: migrated as data, no endpoints (nothing reads it).

**Authorization (38 RLS policies → app checks):** two dependencies — `get_current_user` (JWT → users row, 401; no role cache needed, it's a local PK lookup) and `require_admin` (403). Iron rule, enforced by tests: **no endpoint outside `/admin/*` accepts a user identifier from the request** — ownership comes exclusively from the token (`current_user.id` hardwired into queries).

**Scoring port** (`services/scoring_service.py`): line-for-line port of `app/api/_lib/scoring.js`; **known trap**: JS `null >= 2` is false, Python `None >= 2` raises — port as `c5 is not None and c5 >= 2` (integrator gate) and `c5 is not None and c5 < 2` (mandatory modules). `ScoringError(422)` mapped to HTTP 422.
**Golden parity tests:** one-off Node script dumps `tests/golden/scoring_golden.json` from the real scoring.js (all 31 C5 subsets, all 25 freq×breadth pairs, ~500 seeded random combos incl. invalid, hand-picked boundary cases); pytest replays for exact equality incl. error statuses and `mandatory_modules` ordering. Migration-day check: re-score both migrated complete survey rows, diff against stored columns.

**Cross-cutting:** pydantic-settings per skill (`DATABASE__*` nested; `JWT_SECRET` SecretStr; `APP_URL`); CORS with `allow_origins=[APP_URL, localhost dev ports]`, no credentials (Bearer only); single error shape `{"error":{code,message}}`; lifespan background task deletes expired tokens/sessions daily.

**Must-have tests:** scoring golden parity; invite lifecycle (invite→info→set-password→login, reuse→404/410, expiry, reset revokes sessions); parametrized authz matrix (every endpoint × {none, user, admin} + cross-user isolation); survey flow (draft idempotency, 409s, scored persistence); learning graph shape + reorder set-validation.

# Workstream 3 — Frontend (React 18 + TS + Vite, ~7–8 days)

Scaffold `npm create vite@latest -- --template react-ts`; **pin react/react-dom ^18.3.1** (no React 19), react-router-dom v6, framer-motion ^12. Structure mirrors old app (`pages/`, `components/`, `contexts/`, `lib/`) + `api/` + `types/`. tsconfig `strict: true` but `noUncheckedIndexedAccess` OFF for the port. **Vite dev proxy `/api → http://localhost:8000`** — one origin in dev and prod, CORS never in the happy path; old app on :3000, new on :5173 side-by-side.

**API client:** `openapi-typescript` (generate `src/api/schema.d.ts` from `/openapi.json`, committed; `gen:api` script) + `openapi-fetch` (~6 kB typed runtime). NOT hey-api (over-generated), NOT hand-written (drift risk is this rebuild's biggest failure mode — generated types turn backend/frontend drift into compile errors). `content_blocks` JSONB: cast once at the client boundary to the hand-written `ContentBlock` discriminated union (`types/contentBlocks.ts`, **7 block types incl. `question`** — context.md lists only 6).

**Tokens:** access + refresh in localStorage via `src/api/tokens.ts` (single seam — MSAL replaces this module later). Middleware: attach Bearer except auth endpoints; on 401 single-flight refresh, retry once, else clear + broadcast logout. Old app already stores Supabase session in localStorage and CSP is `script-src 'self'` — no security regression.

**AuthContext:** identical provider value shape to old context (`session/user/role/passwordSet/loading/markPasswordSet`) so pages port mechanically; internals: login via `/api/auth/login`, restore via `GET /api/me`, logout revokes. **`isRecovery` deleted** — invite/reset credential is now a URL token, not a session; `SetPassword` gets token mode (`?token=`) + authenticated fallback; `InviteRedirect` navigates to `/set-password?token=…` instead of Supabase redirect (keep expired/invalid UIs).

**State & styling:** keep plain typed `useState`+`useEffect` (NO TanStack Query — no shared-cache needs at this size; aggregates already killed the waterfalls); every fetch effect gets `let cancelled = false` cleanup (systematically fixes A5). Styling ports **as-is**: inline style objects with `satisfies Record<string, React.CSSProperties>` + verbatim `index.css` — highest-fidelity path to required visual parity; no CSS-module migration now.

**Do NOT port:** `lib/migrateMdxToBlocks.js` (dead+broken, D1), dead nav styles in JourneyHome (D2) and adminStyles (D3 — keep `s.navBadge/navDivider/navTabs/navTab/navTabActive/navTabInactive`), `lib/supabase.js`.

**Port order** (each phase compiles + runs): ① scaffold + `index.css`/`index.html` + route shell → ② foundation: `types/contentBlocks.ts`, `lib/*` (constants, surveyOptions `as const` unions, contentBlocks, mdxParser, blocksToMdx — round-trip sanity check vs real JSONB), `api/tokens.ts`, `api/client.ts` → ③ auth spine: AuthContext, App routes/guards, Login, AppNav, SetPassword, InviteRedirect → ④ learner core (needs migrated data): JourneyHome, Assessment (~970 lines, mechanical), ModulePopup, LearningPath (graph/zoom/SVG verbatim), lesson blocks/* + LessonView, LessonPage → ⑤ admin: adminStyles/adminHelpers, Admin shell, ProjectsView/SetupView, ProjectDetailView (closes invite loop), UserPanel/SurveyResults, AddTrackModal/AddModuleModal/ModulePanel, lesson editors/* + LessonEditor last.

# Workstream 4 — Integration & parity verification

Run old (`app/` :3000, live Supabase) and new (FastAPI :8000 + Vite :5173, Azure PG) side by side, same user, per-page checklist:
- **Auth:** login errors, session restore on reload every route, forced-refresh path (shorten access TTL in dev), logout, invite end-to-end (admin creates → copy link → new browser profile → set password → login), reset link, consumed/expired token UIs.
- **Assessment:** resume mid-step after reload, c5 multi-select, completion → correct level/band in admin (compare against old app for the same answers — scoring parity in vivo).
- **LearningPath:** graph layout identical on the real dataset (node positions, prerequisite edges, track colors, zoom, lesson-count badges).
- **LessonPage:** all 7 block types render identically (screenshot-diff one content-heavy lesson), quiz all-correct gate, next-lesson/cross-module navigation, answers pre-filled.
- **Admin:** level badges, role toggle, delete user (cascades), component toggles reflected on learner's JourneyHome, track/module assignment reflected on learner's LearningPath, add track/module/lesson, reorder survives reload, MDX import round-trip.
- **Backend gates:** `poe format` / `poe ty` / `poe test` green, coverage ≥80%; migration script exits 0 with all checks; re-scored migrated surveys match stored values.

**Sequencing across workstreams:** WS0 → WS1 (schema) → WS2 steps 1–2 (scaffold+auth) unblocks frontend ③; WS1 data migration unblocks frontend ④; WS2 steps 4–7 parallelize with frontend ④–⑤. Realistic total: ~3 weeks calendar, AI-assisted.

# Execution in batches (user reviews between each)

The work is executed and approved **batch by batch** — each batch ends in a verifiable, stable state and a review with Matthias before the next begins.

| Batch | Scope | Done when |
|---|---|---|
| **1 (THIS APPROVAL)** | WS0 + WS1: baseline pg_dump exports committed; `ai_hub_owner`/`ai_hub_app` roles + default-privileges probe on Azure PG; backend skeleton per skill (pyproject/uv, src/db/models for all 15 tables, Alembic initial migration applied); data migration script written, run, verified, re-run (idempotency) | Azure DB has full schema + all Supabase data, verification gates pass, `db/README.md` documents roles/DSNs/re-run |
| 2 | WS2 auth core: `core/security.py`, token + user services/repos, auth router, deps, invite lifecycle + authz tests | invite → set-password → login works via httpx tests; `poe test` green |
| 3 | WS2 remaining: me/survey/learning/admin routers, scoring port + golden parity, cleanup task, full test suite | all 29 endpoints live at `/docs`; golden scoring parity passes; authz matrix green |
| 4 | WS3 frontend foundation + auth spine: scaffold, types/lib ports, api client + generated schema, AuthContext, Login/SetPassword/InviteRedirect/App | login + session restore + invite flow work in browser against the real backend |
| 5 | WS3 learner core: JourneyHome, Assessment, LearningPath, LessonPage + blocks | learner journey parity vs old app on migrated data |
| 6 | WS3 admin + WS4 full parity pass: admin views, modals, editors; side-by-side checklist | full parity checklist passes; rebuild ready for the (later) hosting phase |

**Out of scope (explicitly deferred):** Container Apps/Docker/CI deployment, Entra ID swap, decommissioning Supabase/Vercel (keep both live until parity is proven), styling-system migration, `curricula` endpoints.
