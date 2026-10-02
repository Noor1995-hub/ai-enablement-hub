from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel

__all__ = ["ProjectAdminOut", "ProjectAdminsResponse"]


class ProjectAdminOut(BaseModel):
    user_id: uuid.UUID
    first_name: str
    last_name: str
    email: str
    granted_at: datetime


class ProjectAdminsResponse(BaseModel):
    admins: list[ProjectAdminOut]
