import asyncio

import pytest
from httpx import AsyncClient


_CANDIDATE_PAYLOAD = {
    "startTime": "0:10",
    "endTime": "0:25",
    "duration": "0:15",
    "title": "Test Highlight",
    "indicators": ["audio_spike"],
    "confidence": 90,
}

_GENERATE_PAYLOAD = {
    "template": "blur_fill",
    "caption": "Amazing play!",
}


async def _seed_candidate(client: AsyncClient) -> str:
    """Create a candidate and return its ID."""
    resp = await client.post("/api/shorts/candidates", json=_CANDIDATE_PAYLOAD)
    assert resp.status_code == 201
    return resp.json()["id"]


@pytest.mark.anyio
async def test_generate_returns_job_id(client: AsyncClient):
    cid = await _seed_candidate(client)
    resp = await client.post("/api/shorts/generate", json={
        **_GENERATE_PAYLOAD,
        "candidateId": cid,
    })
    assert resp.status_code == 200
    body = resp.json()
    assert "jobId" in body
    assert body["jobId"].startswith("job-")
    assert body["status"] == "generating"


@pytest.mark.anyio
async def test_generate_nonexistent_candidate_404(client: AsyncClient):
    resp = await client.post("/api/shorts/generate", json={
        **_GENERATE_PAYLOAD,
        "candidateId": "sc-nonexistent",
    })
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_generate_creates_short_after_completion(client: AsyncClient):
    cid = await _seed_candidate(client)
    resp = await client.post("/api/shorts/generate", json={
        **_GENERATE_PAYLOAD,
        "candidateId": cid,
    })
    assert resp.status_code == 200

    # _run_generation is an async background task: 6 steps x 0.5s = 3s
    await asyncio.sleep(4)

    resp = await client.get("/api/shorts")
    assert resp.status_code == 200
    shorts = resp.json()
    assert len(shorts) >= 1

    generated = shorts[0]
    assert generated["template"] == "blur_fill"
    assert generated["caption"] == "Amazing play!"
    assert "artifactUrl" in generated
    assert "thumbnailUrl" in generated
    assert generated["title"] == "Test Highlight"


@pytest.mark.anyio
async def test_candidate_status_done_after_generation(client: AsyncClient):
    cid = await _seed_candidate(client)
    await client.post("/api/shorts/generate", json={
        **_GENERATE_PAYLOAD,
        "candidateId": cid,
    })
    await asyncio.sleep(4)

    resp = await client.get("/api/shorts/candidates")
    candidates = resp.json()
    match = [c for c in candidates if c["id"] == cid]
    assert len(match) == 1
    assert match[0]["status"] == "done"
    assert match[0]["progress"] == 100
