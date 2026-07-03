---
name: python-be-architecture
description: Set up and build a Python + FastAPI backend using the layered, iDesign-aligned architecture from the delaware Python template — uv + Python 3.13, async SQLAlchemy 2.0, Alembic migrations, Pydantic-Settings config, a strict router→service→repository→model layering, bcrypt security, distroless Docker, and pytest with in-memory SQLite. Use when scaffolding a new FastAPI backend, adding a feature slice (model + repository + service + router + schemas), wiring settings/DB/DI, setting up Alembic migrations, or reviewing BE code for these conventions. Triggers on "new FastAPI app", "set up backend", "BE setup", "add an endpoint", "add a model", "wire the database", "add a migration", "BE architecture".
---

# Python FastAPI Backend Architecture (layered / iDesign)

A reusable blueprint for a Python + FastAPI backend, extracted from a working delaware template.
It describes **how the code is layered, how a request flows, and how to add a feature** — copy the
patterns, not the domain (the `User` slice is the reference example). Apply every relevant rule
before writing BE code.

The organising idea mirrors **iDesign** layering. A request flows **downward only**: a **router**
(HTTP edge) calls a **service** (use case / business logic) → the service calls a **repository**
(data access) → the repository talks to the DB via SQLAlchemy models. **Schemas** (Pydantic DTOs)
cross the HTTP boundary; **DB models** never leave the router untranslated. Dependency injection
wires each layer together in `core/dependencies/`. Nothing calls upward.

## Stack (baseline versions)

| Concern | Choice |
|---|---|
| Language / runtime | Python `~=3.13` (pinned in `.python-version`) |
| Package / venv manager | **uv** (`uv sync`, `uv run`, `uv.lock` committed) |
| Task runner | **poethepoet** (`poe <task>`, tasks in `pyproject.toml`) |
| Web framework | **FastAPI** `~=0.135` |
| ASGI server | **uvicorn[standard]** `~=0.44` (+ `httptools` in prod) |
| ORM | **SQLAlchemy 2.0** async (`AsyncSession`, `Mapped`/`mapped_column`) |
| DB drivers | `aiosqlite` (dev/test), `asyncpg` (prod PostgreSQL) |
| Migrations | **Alembic** `~=1.18` (async env, autogenerate) |
| Config | **pydantic-settings** — nested env, `SecretStr`, frozen models |
| Password hashing | **bcrypt** (thin wrappers in `core/security.py`) |
| Lint / format | **ruff** (`ruff check`, `ruff format`) |
| Type check | **ty** (`uvx ty check`) |
| Testing | **pytest** + `pytest-asyncio` (auto mode) + `pytest-cov`, `httpx` ASGI client |

## Project layout

The backend is its own root (sibling to `frontend/`, orchestrated by a top-level
`docker-compose.yml`). Everything below lives under `backend/`.

```
backend/
  src/
    main.py                     ← FastAPI app + lifespan (creates the async engine)
    core/
      configs/
        settings.py             ← root Settings (BaseSettings), composes sub-settings
        database.py             ← DatabaseSettings + computed connection URL
      dependencies/
        settings.py             ← get_settings()
        database.py             ← get_db() / get_session() (per-request AsyncSession)
        user.py                 ← get_user_repository() / get_user_service() (DI wiring)
      security.py               ← hash_password / verify_password (bcrypt)
    db/
      base.py                   ← DeclarativeBase (shared `Base`, `to_dict()`)
      models/<entity>.py        ← SQLAlchemy models (the DB shape)
    repositories/
      base.py                   ← Abstract<Entity>Repository (ABC, the contract)
      <entity>_repository.py    ← concrete data-access implementation
    services/
      <entity>_service.py       ← business logic / use cases
    routers/
      <entity>s.py              ← APIRouter with the HTTP endpoints
    schemas/
      <entity>.py               ← Pydantic DTOs: <Entity>Create/Update/Response
  alembic/
    env.py                      ← async migration env (pulls URL from Settings)
    versions/                   ← migration scripts
  tests/
    conftest.py                 ← engine/session/app/client fixtures + auto-markers
    fixtures/                   ← repository & service fixtures
    unit/ integration/          ← mirror the src layers
  startup.py                    ← prod entrypoint: run migrations, then start uvicorn
  pyproject.toml                ← deps, optional-deps (dev/prod), poe tasks
  alembic.ini  .coveragerc  Dockerfile  .python-version
  .env.local.example  .env.prod.example  .env.docker
```

Every package has an `__init__.py`. Imports are absolute from `src` (e.g.
`from src.services.user_service import UserService`), never relative across layers.

## Layers and responsibilities

Follow this table strictly — it is the whole architecture. When adding code, decide its layer
first, then write it there.

| Layer | Package | Contains | May depend on |
|---|---|---|---|
| **Router** | `routers/` | `APIRouter` with `prefix`/`tags`, endpoint functions, status codes. Depends on a **service** via `Depends`. Validates/serialises with **schemas** — maps DB model → `Response` schema with `model_validate`. No business logic, no DB access. | services, schemas, DI deps |
| **Service** | `services/` | Business logic / use cases (hashing a password, composing updates, enforcing rules). Takes an **abstract repository** in its constructor. Returns DB models or primitives. | repositories (abstract), schemas, core/security |
| **Repository** | `repositories/` | All data access. A concrete class extends the module's `Abstract<Entity>Repository` (ABC). Owns `select`/`add`/`commit`/`refresh`/`delete`. The **only** layer that touches the session/queries. | db models, SQLAlchemy |
| **Model** | `db/models/` | SQLAlchemy declarative models (`Mapped`/`mapped_column`) — the persisted shape. | `db.base.Base` |
| **Schema** | `schemas/` | Pydantic DTOs for the wire: `Create`, `Update` (all-optional), `Response` (`from_attributes=True`). Never expose secrets (e.g. no `password_hash` in `Response`). | — |
| **Core** | `core/` | Cross-cutting: `Settings`, DI providers (`get_*`), `security`. | pydantic-settings, SQLAlchemy |

### Non-negotiable rules

- **Calls flow downward only.** Router → service → repository → model. A service never imports a
  router; a repository never imports a service. Services never import other services.
- **Depend on the abstraction.** Services type their constructor arg as the
  `Abstract<Entity>Repository` ABC (import under `TYPE_CHECKING`), not the concrete class — so they
  can be unit-tested with an `AsyncMock`. The concrete repo is chosen in `core/dependencies/`.
- **DB models never cross the HTTP boundary raw.** Routers convert models to `Response` schemas
  with `Response.model_validate(obj)` (schemas set `model_config = {"from_attributes": True}`).
  Request bodies arrive as `Create`/`Update` schemas.
- **DI is explicit and chained.** Endpoints declare `service: XService = Depends(get_x_service)`;
  `get_x_service` depends on `get_x_repository`, which depends on `get_session`. Add a new wiring
  function per entity in `core/dependencies/`.
- **One `AsyncSession` per request**, yielded by `get_session` from the app-state engine. The
  engine is created once in the `lifespan` and stored on `app.state.db_engine`; never create
  engines per request.
- **Secrets stay secret.** DB password is `SecretStr`; the connection URL is a computed `SecretStr`
  with `hide_parameters=True` on the engine. Never log or return credentials.
- **Async all the way down.** Every I/O function is `async`; repositories `await session.execute`.
  No sync SQLAlchemy sessions.
- **`from __future__ import annotations`** at the top of modules with type-only imports, and put
  cross-layer type imports under `if TYPE_CHECKING:` to avoid import cycles.
- **`__all__`** is declared in every module, listing its public names.
- **Type everything.** Full annotations on parameters and returns; keep `ty` and `ruff` clean.

## Configuration (pydantic-settings)

Nested settings loaded from env / `.env`, using `__` as the nesting delimiter and a **frozen**
model so config is immutable at runtime.

```python
# core/configs/settings.py
class Settings(BaseSettings):
    database: DatabaseSettings
    model_config = SettingsConfigDict(
        frozen=True, env_file=".env", env_file_encoding="utf-8",
        case_sensitive=False, extra="ignore", env_nested_delimiter="__",
    )
```

So `DATABASE__PROTOCOL=postgresql`, `DATABASE__HOST=…` populate `settings.database.*`. The DB URL
is a **computed** `SecretStr` that switches driver by protocol (`sqlite+aiosqlite` for dev/test,
`postgresql+asyncpg` for prod, appends `?ssl=<mode>` when set, and requires a password for
PostgreSQL). Add a new sub-settings model (a frozen `BaseModel`) per concern and compose it onto
`Settings` — mirror `DatabaseSettings`.

Provide env examples, not real `.env`: `.env.local.example` (Postgres for local),
`.env.prod.example` (managed Postgres + `SSL_MODE=require`), `.env.docker` (compose). Default
protocol is SQLite so the app boots with zero config.

## Database engine & session

```python
# main.py — engine lives for the app's lifetime
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    settings = get_settings()
    kwargs = {"url": settings.database.url.get_secret_value(), "hide_parameters": True}
    if settings.database.protocol == DatabaseProtocol.POSTGRESQL:
        kwargs.update(pool_size=..., max_overflow=..., pool_pre_ping=True)
    engine = create_async_engine(**kwargs)
    app.state.db_engine = engine
    yield
    await engine.dispose()
```

```python
# core/dependencies/database.py — one session per request
async def get_session(request: Request) -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSession(request.app.state.db_engine) as session:
        yield session
```

Connection pooling (`pool_size`, `max_overflow`, `pool_pre_ping`) applies **only** to PostgreSQL;
SQLite skips it.

## Adding a feature slice (the recipe)

Build one layer at a time, downward. Mirror the `User` slice exactly.

1. **Model** (`db/models/<entity>.py`): a SQLAlchemy model extending `Base`, using
   `Mapped[...] = mapped_column(...)`. Add `created_on`/`updated_on` with
   `server_default=func.now()` (and `onupdate=func.now()` for updated). Declare `__all__`.

2. **Schemas** (`schemas/<entity>.py`): `Create` (required fields), `Update` (all fields optional,
   default `None`), `Response` (safe fields only, `model_config = {"from_attributes": True}`).
   Never put secrets in `Response`.

3. **Repository** (`repositories/base.py` + `<entity>_repository.py`): first define
   `Abstract<Entity>Repository(ABC)` with `__init__(self, session: AsyncSession)` and
   `@abstractmethod` signatures (`get_all`, `get_by_id`, `create`, `update`, `delete`, …). Then the
   concrete class implements them with async SQLAlchemy:
   ```python
   async def get_by_id(self, entity_id: int) -> Entity | None:
       result = await self._session.execute(select(Entity).where(Entity.id == entity_id))
       return result.scalar_one_or_none()

   async def create(self, ...) -> Entity:
       obj = Entity(...)
       self._session.add(obj)
       await self._session.commit()
       await self._session.refresh(obj)
       return obj
   ```

4. **Service** (`services/<entity>_service.py`): constructor takes the abstract repository; methods
   express use cases and translate schemas → repo calls (e.g. hash the password, build a partial
   update dict skipping `None` fields). Import the abstract repo under `TYPE_CHECKING`.

5. **DI wiring** (`core/dependencies/<entity>.py`): two chained providers —
   `get_<entity>_repository(session=Depends(get_session))` returns the **concrete** repo, and
   `get_<entity>_service(repository=Depends(get_<entity>_repository))` returns the service.

6. **Router** (`routers/<entity>s.py`): `router = APIRouter(prefix="/<entity>s", tags=["<entity>s"])`.
   Endpoints depend on the service, take/return schemas, set explicit status codes (`201` create,
   `204` delete). Convert with `Response.model_validate(...)`. Then register it in `main.py`:
   `app.include_router(<entity>s.router)`.

7. **Migration**: `poe migrate m="add <entity>"` (autogenerate) → review the script → `poe upgrade`.

8. **Tests**: unit-test the service with a mocked repo; integration-test the repository and the
   router (see Testing).

## Migrations (Alembic, async)

- `alembic/env.py` imports `Base` (for `target_metadata`) and pulls the URL from `Settings` (so one
  source of truth), escaping `%` as `%%`. It runs migrations through an async engine.
- `Base.metadata` must see every model — ensure new models are imported (transitively) so
  autogenerate detects them.
- Poe tasks: `poe migrate m="msg"` (autogenerate revision), `poe upgrade` (→ head), `poe downgrade`
  (-1), `poe history`. Always **review** autogenerated scripts before applying.
- In production, `startup.py` runs `command.upgrade(cfg, "head")` **before** starting uvicorn, so a
  container comes up migrated. It uses the Alembic Python API (distroless has no shell).

## poe tasks (from `pyproject.toml`)

`poe startup` (migrate + serve via `startup.py`), `poe test` (`pytest tests -v`), `poe format`
(`ruff format`), `poe ty` (`ty check`), `poe migrate`/`upgrade`/`downgrade`/`history`. Optional-deps
groups: **dev** (pytest, ruff, httpx, aiosqlite, poe) and **prod** (httptools, asyncpg). Install with
`uv sync --extra dev`.

## Testing

- **pytest-asyncio in `auto` mode** — no per-test decorator needed (the template still marks some).
- **In-memory SQLite** engine per test (`sqlite+aiosqlite:///:memory:`, `StaticPool`,
  `check_same_thread=False`); `conftest.py` creates all tables from `Base.metadata` before and
  drops after each test — full isolation, no migrations in tests.
- **Override DI, don't monkeypatch.** The `test_app` fixture sets `app.dependency_overrides` for
  `get_settings` and `get_session` and points `app.state.db_engine` at the test engine, then clears
  overrides on teardown. HTTP tests use an `httpx.AsyncClient` over `ASGITransport(app=test_app)`.
- **Test each layer at its level:** services with an `AsyncMock` repository (`unit/`, AAA pattern,
  no DB); repositories against real in-memory SQLite (`integration/test_repositories/`); routers
  end-to-end through the async client (`integration/test_routers/`).
- **Auto-markers:** `conftest.py`'s `pytest_collection_modifyitems` marks tests `unit`/
  `integration`/`e2e`/`db` by path. Coverage config lives in `tests/pytest.ini` +`.coveragerc`
  (source = `src`, omits migrations/tests/`main.py`, `--cov-fail-under=80`).
- Run with `poe test` or `uv run pytest tests`.

## Docker & deployment

- **Multi-stage, distroless.** Stage 1: `python:3.13-slim` + `uv sync --frozen --no-dev
  --no-install-project --extra prod` (cached). Stage 2: `gcr.io/distroless/cc-debian13:nonroot` —
  copy Python + the `.venv` + `src/` + `alembic/` + `startup.py`, run as `nonroot` (uid 65532),
  `EXPOSE 8000`, entrypoint `python startup.py`.
- **`.dockerignore`** excludes `.venv`, caches, `tests/`, `.env*`, `*.md`.
- **`docker-compose.yml`** (repo root) wires `postgres:17-alpine` (with a `pg_isready`
  healthcheck), the backend (`depends_on` postgres `service_healthy`, `env_file: .env.docker`), and
  the frontend. Backend on `8000`.
- **Prod uvicorn** (in `startup.py`): `http="httptools"`, `proxy_headers=True`,
  `forwarded_allow_ips="*"`, single worker. Dev uses `reload=True` via `python -m src.main`.

## CI (GitHub Actions)

Three jobs, all `working-directory: backend`, using `astral-sh/setup-uv`: **ruff** (`ruff check .
--output-format=sarif`), **ty** (`uv sync --extra dev` then `uvx ty check .`), **tests** (`uv sync
--extra dev` then `uv run pytest tests`). Keep all three green before merging.

## Before you write code

1. Read the `User` slice end-to-end (`db/models/user.py` → `schemas/user.py` →
   `repositories/*user*` → `services/user_service.py` → `core/dependencies/user.py` →
   `routers/users.py`) and copy its shape for the new entity.
2. Decide the layer for any new code **first**; put it there, respect downward-only calls.
3. Match the neighbouring module's conventions: `from __future__ import annotations`,
   `TYPE_CHECKING` imports, `__all__`, full type hints, async.
4. After changes, run `poe format`, `poe ty`, and `poe test` — confirm real output before claiming
   it passes.
