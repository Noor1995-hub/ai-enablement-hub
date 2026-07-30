# backend/src/repositories/conversation_repository.py
from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import delete, select, update

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

    async def get_by_id(self, conversation_id: uuid.UUID) -> Conversation | None:
        result = await self._session.execute(
            select(Conversation).where(Conversation.id == conversation_id)
        )
        return result.scalar_one_or_none()

    async def list_for_user(self, user_id: uuid.UUID, kind: str) -> list[Conversation]:
        result = await self._session.execute(
            select(Conversation)
            .where(Conversation.user_id == user_id, Conversation.kind == kind)
            .order_by(Conversation.updated_at.desc())
        )
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
