"""Maturity-gated learning path (2026-07-08).

Covers the graph's per-track maturity locks + effective maturity_level, the admin
override endpoint (set/clear/change, 404/422, no assignment side effects), and a
migration-sanity check that runs the shipped restructure SQL (General → General I
+ General II) against the real production ids.
"""

from __future__ import annotations

import importlib.util
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

import pytest_asyncio
from sqlalchemy import text

from tests.fixtures.auth import auth_headers
from tests.fixtures.factories import (
    assign_lesson,
    assign_module,
    assign_track,
    complete_lesson,
    create_company,
    create_lesson,
    create_module,
    create_project,
    create_survey,
    create_track,
    create_user,
)

if TYPE_CHECKING:
    from httpx import AsyncClient
    from sqlalchemy.ext.asyncio import AsyncSession

    from src.core.configs.settings import Settings
    from src.db.models import Lesson, Module, Track, User


@dataclass
class MWorld:
    """General I (explore) → General II (practitioner) → a tool track (integrator),
    one assigned module + lesson each. The learner scored Explorer and has an
    admin sitting alongside for the override endpoint."""

    gi: Track
    gii: Track
    tool: Track
    gi_lesson: Lesson
    gii_lesson: Lesson
    tool_lesson: Lesson
    gi_mod: Module
    gii_mod: Module
    tool_mod: Module
    learner: User
    admin: User
    project_id: uuid.UUID


@pytest_asyncio.fixture
async def mworld(db_session: AsyncSession) -> MWorld:
    company = await create_company(db_session, "Maturity Co")
    project = await create_project(db_session, company, "Maturity Project")
    gi = await create_track(db_session, "General I", sort_order=0, required_level="explore")
    gii = await create_track(db_session, "General II", sort_order=1, required_level="practitioner")
    tool = await create_track(
        db_session, "Copilot", sort_order=2, track_type="tool", required_level="integrator"
    )
    gi_mod = await create_module(db_session, gi, "GI Module")
    gii_mod = await create_module(db_session, gii, "GII Module")
    tool_mod = await create_module(db_session, tool, "Tool Module")
    gi_lesson = await create_lesson(db_session, gi_mod, "GI L0")
    gii_lesson = await create_lesson(db_session, gii_mod, "GII L0")
    tool_lesson = await create_lesson(db_session, tool_mod, "Tool L0")

    learner = await create_user(
        db_session,
        email="maturity-learner@example.com",
        company_id=company.id,
        project_id=project.id,
    )
    await create_survey(db_session, learner, status="complete", score_level="explore")
    for track in (gi, gii, tool):
        await assign_track(db_session, learner, track)
    for module in (gi_mod, gii_mod, tool_mod):
        await assign_module(db_session, learner, module)
    for lesson in (gi_lesson, gii_lesson, tool_lesson):
        await assign_lesson(db_session, learner, lesson)

    admin = await create_user(db_session, email="maturity-admin@example.com", role="admin")
    return MWorld(
        gi,
        gii,
        tool,
        gi_lesson,
        gii_lesson,
        tool_lesson,
        gi_mod,
        gii_mod,
        tool_mod,
        learner,
        admin,
        project.id,
    )


def _tracks(graph: dict) -> dict[str, dict]:
    return {t["id"]: t for t in graph["tracks"]}


def _modules(graph: dict) -> dict[str, dict]:
    return {m["id"]: m for m in graph["modules"]}


class TestGraphMaturityLocks:
    async def test_explorer_unlocks_only_general_i(
        self, client: AsyncClient, mworld: MWorld, test_settings: Settings
    ) -> None:
        graph = (
            await client.get(
                "/api/learning/graph", headers=auth_headers(mworld.learner, test_settings)
            )
        ).json()
        assert graph["maturity_level"] == "explore"
        tracks = _tracks(graph)
        assert tracks[str(mworld.gi.id)]["required_level"] == "explore"
        assert tracks[str(mworld.gi.id)]["unlocked_by_maturity"] is True
        assert tracks[str(mworld.gii.id)]["unlocked_by_maturity"] is False
        assert tracks[str(mworld.tool.id)]["unlocked_by_maturity"] is False
        # Modules inherit their track's flag.
        modules = _modules(graph)
        assert modules[str(mworld.gi_mod.id)]["unlocked_by_maturity"] is True
        assert modules[str(mworld.gii_mod.id)]["unlocked_by_maturity"] is False

    async def test_completing_general_i_unlocks_general_ii(
        self, client: AsyncClient, mworld: MWorld, test_settings: Settings
    ) -> None:
        headers = auth_headers(mworld.learner, test_settings)
        # Complete General I's only lesson via the real progress endpoint.
        assert (
            await client.put(
                f"/api/lessons/{mworld.gi_lesson.id}/progress", json={}, headers=headers
            )
        ).status_code == 204

        graph = (await client.get("/api/learning/graph", headers=headers)).json()
        assert graph["maturity_level"] == "practitioner"
        tracks = _tracks(graph)
        assert tracks[str(mworld.gii.id)]["unlocked_by_maturity"] is True
        assert tracks[str(mworld.tool.id)]["unlocked_by_maturity"] is False

    async def test_full_ladder_unlocks_tool_track(
        self, client: AsyncClient, mworld: MWorld, test_settings: Settings
    ) -> None:
        headers = auth_headers(mworld.learner, test_settings)
        for lesson in (mworld.gi_lesson, mworld.gii_lesson):
            await client.put(f"/api/lessons/{lesson.id}/progress", json={}, headers=headers)
        graph = (await client.get("/api/learning/graph", headers=headers)).json()
        assert graph["maturity_level"] == "integrator"
        assert _tracks(graph)[str(mworld.tool.id)]["unlocked_by_maturity"] is True

    async def test_assignments_unchanged_by_maturity(
        self, client: AsyncClient, mworld: MWorld, test_settings: Settings
    ) -> None:
        graph = (
            await client.get(
                "/api/learning/graph", headers=auth_headers(mworld.learner, test_settings)
            )
        ).json()
        # Every assigned track/module stays assigned regardless of lock state.
        tracks = _tracks(graph)
        assert all(tracks[str(t.id)]["assigned"] for t in (mworld.gi, mworld.gii, mworld.tool))
        assert _modules(graph)[str(mworld.gii_mod.id)]["assigned"] is True


class TestAdminOverride:
    async def _learner_row(
        self, client: AsyncClient, mworld: MWorld, test_settings: Settings
    ) -> dict:
        users = (
            await client.get(
                f"/api/admin/users?project_id={mworld.project_id}",
                headers=auth_headers(mworld.admin, test_settings),
            )
        ).json()["users"]
        return next(u for u in users if u["id"] == str(mworld.learner.id))

    async def test_set_override_updates_effective(
        self, client: AsyncClient, mworld: MWorld, test_settings: Settings
    ) -> None:
        resp = await client.put(
            f"/api/admin/users/{mworld.learner.id}/maturity",
            json={"level": "practitioner"},
            headers=auth_headers(mworld.admin, test_settings),
        )
        assert resp.status_code == 204
        row = await self._learner_row(client, mworld, test_settings)
        assert row["maturity_override"] == "practitioner"
        assert row["effective_maturity"] == "practitioner"
        # Maturity never touches assignments.
        assert len(row["assigned_module_ids"]) == 3

    async def test_clear_override_falls_back_to_assessment(
        self, client: AsyncClient, mworld: MWorld, test_settings: Settings
    ) -> None:
        headers = auth_headers(mworld.admin, test_settings)
        await client.put(
            f"/api/admin/users/{mworld.learner.id}/maturity",
            json={"level": "integrator"},
            headers=headers,
        )
        await client.put(
            f"/api/admin/users/{mworld.learner.id}/maturity",
            json={"level": None},
            headers=headers,
        )
        row = await self._learner_row(client, mworld, test_settings)
        assert row["maturity_override"] is None
        assert row["effective_maturity"] == "explore"  # the assessed base

    async def test_low_override_cannot_demote_below_earned(
        self, client: AsyncClient, mworld: MWorld, db_session: AsyncSession, test_settings: Settings
    ) -> None:
        # Learner earns Practitioner by finishing General I, then is pinned back
        # to Explorer — effective re-advances to the earned level.
        await complete_lesson(db_session, mworld.learner, mworld.gi_lesson)
        await client.put(
            f"/api/admin/users/{mworld.learner.id}/maturity",
            json={"level": "explore"},
            headers=auth_headers(mworld.admin, test_settings),
        )
        row = await self._learner_row(client, mworld, test_settings)
        assert row["maturity_override"] == "explore"
        assert row["effective_maturity"] == "practitioner"

    async def test_unknown_user_is_404(
        self, client: AsyncClient, mworld: MWorld, test_settings: Settings
    ) -> None:
        resp = await client.put(
            f"/api/admin/users/{uuid.uuid4()}/maturity",
            json={"level": "explore"},
            headers=auth_headers(mworld.admin, test_settings),
        )
        assert resp.status_code == 404

    async def test_bad_level_is_422(
        self, client: AsyncClient, mworld: MWorld, test_settings: Settings
    ) -> None:
        resp = await client.put(
            f"/api/admin/users/{mworld.learner.id}/maturity",
            json={"level": "wizard"},
            headers=auth_headers(mworld.admin, test_settings),
        )
        assert resp.status_code == 422


# Real production ids the migration keys on (db/baseline/data).
GENERAL_ID = "1a810a92-dce9-4f6f-88e6-b73d63cf65fa"
MOVER_IDS = (
    "8a22da4a-0ce3-4d8f-8713-c5a6ab7082bb",  # Integrating (has the boundary prereq)
    "e2202cbc-e26f-4ed6-a178-27fcdd85abce",
    "4e9f8450-5bbe-47f8-a014-ce3cc41f19d0",
)
USING_AI_SAFELY_ID = "2b509c09-62fb-483b-a1f2-72bd23def106"  # stays in General I


def _load_restructure_sql() -> tuple[str, str]:
    path = (
        Path(__file__).resolve().parents[3]
        / "alembic"
        / "versions"
        / "b4e5f6a7c8d9_maturity_gated_learning_path.py"
    )
    spec = importlib.util.spec_from_file_location("_maturity_migration", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.RESTRUCTURE_SQL, module.GENERAL_II_ID


class TestMigrationRestructure:
    async def test_general_split_and_boundary_prereq_preserved(
        self, db_session: AsyncSession
    ) -> None:
        restructure_sql, general_ii_id = _load_restructure_sql()

        # Seed the PRE-split structure with the real ids (required_level as the
        # migration's POPULATE step would leave it: general=explore, tool=integrator).
        await db_session.execute(
            text(
                "INSERT INTO tracks (id, name, sort_order, track_type, color, required_level) "
                "VALUES (:id, 'General', 0, 'general', '#6366f1', 'explore')"
            ),
            {"id": GENERAL_ID},
        )
        tool_id = uuid.uuid4()
        await db_session.execute(
            text(
                "INSERT INTO tracks (id, name, sort_order, track_type, required_level) "
                "VALUES (:id, 'Copilot', 1, 'tool', 'integrator')"
            ),
            {"id": tool_id},
        )
        # 5 stayers (incl. Using-AI-safely, the boundary prereq source) + 3 movers.
        stayers = [USING_AI_SAFELY_ID, *(str(uuid.uuid4()) for _ in range(4))]
        for i, mid in enumerate(stayers):
            await db_session.execute(
                text(
                    "INSERT INTO modules (id, track_id, title, sort_order) "
                    "VALUES (:id, :tid, :title, :so)"
                ),
                {"id": mid, "tid": GENERAL_ID, "title": f"Stayer {i}", "so": i * 10 + 10},
            )
        for i, mid in enumerate(MOVER_IDS):
            await db_session.execute(
                text(
                    "INSERT INTO modules (id, track_id, title, sort_order) "
                    "VALUES (:id, :tid, :title, :so)"
                ),
                {"id": mid, "tid": GENERAL_ID, "title": f"Mover {i}", "so": 60 + i * 10},
            )
        # Boundary prereq: Integrating (mover) ← Using AI safely (stayer).
        await db_session.execute(
            text(
                "INSERT INTO module_prerequisites (module_id, prerequisite_module_id) "
                "VALUES (:m, :p)"
            ),
            {"m": MOVER_IDS[0], "p": USING_AI_SAFELY_ID},
        )

        await db_session.execute(text(restructure_sql))

        # General → General I (explore), 5 modules kept.
        gi = (
            await db_session.execute(
                text("SELECT name, sort_order, required_level FROM tracks WHERE id = :id"),
                {"id": GENERAL_ID},
            )
        ).one()
        assert gi.name == "General I"
        assert gi.sort_order == 0
        assert gi.required_level == "explore"
        gi_count = (
            await db_session.execute(
                text("SELECT count(*) FROM modules WHERE track_id = :id"), {"id": GENERAL_ID}
            )
        ).scalar_one()
        assert gi_count == 5

        # General II (practitioner), 3 movers.
        gii = (
            await db_session.execute(
                text(
                    "SELECT name, sort_order, track_type, required_level FROM tracks WHERE id = :id"
                ),
                {"id": general_ii_id},
            )
        ).one()
        assert gii.name == "General II"
        assert gii.sort_order == 1
        assert gii.track_type == "general"
        assert gii.required_level == "practitioner"
        gii_count = (
            await db_session.execute(
                text("SELECT count(*) FROM modules WHERE track_id = :id"), {"id": general_ii_id}
            )
        ).scalar_one()
        assert gii_count == 3

        # Tool track pushed down by one, still Integrator.
        tool = (
            await db_session.execute(
                text("SELECT sort_order, required_level FROM tracks WHERE id = :id"),
                {"id": tool_id},
            )
        ).one()
        assert tool.sort_order == 2
        assert tool.required_level == "integrator"

        # Boundary prereq preserved (now a cross-track edge General II ← General I).
        prereq = (
            await db_session.execute(
                text(
                    "SELECT count(*) FROM module_prerequisites "
                    "WHERE module_id = :m AND prerequisite_module_id = :p"
                ),
                {"m": MOVER_IDS[0], "p": USING_AI_SAFELY_ID},
            )
        ).scalar_one()
        assert prereq == 1

    async def test_restructure_is_idempotent(self, db_session: AsyncSession) -> None:
        restructure_sql, general_ii_id = _load_restructure_sql()
        await db_session.execute(
            text(
                "INSERT INTO tracks (id, name, sort_order, track_type, required_level) "
                "VALUES (:id, 'General', 0, 'general', 'explore')"
            ),
            {"id": GENERAL_ID},
        )
        await db_session.execute(text(restructure_sql))
        await db_session.execute(text(restructure_sql))  # replay — guard must no-op
        count = (
            await db_session.execute(
                text("SELECT count(*) FROM tracks WHERE id = :id"), {"id": general_ii_id}
            )
        ).scalar_one()
        assert count == 1
