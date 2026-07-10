from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from pydantic import SecretStr
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
    # email=None/storage=None explicitly: keeps tests hermetic (and away from
    # real ACS/Blob Storage) even once the developer's backend/.env carries
    # EMAIL__*/STORAGE__* values.
    return Settings(
        auth=AuthSettings(jwt_secret=SecretStr("integration-test-jwt-secret-0123456789")),
        email=None,
        storage=None,
    )


@pytest_asyncio.fixture(scope="session")
async def engine() -> AsyncGenerator[AsyncEngine]:
    engine = create_async_engine(_test_database_url(), poolclass=NullPool)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield engine
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
