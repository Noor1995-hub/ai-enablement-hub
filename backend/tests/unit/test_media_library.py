from __future__ import annotations

import uuid
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from src.repositories.base import AbstractContentRepository, AbstractProposalRepository
from src.services.exceptions import MediaInUseError
from src.services.media_service import MediaService
from src.services.media_usage_service import MediaUsageService
from tests.fixtures.media import TEST_STORAGE, RecordingUploader

IMG = "images/" + "a" * 32 + ".png"
VID = "videos/" + "b" * 32 + ".mp4"


def _media(uploader: RecordingUploader) -> MediaService:
    return MediaService(
        uploader,
        account_name=TEST_STORAGE.account_name,
        account_key=TEST_STORAGE.account_key.get_secret_value(),
        blob_endpoint=TEST_STORAGE.blob_endpoint,
        container=TEST_STORAGE.container,
        sas_ttl_hours=TEST_STORAGE.sas_ttl_hours,
    )


async def test_list_and_delete_files() -> None:
    uploader = RecordingUploader()
    uploader.stored[IMG] = (10, datetime(2026, 1, 1, tzinfo=UTC))
    uploader.stored[VID] = (20, datetime(2026, 2, 1, tzinfo=UTC))
    media = _media(uploader)

    files = await media.list_files()
    assert [(f.path, f.kind, f.size_bytes) for f in files] == [
        (VID, "video", 20),
        (IMG, "image", 10),
    ]
    assert await media.delete_file(IMG) is True
    assert await media.delete_file(IMG) is False


def _usage(lessons: list, proposal_sets: list) -> MediaUsageService:  # noqa: ANN401
    content = AsyncMock(spec=AbstractContentRepository)
    content.lessons_with_module_titles.return_value = lessons
    proposals = AsyncMock(spec=AbstractProposalRepository)
    proposals.live_block_sets.return_value = proposal_sets
    return MediaUsageService(content, proposals)


async def test_usage_maps_paths_to_lessons_and_live_proposals() -> None:
    lesson = SimpleNamespace(
        id=uuid.uuid4(),
        title="Prompts",
        content_blocks=[{"id": "i", "type": "image", "blob_path": IMG, "alt": "a"}],
    )
    service = _usage(
        [(lesson, "Basics")], [[{"id": "v", "type": "video", "source": "blob", "blob_path": VID}]]
    )

    usage = await service.usage()

    assert usage[IMG].lessons == [(lesson.id, "Prompts", "Basics")]
    assert usage[VID].proposals == 1


async def test_usage_ignores_dead_proposals_and_embed_videos() -> None:
    lesson = SimpleNamespace(
        id=uuid.uuid4(),
        title="L",
        content_blocks=[{"id": "y", "type": "video", "source": "embed", "url": "https://x"}],
    )
    service = _usage([(lesson, "M")], [])  # live_block_sets already excludes rejected/superseded
    assert await service.usage() == {}


async def test_ensure_unused_refuses_a_referenced_file_naming_the_lesson() -> None:
    lesson = SimpleNamespace(
        id=uuid.uuid4(),
        title="Prompts",
        content_blocks=[{"id": "i", "type": "image", "blob_path": IMG, "alt": "a"}],
    )
    service = _usage([(lesson, "Basics")], [])
    with pytest.raises(MediaInUseError, match="Prompts"):
        await service.ensure_unused(IMG)
    await service.ensure_unused(VID)  # unused: no error
