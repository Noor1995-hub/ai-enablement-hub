"""Write the backend's OpenAPI document to a file, without starting the server.

Used by `npm run gen:api` (frontend/package.json) and the CI API-types check. Importing the app
runs no lifespan, so nothing connects to the database — unlike `poe dev`, whose cleanup loop
deletes expired sessions in the one shared database (docs/superpowers/lessons.md, 2026-09-23).

Run from backend/: `uv run python scripts/export_openapi.py <out.json>`.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.main import app  # noqa: E402 — needs the sys.path entry above


def main() -> None:
    if len(sys.argv) != 2:
        sys.exit("usage: export_openapi.py <out.json>")
    Path(sys.argv[1]).write_text(json.dumps(app.openapi()), encoding="utf-8")


if __name__ == "__main__":
    main()
