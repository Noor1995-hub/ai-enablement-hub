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
- Batch 3: remaining routers + scoring port (golden-parity tests vs `../app/api/_lib/scoring.js`;
  beware JS `null >= 2` is false vs Python TypeError on the c5 rung).
- Batches 4–6: frontend (foundation/auth → learner pages → admin + parity pass).

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
