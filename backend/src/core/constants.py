"""Server-side home of the component constants (was app/api/_lib/constants.js).

Moving these behind the API kills the old D4 duplication: the frontend now
receives resolved hidden/locked flags from /me/journey and the admin component
endpoints instead of re-deriving defaults itself.
"""

from __future__ import annotations

__all__ = ["COMPONENTS", "DEFAULT_HIDDEN", "DEFAULT_LOCKED"]

COMPONENTS = ("assessment", "learning", "interview")
DEFAULT_LOCKED = {"assessment": False, "learning": True, "interview": True}
DEFAULT_HIDDEN = {"assessment": False, "learning": False, "interview": False}
