from __future__ import annotations

import uuid

from pydantic import BaseModel

__all__ = ["ApplyDefaultsResponse", "DefaultsResponse", "DefaultsUpdateRequest"]


class DefaultsResponse(BaseModel):
    track_ids: list[uuid.UUID]


class DefaultsUpdateRequest(BaseModel):
    """Full replace; an empty list clears the project's defaults."""

    track_ids: list[uuid.UUID]


class ApplyDefaultsResponse(BaseModel):
    """Response of POST .../defaults/apply — how many of the project's
    existing users the additive backfill ran over (regardless of whether the
    project currently has any default tracks configured)."""

    users_updated: int
