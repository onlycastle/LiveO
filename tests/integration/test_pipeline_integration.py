"""Integration tests for the full pipeline flow.

Verifies the complete lifecycle: seed -> confirm -> generate -> artifact -> download URL.
All tests run in LIVEO_TEST_MODE=1 (set in conftest.py).
"""
import asyncio

import pytest
from httpx import AsyncClient


@pytest.mark.anyio
async def test_full_flow_seed_confirm_generate_download(client: AsyncClient):
    """Test the complete flow: seed -> confirm -> generate -> artifact -> download URL."""
    # 1. Seed a candidate
    resp = await client.post("/api/test/seed", json={
        "candidates": [{
            "id": "sc-integ-1",
            "title": "Integration Test Highlight",
            "status": "pending",
            "confidence": 85,
            "indicators": ["audio_spike", "keyword"],
            "startTime": "0:10",
            "endTime": "0:25",
            "duration": "0:15",
        }],
    })
    assert resp.status_code == 200

    # 2. Confirm the candidate
    resp = await client.patch("/api/shorts/candidates/sc-integ-1", json={
        "status": "confirmed",
    })
    assert resp.status_code == 200
    assert resp.json()["status"] == "confirmed"

    # 3. Generate a short
    resp = await client.post("/api/shorts/generate", json={
        "candidateId": "sc-integ-1",
        "template": "blur_fill",
    })
    assert resp.status_code == 200
    job_id = resp.json()["jobId"]
    assert job_id.startswith("job-")

    # 4. Wait for generation to complete (6 steps x 0.5s = 3s, plus margin)
    await asyncio.sleep(4)

    # 5. Verify generated short exists
    resp = await client.get("/api/shorts")
    assert resp.status_code == 200
    shorts = resp.json()
    assert len(shorts) >= 1

    generated = shorts[0]
    assert generated["template"] == "blur_fill"
    assert generated["artifactUrl"].startswith("/artifacts/videos/")
    assert generated["thumbnailUrl"].startswith("/artifacts/thumbs/")

    # 6. Verify candidate status is done
    resp = await client.get("/api/shorts/candidates")
    candidates = resp.json()
    integ_candidate = next((c for c in candidates if c["id"] == "sc-integ-1"), None)
    assert integ_candidate is not None
    assert integ_candidate["status"] == "done"
    assert integ_candidate["progress"] == 100


@pytest.mark.anyio
async def test_multiple_templates_generate(client: AsyncClient):
    """Test generating all 3 templates for one candidate."""
    # Seed with confirmed status so we can skip the confirm step
    await client.post("/api/test/seed", json={
        "candidates": [{
            "id": "sc-multi-1",
            "title": "Multi-template Test",
            "status": "confirmed",
            "confidence": 90,
            "indicators": ["kill_event"],
            "startTime": "0:00",
            "endTime": "0:30",
            "duration": "0:30",
        }],
    })

    # Generate all 3 templates
    for template in ["blur_fill", "letterbox", "cam_split"]:
        resp = await client.post("/api/shorts/generate", json={
            "candidateId": "sc-multi-1",
            "template": template,
        })
        assert resp.status_code == 200

    # Wait for all to complete (3 jobs x ~3s each, but they run concurrently)
    await asyncio.sleep(12)

    # Verify 3 generated shorts
    resp = await client.get("/api/shorts")
    shorts = resp.json()
    assert len(shorts) >= 3
    templates = {s["template"] for s in shorts}
    assert "blur_fill" in templates
    assert "letterbox" in templates
    assert "cam_split" in templates


@pytest.mark.anyio
async def test_reload_recovers_state(client: AsyncClient):
    """Test that bootstrap GET endpoints recover seeded state."""
    # Seed complete state
    await client.post("/api/test/seed", json={
        "candidates": [
            {
                "id": "sc-reload-1",
                "title": "Reload Test",
                "startTime": "0:00",
                "endTime": "0:15",
                "duration": "0:15",
            },
        ],
        "generated": [
            {
                "id": "gs-reload-1",
                "title": "Reload Short",
                "duration": "0:15",
                "template": "blur_fill",
            },
        ],
    })

    # Bootstrap GETs (simulating page reload)
    resp = await client.get("/api/stream/status")
    assert resp.status_code == 200

    resp = await client.get("/api/shorts/candidates")
    assert resp.status_code == 200
    assert len(resp.json()) == 1

    resp = await client.get("/api/shorts")
    assert resp.status_code == 200
    assert len(resp.json()) == 1

    resp = await client.get("/api/settings")
    assert resp.status_code == 200


@pytest.mark.anyio
async def test_highlight_detectors_available():
    """Verify detector modules import correctly and aggregator works end-to-end."""
    from backend.detectors import AudioExcitementDetector, KeywordDetector, KillfeedOCRDetector
    from backend.highlight_aggregator import HighlightAggregator

    audio = AudioExcitementDetector()
    keyword = KeywordDetector()
    ocr = KillfeedOCRDetector()
    agg = HighlightAggregator()

    # Verify all detectors instantiate
    assert audio is not None
    assert keyword is not None
    assert ocr is not None
    assert agg is not None

    # Verify keyword detector produces expected output structure
    kw_result = keyword.analyze("ACE CLUTCH!!!")
    assert "score" in kw_result
    assert "matched_keywords" in kw_result
    assert kw_result["score"] > 0

    # Verify aggregator works with detector outputs
    result = agg.aggregate(
        audio_result={"score": 0.8},
        keyword_result=kw_result,
        killfeed_result={"score": 0.5},
    )
    assert result.is_highlight is True
    assert result.total > 0.6


@pytest.mark.anyio
async def test_reset_clears_all_state(client: AsyncClient):
    """Test that reset completely clears state."""
    # Seed data
    await client.post("/api/test/seed", json={
        "candidates": [{
            "id": "sc-reset-1",
            "title": "Reset Test",
            "startTime": "0:00",
            "endTime": "0:15",
            "duration": "0:15",
        }],
        "generated": [{
            "id": "gs-reset-1",
            "title": "Reset Short",
            "duration": "0:15",
        }],
    })

    # Verify seeded
    resp = await client.get("/api/shorts/candidates")
    assert len(resp.json()) == 1
    resp = await client.get("/api/shorts")
    assert len(resp.json()) == 1

    # Reset
    resp = await client.post("/api/test/reset")
    assert resp.status_code == 200

    # Verify empty
    resp = await client.get("/api/shorts/candidates")
    assert len(resp.json()) == 0
    resp = await client.get("/api/shorts")
    assert len(resp.json()) == 0


@pytest.mark.anyio
async def test_candidate_lifecycle_states(client: AsyncClient):
    """Test candidate transitions through all states: pending -> confirmed -> generating -> done."""
    # Seed pending candidate
    await client.post("/api/test/seed", json={
        "candidates": [{
            "id": "sc-lifecycle-1",
            "title": "Lifecycle Test",
            "status": "pending",
            "confidence": 80,
            "indicators": ["audio_spike"],
            "startTime": "0:05",
            "endTime": "0:20",
            "duration": "0:15",
        }],
    })

    # Verify pending
    resp = await client.get("/api/shorts/candidates")
    cand = resp.json()[0]
    assert cand["status"] == "pending"

    # Confirm
    resp = await client.patch("/api/shorts/candidates/sc-lifecycle-1", json={
        "status": "confirmed",
    })
    assert resp.json()["status"] == "confirmed"

    # Generate (triggers generating -> done)
    resp = await client.post("/api/shorts/generate", json={
        "candidateId": "sc-lifecycle-1",
        "template": "letterbox",
    })
    assert resp.status_code == 200

    # While generating, status should be "generating"
    resp = await client.get("/api/shorts/candidates")
    cand = next(c for c in resp.json() if c["id"] == "sc-lifecycle-1")
    assert cand["status"] == "generating"

    # Wait for completion
    await asyncio.sleep(4)

    # Verify done
    resp = await client.get("/api/shorts/candidates")
    cand = next(c for c in resp.json() if c["id"] == "sc-lifecycle-1")
    assert cand["status"] == "done"
    assert cand["progress"] == 100

    # Verify short was generated
    resp = await client.get("/api/shorts")
    shorts = resp.json()
    assert any(s["template"] == "letterbox" for s in shorts)


@pytest.mark.anyio
async def test_generated_short_has_correct_metadata(client: AsyncClient):
    """Test that generated shorts carry correct metadata from the candidate."""
    await client.post("/api/test/seed", json={
        "candidates": [{
            "id": "sc-meta-1",
            "title": "Clutch Ace Round",
            "status": "confirmed",
            "confidence": 95,
            "indicators": ["audio_spike", "keyword", "kill_event"],
            "startTime": "1:30",
            "endTime": "1:45",
            "duration": "0:15",
        }],
    })

    resp = await client.post("/api/shorts/generate", json={
        "candidateId": "sc-meta-1",
        "template": "cam_split",
        "caption": "INSANE ACE!",
    })
    assert resp.status_code == 200

    await asyncio.sleep(4)

    resp = await client.get("/api/shorts")
    shorts = resp.json()
    assert len(shorts) >= 1

    short = next(s for s in shorts if s["template"] == "cam_split")
    assert short["title"] == "Clutch Ace Round"
    assert short["template"] == "cam_split"
    assert short["caption"] == "INSANE ACE!"
    assert short["duration"] == "0:15"
    assert "audio_spike" in short["indicators"]
    assert "keyword" in short["indicators"]
    assert "kill_event" in short["indicators"]
