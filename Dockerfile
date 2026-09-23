# Single-container image: FastAPI serves the API under /api/* and the built
# React SPA for everything else (see the SPA block in backend/src/main.py).
# Built by the Deploy workflow (.github/workflows/deploy.yml, docker build on the runner) or,
# break-glass, by infra/deploy-legacy.ps1 via az acr build — classic syntax only,
# no BuildKit-specific features.

# ---------- Stage 1: frontend build ----------
FROM node:22-alpine AS frontend-build
WORKDIR /fe
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
# "build" = tsc -b && vite build -> /fe/dist
RUN npm run build

# ---------- Stage 2: backend deps ----------
# Same Debian/Python base family as the runtime stage so the venv transplants cleanly.
FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim AS backend-deps
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never
WORKDIR /app
COPY backend/pyproject.toml backend/uv.lock ./
# --no-install-project: never build/install the app itself (hatchling never runs);
# startup.py resolves `src` from the working directory and alembic.ini has
# prepend_sys_path=. so the source tree on disk is all that's needed.
RUN uv sync --frozen --no-dev --no-install-project --extra prod

# ---------- Stage 3: runtime ----------
FROM python:3.13-slim-bookworm
WORKDIR /app
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1
RUN useradd --create-home --uid 1000 appuser
COPY --from=backend-deps --chown=appuser:appuser /app/.venv /app/.venv
COPY --chown=appuser:appuser backend/src ./src
# Runtime-loaded system prompts (services/prompts.py reads /app/prompts/<kind>.md).
# Also un-ignored in .dockerignore, which otherwise drops all *.md from the context.
COPY --chown=appuser:appuser backend/prompts ./prompts
COPY --chown=appuser:appuser backend/alembic ./alembic
COPY --chown=appuser:appuser backend/alembic.ini backend/startup.py backend/migrate.py ./
COPY --from=frontend-build --chown=appuser:appuser /fe/dist ./static
USER appuser
EXPOSE 8000
# uvicorn on 0.0.0.0:8000 (backend/startup.py). Migrations run in the migrate job (backend/migrate.py).
CMD ["python", "startup.py"]
