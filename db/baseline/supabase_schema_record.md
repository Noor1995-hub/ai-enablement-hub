# Supabase Schema Record — baseline snapshot 2026-07-03

Authoritative record of the live Supabase schema (project `tbeogvbjbaxgfwaoebfj`, PG 17.6, eu-west-1)
at the moment of the Azure rebuild baseline. Extracted live via the Supabase MCP (read-only queries of
`pg_catalog`/`information_schema`). This is a **record for rollback/reference**, not an input to the new
system — the new schema is defined by SQLAlchemy models + Alembic in `backend/`.

Data snapshot: `data/*.json` (one file per table, exported via PostgREST with the service-role key by
`../export_supabase_snapshot.py`; counts in `data/_manifest.json`). Total 202 rows across 14 tables.

Legacy naming note: `companies` was once named `clients` — its PK index is `clients_pkey` and the FK
from `users.company_id` is named `users_client_id_fkey`. Recorded as-is.

Known staleness in `context.md` corrected here: `modules` has NO `col_offset` column (has `description`);
`lesson_progress` has an `answers jsonb` column; lesson content has 7 block types (incl. `question`).

---

## Tables (columns · defaults · nullability)

### companies — 4 rows
| column | type | null | default |
|---|---|---|---|
| id | uuid PK | no | gen_random_uuid() |
| name | text | no | |
| created_at | timestamptz | no | now() |

### projects — 5 rows
| column | type | null | default |
|---|---|---|---|
| id | uuid PK | no | gen_random_uuid() |
| name | text | no | |
| company_id | uuid | no | |
| created_at | timestamptz | no | now() |

### project_component_settings — 8 rows
| column | type | null | default |
|---|---|---|---|
| id | uuid PK | no | gen_random_uuid() |
| project_id | uuid | no | |
| component | text | no | CHECK IN ('assessment','learning','interview') |
| locked | bool | no | false |
| hidden | bool | no | false |
| updated_at | timestamptz | no | now() |

### users — 6 rows
| column | type | null | default |
|---|---|---|---|
| id | uuid PK | no | gen_random_uuid() |
| auth_id | uuid → auth.users(id) | no* | |
| email | text UNIQUE | no | |
| first_name | text | no | |
| last_name | text | no | |
| company_id | uuid | yes | |
| is_active | bool | no | true |
| created_at | timestamptz | yes | now() |
| role | text | no | 'user' — CHECK IN ('admin','user') |
| project_id | uuid | yes | |
| updated_at | timestamptz | yes | now() |
| password_set | bool | no | false |

\* auth_id column reported NOT NULL by catalog but FK is ON DELETE SET NULL (latent conflict in live schema; irrelevant after rebuild — column dropped).

### tracks — 7 rows
| column | type | null | default |
|---|---|---|---|
| id | uuid PK | no | gen_random_uuid() |
| name | text | no | |
| sort_order | int | no | 0 |
| track_type | text | no | CHECK IN ('general','tool') |
| color | text | yes | |
| created_at | timestamptz | no | now() |

### curricula — 7 rows (referenced by nothing; data-only in rebuild)
| column | type | null | default |
|---|---|---|---|
| id | uuid PK | no | gen_random_uuid() |
| track_id | uuid | no | |
| name | text | no | 'default' |
| created_at | timestamptz | yes | now() |

### modules — 27 rows
| column | type | null | default |
|---|---|---|---|
| id | uuid PK | no | gen_random_uuid() |
| track_id | uuid | no | |
| title | text | no | |
| description | text | yes | |
| sort_order | int | no | 0 |
| created_at | timestamptz | no | now() |

### module_prerequisites — 23 rows
| column | type | null | default |
|---|---|---|---|
| module_id | uuid (PK part) | no | |
| prerequisite_module_id | uuid (PK part) | no | |
| created_at | timestamptz | no | now() |

CHECK (module_id <> prerequisite_module_id)

### lessons — 25 rows
| column | type | null | default |
|---|---|---|---|
| id | uuid PK | no | gen_random_uuid() |
| module_id | uuid | no | |
| title | text | no | |
| sort_order | int | no | 0 |
| content_blocks | jsonb | no | '[]' |
| created_at | timestamptz | no | now() |

### user_tracks — 18 rows
id uuid PK gen_random_uuid() · user_id uuid NOT NULL · track_id uuid NOT NULL · assigned_at timestamptz NOT NULL now() · UNIQUE (user_id, track_id)

### user_modules — 53 rows
id uuid PK gen_random_uuid() · user_id uuid NOT NULL · module_id uuid NOT NULL · assigned_at timestamptz NOT NULL now() · UNIQUE (user_id, module_id)

### lesson_progress — 4 rows
id uuid PK gen_random_uuid() · user_id uuid NOT NULL · lesson_id uuid NOT NULL · completed_at timestamptz NOT NULL now() · answers jsonb NOT NULL '{}' · UNIQUE (user_id, lesson_id)

### survey_responses — 2 rows
| column | type | null | default |
|---|---|---|---|
| id | uuid PK | no | gen_random_uuid() |
| user_id | uuid | no | UNIQUE (via unique index `survey_responses_user_id_idx`) |
| status | text | no | 'in_progress' — CHECK IN ('in_progress','complete') |
| instrument_version | text | no | '1.0' |
| current_step | int | no | 0 |
| job_title, department | text | yes | |
| consent | bool | yes | |
| c1_code..c4_code, c6_code | text | yes | |
| c5_codes | text[] | yes | |
| b_freq, b_breadth | text | yes | |
| b_setup, b_tools, b_barriers | text[] | yes | |
| b_attitude, b_readiness | smallint | yes | |
| q_excitement, q_timesink | text | yes | |
| score_level | text | yes | CHECK IN ('explore','practitioner','integrator') |
| c1_rung..c6_rung | smallint | yes | |
| have_count, adv_count | smallint | yes | |
| safety_flag | bool | yes | |
| mandatory_modules | text[] | yes | |
| usage_band | text | yes | CHECK IN ('dormant','occasional','regular','embedded') |
| started_at | timestamptz | no | now() |
| completed_at, scored_at | timestamptz | yes | |
| updated_at | timestamptz | no | now() |

### invite_tokens — 13 rows (NOT migrated — stale Supabase action links)
id text PK (32-char hex) · supabase_link text NOT NULL · email text NOT NULL · created_at timestamptz now()

---

## Foreign keys (live definitions)

| table.column | references | on delete |
|---|---|---|
| projects.company_id | companies(id) | CASCADE |
| project_component_settings.project_id | projects(id) | CASCADE |
| users.auth_id | auth.users(id) | SET NULL |
| users.company_id (`users_client_id_fkey`) | companies(id) | NO ACTION |
| users.project_id | projects(id) | SET NULL |
| curricula.track_id | tracks(id) | CASCADE |
| modules.track_id | tracks(id) | CASCADE |
| module_prerequisites.module_id | modules(id) | CASCADE |
| module_prerequisites.prerequisite_module_id | modules(id) | CASCADE |
| lessons.module_id | modules(id) | CASCADE |
| user_tracks.user_id / .track_id | users(id) / tracks(id) | CASCADE / CASCADE |
| user_modules.user_id / .module_id | users(id) / modules(id) | CASCADE / CASCADE |
| lesson_progress.user_id / .lesson_id | users(id) / lessons(id) | CASCADE / CASCADE |
| survey_responses.user_id | users(id) | CASCADE |

## Non-PK indexes

idx_curricula_track_id · lessons_module_id_idx · idx_module_prerequisites_prerequisite_module_id ·
idx_modules_track_id · idx_projects_company_id · survey_responses_user_id_idx (UNIQUE) ·
idx_user_modules_module_id · user_modules_user_id_module_id_key (UNIQUE) · idx_user_tracks_track_id ·
user_tracks_user_id_track_id_key (UNIQUE) · lesson_progress_user_id_lesson_id_key (UNIQUE) ·
idx_users_company_id · idx_users_project_id · users_auth_id_idx · users_email_key (UNIQUE) ·
project_component_settings_project_id_component_key (UNIQUE)

## Functions & triggers

```sql
CREATE OR REPLACE FUNCTION public.is_admin() RETURNS boolean
 LANGUAGE sql SECURITY DEFINER SET search_path TO 'public' AS $$
  select exists (select 1 from public.users where auth_id = auth.uid() and role = 'admin')
$$;

CREATE OR REPLACE FUNCTION public.set_updated_at() RETURNS trigger
 LANGUAGE plpgsql SET search_path TO 'public' AS $$
BEGIN NEW.updated_at = now(); RETURN NEW; END; $$;
-- trigger exists on `users` only
```

Neither is recreated on Azure: `is_admin()` becomes the FastAPI `require_admin` dependency;
`updated_at` becomes SQLAlchemy `onupdate=func.now()`.

## RLS policies (38 — all become FastAPI application-level checks)

| table | policy | cmd | rule (summarized) |
|---|---|---|---|
| companies | read own company | SELECT | id = caller's users.company_id |
| curricula | Public read / authenticated read | SELECT ×2 | true |
| lesson_progress | Users manage their own progress | ALL | user_id = caller's users.id |
| lessons | Authenticated read | SELECT | auth.role() = 'authenticated' |
| lessons | Admin write/update/delete | INS/UPD/DEL | is_admin() |
| module_prerequisites | authenticated read | SELECT | true |
| module_prerequisites | admin write/update/delete | INS/UPD/DEL | is_admin() |
| modules | authenticated read | SELECT | true (authenticated role) |
| modules | admin insert/update/delete | INS/UPD/DEL | is_admin() / role='admin' EXISTS check |
| project_component_settings | select own project or admin | SELECT | project_id = caller's project_id OR caller is admin |
| project_component_settings | admin insert/update/delete | INS/UPD/DEL | caller users.role = 'admin' |
| projects | select own or admin | SELECT | id = caller's project_id OR admin |
| projects | admin insert/update/delete | INS/UPD/DEL | caller users.role = 'admin' |
| survey_responses | read own / insert own | SELECT, INSERT | user_id = caller's users.id |
| survey_responses | update own in_progress | UPDATE | own row AND status='in_progress' (both qual & check) |
| tracks | Public read | SELECT | true |
| tracks | admin insert/update/delete | INS/UPD/DEL | is_admin() |
| user_modules | read own | SELECT | user_id = caller's users.id |
| user_modules | admin insert/delete | INS/DEL | admin EXISTS check |
| user_tracks | read own | SELECT | user_id = caller's users.id |
| user_tracks | admin insert/delete | INS/DEL | admin EXISTS check |
| users | read own row | SELECT | auth_id = auth.uid() |

## Grants quirk (fixed 2026-07-03, user-authorized)

`lessons` and `lesson_progress` were missing `service_role` SELECT grants (tables created without the
standard Supabase default privileges — same class of issue as the project's earlier grant problems).
Fixed via `GRANT SELECT ON public.lessons, public.lesson_progress TO service_role;` to enable the
PostgREST snapshot export. No other grants were changed.

## Re-export / true pg_dump

Re-run the JSON snapshot anytime: `uv run ../export_supabase_snapshot.py` (service-role key from
`app/.env.local`). For a byte-exact `pg_dump` baseline (optional), install PG17+ client tools and use the
**session pooler** DSN (direct DB host is IPv6-only; password from Supabase Dashboard → Settings → Database):

```powershell
pg_dump "postgresql://postgres.tbeogvbjbaxgfwaoebfj:<DB_PASSWORD>@aws-1-eu-west-1.pooler.supabase.com:5432/postgres?sslmode=require" --schema=public --schema-only --no-owner --no-privileges -f supabase_schema.sql
pg_dump "<same DSN>" --schema=public --data-only --column-inserts --rows-per-insert=100 -f supabase_data.sql
```
