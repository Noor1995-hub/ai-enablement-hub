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
    """Reserved for the later "apply defaults to existing users" endpoint —
    not wired to any router yet."""

    users_updated: int
