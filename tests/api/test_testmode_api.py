import pytest
from httpx import AsyncClient


@pytest.mark.anyio
async def test_reset_clears_state(client: AsyncClient):
    # Seed some data first
    await client.post("/api/test/seed", json={
        "candidates": [{"id": "sc-1", "title": "Test", "startTime": "0:00", "endTime": "0:30", "duration": "0:30"}],
        "generated": [{"id": "gs-1", "title": "Gen Test", "duration": "0:15"}],
    })

    # Verify seeded
    resp = await client.get("/api/shorts/candidates")
    assert len(resp.json()) == 1

    resp = await client.get("/api/shorts")
    assert len(resp.json()) == 1

    # Reset
    resp = await client.post("/api/test/reset")
    assert resp.status_code == 200
    assert resp.json()["status"] == "reset"

    # Verify cleared
    resp = await client.get("/api/shorts/candidates")
    assert len(resp.json()) == 0

    resp = await client.get("/api/shorts")
    assert len(resp.json()) == 0


@pytest.mark.anyio
async def test_seed_creates_candidates_and_generated(client: AsyncClient):
    resp = await client.post("/api/test/seed", json={
        "candidates": [
            {
                "id": "sc-test-1",
                "title": "Test Highlight",
                "status": "pending",
                "confidence": 85,
                "indicators": ["audio_spike", "keyword"],
                "startTime": "0:10",
                "endTime": "0:25",
                "duration": "0:15",
            }
        ],
        "generated": [
            {
                "id": "gs-test-1",
                "title": "Test Short",
                "duration": "0:15",
                "indicators": ["audio_spike"],
                "template": "blur_fill",
                "caption": "TEST",
            }
        ],
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["candidates"] == 1
    assert body["generated"] == 1

    # Verify candidates
    resp = await client.get("/api/shorts/candidates")
    candidates = resp.json()
    assert len(candidates) == 1
    assert candidates[0]["id"] == "sc-test-1"
    assert candidates[0]["title"] == "Test Highlight"
    assert candidates[0]["confidence"] == 85

    # Verify generated
    resp = await client.get("/api/shorts")
    generated = resp.json()
    assert len(generated) == 1
    assert generated[0]["id"] == "gs-test-1"
    assert generated[0]["template"] == "blur_fill"


@pytest.mark.anyio
async def test_events_broadcasts_ws(client: AsyncClient):
    resp = await client.post("/api/test/events", json={
        "type": "test_event",
        "data": {"message": "hello"},
    })
    assert resp.status_code == 200
    assert resp.json()["type"] == "test_event"


@pytest.mark.anyio
async def test_stream_start_uses_fake_capture(client: AsyncClient):
    resp = await client.post("/api/stream/start", json={
        "source": "demo",
        "url": "https://twitch.tv/test",
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["isLive"] is True
    assert body["captureMethod"] == "fake"

    # Verify status
    resp = await client.get("/api/stream/status")
    assert resp.json()["isLive"] is True

    # Stop
    resp = await client.post("/api/stream/stop")
    assert resp.status_code == 200
    assert resp.json()["isLive"] is False
