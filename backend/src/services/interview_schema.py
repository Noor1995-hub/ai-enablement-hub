from __future__ import annotations

from src.schemas.interview import PlaybookExtraction
from src.services.llm_service import StructuredSchema

__all__ = ["PLAYBOOK_SCHEMA"]

_schema = PlaybookExtraction.model_json_schema()
_schema["additionalProperties"] = False

PLAYBOOK_SCHEMA = StructuredSchema(
    name="record_playbook",
    description=(
        "Record the two-box interview playbook: internal (delaware-only) "
        "and shared (learner-facing)."
    ),
    input_schema=_schema,
)
