# Database — Azure PostgreSQL

**Cutover is complete and permanent (confirmed 2026-07-08).** Azure is the sole authoritative
database. The pre-cutover Supabase migration scripts (`export_supabase_snapshot.py`,
`migrate_supabase_to_azure.py`, `sync_content_from_supabase.py`, `backfill_user_lessons.py`)
were **removed 2026-08-10** — they TRUNCATE-and-reload live tables from a stale snapshot and
had no remaining legitimate use. Recover them from git history if ever needed
(last present at commit `c408463`). The `baseline/data/*.json` snapshot is a frozen historical
record of the Supabase state at migration time, not a live mirror — never treat it as current.
The five user-data files (`users`, `survey_responses`, `lesson_progress`, `user_tracks`,
`user_modules`) were **purged from the entire git history on 2026-08-10** (review finding 5.1)
before the repo's move to the org; only content/org-structure tables remain in the snapshot.

State after Batch 1 (2026-07-03): the Azure database has the full 15-table schema
(Alembic-managed) and all Supabase data loaded and verified. Users are reset for
manual re-invite (`password_set=false`, no password hashes).

## Environments

| What | Where |
|---|---|
| Server | `imaginemore-playground-pg.postgres.database.azure.com` (PG 18, resource group `imaginemore-playground`, subscription "Playground BELU Imagine More") |
| Main DB | `ai-enablement-hub` |
| Test DB | `ai-enablement-hub-test` (owned by `ai_hub_owner`; for backend integration tests) |
| Old system | Supabase project `tbeogvbjbaxgfwaoebfj` — **frozen, cutover complete (2026-07-08); no longer authoritative, do not sync from it** |

Always connect with `sslmode=require`. The DB name contains hyphens — double-quote
`"ai-enablement-hub"` in SQL; DSNs need no quoting.

## Roles (created by `provision_roles.py`)

| Role | Auth | Purpose |
|---|---|---|
| `danneelm@delawareconsulting.com` | Entra AAD token (~1 h expiry) | Server admin: role management, emergencies. Token: `az account get-access-token --resource https://ossrdbms-aad.database.windows.net --query accessToken -o tsv` |
| `ai_hub_owner` | password (in `db/.env`) | DDL: Alembic migrations, data migration script. Owns all tables. |
| `ai_hub_app` | password (in `db/.env`) | Runtime DML for the FastAPI app. Cannot alter schema. |

**Default privileges are configured** (`ALTER DEFAULT PRIVILEGES` executed *as*
`ai_hub_owner`): every table/sequence a future Alembic migration creates is
automatically SELECT/INSERT/UPDATE/DELETE-able by `ai_hub_app`. No GRANT
statements are ever needed in migrations. (This permanently fixes the
"new table has RLS but no grants" class of bug from the Supabase era.)

Secrets live in `db/.env` and `backend/.env` — both git-ignored. Never commit them.
`backend/.env.local.example` documents the expected keys.

## Files

| File | Purpose |
|---|---|
| `provision_roles.py` | One-time (idempotent) role + test-DB + default-privileges setup. Requires az CLI login as the Entra admin. `--rotate-passwords` resets role passwords. |
| `baseline/supabase_schema_record.md` | Frozen record of the live Supabase schema (columns, constraints, indexes, FK actions, RLS policies, functions) as of 2026-07-03. |
| `baseline/data/*.json` | The frozen pre-cutover data snapshot (historical only). The git-ignored `invite_tokens.json` was deleted 2026-08-10 (contained real emails + possibly-redeemable recovery links). |
| `content_tools/` | Reusable scripts for live lesson-content edit passes (fetch, quiz-bias check, locator-based edit/apply, baseline re-sync). Built for the General I/II content review round (2026-07-15/16); see that folder's own docstrings for usage. Safe-write pattern: fetch fresh → dry-run → `apply_content_edits.py --apply` → verify → `sync_baseline.py`. |

Run scripts with [uv](https://docs.astral.sh/uv/) — dependencies are inline (PEP 723):
`uv run <script>.py`.

## Schema management (backend/)

The schema is owned by SQLAlchemy models in `backend/src/db/models/` and applied via
Alembic (`backend/alembic/`), connecting as `ai_hub_owner` through
`ALEMBIC_DATABASE_URL` in `backend/.env`.

```powershell
cd backend
uv run alembic upgrade head      # apply (or: uv run poe upgrade)
uv run alembic revision --autogenerate -m "message"   # new migration — always hand-review!
```

Autogenerate is known to miss CHECK-constraint *changes* — review every generated
revision against the models before applying.

## Migration verification results (2026-07-03, historical — run twice, idempotent)

- 13/13 tables: row counts match manifest (189 rows migrated; invite_tokens excluded)
- 13/13 tables: primary-key-set MD5 hashes equal
- 25/25 lessons: `content_blocks` JSONB deep-equal to snapshot (362 elements)
- users: 6/6 with `password_set=false`, `password_hash IS NULL`; (email, role) preserved
- survey_responses: status/score_level/c5 cardinality preserved
- Live constraint check: invalid `role` insert rejected (8 CHECK, 18 FK, 9 UNIQUE constraints on Azure)
- Grant probe: `ai_hub_app` can DML a table created by `ai_hub_owner` with no explicit GRANT
