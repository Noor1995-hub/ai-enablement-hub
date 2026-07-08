# Database — Azure PostgreSQL setup & Supabase migration

**Cutover is complete (confirmed 2026-07-08).** Azure is now the sole authoritative database —
the "Refresh data from Supabase" section below and the scripts it points to
(`export_supabase_snapshot.py`, `migrate_supabase_to_azure.py`, `sync_content_from_supabase.py`)
describe the **pre-cutover migration process only**. Do not run them. `migrate_supabase_to_azure.py`
TRUNCATEs and reloads from the Supabase snapshot; `sync_content_from_supabase.py --apply` overwrites
`tracks`/`modules`/`lessons`/`curricula` rows to match that same stale snapshot. Either one would
silently erase any content edited directly on Azure since cutover (e.g. the 2026-07-08 interactivity
pass — new `interactive`/`try_it_yourself` blocks, the General-track capstone rewrite). The
`baseline/data/*.json` snapshot itself is a frozen historical record of the Supabase state at
migration time, not a live mirror — it is not kept in sync with Azure and should not be treated as
current.

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
| `export_supabase_snapshot.py` | Pulls all 14 tables from Supabase via PostgREST (service-role key from `app/.env.local`) into `baseline/data/*.json` + `_manifest.json`. Re-run any time to refresh the snapshot (e.g. right before final cutover). |
| `migrate_supabase_to_azure.py` | Loads the snapshot into Azure: TRUNCATE-and-reload in one transaction, FK-safe order, users transformed (no auth_id, `password_set=false`, `password_hash=NULL`, lowercased email), `invite_tokens` skipped. Ends with verification gates (row counts, PK-set hashes, content_blocks element count, users/survey spot-checks); non-zero exit on any failure. `--check-only` for a dry run. |
| `baseline/supabase_schema_record.md` | Frozen record of the live Supabase schema (columns, constraints, indexes, FK actions, RLS policies, functions) as of 2026-07-03. |
| `baseline/data/*.json` | The data snapshot (202 rows incl. 13 non-migrated invite_tokens). `invite_tokens.json` is git-ignored — it contains Supabase action links that may still be redeemable; it stays local-only. |

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

## Refresh data from Supabase (e.g. cutover day)

```powershell
cd db
uv run export_supabase_snapshot.py     # refresh baseline/data/ from live Supabase
uv run migrate_supabase_to_azure.py    # wipe + reload Azure, verify
```

The reload TRUNCATEs all app tables (including `auth_tokens`/`auth_sessions`) — any
passwords set on Azure since the previous load are wiped and users must be
re-invited. That is the intended cutover behavior; don't run it casually once real
usage starts on Azure.

## Verification results (2026-07-03, run twice — idempotent)

- 13/13 tables: row counts match manifest (189 rows migrated; invite_tokens excluded)
- 13/13 tables: primary-key-set MD5 hashes equal
- 25/25 lessons: `content_blocks` JSONB deep-equal to snapshot (362 elements)
- users: 6/6 with `password_set=false`, `password_hash IS NULL`; (email, role) preserved
- survey_responses: status/score_level/c5 cardinality preserved
- Live constraint check: invalid `role` insert rejected (8 CHECK, 18 FK, 9 UNIQUE constraints on Azure)
- Grant probe: `ai_hub_app` can DML a table created by `ai_hub_owner` with no explicit GRANT
