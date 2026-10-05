from __future__ import annotations

from typing import Literal

__all__ = ["EXPORT_SECTIONS", "ExportSection"]

# The project data export's sheets (#92). Interview is sensitive and the
# dialog leaves it unticked; the API takes whatever is asked for.
ExportSection = Literal["people", "assessment", "progress", "interview"]
EXPORT_SECTIONS: tuple[ExportSection, ...] = ("people", "assessment", "progress", "interview")
