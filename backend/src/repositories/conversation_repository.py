# backend/src/repositories/conversation_repository.py
from __future__ import annotations

import uuid

from sqlalchemy import func, select, update

from src.db.models import Conversation
from src.repositories.base import AbstractConversationRepository

__all__ = ["ConversationRepository"]


class ConversationRepository(AbstractConversationRepository):
    async def create(
        self, *, user_id: uuid.UUID, kind: str, context_ref: str | None = None
    ) -> Conversation:
        conversation = Conversation(user_id=user_id, kind=kind, context_ref=context_ref)
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
            .values(updated_at=func.now())
        )
        await self._session.commit()
