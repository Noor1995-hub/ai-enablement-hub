"""Shared helpers for the apply phase: fresh fetch, safe write, text transform.

All writes go straight to lessons.content_blocks as ai_hub_app. We only ever
change string VALUES inside existing blocks (never add/remove/reorder keys in
the deterministic passes), and we assert the block id/type skeleton is
unchanged before writing, so structure can't drift.
"""

from __future__ import annotations

import json
import os
from collections.abc import Callable

import asyncpg
from dotenv import load_dotenv

from content_qa.blocks import NON_PROSE_KEYS

_ENV_LOADED = False


def _ensure_env() -> None:
    global _ENV_LOADED
    if not _ENV_LOADED:
        from pathlib import Path

        load_dotenv(Path(__file__).resolve().parents[2] / ".env")
        _ENV_LOADED = True


async def connect() -> asyncpg.Connection:
    _ensure_env()
    return await asyncpg.connect(
        host=os.environ["DATABASE__HOST"],
        port=int(os.environ["DATABASE__PORT"]),
        user=os.environ["DATABASE__USERNAME"],
        password=os.environ["DATABASE__PASSWORD"],
        database=os.environ["DATABASE__NAME"],
        ssl="require",
    )


async def fetch_blocks(conn: asyncpg.Connection, lesson_id: str) -> list[dict]:
    raw = await conn.fetchval("SELECT content_blocks FROM lessons WHERE id = $1", lesson_id)
    if raw is None:
        return []
    return json.loads(raw) if isinstance(raw, str) else raw


def skeleton(blocks: list[dict]) -> list[tuple]:
    """The (id, type) list used to assert structure is unchanged by text edits."""
    return [(b.get("id"), b.get("type")) for b in (blocks or [])]


async def write_blocks(conn: asyncpg.Connection, lesson_id: str, blocks: list[dict]) -> None:
    await conn.execute(
        "UPDATE lessons SET content_blocks = $1::jsonb WHERE id = $2",
        json.dumps(blocks, ensure_ascii=False),
        lesson_id,
    )


def transform_texts(node: object, fn: Callable[[str], str]) -> object:
    """Return a copy of node with fn applied to every prose string.

    Mirrors blocks.iter_texts traversal: recurses dict/list, skips NON_PROSE_KEYS,
    applies fn to non-empty strings. Non-prose scalars pass through untouched.
    """
    if isinstance(node, str):
        return fn(node) if node.strip() else node
    if isinstance(node, dict):
        return {k: (v if k in NON_PROSE_KEYS else transform_texts(v, fn)) for k, v in node.items()}
    if isinstance(node, list):
        return [transform_texts(v, fn) for v in node]
    return node
