"""ContentService.update_lesson: the 1 MiB ceiling on `content_blocks` saves
(decision 5.2 option A) -- boundary behaviour only, with an AsyncMock
repository (no DB). Human lesson saves stay structurally *unvalidated* by
design (most of the live corpus predates `validate_content_blocks`'s
nested-id rule); this is a size cap, not a structural gate, and it must sit
after A8's url-scheme check without changing that check's behaviour."""

from __future__ import annotations

import json
import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from src.repositories.base import AbstractContentRepository
from src.services.content_service import MAX_LESSON_BLOCKS_BYTES, ContentService
from src.services.exceptions import InvalidRequestError, PayloadTooLargeError


def _service(*, lesson: object | None) -> tuple[ContentService, AsyncMock]:
    content = AsyncMock(spec=AbstractContentRepository)
    content.get_lesson.return_value = lesson
    return ContentService(content), content


def _blocks_of_size(target_bytes: int) -> list[dict[str, str]]:
    """A single paragraph block whose serialized JSON (the exact bytes the
    service measures: `ensure_ascii=False`, compact separators) is exactly
    `target_bytes` long. Padding is plain ASCII, so each extra character adds
    exactly one byte -- no escaping, and the block type is neither `image`
    nor a blob `video`, so `strip_ephemeral` never touches it."""
    block = {"id": "b1", "type": "paragraph", "text": ""}
    overhead = len(json.dumps([block], ensure_ascii=False, separators=(",", ":")).encode())
    pad = target_bytes - overhead
    assert pad >= 0, "target_bytes too small for the block's fixed overhead"
    block["text"] = "a" * pad
    blocks = [block]
    assert (
        len(json.dumps(blocks, ensure_ascii=False, separators=(",", ":")).encode()) == target_bytes
    )
    return blocks


class TestLessonSizeCeiling:
    async def test_content_exactly_at_limit_saves(self) -> None:
        lesson = SimpleNamespace(id=uuid.uuid4())
        service, content = _service(lesson=lesson)
        blocks = _blocks_of_size(MAX_LESSON_BLOCKS_BYTES)

        await service.update_lesson(lesson.id, {"content_blocks": blocks})

        content.update_lesson.assert_awaited_once()
        saved_blocks = content.update_lesson.await_args.args[1]["content_blocks"]
        assert saved_blocks == blocks

    async def test_one_byte_over_limit_raises_and_does_not_save(self) -> None:
        lesson = SimpleNamespace(id=uuid.uuid4())
        service, content = _service(lesson=lesson)
        blocks = _blocks_of_size(MAX_LESSON_BLOCKS_BYTES + 1)

        with pytest.raises(PayloadTooLargeError) as exc_info:
            await service.update_lesson(lesson.id, {"content_blocks": blocks})

        assert str(MAX_LESSON_BLOCKS_BYTES) in str(exc_info.value)
        content.update_lesson.assert_not_awaited()

    async def test_bad_link_scheme_still_rejected_even_when_small(self) -> None:
        """A8's scheme check must keep running, and keep winning, ahead of the
        size check -- a small but unsafe payload is still a 400, not a save."""
        lesson = SimpleNamespace(id=uuid.uuid4())
        service, content = _service(lesson=lesson)
        blocks = [{"id": "b1", "type": "paragraph", "text": "[click](javascript:alert(1))"}]

        with pytest.raises(InvalidRequestError):
            await service.update_lesson(lesson.id, {"content_blocks": blocks})

        content.update_lesson.assert_not_awaited()
