from __future__ import annotations

from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

from fastapi import FastAPI
from sqlalchemy.ext.asyncio import create_async_engine

from src.core.configs.database import DatabaseProtocol
from src.core.dependencies.settings import get_settings

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

__all__ = ["app"]


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    settings = get_settings()
    kwargs: dict = {
        "url": settings.database.url.get_secret_value(),
        "hide_parameters": True,
    }
    if settings.database.protocol is DatabaseProtocol.POSTGRESQL:
        kwargs.update(
            pool_size=settings.database.pool_size,
            max_overflow=settings.database.max_overflow,
            pool_pre_ping=True,
        )
    engine = create_async_engine(**kwargs)
    app.state.db_engine = engine
    yield
    await engine.dispose()


app = FastAPI(title="AI Enablement Hub API", lifespan=lifespan)


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("src.main:app", host="127.0.0.1", port=8000, reload=True)
