"""Field validators shared across the schema modules.

Underscore-prefixed because it is internal to `schemas/` — nothing outside this
package should import it. Kept here rather than in `core/` because it is part of
the wire-validation layer, not a cross-cutting concern.
"""

from __future__ import annotations

__all__ = ["require_non_blank"]


def require_non_blank(value: str | None) -> str | None:
    """Reject a present-but-whitespace-only string; pass None through.

    `None` is allowed so the one function serves both the required-field schemas
    (where Pydantic never hands a validator None) and the all-optional `Update`
    schemas, where an omitted field is legitimately None and only an explicitly
    blanked one is an error. Deliberately does NOT strip: the services own
    trimming on write (`content_service.update_lesson`, `org_service`), and a
    validator that quietly rewrote values would hide that.
    """
    if value is not None and not value.strip():
        msg = "must not be blank"
        raise ValueError(msg)
    return value
