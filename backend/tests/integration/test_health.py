"""`/api/health` is the deploy workflow's read-back: it must report the build identity."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.integration


async def test_health_reports_status_and_build_identity(client: AsyncClient) -> None:
    response = await client.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["build_sha"] == "test-sha"  # from the overridden test_settings fixture
    assert body["build_time"] == "2026-01-01T00:00:00Z"
    assert set(body) == {"status", "build_sha", "build_time"}
