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
- Batches 4–6: frontend (foundation/auth → learner pages → admin + parity pass) —
  **React 18 + TypeScript (Vite)** per the approved plan.

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
