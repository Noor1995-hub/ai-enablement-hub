# /// script
# requires-python = ">=3.11"
# dependencies = ["asyncpg~=0.30"]
# ///
"""Inspect, create or drop the restore-drill scratch database.

    $env:LIVE_DSN = '<DSN for ai-enablement-hub>'
    uv run infra/backup/drill_db.py --check
    uv run infra/backup/drill_db.py --create
    uv run infra/backup/drill_db.py --drop

CREATE/DROP DATABASE cannot run inside a transaction; asyncpg autocommits, so a
plain connection is enough.

**--create must run as the Entra admin, not ai_hub_owner.** Confirmed 2026-07-30:
`ai_hub_owner` has rolcreatedb=False on this server, so it cannot create the
scratch database at all. Get an admin DSN with the token recipe in db/README.md
(user `danneelm%40delawareconsulting.com`, password = the AAD access token) --
`--check` prints the connected role's rolcreatedb so you can tell which you have.

--create does TWO privilege steps, and both are load-bearing for the restore job
(which connects as ai_hub_owner and must be able to create every table):

1. `CREATE DATABASE ... OWNER ai_hub_owner`.
2. `ALTER SCHEMA public OWNER TO ai_hub_owner` *inside the new database*.

Step 2 is not redundant. On this Azure Flexible Server a freshly created
database's `public` schema is NOT owned by `pg_database_owner`, so owning the
database does not confer CREATE on its public schema. Proven the hard way
2026-07-30: with step 1 only, the restore job died on
`pg_restore: error: could not execute query: ERROR: permission denied for
schema public / CREATE TABLE public.alembic_version`.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from urllib.parse import urlsplit, urlunsplit

import asyncpg

DRILL_DB = "ai-enablement-hub-restoredrill"
# The role the restore job connects as; it must own the scratch DB (see docstring).
DRILL_OWNER = "ai_hub_owner"


def with_dbname(dsn: str, dbname: str) -> str:
    """Same DSN, different database — for connecting into the scratch DB."""
    parts = urlsplit(dsn)
    return urlunsplit((parts.scheme, parts.netloc, f"/{dbname}", parts.query, parts.fragment))


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
            await conn.execute(f'CREATE DATABASE "{DRILL_DB}" OWNER "{DRILL_OWNER}"')
            print(f"created {DRILL_DB} owned by {DRILL_OWNER}")
            inner = await asyncpg.connect(with_dbname(dsn, DRILL_DB))
            try:
                await inner.execute(f'ALTER SCHEMA public OWNER TO "{DRILL_OWNER}"')
            finally:
                await inner.close()
            print(f"public schema owner -> {DRILL_OWNER}")
        else:
            await conn.execute(f'DROP DATABASE "{DRILL_DB}"')
            print(f"dropped {DRILL_DB}")
    finally:
        await conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
