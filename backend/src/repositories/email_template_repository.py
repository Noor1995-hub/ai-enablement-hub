from __future__ import annotations

import uuid

from sqlalchemy import delete as sa_delete
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from src.db.models import ProjectEmailTemplate
from src.repositories.base import AbstractEmailTemplateRepository

__all__ = ["EmailTemplateRepository"]


class EmailTemplateRepository(AbstractEmailTemplateRepository):
    async def get(self, project_id: uuid.UUID, purpose: str) -> ProjectEmailTemplate | None:
        result = await self._session.execute(
            select(ProjectEmailTemplate).where(
                ProjectEmailTemplate.project_id == project_id,
                ProjectEmailTemplate.purpose == purpose,
            )
        )
        return result.scalar_one_or_none()

    async def list_for_project(self, project_id: uuid.UUID) -> list[ProjectEmailTemplate]:
        result = await self._session.execute(
            select(ProjectEmailTemplate).where(ProjectEmailTemplate.project_id == project_id)
        )
        return list(result.scalars().all())

    async def upsert(
        self, project_id: uuid.UUID, purpose: str, *, subject: str, body_markdown: str
    ) -> None:
        stmt = pg_insert(ProjectEmailTemplate).values(
            project_id=project_id, purpose=purpose, subject=subject, body_markdown=body_markdown
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=["project_id", "purpose"],
            set_={
                "subject": stmt.excluded.subject,
                "body_markdown": stmt.excluded.body_markdown,
                "updated_at": func.now(),
            },
        )
        await self._session.execute(stmt)
        await self._session.commit()

    async def delete(self, project_id: uuid.UUID, purpose: str) -> None:
        await self._session.execute(
            sa_delete(ProjectEmailTemplate).where(
                ProjectEmailTemplate.project_id == project_id,
                ProjectEmailTemplate.purpose == purpose,
            )
        )
        await self._session.commit()
