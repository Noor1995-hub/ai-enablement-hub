from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

__all__ = ["AppSettings"]


class AppSettings(BaseModel):
    """App-level settings; env prefix `APP__` (see Settings).

    `url` is the public frontend origin: it is both the CORS allow-origin and
    the base for invite/reset links (`{url}/invite/{token}`).
    """

    model_config = ConfigDict(frozen=True)

    url: str = "http://localhost:5173"
    env: Literal["dev", "prod"] = "dev"

    # Stamped by .github/workflows/deploy.yml at roll time (APP__BUILD_SHA = full commit SHA,
    # APP__BUILD_TIME = ISO-8601 UTC). Defaults mark a local/dev process. Surfaced by /api/health.
    build_sha: str = "dev"
    build_time: str = ""

    @property
    def cors_origins(self) -> list[str]:
        origins = [self.url.rstrip("/")]
        if self.env == "dev":
            for origin in ("http://localhost:3000", "http://localhost:5173"):
                if origin not in origins:
                    origins.append(origin)
        return origins
