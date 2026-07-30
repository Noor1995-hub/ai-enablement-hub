#!/usr/bin/env python3
"""Restore an ai-enablement-hub dump into a target database.

Runs as the manually-triggered Container Apps Job `ai-enablement-hub-db-restore`
(same image as the nightly backup). Restores happen in Azure because no
Postgres client tools are installed on the maintainer's machine — the runbook
must not require an install during an outage.

Env:
  PGURL_TARGET     required  DSN of the ALREADY-EXISTING target database
  STORAGE_ACCOUNT  required  e.g. aienablementhubmedia
  BLOB_CONTAINER   db-backups
  BLOB_PREFIX      ai-enablement-hub
  SOURCE_BLOB      empty => newest dump under the prefix
  RESTORE_TABLE    empty => whole database; else that table's data only

Never writes to the production database unless PGURL_TARGET points at it —
the runbook's cherry-pick step is a separate, human-driven action.

Exit codes: 0 ok | 2 config error | 3 download failure | 4 pg_restore failure
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

from dumpcheck import parse_backup_ts


def required(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        print(f"FATAL: missing required env var {name}", file=sys.stderr)
        raise SystemExit(2)
    return value


def main() -> int:
    target = required("PGURL_TARGET")
    account = required("STORAGE_ACCOUNT")
    container_name = os.environ.get("BLOB_CONTAINER", "db-backups")
    prefix = os.environ.get("BLOB_PREFIX", "ai-enablement-hub")
    source = os.environ.get("SOURCE_BLOB", "").strip()
    table = os.environ.get("RESTORE_TABLE", "").strip()

    from azure.identity import DefaultAzureCredential
    from azure.storage.blob import BlobServiceClient

    try:
        credential = DefaultAzureCredential()
        service = BlobServiceClient(
            f"https://{account}.blob.core.windows.net", credential=credential
        )
        container = service.get_container_client(container_name)

        if not source:
            dumps = [
                b.name
                for b in container.list_blobs(name_starts_with=f"{prefix}/")
                if b.name.endswith(".dump") and parse_backup_ts(b.name) is not None
            ]
            if not dumps:
                print(f"FATAL: no dumps found under {prefix}/", file=sys.stderr)
                return 3
            source = max(dumps, key=lambda name: parse_backup_ts(name))
        print(f"restoring from {source}")

        with tempfile.TemporaryDirectory() as tmp:
            local = Path(tmp) / Path(source).name
            with local.open("wb") as handle:
                container.download_blob(source).readinto(handle)
            print(f"downloaded {local.stat().st_size} bytes")

            cmd = [
                "pg_restore",
                "--no-owner",
                "--no-acl",
                "--exit-on-error",
                "--dbname",
                target,
            ]
            if table:
                cmd += ["--data-only", "--table", table]
            cmd.append(str(local))

            proc = subprocess.run(cmd, capture_output=True, text=True)
            if proc.returncode != 0:
                print(
                    f"FATAL: pg_restore exited {proc.returncode}: {proc.stderr.strip()[:4000]}",
                    file=sys.stderr,
                )
                return 4
            if proc.stderr.strip():
                print(proc.stderr.strip()[:4000])
    except Exception as exc:  # noqa: BLE001
        print(f"FATAL: blob stage failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 3

    scope = f"table {table}" if table else "whole database"
    print(f"OK restored {scope} from {source}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
