# Database, Data-Migration & Dev-Environment Design — AI Enablement Hub Rebuild

> **Point-in-time rebuild contract (2026-07-03).** Superseded wherever it conflicts with the
> code, the Alembic migrations, or the root `CLAUDE.md`. Kept at this path because source
> comments cite it by basename — do not rename.
>
> Live-schema facts verified against Supabase at design time that corrected older docs:
> `modules` has **no `col_offset`** column (context.md was stale) but has `description`;
> `survey_responses` has a **unique index** (not constraint) on `user_id`; the
> `set_updated_at` trigger exists **only on `users`**; `users.company_id` FK has **no
> ON DELETE action**; `curricula` exists (7 rows) referencing `tracks` but nothing references it.

Verified live source: Supabase project `tbeogvbjbaxgfwaoebfj` (PG 17.6, eu-west-1). Row counts (2026-07-03): companies 4, projects 5, project_component_settings 8, users 6, invite_tokens 13, survey_responses 2, tracks 7, curricula 7, modules 27, module_prerequisites 23, lessons 25, user_tracks 18, user_modules 53, lesson_progress 4. Total ≈ 202 rows (189 migrated; invite_tokens dropped).

Target: Azure PG Flexible Server `imaginemore-playground-pg.postgres.database.azure.com` (PG 18), database `ai-enablement-hub` (empty). New code root: `c:\Users\danneelm\projects\AI enablement hub\AI ENABLEMENT HUB REBUILD\` with `backend/` and `frontend/`; DB artifacts in a new `db/` sibling folder.

---

## 1. Target Schema (DDL-level)

General rules: keep UUID PKs with `DEFAULT gen_random_uuid()` (built-in since PG13; no extension needed on Azure PG18), keep all timestamptz defaults, keep all CHECK/UNIQUE constraints verbatim, **no RLS, no `is_admin()`, no Supabase-specific objects**. All authorization moves to FastAPI.

### 1.1 Tables kept 1:1 (verbatim from live Supabase DDL)

| Table | Columns (exact, from live DB) | Constraints to reproduce |
|---|---|---|
| `companies` | id uuid PK gen_random_uuid(), name text NOT NULL, created_at timestamptz NOT NULL now() | PK |
| `projects` | id uuid PK, name text NOT NULL, company_id uuid NOT NULL, created_at timestamptz NOT NULL now() | FK company_id→companies **ON DELETE CASCADE** (as today); idx on company_id |
| `project_component_settings` | id uuid PK, project_id uuid NOT NULL, component text NOT NULL, locked bool NOT NULL false, hidden bool NOT NULL false, updated_at timestamptz NOT NULL now() | CHECK component IN ('assessment','learning','interview'); UNIQUE (project_id, component); FK project_id→projects **CASCADE** |
| `tracks` | id uuid PK, name text NOT NULL, sort_order int NOT NULL 0, track_type text NOT NULL, color text NULL, created_at timestamptz NOT NULL now() | CHECK track_type IN ('general','tool') |
| `curricula` | id uuid PK, track_id uuid NOT NULL, name text NOT NULL DEFAULT 'default', created_at timestamptz NULL now() | FK track_id→tracks **CASCADE**; idx track_id. (Nothing references it; migrate as-is — 7 rows.) |
| `modules` | id uuid PK, track_id uuid NOT NULL, title text NOT NULL, description text NULL, sort_order int NOT NULL 0, created_at timestamptz NOT NULL now() | FK track_id→tracks **CASCADE**; idx track_id. **No col_offset column** (context.md stale) |
| `module_prerequisites` | module_id uuid, prerequisite_module_id uuid, created_at timestamptz NOT NULL now() | PK (module_id, prerequisite_module_id); CHECK module_id <> prerequisite_module_id; both FKs→modules **CASCADE**; idx prerequisite_module_id |
| `lessons` | id uuid PK, module_id uuid NOT NULL, title text NOT NULL, sort_order int NOT NULL 0, content_blocks jsonb NOT NULL '[]', created_at timestamptz NOT NULL now() | FK module_id→modules **CASCADE**; idx module_id |
| `user_tracks` | id uuid PK, user_id uuid NOT NULL, track_id uuid NOT NULL, assigned_at timestamptz NOT NULL now() | UNIQUE (user_id, track_id); FK user_id→users **CASCADE**, FK track_id→tracks **CASCADE**; idx track_id |
| `user_modules` | id uuid PK, user_id uuid NOT NULL, module_id uuid NOT NULL, assigned_at timestamptz NOT NULL now() | UNIQUE (user_id, module_id); FKs→users/modules **CASCADE**; idx module_id |
| `lesson_progress` | id uuid PK, user_id uuid NOT NULL, lesson_id uuid NOT NULL, completed_at timestamptz NOT NULL now(), answers jsonb NOT NULL '{}' | UNIQUE (user_id, lesson_id); FKs→users/lessons **CASCADE** |
| `survey_responses` | id uuid PK, user_id uuid NOT NULL, status text NOT NULL 'in_progress', instrument_version text NOT NULL '1.0', current_step int NOT NULL 0, job_title/department text NULL, consent bool NULL, c1_code..c4_code text NULL, c5_codes text[] NULL, c6_code text NULL, b_freq/b_breadth text NULL, b_setup/b_tools/b_barriers text[] NULL, b_attitude/b_readiness smallint NULL, q_excitement/q_timesink text NULL, score_level text NULL, c1_rung..c6_rung smallint NULL, have_count/adv_count smallint NULL, safety_flag bool NULL, mandatory_modules text[] NULL, usage_band text NULL, started_at timestamptz NOT NULL now(), completed_at timestamptz NULL, scored_at timestamptz NULL, updated_at timestamptz NOT NULL now() | CHECKs: status IN ('in_progress','complete'); score_level IN ('explore','practitioner','integrator'); usage_band IN ('dormant','occasional','regular','embedded'); FK user_id→users **CASCADE**. **Change: promote the live unique index on user_id to a named `UNIQUE (user_id)` constraint** (the app upserts `ON CONFLICT (user_id)`) |

### 1.2 `users` — redesigned

```sql
CREATE TABLE users (
  id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  email         text NOT NULL UNIQUE,          -- store lowercased; app normalizes on write
  first_name    text NOT NULL,
  last_name     text NOT NULL,
  role          text NOT NULL DEFAULT 'user' CHECK (role IN ('admin','user')),
  company_id    uuid REFERENCES companies(id) ON DELETE RESTRICT,   -- explicit; was implicit NO ACTION
  project_id    uuid REFERENCES projects(id)  ON DELETE SET NULL,   -- as today
  is_active     boolean NOT NULL DEFAULT true,
  password_set  boolean NOT NULL DEFAULT false,
  password_hash text,            -- NULL until user completes invite; bcrypt/argon2 string
  external_id   text UNIQUE,     -- NULL for now; future Entra ID OID (string GUID)
  created_at    timestamptz NOT NULL DEFAULT now(),
  updated_at    timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX idx_users_company_id ON users (company_id);
CREATE INDEX idx_users_project_id ON users (project_id);
-- UNIQUE(external_id) creates a partial-null-friendly unique index automatically (NULLs allowed, multiple)
```

Changes vs Supabase: **drop `auth_id`** (and its FK to auth.users + index), add `password_hash`, add `external_id`. `updated_at` becomes NOT NULL (currently nullable; all 6 rows have values — coalesce to created_at in migration if any NULL). Identity seam: the app keys everything on `users.id` (internal UUID); the auth dependency resolves "token → users row" in exactly one place, so Entra later means: verify Entra JWT instead of own JWT, match `external_id` (fallback: email match once, then stamp external_id), leave every FK untouched.

### 1.3 `invite_tokens` → `auth_tokens` (new, NOT migrated)

```sql
CREATE TABLE auth_tokens (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id     uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  purpose     text NOT NULL CHECK (purpose IN ('invite','reset')),
  token_hash  text NOT NULL UNIQUE,     -- sha256 hexdigest of the raw token
  expires_at  timestamptz NOT NULL,     -- now() + 7 days for invite, + 24h for reset
  consumed_at timestamptz,              -- NULL = unused; set on redemption (single-use)
  created_at  timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX idx_auth_tokens_user_id ON auth_tokens (user_id);
```

**Yes, store only the SHA-256 hash.** The raw token (`secrets.token_urlsafe(32)`, 256 bits) is generated in FastAPI, embedded once in the link the admin copies (`{APP_URL}/invite/{raw_token}`), and never persisted. Redemption: `SELECT ... WHERE token_hash = sha256(raw) AND consumed_at IS NULL AND expires_at > now()`. Cost is one hash call; benefit is that a DB dump/backup leak yields no usable invite/reset links (these tokens grant account takeover — this is the one place hashing genuinely matters). Lookup by unique `token_hash` is O(1); no need for a token id in the URL. Issuing a new token for a user should soft-invalidate older ones of the same purpose (`UPDATE ... SET consumed_at = now() WHERE user_id=? AND purpose=? AND consumed_at IS NULL`) — app logic, no schema support needed. Cleanup of expired rows: opportunistic `DELETE` on each issuance (6 users — no cron needed; fixes old DB2 issue).

### 1.4 `refresh_tokens` — recommendation: **do NOT add one now**

Justification:
- Scale/threat model: internal tool, ~6 known users, 4 companies. Issue a single access JWT with 24h expiry (`exp`), no refresh flow. Users log in each day — matches current Supabase session behavior closely enough.
- Revocation is already immediate without it: the FastAPI auth dependency loads the `users` row on every request (needed anyway for role/project scoping); it rejects `is_active = false` or deleted users instantly, regardless of remaining JWT lifetime. The only thing a refresh table would buy is shorter access-token life, which protects against token theft — marginal here.
- Entra alignment: when Entra ID replaces native auth, MSAL owns token acquisition/refresh in the SPA and the backend only validates; a bespoke refresh-rotation table would be dead code. Keeping the seam minimal (verify-token dependency + users table) is exactly the "minimal rework" goal.
- If needed later, adding a `refresh_tokens` table is a plain additive Alembic migration with zero data impact.

### 1.5 `updated_at`: SQLAlchemy `onupdate`, drop the trigger

Live Supabase has `set_updated_at()` on **users only**; `survey_responses.updated_at` and `project_component_settings.updated_at` are maintained by app code today. Recommendation: **no DB trigger** — declare `updated_at = mapped_column(server_default=func.now(), onupdate=func.now())` on the three tables that have it (users, survey_responses, project_component_settings). Rationale: one codepath, visible in the models, no hidden DDL that Alembic autogenerate can't represent; all writes go through the FastAPI/SQLAlchemy layer now (no more anon-key direct writes), so the trigger's "catch writes from anywhere" advantage is void. Caveat to document: raw SQL/psql edits won't bump `updated_at` — acceptable.

### 1.6 Sort-order note (carry-over issue A4/DB6)

Keep `sort_order int NOT NULL DEFAULT 0` as-is (1:1 rule). Do not add sequences; duplicate sort_orders are tolerated by the UI sort. Flag for the API design: compute `max+1` server-side inside a transaction instead of client-side.

---

## 2. Schema-as-code: SQLAlchemy models + Alembic (recommended)

Choose **Alembic with a single hand-verified initial migration generated from SQLAlchemy 2.0 models**, not raw SQL files:

- The backend is FastAPI + SQLAlchemy anyway; models are the source of truth for the app, so letting them also drive DDL removes a drift axis. Raw SQL would mean maintaining schema twice.
- Future changes (adding `refresh_tokens`, Entra columns, new features) get ordered, reversible migrations for free; `alembic upgrade head` is the only provisioning command anyone needs.
- Do it as: write models → `alembic revision --autogenerate -m "initial schema"` → **hand-edit** the generated migration (autogenerate misses CHECK constraints on some versions, and named constraints matter). Configure `MetaData(naming_convention=...)` up front so constraint names are deterministic (`uq_user_tracks_user_id_track_id`, `ck_users_role`, etc.).
- Alembic reads its URL from env (`ALEMBIC_DATABASE_URL`, the **owner** role — see §4); the app uses `DATABASE_URL` (the app role). `alembic/env.py` imports `Base.metadata` from the models package.
- Driver: `psycopg` (v3), sync engine — simplest correct choice at this scale; DSN `postgresql+psycopg://...` supports `sslmode=require` natively.

Planned layout:

```
AI ENABLEMENT HUB REBUILD/
├── backend/
│   ├── app/models/          # SQLAlchemy Base + one module per aggregate
│   ├── alembic/versions/0001_initial_schema.py
│   ├── alembic.ini
│   └── .env                 # git-ignored; .env.example committed
├── frontend/
└── db/                      # baseline dumps + migration script (see §3, §5)
```

---

## 3. Data-migration script design

**Tooling decision: a single idempotent Python script using psycopg 3** (`db/migrate_supabase_to_azure.py`), not pg_dump/pg_restore. Reasons: users need a column transform (drop auth_id, null password_hash, force password_set=false), invite_tokens must be skipped, target schema is created by Alembic (so restore-with-schema-surgery fights the tool), and at 189 rows readability/re-runnability beat throughput. pg_dump is still used — but only for the *baseline snapshot* (§5).

Design:

- **Connections** (both from env / CLI args, never hardcoded):
  - Source: Supabase session pooler DSN (IPv4-safe from a Windows laptop): `postgresql://postgres.tbeogvbjbaxgfwaoebfj:<db-password>@aws-1-eu-west-1.pooler.supabase.com:5432/postgres?sslmode=require` (exact pooler host shown in Supabase dashboard → Connect; direct `db.tbeogvbjbaxgfwaoebfj.supabase.co` is IPv6-only and may not resolve from the dev machine).
  - Target: `postgresql://ai_hub_owner:<pw>@imaginemore-playground-pg.postgres.database.azure.com:5432/ai-enablement-hub?sslmode=require` — run as the **owner** role so inserts bypass any grant gaps.
- **Idempotency**: one target transaction; first statement `TRUNCATE companies, projects, project_component_settings, users, tracks, curricula, modules, module_prerequisites, lessons, user_tracks, user_modules, lesson_progress, survey_responses, auth_tokens CASCADE;` then reload. Safe because the target is dedicated and empty/replaceable during the rebuild; re-run at will. Abort (rollback) on any error.
- **FK-safe insert order**: `companies → projects → project_component_settings → users → tracks → curricula → modules → module_prerequisites → lessons → user_tracks → user_modules → survey_responses → lesson_progress`.
- **Per-table method**: `SELECT <explicit column list> FROM <t>` on source; `INSERT INTO <t> (<cols>) VALUES (...)` with executemany on target. Explicit column lists (not `SELECT *`) so source/target column mismatches fail loudly. psycopg passes uuid/jsonb/text[]/timestamptz through natively — no serialization code needed (jsonb arrives as parsed objects; wrap with `psycopg.types.json.Jsonb` on insert, or cast via `::jsonb` with `json.dumps` — pick one, note it in the script).
- **Transforms**:
  - `users`: select all columns except `auth_id`; override `password_hash=NULL`, `external_id=NULL`, `password_set=False`; `email=email.lower()`; `updated_at=coalesce(updated_at, created_at, now())`. Preserve `id`, `role`, `is_active`, timestamps — all FKs (survey_responses, user_tracks, user_modules, lesson_progress) keep working because `users.id` is unchanged.
  - `invite_tokens`: **not migrated** (13 stale Supabase action links, useless and a liability). `auth_tokens` starts empty; admins re-invite from the new UI.
  - Everything else verbatim.
- **Verification (built into the script, printed as a table)**:
  1. Row counts source vs target for all 13 migrated tables — must match exactly (users 6, companies 4, projects 5, pcs 8, tracks 7, curricula 7, modules 27, module_prerequisites 23, lessons 25, user_tracks 18, user_modules 53, survey_responses 2, lesson_progress 4).
  2. Checksum per table: `SELECT md5(string_agg(id::text, ',' ORDER BY id)) FROM <t>` both sides (PK-set equality); for module_prerequisites use `module_id||':'||prerequisite_module_id`.
  3. Content spot-checks: `SELECT sum(jsonb_array_length(content_blocks)) FROM lessons` equal both sides; `SELECT email, role, password_set FROM users ORDER BY email` (target must show all `password_set=false`, roles preserved); `SELECT status, score_level, cardinality(c5_codes) FROM survey_responses ORDER BY user_id` equal both sides; `SELECT count(*) FROM survey_responses WHERE status='complete'`.
  4. Exit non-zero if any check fails (script is CI-friendly).

---

## 4. Dev environment

### 4.1 Roles on Azure PG (run once as Entra admin `danneelm@delawareconsulting.com`)

Connect as admin: 
```powershell
$env:PGPASSWORD = az account get-access-token --resource-type oss-rdbms --query accessToken -o tsv
psql "host=imaginemore-playground-pg.postgres.database.azure.com port=5432 dbname=ai-enablement-hub user=danneelm@delawareconsulting.com sslmode=require"
```

Two dedicated password-auth roles — an **owner** (runs Alembic + migration script, owns all objects) and an **app** role (DML only). AAD tokens expire hourly, so tooling must not depend on them:

```sql
CREATE ROLE ai_hub_owner LOGIN PASSWORD '<strong-pw-1>';
CREATE ROLE ai_hub_app   LOGIN PASSWORD '<strong-pw-2>';
GRANT CONNECT ON DATABASE "ai-enablement-hub" TO ai_hub_owner, ai_hub_app;
-- make owner own the schema it creates into
GRANT ALL ON SCHEMA public TO ai_hub_owner;
GRANT USAGE ON SCHEMA public TO ai_hub_app;
-- app privileges on existing tables (rerun-safe)
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO ai_hub_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO ai_hub_app;
-- THE FIX for the past "new tables lack grants" pain:
-- default privileges are per-GRANTOR — must be FOR ROLE ai_hub_owner,
-- because ai_hub_owner is who runs Alembic and creates future tables.
ALTER DEFAULT PRIVILEGES FOR ROLE ai_hub_owner IN SCHEMA public
  GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO ai_hub_app;
ALTER DEFAULT PRIVILEGES FOR ROLE ai_hub_owner IN SCHEMA public
  GRANT USAGE, SELECT ON SEQUENCES TO ai_hub_app;
```

Key subtlety (documents the past pain): `ALTER DEFAULT PRIVILEGES` without `FOR ROLE` applies only to objects created by the role executing it (the Entra admin). Since **Alembic runs as `ai_hub_owner`**, the `FOR ROLE ai_hub_owner` form is the one that makes every future Alembic-created table automatically readable/writable by `ai_hub_app`. No RLS, no `GRANT` statements ever needed inside migrations. Database name contains hyphens — always double-quote it in SQL (`"ai-enablement-hub"`); DSNs need no quoting.

### 4.2 Connection matrix

| Actor | Role | Auth | Used for |
|---|---|---|---|
| Matthias / az cli / psql | Entra admin | AAD access token | role creation, emergencies |
| Alembic + migration script | `ai_hub_owner` | password | DDL, data load |
| FastAPI app | `ai_hub_app` | password | all runtime DML |

All with `sslmode=require`.

### 4.3 .env layout

`backend/.env` (git-ignored; commit `backend/.env.example` with blanks):
```
DATABASE_URL=postgresql+psycopg://ai_hub_app:<pw>@imaginemore-playground-pg.postgres.database.azure.com:5432/ai-enablement-hub?sslmode=require
ALEMBIC_DATABASE_URL=postgresql+psycopg://ai_hub_owner:<pw>@imaginemore-playground-pg.postgres.database.azure.com:5432/ai-enablement-hub?sslmode=require
JWT_SECRET=<openssl rand -hex 32>
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440
APP_URL=http://localhost:3000            # invite-link base + CORS allow-origin
```
Migration script env (can live in `db/.env` or be passed as args): `SOURCE_DATABASE_URL` (Supabase pooler DSN), `TARGET_DATABASE_URL` (= ALEMBIC_DATABASE_URL without the `+psycopg` marker).

`frontend/.env`:
```
VITE_API_URL=http://localhost:8000
```

`alembic/env.py` reads `ALEMBIC_DATABASE_URL` (fallback `DATABASE_URL`) via `os.environ`, overriding `sqlalchemy.url` in `alembic.ini` (keep the ini value blank so no credential ever lands in git).

---

## 5. Baseline / rollback artifact (do this FIRST)

Snapshot current Supabase schema + data into the rebuild repo under `db/baseline/`. Requires PG17+ client tools (`pg_dump --version` ≥ 17; on Windows install "PostgreSQL 17 command line tools" or use the one bundled with pgAdmin). Use the session pooler DSN (IPv4):

```powershell
$SRC = "postgresql://postgres.tbeogvbjbaxgfwaoebfj:<db-password>@aws-1-eu-west-1.pooler.supabase.com:5432/postgres?sslmode=require"
# 1. schema (public only, portable: no owners/grants/RLS-owner noise)
pg_dump $SRC --schema=public --schema-only --no-owner --no-privileges -f "db/baseline/supabase_schema_2026-07-03.sql"
# 2. data as readable, re-playable INSERTs (includes invite_tokens for the record)
pg_dump $SRC --schema=public --data-only --column-inserts --rows-per-insert=100 -f "db/baseline/supabase_data_2026-07-03.sql"
# 3. binary belt-and-braces copy for exact restore
pg_dump $SRC --schema=public -Fc -f "db/baseline/supabase_full_2026-07-03.dump"
```

Notes: the schema dump will contain Supabase-isms (RLS policies, `is_admin()`, FK to `auth.users` may appear as a broken reference since `auth` schema is excluded) — that is fine, it is a *record*, not an input to the new system. The `.dump` restores with `pg_restore -d <db> --no-owner`. Commit the two `.sql` files; the `.dump` too (tiny). This is the rollback story: the old Supabase project also simply keeps running untouched until cutover is proven.

---

## 6. Ordered task list

| # | Task | Verification |
|---|---|---|
| 1 | **Baseline snapshot** (§5): create `db/baseline/`, run the three pg_dump commands against the Supabase pooler | Files exist; `supabase_data_*.sql` contains `INSERT INTO public.users` lines; grep confirms all 14 tables present; row counts in dump match §0 counts |
| 2 | **Provision roles on Azure PG** (§4.1) as Entra admin via psql + AAD token | `psql "...user=ai_hub_owner..." -c "select current_user"` and same for `ai_hub_app` both succeed with `sslmode=require`; `\du` shows both roles |
| 3 | **Backend scaffold + SQLAlchemy models** for all 14 target tables (§1) incl. naming convention, `auth_tokens`, redesigned `users`; `.env`/`.env.example` | `python -c "from app.models import Base; print(sorted(Base.metadata.tables))"` lists 14 tables |
| 4 | **Alembic init + initial migration**: autogenerate, hand-edit CHECKs/uniques/FK actions to match §1 exactly; run `alembic upgrade head` as `ai_hub_owner` | `alembic current` shows head; psql as admin: `\dt` shows 14 tables + `alembic_version`; compare `pg_dump --schema-only` of Azure vs §1 spec (spot-check CHECK constraints via `pg_constraint` query); **grant check**: connect as `ai_hub_app`, `SELECT` from `users` and `INSERT`/`DELETE` a probe row in `companies` |
| 5 | **Default-privileges proof** (guards the known pain): as `ai_hub_owner` run `CREATE TABLE _grant_probe(id int); ` then as `ai_hub_app` `SELECT * FROM _grant_probe;` then drop it as owner | app-role SELECT succeeds without any explicit GRANT |
| 6 | **Write migration script** `db/migrate_supabase_to_azure.py` (§3): psycopg3, TRUNCATE-and-load, users transform, skip invite_tokens, built-in verification | dry-run mode (`--check-only`) connects to both DBs and prints source counts |
| 7 | **Run migration** against Azure | Script's own gates: 13/13 row-count matches, PK-set md5 equal per table, `sum(jsonb_array_length(content_blocks))` equal, all target users `password_set=false ∧ password_hash IS NULL`, survey spot-check rows equal; exit code 0 |
| 8 | **Manual spot-check** in psql on Azure: one full lesson's `content_blocks` rendered JSON vs Supabase; one complete survey row field-by-field; FK sanity `SELECT count(*) FROM lesson_progress lp LEFT JOIN users u ON u.id=lp.user_id WHERE u.id IS NULL` = 0 | Human eyeball + zero-orphan queries |
| 9 | **Document** in `db/README.md`: role model, DSNs (placeholder passwords), re-run instructions for the migration script, baseline restore procedure | README exists; a teammate could re-provision from it |
| 10 | Re-run migration once more end-to-end (idempotency proof) before backend feature work starts | Same verification output; no duplicate-key errors |

Dependencies: 1 → (2,3 parallel) → 4 → 5 → 6 → 7 → 8 → 9/10. Steps 1–2 have no code dependency and unblock everything.

Anticipated challenges: (a) pg_dump client older than server 17 → install PG17 tools first; (b) Supabase direct host is IPv6-only → always use the pooler DSN; (c) Alembic autogenerate silently dropping CHECK constraints → hand-audit the initial revision against §1 (verification in task 4 catches it); (d) `ALTER DEFAULT PRIVILEGES` grantor mismatch → task 5 probe catches it; (e) hyphenated DB name → quote in SQL, fine in DSNs.

### Critical Files for Implementation
- C:\Users\danneelm\projects\AI enablement hub\AI ENABLEMENT HUB REBUILD\backend\app\models\__init__.py (new — SQLAlchemy Base + all 14 models; source of truth for schema)
- C:\Users\danneelm\projects\AI enablement hub\AI ENABLEMENT HUB REBUILD\backend\alembic\versions\0001_initial_schema.py (new — hand-verified initial migration)
- C:\Users\danneelm\projects\AI enablement hub\AI ENABLEMENT HUB REBUILD\db\migrate_supabase_to_azure.py (new — idempotent psycopg3 data migration with built-in verification)
- C:\Users\danneelm\projects\AI enablement hub\AI ENABLEMENT HUB REBUILD\db\provision_roles.sql (new — ai_hub_owner/ai_hub_app roles + default privileges)
- C:\Users\danneelm\projects\AI enablement hub\context.md (reference — schema/RLS/known-issues doc; note `modules.col_offset` there is stale vs live DB)