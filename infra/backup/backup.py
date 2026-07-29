#!/usr/bin/env python3
"""Nightly logical backup of the ai-enablement-hub database.

Runs as the Azure Container Apps Job `ai-enablement-hub-db-backup`:
    pg_dump -Fc + pg_dumpall --globals-only
      -> verify (size floor + TABLE DATA count)
      -> upload to Blob Storage (server-side MD5 validated)
      -> prune backups older than KEEP_DAYS
Nothing is uploaded unless verification passes.

Env:
  PGURL                 required   ai_hub_owner DSN, sslmode=require
  STORAGE_ACCOUNT       required   e.g. aienablementhubmedia
  BLOB_CONTAINER        db-backups
  BLOB_PREFIX           ai-enablement-hub
  KEEP_DAYS             30
  EXPECTED_TABLE_COUNT  1          raise to (observed - 2) after the first run
  MIN_DUMP_BYTES        1          raise to (observed / 2) after the first run

Blob auth is the job's managed identity (DefaultAzureCredential) — no keys.

Exit codes: 0 ok | 2 config error | 3 dump/verify failure | 4 upload/prune failure
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from dumpcheck import DumpVerificationError, blob_names, select_prunable, verify_dump


def required(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        print(f"FATAL: missing required env var {name}", file=sys.stderr)
        raise SystemExit(2)
    return value


def optional_int(name: str, default: int) -> int:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        print(f"FATAL: env var {name}={raw!r} is not an integer", file=sys.stderr)
        raise SystemExit(2) from None


def run_tool(cmd: list[str]) -> str:
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise DumpVerificationError(
            f"{cmd[0]} exited {proc.returncode}: {proc.stderr.strip()[:2000]}"
        )
    return proc.stdout


def main() -> int:
    pgurl = required("PGURL")
    account = required("STORAGE_ACCOUNT")
    container_name = os.environ.get("BLOB_CONTAINER", "db-backups")
    prefix = os.environ.get("BLOB_PREFIX", "ai-enablement-hub")
    keep_days = optional_int("KEEP_DAYS", 30)
    expected_tables = optional_int("EXPECTED_TABLE_COUNT", 1)
    min_bytes = optional_int("MIN_DUMP_BYTES", 1)

    # Imported after the config guard so a misconfigured job fails fast and
    # identically whether or not the Azure SDKs are importable.
    from azure.identity import DefaultAzureCredential
    from azure.storage.blob import BlobServiceClient

    now = datetime.now(timezone.utc)
    dump_blob, globals_blob = blob_names(prefix, now)

    with tempfile.TemporaryDirectory() as tmp:
        dump_path = Path(tmp) / Path(dump_blob).name
        globals_path = Path(tmp) / Path(globals_blob).name
        try:
            run_tool(["pg_dump", "--format=custom", "--compress=9", "--file", str(dump_path), pgurl])
            run_tool(
                [
                    "pg_dumpall",
                    "--globals-only",
                    "--no-role-passwords",  # ai_hub_owner cannot read pg_authid
                    "--file",
                    str(globals_path),
                    "--dbname",
                    pgurl,
                ]
            )
            listing = run_tool(["pg_restore", "--list", str(dump_path)])
            size = dump_path.stat().st_size
            tables = verify_dump(size, listing, min_bytes, expected_tables)
        except DumpVerificationError as exc:
            print(f"FATAL: {exc}", file=sys.stderr)
            return 3

        try:
            credential = DefaultAzureCredential()
            service = BlobServiceClient(
                f"https://{account}.blob.core.windows.net", credential=credential
            )
            container = service.get_container_client(container_name)
            for path, blob_name in ((dump_path, dump_blob), (globals_path, globals_blob)):
                with path.open("rb") as handle:
                    container.upload_blob(
                        name=blob_name,
                        data=handle,
                        overwrite=False,
                        validate_content=True,  # service-side MD5 check
                    )
                print(f"uploaded {blob_name} ({path.stat().st_size} bytes)")

            existing = [b.name for b in container.list_blobs(name_starts_with=f"{prefix}/")]
            doomed = select_prunable(existing, now, keep_days)
            for blob_name in doomed:
                container.delete_blob(blob_name)
                print(f"pruned {blob_name}")
        except Exception as exc:  # noqa: BLE001 - the job's job is to report and fail
            print(f"FATAL: blob stage failed: {type(exc).__name__}: {exc}", file=sys.stderr)
            return 4

    # `existing` was listed AFTER the two uploads, so it already includes them.
    print(
        f"OK dump={dump_blob} bytes={size} tables={tables} "
        f"kept={len(existing) - len(doomed)} pruned={len(doomed)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
