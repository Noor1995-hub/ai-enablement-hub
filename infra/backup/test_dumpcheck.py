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
