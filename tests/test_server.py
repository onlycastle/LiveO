from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from backend.server import app


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.mark.anyio
async def test_stream_status_initial(client: AsyncClient):
    resp = await client.get("/api/stream/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["isLive"] is False


@pytest.mark.anyio
async def test_stream_start_demo_requires_url(client: AsyncClient):
    resp = await client.post("/api/stream/start", json={"source": "demo"})
    assert resp.status_code == 400


@pytest.mark.anyio
async def test_stream_stop_without_start(client: AsyncClient):
    resp = await client.post("/api/stream/stop")
    assert resp.status_code == 400


@pytest.mark.anyio
async def test_candidates_crud(client: AsyncClient):
    resp = await client.get("/api/shorts/candidates")
    assert resp.status_code == 200
    assert resp.json() == []

    resp = await client.post("/api/shorts/candidates", json={
        "startTime": "00:01:00",
        "endTime": "00:01:30",
        "duration": "0:30",
        "title": "Test clip",
        "indicators": ["kill_event"],
        "confidence": 90,
        "isManual": True,
    })
    assert resp.status_code == 201
    data = resp.json()
    cid = data["id"]
    assert data["title"] == "Test clip"
    assert data["status"] == "pending"
    assert data["isManual"] is True

    resp = await client.patch(f"/api/shorts/candidates/{cid}", json={
        "status": "confirmed",
    })
    assert resp.status_code == 200
    assert resp.json()["status"] == "confirmed"

    resp = await client.delete(f"/api/shorts/candidates/{cid}")
    assert resp.status_code == 204

    resp = await client.get("/api/shorts/candidates")
    assert resp.json() == []


@pytest.mark.anyio
async def test_candidate_not_found(client: AsyncClient):
    resp = await client.patch("/api/shorts/candidates/nonexistent", json={"status": "confirmed"})
    assert resp.status_code == 404

    resp = await client.delete("/api/shorts/candidates/nonexistent")
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_settings_get_and_update(client: AsyncClient):
    resp = await client.get("/api/settings")
    assert resp.status_code == 200
    data = resp.json()
    assert data["shortsDuration"] == "30s"
    assert data["autoConfirmThreshold"] == 85

    resp = await client.patch("/api/settings", json={"shortsDuration": "15s"})
    assert resp.status_code == 200
    assert resp.json()["shortsDuration"] == "15s"


@pytest.mark.anyio
async def test_generate_requires_candidate(client: AsyncClient):
    resp = await client.post("/api/shorts/generate", json={
        "candidateId": "nonexistent",
        "template": "crop",
    })
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_generated_shorts_list(client: AsyncClient):
    resp = await client.get("/api/shorts")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
