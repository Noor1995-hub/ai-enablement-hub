from __future__ import annotations

import uuid

from sqlalchemy import delete as sa_delete
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models.prompt import Prompt

__all__ = ["PromptRepository"]


class PromptRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_all(self) -> list[Prompt]:
        result = await self._session.execute(select(Prompt))
        return list(result.scalars().all())

    async def get(self, kind: str) -> Prompt | None:
        return await self._session.get(Prompt, kind)

    async def upsert(self, kind: str, content: str, updated_by: uuid.UUID | None) -> None:
        stmt = pg_insert(Prompt).values(kind=kind, content=content, updated_by=updated_by)
        stmt = stmt.on_conflict_do_update(
            index_elements=[Prompt.kind],
            set_={
                "content": stmt.excluded.content,
                "updated_by": stmt.excluded.updated_by,
                "updated_at": func.now(),
            },
        )
        await self._session.execute(stmt)
        await self._session.commit()

    async def delete(self, kind: str) -> None:
        await self._session.execute(sa_delete(Prompt).where(Prompt.kind == kind))
        await self._session.commit()
