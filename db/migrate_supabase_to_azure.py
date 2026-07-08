# /// script
# requires-python = ">=3.12"
# dependencies = ["psycopg[binary]>=3.2"]
# ///
"""Load the Supabase baseline snapshot into the Azure PostgreSQL database.

Source: db/baseline/data/*.json (produced by export_supabase_snapshot.py).
Target: the "ai-enablement-hub" database, connected as ai_hub_owner
        (AZURE_PG_OWNER_DSN from db/.env, written by provision_roles.py).

Idempotent TRUNCATE-and-reload in ONE transaction, FK-safe insert order.
Transforms:
  - users: drop auth_id; password_hash=NULL, external_id=NULL, password_set=false
    (everyone is re-invited manually in the new system); email lowercased;
    updated_at coalesced to created_at when null.
  - invite_tokens: NOT migrated (stale Supabase action links).

Built-in verification gates (script exits non-zero if any fails):
  1. Row count per table == snapshot manifest count.
  2. Primary-key-set MD5 equality per table (snapshot vs target).
  3. lessons: total content_blocks element count equal.
  4. users: password_set=false AND password_hash IS NULL everywhere; (email, role)
     pairs preserved.
  5. survey_responses: (user_id, status, score_level, len(c5_codes)) preserved.

Usage:
    uv run migrate_supabase_to_azure.py [--check-only]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import psycopg
from psycopg.types.json import Jsonb

DATA_DIR = Path(__file__).parent / "baseline" / "data"
ENV_FILE = Path(__file__).parent / ".env"

# FK-safe insert order. Values are the explicit target column lists; snapshot rows
# must contain exactly these keys (after transforms) or the script fails loudly.
TABLES: dict[str, list[str]] = {
    "companies": ["id", "name", "created_at"],
    "projects": ["id", "name", "company_id", "created_at"],
    "project_component_settings": [
        "id", "project_id", "component", "locked", "hidden", "updated_at",
    ],
    "users": [
        "id", "email", "first_name", "last_name", "role", "company_id", "project_id",
        "is_active", "password_set", "password_hash", "external_id", "created_at",
        "updated_at",
    ],
    "tracks": ["id", "name", "sort_order", "track_type", "color", "required_level", "created_at"],
    "curricula": ["id", "track_id", "name", "created_at"],
    "modules": ["id", "track_id", "title", "description", "sort_order", "created_at"],
    "module_prerequisites": ["module_id", "prerequisite_module_id", "created_at"],
    "lessons": ["id", "module_id", "title", "sort_order", "content_blocks", "created_at"],
    "user_tracks": ["id", "user_id", "track_id", "assigned_at"],
    "user_modules": ["id", "user_id", "module_id", "assigned_at"],
    "survey_responses": [
        "id", "user_id", "status", "instrument_version", "current_step", "job_title",
        "department", "consent", "c1_code", "c2_code", "c3_code", "c4_code", "c5_codes",
        "c6_code", "b_freq", "b_breadth", "b_setup", "b_tools", "b_barriers",
        "b_attitude", "b_readiness", "q_excitement", "q_timesink", "score_level",
        "c1_rung", "c2_rung", "c3_rung", "c4_rung", "c5_rung", "c6_rung", "have_count",
        "adv_count", "safety_flag", "mandatory_modules", "usage_band", "started_at",
        "completed_at", "scored_at", "updated_at",
    ],
    "lesson_progress": ["id", "user_id", "lesson_id", "completed_at", "answers"],
}

JSONB_COLUMNS = {"content_blocks", "answers"}

# Snapshot keys per table where the pk-set hash uses something other than `id`
PK_KEYS: dict[str, list[str]] = {"module_prerequisites": ["module_id", "prerequisite_module_id"]}


def owner_dsn() -> str:
    for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        if line.startswith("AZURE_PG_OWNER_DSN="):
            return line.partition("=")[2].strip()
    sys.exit("AZURE_PG_OWNER_DSN not found in db/.env — run provision_roles.py first")


def load_snapshot() -> tuple[dict[str, list[dict]], dict]:
    manifest = json.loads((DATA_DIR / "_manifest.json").read_text(encoding="utf-8"))
    data = {
        t: json.loads((DATA_DIR / f"{t}.json").read_text(encoding="utf-8"))
        for t in TABLES
    }
    return data, manifest


def transform_users(rows: list[dict]) -> list[dict]:
    out = []
    for r in rows:
        out.append({
            "id": r["id"],
            "email": r["email"].lower(),
            "first_name": r["first_name"],
            "last_name": r["last_name"],
            "role": r["role"],
            "company_id": r["company_id"],
            "project_id": r["project_id"],
            "is_active": r["is_active"],
            "password_set": False,
            "password_hash": None,
            "external_id": None,
            "created_at": r["created_at"],
            "updated_at": r["updated_at"] or r["created_at"],
        })
    return out


def transform_tracks(rows: list[dict]) -> list[dict]:
    """Derive the maturity-ladder `required_level` (added by the
    maturity-gated-learning migration, NOT NULL). The baseline JSON stays
    pre-split — every general track loads as Explorer here; the migration's
    General I/II split later bumps General II to Practitioner. Adding the column
    VALUE does not change row counts or PK-set hashes, so the verification gates
    below still pass. See db/README.md for the re-seed replay procedure."""
    out = []
    for r in rows:
        out.append({
            **r,
            "required_level": "integrator" if r["track_type"] == "tool" else "explore",
        })
    return out


def pk_hash(rows: list[dict], keys: list[str]) -> str:
    ids = sorted(":".join(str(r[k]) for k in keys) for r in rows)
    return hashlib.md5(",".join(ids).encode()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check-only", action="store_true")
    args = parser.parse_args()

    data, manifest = load_snapshot()
    data["users"] = transform_users(data["users"])
    data["tracks"] = transform_tracks(data["tracks"])

    print(f"Snapshot from {manifest['exported_at']} ({manifest['source']})")
    for t in TABLES:
        expected = manifest["tables"][t]
        if len(data[t]) != expected:
            sys.exit(f"FATAL: {t}: snapshot file has {len(data[t])} rows, manifest says {expected}")
        print(f"  {t:32s} {len(data[t]):4d} rows")
    print(f"  (invite_tokens: {manifest['tables'].get('invite_tokens', 0)} rows — intentionally NOT migrated)")

    if args.check_only:
        print("--check-only: no writes performed.")
        return

    failures: list[str] = []
    with psycopg.connect(owner_dsn()) as conn:
        with conn.transaction():
            cur = conn.cursor()
            truncate_list = ", ".join(f'"{t}"' for t in TABLES) + ", auth_tokens, auth_sessions"
            cur.execute(f"TRUNCATE {truncate_list} CASCADE")
            for t, cols in TABLES.items():
                rows = data[t]
                if not rows:
                    continue
                for r in rows:
                    extra = set(r) - set(cols)
                    missing = set(cols) - set(r)
                    if extra or missing:
                        sys.exit(f"FATAL: {t}: column mismatch extra={extra} missing={missing}")
                placeholders = ", ".join(["%s"] * len(cols))
                col_sql = ", ".join(cols)
                params = [
                    tuple(Jsonb(r[c]) if c in JSONB_COLUMNS else r[c] for c in cols)
                    for r in rows
                ]
                cur.executemany(f'INSERT INTO "{t}" ({col_sql}) VALUES ({placeholders})', params)
                print(f"  loaded {t} ({len(rows)})")

        # ---- verification gates (fresh cursor, committed data) ----
        cur = conn.cursor()
        print("\nVerification:")

        for t in TABLES:
            cur.execute(f'SELECT count(*) FROM "{t}"')
            n = cur.fetchone()[0]
            ok = n == manifest["tables"][t]
            print(f"  [{'OK' if ok else 'FAIL'}] {t}: rows {n} == {manifest['tables'][t]}")
            if not ok:
                failures.append(f"{t} row count {n} != {manifest['tables'][t]}")

        for t in TABLES:
            keys = PK_KEYS.get(t, ["id"])
            cur.execute(f'SELECT {", ".join(keys)} FROM "{t}"')
            db_rows = [dict(zip(keys, row)) for row in cur.fetchall()]
            h_db = pk_hash(db_rows, keys)
            h_snap = pk_hash(data[t], keys)
            if h_db != h_snap:
                failures.append(f"{t} pk-set hash mismatch")
                print(f"  [FAIL] {t}: pk-set hash")
        print("  [OK] pk-set hashes match for all 13 tables" if not any("hash" in f for f in failures) else "")

        cur.execute("SELECT coalesce(sum(jsonb_array_length(content_blocks)), 0) FROM lessons")
        db_blocks = cur.fetchone()[0]
        snap_blocks = sum(len(r["content_blocks"]) for r in data["lessons"])
        ok = db_blocks == snap_blocks
        print(f"  [{'OK' if ok else 'FAIL'}] lessons content_blocks elements: {db_blocks} == {snap_blocks}")
        if not ok:
            failures.append("content_blocks element count mismatch")

        cur.execute("SELECT count(*) FROM users WHERE password_set OR password_hash IS NOT NULL")
        n = cur.fetchone()[0]
        print(f"  [{'OK' if n == 0 else 'FAIL'}] users: all password_set=false, password_hash null ({n} violations)")
        if n:
            failures.append("users not reset for re-invite")

        cur.execute("SELECT email, role FROM users ORDER BY email")
        db_pairs = set(cur.fetchall())
        snap_pairs = {(r["email"], r["role"]) for r in data["users"]}
        ok = db_pairs == snap_pairs
        print(f"  [{'OK' if ok else 'FAIL'}] users: (email, role) pairs preserved")
        if not ok:
            failures.append(f"user pairs diff: {db_pairs ^ snap_pairs}")

        cur.execute("SELECT user_id::text, status, score_level, coalesce(cardinality(c5_codes), -1) FROM survey_responses")
        db_survey = set(cur.fetchall())
        snap_survey = {
            (r["user_id"], r["status"], r["score_level"],
             len(r["c5_codes"]) if r["c5_codes"] is not None else -1)
            for r in data["survey_responses"]
        }
        ok = db_survey == snap_survey
        print(f"  [{'OK' if ok else 'FAIL'}] survey_responses: status/level/c5 preserved")
        if not ok:
            failures.append(f"survey diff: {db_survey ^ snap_survey}")

    if failures:
        print(f"\nMIGRATION FAILED VERIFICATION ({len(failures)}):")
        for f in failures:
            print(" -", f)
        sys.exit(1)
    print("\nAll verification gates passed.")


if __name__ == "__main__":
    main()
