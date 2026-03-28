from __future__ import annotations

import asyncio
import time
import uuid
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from .capture import RTMPStreamCapture, YtdlpDemoCapture
from .events import SegmentReadyEvent, StreamEvent
from .models import (
    CandidateStatus,
    GenerateRequest,
    GeneratedShort,
    Settings,
    ShortsCandidateCreate,
    ShortsCandidateUpdate,
    ShortsCandidate,
    StreamStartRequest,
    StreamStatus,
)
from .pipeline import Pipeline
from .ring_buffer import RingBuffer
from .ws_manager import manager, set_event_loop


_pipeline: Pipeline | None = None
_start_time: float = 0
_capture_method: str = ""
_error: str | None = None

_candidates: dict[str, dict[str, Any]] = {}
_generated: dict[str, dict[str, Any]] = {}
_settings = Settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    set_event_loop(asyncio.get_running_loop())
    yield
    if _pipeline:
        _pipeline.stop()


app = FastAPI(title="LiveO API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _on_segment(event: SegmentReadyEvent) -> None:
    manager.broadcast_sync("segment_ready", {
        "videoPath": event.video_path,
        "audioPath": event.audio_path,
        "timestampStart": event.timestamp_start,
        "timestampEnd": event.timestamp_end,
        "duration": event.duration,
    })


# ── Stream Control ──────────────────────────────────────────


@app.post("/api/stream/start")
async def stream_start(req: StreamStartRequest) -> StreamStatus:
    global _pipeline, _start_time, _capture_method, _error
    if _pipeline and _pipeline.capture.is_alive():
        raise HTTPException(400, "Stream already running")

    _error = None
    if req.source == "demo":
        if not req.url:
            raise HTTPException(400, "url is required for demo source")
        capture = YtdlpDemoCapture(req.url)
        _capture_method = "yt-dlp"
    else:
        url = req.url or "rtmp://localhost:1935/live/stream"
        capture = RTMPStreamCapture(url)
        _capture_method = "obs-rtmp"

    ring_buffer = RingBuffer(max_duration_sec=300)
    _pipeline = Pipeline(capture=capture, ring_buffer=ring_buffer)
    _pipeline.on_segment(_on_segment)

    try:
        _pipeline.start()
    except Exception as exc:
        _error = str(exc)
        raise HTTPException(500, str(exc))

    _start_time = time.time()

    await manager.broadcast("stream_status", {
        "isLive": True,
        "elapsed": 0,
        "captureMethod": _capture_method,
    })

    return StreamStatus(
        is_live=True,
        elapsed=0,
        capture_method=_capture_method,
        segment_count=0,
    )


@app.post("/api/stream/stop")
async def stream_stop() -> StreamStatus:
    global _pipeline, _start_time
    if not _pipeline:
        raise HTTPException(400, "No stream running")

    elapsed = time.time() - _start_time
    seg_count = len(_pipeline.ring_buffer)
    _pipeline.stop()
    _pipeline = None

    await manager.broadcast("stream_status", {"isLive": False, "elapsed": elapsed})

    return StreamStatus(
        is_live=False,
        elapsed=elapsed,
        capture_method=_capture_method,
        segment_count=seg_count,
    )


@app.get("/api/stream/status")
async def stream_status() -> StreamStatus:
    if _pipeline and _pipeline.capture.is_alive():
        return StreamStatus(
            is_live=True,
            elapsed=time.time() - _start_time,
            capture_method=_capture_method,
            segment_count=len(_pipeline.ring_buffer),
        )
    return StreamStatus(
        is_live=False,
        elapsed=0,
        capture_method=_capture_method,
        error=_error,
    )


# ── Shorts Candidates ──────────────────────────────────────


@app.get("/api/shorts/candidates")
async def list_candidates() -> list[dict[str, Any]]:
    return list(_candidates.values())


@app.post("/api/shorts/candidates", status_code=201)
async def create_candidate(req: ShortsCandidateCreate) -> dict[str, Any]:
    cid = f"sc-{uuid.uuid4().hex[:8]}"
    candidate = ShortsCandidate(
        id=cid,
        start_time=req.start_time,
        end_time=req.end_time,
        duration=req.duration,
        title=req.title,
        indicators=req.indicators,
        confidence=req.confidence,
        status=CandidateStatus.PENDING,
        is_manual=req.is_manual,
        captured_transcript=req.captured_transcript,
    )
    data = candidate.model_dump(by_alias=True)
    _candidates[cid] = data

    await manager.broadcast("candidate_created", data)
    return data


@app.patch("/api/shorts/candidates/{candidate_id}")
async def update_candidate(candidate_id: str, req: ShortsCandidateUpdate) -> dict[str, Any]:
    if candidate_id not in _candidates:
        raise HTTPException(404, "Candidate not found")

    updates = req.model_dump(by_alias=True, exclude_none=True)
    _candidates[candidate_id].update(updates)

    await manager.broadcast("candidate_updated", _candidates[candidate_id])
    return _candidates[candidate_id]


@app.delete("/api/shorts/candidates/{candidate_id}", status_code=204)
async def delete_candidate(candidate_id: str) -> None:
    if candidate_id not in _candidates:
        raise HTTPException(404, "Candidate not found")
    del _candidates[candidate_id]
    await manager.broadcast("candidate_deleted", {"id": candidate_id})


# ── Shorts Generation ──────────────────────────────────────


@app.post("/api/shorts/generate")
async def generate_short(req: GenerateRequest) -> dict[str, str]:
    cid = req.candidate_id
    if cid not in _candidates:
        raise HTTPException(404, "Candidate not found")

    _candidates[cid]["status"] = "generating"
    _candidates[cid]["progress"] = 0
    await manager.broadcast("candidate_updated", _candidates[cid])

    job_id = f"job-{uuid.uuid4().hex[:8]}"
    asyncio.create_task(_run_generation(job_id, cid, req))
    return {"jobId": job_id, "status": "generating"}


async def _run_generation(job_id: str, cid: str, req: GenerateRequest) -> None:
    for pct in (10, 30, 50, 70, 90, 100):
        await asyncio.sleep(0.5)
        if cid in _candidates:
            _candidates[cid]["progress"] = pct
            await manager.broadcast("generate_progress", {
                "candidateId": cid,
                "jobId": job_id,
                "percent": pct,
            })

    short_id = f"gs-{uuid.uuid4().hex[:8]}"
    title = _candidates[cid]["title"] if cid in _candidates else "Untitled"
    generated = GeneratedShort(
        id=short_id,
        title=title,
        duration=_candidates[cid].get("duration", "0:30") if cid in _candidates else "0:30",
        created_at="방금 전",
        indicators=_candidates[cid].get("indicators", []) if cid in _candidates else [],
    )
    data = generated.model_dump(by_alias=True)
    _generated[short_id] = data

    if cid in _candidates:
        _candidates[cid]["status"] = "done"
        _candidates[cid]["progress"] = 100
        await manager.broadcast("candidate_updated", _candidates[cid])

    await manager.broadcast("generate_complete", {
        "jobId": job_id,
        "candidateId": cid,
        "generatedShort": data,
    })


@app.get("/api/shorts")
async def list_generated() -> list[dict[str, Any]]:
    return list(_generated.values())


# ── Settings ────────────────────────────────────────────────


@app.get("/api/settings")
async def get_settings() -> dict[str, Any]:
    return _settings.model_dump(by_alias=True)


@app.patch("/api/settings")
async def update_settings(req: dict[str, Any]) -> dict[str, Any]:
    global _settings
    current = _settings.model_dump(by_alias=True)
    current.update(req)
    _settings = Settings.model_validate(current)
    return _settings.model_dump(by_alias=True)


# ── WebSocket ───────────────────────────────────────────────


@app.websocket("/ws/events")
async def websocket_events(ws: WebSocket) -> None:
    await manager.connect(ws)
    try:
        while True:
            data = await ws.receive_text()
            pass
    except WebSocketDisconnect:
        manager.disconnect(ws)
