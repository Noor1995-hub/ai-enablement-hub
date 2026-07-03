# FastAPI Backend Design — AI Enablement Hub Rebuild

Target location: `c:\Users\danneelm\projects\AI enablement hub\AI ENABLEMENT HUB REBUILD\backend\`
Reference code inspected: `app/api/_lib/*` (auth.js, handlers.js, scoring.js, rateLimit.js, cors.js, constants.js), `app/src/**` per inventory, `context.md`.

---

## 1. Project structure & libraries

### Folder tree

```
backend/
├── pyproject.toml                # deps + tool config (use uv for env mgmt)
├── .env.example                  # documented env vars, no secrets
├── alembic.ini
├── alembic/
│   ├── env.py                    # sync psycopg URL for migrations
│   └── versions/
│       └── 0001_initial_schema.py    # full 14-table schema + new auth tables
├── app/
│   ├── main.py                   # app factory, CORSMiddleware, exception handlers,
│   │                             #   lifespan (engine + token-cleanup task)
│   ├── config.py                 # pydantic-settings Settings
│   ├── db.py                     # async engine, session factory, get_db dependency
│   ├── models.py                 # ALL SQLAlchemy 2.0 ORM models (14 tables + 2 auth tables
│   │                             #   is fine in one ~400-line file for this size)
│   ├── core/
│   │   ├── security.py           # ← IDENTITY-PROVIDER SEAM (see §2)
│   │   │                         #   hash_password/verify_password (argon2id)
│   │   │                         #   create_access_token/decode_access_token (PyJWT HS256)
│   │   │                         #   new_opaque_token/hash_token (secrets + sha256)
│   │   └── ratelimit.py          # in-process sliding-window limiter (port of rateLimit.js)
│   ├── api/
│   │   ├── deps.py               # get_current_user, require_admin (the ONLY authz entry points)
│   │   └── routers/
│   │       ├── auth.py           # login/refresh/logout/set-password/invite-token-info
│   │       ├── me.py             # /me profile + /me/journey
│   │       ├── survey.py         # learner survey draft/complete
│   │       ├── learning.py       # graph aggregate, module lessons, lesson detail, progress
│   │       ├── admin_org.py      # companies, projects, component settings
│   │       ├── admin_users.py    # users CRUD, invites, reset-links, track/module
│   │       │                     #   assignments, survey results
│   │       └── admin_content.py  # tracks/modules/lessons/prereqs CRUD + batch reorder
│   ├── schemas/                  # Pydantic v2 models, one file per router group
│   │   ├── auth.py
│   │   ├── users.py
│   │   ├── survey.py
│   │   ├── learning.py
│   │   └── admin.py
│   └── services/
│       ├── scoring.py            # pure port of scoring.js — zero I/O, zero FastAPI imports
│       └── tokens.py             # invite/reset token issue + validate + consume + cleanup
└── tests/
    ├── conftest.py               # app fixture, test DB session w/ per-test rollback, user factories
    ├── golden/scoring_golden.json
    ├── test_scoring.py           # golden parity suite
    ├── test_authz.py             # matrix tests (public/user/admin per endpoint)
    ├── test_invite_lifecycle.py  # invite → set-password → login → reset → reuse-rejection
    ├── test_survey_flow.py       # draft upsert → complete → scored fields persisted
    └── test_learning_graph.py    # aggregate endpoint shape vs seeded data
```

Rationale: no repository/UoW layers, no per-entity module explosion — ~28 endpoints, 6 users. Routers own their queries directly via SQLAlchemy; only two things are extracted into `services/`: scoring (must be pure for golden tests) and token logic (shared by invite/reset/set-password and cleanup task).

### Library choices (with reasoning)

| Concern | Choice | Version pin | Why |
|---|---|---|---|
| Framework | FastAPI | `>=0.115` | decided |
| Server | uvicorn[standard] | `>=0.30` | local dev; works in Container Apps later |
| ORM | SQLAlchemy 2.0 **async** | `>=2.0.36` | async is FastAPI-native; queries here are simple so async pitfalls are minimal |
| Driver | **psycopg 3** (`psycopg[binary]`) | `>=3.2` | one driver for both async app (`postgresql+psycopg://`) and sync Alembic; crucially it accepts `sslmode=require` directly in the DSN — asyncpg does not, which is a recurring pain point with Azure PG |
| Migrations | Alembic | `>=1.14` | standard; env.py uses the sync psycopg URL |
| Validation | Pydantic v2 + pydantic-settings | `>=2.9` / `>=2.6` | decided/standard |
| JWT | **PyJWT** | `>=2.10` | python-jose is effectively unmaintained with past CVEs; PyJWT also has `PyJWKClient` which is exactly what the later Entra swap needs |
| Password hashing | **argon2-cffi** (argon2id) | `>=23.1` | passlib is unmaintained (breaks on modern bcrypt); argon2id is the OWASP first choice; use library defaults (time_cost=3, 64 MiB) |
| Rate limiting | tiny custom in-process dependency (~30 lines, port of `rateLimit.js`) | — | slowapi adds Starlette-middleware friction for no benefit at this scale; current JS solution is the same design. Single-process local dev now; when Container Apps arrives, pin min/max replicas = 1 or move counters to a PG table (documented seam) |
| Tests | pytest, pytest-asyncio, httpx (`ASGITransport`) | `>=8.3` / `>=0.24` / `>=0.28` | in-process client, no live server needed |
| Test DB | second database `ai-enablement-hub-test` on the same Azure server (or local docker PG) | — | JSONB + text[] + ON CONFLICT rule out SQLite |

DSN (app role, not Entra admin):
`postgresql+psycopg://ai_hub_app:<pw>@imaginemore-playground-pg.postgres.database.azure.com:5432/ai-enablement-hub?sslmode=require`

---

## 2. Auth design

### New/changed tables (vs Supabase schema)

- `users`: **drop** `auth_id`; **add** `password_hash TEXT NULL`, `external_id TEXT NULL UNIQUE` (future Entra OID); keep `password_set BOOL`, `role` CHECK, `email` UNIQUE. All migrated users arrive with `password_hash = NULL, password_set = false` → matches the "re-invite manually" decision.
- `auth_tokens` (replaces `invite_tokens`): `id UUID PK, user_id UUID FK→users ON DELETE CASCADE, token_hash TEXT UNIQUE, purpose TEXT CHECK ('invite','reset'), expires_at TIMESTAMPTZ, used_at TIMESTAMPTZ NULL, created_at`. The raw token (43-char `secrets.token_urlsafe(32)`) is **never stored** — only its SHA-256. No more Supabase action links.
- `auth_sessions` (refresh tokens): `id UUID PK, user_id FK CASCADE, token_hash TEXT UNIQUE, expires_at, revoked_at NULL, created_at, last_used_at`.

### Endpoints & token model

| Endpoint | Auth | Behavior |
|---|---|---|
| `POST /api/auth/login` `{email, password}` | public, rate-limited 5/min per email | verify argon2; reject if `password_hash IS NULL` or `is_active=false`; returns `{access_token, refresh_token, token_type:"bearer", expires_in}` |
| `POST /api/auth/refresh` `{refresh_token}` | public | look up sha256 hash; must be unrevoked + unexpired; **rotate** (revoke old row, insert new) and issue fresh access token |
| `POST /api/auth/logout` `{refresh_token}` | public (token is the credential) | revoke session row; 204. Frontend also drops tokens |
| `GET /api/auth/invite/{token}` | public | validate (exists, unused, unexpired) **without consuming** → `{purpose, email, first_name}`; 410 if expired, 404 if unknown/used. Replaces `/api/invite/[id]` |
| `POST /api/auth/set-password` `{token, password}` | public, rate-limited | validate+consume token (set `used_at`), set `password_hash`, `password_set=true`, revoke all other outstanding tokens and sessions for the user, auto-login (returns token pair). Serves BOTH `invite` and `reset` purposes — replaces `supabase.auth.updateUser` + `/api/user/complete-password-setup` in one call |

**JWT (access token):** HS256, 256-bit secret from env. Claims: `sub` = internal user UUID, `iat`, `exp` (**30 min**), `iss:"ai-hub"`, `aud:"ai-hub-api"`, `typ:"access"`. Deliberately **no role claim** — role is read from `users` inside the dependency on every request (6 users; one indexed PK lookup; makes role changes instant and keeps the token shape identical to a future Entra token). Refresh token: opaque random, **14-day sliding** lifetime, rotation-on-use, stored hashed.

**Invite flow (admin-copies-link, no email):**
1. `POST /api/admin/invites` → validates email format + uniqueness + project exists → inserts `users` row (`password_set=false`) → inserts `auth_tokens` row (`purpose='invite'`, `expires_at = now()+7 days`) → returns `{link: "{APP_URL}/invite/{raw_token}"}`. Admin copies link from UI, as today.
2. Frontend `/invite/{token}` page calls `GET /api/auth/invite/{token}`, shows set-password form.
3. `POST /api/auth/set-password` completes it. Single-use enforced by `used_at`.

**Reset flow:** `POST /api/admin/users/{user_id}/reset-link` → same mechanism, `purpose='reset'`, revokes prior unused reset tokens for that user first. Rest identical.

### The Entra ID seam — exactly what changes later

Contract that never changes: every protected router depends on `get_current_user(...) -> User` (ORM row from **our** `users` table) and `require_admin`. Routers never inspect tokens.

| Module | Now | After Entra swap |
|---|---|---|
| `core/security.py::decode_access_token` | PyJWT HS256, self-issued | PyJWT + `PyJWKClient` against `https://login.microsoftonline.com/{tenant}/discovery/v2.0/keys`, validate `aud` = app-registration client ID. **~20 lines changed** |
| `api/deps.py::get_current_user` | claims → `users.id = sub` | claims → `users.external_id = oid`; fallback: match by `preferred_username` email once, write `external_id` (first-login linking). **~10 lines changed** |
| `routers/auth.py` | login/refresh/logout/set-password | **deleted** (MSAL on the frontend handles login/refresh); invite endpoint degrades to "create user row" only |
| `services/tokens.py`, `auth_tokens`, `auth_sessions`, `password_hash` | active | dead code/columns — drop at leisure |
| Everything else (routers, schemas, models, scoring, authz checks) | — | **zero changes** |

Concrete answer to "how hard": ~30 changed lines in two functions, one router deleted, frontend login page swapped for MSAL redirect. Roles stay in our `users.role` column throughout, so no Entra app-role configuration is ever required.

---

## 3. Complete endpoint contract

Conventions: all paths under `/api`. Auth levels: **P** public, **U** authenticated user, **A** admin. All IDs are UUIDs, validated by Pydantic. `204` for pure mutations. This covers all 13 legacy `/api` endpoints and all ~35 direct Supabase queries from the inventory.

### Router `auth.py` — see §2 (5 endpoints, all P)

### Router `me.py`
| Method/Path | Auth | Request → Response |
|---|---|---|
| `GET /me` | U | → `UserProfile {id, email, first_name, last_name, role, company_id, project_id, password_set}` — replaces AuthContext `users` select |
| `GET /me/journey` | U | → `{components: {assessment:{hidden,locked}, learning:{...}, interview:{...}}, survey_status: "not_started"\|"in_progress"\|"complete"}` — replaces JourneyHome's 2 queries; server applies `DEFAULT_HIDDEN/DEFAULT_LOCKED` fallback (constants move server-side, killing the D4 duplication) |

### Router `survey.py`
| Method/Path | Auth | Request → Response |
|---|---|---|
| `GET /survey/me` | U | → full `SurveyResponse` (all c*_code, b_*, q_*, status, current_step, updated_at) or `null` — Assessment resume |
| `PUT /survey/me` | U | `SurveyDraft` (all answer fields Optional; `c5_codes/b_tools/b_barriers: list[str]`; `q_excitement/q_timesink: max_length=2000` — fixes S5; `current_step: int`) → upsert on `user_id`, forced `status='in_progress'` unless already complete (409 if complete) → row |
| `POST /survey/complete` | U | no body → loads own in_progress row, runs `scoring.score_response`, writes rungs/level/band/flags + `status='complete'`, `completed_at`, `scored_at` → `{score_level, usage_band, mandatory_modules}`; 409 with clear message if no in_progress row (fixes B3) |

### Router `learning.py`
| Method/Path | Auth | Request → Response |
|---|---|---|
| `GET /learning/graph` | U | → **one aggregate** replacing LearningPath's 7-query chain: `{tracks:[{id,name,sort_order,track_type,color,assigned}], modules:[{id,track_id,title,sort_order,col_offset,assigned,lesson_count,completed_lesson_count}], prerequisites:[{module_id,prerequisite_module_id}]}` — 4 queries server-side in one session; `assigned` computed from user_tracks/user_modules for the caller |
| `GET /modules/{module_id}/lessons` | U | → `{lessons:[{id,title,sort_order,completed}], next_lesson_id}` — serves ModulePopup (first uncompleted) + LessonPage sidebar in one call |
| `GET /lessons/{lesson_id}` | U | → `{id, module_id, title, sort_order, content_blocks, module:{id,title,track_id,sort_order}, my_answers, next_lesson_id, next_module_id}` — collapses LessonPage's sequential prefetch chain (fixes B4) into one server-side response |
| `PUT /lessons/{lesson_id}/progress` | U | `{answers: dict\|null}` → upsert `lesson_progress (user_id, lesson_id)` ON CONFLICT → 204 |

### Router `admin_org.py` (all A)
| Method/Path | Request → Response |
|---|---|
| `GET /admin/companies` | → `{companies:[{id,name,projects:[{id,name,company_id,created_at}]}]}` |
| `POST /admin/companies` | `{name}` → 409 on case-insensitive dup → `{id,name}` |
| `POST /admin/projects` | `{name, company_id}` → creates project **+ 3 default `project_component_settings` rows in the same transaction** → `{id,name,company_id}` (splits the old type-discriminated POST) |
| `GET /admin/projects/{project_id}/components` | → `{components:{...}}` with defaults fallback |
| `PUT /admin/projects/{project_id}/components/{component}` | `{hidden?: bool, locked?: bool}`; `component` validated against Literal['assessment','learning','interview'] → upsert → 204 |

### Router `admin_users.py` (all A)
| Method/Path | Request → Response |
|---|---|
| `GET /admin/users?project_id=` | → `{users:[{id,email,first_name,last_name,role,is_active,password_set,created_at,company_id,project_id,company_name,project_name,assigned_track_ids,assigned_module_ids}]}` |
| `POST /admin/invites` | `{email, first_name, last_name, project_id}` → rate-limited per email → `{link}` (§2) |
| `POST /admin/users/{user_id}/reset-link` | no body → rate-limited → `{link}` |
| `PATCH /admin/users/{user_id}` | `{role: Literal['admin','user']}` → 204 |
| `DELETE /admin/users/{user_id}` | single DELETE, FK cascades wipe tokens/sessions/progress/survey — fixes B2's two-system atomicity problem by construction → 204 |
| `PUT /admin/users/{user_id}/tracks/{track_id}` | `{assigned: bool}` → upsert or delete `user_tracks` → 204 |
| `PUT /admin/users/{user_id}/modules/{module_id}` | `{assigned: bool}` → same for `user_modules` → 204 |
| `GET /admin/learning` | → `{modules:[{id,track_id,title,sort_order}], users:[{id,first_name,last_name,project_name,company_name,assigned_track_ids,assigned_module_ids}]}` |
| `GET /admin/surveys?user_ids=a,b,c` | → `{levels:{[user_id]: score_level}}` (DISTINCT ON user_id ORDER BY completed_at DESC — preserves the B1 fix) |
| `GET /admin/surveys/{user_id}` | → `{survey: {...full scored row...} \| null}` (latest complete) |

### Router `admin_content.py` (write = A; two reads are U because learner UI needs them)
| Method/Path | Auth | Request → Response |
|---|---|---|
| `GET /tracks` | U | → `[{id,name,sort_order,track_type,color}]` — Admin track panel, AddTrackModal/AddModuleModal dropdowns |
| `GET /tracks/{track_id}/modules` | U | → `[{id,title,sort_order}]` — AddModuleModal predecessor picker |
| `POST /admin/tracks` | A | `{name, track_type: Literal['tool','general'], color}` → **server computes** `sort_order = max+1` inside the transaction (mitigates A4) → track |
| `POST /admin/modules` | A | `{track_id, title, col_offset?: -1\|0\|1, after_module_id?: UUID, prerequisite_ids?: [UUID]}` → server computes sort_order, shifts successors (`UPDATE ... SET sort_order = sort_order + 1 WHERE ...` — fixes DB6), inserts prerequisites in same transaction → module |
| `POST /admin/lessons` | A | `{module_id, title}` → sort_order = max+1, `content_blocks=[]` → `{id,title,sort_order}` |
| `PATCH /admin/lessons/{lesson_id}` | A | `{title?, content_blocks?: list[dict]}` → lesson (LessonPage MDX editor save) |
| `DELETE /admin/lessons/{lesson_id}` | A | → 204 (lesson_progress rows cascade) |
| `PUT /admin/modules/{module_id}/lessons/order` | A | `{lesson_ids: [UUID, ...]}` → validates set equality with module's lessons → single transaction assigning index positions → 204. **Replaces ModulePanel's N parallel updates (fixes B5)** |

Total: 29 endpoints. `curricula` table: migrated as data, no endpoints (nothing in the frontend touches it); add later if needed.

---

## 4. Authorization matrix (38 RLS policies → app checks)

Two dependencies do all the work; ownership filters live in the queries themselves:

- `get_current_user` — decode JWT, load `users` row, 401 on failure. (No 60s role cache needed: it existed to save a Supabase round trip; here it's one local PK lookup.)
- `require_admin = Depends(get_current_user)` + `role=='admin'` check, 403 otherwise.

| Table | Old RLS intent | App enforcement |
|---|---|---|
| `users` | read own row; admin all; admin write | own row only via `GET /me` (query hardwired to `current_user.id`); all admin ops behind `require_admin`; **no endpoint accepts a caller-supplied user_id outside `/admin/*`** |
| `companies`, `projects` | admin read/write | `/admin/*` only; learners see only their own `company_id/project_id` values via `/me` |
| `project_component_settings` | read own project; admin write | `/me/journey` filters `project_id = current_user.project_id`; writes admin-only |
| `tracks`, `curricula` | public read; admin write | `GET /tracks` requires U (public read was incidental to the anon-key architecture; nothing anonymous needs it); writes A |
| `modules`, `module_prerequisites`, `lessons` | authenticated read; admin write | reads U; all writes in `admin_content` (A) |
| `user_tracks`, `user_modules` | read own; admin write | `/learning/graph` filters `user_id = current_user.id`; assignment writes A only |
| `lesson_progress` | read/upsert own | every query/upsert hardwires `current_user.id`; lesson_id is the only client input; UNIQUE (user_id,lesson_id) upsert |
| `survey_responses` | read/write own; admin read | `/survey/*` hardwires `current_user.id`; `/admin/surveys*` behind A |
| `invite_tokens` → `auth_tokens` | service-role only | never exposed; only `services/tokens.py` touches it; raw token is the sole credential |
| `is_admin()` SECURITY DEFINER fn | RLS helper | replaced by `require_admin` dependency; not recreated in PG |

Rule of thumb encoded in tests: **any endpoint outside `/admin/*` must never read a user identifier from the request** — it comes exclusively from the token.

The rebuilt DB keeps CHECK/UNIQUE/FK constraints and the `set_updated_at` trigger (defense in depth) but does **not** enable RLS — the app role is the only client and authz is application-level.

---

## 5. Survey scoring port

`app/services/scoring.py` — line-for-line port of `app/api/_lib/scoring.js` (123 lines, fully deterministic, I read it in full):

- `RUNG = {"MISSING":0,"PARTIAL":1,"HAVE":2,"ADV_D":3,"ADV_E":3}`; `competency_rung(code, bucket)` raising `ScoringError(422, msg)` (custom exception; router maps to HTTP 422).
- `c5_rung(codes)` — preserve the exact cascade order: PUBLIC_PASTE → (APPROVED|KEPT_OUT ⇒ 1 else 0); APPROVED_PASTE ⇒ 2; KEPT_OUT ⇒ 2; UNSURE ⇒ 1; NO_USE alone ⇒ `None`; else 422. `safety_flag = 'PUBLIC_PASTE' in codes`.
- `USAGE_BAND_MATRIX` verbatim 5×5 dict; unknown keys → `None`.
- `score_response(answers: dict) -> dict` — careful with the one JS/Python trap: `c5_rung >= 2` in JS with `null` is `false`; in Python `None >= 2` raises. Port as `c5_ok = c5 is not None and c5 >= 2`; integrator gate uses `c5_ok`. Same for `mandatory_modules` (`c5 is not None and c5 < 2`).

**Golden-test plan (parity proof):**
1. One-off Node script (run manually during implementation, output committed): import the real `scoring.js`, enumerate a corpus, dump `tests/golden/scoring_golden.json` as `[{input, output|{error_status}}]`. Corpus: full cartesian product of `c1..c4, c6 ∈ 5 valid codes` is 3,125 — too big × c5; instead: (a) all 31 non-empty subsets of the 5 C5 codes with fixed competent baseline; (b) all 25 freq×breadth pairs + unknown/None pairs; (c) ~500 pseudo-random (seeded) full-answer combos including invalid codes and missing fields to lock error behavior; (d) hand-picked boundary cases: exactly integrator, integrator-minus-one on each of the four gate conditions, have_count 2/3 boundary, NO_USE-only null c5 with otherwise-integrator answers.
2. `test_scoring.py` replays the JSON against the Python port; asserts exact equality including `mandatory_modules` ordering (`safe-use` before `trust`) and error statuses.
3. Migration-day check (script, not pytest): re-score every migrated `complete` survey_responses row with Python and diff against the stored rungs/level/band columns — real-data parity on actual production answers.

---

## 6. Cross-cutting

- **Config (`config.py`)**: `class Settings(BaseSettings)` with `database_url: PostgresDsn`, `jwt_secret: SecretStr`, `jwt_issuer="ai-hub"`, `jwt_audience="ai-hub-api"`, `access_token_minutes=30`, `refresh_token_days=14`, `invite_ttl_days=7`, `app_url: AnyHttpUrl` (CORS origin + link base), `env: Literal['dev','prod']='dev'`; `model_config = SettingsConfigDict(env_file=".env")`. `.env.example` committed; `.env` gitignored.
- **CORS**: `CORSMiddleware(allow_origins=[settings.app_url] + (["http://localhost:3000","http://localhost:5173"] if dev), allow_methods=["GET","POST","PUT","PATCH","DELETE","OPTIONS"], allow_headers=["Authorization","Content-Type"], max_age=86400)`. No `allow_credentials` (Bearer header, no cookies).
- **Error shape**: single convention `{"error": {"code": str, "message": str}}` via handlers for `HTTPException` (code from a small registry or "http_error"), `RequestValidationError` → 422 `{"error":{"code":"validation_error","message":..., "fields":[...]}}`, `ScoringError` → 422, catch-all 500 with generic message (details logged only). Frontend gets one shape to parse everywhere.
- **Rate limiting** (`core/ratelimit.py`): dict of `key -> (window_start, count)` with the same 5/60s semantics as `rateLimit.js`; used as `Depends(rate_limit("login", key=lambda body: body.email))` on login, set-password (keyed by client IP), invite and reset-link (keyed by target email — matches current behavior). Honest limitation documented: in-process, resets on restart; fine for one local process / one replica; PG-table fallback noted for multi-replica future.
- **Token cleanup** (fixes DB2): (a) opportunistic `DELETE FROM auth_tokens WHERE expires_at < now()` piggybacked on token validation; (b) lifespan-started `asyncio` task running every 24 h deleting expired `auth_tokens` and expired/revoked `auth_sessions`. No pg_cron dependency.
- **OpenAPI**: free `/docs` — becomes the contract document for the frontend agent.

---

## 7. Build order, effort, testing strategy

| Step | Deliverable | Effort |
|---|---|---|
| 1 | Scaffold: pyproject, config, db.py, `models.py` (16 tables), Alembic `0001` applied to the empty Azure DB, dedicated `ai_hub_app` PG role | 0.5–1 d |
| 2 | `core/security.py`, `services/tokens.py`, `auth.py` router (login/refresh/logout/set-password/invite-info), deps.py | 1–1.5 d |
| 3 | `me.py` router + error handlers + CORS + rate limiter | 0.5 d |
| 4 | `services/scoring.py` + golden corpus generation + `survey.py` router | 1 d |
| 5 | `learning.py` incl. `/learning/graph` aggregate | 1 d |
| 6 | `admin_org.py` + `admin_users.py` (invite/reset wired to step 2) | 1 d |
| 7 | `admin_content.py` incl. batch reorder + module-insert shifting | 0.5–1 d |
| 8 | Cleanup task, hardening pass, remaining tests, OpenAPI review | 1 d |

Total ≈ **7–8 dev-days**. Steps 4–7 are parallelizable after step 3.

**Must-have tests (non-negotiable):**
1. `test_scoring.py` — golden parity (§5). Highest-value, zero-DB, write first.
2. `test_invite_lifecycle.py` — invite → link → info → set-password → login works; token reuse → 404/410; expired (freeze time) → 410; reset revokes old reset tokens; set-password revokes sessions.
3. `test_authz.py` — parametrized matrix: every endpoint × {no token, user token, admin token} asserts 401/403/2xx per §3; plus own-row isolation (user B cannot see user A's survey/progress/graph via any endpoint).
4. `test_survey_flow.py` — draft upsert idempotency, complete-without-draft 409, scored columns persisted, complete-twice 409.
5. `test_learning_graph.py` — seeded tracks/modules/prereqs/lessons/progress produce correct counts and `assigned` flags; batch reorder rejects mismatched lesson-id sets.

Auth/refresh happy-path and rotation tests fold into 2. Everything runs against a throwaway PG database with per-test transaction rollback in `conftest.py`.

---

### Critical Files for Implementation
- `C:\Users\danneelm\projects\AI enablement hub\app\api\_lib\scoring.js` — source of truth for the scoring port and golden corpus
- `C:\Users\danneelm\projects\AI enablement hub\app\api\_lib\handlers.js` — exact legacy business logic (validation, upsert conflict keys, response shapes) for every admin/user endpoint
- `C:\Users\danneelm\projects\AI enablement hub\app\api\_lib\auth.js` — legacy requireAdmin/requireUser semantics being replaced by `deps.py`
- `C:\Users\danneelm\projects\AI enablement hub\context.md` — schema, RLS intent, and known issues (B1–B5, DB2, DB6) the new backend must fix
- `C:\Users\danneelm\projects\AI enablement hub\app\src\pages\LearningPath.jsx` — the 7-query chain that defines the `/learning/graph` aggregate contract