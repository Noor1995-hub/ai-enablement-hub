"""Production entrypoint: start uvicorn. Nothing else.

Migrations run in the `ai-enablement-hub-migrate` Container Apps Job before each deploy rolls
the app (see .github/workflows/deploy.yml and backend/migrate.py); the container never migrates,
so a restart can never change the schema and the startup probe only waits for uvicorn to bind.
"""

from __future__ import annotations

import uvicorn

__all__ = ["main"]


def main() -> None:
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
