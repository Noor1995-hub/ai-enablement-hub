"""Migration-day parity check (design-backend.md §5, step 3).

Re-scores every migrated `complete` survey_responses row with the Python port
and diffs the result against the stored rung/level/band/flag columns from the
old app. Read-only; exits 1 on any mismatch.

Run from backend/ (uses DATABASE__* from .env):
    uv run python scripts/rescore_parity.py
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from src.core.dependencies.settings import get_settings
from src.db.models import SurveyResponse
from src.services.scoring import ScoringError, score_response

SCORED_FIELDS = (
    "score_level",
    "c1_rung",
    "c2_rung",
    "c3_rung",
    "c4_rung",
    "c5_rung",
    "c6_rung",
    "have_count",
    "adv_count",
    "safety_flag",
    "mandatory_modules",
    "usage_band",
)


async def main() -> int:
    settings = get_settings()
    engine = create_async_engine(settings.database.url.get_secret_value())
    mismatches = 0
    unscored = 0
    compared = 0
    try:
        async with AsyncSession(engine) as session:
            rows = (
                (
                    await session.execute(
                        select(SurveyResponse).where(SurveyResponse.status == "complete")
                    )
                )
                .scalars()
                .all()
            )
            print(f"re-scoring {len(rows)} complete survey response(s)...")
            for row in rows:
                try:
                    scores = score_response(
                        {
                            "c1_code": row.c1_code,
                            "c2_code": row.c2_code,
                            "c3_code": row.c3_code,
                            "c4_code": row.c4_code,
                            "c5_codes": row.c5_codes,
                            "c6_code": row.c6_code,
                            "b_freq": row.b_freq,
                            "b_breadth": row.b_breadth,
                        }
                    )
                except ScoringError as exc:
                    print(f"  MISMATCH {row.id} (user {row.user_id}): scorer raised {exc.message}")
                    mismatches += 1
                    continue
                if row.scored_at is None and all(
                    getattr(row, field) is None for field in SCORED_FIELDS
                ):
                    # Legacy anomaly (B3 class): marked complete but the old app
                    # never persisted scores. Nothing to be at parity with.
                    unscored += 1
                    print(
                        f"  UNSCORED-IN-LEGACY {row.id} (user {row.user_id}): "
                        f"Python scores it as {scores['score_level']!r} "
                        f"(band {scores['usage_band']!r}) — consider a manual backfill"
                    )
                    continue
                compared += 1
                diffs = {
                    field: (getattr(row, field), scores[field])
                    for field in SCORED_FIELDS
                    if getattr(row, field) != scores[field]
                }
                if diffs:
                    mismatches += 1
                    print(f"  MISMATCH {row.id} (user {row.user_id}):")
                    for field, (stored, computed) in diffs.items():
                        print(f"    {field}: stored={stored!r} computed={computed!r}")
    finally:
        await engine.dispose()

    print(f"compared: {compared}, unscored-in-legacy: {unscored}, mismatches: {mismatches}")
    if mismatches:
        print("FAIL: stored legacy scores differ from the Python scorer")
        return 1
    print("OK: every row the legacy app scored matches the Python scorer exactly")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
