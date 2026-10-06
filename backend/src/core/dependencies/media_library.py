"""DI for the media library's usage scan (B6). Its own module because the
proposal repository provider lives in content_ai.py. All parameter annotations
are runtime imports on purpose (see database.py)."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from src.core.dependencies.content_ai import get_proposal_repository
from src.core.dependencies.domain import get_content_repository
from src.repositories.content_repository import ContentRepository
from src.repositories.proposal_repository import ProposalRepository
from src.services.media_usage_service import MediaUsageService

__all__ = ["get_media_usage_service"]


def get_media_usage_service(
    content: Annotated[ContentRepository, Depends(get_content_repository)],
    proposals: Annotated[ProposalRepository, Depends(get_proposal_repository)],
) -> MediaUsageService:
    return MediaUsageService(content, proposals)
