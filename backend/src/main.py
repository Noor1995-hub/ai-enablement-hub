from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager, suppress
from pathlib import Path
from typing import TYPE_CHECKING, Annotated

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import RequestResponseEndpoint

from src.core.configs.database import DatabaseProtocol
from src.core.configs.settings import Settings
from src.core.dependencies.settings import get_settings
from src.repositories.auth_session_repository import AuthSessionRepository
from src.repositories.auth_token_repository import AuthTokenRepository
from src.repositories.prompt_repository import PromptRepository
from src.repositories.user_repository import UserRepository
from src.routers import (
    admin_calibration_notes,
    admin_content,
    admin_content_improvement,
    admin_dashboard,
    admin_defaults,
    admin_email_templates,
    admin_feedback,
    admin_media,
    admin_org,
    admin_prompts,
    admin_users,
    auth,
    auth_entra,
    chat,
    feedback,
    interview,
    learning,
    me,
    survey,
)
from src.schemas.health import HealthOut
from src.services.exceptions import (
    AiGenerationError,
    ComponentLockedError,
    ConflictError,
    DomainError,
    NotFoundError,
    PayloadTooLargeError,
    UnsupportedMediaTypeError,
)
from src.services.prompt_service import PromptService
from src.services.scoring import ScoringError
from src.services.token_service import TokenService

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator, Mapping

    from sqlalchemy.ext.asyncio import AsyncEngine

    from src.core.configs.auth import AuthSettings
    from src.core.configs.storage import StorageSettings

__all__ = ["app"]

logger = logging.getLogger(__name__)

_LOG_FORMAT = "%(levelname)-5.5s [%(name)s] %(message)s"


def _configure_logging() -> None:
    """Make the app's own INFO logs reachable (audit lines like bulk-invite outcomes).

    In the container, `startup.py` runs Alembic before uvicorn *in the same
    process*, and Alembic's `fileConfig()` applies `alembic.ini`'s logging block
    — which pins the ROOT logger at WARNING. That silently swallowed every
    `logger.info()` under `src/`, including the bulk-invite audit line, while
    letting ERROR through: an invite batch could half-fail with no trace of the
    summary. Found 2026-08-17 while reconstructing one such batch from logs.

    Set the level on our own package logger rather than root, so library loggers
    (sqlalchemy, asyncpg, azure.*) keep their WARNING floor instead of flooding
    Log Analytics. Records still reach root's handler by propagation — handler
    levels are NOTSET, and an ancestor logger's level does not gate propagated
    records. The handler is only added when nothing else installed one (dev,
    where uvicorn runs without the Alembic step).
    """
    logging.getLogger("src").setLevel(logging.INFO)
    if not logging.getLogger().handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter(_LOG_FORMAT))
        logging.getLogger("src").addHandler(handler)


_configure_logging()

_CLEANUP_INTERVAL_SECONDS = 24 * 60 * 60

# Vite build output; only exists in the container image (the Dockerfile copies
# frontend/dist here). Absent in dev, so the SPA block at the bottom is a no-op locally.
_STATIC_DIR = (Path(__file__).resolve().parents[1] / "static").resolve()


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
    async with AsyncSession(engine, expire_on_commit=False) as session:
        await PromptService(PromptRepository(session)).refresh_cache()
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


# Ported from the old app's vercel.json headers. style-src needs 'unsafe-inline'
# (framer-motion inline styles) and fonts.googleapis.com (index.css @imports it).
# img-src/media-src additionally allow the lesson-media blob endpoint once
# storage is configured. frame-src is always present (embeds don't need
# storage) — the sharepoint host is broad on purpose; tighten it to the
# delaware tenant host once a real Stream embed URL confirms it.
def _build_csp(storage: StorageSettings | None) -> str:
    blob_endpoint = f" {storage.blob_endpoint}" if storage is not None else ""
    return (
        "default-src 'self'; script-src 'self'; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com; "
        f"img-src 'self' data:{blob_endpoint}; connect-src 'self'; frame-ancestors 'none'; "
        f"media-src 'self'{blob_endpoint}; "
        "frame-src https://www.youtube-nocookie.com https://player.vimeo.com "
        "https://*.sharepoint.com"
    )


@app.middleware("http")
async def security_headers(request: Request, call_next: RequestResponseEndpoint) -> Response:
    response = await call_next(request)
    h = response.headers
    h["X-Content-Type-Options"] = "nosniff"
    h["X-Frame-Options"] = "DENY"
    h["Referrer-Policy"] = "strict-origin-when-cross-origin"
    h["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains; preload"
    h["Permissions-Policy"] = "camera=(), microphone=(), geolocation=(), payment=()"
    path = request.url.path
    # Swagger UI at /docs loads its JS/CSS from cdn.jsdelivr.net — exempt it.
    if not path.startswith(("/docs", "/redoc")):
        # Resolved the same way FastAPI's dependency injection would (honoring
        # dependency_overrides), so tests can swap settings without an app
        # factory/reimport — plain middleware doesn't go through Depends().
        settings = request.app.dependency_overrides.get(get_settings, get_settings)()
        h["Content-Security-Policy"] = _build_csp(settings.storage)
    if path.startswith("/assets/"):
        # Files directly under /assets/ are Vite hash-named bundles; subdirs
        # (icons/, images/, logo/) come from public/ un-hashed and must NOT
        # be cached as immutable.
        if "/" not in path.removeprefix("/assets/"):
            h["Cache-Control"] = "public, max-age=31536000, immutable"
        else:
            h["Cache-Control"] = "public, max-age=3600"
    return response


app.include_router(auth.router)
app.include_router(auth_entra.router)
app.include_router(me.router)
app.include_router(survey.router)
app.include_router(learning.router)
app.include_router(admin_org.router)
app.include_router(admin_users.router)
app.include_router(admin_email_templates.router)
app.include_router(admin_prompts.router)
app.include_router(admin_content.router)
app.include_router(admin_media.router)
app.include_router(chat.router)
app.include_router(interview.router)
app.include_router(interview.admin_router)
app.include_router(admin_defaults.router)
app.include_router(admin_feedback.router)
app.include_router(admin_content_improvement.router)
app.include_router(admin_calibration_notes.router)
app.include_router(admin_dashboard.router)
app.include_router(feedback.router)

# Single error shape for the frontend: {"error": {"code", "message"[, "fields"]}}
_ERROR_CODES = {
    400: "bad_request",
    401: "unauthorized",
    403: "forbidden",
    404: "not_found",
    409: "conflict",
    410: "gone",
    413: "payload_too_large",
    415: "unsupported_media_type",
    422: "validation_error",
    429: "rate_limited",
    502: "bad_gateway",
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


@app.exception_handler(ComponentLockedError)
async def component_locked_handler(request: Request, exc: ComponentLockedError) -> JSONResponse:
    return _error_response(403, exc.message)


@app.exception_handler(DomainError)
async def domain_error_handler(request: Request, exc: DomainError) -> JSONResponse:
    return _error_response(400, exc.message)


@app.exception_handler(AiGenerationError)
async def ai_generation_error_handler(request: Request, exc: AiGenerationError) -> JSONResponse:
    return _error_response(502, exc.message)


@app.exception_handler(ScoringError)
async def scoring_error_handler(request: Request, exc: ScoringError) -> JSONResponse:
    return _error_response(422, exc.message)


@app.exception_handler(UnsupportedMediaTypeError)
async def unsupported_media_type_handler(
    request: Request, exc: UnsupportedMediaTypeError
) -> JSONResponse:
    return _error_response(415, exc.message)


@app.exception_handler(PayloadTooLargeError)
async def payload_too_large_handler(request: Request, exc: PayloadTooLargeError) -> JSONResponse:
    return _error_response(413, exc.message)


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


@app.get("/api/health", response_model=HealthOut)
async def health(settings: Annotated[Settings, Depends(get_settings)]) -> HealthOut:
    return HealthOut(
        status="ok", build_sha=settings.app.build_sha, build_time=settings.app.build_time
    )


# --- SPA serving (container only) -------------------------------------------
# Registered last so every explicit route above (routers, /docs, /openapi.json)
# wins over the catch-all.
if (_STATIC_DIR / "index.html").is_file():
    app.mount("/assets", StaticFiles(directory=_STATIC_DIR / "assets"), name="assets")

    # api_route with explicit HEAD: link-preview bots probe with HEAD, and
    # FastAPI's @app.get does not add HEAD automatically (FileResponse handles it).
    @app.api_route("/{full_path:path}", methods=["GET", "HEAD"], include_in_schema=False)
    async def spa(full_path: str) -> FileResponse:
        # Unknown /api/* paths must 404 as JSON, never fall back to index.html.
        if full_path.split("/", 1)[0] == "api":
            raise HTTPException(status_code=404, detail="Not Found")
        candidate = (_STATIC_DIR / full_path).resolve()
        if candidate.is_relative_to(_STATIC_DIR) and candidate.is_file():
            return FileResponse(candidate, headers={"Cache-Control": "public, max-age=3600"})
        # Missing file-looking paths (e.g. /favicon.ico) -> 404, not index.html.
        if "." in full_path.rsplit("/", 1)[-1]:
            raise HTTPException(status_code=404, detail="Not Found")
        return FileResponse(_STATIC_DIR / "index.html", headers={"Cache-Control": "no-cache"})


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("src.main:app", host="127.0.0.1", port=8000, reload=True)
