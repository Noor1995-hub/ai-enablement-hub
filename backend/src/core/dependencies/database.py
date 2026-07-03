from __future__ import annotations

from typing import TYPE_CHECKING

# Types used in FastAPI-inspected parameter annotations must be imported at
# runtime: with deferred annotations, FastAPI evaluates the strings against
# module globals, and an unresolvable name silently degrades the parameter to
# a required query param (breaking the endpoint with 422s).
from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

__all__ = ["get_session"]


async def get_session(request: Request) -> AsyncGenerator[AsyncSession]:
    """Yield one AsyncSession per request from the lifespan-owned engine.

    expire_on_commit=False: multi-step use cases (e.g. set-password) keep using
    ORM objects after intermediate commits; expiring them would trigger implicit
    async lazy-loads (MissingGreenlet). Repositories refresh explicitly where
    server-generated values matter.
    """
    async with AsyncSession(request.app.state.db_engine, expire_on_commit=False) as session:
        yield session
