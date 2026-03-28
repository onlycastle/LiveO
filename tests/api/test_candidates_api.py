import pytest
from httpx import AsyncClient


_VALID_CANDIDATE = {
    "startTime": "0:10",
    "endTime": "0:25",
    "duration": "0:15",
    "title": "Test Candidate",
    "indicators": ["audio_spike"],
    "confidence": 85,
}


async def _create_candidate(client: AsyncClient, **overrides) -> dict:
    payload = {**_VALID_CANDIDATE, **overrides}
    resp = await client.post("/api/shorts/candidates", json=payload)
    assert resp.status_code == 201
    return resp.json()


# ── Create ──────────────────────────────────────────────────


@pytest.mark.anyio
async def test_create_candidate_returns_201_with_shape(client: AsyncClient):
    resp = await client.post("/api/shorts/candidates", json=_VALID_CANDIDATE)
    assert resp.status_code == 201
    body = resp.json()
    # Required response fields
    assert "id" in body
    assert body["id"].startswith("sc-")
    assert body["startTime"] == "0:10"
    assert body["endTime"] == "0:25"
    assert body["duration"] == "0:15"
    assert body["title"] == "Test Candidate"
    assert body["indicators"] == ["audio_spike"]
    assert body["confidence"] == 85
    assert body["status"] == "pending"


# ── List ────────────────────────────────────────────────────


@pytest.mark.anyio
async def test_list_candidates_empty(client: AsyncClient):
    resp = await client.get("/api/shorts/candidates")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.anyio
async def test_list_candidates_after_create(client: AsyncClient):
    await _create_candidate(client)
    resp = await client.get("/api/shorts/candidates")
    assert resp.status_code == 200
    items = resp.json()
    assert isinstance(items, list)
    assert len(items) == 1
    assert items[0]["title"] == "Test Candidate"


# ── Update (PATCH) ──────────────────────────────────────────


@pytest.mark.anyio
async def test_update_candidate_confirmed(client: AsyncClient):
    created = await _create_candidate(client)
    cid = created["id"]
    resp = await client.patch(f"/api/shorts/candidates/{cid}", json={
        "status": "confirmed",
    })
    assert resp.status_code == 200
    assert resp.json()["status"] == "confirmed"


@pytest.mark.anyio
async def test_update_candidate_dismissed(client: AsyncClient):
    created = await _create_candidate(client)
    cid = created["id"]
    resp = await client.patch(f"/api/shorts/candidates/{cid}", json={
        "status": "dismissed",
    })
    assert resp.status_code == 200
    assert resp.json()["status"] == "dismissed"


@pytest.mark.anyio
async def test_update_candidate_undo_to_pending(client: AsyncClient):
    created = await _create_candidate(client)
    cid = created["id"]
    # First confirm
    await client.patch(f"/api/shorts/candidates/{cid}", json={"status": "confirmed"})
    # Then undo to pending
    resp = await client.patch(f"/api/shorts/candidates/{cid}", json={
        "status": "pending",
    })
    assert resp.status_code == 200
    assert resp.json()["status"] == "pending"


@pytest.mark.anyio
async def test_update_nonexistent_candidate_404(client: AsyncClient):
    resp = await client.patch("/api/shorts/candidates/sc-nonexistent", json={
        "status": "confirmed",
    })
    assert resp.status_code == 404


# ── Delete ──────────────────────────────────────────────────


@pytest.mark.anyio
async def test_delete_candidate_204(client: AsyncClient):
    created = await _create_candidate(client)
    cid = created["id"]
    resp = await client.delete(f"/api/shorts/candidates/{cid}")
    assert resp.status_code == 204

    # Verify it's gone
    resp = await client.get("/api/shorts/candidates")
    assert len(resp.json()) == 0


@pytest.mark.anyio
async def test_delete_nonexistent_candidate_404(client: AsyncClient):
    resp = await client.delete("/api/shorts/candidates/sc-nonexistent")
    assert resp.status_code == 404
