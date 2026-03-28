import pytest
from httpx import AsyncClient


@pytest.mark.anyio
async def test_stream_start_demo_with_url(client: AsyncClient):
    resp = await client.post("/api/stream/start", json={
        "source": "demo",
        "url": "https://twitch.tv/test",
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["isLive"] is True
    assert body["captureMethod"] == "fake"


@pytest.mark.anyio
async def test_stream_start_demo_requires_url(client: AsyncClient):
    resp = await client.post("/api/stream/start", json={
        "source": "demo",
    })
    assert resp.status_code == 400


@pytest.mark.anyio
async def test_stream_start_duplicate(client: AsyncClient):
    await client.post("/api/stream/start", json={
        "source": "demo",
        "url": "https://twitch.tv/test",
    })
    resp = await client.post("/api/stream/start", json={
        "source": "demo",
        "url": "https://twitch.tv/test2",
    })
    assert resp.status_code == 400


@pytest.mark.anyio
async def test_stream_stop(client: AsyncClient):
    await client.post("/api/stream/start", json={
        "source": "demo",
        "url": "https://twitch.tv/test",
    })
    resp = await client.post("/api/stream/stop")
    assert resp.status_code == 200
    assert resp.json()["isLive"] is False


@pytest.mark.anyio
async def test_stream_status_shape(client: AsyncClient):
    resp = await client.get("/api/stream/status")
    assert resp.status_code == 200
    body = resp.json()
    assert "isLive" in body
    assert "elapsed" in body
    assert "captureMethod" in body
