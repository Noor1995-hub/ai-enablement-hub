from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from pydantic import SecretStr
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from src.core.configs.auth import AuthSettings
from src.core.configs.settings import Settings
from src.core.dependencies.database import get_session
from src.core.dependencies.settings import get_settings
from src.core.ratelimit import rate_limiter
from src.db.base import Base
from src.main import app
from src.repositories.auth_session_repository import AuthSessionRepository
from src.repositories.auth_token_repository import AuthTokenRepository
from src.repositories.user_repository import UserRepository
from src.services.token_service import TokenService

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator, Generator

    from sqlalchemy.engine import URL
    from sqlalchemy.ext.asyncio import AsyncEngine

# Integration tests run against a real PostgreSQL database (approved deviation
# from the in-memory-SQLite template default: the schema uses text[]/JSONB/
# ON CONFLICT). The connection is derived from ALEMBIC_DATABASE_URL (the
# ai_hub_owner role, which may run DDL) with the database swapped to the
# dedicated test DB.
TEST_DB_NAME = "ai-enablement-hub-test"
_ENV_FILE = Path(__file__).resolve().parent.parent / ".env"


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    for item in items:
        path = str(item.fspath)
        if f"{os.sep}unit{os.sep}" in path:
            item.add_marker(pytest.mark.unit)
        elif f"{os.sep}integration{os.sep}" in path:
            item.add_marker(pytest.mark.integration)
            # Integration tests hit a real remote Postgres; retry once on a
            # transient blip instead of forcing a manual re-run/diagnosis.
            # Unit tests are pure/mocked, so a failure there is never
            # transient and shouldn't be retried.
            item.add_marker(pytest.mark.flaky(reruns=1, reruns_delay=1))


def pytest_xdist_auto_num_workers(config: pytest.Config) -> int:
    """`-n auto` otherwise claims every logical core with no headroom, which
    leaves no room for OS/background activity — plausibly what caused a
    one-off pile of transient DB-setup errors under full-core parallel load.
    Leaving 2 cores free keeps most of the parallel speedup (measured: ~14
    workers ≈ 100s, 4 workers ≈ 210s for the full suite) while giving the
    box some slack."""
    return max(1, (os.cpu_count() or 2) - 2)


def _test_database_url() -> URL:
    url = os.environ.get("ALEMBIC_DATABASE_URL")
    if not url and _ENV_FILE.exists():
        for line in _ENV_FILE.read_text(encoding="utf-8").splitlines():
            if line.strip().startswith("ALEMBIC_DATABASE_URL="):
                url = line.partition("=")[2].strip()
                break
    if not url:
        msg = "ALEMBIC_DATABASE_URL is required to run integration tests (see .env.local.example)"
        raise RuntimeError(msg)
    test_url = make_url(url).set(database=TEST_DB_NAME)
    # Hard guard: never point destructive test setup at a non-test database.
    assert test_url.database is not None and test_url.database.endswith("-test")
    return test_url


@pytest.fixture(autouse=True)
def _reset_rate_limiter() -> Generator[None]:
    """The limiter is a process-global; isolate its counters per test."""
    rate_limiter.reset()
    yield
    rate_limiter.reset()


@pytest.fixture(scope="session")
def test_settings() -> Settings:
    # email=None/storage=None/llm=None explicitly: keeps tests hermetic (and away
    # from real ACS/Blob/Anthropic calls) even once the developer's backend/.env
    # carries EMAIL__*/STORAGE__*/LLM__* values.
    return Settings(
        auth=AuthSettings(jwt_secret=SecretStr("integration-test-jwt-secret-0123456789")),
        email=None,
        storage=None,
        llm=None,
    )


@pytest_asyncio.fixture(scope="session")
async def engine(worker_id: str) -> AsyncGenerator[AsyncEngine]:
    """Pooled (not NullPool) so tests in this worker reuse physical connections
    instead of paying a fresh TCP/TLS handshake to Azure per test. Under
    pytest-xdist each worker process runs this fixture independently against
    the SAME remote database, so every worker but "master" (i.e. running under
    -n) gets its own Postgres schema — otherwise two workers' drop_all/
    create_all would race on the same tables mid-run."""
    schema = "public" if worker_id == "master" else f"test_{worker_id}"
    url = _test_database_url()
    if schema != "public":
        # Create the schema on a throwaway connection BEFORE the real engine
        # (whose search_path already points at it) opens its first connection.
        # SQLAlchemy probes current_schema() once per engine and caches it; if
        # that probe ran first, Postgres would find the schema missing and
        # silently fall back to "public" for search_path resolution, so the
        # dialect would cache "public" as the default — then create_all's
        # existence-check would see this worker's tables already in "public"
        # (left over from a prior serial/master run) and skip creating them
        # here, leaving this worker's schema empty. Bootstrapping the schema
        # first closes that race.
        bootstrap_engine = create_async_engine(url, poolclass=NullPool)
        async with bootstrap_engine.begin() as conn:
            await conn.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{schema}"'))
        await bootstrap_engine.dispose()
    engine = create_async_engine(
        url,
        connect_args={"server_settings": {"search_path": f'"{schema}",public'}},
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    if schema != "public":
        async with engine.begin() as conn:
            await conn.execute(text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(engine: AsyncEngine) -> AsyncGenerator[AsyncSession]:
    """One outer transaction per test, rolled back at the end. Application-level
    session.commit() only releases savepoints (join_transaction_mode), so every
    test leaves the database untouched."""
    async with engine.connect() as conn:
        outer = await conn.begin()
        session = AsyncSession(
            bind=conn, join_transaction_mode="create_savepoint", expire_on_commit=False
        )
        try:
            yield session
        finally:
            await session.close()
            await outer.rollback()


@pytest_asyncio.fixture
async def client(db_session: AsyncSession, test_settings: Settings) -> AsyncGenerator[AsyncClient]:
    async def _override_session() -> AsyncGenerator[AsyncSession]:
        yield db_session

    app.dependency_overrides[get_session] = _override_session
    app.dependency_overrides[get_settings] = lambda: test_settings
    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            yield client
    finally:
        app.dependency_overrides.clear()


@pytest.fixture
def token_service(db_session: AsyncSession, test_settings: Settings) -> TokenService:
    """Service wired to the test session — used to issue invite/reset tokens
    until the Batch 3 admin endpoints exist."""
    return TokenService(
        UserRepository(db_session),
        AuthTokenRepository(db_session),
        AuthSessionRepository(db_session),
        test_settings.auth,
    )
