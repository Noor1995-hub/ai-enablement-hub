# /// script
# requires-python = ">=3.12"
# dependencies = ["psycopg[binary]>=3.2"]
# ///
"""Bring Azure's tracks/modules/lessons/curricula/module_prerequisites content in
line with the Supabase snapshot.

Unlike migrate_supabase_to_azure.py, this touches ONLY these five content tables,
and never TRUNCATEs — safe to run once real users/auth/progress/survey data exist
on Azure. Source: db/baseline/data/*.json (refresh first with
export_supabase_snapshot.py).

For tracks/modules/lessons/curricula, rows are matched by id:
  - present in Supabase but not Azure -> INSERT
  - present in both with different content field(s) -> UPDATE (created_at is
    never touched on existing rows)
  - present in Azure but not Supabase -> reported only, never deleted

module_prerequisites has no id (composite key module_id+prerequisite_module_id)
and is a pure edge list, so it IS reconciled both ways: edges Supabase has that
Azure doesn't are inserted, and edges Azure has that Supabase doesn't are
deleted (the graph is meant to describe exactly the Supabase relation).

Usage:
    uv run sync_content_from_supabase.py               # dry run, prints the plan
    uv run sync_content_from_supabase.py --apply        # writes to Azure
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import psycopg
from psycopg.types.json import Jsonb

DATA_DIR = Path(__file__).parent / "baseline" / "data"
ENV_FILE = Path(__file__).parent / ".env"

TRACK_FIELDS = ["name", "sort_order", "track_type", "color"]
MODULE_FIELDS = ["track_id", "title", "description", "sort_order"]
LESSON_FIELDS = ["module_id", "title", "sort_order", "content_blocks"]
CURRICULA_FIELDS = ["track_id", "name"]


def owner_dsn() -> str:
    for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        if line.startswith("AZURE_PG_OWNER_DSN="):
            return line.partition("=")[2].strip()
    sys.exit("AZURE_PG_OWNER_DSN not found in db/.env")


def load(table: str) -> list[dict]:
    return json.loads((DATA_DIR / f"{table}.json").read_text(encoding="utf-8"))


def plan_and_apply(cur, table: str, fields: list[str], apply: bool) -> dict:
    sb_rows = {r["id"]: r for r in load(table)}

    cur.execute(f'SELECT id, {", ".join(fields)} FROM "{table}"')
    cols = ["id"] + fields

    def normalize(row):
        return {c: (str(v) if hasattr(v, "hex") else v) for c, v in zip(cols, row)}

    az_rows = {str(row[0]): normalize(row) for row in cur.fetchall()}

    to_insert = [i for i in sb_rows if i not in az_rows]
    to_update = [
        i
        for i in sb_rows
        if i in az_rows
        and any(sb_rows[i][f] != az_rows[i][f] for f in fields)
    ]
    only_azure = [i for i in az_rows if i not in sb_rows]

    print(f"\n{table}: {len(to_insert)} to insert, {len(to_update)} to update, "
          f"{len(only_azure)} only-in-azure (not touched)")
    for i in only_azure:
        print(f"    [azure-only, left alone] {i}  {az_rows[i]}")

    if apply:
        jsonb_fields = {"content_blocks"}
        col_list = ["id"] + fields + ["created_at"]
        placeholders = ", ".join(["%s"] * len(col_list))
        update_clause = ", ".join(f"{f} = EXCLUDED.{f}" for f in fields)
        sql = (
            f'INSERT INTO "{table}" ({", ".join(col_list)}) VALUES ({placeholders}) '
            f'ON CONFLICT (id) DO UPDATE SET {update_clause}'
        )
        for i in to_insert + to_update:
            r = sb_rows[i]
            params = [
                Jsonb(r[c]) if c in jsonb_fields else r[c]
                for c in col_list
            ]
            cur.execute(sql, params)

    return {"insert": to_insert, "update": to_update, "azure_only": only_azure}


def plan_and_apply_edges(cur, apply: bool) -> dict:
    """module_prerequisites: composite-key edge list, reconciled both ways."""
    sb_rows = load("module_prerequisites")
    sb_edges = {(r["module_id"], r["prerequisite_module_id"]): r for r in sb_rows}

    cur.execute("SELECT module_id, prerequisite_module_id FROM module_prerequisites")

    def s(v):
        return str(v) if hasattr(v, "hex") else v

    az_edges = {(s(m), s(p)) for m, p in cur.fetchall()}

    to_insert = sorted(set(sb_edges) - az_edges)
    to_delete = sorted(az_edges - set(sb_edges))

    print(f"\nmodule_prerequisites: {len(to_insert)} to insert, {len(to_delete)} to delete "
          f"(edge list, reconciled both ways)")
    for m, p in to_insert:
        print(f"    + module={m} prerequisite={p}")
    for m, p in to_delete:
        print(f"    - module={m} prerequisite={p}")

    if apply:
        for m, p in to_insert:
            r = sb_edges[(m, p)]
            cur.execute(
                "INSERT INTO module_prerequisites (module_id, prerequisite_module_id, created_at) "
                "VALUES (%s, %s, %s) ON CONFLICT DO NOTHING",
                [r["module_id"], r["prerequisite_module_id"], r["created_at"]],
            )
        for m, p in to_delete:
            cur.execute(
                "DELETE FROM module_prerequisites WHERE module_id = %s AND prerequisite_module_id = %s",
                [m, p],
            )

    return {"insert": to_insert, "delete": to_delete}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="write changes to Azure (default: dry run)")
    args = parser.parse_args()

    with psycopg.connect(owner_dsn()) as conn:
        cur = conn.cursor()
        # Sentinel: the frozen Supabase snapshot predates the maturity split
        # (migration b4e5f6a7c8d9). Applying it against the post-split live DB would
        # rename "General I" back to "General", move the split modules' track_id back,
        # and DELETE prerequisite edges the snapshot lacks — silently unwinding the
        # migration. Refuse to --apply once General II exists.
        if args.apply:
            cur.execute("SELECT count(*) FROM tracks WHERE name = 'General II'")
            if cur.fetchone()[0]:
                sys.exit(
                    "REFUSING TO APPLY: a 'General II' track exists, so the maturity split "
                    "(migration b4e5f6a7c8d9) is live. Applying the stale Supabase snapshot "
                    "would unwind it. Run without --apply to inspect the plan."
                )
        summary = {}
        summary["tracks"] = plan_and_apply(cur, "tracks", TRACK_FIELDS, args.apply)
        summary["modules"] = plan_and_apply(cur, "modules", MODULE_FIELDS, args.apply)
        summary["lessons"] = plan_and_apply(cur, "lessons", LESSON_FIELDS, args.apply)
        summary["curricula"] = plan_and_apply(cur, "curricula", CURRICULA_FIELDS, args.apply)
        summary["module_prerequisites"] = plan_and_apply_edges(cur, args.apply)

        if args.apply:
            conn.commit()
            print("\nApplied and committed.")
        else:
            conn.rollback()
            print("\nDRY RUN — no changes written. Re-run with --apply to write to Azure.")

    total_insert = sum(len(s["insert"]) for s in summary.values())
    total_update = sum(len(s.get("update", [])) for s in summary.values())
    total_delete = sum(len(s.get("delete", [])) for s in summary.values())
    print(f"\nTotal: {total_insert} inserts, {total_update} updates, {total_delete} deletes.")


if __name__ == "__main__":
    main()
