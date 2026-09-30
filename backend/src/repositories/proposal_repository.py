from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import Select, func, select

from src.db.models import Lesson, LessonContentProposal, Module, Track
from src.repositories.base import AbstractProposalRepository

__all__ = ["ProposalRepository"]

# Statuses whose source feedback counts as already incorporated. `rejected`
# and `superseded` are deliberately absent — their feedback becomes eligible
# for a future run again (design doc, "Applying an approved proposal").
_COVERING_STATUSES = ("pending", "approved", "failed")


class ProposalRepository(AbstractProposalRepository):
    async def create(
        self,
        *,
        lesson_id: uuid.UUID,
        proposed_blocks: list[Any],
        base_blocks: list[Any],
        source_feedback_ids: list[uuid.UUID],
        summary: str,
        status: str = "pending",
    ) -> LessonContentProposal:
        proposal = LessonContentProposal(
            lesson_id=lesson_id,
            proposed_blocks=proposed_blocks,
            base_blocks=base_blocks,
            source_feedback_ids=[str(feedback_id) for feedback_id in source_feedback_ids],
            summary=summary,
            status=status,
        )
        self._session.add(proposal)
        await self._session.commit()
        await self._session.refresh(proposal)
        return proposal

    async def get_by_id(self, proposal_id: uuid.UUID) -> LessonContentProposal | None:
        result = await self._session.execute(
            select(LessonContentProposal).where(LessonContentProposal.id == proposal_id)
        )
        return result.scalar_one_or_none()

    async def covered_feedback_ids(self) -> set[uuid.UUID]:
        query = select(LessonContentProposal.source_feedback_ids).where(
            LessonContentProposal.status.in_(_COVERING_STATUSES)
        )
        covered: set[uuid.UUID] = set()
        for (ids,) in (await self._session.execute(query)).all():
            if not isinstance(ids, list):
                continue
            for raw in ids:
                try:
                    covered.add(uuid.UUID(str(raw)))
                except ValueError:
                    # A non-uuid in the JSONB array can only be corrupt data;
                    # skipping it is safer than failing every future run.
                    continue
        return covered

    def _admin_query(self, status: str | None) -> Select[Any]:
        query = (
            select(
                LessonContentProposal,
                Lesson.title.label("lesson_title"),
                Module.title.label("module_title"),
                Track.id.label("track_id"),
                Track.name.label("track_name"),
                Track.required_level.label("track_level"),
            )
            .join(Lesson, Lesson.id == LessonContentProposal.lesson_id)
            .join(Module, Module.id == Lesson.module_id)
            .join(Track, Track.id == Module.track_id)
        )
        if status is not None:
            query = query.where(LessonContentProposal.status == status)
        return query

    async def list_admin(self, *, status: str | None = None, limit: int, offset: int) -> list[Any]:
        query = (
            self._admin_query(status)
            .order_by(LessonContentProposal.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list((await self._session.execute(query)).all())

    async def count_admin(self, *, status: str | None = None) -> int:
        query = select(func.count()).select_from(self._admin_query(status).subquery())
        return int((await self._session.execute(query)).scalar_one())

    async def set_status(
        self, proposal: LessonContentProposal, status: str, reviewed_by: uuid.UUID | None
    ) -> None:
        proposal.status = status
        proposal.reviewed_by = reviewed_by
        proposal.reviewed_at = None if reviewed_by is None else datetime.now(UTC)
        await self._session.commit()

    async def stage_approved(
        self,
        proposal: LessonContentProposal,
        *,
        edited_blocks: list[Any] | None,
        reviewed_by: uuid.UUID,
    ) -> None:
        proposal.status = "approved"
        proposal.edited_blocks = edited_blocks
        proposal.reviewed_by = reviewed_by
        proposal.reviewed_at = datetime.now(UTC)
        await self._session.flush()

    async def set_approved(
        self,
        proposal: LessonContentProposal,
        *,
        edited_blocks: list[Any] | None,
        reviewed_by: uuid.UUID,
    ) -> None:
        await self.stage_approved(proposal, edited_blocks=edited_blocks, reviewed_by=reviewed_by)
        await self._session.commit()

    async def set_critique(
        self, proposal: LessonContentProposal, *, agent_wrong: str, admin_preferred: str
    ) -> None:
        proposal.critique_agent_wrong = agent_wrong
        proposal.critique_admin_preferred = admin_preferred
        proposal.critiqued_at = datetime.now(UTC)
        await self._session.commit()
