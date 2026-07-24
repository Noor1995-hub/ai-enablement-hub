# backend/src/repositories/message_repository.py
from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select

from src.db.models import Message
from src.repositories.base import AbstractMessageRepository

__all__ = ["MessageRepository"]


class MessageRepository(AbstractMessageRepository):
    async def create(
        self,
        conversation_id: uuid.UUID,
        *,
        role: str,
        content: str,
        metadata: dict[str, Any] | None,
    ) -> Message:
        # created_at is set here (rather than left to the column's server-side
        # `now()` default) because `now()` is fixed at transaction start: two
        # messages created back-to-back within the same transaction — as every
        # request handler's unit-of-work is, and as every test's savepoint-
        # wrapped session is — would otherwise get an identical timestamp and
        # break the chronological ordering list_for_conversation/list_recent
        # depend on.
        message = Message(
            conversation_id=conversation_id,
            role=role,
            content=content,
            metadata_=metadata,
            created_at=datetime.now(UTC),
        )
        self._session.add(message)
        await self._session.commit()
        await self._session.refresh(message)
        return message

    async def list_for_conversation(self, conversation_id: uuid.UUID) -> list[Message]:
        result = await self._session.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.asc())
        )
        return list(result.scalars().all())

    async def list_recent(self, conversation_id: uuid.UUID, *, limit: int) -> list[Message]:
        result = await self._session.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.desc())
            .limit(limit)
        )
        rows = list(result.scalars().all())
        rows.reverse()
        return rows
