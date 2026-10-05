# backend/src/repositories/conversation_repository.py
from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import delete, select, text, update
from sqlalchemy.dialects.postgresql import insert as pg_insert

from src.db.models import Conversation
from src.repositories.base import AbstractConversationRepository

__all__ = ["ConversationRepository"]


class ConversationRepository(AbstractConversationRepository):
    async def create(
        self, *, user_id: uuid.UUID, kind: str, context_ref: str | None = None
    ) -> Conversation:
        # created_at/updated_at are set here (rather than left to the columns'
        # server-side `now()` default) because `now()` is fixed at transaction
        # start: two conversations created back-to-back within the same
        # transaction — as every request handler's unit-of-work is, and as
        # every test's savepoint-wrapped session is — would otherwise get an
        # identical timestamp and break chronological ordering.
        now = datetime.now(UTC)
        conversation = Conversation(
            user_id=user_id,
            kind=kind,
            context_ref=context_ref,
            created_at=now,
            updated_at=now,
        )
        self._session.add(conversation)
        await self._session.commit()
        await self._session.refresh(conversation)
        return conversation

    async def create_interview_if_absent(
        self, user_id: uuid.UUID, *, language: str | None = None
    ) -> Conversation | None:
        # ON CONFLICT DO NOTHING against the partial unique index
        # uq_conversations_interview_user_id (the index_where must match its
        # predicate for Postgres to infer it as the arbiter). The loser of a
        # concurrent insert gets no row back instead of an IntegrityError, so the
        # session never enters the failed-flush state. Timestamps set here for the
        # same reason as in create().
        now = datetime.now(UTC)
        result = await self._session.execute(
            pg_insert(Conversation)
            .values(
                user_id=user_id,
                kind="interview",
                language=language,
                created_at=now,
                updated_at=now,
            )
            .on_conflict_do_nothing(
                index_elements=["user_id"], index_where=text("kind = 'interview'")
            )
            .returning(Conversation.id)
        )
        conversation_id = result.scalar_one_or_none()
        await self._session.commit()
        if conversation_id is None:
            return None
        return await self.get_by_id(conversation_id)

    async def get_by_id(self, conversation_id: uuid.UUID) -> Conversation | None:
        result = await self._session.execute(
            select(Conversation).where(Conversation.id == conversation_id)
        )
        return result.scalar_one_or_none()

    async def list_for_user(
        self, user_id: uuid.UUID, kind: str, *, limit: int | None = None
    ) -> list[Conversation]:
        query = (
            select(Conversation)
            .where(Conversation.user_id == user_id, Conversation.kind == kind)
            .order_by(Conversation.updated_at.desc(), Conversation.id.desc())
        )
        if limit is not None:
            query = query.limit(limit)
        result = await self._session.execute(query)
        return list(result.scalars().all())

    async def touch(self, conversation_id: uuid.UUID) -> None:
        await self._session.execute(
            update(Conversation)
            .where(Conversation.id == conversation_id)
            .values(updated_at=datetime.now(UTC))
        )
        await self._session.commit()

    async def update_summary(self, conversation_id: uuid.UUID, summary: dict[str, Any]) -> None:
        await self._session.execute(
            update(Conversation).where(Conversation.id == conversation_id).values(summary=summary)
        )
        await self._session.commit()

    async def delete(self, conversation_id: uuid.UUID) -> None:
        await self._session.execute(delete(Conversation).where(Conversation.id == conversation_id))
        await self._session.commit()

    async def interviews_for_users(self, user_ids: list[uuid.UUID]) -> list[Conversation]:
        if not user_ids:
            return []
        result = await self._session.execute(
            select(Conversation).where(
                Conversation.user_id.in_(user_ids), Conversation.kind == "interview"
            )
        )
        return list(result.scalars().all())
