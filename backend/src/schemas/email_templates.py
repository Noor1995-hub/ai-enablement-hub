from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

__all__ = [
    "EmailTemplateOut",
    "EmailTemplatePreviewRequest",
    "EmailTemplatePreviewResponse",
    "EmailTemplateUpdateRequest",
    "EmailTemplatesResponse",
]

EmailPurpose = Literal["invite", "reset"]


class EmailTemplateOut(BaseModel):
    purpose: EmailPurpose
    subject: str
    body_markdown: str
    # False = the code default is in effect (no per-project override stored).
    is_custom: bool


class EmailTemplatesResponse(BaseModel):
    templates: list[EmailTemplateOut]


class EmailTemplateUpdateRequest(BaseModel):
    # Content-level rules (link token present, known tokens only, non-blank) are
    # enforced in the service so subject/body stay a single validation surface.
    subject: str
    body_markdown: str


class EmailTemplatePreviewRequest(BaseModel):
    subject: str
    body_markdown: str


class EmailTemplatePreviewResponse(BaseModel):
    subject: str
    html: str
    plain_text: str
