# Nightly Database Backups Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the production `ai-enablement-hub` database restorable — selectively and for 30 days — via a nightly Azure Container Apps Job that dumps, verifies, uploads and prunes, plus a proven restore path.

**Architecture:** A small purpose-built container image (`postgres:18` base, so `pg_dump` matches the PG 18 server) holds three entrypoints: `backup.py` (scheduled nightly), `restore.py` (manual, materializes any dated dump into a scratch database) and pure helper module `dumpcheck.py`. Dumps land in a private `db-backups` container on the existing `aienablementhubmedia` storage account, authorized by the job's system-assigned managed identity. Retention is pruned by the script itself (never by an account-wide lifecycle policy). The app image, [`Dockerfile`](../../../Dockerfile) and [`deploy.ps1`](../../../deploy.ps1) are not touched.

**Tech Stack:** Azure Container Apps Jobs, Azure Blob Storage + managed identity, `pg_dump`/`pg_restore` 18, Python 3 (`azure-identity`, `azure-storage-blob`), `uv` for local scripts, `pytest` for the pure logic, `az` CLI for all provisioning.

**Spec:** [`../specs/2026-07-29-database-backups-design.md`](../specs/2026-07-29-database-backups-design.md)

## Plan-time discovery that shaped this plan

This machine has **no `pg_restore`, no `pg_dump`, no `psql` and no Docker** (verified 2026-07-29 — only `uv`, `git` and the old `az` CLI at `C:\Program Files\Microsoft SDKs\Azure\CLI2\wbin\az.cmd`). The spec's restore runbook implicitly assumed a local Postgres client. Rather than require a client install during an outage, restores run **in Azure** as a second, manually-triggered Container Apps Job built from the same image (`restore.py`), and the row-level verification/cherry-pick step runs locally over `asyncpg` (no binaries needed). The spec has been amended to match.

Also confirmed read-only: the PG server has an `AllowAllAzureServices` firewall rule, so the job needs **no new firewall rule**. The Container Apps environment `imaginemore-playground-cae` has static outbound IP `4.165.21.169`.

## Global Constraints

- **Branch:** `feature/db-backups` (already created; spec committed as `6ed0150`).
- **Every Azure/DB mutation is confirmed with Matthias immediately before running it.** Read-only `az` queries need no confirmation. This includes `az acr build`, container/job/identity/role-assignment creation, alert creation, `CREATE DATABASE`, `DROP DATABASE` and every `az containerapp job start`.
- **`az` CLI is old and not on PATH:** invoke as `& 'C:\Program Files\Microsoft SDKs\Azure\CLI2\wbin\az.cmd'`, and set `$env:PYTHONIOENCODING='utf-8'` first or log streaming crashes on unicode.
- **Shell is PowerShell 5.1:** no `&&`, no `||`, no ternary `?:`, no `??`, no inline `if` expressions. Chain with `;` plus `if ($?) { ... }`. Closing `'@` of a here-string must sit at column 0.
- **Never `git add -A`.** The working tree contains other sessions' untracked files (`.claude/`, another spec). Stage explicit paths only.
- **`pg_dump` major version must be >= the server's (18).** It refuses to dump from a newer server. This is why the image is based on `postgres:18`, not a slim image with whatever client apt offers.
- **`pg_dumpall --globals-only` MUST pass `--no-role-passwords`.** Reading password hashes needs `pg_authid` access `ai_hub_owner` does not have on Azure PG.
- **Do not change the PG server's backup retention, replication or HA.** Those are server-wide and the playground server is shared with other apps.
- **Never add a lifecycle-management policy to `aienablementhubmedia`.** Policies are account-wide with prefix filters; a typo would delete lesson media. Pruning is script-side, name-based, scoped to one prefix and one filename pattern.
- **Do not modify the app image, `Dockerfile`, `deploy.ps1`, `backend/pyproject.toml` or `infra/containerapp.yaml`.** This work is additive: `infra/backup/`, `docs/`, and one `CLAUDE.md` entry.
- **Fixed names/values** (copy verbatim): resource group `imaginemore-playground`; PG server `imaginemore-playground-pg`; database `ai-enablement-hub`; Container Apps env `imaginemore-playground-cae`; ACR `ca530fc7463eacr`; storage account `aienablementhubmedia`; blob container `db-backups`; blob prefix `ai-enablement-hub`; backup job `ai-enablement-hub-db-backup`; restore job `ai-enablement-hub-db-restore`; cron `30 2 * * *`; retention 30 days; alert email `matthias.danneel@delaware.pro`.

## File Structure

| File | Responsibility |
|---|---|
| `infra/backup/dumpcheck.py` | **Create.** Pure, stdlib-only logic: dump verification, blob naming, prune selection. No `azure-*` imports so it is unit-testable without the SDKs. |
| `infra/backup/test_dumpcheck.py` | **Create.** Unit tests for the above; the only automated tests in this work. |
| `infra/backup/backup.py` | **Create.** Nightly entrypoint: env config → `pg_dump`/`pg_dumpall` → verify → upload → prune → summary. I/O shell only; decisions live in `dumpcheck.py`. |
| `infra/backup/restore.py` | **Create.** Manual entrypoint: resolve a blob (named or latest) → download → `pg_restore` into a target database. |
| `infra/backup/verify_restore.py` | **Create.** Local `uv` PEP 723 script (asyncpg): compares a restored database against live table-by-table and deep-compares one lesson's `content_blocks`. |
| `infra/backup/drill_db.py` | **Create.** Local `uv` script: `--check` / `--create` / `--drop` for the scratch database. Keeps `CREATE DATABASE` out of shell one-liners. |
| `infra/backup/copy_lesson.py` | **Create.** Local `uv` script: copy one lesson's `content_blocks` from a restored database into live. Dry run by default; this is the everyday recovery action. |
| `infra/backup/Dockerfile` | **Create.** The job image. Build context is `infra/backup/` itself (tiny upload, no `.dockerignore` interaction). |
| `infra/backup/README.md` | **Create.** How to rebuild the image and roll the jobs; points at the runbook for operations. |
| `docs/db-backup-restore.md` | **Create.** The operator runbook: freshness check, three restore paths, cherry-pick example, drill results, known limitations. |
| `CLAUDE.md` | **Modify.** Add a short "Backups" bullet under Deployment pointing at the runbook. |

---

### Task 1: Pure backup logic (`dumpcheck.py`) — TDD

**Files:**
- Create: `infra/backup/dumpcheck.py`
- Test: `infra/backup/test_dumpcheck.py`

**Interfaces:**
- Consumes: nothing (first task).
- Produces, all imported by `backup.py`/`restore.py` in Tasks 2–3:
  - `class DumpVerificationError(RuntimeError)`
  - `TS_FORMAT: str` — `"%Y%m%dT%H%M%SZ"`
  - `count_table_data(listing: str) -> int`
  - `verify_dump(size_bytes: int, listing: str, min_bytes: int, expected_tables: int) -> int` (returns the table count; raises `DumpVerificationError`)
  - `blob_names(prefix: str, ts: datetime) -> tuple[str, str]` → `(dump_blob_name, globals_blob_name)`
  - `parse_backup_ts(blob_name: str) -> datetime | None`
  - `select_prunable(names: Iterable[str], now: datetime, keep_days: int) -> list[str]`

- [ ] **Step 1: Write the failing tests**

Create `infra/backup/test_dumpcheck.py`:

```python
"""Unit tests for the pure backup logic.

Run (no venv, no project install needed):
    uv run --no-project --with pytest pytest infra/backup/test_dumpcheck.py -v
"""

from datetime import datetime, timezone

import pytest

from dumpcheck import (
    DumpVerificationError,
    blob_names,
    count_table_data,
    parse_backup_ts,
    select_prunable,
    verify_dump,
)

LISTING = """;
; Archive created at 2026-07-29 02:30:11 UTC
;     dbname: ai-enablement-hub
;
215; 1259 16456 TABLE public lessons ai_hub_owner
3412; 0 16456 TABLE DATA public lessons ai_hub_owner
3413; 0 16460 TABLE DATA public modules ai_hub_owner
3414; 0 16470 TABLE DATA public users ai_hub_owner
4001; 2606 16600 CONSTRAINT public lessons lessons_pkey ai_hub_owner
"""

NOW = datetime(2026, 7, 29, 2, 30, 0, tzinfo=timezone.utc)


def test_count_table_data_counts_only_data_entries():
    assert count_table_data(LISTING) == 3


def test_count_table_data_on_empty_listing():
    assert count_table_data("") == 0


def test_verify_dump_returns_table_count_when_healthy():
    assert verify_dump(5_000_000, LISTING, min_bytes=1_000_000, expected_tables=3) == 3


def test_verify_dump_rejects_a_dump_below_the_size_floor():
    with pytest.raises(DumpVerificationError) as excinfo:
        verify_dump(12, LISTING, min_bytes=1_000_000, expected_tables=3)
    assert "too small" in str(excinfo.value)


def test_verify_dump_rejects_a_dump_missing_tables():
    with pytest.raises(DumpVerificationError) as excinfo:
        verify_dump(5_000_000, LISTING, min_bytes=1_000_000, expected_tables=20)
    assert "expected >= 20" in str(excinfo.value)


def test_blob_names_are_date_partitioned_and_timestamped():
    dump, globals_ = blob_names("ai-enablement-hub", NOW)
    assert dump == "ai-enablement-hub/2026/07/29/ai-enablement-hub-20260729T023000Z.dump"
    assert globals_ == "ai-enablement-hub/2026/07/29/globals-20260729T023000Z.sql"


@pytest.mark.parametrize(
    "name",
    [
        "ai-enablement-hub/2026/07/29/ai-enablement-hub-20260729T023000Z.dump",
        "ai-enablement-hub/2026/07/29/globals-20260729T023000Z.sql",
    ],
)
def test_parse_backup_ts_reads_both_artifact_kinds(name):
    assert parse_backup_ts(name) == NOW


@pytest.mark.parametrize(
    "name",
    [
        "ai-enablement-hub/2026/07/29/notes.txt",
        "lesson-media/some-image.png",
        "ai-enablement-hub/2026/07/29/ai-enablement-hub-notadate.dump",
        "ai-enablement-hub-20260729T023000Z.dump.bak",
    ],
)
def test_parse_backup_ts_returns_none_for_foreign_names(name):
    assert parse_backup_ts(name) is None


def test_select_prunable_picks_only_blobs_older_than_retention():
    names = [
        "ai-enablement-hub/2026/06/20/ai-enablement-hub-20260620T023000Z.dump",  # 39 days
        "ai-enablement-hub/2026/06/29/ai-enablement-hub-20260629T023000Z.dump",  # exactly 30 days
        "ai-enablement-hub/2026/07/28/ai-enablement-hub-20260728T023000Z.dump",  # 1 day
    ]
    assert select_prunable(names, NOW, keep_days=30) == [
        "ai-enablement-hub/2026/06/20/ai-enablement-hub-20260620T023000Z.dump"
    ]


def test_select_prunable_never_touches_names_it_cannot_parse():
    names = [
        "lesson-media/logo.png",
        "ai-enablement-hub/2026/01/01/handwritten-notes.txt",
    ]
    assert select_prunable(names, NOW, keep_days=30) == []


def test_select_prunable_prunes_globals_too():
    names = ["ai-enablement-hub/2026/06/01/globals-20260601T023000Z.sql"]
    assert select_prunable(names, NOW, keep_days=30) == names
```

- [ ] **Step 2: Run the tests to verify they fail**

```powershell
cd 'c:\Users\danneelm\projects\AI enablement hub\AI ENABLEMENT HUB REBUILD'
uv run --no-project --with pytest pytest infra/backup/test_dumpcheck.py -v
```

Expected: collection error — `ModuleNotFoundError: No module named 'dumpcheck'`.

- [ ] **Step 3: Write the implementation**

Create `infra/backup/dumpcheck.py`:

```python
"""Pure helpers for the database backup job.

Deliberately free of azure-* imports: this is the part worth unit testing, and
the tests must run with plain `uv run --no-project --with pytest` on a machine
that has no Azure SDKs installed.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from datetime import datetime, timedelta, timezone

TS_FORMAT = "%Y%m%dT%H%M%SZ"

# Matches only the artifacts this job writes:
#   .../ai-enablement-hub-20260729T023000Z.dump
#   .../globals-20260729T023000Z.sql
_BLOB_RE = re.compile(r"(?:^|/)(?:ai-enablement-hub|globals)-(\d{8}T\d{6}Z)\.(?:dump|sql)$")


class DumpVerificationError(RuntimeError):
    """A freshly written dump failed its pre-upload checks (or a tool failed)."""


def count_table_data(listing: str) -> int:
    """Number of 'TABLE DATA' entries in `pg_restore --list` output."""
    return sum(1 for line in listing.splitlines() if "TABLE DATA" in line)


def verify_dump(size_bytes: int, listing: str, min_bytes: int, expected_tables: int) -> int:
    """Return the dump's table count, or raise if it looks truncated/empty."""
    if size_bytes < min_bytes:
        raise DumpVerificationError(f"dump too small: {size_bytes} bytes < floor {min_bytes}")
    tables = count_table_data(listing)
    if tables < expected_tables:
        raise DumpVerificationError(
            f"dump lists {tables} TABLE DATA entries, expected >= {expected_tables}"
        )
    return tables


def blob_names(prefix: str, ts: datetime) -> tuple[str, str]:
    """(dump, globals) blob names for a run at `ts`, partitioned by UTC date."""
    stamp = ts.strftime(TS_FORMAT)
    day = ts.strftime("%Y/%m/%d")
    return (
        f"{prefix}/{day}/ai-enablement-hub-{stamp}.dump",
        f"{prefix}/{day}/globals-{stamp}.sql",
    )


def parse_backup_ts(blob_name: str) -> datetime | None:
    """Timestamp encoded in one of our backup blob names, else None."""
    match = _BLOB_RE.search(blob_name)
    if match is None:
        return None
    return datetime.strptime(match.group(1), TS_FORMAT).replace(tzinfo=timezone.utc)


def select_prunable(names: Iterable[str], now: datetime, keep_days: int) -> list[str]:
    """Backup blobs strictly older than `keep_days`.

    Names that are not recognisably ours are never selected — the prune runs in
    a container that also holds lesson media, so 'unrecognised' must mean
    'leave alone'.
    """
    cutoff = now - timedelta(days=keep_days)
    doomed = []
    for name in names:
        ts = parse_backup_ts(name)
        if ts is not None and ts < cutoff:
            doomed.append(name)
    return sorted(doomed)
```

- [ ] **Step 4: Run the tests to verify they pass**

```powershell
uv run --no-project --with pytest pytest infra/backup/test_dumpcheck.py -v
```

Expected: 15 passed.

- [ ] **Step 5: Commit**

```powershell
git add infra/backup/dumpcheck.py infra/backup/test_dumpcheck.py
git commit -m "feat(backup): pure dump-verification and prune-selection logic"
```

---

### Task 2: Nightly entrypoint (`backup.py`) + image

**Files:**
- Create: `infra/backup/backup.py`
- Create: `infra/backup/Dockerfile`
- Create: `infra/backup/README.md`

**Interfaces:**
- Consumes: `dumpcheck.verify_dump`, `blob_names`, `select_prunable`, `DumpVerificationError` (Task 1).
- Produces: the container image contract later tasks provision against — entrypoint `python3 backup.py`, env vars `PGURL`, `STORAGE_ACCOUNT`, `BLOB_CONTAINER`, `BLOB_PREFIX`, `KEEP_DAYS`, `EXPECTED_TABLE_COUNT`, `MIN_DUMP_BYTES`; exit codes `0` ok / `2` config / `3` dump-or-verify / `4` upload-or-prune.

- [ ] **Step 1: Write the failing test (config guard)**

The upload/prune path is exercised for real against Azure in Task 4; what is unit-testable here is that a misconfigured run dies immediately and loudly instead of half-working. Append to `infra/backup/test_dumpcheck.py`:

```python
def test_backup_script_exits_2_when_required_env_is_missing():
    """A misconfigured job must fail fast with exit code 2, not run pg_dump.

    Also proves the Azure SDKs are imported *after* the config guard: this runs
    on a machine where azure-storage-blob isn't installed.
    """
    import os
    import subprocess
    import sys
    from pathlib import Path

    script = Path(__file__).with_name("backup.py")
    env = {k: v for k, v in os.environ.items() if k not in ("PGURL", "STORAGE_ACCOUNT")}
    proc = subprocess.run(
        [sys.executable, str(script)], capture_output=True, text=True, env=env
    )
    assert proc.returncode == 2, f"stdout={proc.stdout!r} stderr={proc.stderr!r}"
    assert "PGURL" in proc.stderr
```

- [ ] **Step 2: Run it to verify it fails**

```powershell
uv run --no-project --with pytest pytest infra/backup/test_dumpcheck.py -k exits_2 -v
```

Expected: FAIL — `backup.py` does not exist yet (the subprocess exits non-2 with a "can't open file" error).

- [ ] **Step 3: Write `infra/backup/backup.py`**

```python
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
```

- [ ] **Step 4: Run the test to verify it passes**

```powershell
uv run --no-project --with pytest pytest infra/backup/test_dumpcheck.py -v
```

Expected: 16 passed (the new config-guard test included).

- [ ] **Step 5: Write the Dockerfile**

Create `infra/backup/Dockerfile`:

```dockerfile
# Image for the ai-enablement-hub database backup/restore jobs.
# Base is the official postgres 18 image so pg_dump/pg_restore match the
# server's major version (pg_dump refuses to dump from a NEWER server).
# Build context is this directory: `az acr build ... infra/backup`.
FROM postgres:18

RUN apt-get update \
 && apt-get install -y --no-install-recommends python3-minimal python3-pip \
 && pip3 install --no-cache-dir --break-system-packages azure-identity azure-storage-blob \
 && apt-get purge -y python3-pip \
 && apt-get autoremove -y \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY dumpcheck.py backup.py restore.py ./
USER postgres
ENTRYPOINT ["python3", "backup.py"]
```

- [ ] **Step 6: Write `infra/backup/README.md`**

```markdown
# Database backup & restore jobs

Two Azure Container Apps Jobs, one image, in RG `imaginemore-playground`:

| Job | Trigger | Entrypoint | What it does |
|---|---|---|---|
| `ai-enablement-hub-db-backup` | schedule `30 2 * * *` (UTC) | `backup.py` | dump → verify → upload to `db-backups` → prune >30 d |
| `ai-enablement-hub-db-restore` | manual | `restore.py` | download a dump → `pg_restore` into a target database |

**Operations (freshness check, restoring, the drill) live in
[`docs/db-backup-restore.md`](../../docs/db-backup-restore.md).** This file is
only about the code and the image.

## Layout

- `dumpcheck.py` — pure logic (verification, blob naming, prune selection). Unit-tested.
- `backup.py` / `restore.py` — thin I/O shells around it; these two run in the container.
- `Dockerfile` — `postgres:18` + python3 + `azure-identity`/`azure-storage-blob`.

These run *locally* via `uv run` (no Postgres client needed, PEP 723 deps inline):

- `verify_restore.py` — compares a restored database to live, table by table.
- `drill_db.py` — `--check` / `--create` / `--drop` the scratch database.
- `copy_lesson.py` — copy one lesson's `content_blocks` restored → live (dry run by default).

Deliberately separate from the app image: an app deploy can't change the
backup's `pg_dump`, and a backup change can't break the app build.

## Tests

```powershell
uv run --no-project --with pytest pytest infra/backup/test_dumpcheck.py -v
```

## Rebuild and roll the jobs (after changing any .py here)

```powershell
$env:PYTHONIOENCODING='utf-8'
$az  = 'C:\Program Files\Microsoft SDKs\Azure\CLI2\wbin\az.cmd'
$tag = "ai-enablement-hub-db-backup:" + (Get-Date -Format 'yyyyMMdd-HHmmss')
& $az acr build --registry ca530fc7463eacr --image $tag --platform linux/amd64 `
    --file infra/backup/Dockerfile infra/backup
& $az containerapp job update -n ai-enablement-hub-db-backup  -g imaginemore-playground --image "ca530fc7463eacr.azurecr.io/$tag"
& $az containerapp job update -n ai-enablement-hub-db-restore -g imaginemore-playground --image "ca530fc7463eacr.azurecr.io/$tag"
```

Both jobs always run the same tag — roll them together.
```

- [ ] **Step 7: Commit**

```powershell
git add infra/backup/backup.py infra/backup/Dockerfile infra/backup/README.md infra/backup/test_dumpcheck.py
git commit -m "feat(backup): nightly dump/verify/upload/prune job + image"
```

---

### Task 3: Restore entrypoint (`restore.py`) + local operator scripts

**Files:**
- Create: `infra/backup/restore.py`
- Create: `infra/backup/verify_restore.py`
- Create: `infra/backup/drill_db.py`
- Create: `infra/backup/copy_lesson.py`

**Interfaces:**
- Consumes: `dumpcheck.parse_backup_ts` (Task 1); the image and blob layout from Task 2.
- Produces:
  - Container entrypoint `python3 restore.py` with env `PGURL_TARGET`, `STORAGE_ACCOUNT`, `BLOB_CONTAINER`, `BLOB_PREFIX`, `SOURCE_BLOB` (empty ⇒ latest), `RESTORE_TABLE` (empty ⇒ whole database); exit codes `0` / `2` config / `3` download / `4` restore.
  - `uv run infra/backup/verify_restore.py --live <dsn> --restored <dsn> [--lesson-id <uuid>]`
  - `uv run infra/backup/drill_db.py --check | --create | --drop` (reads `LIVE_DSN`)
  - `uv run infra/backup/copy_lesson.py --lesson-id <uuid> [--apply]` (reads `RESTORED_DSN` + `LIVE_DSN`)

**Why the two extra local scripts:** every operator action here needs SQL with
`"quoted-identifiers"` and `$1` placeholders, which is a quoting minefield inside
PowerShell `python -c` one-liners (`$1` silently expands to empty in a double-quoted
PowerShell string). Committed scripts remove that whole failure class from the runbook,
and the drill exercises them.

**Env-var names used throughout Tasks 3–6 and the runbook** (set them once per shell,
never echo them):
- `LIVE_DSN` — `ai_hub_owner` DSN for the live `ai-enablement-hub` database.
- `RESTORED_DSN` — same credentials, `dbname=ai-enablement-hub-restoredrill`.

- [ ] **Step 1: Write `infra/backup/restore.py`**

```python
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
```

- [ ] **Step 2: Write `infra/backup/verify_restore.py`**

```python
# /// script
# requires-python = ">=3.11"
# dependencies = ["asyncpg~=0.30"]
# ///
"""Compare a restored database against live, from a machine with no psql.

    uv run infra/backup/verify_restore.py --live "<dsn>" --restored "<dsn>" \
        [--lesson-id <uuid>]

Prints a per-table row-count comparison and, when --lesson-id is given, a deep
comparison of that lesson's content_blocks. Exits non-zero on a STRUCTURAL
problem (a table missing from the restore, or empty in the restore while live
has rows). Row-count deltas on progress/session tables are expected and are
reported, not failed — live keeps moving after the dump was taken.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import uuid

import asyncpg

TABLES_SQL = """
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
ORDER BY table_name
"""


async def snapshot(dsn: str) -> dict[str, int]:
    conn = await asyncpg.connect(dsn)
    try:
        names = [r["table_name"] for r in await conn.fetch(TABLES_SQL)]
        counts = {}
        for name in names:
            counts[name] = await conn.fetchval(f'SELECT count(*) FROM "{name}"')
        return counts
    finally:
        await conn.close()


async def lesson_blocks(dsn: str, lesson_id: str):
    conn = await asyncpg.connect(dsn)
    try:
        # lessons.id is a uuid column — asyncpg wants a uuid.UUID, not a str.
        return await conn.fetchval(
            "SELECT content_blocks FROM lessons WHERE id = $1", uuid.UUID(lesson_id)
        )
    finally:
        await conn.close()


def as_json(value):
    if isinstance(value, str):
        return json.loads(value)
    return value


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--live", required=True)
    parser.add_argument("--restored", required=True)
    parser.add_argument("--lesson-id")
    args = parser.parse_args()

    live, restored = await asyncio.gather(snapshot(args.live), snapshot(args.restored))

    print(f"{'table':<32}{'restored':>10}{'live':>10}{'delta':>10}")
    failures = []
    for name in sorted(set(live) | set(restored)):
        rest_n = restored.get(name)
        live_n = live.get(name)
        shown_rest = "MISSING" if rest_n is None else rest_n
        shown_live = "MISSING" if live_n is None else live_n
        delta = "" if rest_n is None or live_n is None else f"{rest_n - live_n:+d}"
        print(f"{name:<32}{str(shown_rest):>10}{str(shown_live):>10}{delta:>10}")
        if rest_n is None and live_n is not None:
            failures.append(f"{name}: missing from the restore")
        elif rest_n == 0 and (live_n or 0) > 0:
            failures.append(f"{name}: empty in the restore but {live_n} rows live")

    if args.lesson_id:
        rest_blocks, live_blocks = await asyncio.gather(
            lesson_blocks(args.restored, args.lesson_id),
            lesson_blocks(args.live, args.lesson_id),
        )
        if rest_blocks is None:
            failures.append(f"lesson {args.lesson_id} missing from the restore")
        elif live_blocks is None:
            print(f"\nlesson {args.lesson_id} does not exist live — pick another id")
        else:
            rest_json, live_json = as_json(rest_blocks), as_json(live_blocks)
            same = rest_json == live_json
            print(
                f"\nlesson {args.lesson_id}: restored {len(rest_json)} blocks, "
                f"live {len(live_json)} blocks, identical={same}"
            )
            if not same:
                print("(a difference here is expected if the lesson was edited after the dump)")

    if failures:
        print("\nFAILED:")
        for line in failures:
            print(f"  - {line}")
        return 1
    print("\nOK: every live table is present and non-empty in the restore")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
```

- [ ] **Step 3: Write `infra/backup/drill_db.py`**

```python
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
```

- [ ] **Step 4: Write `infra/backup/copy_lesson.py`**

```python
# /// script
# requires-python = ">=3.11"
# dependencies = ["asyncpg~=0.30"]
# ///
"""Copy one lesson's content_blocks from a restored database back into live.

    $env:RESTORED_DSN = '<...dbname=ai-enablement-hub-restoredrill>'
    $env:LIVE_DSN     = '<...dbname=ai-enablement-hub>'
    uv run infra/backup/copy_lesson.py --lesson-id <uuid>           # dry run
    uv run infra/backup/copy_lesson.py --lesson-id <uuid> --apply    # WRITES to live

This is the everyday recovery step: the restore job materializes an old dump into
the scratch database, then this moves one lesson back. Dry run by default.
Postgres cannot query across databases, hence two connections.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import uuid

import asyncpg

SELECT = "SELECT title, content_blocks FROM lessons WHERE id = $1"
UPDATE = "UPDATE lessons SET content_blocks = $2 WHERE id = $1"


def as_json(value):
    if isinstance(value, str):
        return json.loads(value)
    return value


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--lesson-id", required=True)
    parser.add_argument("--apply", action="store_true", help="actually write to LIVE_DSN")
    args = parser.parse_args()

    for var in ("RESTORED_DSN", "LIVE_DSN"):
        if not os.environ.get(var, "").strip():
            print(f"FATAL: set {var} first", file=sys.stderr)
            return 2

    lesson_id = uuid.UUID(args.lesson_id)
    src = await asyncpg.connect(os.environ["RESTORED_DSN"])
    dst = await asyncpg.connect(os.environ["LIVE_DSN"])
    try:
        old = await src.fetchrow(SELECT, lesson_id)
        current = await dst.fetchrow(SELECT, lesson_id)
        if old is None:
            print(f"FATAL: lesson {lesson_id} not in the restored database", file=sys.stderr)
            return 3
        if current is None:
            print(f"FATAL: lesson {lesson_id} not in the live database", file=sys.stderr)
            return 3

        restored_blocks = as_json(old["content_blocks"])
        live_blocks = as_json(current["content_blocks"])
        print(f"lesson: {old['title']}")
        print(f"  restored: {len(restored_blocks)} blocks")
        print(f"  live:     {len(live_blocks)} blocks")
        print(f"  identical: {restored_blocks == live_blocks}")

        if not args.apply:
            print("\ndry run — nothing written. Re-run with --apply to overwrite live.")
            return 0

        await dst.execute(UPDATE, lesson_id, old["content_blocks"])
        print("\napplied: live content_blocks replaced with the restored version")
    finally:
        await src.close()
        await dst.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
```

- [ ] **Step 5: Verify all four scripts parse and self-document**

```powershell
uv run --no-project --with pytest pytest infra/backup/test_dumpcheck.py -v
uv run --no-project python -c "import ast,pathlib; [ast.parse(pathlib.Path(p).read_text()) for p in ['infra/backup/restore.py','infra/backup/verify_restore.py','infra/backup/drill_db.py','infra/backup/copy_lesson.py']]; print('parse ok')"
uv run infra/backup/verify_restore.py --help
uv run infra/backup/drill_db.py --help
uv run infra/backup/copy_lesson.py --help
```

Expected: 16 passed, `parse ok`, and a usage block from each `--help` (which also proves the PEP 723 headers resolve `asyncpg`).

- [ ] **Step 6: Commit**

```powershell
git add infra/backup/restore.py infra/backup/verify_restore.py infra/backup/drill_db.py infra/backup/copy_lesson.py
git commit -m "feat(backup): restore job entrypoint + local verify/drill/copy scripts"
```

---

### Task 4: Provision on Azure and prove the happy path

**Files:** none (infrastructure). Record every observed value — later steps and the runbook need them.

**Interfaces:**
- Consumes: the image contract from Task 2 (`backup.py` env vars, exit codes).
- Produces, for Tasks 5–6: the backup job's resource id, its managed-identity principal id, the observed first-run table count and dump size, and the blob path of the first successful backup.

**Every step here is an Azure mutation — confirm with Matthias before each `az` call that is not a query.**

- [ ] **Step 1: Collect the facts the commands need (read-only, no confirmation)**

```powershell
$env:PYTHONIOENCODING='utf-8'
$az = 'C:\Program Files\Microsoft SDKs\Azure\CLI2\wbin\az.cmd'
& $az account show --query "{sub:id, name:name}" -o json
& $az acr credential show -n ca530fc7463eacr --query "{user:username}" -o json
```

Expected: the "Playground BELU Imagine More" subscription id, and that ACR admin auth is enabled (the app already relies on it).

- [ ] **Step 2: Build the image (confirm first)**

```powershell
$tag = "ai-enablement-hub-db-backup:" + (Get-Date -Format 'yyyyMMdd-HHmmss')
& $az acr build --registry ca530fc7463eacr --image $tag --platform linux/amd64 `
    --file infra/backup/Dockerfile infra/backup
```

Expected: `Run ID ... was successful`. Note the tag — Steps 4 and 6 need it.

- [ ] **Step 3: Create the private blob container (confirm first)**

```powershell
$key = & $az storage account keys list -n aienablementhubmedia -g imaginemore-playground --query "[0].value" -o tsv
& $az storage container create -n db-backups --account-name aienablementhubmedia --account-key $key --public-access off
& $az storage container show -n db-backups --account-name aienablementhubmedia --account-key $key --query "{name:name, public:properties.publicAccess}" -o json
```

Expected: `"public": null` — private. The account key is used only here, from your own shell; the job never gets it.

- [ ] **Step 4: Create the backup job with a system-assigned identity (confirm first)**

Take the `ai_hub_owner` DSN from `db/.env` (never echo it into the transcript; assign it in one line and reuse the variable).

```powershell
$dsn = '<ai_hub_owner DSN from db/.env, with sslmode=require>'
$acrUser = & $az acr credential show -n ca530fc7463eacr --query username -o tsv
$acrPass = & $az acr credential show -n ca530fc7463eacr --query "passwords[0].value" -o tsv
& $az containerapp job create -n ai-enablement-hub-db-backup -g imaginemore-playground `
    --environment imaginemore-playground-cae `
    --trigger-type Schedule --cron-expression "30 2 * * *" `
    --replica-timeout 900 --replica-retry-limit 1 --parallelism 1 --replica-completion-count 1 `
    --image "ca530fc7463eacr.azurecr.io/$tag" --cpu 0.25 --memory 0.5Gi `
    --registry-server ca530fc7463eacr.azurecr.io --registry-username $acrUser --registry-password $acrPass `
    --secrets "backup-database-url=$dsn" `
    --env-vars "PGURL=secretref:backup-database-url" "STORAGE_ACCOUNT=aienablementhubmedia" `
               "BLOB_CONTAINER=db-backups" "BLOB_PREFIX=ai-enablement-hub" "KEEP_DAYS=30" `
               "EXPECTED_TABLE_COUNT=1" "MIN_DUMP_BYTES=1" `
    --mi-system-assigned
```

If this CLI is too old for `--mi-system-assigned`, drop that flag and follow with:

```powershell
& $az containerapp job identity assign -n ai-enablement-hub-db-backup -g imaginemore-playground --system-assigned
```

`EXPECTED_TABLE_COUNT`/`MIN_DUMP_BYTES` start permissive on purpose — Step 7 raises them to real values once a genuine dump has been observed.

- [ ] **Step 5: Grant the identity blob access, container-scoped only (confirm first)**

```powershell
$sub = & $az account show --query id -o tsv
$pid = & $az containerapp job show -n ai-enablement-hub-db-backup -g imaginemore-playground --query identity.principalId -o tsv
$scope = "/subscriptions/$sub/resourceGroups/imaginemore-playground/providers/Microsoft.Storage/storageAccounts/aienablementhubmedia/blobServices/default/containers/db-backups"
& $az role assignment create --assignee-object-id $pid --assignee-principal-type ServicePrincipal `
    --role "Storage Blob Data Contributor" --scope $scope
& $az role assignment list --assignee $pid --query "[].{role:roleDefinitionName, scope:scope}" -o json
```

Expected: exactly one assignment, scoped to `.../containers/db-backups` — not the account, not the resource group. If the scope is wider, delete and redo it: a wider scope would let the job touch lesson media.

- [ ] **Step 6: Create the restore job — manual trigger, same image (confirm first)**

```powershell
& $az containerapp job create -n ai-enablement-hub-db-restore -g imaginemore-playground `
    --environment imaginemore-playground-cae `
    --trigger-type Manual `
    --replica-timeout 1800 --replica-retry-limit 0 --parallelism 1 --replica-completion-count 1 `
    --image "ca530fc7463eacr.azurecr.io/$tag" --cpu 0.5 --memory 1.0Gi `
    --registry-server ca530fc7463eacr.azurecr.io --registry-username $acrUser --registry-password $acrPass `
    --command "python3" "restore.py" `
    --secrets "restore-target-url=placeholder" `
    --env-vars "PGURL_TARGET=secretref:restore-target-url" "STORAGE_ACCOUNT=aienablementhubmedia" `
               "BLOB_CONTAINER=db-backups" "BLOB_PREFIX=ai-enablement-hub" `
    --mi-system-assigned
& $az containerapp job identity assign -n ai-enablement-hub-db-restore -g imaginemore-playground --system-assigned
$rpid = & $az containerapp job show -n ai-enablement-hub-db-restore -g imaginemore-playground --query identity.principalId -o tsv
& $az role assignment create --assignee-object-id $rpid --assignee-principal-type ServicePrincipal `
    --role "Storage Blob Data Reader" --scope $scope
```

If this CLI rejects the multi-token `--command`, use `--command python3 --args restore.py` instead, then confirm with:

```powershell
& $az containerapp job show -n ai-enablement-hub-db-restore -g imaginemore-playground `
    --query "properties.template.containers[0].{command:command, args:args}" -o json
```

The restore job gets **Reader** on the container (it only ever downloads) and its target DSN is a placeholder until Task 6 sets it to the scratch database.

- [ ] **Step 7: Run the backup job manually and record what it produced (confirm first)**

```powershell
& $az containerapp job start -n ai-enablement-hub-db-backup -g imaginemore-playground
& $az containerapp job execution list -n ai-enablement-hub-db-backup -g imaginemore-playground `
    --query "[0].{name:name, status:properties.status, start:properties.startTime}" -o json
```

Poll the execution until it leaves `Running`. Expected: `Succeeded`. Then read the summary line from the logs:

```powershell
& $az containerapp job logs show -n ai-enablement-hub-db-backup -g imaginemore-playground `
    --execution <execution-name> --container ai-enablement-hub-db-backup --tail 50
```

If this CLI lacks `job logs show`, query Log Analytics instead:

```powershell
$ws = & $az containerapp env show -n imaginemore-playground-cae -g imaginemore-playground --query properties.appLogsConfiguration.logAnalyticsConfiguration.customerId -o tsv
& $az monitor log-analytics query -w $ws --analytics-query "ContainerAppConsoleLogs_CL | where ContainerGroupName_s startswith 'ai-enablement-hub-db-backup' | order by TimeGenerated desc | take 50 | project TimeGenerated, Log_s" -o table
```

Record from the `OK dump=... bytes=... tables=...` line: **the blob path, the byte size and the table count.** Confirm the blobs exist:

```powershell
& $az storage blob list -c db-backups --account-name aienablementhubmedia --account-key $key `
    --prefix ai-enablement-hub/ --query "[].{name:name, bytes:properties.contentLength}" -o table
```

Expected: one `.dump` and one `globals-*.sql` at today's date partition.

- [ ] **Step 8: Tighten the verification thresholds to real values (confirm first)**

Using the observed numbers: `EXPECTED_TABLE_COUNT` = observed tables − 2, `MIN_DUMP_BYTES` = observed bytes ÷ 2.

```powershell
& $az containerapp job update -n ai-enablement-hub-db-backup -g imaginemore-playground `
    --set-env-vars "EXPECTED_TABLE_COUNT=<observed-2>" "MIN_DUMP_BYTES=<observed/2>"
& $az containerapp job show -n ai-enablement-hub-db-backup -g imaginemore-playground `
    --query "properties.template.containers[0].env" -o json
```

- [ ] **Step 9: Prove pruning deletes only old backups (confirm first)**

Upload three synthetic blobs — one old backup, one old *non*-backup, one recent backup — then run the job and check what survived.

```powershell
$tmp = Join-Path $env:TEMP 'synthetic.txt'
"synthetic" | Out-File -Encoding ascii $tmp
$old = "ai-enablement-hub/2026/01/15/ai-enablement-hub-20260115T023000Z.dump"
$decoy = "ai-enablement-hub/2026/01/15/operator-notes.txt"
$recent = "ai-enablement-hub/2026/07/28/ai-enablement-hub-20260728T023000Z.dump"
foreach ($n in $old, $decoy, $recent) {
  & $az storage blob upload -c db-backups --account-name aienablementhubmedia --account-key $key `
      -n $n -f $tmp --overwrite
}
& $az containerapp job start -n ai-enablement-hub-db-backup -g imaginemore-playground
# after it succeeds:
& $az storage blob list -c db-backups --account-name aienablementhubmedia --account-key $key `
    --prefix ai-enablement-hub/ --query "[].name" -o tsv
```

Expected: `$old` is gone; `$decoy` and `$recent` are still there; the two real dumps from Steps 7 and 9 are there. Then delete the two leftover synthetics:

```powershell
foreach ($n in $decoy, $recent) {
  & $az storage blob delete -c db-backups --account-name aienablementhubmedia --account-key $key -n $n
}
```

- [ ] **Step 10: Record the results in the plan and move on**

Tick the boxes above with the observed numbers written next to them (table count, dump bytes, blob paths, execution names). Task 6's runbook quotes these.

---

### Task 5: Failure alerting, proven by a real failure

**Files:** none (infrastructure).

**Interfaces:**
- Consumes: the backup job resource from Task 4.
- Produces: an action group and an alert rule; a confirmed email in Matthias's inbox.

- [ ] **Step 1: Check which metrics the job actually exposes (read-only)**

```powershell
$jobId = & $az containerapp job show -n ai-enablement-hub-db-backup -g imaginemore-playground --query id -o tsv
& $az monitor metrics list-definitions --resource $jobId `
    --query "[].{name:name.value, dims:join(',', dimensions[].value)}" -o table
```

Expected: a `JobExecutionCount` metric with a `Status` dimension. **If it is absent, use the fallback in Step 3** — the requirement is "a failed run emails Matthias", not a specific metric.

- [ ] **Step 2: Create the action group (confirm first)**

```powershell
& $az monitor action-group create -n ai-hub-backup-alerts -g imaginemore-playground `
    --short-name hubbackup --action email matthias matthias.danneel@delaware.pro
$agId = & $az monitor action-group show -n ai-hub-backup-alerts -g imaginemore-playground --query id -o tsv
```

Expected: Azure sends a "you were added to an action group" confirmation email — the first proof the channel works.

- [ ] **Step 3: Create the alert rule (confirm first)**

Metric path (preferred):

```powershell
& $az monitor metrics alert create -n ai-hub-db-backup-failed -g imaginemore-playground `
    --scopes $jobId --action $agId --severity 1 `
    --window-size 24h --evaluation-frequency 1h `
    --condition "total JobExecutionCount >= 1 where Status includes Failed" `
    --description "Nightly ai-enablement-hub database backup failed. Runbook: docs/db-backup-restore.md"
```

Activity-log fallback, if Step 1 showed no usable metric:

```powershell
& $az monitor activity-log alert create -n ai-hub-db-backup-failed -g imaginemore-playground `
    --scope $jobId --action-group $agId `
    --condition category=ResourceHealth `
    --description "Nightly ai-enablement-hub database backup failed. Runbook: docs/db-backup-restore.md"
```

Record which path was used — the runbook must describe the one that exists.

- [ ] **Step 4: Force a real failure and confirm the alert (confirm first)**

Make verification fail without breaking anything: demand more tables than the database has.

```powershell
& $az containerapp job update -n ai-enablement-hub-db-backup -g imaginemore-playground `
    --set-env-vars "EXPECTED_TABLE_COUNT=9999"
& $az containerapp job start -n ai-enablement-hub-db-backup -g imaginemore-playground
```

Expected: the execution ends `Failed`; the logs show `FATAL: dump lists N TABLE DATA entries, expected >= 9999`; **no new blob was uploaded** (verify with `az storage blob list` — the count is unchanged); an alert email arrives (metric alerts can take up to ~15 minutes).

- [ ] **Step 5: Restore the real threshold and confirm green (confirm first)**

```powershell
& $az containerapp job update -n ai-enablement-hub-db-backup -g imaginemore-playground `
    --set-env-vars "EXPECTED_TABLE_COUNT=<observed-2>"
& $az containerapp job start -n ai-enablement-hub-db-backup -g imaginemore-playground
```

Expected: `Succeeded`, and a new dump blob appears. **Do not leave 9999 in place** — double-check the env with `az containerapp job show ... --query "properties.template.containers[0].env"`.

---

### Task 6: Restore drill + runbook + CLAUDE.md

**Files:**
- Create: `docs/db-backup-restore.md`
- Modify: `CLAUDE.md` (Deployment section — add one "Backups" bullet)

**Interfaces:**
- Consumes: everything above — the jobs, the blob paths, `verify_restore.py`, the alert path chosen in Task 5.
- Produces: the runbook, with the drill's real numbers in it.

- [ ] **Step 1: Check whether `ai_hub_owner` may create databases (read-only)**

Set the DSNs for this shell first, from `db/.env` (assign, never echo):

```powershell
$env:LIVE_DSN     = '<ai_hub_owner DSN, dbname=ai-enablement-hub, sslmode=require>'
$env:RESTORED_DSN = '<same credentials, dbname=ai-enablement-hub-restoredrill>'
uv run infra/backup/drill_db.py --check
```

Expected: `connected as ai_hub_owner: rolcreatedb=... rolsuper=...` and `exists: False`. If `rolcreatedb=True`, Step 2 works as written; if `False`, run the same `CREATE DATABASE` as the Entra admin instead (token: `az account get-access-token --resource https://ossrdbms-aad.database.windows.net --query accessToken -o tsv`, user `danneelm@delawareconsulting.com` — recipe in [`db/README.md`](../../../db/README.md)).

If the connection is refused rather than rejected, the cause is the PG firewall (the recorded dev rule is `matthias-20260708` = 151.248.52.105 and your IP may have changed since). Adding a firewall rule is an Azure mutation — confirm first.

- [ ] **Step 2: Create the scratch database (confirm first)**

```powershell
uv run infra/backup/drill_db.py --create
uv run infra/backup/drill_db.py --check
```

Expected: `created ai-enablement-hub-restoredrill`, then `exists: True`.

- [ ] **Step 3: Point the restore job at the scratch database and run it (confirm first)**

```powershell
& $az containerapp job secret set -n ai-enablement-hub-db-restore -g imaginemore-playground `
    --secrets "restore-target-url=$env:RESTORED_DSN"
& $az containerapp job start -n ai-enablement-hub-db-restore -g imaginemore-playground
& $az containerapp job execution list -n ai-enablement-hub-db-restore -g imaginemore-playground `
    --query "[0].{name:name, status:properties.status}" -o json
```

Expected: execution `Succeeded`, logs ending `OK restored whole database from ai-enablement-hub/...dump`. (`SOURCE_BLOB` is unset, so it picks the newest dump.)

- [ ] **Step 4: Verify the restore against live from this machine**

Pick a lesson id that has not been edited today (any row from `SELECT id, title FROM lessons LIMIT 5`):

```powershell
uv run infra/backup/verify_restore.py --live "$env:LIVE_DSN" --restored "$env:RESTORED_DSN" --lesson-id <lesson uuid>
```

Expected: every live table present and non-empty in the restore; `OK` and exit 0. Row-count deltas on `lesson_progress`, `auth_sessions`, `conversations` and similar are expected and printed — live keeps moving after the dump was taken. Copy the printed table; it goes into the runbook.

Then dry-run the everyday recovery path, to prove the tool the runbook tells you to reach for actually works:

```powershell
uv run infra/backup/copy_lesson.py --lesson-id <same uuid>
```

Expected: block counts for both sides, `identical: True`, and `dry run — nothing written`. **Do not pass `--apply`** during the drill — there is nothing to recover.

- [ ] **Step 5: Write `docs/db-backup-restore.md`**

Content, with the real values from Tasks 4–5 filled in where marked:

```markdown
# Database backups & restore runbook

**What protects the `ai-enablement-hub` database**

| Layer | Covers | Window | Granularity |
|---|---|---|---|
| Azure PITR (server-level, untouched by us) | server/infrastructure loss, "restore to 14:32 yesterday" | 7 days | whole server → NEW server |
| Nightly logical dumps (this runbook) | bad edits, bad migrations, bad scripts, older mistakes | 30 days | one table, one row, or the whole DB |

Design: [`docs/superpowers/specs/2026-07-29-database-backups-design.md`](superpowers/specs/2026-07-29-database-backups-design.md).
Code: [`infra/backup/`](../infra/backup/README.md).

## Is the backup healthy?

```powershell
$env:PYTHONIOENCODING='utf-8'
$az  = 'C:\Program Files\Microsoft SDKs\Azure\CLI2\wbin\az.cmd'
$key = & $az storage account keys list -n aienablementhubmedia -g imaginemore-playground --query "[0].value" -o tsv
& $az storage blob list -c db-backups --account-name aienablementhubmedia --account-key $key `
    --prefix ai-enablement-hub/ --query "[-2:].{name:name, bytes:properties.contentLength}" -o table
```

The newest entry should be dated **today or yesterday** (the job runs 02:30 UTC).
A *failed* run emails matthias.danneel@delaware.pro (<ALERT PATH FROM TASK 5>);
a job that never runs at all is what this manual check catches, so run it
occasionally — after any Azure work on the container-apps environment especially.

Typical size: **<OBSERVED BYTES>** for **<OBSERVED TABLE COUNT>** tables (2026-07-29).

## Restore path 1 — one table (the common case: undo a bad content edit)

1. Find the dump from before the damage (`az storage blob list` as above).
2. Make sure the scratch database exists, then restore into it — never into prod:

```powershell
& $az containerapp job secret set -n ai-enablement-hub-db-restore -g imaginemore-playground `
    --secrets "restore-target-url=<DSN with dbname=ai-enablement-hub-restoredrill>"
& $az containerapp job update -n ai-enablement-hub-db-restore -g imaginemore-playground `
    --set-env-vars "SOURCE_BLOB=ai-enablement-hub/2026/07/10/ai-enablement-hub-20260710T023000Z.dump" "RESTORE_TABLE=lessons"
& $az containerapp job start -n ai-enablement-hub-db-restore -g imaginemore-playground
```

3. Copy the row across. Both databases sit on the same server, but Postgres
   cannot query across databases, so this holds two connections. Dry run first:

```powershell
$env:LIVE_DSN     = '<ai_hub_owner DSN, dbname=ai-enablement-hub>'
$env:RESTORED_DSN = '<same credentials, dbname=ai-enablement-hub-restoredrill>'
uv run infra/backup/copy_lesson.py --lesson-id <lesson uuid>           # shows the diff, writes nothing
uv run infra/backup/copy_lesson.py --lesson-id <lesson uuid> --apply    # writes to live
```

4. Check the lesson in the app, then clear the job's overrides so the next manual
   start doesn't silently reuse them:
   `az containerapp job update -n ai-enablement-hub-db-restore -g imaginemore-playground --set-env-vars "SOURCE_BLOB=" "RESTORE_TABLE="`.

## Restore path 2 — the whole database

Same as path 1 without `RESTORE_TABLE`, into a freshly created empty database.
Then either repoint the app (`az containerapp update -n ai-enablement-hub -g
imaginemore-playground --set-env-vars ...`, and its `database-password` /
`alembic-database-url` secrets) or copy tables across. Restoring **over** the
live database is not supported by this job on purpose — create a new database
and switch.

## Restore path 3 — the server is gone

1. Create a new PG 18 flexible server (ask before provisioning).
2. Apply the matching `globals-*.sql` to recreate roles (`--no-role-passwords`
   means passwords are NOT in it — set them from `db/.env`, or rotate with
   `uv run db/provision_roles.py --rotate-passwords`).
3. Create the `ai-enablement-hub` database and run the restore job against it
   (update its target secret first).
4. Re-run `uv run db/provision_roles.py` for the default privileges that keep
   `ai_hub_app` working without GRANTs in migrations.
5. Update the app's DB secrets and redeploy.

## Drill result (2026-07-29)

<PASTE the verify_restore.py comparison table, and note the lesson id used and
that content_blocks matched.>

Scratch database `ai-enablement-hub-restoredrill` was dropped afterwards.
Re-run the drill after any change to `infra/backup/` or the storage layout.

## Known limitations (accepted)

- Backups live in `aienablementhubmedia`, which is **LRS** — a Sweden Central
  regional loss takes app, database and backups together. Upgrade if that
  matters: `az storage account update -n aienablementhubmedia -g imaginemore-playground --sku Standard_GRS` (non-disruptive).
- Up to ~24 h of learner progress could be lost if PITR is unavailable too.
- **Lesson media blobs are not backed up.** A deleted media blob is gone unless
  blob soft-delete gets enabled on the account.
- Role passwords are not in the globals dump (see path 3).
- The pending hosting move will require recreating both jobs, their identities
  and the role assignments in the new environment.
```

- [ ] **Step 6: Drop the scratch database (confirm first)**

```powershell
uv run infra/backup/drill_db.py --drop
uv run infra/backup/drill_db.py --check
```

Expected: `dropped ai-enablement-hub-restoredrill`, then `exists: False`.

Then reset the restore job's target secret to `placeholder` so a stray manual start cannot write anywhere real:

```powershell
& $az containerapp job secret set -n ai-enablement-hub-db-restore -g imaginemore-playground `
    --secrets "restore-target-url=placeholder"
```

- [ ] **Step 7: Add the `CLAUDE.md` entry**

In the Deployment section, after the "Secrets" bullet, add:

```markdown
- **Backups (2026-07-29):** the prod DB is dumped nightly at 02:30 UTC by the Container
  Apps Job `ai-enablement-hub-db-backup` (image built from `infra/backup/`, separate from
  the app image) into the private `db-backups` container on `aienablementhubmedia`,
  30-day retention, pruned by the job itself. Failures email Matthias. Restores run via
  the manual job `ai-enablement-hub-db-restore` — **there are no Postgres client tools on
  the dev machine**, so never assume a local `pg_restore`. Runbook (incl. the verified
  restore drill): `docs/db-backup-restore.md`. Azure PITR on the shared server stays at
  its default 7 days and is deliberately not touched.
```

- [ ] **Step 8: Commit**

```powershell
git add docs/db-backup-restore.md CLAUDE.md
git commit -m "docs(backup): restore runbook with verified drill results"
```

- [ ] **Step 9: Final verification sweep**

```powershell
uv run --no-project --with pytest pytest infra/backup/test_dumpcheck.py -v
& $az containerapp job show -n ai-enablement-hub-db-backup -g imaginemore-playground `
    --query "{image:properties.template.containers[0].image, cron:properties.configuration.scheduleTriggerConfig.cronExpression, env:properties.template.containers[0].env}" -o json
& $az storage blob list -c db-backups --account-name aienablementhubmedia --account-key $key --prefix ai-enablement-hub/ --query "[].name" -o tsv
& $az role assignment list --assignee $pid --query "[].{role:roleDefinitionName, scope:scope}" -o json
git status --porcelain
```

Confirm: tests green; cron `30 2 * * *`; `EXPECTED_TABLE_COUNT` is the real value (**not 9999, not 1**); only real dumps and no leftover synthetic blobs in the container; the role assignment is container-scoped; and `git status` shows no stray files from this work (other sessions' untracked files stay untracked).

---

## Deviations from the spec, recorded

1. **Restores run in Azure, not locally** (a second manually-triggered job, `ai-enablement-hub-db-restore`, from the same image). Cause: no `pg_restore`/`psql`/Docker on the maintainer's machine. The spec's §8 has been amended.
2. **Row-level verification and cherry-picking happen locally over `asyncpg`** (`verify_restore.py`), which needs no Postgres binaries — this is what makes path 1 usable without an install.
3. **The restore job holds `Storage Blob Data Reader`**, not Contributor: it only downloads.
4. **The negative test uses `EXPECTED_TABLE_COUNT=9999`, not a broken DSN** (spec acceptance criteria said broken DSN). Same proof — verification fails, exit is non-zero, nothing is uploaded — without editing a secret that holds real credentials, so there is no window where the job carries a mangled DSN.
5. **Two extra committed local scripts** (`drill_db.py`, `copy_lesson.py`) beyond the spec's file list, because the runbook's SQL cannot be safely inlined into PowerShell one-liners (`$1` expands to empty in a double-quoted PowerShell string).
