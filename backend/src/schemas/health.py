from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

__all__ = ["HealthOut"]


class HealthOut(BaseModel):
    """Liveness + build identity. `build_sha` is the deploy workflow's read-back target."""

    status: Literal["ok"]
    build_sha: str
    build_time: str
