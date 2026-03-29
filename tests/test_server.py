from __future__ import annotations

import asyncio
import os
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

import backend.server as srv
from backend.clip_editor import RenderResult
from backend.events import SegmentReadyEvent, StreamEvent
from backend.models import GenerateRequest
from backend.ring_buffer import RingBuffer
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
async def test_indicators_endpoint_returns_default_dashboard_state(client: AsyncClient):
    resp = await client.get("/api/indicators")
    assert resp.status_code == 200

    indicators = resp.json()
    assert len(indicators) == 8

    audio = next(ind for ind in indicators if ind["type"] == "audio_spike")
    keyword = next(ind for ind in indicators if ind["type"] == "keyword")
    kill_event = next(ind for ind in indicators if ind["type"] == "kill_event")

    assert audio["value"] == 0
    assert audio["active"] is False
    assert keyword["value"] == 0
    assert keyword["active"] is False
    assert kill_event["value"] == 0
    assert kill_event["active"] is False


@pytest.mark.anyio
async def test_indicator_updates_persist_for_bootstrap_endpoint(client: AsyncClient):
    resp = await client.post("/api/test/events", json={
        "type": "indicator_update",
        "data": {"type": "audio_spike", "value": 75, "active": True},
    })
    assert resp.status_code == 200

    resp = await client.get("/api/indicators")
    assert resp.status_code == 200

    indicators = resp.json()
    audio = next(ind for ind in indicators if ind["type"] == "audio_spike")
    assert audio["value"] == 75
    assert audio["active"] is True


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
    assert data["autoConfirmThreshold"] == 10

    resp = await client.patch("/api/settings", json={"shortsDuration": "15s"})
    assert resp.status_code == 200
    assert resp.json()["shortsDuration"] == "15s"


@pytest.mark.anyio
async def test_generate_requires_candidate(client: AsyncClient):
    resp = await client.post("/api/shorts/generate", json={
        "candidateId": "nonexistent",
        "template": "blur_fill",
    })
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_generated_shorts_list(client: AsyncClient):
    resp = await client.get("/api/shorts")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.anyio
async def test_run_generation_renders_from_buffered_segments(monkeypatch, tmp_path):
    seg_path = tmp_path / "seg_001.ts"
    seg_path.write_bytes(b"segment")

    ring = RingBuffer()
    ring.add_segment(10.0, 20.0, str(seg_path))
    srv._clip_buffer = ring
    srv._candidates["sc-live-1"] = {
        "id": "sc-live-1",
        "title": "Live Render Test",
        "status": "confirmed",
        "progress": 0,
        "confidence": 92,
        "indicators": ["kill_event"],
        "startTime": "0:10",
        "endTime": "0:15",
        "duration": "0:05",
    }

    async def fake_sleep(_seconds: float) -> None:
        return None

    async def fake_broadcast(_event: str, _payload: dict) -> None:
        return None

    def fake_concat(segment_paths: list[str], output_path: Path) -> None:
        assert segment_paths == [str(seg_path)]
        output_path.write_bytes(b"\x00" * 2048)

    def fake_render(**kwargs):
        output_dir = Path(kwargs["output_dir"])
        output_dir.mkdir(parents=True, exist_ok=True)
        video_path = output_dir / f"{kwargs['output_name']}.mp4"
        thumb_path = output_dir / f"{kwargs['output_name']}.jpg"
        video_path.write_bytes(b"video")
        thumb_path.write_bytes(b"thumb")
        return RenderResult(
            video_path=str(video_path),
            thumbnail_path=str(thumb_path),
            template=kwargs["template"],
            duration=5.0,
            width=1080,
            height=1920,
        )

    monkeypatch.setattr(asyncio, "sleep", fake_sleep)
    monkeypatch.setattr(srv.manager, "broadcast", fake_broadcast)
    monkeypatch.setattr(srv, "_build_concat_source", fake_concat)
    monkeypatch.setattr(srv, "render", fake_render)
    monkeypatch.setenv("LIVEO_TEST_MODE", "0")

    req = GenerateRequest(candidateId="sc-live-1", template="blur_fill")
    await srv._run_generation("job-live-1", "sc-live-1", req)

    assert any(item["title"] == "Live Render Test" for item in srv._generated.values())
    assert srv._candidates["sc-live-1"]["status"] == "done"
    generated = next(item for item in srv._generated.values() if item["title"] == "Live Render Test")
    assert os.path.exists(Path("artifacts/videos") / Path(generated["artifactUrl"]).name)
    assert os.path.exists(Path("artifacts/thumbs") / Path(generated["thumbnailUrl"]).name)


@pytest.mark.anyio
async def test_debug_logs_endpoint_returns_recent_logs(client: AsyncClient):
    create_resp = await client.post("/api/shorts/candidates", json={
        "startTime": "00:00:05",
        "endTime": "00:00:10",
        "duration": "0:05",
        "title": "Debug log candidate",
        "indicators": ["manual"],
        "confidence": 88,
        "isManual": True,
    })
    assert create_resp.status_code == 201

    logs_resp = await client.get("/api/debug/logs?limit=20")
    assert logs_resp.status_code == 200
    logs = logs_resp.json()
    assert isinstance(logs, list)
    assert any(entry["event"] == "candidate_created" for entry in logs)


@pytest.mark.anyio
async def test_auto_create_candidate_auto_confirms_and_schedules_generation(monkeypatch):
    generated_jobs = []

    async def fake_run_generation(job_id: str, candidate_id: str, req: GenerateRequest) -> None:
        generated_jobs.append((job_id, candidate_id, req.template))

    monkeypatch.setattr(srv, "_run_generation", fake_run_generation)
    srv._settings = srv.Settings(auto_confirm_threshold=85)

    await srv._auto_create_candidate({
        "startTime": "0:10",
        "endTime": "0:20",
        "duration": "0:10",
        "title": "Auto Confirm Test",
        "indicators": ["audio_spike"],
        "confidence": 90,
    })

    await asyncio.sleep(0)

    assert len(srv._candidates) == 1
    candidate = next(iter(srv._candidates.values()))
    assert candidate["status"] == "confirmed"
    assert {template for _, _, template in generated_jobs} == {"blur_fill", "letterbox", "cam_split"}
    assert len(generated_jobs) == 3


@pytest.mark.anyio
async def test_auto_create_candidate_below_threshold_stays_pending(monkeypatch):
    generated_jobs = []

    async def fake_run_generation(job_id: str, candidate_id: str, req: GenerateRequest) -> None:
        generated_jobs.append((job_id, candidate_id, req.template))

    monkeypatch.setattr(srv, "_run_generation", fake_run_generation)
    srv._settings = srv.Settings(auto_confirm_threshold=95)

    await srv._auto_create_candidate({
        "startTime": "0:10",
        "endTime": "0:20",
        "duration": "0:10",
        "title": "Pending Test",
        "indicators": ["keyword"],
        "confidence": 90,
    })

    await asyncio.sleep(0)

    assert len(srv._candidates) == 1
    candidate = next(iter(srv._candidates.values()))
    assert candidate["status"] == "pending"
    assert generated_jobs == []
    assert all(entry["origin"] == "backend" for entry in logs)


def test_on_segment_without_stt_does_not_queue_transcript_and_resolves_bucket(monkeypatch):
    from backend.detectors.gemini import GeminiHighlightResult

    transcript_proc = MagicMock()
    transcript_proc.available = False
    srv._transcript_proc = transcript_proc

    monkeypatch.setattr(srv.manager, "broadcast_sync", lambda *args, **kwargs: None)
    srv._gemini_detector._api_key = "test-key"
    monkeypatch.setattr(
        srv._gemini_detector,
        "analyze",
        lambda audio_path=None, frame_path=None: GeminiHighlightResult(
            is_highlight=False, confidence=0.2, audio_excitement=0.2,
            visual_action=0.0, keyword_relevance=0.0, kill_event=0.0,
            highlight_type="none", title_suggestion="", reasoning="test",
        ),
    )
    monkeypatch.setattr(srv, "_extract_segment_frame", lambda video_path, frame_offset_sec=1.5: "/tmp/frame.jpg")

    srv._on_segment(SegmentReadyEvent(
        event=StreamEvent.SEGMENT_READY,
        video_path="/tmp/seg.ts",
        audio_path="/tmp/seg.wav",
        timestamp_start=35.0,
        timestamp_end=41.2,
        duration=6.2,
    ))

    transcript_proc.submit.assert_not_called()
    assert srv._pending_detections == {}


def test_transcript_completion_resolves_pending_highlight_bucket(monkeypatch):
    from backend.detectors.gemini import GeminiHighlightResult

    monkeypatch.setattr(srv.manager, "broadcast_sync", lambda *args, **kwargs: None)

    srv._check_highlight(
        35.0,
        41.2,
        gemini_result=GeminiHighlightResult(
            is_highlight=False, confidence=0.1, audio_excitement=0.0,
            visual_action=0.0, keyword_relevance=0.0, kill_event=0.0,
            highlight_type="none", title_suggestion="", reasoning="test",
        ),
    )

    assert "35" in srv._pending_detections

    srv._on_transcript_segment_complete(
        "/tmp/seg.wav",
        35.0,
        "empty_stt",
        0,
    )

    assert srv._pending_detections == {}


def test_on_segment_emits_indicator_updates_from_gemini(monkeypatch):
    from backend.detectors.gemini import GeminiHighlightResult

    emitted: list[tuple[str, dict]] = []

    monkeypatch.setattr(srv.manager, "broadcast_sync", lambda msg_type, data: emitted.append((msg_type, data)))
    srv._gemini_detector._api_key = "test-key"
    monkeypatch.setattr(
        srv._gemini_detector,
        "analyze",
        lambda audio_path=None, frame_path=None: GeminiHighlightResult(
            is_highlight=True, confidence=0.85, audio_excitement=0.6,
            visual_action=0.7, keyword_relevance=0.4, kill_event=0.8,
            highlight_type="kill_streak", title_suggestion="Triple Kill!",
            reasoning="Intense kill streak moment",
        ),
    )
    monkeypatch.setattr(
        srv,
        "_extract_segment_frame",
        lambda video_path, frame_offset_sec=1.5: "/tmp/liveo-frame.jpg",
    )

    srv._on_segment(SegmentReadyEvent(
        event=StreamEvent.SEGMENT_READY,
        video_path="/tmp/seg.ts",
        audio_path="/tmp/seg.wav",
        timestamp_start=10.0,
        timestamp_end=15.0,
        duration=5.0,
    ))

    kill_update = next(
        data
        for event_type, data in emitted
        if event_type == "indicator_update" and data["type"] == "kill_event"
    )
    assert kill_update["value"] == 80
    assert kill_update["active"] is True

    audio_update = next(
        data
        for event_type, data in emitted
        if event_type == "indicator_update" and data["type"] == "audio_spike"
    )
    assert audio_update["value"] == 60
    assert audio_update["active"] is True

    assert srv._indicator_state["kill_event"]["value"] == 80
    assert srv._indicator_state["audio_spike"]["value"] == 60
