from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy.ext.asyncio import AsyncSession

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from fastapi import Request

__all__ = ["get_session"]


async def get_session(request: Request) -> AsyncGenerator[AsyncSession]:
    """Yield one AsyncSession per request from the lifespan-owned engine."""
    async with AsyncSession(request.app.state.db_engine) as session:
        yield session
