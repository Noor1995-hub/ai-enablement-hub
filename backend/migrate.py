"""Migration job entrypoint: `alembic upgrade head`, then exit.

Runs in the `ai-enablement-hub-migrate` Container Apps Job BEFORE each deploy rolls the app
(see .github/workflows/deploy.yml). The app container itself never migrates (startup.py).
Uses the Alembic Python API because the image has no shell entrypoint conventions to rely on.
Exit code is the contract: 0 = schema at head, non-zero = the deploy must not proceed.
"""

from __future__ import annotations

import sys

from alembic.config import Config
from alembic.script import ScriptDirectory

from alembic import command

__all__ = ["main"]


def main() -> int:
    cfg = Config("alembic.ini")
    script_head = ScriptDirectory.from_config(cfg).get_current_head()
    print(f"[migrate] code head: {script_head}", flush=True)
    try:
        command.upgrade(cfg, "head")
    except Exception as exc:  # noqa: BLE001 - the exit code is the contract
        # Type only: the message may embed the DSN (e.g. SQLAlchemy ArgumentError). The message is
        # dropped on purpose - diagnose from alembic's log lines above, or reproduce on the test DB.
        print(f"[migrate] FAILED: {type(exc).__name__}", flush=True)
        return 1
    print("[migrate] upgrade head: done", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
