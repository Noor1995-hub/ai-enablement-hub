# /// script
# requires-python = ">=3.11"
# dependencies = ["asyncpg~=0.30"]
# ///
"""Inspect, create or drop the restore-drill scratch database.

    $env:LIVE_DSN = '<ai_hub_owner DSN for ai-enablement-hub>'
    uv run infra/backup/drill_db.py --check
    uv run infra/backup/drill_db.py --create
    uv run infra/backup/drill_db.py --drop

CREATE/DROP DATABASE cannot run inside a transaction; asyncpg autocommits, so a
plain connection is enough. If --check reports rolcreatedb=False, connect as the
Entra admin instead (token recipe in db/README.md) and run the same statements.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys

import asyncpg

DRILL_DB = "ai-enablement-hub-restoredrill"


async def main() -> int:
    parser = argparse.ArgumentParser()
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--check", action="store_true", help="report privileges and existence")
    action.add_argument("--create", action="store_true")
    action.add_argument("--drop", action="store_true")
    args = parser.parse_args()

    dsn = os.environ.get("LIVE_DSN", "").strip()
    if not dsn:
        print("FATAL: set LIVE_DSN first", file=sys.stderr)
        return 2

    conn = await asyncpg.connect(dsn)
    try:
        if args.check:
            role = await conn.fetchrow(
                "SELECT rolname, rolcreatedb, rolsuper FROM pg_roles WHERE rolname = current_user"
            )
            exists = await conn.fetchval("SELECT 1 FROM pg_database WHERE datname = $1", DRILL_DB)
            print(
                f"connected as {role['rolname']}: "
                f"rolcreatedb={role['rolcreatedb']} rolsuper={role['rolsuper']}"
            )
            print(f"scratch database {DRILL_DB!r} exists: {bool(exists)}")
        elif args.create:
            await conn.execute(f'CREATE DATABASE "{DRILL_DB}"')
            print(f"created {DRILL_DB}")
        else:
            await conn.execute(f'DROP DATABASE "{DRILL_DB}"')
            print(f"dropped {DRILL_DB}")
    finally:
        await conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
