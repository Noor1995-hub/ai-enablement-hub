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
