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
  workflow's migrate job. Phase C (#54) is done; new migrations chain off the current head via the
  normal flow, expand-first (the old image must keep working on the new schema). CI's `migrations`
  job (upgrade → `alembic check` → round-trip) is how a migration gets executed before prod.

## Conventions

1. `python-be-architecture.md` (repo root) — **MANDATORY** (delaware template): router → service
   → repository → model layering, abstract repositories, DI in `core/dependencies/`, poe tasks,
   ruff/ty clean. Two approved deviations: asyncpg is a main dependency, and integration tests run
   against real Postgres (schema needs text[]/JSONB/ON CONFLICT), not in-memory SQLite.
2. **Authorization iron rule (tests must enforce):** no endpoint outside `/admin/*` accepts a user
   identifier from the request — ownership comes from the token only. **Admin routes** each declare
   exactly one guard from `core/dependencies/admin_scope.py` (`require_power_admin`,
   `require_project_in_scope`, `require_user_in_scope`, or `AdminScopeDep` for lists and bodies);
   `tests/integration/test_routers/test_authz.py` fails on an admin route missing from `_MATRIX`.
3. **FastAPI signature gotcha:** any type in a *parameter* annotation FastAPI inspects (routers,
   DI providers) must be imported at runtime, not under `TYPE_CHECKING` — an unresolvable name
   silently degrades the param to a required query param (uniform 422s).
4. **Integration tests** derive their DSN from `ALEMBIC_DATABASE_URL` with the database swapped to
   `ai-enablement-hub-test`; per-test savepoint rollback. Locally that is the shared Azure test DB,
   in CI a throwaway `postgres:18` service container. Flaky `-n auto` runs against the shared remote
   DB happen — rerun before panicking.
5. **Environment-dependent tests** (anything branching on `CI`, `UPDATE_GOLDEN`, …) set or clear
   every variable they depend on; run such a change once with `CI=true` before the PR.
6. **Services never call other services, with no exception** (decision 5.1 of the July master
   plan, 2026-09-25; `admin_user_service.py`, `content_improvement_service.py` say so). Logic two
   use cases share becomes a **pure module** both call (`core/attention.py::attention_for`,
   `core/constants.py::advance_level` / `module_level_map`). A shared *fetch* becomes a
   module-level `async` function handed the repository ABCs as arguments, which is not a
   service dependency. One known violation remains until fix-programme task D10 removes it:
   `services/interview_context.py` (`InterviewContextService` takes three services). Don't
   copy it. **When a use case needs two independent services, the router orchestrates**
   (review 9.3): an invite endpoint in `routers/admin_users.py` gets the user from
   `AdminUserService` and the link from `TokenService`, then its helper `_email_the_link`
   renders the email with `EmailTemplateService` and sends it with `EmailService`. Such router
   code does no data access and branches only on what the services return; domain rules stay
   in a service. **List
   responses** (review 9.8): return a wrapped object (`{items, total, limit, offset}`,
   `{users, total}`, `{templates}`) whenever the response carries pagination or aggregate
   metadata. A bare array is fine for a small, bounded, unpaginated collection (the two
   track lists `GET /api/tracks` and `…/{track_id}/modules`). Changing that shape is a
   wire change, not a refactor. Run stamps: assistant turns carry
   `model` + `prompt_version` in `messages.metadata`; playbooks carry
   `conversations.summary["meta"]` (model, both prompt versions, max_tokens, thinking, attempts,
   usage, generated_at). `prompt_version` = first 12 hex of SHA-256 of the shipped prompt file.
7. `anthropic` is a main dependency, bounded to `~=1.x`; 1.x is built on `httpx2`, so tests that
   build SDK errors use `httpx2.Request/Response`. A major SDK bump is its own PR.
8. **Client IP:** any per-IP key (rate limits, logs) uses `src/core/client_ip.py::client_ip`, the
   rightmost X-Forwarded-For hop that the Container Apps ingress appends — **never
   `request.client.host`**, which uvicorn fills from the client-controlled leftmost hop
   (`docs/superpowers/lessons.md`, 2026-09-25). Limits that must not punish a shared office NAT
   count failures only (`RateLimiter.charge` + `refund`, see `routers/auth.py` login).
9. **Error envelope:** everything answers `{"error":{code,message}}` — domain errors via their
   handlers, unclaimed exceptions via the catch-all 500 in `main.py`; Anthropic/provider failures
   raise `AiGenerationError` (502, `llm_service.is_provider_error` tells them from our own bugs);
   a failed SSE stream ends with an `event: error` frame instead.
10. **Admin lesson saves (`PATCH /api/admin/lessons/{id}`):** `ContentService.update_lesson` runs
    A8's `check_link_schemes` and strips ephemeral SAS urls, then enforces a 1 MiB ceiling
    (`MAX_LESSON_BLOCKS_BYTES`) on the serialized `content_blocks` — scheme-checked and size-capped,
    not structurally validated (decision 5.2 option A: 66/91 live lessons predate
    `validate_content_blocks`'s nested-id rule; option B follows the backfill).

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
