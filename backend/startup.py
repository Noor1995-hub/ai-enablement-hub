"""Production entrypoint: run migrations, then start uvicorn.

Uses the Alembic Python API (a distroless container has no shell).
"""

from __future__ import annotations

import uvicorn
from alembic.config import Config

from alembic import command

__all__ = ["main"]


def main() -> None:
    cfg = Config("alembic.ini")
    command.upgrade(cfg, "head")

    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=8000,
        http="httptools",
        proxy_headers=True,
        forwarded_allow_ips="*",
    )


if __name__ == "__main__":
    main()
