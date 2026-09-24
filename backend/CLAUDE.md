# Backend — scoped guide

Loaded when working under `backend/`. The root `CLAUDE.md` rules still apply — above all **the
one-database rule**: dev and prod share one Azure PG database, so a local `alembic upgrade`, a
test user or a script that writes rows edits live learner data.

## Checks (the same four CI runs)

`uv run poe format-check && uv run poe lint-src && uv run poe ty-src && uv run poe test`

- `poe format` rewrites; `poe lint` also covers `scripts/`, which carries known findings and is
  counted by the non-required `staged` CI job — a ratchet (baselines in `ci.yml`): red only when a
  change adds findings; lower the baseline when you fix some.
- `ty` is pinned exactly in the dev extra (pre-1.0, every release can add diagnostics).
- Coverage floor 90% of `src/` in CI (`--cov-fail-under=90`). Add tests with the code.
- **Never start `uv run poe dev` to "just check something"** — it connects to the live DB and its
  lifespan cleanup loop deletes expired sessions. Swagger at `/docs` if you really run it.
- Migrations: `uv run poe upgrade` — against the live DB; the normal path is the Deploy
  workflow's migrate job. New migrations belong to fix-programme phase C (#54), chained off the
  current head, expand-first (the old image must keep working on the new schema).

## Conventions

1. `python-be-architecture.md` (repo root) — **MANDATORY** (delaware template): router → service
   → repository → model layering, abstract repositories, DI in `core/dependencies/`, poe tasks,
   ruff/ty clean. Two approved deviations: asyncpg is a main dependency, and integration tests run
   against real Postgres (schema needs text[]/JSONB/ON CONFLICT), not in-memory SQLite.
2. **Authorization iron rule (tests must enforce):** no endpoint outside `/admin/*` accepts a user
   identifier from the request — ownership comes from the token only.
3. **FastAPI signature gotcha:** any type in a *parameter* annotation FastAPI inspects (routers,
   DI providers) must be imported at runtime, not under `TYPE_CHECKING` — an unresolvable name
   silently degrades the param to a required query param (uniform 422s).
4. **Integration tests** derive their DSN from `ALEMBIC_DATABASE_URL` with the database swapped to
   `ai-enablement-hub-test`; per-test savepoint rollback. Locally that is the shared Azure test DB,
   in CI a throwaway `postgres:18` service container. Flaky `-n auto` runs against the shared remote
   DB happen — rerun before panicking.
5. **Environment-dependent tests** (anything branching on `CI`, `UPDATE_GOLDEN`, …) set or clear
   every variable they depend on; run such a change once with `CI=true` before the PR.
6. **Services never call other services** (`admin_user_service.py`, `content_improvement_service.py`
   say so; `core/attention.py` + `advance_level` exist to avoid it). The interviewer slice is the
   known exception — decision 5.1 of the July master plan.
7. `anthropic` is a main dependency, bounded to `~=1.x`; 1.x is built on `httpx2`, so tests that
   build SDK errors use `httpx2.Request/Response`. A major SDK bump is its own PR.

## Prompts are runtime assets

`backend/prompts/*.md` are the AI system prompts, COPY'd into the Docker image and loaded by
`services/prompts.py`. Git is the only source of truth (the admin System Prompts page is
read-only). Treat an edit as a production change: regenerate the golden snapshots with
`UPDATE_GOLDEN=1 uv run pytest tests/golden/ai`, read the diff, commit it with the change. Never
move or rename a prompt file.

## Ops tooling (`backend/scripts/`)

`content_qa/` (content-review toolkit incl. `check_draft.py`, the pre-write drafting gate),
`issue_invite.py` (bootstrap invite links), `rescore_parity.py`, `read_goldstandard.py`,
`export_openapi.py` (the OpenAPI document by importing the app — used by `npm run gen:api`).

## Secrets

`backend/.env` + `db/.env` (git-ignored; keys documented in `backend/.env.local.example`). Local
`.env` carries `EMAIL__*` → local invites/resets send **real** email (comment out to disable).
Full inventory and rotation recipes: `SECURITY.md`. DB role passwords:
`db/provision_roles.py --rotate-passwords`; read `db/README.md` before any DB work.
