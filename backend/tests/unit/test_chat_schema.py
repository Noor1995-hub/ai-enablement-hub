from __future__ import annotations

import pytest

from src.schemas.chat import ChatMessageCreate


def test_blank_content_is_rejected() -> None:
    with pytest.raises(ValueError, match="empty"):
        ChatMessageCreate(content="   ", conversation_id=None)


def test_oversized_content_is_rejected() -> None:
    with pytest.raises(ValueError, match="4000"):
        ChatMessageCreate(content="x" * 4001, conversation_id=None)


def test_content_is_stripped() -> None:
    body = ChatMessageCreate(content="  hi  ", conversation_id=None)
    assert body.content == "hi"
