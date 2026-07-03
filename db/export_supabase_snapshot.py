# /// script
# requires-python = ">=3.12"
# dependencies = ["httpx>=0.28"]
# ///
"""Export a full data snapshot of the Supabase project via PostgREST.

Reads every public table with the service-role key and writes one JSON file per
table under db/baseline/data/, plus a manifest with row counts and export time.
The snapshot is the source for migrate_supabase_to_azure.py and doubles as the
rollback/baseline artifact (the Supabase project itself stays live untouched).

Credentials: SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY env vars; falls back to
parsing the old app's env file at ../app/.env.local (repo-relative).

Usage:
    uv run export_supabase_snapshot.py [--out db/baseline/data]
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import httpx

# FK-safe load order — the migration script inserts in this order.
TABLES = [
    "companies",
    "projects",
    "project_component_settings",
    "users",
    "tracks",
    "curricula",
    "modules",
    "module_prerequisites",
    "lessons",
    "user_tracks",
    "user_modules",
    "survey_responses",
    "lesson_progress",
    "invite_tokens",  # exported for the record; NOT migrated (stale Supabase links)
]

PAGE_SIZE = 500


def load_credentials() -> tuple[str, str]:
    import os

    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if url and key:
        return url, key

    env_file = Path(__file__).resolve().parents[2] / "app" / ".env.local"
    if env_file.exists():
        values: dict[str, str] = {}
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                values[k.strip()] = v.strip()
        url = url or values.get("SUPABASE_URL")
        key = key or values.get("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        sys.exit("Missing SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY (env or app/.env.local)")
    return url, key


def fetch_table(client: httpx.Client, base: str, table: str) -> list[dict]:
    rows: list[dict] = []
    offset = 0
    while True:
        resp = client.get(
            f"{base}/rest/v1/{table}",
            params={"select": "*", "limit": PAGE_SIZE, "offset": offset},
        )
        resp.raise_for_status()
        page = resp.json()
        rows.extend(page)
        if len(page) < PAGE_SIZE:
            return rows
        offset += PAGE_SIZE


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default=str(Path(__file__).parent / "baseline" / "data"))
    args = parser.parse_args()

    url, key = load_credentials()
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    headers = {"apikey": key, "Authorization": f"Bearer {key}"}
    manifest: dict = {
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "source": url,
        "tables": {},
    }

    with httpx.Client(headers=headers, timeout=60) as client:
        for table in TABLES:
            rows = fetch_table(client, url, table)
            path = out_dir / f"{table}.json"
            path.write_text(
                json.dumps(rows, indent=1, ensure_ascii=False, sort_keys=True),
                encoding="utf-8",
            )
            manifest["tables"][table] = len(rows)
            print(f"{table:32s} {len(rows):4d} rows -> {path.name}")

    (out_dir / "_manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )
    print(f"\nManifest written. Total rows: {sum(manifest['tables'].values())}")


if __name__ == "__main__":
    main()
