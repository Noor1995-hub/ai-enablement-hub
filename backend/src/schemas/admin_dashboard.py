from __future__ import annotations

import uuid
from typing import Literal

from pydantic import BaseModel

__all__ = [
    "AttentionItemOut",
    "DashboardResponse",
    "DashboardTiles",
    "FunnelOut",
    "MaturityDistributionOut",
]


class DashboardTiles(BaseModel):
    learners: int  # non-admin users in scope
    active_week: int  # last activity <= ACTIVE_DAYS (locked)
    attention: int
    new_feedback: int


class AttentionItemOut(BaseModel):
    user_id: uuid.UUID
    name: str
    email: str
    project_id: uuid.UUID | None
    project_name: str | None
    company_name: str | None
    kind: Literal["never_activated", "not_assessed", "stalled"]
    reason: str


class FunnelOut(BaseModel):
    project_id: uuid.UUID
    project_name: str
    company_name: str
    invited: int  # all learners of the project
    activated: int
    assessed: int
    started: int  # >= 1 lesson completed
    completed_track: int  # >= 1 assigned track fully completed (locked definition)


class MaturityDistributionOut(BaseModel):
    explore: int
    practitioner: int
    integrator: int
    multiplier: int


class DashboardResponse(BaseModel):
    tiles: DashboardTiles
    attention: list[AttentionItemOut]
    funnels: list[FunnelOut]
    maturity: MaturityDistributionOut
