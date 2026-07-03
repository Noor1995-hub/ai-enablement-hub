from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager, suppress
from typing import TYPE_CHECKING

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from starlette.exceptions import HTTPException as StarletteHTTPException

from src.core.configs.database import DatabaseProtocol
from src.core.dependencies.settings import get_settings
from src.repositories.auth_session_repository import AuthSessionRepository
from src.repositories.auth_token_repository import AuthTokenRepository
from src.repositories.user_repository import UserRepository
from src.routers import admin_content, admin_org, admin_users, auth, learning, me, survey
from src.services.exceptions import ConflictError, DomainError, NotFoundError
from src.services.scoring import ScoringError
from src.services.token_service import TokenService

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator, Mapping

    from sqlalchemy.ext.asyncio import AsyncEngine

    from src.core.configs.auth import AuthSettings

__all__ = ["app"]

logger = logging.getLogger(__name__)

_CLEANUP_INTERVAL_SECONDS = 24 * 60 * 60


async def _auth_cleanup_loop(engine: AsyncEngine, auth_settings: AuthSettings) -> None:
    """Daily purge of expired invite/reset tokens and dead sessions (fixes DB2).

    Runs once at startup, then every 24 h. No pg_cron dependency.
    """
    while True:
        try:
            async with AsyncSession(engine, expire_on_commit=False) as session:
                token_service = TokenService(
                    UserRepository(session),
                    AuthTokenRepository(session),
                    AuthSessionRepository(session),
                    auth_settings,
                )
                tokens_deleted, sessions_deleted = await token_service.purge_expired()
            logger.info(
                "auth cleanup: deleted %d expired tokens, %d dead sessions",
                tokens_deleted,
                sessions_deleted,
            )
        except Exception:
            logger.exception("auth cleanup failed; retrying next interval")
        await asyncio.sleep(_CLEANUP_INTERVAL_SECONDS)


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
    cleanup_task = asyncio.create_task(_auth_cleanup_loop(engine, settings.auth))
    yield
    cleanup_task.cancel()
    with suppress(asyncio.CancelledError):
        await cleanup_task
    await engine.dispose()


app = FastAPI(title="AI Enablement Hub API", lifespan=lifespan)

# Bearer-token API, no cookies — hence no allow_credentials.
_app_settings = get_settings().app
app.add_middleware(
    CORSMiddleware,
    allow_origins=_app_settings.cors_origins,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
    max_age=86400,
)

app.include_router(auth.router)
app.include_router(me.router)
app.include_router(survey.router)
app.include_router(learning.router)
app.include_router(admin_org.router)
app.include_router(admin_users.router)
app.include_router(admin_content.router)

# Single error shape for the frontend: {"error": {"code", "message"[, "fields"]}}
_ERROR_CODES = {
    400: "bad_request",
    401: "unauthorized",
    403: "forbidden",
    404: "not_found",
    409: "conflict",
    410: "gone",
    422: "validation_error",
    429: "rate_limited",
}


def _error_response(
    status_code: int, message: str, headers: Mapping[str, str] | None = None
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": _ERROR_CODES.get(status_code, "http_error"),
                "message": message,
            }
        },
        headers=headers,
    )


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    return _error_response(exc.status_code, str(exc.detail), exc.headers)


@app.exception_handler(NotFoundError)
async def not_found_handler(request: Request, exc: NotFoundError) -> JSONResponse:
    return _error_response(404, exc.message)


@app.exception_handler(ConflictError)
async def conflict_handler(request: Request, exc: ConflictError) -> JSONResponse:
    return _error_response(409, exc.message)


@app.exception_handler(DomainError)
async def domain_error_handler(request: Request, exc: DomainError) -> JSONResponse:
    return _error_response(400, exc.message)


@app.exception_handler(ScoringError)
async def scoring_error_handler(request: Request, exc: ScoringError) -> JSONResponse:
    return _error_response(422, exc.message)


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
