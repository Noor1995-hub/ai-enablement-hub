from __future__ import annotations

from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import create_async_engine
from starlette.exceptions import HTTPException as StarletteHTTPException

from src.core.configs.database import DatabaseProtocol
from src.core.dependencies.settings import get_settings
from src.routers import auth

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

app.include_router(auth.router)

# Single error shape for the frontend: {"error": {"code", "message"[, "fields"]}}
_ERROR_CODES = {
    400: "bad_request",
    401: "unauthorized",
    403: "forbidden",
    404: "not_found",
    409: "conflict",
    410: "gone",
    429: "rate_limited",
}


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": _ERROR_CODES.get(exc.status_code, "http_error"),
                "message": str(exc.detail),
            }
        },
        headers=exc.headers,
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    fields = [
        {
            "field": ".".join(str(loc) for loc in error["loc"][1:]) or str(error["loc"][0]),
            "message": error["msg"],
        }
        for error in exc.errors()
    ]
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": "validation_error",
                "message": "Request validation failed",
                "fields": fields,
            }
        },
    )


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("src.main:app", host="127.0.0.1", port=8000, reload=True)
