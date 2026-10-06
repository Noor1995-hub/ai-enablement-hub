"""Where each media file is used (B6): lessons, and AI proposals that are still
pending or approved. Any reference means "in use"; deleting is only for unused
files, re-checked at delete time."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from src.core.media_usage import blob_paths
from src.services.exceptions import MediaInUseError

if TYPE_CHECKING:
    import uuid

    from src.repositories.base import AbstractContentRepository, AbstractProposalRepository

__all__ = ["MediaUsage", "MediaUsageService"]


@dataclass
class MediaUsage:
    """lessons: (lesson id, lesson title, module title); proposals: how many live
    AI proposals reference the file."""

    lessons: list[tuple[uuid.UUID, str, str]] = field(default_factory=list)
    proposals: int = 0


class MediaUsageService:
    def __init__(
        self, content: AbstractContentRepository, proposals: AbstractProposalRepository
    ) -> None:
        self._content = content
        self._proposals = proposals

    async def usage(self) -> dict[str, MediaUsage]:
        found: dict[str, MediaUsage] = {}
        for lesson, module_title in await self._content.lessons_with_module_titles():
            for path in blob_paths(lesson.content_blocks):
                found.setdefault(path, MediaUsage()).lessons.append(
                    (lesson.id, lesson.title, module_title)
                )
        for blocks in await self._proposals.live_block_sets():
            for path in blob_paths(blocks):
                found.setdefault(path, MediaUsage()).proposals += 1
        return found

    async def ensure_unused(self, path: str) -> None:
        use = (await self.usage()).get(path)
        if use is None:
            return
        titles = [title for _, title, _ in use.lessons] or ["an AI content proposal"]
        raise MediaInUseError(titles)
