"""Shared helper: build a live-DB DSN from backend/.env at runtime.

Never persists the password anywhere -- callers read backend/.env fresh each
run and hold the DSN in memory only. Import this from the other content_tools
scripts (each declares its own PEP 723 deps block, so this file has none of
its own -- it has no third-party imports).
"""
from __future__ import annotations
from pathlib import Path


def load_env(path: Path) -> dict[str, str]:
    env: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        env[k.strip()] = v.strip()
    return env


def dsn_from_env(env: dict[str, str]) -> str:
    return (
        f"{env['DATABASE__PROTOCOL']}://{env['DATABASE__USERNAME']}:{env['DATABASE__PASSWORD']}"
        f"@{env['DATABASE__HOST']}:{env['DATABASE__PORT']}/{env['DATABASE__NAME']}"
        f"?sslmode={env['DATABASE__SSL_MODE']}"
    )


def dsn(backend_env_path: str | Path = "backend/.env") -> str:
    return dsn_from_env(load_env(Path(backend_env_path)))
