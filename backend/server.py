from __future__ import annotations

import asyncio
import os
import shutil
import subprocess as sp
import tempfile
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from starlette.staticfiles import StaticFiles

from .clip_editor import render
from .capture import BaseCapture, RTMPStreamCapture, YtdlpDemoCapture, FakeCapture
from .debug import (
    clear_debug_logs,
    configure_debug_logging,
    get_debug_logs,
    record_debug_log,
    set_debug_sink,
)
from .events import SegmentReadyEvent
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
from .transcript import TranscriptLine, TranscriptProcessor
from .ws_manager import manager, set_event_loop
from .detectors.gemini import GeminiDetector
from .highlight_aggregator import HighlightAggregator

configure_debug_logging()


_pipeline: Pipeline | None = None
_transcript_proc: TranscriptProcessor | None = None
_start_time: float = 0
_capture_method: str = ""
_error: str | None = None
_capture: BaseCapture | None = None
_clip_buffer: RingBuffer | None = None
_AUTO_GENERATE_TEMPLATES: tuple[str, ...] = ("blur_fill", "letterbox", "cam_split")

_candidates: dict[str, dict[str, Any]] = {}
_generated: dict[str, dict[str, Any]] = {}
_settings = Settings()

# Highlight detection
_gemini_detector = GeminiDetector()
_aggregator = HighlightAggregator()
_pending_detections: dict[str, dict[str, Any]] = {}
_INDICATOR_CATALOG: list[dict[str, str]] = [
    {"id": "1", "type": "chat_velocity", "label": "Chat Velocity", "icon": "\U0001F4AC", "color": "neon-lime"},
    {"id": "2", "type": "audio_spike", "label": "Audio Spike", "icon": "\U0001F50A", "color": "neon-red"},
    {"id": "3", "type": "superchat", "label": "Super Chat", "icon": "\U0001F4B0", "color": "neon-amber"},
    {"id": "4", "type": "emote_flood", "label": "Emote Flood", "icon": "\U0001F602", "color": "neon-cyan"},
    {"id": "5", "type": "sentiment_shift", "label": "Sentiment", "icon": "\U0001F525", "color": "neon-violet"},
    {"id": "6", "type": "viewer_spike", "label": "Viewer Spike", "icon": "\U0001F441", "color": "neon-cyan"},
    {"id": "7", "type": "kill_event", "label": "Kill Event", "icon": "\U0001F3AF", "color": "neon-red"},
    {"id": "8", "type": "keyword", "label": "Keyword Hit", "icon": "\U0001F511", "color": "neon-lime"},
]


def _create_indicator_state() -> dict[str, dict[str, Any]]:
    return {
        item["type"]: {
            **item,
            "value": 0,
            "active": False,
        }
        for item in _INDICATOR_CATALOG
    }


_indicator_state: dict[str, dict[str, Any]] = _create_indicator_state()


def _debug(
    event: str,
    message: str,
    *,
    level: str = "info",
    details: dict[str, Any] | None = None,
) -> None:
    record_debug_log("backend.server", event, message, level=level, details=details)


def _broadcast_debug_entry(entry: dict[str, Any]) -> None:
    manager.broadcast_sync("debug_log", entry)


def _list_indicator_state() -> list[dict[str, Any]]:
    return [_indicator_state[item["type"]].copy() for item in _INDICATOR_CATALOG]


def _set_indicator_state(indicator_type: str, value: int | float, active: bool) -> dict[str, Any]:
    if indicator_type not in _indicator_state:
        _indicator_state[indicator_type] = {
            "id": indicator_type,
            "type": indicator_type,
            "label": indicator_type.replace("_", " ").title(),
            "icon": "\U0001F4CA",
            "color": "neon-lime",
            "value": 0,
            "active": False,
        }

    state = _indicator_state[indicator_type]
    state["value"] = max(0, min(100, int(value)))
    state["active"] = bool(active)
    return state.copy()


def _broadcast_indicator_update(indicator_type: str, value: int | float, active: bool) -> dict[str, Any]:
    state = _set_indicator_state(indicator_type, value, active)
    manager.broadcast_sync(
        "indicator_update",
        {
            "type": indicator_type,
            "value": state["value"],
            "active": state["active"],
        },
    )
    return state


def _reset_detection_state(*, broadcast_indicators: bool = False) -> None:
    global _gemini_detector, _aggregator
    _pending_detections.clear()
    _gemini_detector = GeminiDetector()
    _aggregator = HighlightAggregator()

    for indicator_type in list(_indicator_state.keys()):
        state = _set_indicator_state(indicator_type, 0, False)
        if broadcast_indicators:
            manager.broadcast_sync(
                "indicator_update",
                {
                    "type": indicator_type,
                    "value": state["value"],
                    "active": state["active"],
                },
            )


def _reset_runtime_state() -> None:
    global _pipeline, _transcript_proc, _start_time, _capture_method, _error, _capture, _clip_buffer
    if _clip_buffer is not None:
        _clip_buffer.clear()
    _pipeline = None
    _transcript_proc = None
    _start_time = 0
    _capture_method = ""
    _error = None
    _capture = None
    _clip_buffer = None
    _reset_detection_state()


def _highlight_bucket_key(ts_start: float) -> str:
    return f"{ts_start:.0f}"


def _find_segment_bucket(ts: float) -> str | None:
    """Find the bucket key of the segment that contains this timestamp."""
    for key, bucket in _pending_detections.items():
        if bucket["ts_start"] <= ts <= bucket["ts_end"] + 1.0:
            return key
    return None


def _ensure_highlight_bucket(ts_start: float, ts_end: float) -> str:
    key = _highlight_bucket_key(ts_start)
    existing = _pending_detections.get(key)
    if existing is None:
        _pending_detections[key] = {
            "gemini": None,
            "gemini_text": None,
            "ts_start": ts_start,
            "ts_end": ts_end,
        }
        _debug(
            "highlight_bucket_created",
            "Created pending highlight bucket",
            details={"bucketKey": key, "timestampStart": ts_start, "timestampEnd": ts_end},
        )
    else:
        existing["ts_end"] = max(existing["ts_end"], ts_end)
    return key


def _transcript_available() -> bool:
    return _transcript_proc is not None and _transcript_proc.available


@asynccontextmanager
async def lifespan(app: FastAPI):
    set_event_loop(asyncio.get_running_loop())
    set_debug_sink(_broadcast_debug_entry)
    _debug("lifespan_startup", "LiveO API lifespan startup complete")
    yield
    _debug("lifespan_shutdown", "LiveO API lifespan shutdown started")
    if _transcript_proc:
        _transcript_proc.stop()
    if _pipeline:
        _pipeline.stop()
    if _capture:
        _capture.stop()
    set_debug_sink(None)


app = FastAPI(title="LiveO API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

artifacts_dir = Path("artifacts")
artifacts_dir.mkdir(exist_ok=True)
(artifacts_dir / "videos").mkdir(exist_ok=True)
(artifacts_dir / "thumbs").mkdir(exist_ok=True)

app.mount("/artifacts", StaticFiles(directory="artifacts"), name="artifacts")

_debug(
    "artifacts_ready",
    "Artifacts directories initialized",
    details={"artifactsDir": str(artifacts_dir.resolve())},
)


def _extract_segment_frame(video_path: str, frame_offset_sec: float = 1.5) -> str | None:
    frame_path = str(Path(video_path).with_suffix(".jpg"))
    attempts: list[tuple[str, list[str]]] = [
        (
            "seek_before_input",
            [
                "ffmpeg",
                "-ss",
                f"{frame_offset_sec:.2f}",
                "-i",
                video_path,
                "-frames:v",
                "1",
                "-y",
                frame_path,
            ],
        ),
        (
            "seek_after_input",
            [
                "ffmpeg",
                "-i",
                video_path,
                "-ss",
                f"{frame_offset_sec:.2f}",
                "-frames:v",
                "1",
                "-y",
                frame_path,
            ],
        ),
        (
            "half_offset_fallback",
            [
                "ffmpeg",
                "-i",
                video_path,
                "-ss",
                "0.10",
                "-frames:v",
                "1",
                "-y",
                frame_path,
            ],
        ),
        (
            "first_frame_fallback",
            [
                "ffmpeg",
                "-i",
                video_path,
                "-frames:v",
                "1",
                "-y",
                frame_path,
            ],
        ),
    ]

    last_error = ""
    for _, cmd in attempts:
        if os.path.exists(frame_path):
            os.remove(frame_path)

        result = sp.run(
            cmd,
            stdout=sp.DEVNULL,
            stderr=sp.PIPE,
            text=True,
        )
        if result.returncode == 0 and os.path.isfile(frame_path):
            return frame_path
        last_error = (result.stderr or "").strip()[-500:]

    _debug(
        "segment_frame_extract_failed",
        "Failed to extract frame after all fallback strategies",
        level="warning",
        details={"videoPath": video_path, "framePath": frame_path, "error": last_error},
    )
    return None


def _is_ad_frame(frame_path: str | None) -> bool:
    """Detect Twitch 'Commercial break in progress' by checking for purple-dominant frames."""
    if not frame_path or not os.path.exists(frame_path):
        return False
    try:
        from PIL import Image

        img = Image.open(frame_path).convert("RGB").resize((64, 64))
        pixels = list(img.getdata())
        purple_count = 0
        for r, g, b in pixels:
            # Twitch commercial screen: purple/violet gradient (high blue, moderate red, low green)
            if b > 100 and b > g and r < b and g < 120:
                purple_count += 1
        ratio = purple_count / len(pixels)
        if ratio > 0.5:
            _debug(
                "ad_frame_detected",
                f"Commercial break detected ({ratio:.0%} purple pixels)",
                details={"framePath": frame_path, "purpleRatio": round(ratio, 3)},
            )
            return True
    except Exception:
        pass
    return False


def _parse_timecode(value: str) -> float:
    parts = value.strip().split(":")
    if not 1 <= len(parts) <= 3:
        raise ValueError(f"Unsupported timecode: {value}")

    total = 0.0
    for part in parts:
        total = total * 60 + float(part)
    return total


def _format_duration_label(seconds: float) -> str:
    total_seconds = max(0, int(round(seconds)))
    minutes, secs = divmod(total_seconds, 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"


def _get_generation_buffer() -> RingBuffer | None:
    if _pipeline is not None:
        return _pipeline.ring_buffer
    return _clip_buffer


def _build_concat_source(segment_paths: list[str], output_path: Path) -> None:
    concat_file = output_path.with_suffix(".txt")
    concat_file.write_text(
        "".join(f"file '{Path(path).resolve()}'\n" for path in segment_paths),
        encoding="utf-8",
    )
    try:
        sp.run(
            [
                "ffmpeg",
                "-y",
                "-fflags",
                "+discardcorrupt",
                "-err_detect",
                "ignore_err",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                str(concat_file),
                "-c",
                "copy",
                "-avoid_negative_ts",
                "make_zero",
                str(output_path),
            ],
            capture_output=True,
            text=True,
            check=True,
        )
    except sp.CalledProcessError as exc:
        raise RuntimeError(
            f"Failed to assemble source clip: {(exc.stderr or '').strip()[-400:]}"
        ) from exc
    finally:
        concat_file.unlink(missing_ok=True)


def _render_candidate_artifacts(
    candidate: dict[str, Any],
    req: GenerateRequest,
    short_id: str,
) -> tuple[str, str, float]:
    ring_buffer = _get_generation_buffer()
    if ring_buffer is None:
        raise RuntimeError("No buffered stream is available for shorts generation")

    candidate_start = _parse_timecode(str(candidate["startTime"]))
    candidate_end = _parse_timecode(str(candidate["endTime"]))
    # Ensure at least 5 seconds when start == end (e.g. manual capture with single transcript line)
    if candidate_end <= candidate_start:
        candidate_end = candidate_start + 5.0
    clip_start = candidate_start + max(0.0, req.trim_start or 0.0)
    clip_end = candidate_start + req.trim_end if req.trim_end is not None else candidate_end
    clip_end = min(candidate_end, clip_end)
    if clip_end <= clip_start:
        raise RuntimeError("Candidate clip window is empty after trim settings")

    segments = [s for s in ring_buffer.get_segments(clip_start, clip_end) if not s.is_ad]
    if not segments:
        raise RuntimeError("No buffered segments overlap the selected highlight window")

    first_segment_start = segments[0].timestamp_start
    render_trim_start = max(0.0, clip_start - first_segment_start)
    render_trim_end = max(render_trim_start + 0.1, clip_end - first_segment_start)

    with tempfile.TemporaryDirectory(prefix="liveo_render_") as tmpdir:
        source_path = Path(tmpdir) / f"{short_id}_source.ts"
        render_dir = Path(tmpdir) / "rendered"
        _build_concat_source([seg.path for seg in segments], source_path)

        if source_path.stat().st_size < 1024:
            raise RuntimeError(
                "Concatenated source has no usable video data — all stream segments may be corrupt"
            )

        result = render(
            input_path=str(source_path),
            output_dir=str(render_dir),
            output_name=short_id,
            template=req.template,
            trim_start=render_trim_start,
            trim_end=render_trim_end,
            caption=req.caption,
        )

        artifact_path = Path("artifacts/videos") / f"{short_id}.mp4"
        artifact_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(result.video_path, artifact_path)

        thumbnail_url = ""
        if result.thumbnail_path and Path(result.thumbnail_path).exists():
            thumb_path = Path("artifacts/thumbs") / f"{short_id}.jpg"
            thumb_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(result.thumbnail_path, thumb_path)
            thumbnail_url = f"/artifacts/thumbs/{short_id}.jpg"

    return (
        f"/artifacts/videos/{short_id}.mp4",
        thumbnail_url,
        result.duration,
    )


def _on_segment(event: SegmentReadyEvent) -> None:
    transcript_expected = bool(event.audio_path) and _transcript_available()
    _debug(
        "segment_ready_received",
        "Received segment from pipeline",
        details={
            "videoPath": event.video_path,
            "audioPath": event.audio_path,
            "timestampStart": event.timestamp_start,
            "timestampEnd": event.timestamp_end,
            "duration": round(event.duration, 3),
        },
    )
    manager.broadcast_sync("segment_ready", {
        "videoPath": event.video_path,
        "audioPath": event.audio_path,
        "timestampStart": event.timestamp_start,
        "timestampEnd": event.timestamp_end,
        "duration": event.duration,
    })

    # Run Gemini multimodal detection on audio + video frame
    if not _gemini_detector.available:
        _debug(
            "gemini_detector_unavailable",
            "Gemini API key not configured; skipping detection",
            level="warning",
        )
        if transcript_expected and _transcript_proc and event.audio_path:
            _transcript_proc.submit(event.audio_path, event.timestamp_start)
        return

    frame_path: str | None = None
    try:
        _ensure_highlight_bucket(event.timestamp_start, event.timestamp_end)

        # Extract a representative frame for visual analysis
        if event.video_path:
            frame_offset = max(0.0, min(2.0, event.duration / 2))
            frame_path = _extract_segment_frame(event.video_path, frame_offset_sec=frame_offset)

        # Skip ad segments — mark in ring buffer and skip detection
        if _is_ad_frame(frame_path):
            if _pipeline and _pipeline.ring_buffer.segments:
                _pipeline.ring_buffer.segments[-1].is_ad = True
            return

        gemini_result = _gemini_detector.analyze(
            audio_path=event.audio_path,
            frame_path=frame_path,
        )

        _debug(
            "gemini_detection_completed",
            "Gemini multimodal detector analyzed segment",
            details={
                "isHighlight": gemini_result.is_highlight,
                "confidence": round(gemini_result.confidence, 3),
                "audioExcitement": round(gemini_result.audio_excitement, 3),
                "visualAction": round(gemini_result.visual_action, 3),
                "keywordRelevance": round(gemini_result.keyword_relevance, 3),
                "killEvent": round(gemini_result.kill_event, 3),
                "highlightType": gemini_result.highlight_type,
                "reasoning": gemini_result.reasoning,
            },
        )

        # Broadcast individual indicator updates
        _broadcast_indicator_update(
            "audio_spike",
            int(gemini_result.audio_excitement * 100),
            gemini_result.audio_excitement > 0.3,
        )
        _broadcast_indicator_update(
            "kill_event",
            int(gemini_result.kill_event * 100),
            gemini_result.kill_event > 0.3,
        )
        _broadcast_indicator_update(
            "keyword",
            int(gemini_result.keyword_relevance * 100),
            gemini_result.keyword_relevance > 0.3,
        )
        _broadcast_indicator_update(
            "sentiment_shift",
            int(gemini_result.visual_action * 100),
            gemini_result.visual_action > 0.3,
        )

        _check_highlight(
            event.timestamp_start,
            event.timestamp_end,
            gemini_result=gemini_result,
            finalize=not transcript_expected,
            resolution="no_stt" if not transcript_expected else None,
        )

    except Exception as exc:
        _debug(
            "gemini_detection_failed",
            "Gemini multimodal detector failed",
            level="error",
            details={
                "audioPath": event.audio_path,
                "videoPath": event.video_path,
                "error": str(exc),
            },
        )
    finally:
        if frame_path:
            Path(frame_path).unlink(missing_ok=True)

    # Submit audio for STT transcription (still useful for transcript display)
    if transcript_expected and _transcript_proc and event.audio_path:
        _transcript_proc.submit(event.audio_path, event.timestamp_start)
    else:
        _debug(
            "segment_no_transcript_submission",
            "Segment did not enter transcript queue",
            details={
                "audioPath": event.audio_path,
                "transcriptProcessorReady": _transcript_proc is not None,
                "sttAvailable": _transcript_available(),
            },
        )


def _on_transcript(line: TranscriptLine) -> None:
    _debug(
        "transcript_line_received",
        "Received transcript line from processor",
        details={
            "lineId": line.id,
            "timestamp": line.timestamp,
            "textPreview": line.text[:80],
            "confidence": round(line.confidence, 4),
        },
    )
    manager.broadcast_sync("transcript_update", {
        "id": line.id,
        "timestamp": line.timestamp,
        "text": line.text,
        "start": line.start,
        "end": line.end,
        "confidence": line.confidence,
        "isHighlight": line.is_highlight,
    })

    # Run Gemini text analysis only when multimodal didn't already score this bucket
    seg_key = _find_segment_bucket(line.start)
    multimodal_done = seg_key and _pending_detections.get(seg_key, {}).get("gemini") is not None
    if _gemini_detector.available and not multimodal_done:
        try:
            text_result = _gemini_detector.analyze_text(line.text)
            score_pct = int(text_result.keyword_relevance * 100)
            _debug(
                "gemini_text_detection_completed",
                "Gemini text detector analyzed transcript line",
                details={
                    "lineId": line.id,
                    "keywordRelevance": score_pct,
                    "isHighlight": text_result.is_highlight,
                    "highlightType": text_result.highlight_type,
                },
            )
            _broadcast_indicator_update("keyword", score_pct, score_pct > 0)
            if seg_key:
                bucket = _pending_detections[seg_key]
                _check_highlight(bucket["ts_start"], bucket["ts_end"], gemini_text_result=text_result)
            else:
                _check_highlight(line.start, line.end, gemini_text_result=text_result)
        except Exception as exc:
            _debug(
                "gemini_text_detection_failed",
                "Gemini text detector failed",
                level="error",
                details={"lineId": line.id, "error": str(exc)},
            )


def _on_transcript_segment_complete(
    audio_path: str,
    ts_start: float,
    outcome: str,
    transcript_count: int,
) -> None:
    _debug(
        "transcript_segment_completed",
        "Transcript worker completed segment",
        details={
            "audioPath": audio_path,
            "timestampStart": round(ts_start, 3),
            "outcome": outcome,
            "transcriptCount": transcript_count,
        },
    )
    key = _highlight_bucket_key(ts_start)
    bucket = _pending_detections.get(key)
    if bucket is None:
        return
    _check_highlight(
        bucket["ts_start"],
        bucket["ts_end"],
        finalize=True,
        resolution=outcome,
    )


def _check_highlight(
    ts_start: float,
    ts_end: float,
    gemini_result: Any = None,
    gemini_text_result: Any = None,
    finalize: bool = False,
    resolution: str | None = None,
) -> None:
    """Accumulate Gemini detection results and auto-create candidate if highlight."""
    from .detectors.gemini import GeminiHighlightResult

    key = _ensure_highlight_bucket(ts_start, ts_end)
    if gemini_result is not None:
        _pending_detections[key]["gemini"] = gemini_result
    if gemini_text_result is not None:
        _pending_detections[key]["gemini_text"] = gemini_text_result

    det = _pending_detections[key]

    # Pick the best result: prefer multimodal (gemini) over text-only (gemini_text)
    best_result: GeminiHighlightResult | None = det.get("gemini") or det.get("gemini_text")
    result = _aggregator.aggregate(gemini_result=best_result)

    _debug(
        "highlight_aggregated",
        "Aggregated Gemini highlight signals",
        details={
            "bucketKey": key,
            "isHighlight": result.is_highlight,
            "totalScore": round(result.total, 4),
            "audioScore": round(result.audio_score, 3),
            "keywordScore": round(result.keyword_score, 3),
            "killfeedScore": round(result.killfeed_score, 3),
            "highlightType": result.highlight_type,
        },
    )

    if result.is_highlight:
        indicators: list[str] = []
        if result.audio_score > 0.3:
            indicators.append("audio_spike")
        if result.keyword_score > 0.3:
            indicators.append("keyword")
        if result.killfeed_score > 0.3:
            indicators.append("kill_event")

        duration_sec = max(15, int(ts_end - ts_start))
        if duration_sec > int(ts_end - ts_start):
            ts_end = ts_start + duration_sec
        start_min, start_sec = divmod(int(ts_start), 60)
        end_min, end_sec = divmod(int(ts_end), 60)

        # Use Gemini's title suggestion if available, fallback to timestamp
        title = result.title_suggestion or f"Highlight @ {int(ts_start)}s"

        candidate_data = {
            "startTime": f"{start_min}:{start_sec:02d}",
            "endTime": f"{end_min}:{end_sec:02d}",
            "duration": f"0:{duration_sec:02d}",
            "title": title,
            "indicators": indicators,
            "confidence": int(result.total * 100),
        }
        _debug(
            "highlight_candidate_scheduled",
            "Highlight detected; scheduling candidate creation",
            details={"bucketKey": key, "candidate": candidate_data},
        )

        # Schedule async candidate creation on the event loop
        from .ws_manager import _get_or_create_loop

        try:
            loop = _get_or_create_loop()
            asyncio.run_coroutine_threadsafe(_auto_create_candidate(candidate_data), loop)
        except RuntimeError:
            _debug(
                "highlight_candidate_schedule_failed",
                "Could not schedule auto candidate creation because event loop is unavailable",
                level="warning",
                details={"bucketKey": key},
            )

        del _pending_detections[key]
        return

    if finalize:
        del _pending_detections[key]
        _debug(
            "highlight_bucket_resolved",
            "Resolved highlight bucket without candidate",
            details={
                "bucketKey": key,
                "resolution": resolution or "completed",
                "totalScore": round(result.total, 4),
            },
        )


async def _auto_create_candidate(data: dict) -> None:
    """Auto-create a candidate from highlight detection."""
    cid = f"sc-{uuid.uuid4().hex[:8]}"
    confidence = int(data.get("confidence", 80))
    auto_threshold = int(_settings.auto_confirm_threshold)
    status = CandidateStatus.CONFIRMED if confidence >= auto_threshold else CandidateStatus.PENDING
    candidate = ShortsCandidate(
        id=cid,
        start_time=data["startTime"],
        end_time=data["endTime"],
        duration=data["duration"],
        title=data["title"],
        indicators=data.get("indicators", []),
        confidence=confidence,
        status=status,
    )
    candidate_dict = candidate.model_dump(by_alias=True, mode="json")
    _candidates[cid] = candidate_dict
    _debug(
        "candidate_auto_created",
        "Auto-created shorts candidate from highlight detector",
        details={
            "candidateId": cid,
            "title": candidate_dict["title"],
            "status": status,
            "confidence": confidence,
            "autoConfirmThreshold": auto_threshold,
        },
    )
    await manager.broadcast("candidate_created", candidate_dict)

    if status == CandidateStatus.CONFIRMED:
        _debug(
            "candidate_auto_confirmed",
            "Auto-confirmed candidate exceeded threshold",
            details={"candidateId": cid, "threshold": auto_threshold, "confidence": confidence},
        )
        for template in _AUTO_GENERATE_TEMPLATES:
            job_id = f"job-{uuid.uuid4().hex[:8]}"
            asyncio.create_task(
                _run_generation(
                    job_id,
                    cid,
                    GenerateRequest(candidate_id=cid, template=template),
                )
            )


# ── Stream Control ──────────────────────────────────────────


@app.post("/api/stream/start")
async def stream_start(req: StreamStartRequest) -> StreamStatus:
    global _pipeline, _transcript_proc, _start_time, _capture_method, _error, _capture, _clip_buffer
    _debug(
        "stream_start_requested",
        "Received stream start request",
        details={"source": req.source, "url": req.url, "testMode": os.getenv("LIVEO_TEST_MODE") == "1"},
    )
    if _capture and _capture.is_alive():
        _debug(
            "stream_start_rejected",
            "Rejected stream start because fake capture is already running",
            level="warning",
        )
        raise HTTPException(400, "Stream already running")
    if _pipeline and _pipeline.capture.is_alive():
        _debug(
            "stream_start_rejected",
            "Rejected stream start because pipeline capture is already running",
            level="warning",
        )
        raise HTTPException(400, "Stream already running")

    _error = None
    _reset_detection_state()

    if os.getenv("LIVEO_TEST_MODE") == "1":
        if req.source == "demo" and not req.url:
            _debug(
                "stream_start_validation_failed",
                "Demo stream start request is missing a URL",
                level="warning",
            )
            raise HTTPException(400, "url is required for demo source")
        capture = FakeCapture(url=req.url or "")
        _capture_method = "fake"
        _capture = capture
        capture.start()
        _start_time = time.time()
        _debug(
            "stream_start_test_mode",
            "Started fake capture in test mode",
            details={"captureMethod": _capture_method, "url": req.url},
        )
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

    if req.source == "demo":
        if not req.url:
            _debug(
                "stream_start_validation_failed",
                "Demo stream start request is missing a URL",
                level="warning",
            )
            raise HTTPException(400, "url is required for demo source")
        capture = YtdlpDemoCapture(req.url)
        _capture_method = "yt-dlp"
    else:
        url = req.url or "rtmp://localhost:1935/live/stream"
        capture = RTMPStreamCapture(url)
        _capture_method = "obs-rtmp"
    _debug(
        "stream_capture_selected",
        "Selected capture backend for stream",
        details={"captureMethod": _capture_method, "source": req.source},
    )

    ring_buffer = RingBuffer(max_duration_sec=300)
    _clip_buffer = ring_buffer
    _pipeline = Pipeline(capture=capture, ring_buffer=ring_buffer)
    _pipeline.on_segment(_on_segment)
    _debug(
        "pipeline_created",
        "Created stream pipeline",
        details={"captureMethod": _capture_method, "bufferDuration": ring_buffer.max_duration_sec},
    )

    _transcript_proc = TranscriptProcessor(
        on_transcript=_on_transcript,
        on_segment_complete=_on_transcript_segment_complete,
    )
    _transcript_proc.start()
    stt_ok = _transcript_proc.available
    _debug(
        "transcript_processor_created",
        "Transcript processor initialized for stream",
        details={"sttAvailable": stt_ok},
    )
    if not stt_ok:
        await manager.broadcast("stream_status", {
            "sttAvailable": False,
            "warning": "STT provider unavailable — install faster-whisper for transcription",
        })

    try:
        await asyncio.to_thread(_pipeline.start)
    except Exception as exc:
        _error = str(exc)
        _transcript_proc.stop()
        _transcript_proc = None
        _debug(
            "stream_start_failed",
            "Failed to start stream pipeline",
            level="error",
            details={"error": str(exc), "captureMethod": _capture_method},
        )
        raise HTTPException(500, str(exc))

    _start_time = time.time()
    _debug(
        "stream_started",
        "Stream pipeline started successfully",
        details={"captureMethod": _capture_method},
    )

    await manager.broadcast("stream_status", {
        "isLive": True,
        "elapsed": 0,
        "captureMethod": _capture_method,
        "sttAvailable": stt_ok,
    })

    return StreamStatus(
        is_live=True,
        elapsed=0,
        capture_method=_capture_method,
        segment_count=0,
        stt_available=stt_ok,
    )


@app.post("/api/stream/stop")
async def stream_stop() -> StreamStatus:
    global _pipeline, _transcript_proc, _start_time, _capture
    _debug("stream_stop_requested", "Received stream stop request")
    if os.getenv("LIVEO_TEST_MODE") == "1" and _capture:
        elapsed = time.time() - _start_time
        _capture.stop()
        _capture = None
        _debug(
            "stream_stopped_test_mode",
            "Stopped fake capture in test mode",
            details={"elapsed": round(elapsed, 3), "captureMethod": _capture_method},
        )
        _reset_detection_state(broadcast_indicators=True)
        await manager.broadcast("stream_status", {"isLive": False, "elapsed": elapsed})
        return StreamStatus(is_live=False, elapsed=elapsed, capture_method=_capture_method, segment_count=0)
    if not _pipeline:
        _debug(
            "stream_stop_rejected",
            "Rejected stream stop because no pipeline is running",
            level="warning",
        )
        raise HTTPException(400, "No stream running")

    elapsed = time.time() - _start_time
    seg_count = len(_pipeline.ring_buffer)
    _pipeline.stop()
    _pipeline = None

    if _transcript_proc:
        _transcript_proc.stop()
        _transcript_proc = None
    _reset_detection_state(broadcast_indicators=True)
    _debug(
        "stream_stopped",
        "Stopped active stream pipeline",
        details={"elapsed": round(elapsed, 3), "segmentCount": seg_count},
    )

    await manager.broadcast("stream_status", {"isLive": False, "elapsed": elapsed})

    return StreamStatus(
        is_live=False,
        elapsed=elapsed,
        capture_method=_capture_method,
        segment_count=seg_count,
    )


@app.get("/api/stream/status")
async def stream_status() -> StreamStatus:
    if os.getenv("LIVEO_TEST_MODE") == "1" and _capture and _capture.is_alive():
        status = StreamStatus(
            is_live=True,
            elapsed=time.time() - _start_time,
            capture_method=_capture_method,
            segment_count=0,
        )
        _debug(
            "stream_status_returned",
            "Returned current stream status",
            details=status.model_dump(by_alias=True),
        )
        return status
    if _pipeline and _pipeline.capture.is_alive():
        status = StreamStatus(
            is_live=True,
            elapsed=time.time() - _start_time,
            capture_method=_capture_method,
            segment_count=len(_pipeline.ring_buffer),
        )
        _debug(
            "stream_status_returned",
            "Returned current stream status",
            details=status.model_dump(by_alias=True),
        )
        return status
    status = StreamStatus(
        is_live=False,
        elapsed=0,
        capture_method=_capture_method,
        error=_error,
    )
    _debug(
        "stream_status_returned",
        "Returned current stream status",
        details=status.model_dump(by_alias=True),
    )
    return status


# ── HLS Live Preview ──────────────────────────────────────


@app.get("/api/stream/hls/live.m3u8")
async def hls_live_playlist():
    ring_buffer = _get_generation_buffer()
    if not ring_buffer or not ring_buffer.segments:
        raise HTTPException(503, "No stream available")

    segments = ring_buffer.segments
    target_duration = 6  # ceil of 5s segment duration

    # Parse media sequence from the first segment filename (seg_000042.ts -> 42)
    first_name = os.path.basename(segments[0].path)
    media_sequence = int(first_name.split("_")[1].split(".")[0])

    lines = [
        "#EXTM3U",
        "#EXT-X-VERSION:3",
        f"#EXT-X-TARGETDURATION:{target_duration}",
        f"#EXT-X-MEDIA-SEQUENCE:{media_sequence}",
    ]

    for seg in segments:
        duration = seg.timestamp_end - seg.timestamp_start
        filename = os.path.basename(seg.path)
        lines.append(f"#EXTINF:{duration:.3f},")
        lines.append(f"/api/stream/hls/segments/{filename}")

    content = "\n".join(lines) + "\n"
    return Response(content=content, media_type="application/vnd.apple.mpegurl")


@app.get("/api/stream/hls/segments/{filename}")
async def hls_segment(filename: str):
    ring_buffer = _get_generation_buffer()
    if not ring_buffer:
        raise HTTPException(404, "No stream buffer")

    for seg in ring_buffer.segments:
        if os.path.basename(seg.path) == filename:
            return FileResponse(seg.path, media_type="video/mp2t")

    raise HTTPException(404, "Segment not found")


@app.get("/api/indicators")
async def list_indicators() -> list[dict[str, Any]]:
    _debug(
        "indicators_listed",
        "Returned current indicator dashboard state",
        details={"count": len(_indicator_state)},
    )
    return _list_indicator_state()


# ── Shorts Candidates ──────────────────────────────────────


@app.get("/api/shorts/candidates")
async def list_candidates() -> list[dict[str, Any]]:
    _debug(
        "candidates_listed",
        "Returned shorts candidates list",
        details={"count": len(_candidates)},
    )
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
    data = candidate.model_dump(by_alias=True, mode="json")
    _candidates[cid] = data
    _debug(
        "candidate_created",
        "Created shorts candidate",
        details={"candidateId": cid, "title": data["title"], "isManual": data.get("isManual", False)},
    )

    await manager.broadcast("candidate_created", data)
    return data


@app.patch("/api/shorts/candidates/{candidate_id}")
async def update_candidate(candidate_id: str, req: ShortsCandidateUpdate) -> dict[str, Any]:
    if candidate_id not in _candidates:
        _debug(
            "candidate_update_failed",
            "Failed to update candidate because it does not exist",
            level="warning",
            details={"candidateId": candidate_id},
        )
        raise HTTPException(404, "Candidate not found")

    updates = req.model_dump(by_alias=True, exclude_none=True, mode="json")
    _candidates[candidate_id].update(updates)
    _debug(
        "candidate_updated",
        "Updated shorts candidate",
        details={"candidateId": candidate_id, "updates": updates},
    )

    await manager.broadcast("candidate_updated", _candidates[candidate_id])
    return _candidates[candidate_id]


@app.delete("/api/shorts/candidates/{candidate_id}", status_code=204)
async def delete_candidate(candidate_id: str) -> None:
    if candidate_id not in _candidates:
        _debug(
            "candidate_delete_failed",
            "Failed to delete candidate because it does not exist",
            level="warning",
            details={"candidateId": candidate_id},
        )
        raise HTTPException(404, "Candidate not found")
    del _candidates[candidate_id]
    _debug(
        "candidate_deleted",
        "Deleted shorts candidate",
        details={"candidateId": candidate_id},
    )
    await manager.broadcast("candidate_deleted", {"id": candidate_id})


# ── Shorts Generation ──────────────────────────────────────


@app.post("/api/shorts/generate")
async def generate_short(req: GenerateRequest) -> dict[str, str]:
    cid = req.candidate_id
    if cid not in _candidates:
        _debug(
            "generate_request_failed",
            "Failed to queue generation because candidate does not exist",
            level="warning",
            details={"candidateId": cid, "template": req.template},
        )
        raise HTTPException(404, "Candidate not found")

    _candidates[cid]["status"] = "generating"
    _candidates[cid]["progress"] = 0
    _debug(
        "generate_request_accepted",
        "Queued shorts generation job",
        details={"candidateId": cid, "template": req.template},
    )
    await manager.broadcast("candidate_updated", _candidates[cid])

    job_id = f"job-{uuid.uuid4().hex[:8]}"
    asyncio.create_task(_run_generation(job_id, cid, req))
    _debug(
        "generate_job_created",
        "Created async generation job",
        details={"candidateId": cid, "jobId": job_id, "template": req.template},
    )
    return {"jobId": job_id, "status": "generating"}


async def _run_generation(job_id: str, cid: str, req: GenerateRequest) -> None:
    try:
        _debug(
            "generate_job_started",
            "Generation worker started",
            details={"candidateId": cid, "jobId": job_id, "template": req.template},
        )
        for pct in (10, 30, 50, 70, 90, 100):
            await asyncio.sleep(0.5)
            if cid in _candidates:
                _candidates[cid]["progress"] = pct
                _debug(
                    "generate_progress",
                    "Generation progress updated",
                    details={"candidateId": cid, "jobId": job_id, "percent": pct},
                )
                await manager.broadcast("generate_progress", {
                    "candidateId": cid,
                    "jobId": job_id,
                    "percent": pct,
                })

        short_id = f"gs-{uuid.uuid4().hex[:8]}"
        artifact_url = f"/artifacts/videos/{short_id}.mp4"
        thumbnail_url = f"/artifacts/thumbs/{short_id}.jpg"
        duration_label = _candidates[cid].get("duration", "0:30") if cid in _candidates else "0:30"

        if os.getenv("LIVEO_TEST_MODE") == "1":
            artifact_dir = Path("artifacts/videos")
            artifact_dir.mkdir(parents=True, exist_ok=True)
            thumb_dir = Path("artifacts/thumbs")
            thumb_dir.mkdir(parents=True, exist_ok=True)
            artifact_path = artifact_dir / f"{short_id}.mp4"
            thumb_path = thumb_dir / f"{short_id}.jpg"
            sp.run([
                "ffmpeg", "-y",
                "-f", "lavfi", "-i", "color=c=black:s=1080x1920:d=1",
                "-c:v", "libx264", str(artifact_path)
            ], capture_output=True, check=True)
            sp.run([
                "ffmpeg", "-y", "-i", str(artifact_path),
                "-frames:v", "1", str(thumb_path)
            ], capture_output=True, check=True)
            _debug(
                "generate_test_artifacts_created",
                "Created test-mode generated short artifacts",
                details={"jobId": job_id, "artifactPath": artifact_path, "thumbPath": thumb_path},
            )
        else:
            if cid not in _candidates:
                raise RuntimeError("Candidate disappeared before generation started")
            artifact_url, thumbnail_url, rendered_duration = await asyncio.to_thread(
                _render_candidate_artifacts,
                _candidates[cid],
                req,
                short_id,
            )
            duration_label = _format_duration_label(rendered_duration)
            _debug(
                "generate_artifacts_created",
                "Rendered short artifacts from buffered stream segments",
                details={
                    "candidateId": cid,
                    "jobId": job_id,
                    "shortId": short_id,
                    "artifactUrl": artifact_url,
                    "thumbnailUrl": thumbnail_url,
                    "duration": duration_label,
                },
            )

        title = _candidates[cid]["title"] if cid in _candidates else "Untitled"
        generated = GeneratedShort(
            id=short_id,
            title=title,
            duration=duration_label,
            created_at="방금 전",
            indicators=_candidates[cid].get("indicators", []) if cid in _candidates else [],
            template=req.template,
            caption=req.caption,
            artifact_url=artifact_url,
            thumbnail_url=thumbnail_url,
        )
        data = generated.model_dump(by_alias=True, mode="json")
        _generated[short_id] = data
        _debug(
            "generate_complete",
            "Generation completed successfully",
            details={"candidateId": cid, "jobId": job_id, "shortId": short_id, "template": req.template},
        )

        if cid in _candidates:
            _candidates[cid]["status"] = "done"
            _candidates[cid]["progress"] = 100
            if not _candidates[cid].get("thumbnailUrl"):
                _candidates[cid]["thumbnailUrl"] = thumbnail_url
            await manager.broadcast("candidate_updated", _candidates[cid])

        await manager.broadcast("generate_complete", {
            "jobId": job_id,
            "candidateId": cid,
            "generatedShort": data,
        })
    except Exception as exc:
        if cid in _candidates:
            _candidates[cid]["status"] = "confirmed"
            _candidates[cid]["progress"] = 0
            await manager.broadcast("candidate_updated", _candidates[cid])
        await manager.broadcast("generate_failed", {
            "jobId": job_id,
            "candidateId": cid,
            "error": str(exc),
        })
        _debug(
            "generate_failed",
            "Generation worker failed",
            level="error",
            details={"candidateId": cid, "jobId": job_id, "template": req.template, "error": str(exc)},
        )


@app.get("/api/shorts")
async def list_generated() -> list[dict[str, Any]]:
    _debug(
        "generated_listed",
        "Returned generated shorts list",
        details={"count": len(_generated)},
    )
    return list(_generated.values())


# ── Settings ────────────────────────────────────────────────


@app.get("/api/settings")
async def get_settings() -> dict[str, Any]:
    _debug("settings_returned", "Returned current settings")
    return _settings.model_dump(by_alias=True)


@app.patch("/api/settings")
async def update_settings(req: dict[str, Any]) -> dict[str, Any]:
    global _settings
    current = _settings.model_dump(by_alias=True)
    current.update(req)
    _settings = Settings.model_validate(current)
    _debug("settings_updated", "Updated settings", details={"updatedKeys": list(req.keys())})
    return _settings.model_dump(by_alias=True)


@app.get("/api/debug/logs")
async def list_debug_logs(limit: int = 150) -> list[dict[str, Any]]:
    _debug(
        "debug_logs_requested",
        "Returned recent debug logs",
        details={"limit": limit},
    )
    return get_debug_logs(limit=limit)


# ── Test Mode Endpoints (LIVEO_TEST_MODE=1 only) ──────────

if os.getenv("LIVEO_TEST_MODE") == "1":

    @app.post("/api/test/reset")
    async def test_reset() -> dict[str, str]:
        global _candidates, _generated, _settings, _pipeline, _transcript_proc
        global _start_time, _capture_method, _error, _capture
        _debug("test_reset_requested", "Resetting test server state")
        _candidates.clear()
        _generated.clear()
        _settings = Settings()
        _reset_runtime_state()
        clear_debug_logs()
        # Clean artifacts
        import shutil
        for d in (Path("artifacts/videos"), Path("artifacts/thumbs")):
            if d.exists():
                shutil.rmtree(d)
            d.mkdir(parents=True, exist_ok=True)
        return {"status": "reset"}

    @app.post("/api/test/seed")
    async def test_seed(payload: dict[str, Any]) -> dict[str, Any]:
        _debug(
            "test_seed_requested",
            "Seeding test data into server state",
            details={
                "candidateCount": len(payload.get("candidates", [])),
                "generatedCount": len(payload.get("generated", [])),
            },
        )
        for c in payload.get("candidates", []):
            cid = c.get("id", f"sc-test-{uuid.uuid4().hex[:8]}")
            candidate = ShortsCandidate(
                id=cid,
                start_time=c.get("startTime", "0:00"),
                end_time=c.get("endTime", "0:30"),
                duration=c.get("duration", "0:30"),
                title=c.get("title", "Test Candidate"),
                indicators=c.get("indicators", []),
                confidence=c.get("confidence", 85),
                status=c.get("status", "pending"),
                is_manual=c.get("isManual", False),
                captured_transcript=c.get("capturedTranscript"),
            )
            _candidates[cid] = candidate.model_dump(by_alias=True, mode="json")

        for g in payload.get("generated", []):
            gid = g.get("id", f"gs-test-{uuid.uuid4().hex[:8]}")
            gen = GeneratedShort(
                id=gid,
                title=g.get("title", "Test Short"),
                duration=g.get("duration", "0:15"),
                created_at=g.get("createdAt", "방금 전"),
                indicators=g.get("indicators", []),
                template=g.get("template", "blur_fill"),
                caption=g.get("caption", ""),
                artifact_url=g.get("artifactUrl", f"/artifacts/videos/{gid}.mp4"),
                thumbnail_url=g.get("thumbnailUrl", f"/artifacts/thumbs/{gid}.jpg"),
            )
            _generated[gid] = gen.model_dump(by_alias=True, mode="json")

        return {"status": "seeded", "candidates": len(payload.get("candidates", [])), "generated": len(payload.get("generated", []))}

    @app.post("/api/test/events")
    async def test_events(payload: dict[str, Any]) -> dict[str, str]:
        event_type = payload.get("type", "")
        event_data = payload.get("data", {})
        if event_type == "indicator_update" and isinstance(event_data, dict):
            _set_indicator_state(
                str(event_data.get("type", "")),
                event_data.get("value", 0),
                bool(event_data.get("active", False)),
            )
        _debug(
            "test_event_broadcast_requested",
            "Broadcasting synthetic test event",
            details={"type": event_type, "data": event_data},
        )
        await manager.broadcast(event_type, event_data)
        return {"status": "sent", "type": event_type}


# ── WebSocket ───────────────────────────────────────────────


@app.websocket("/ws/events")
async def websocket_events(ws: WebSocket) -> None:
    await manager.connect(ws)
    _debug(
        "websocket_connected",
        "WebSocket client connected",
        details={"connectionCount": manager.count},
    )
    try:
        while True:
            data = await ws.receive_text()
            _debug(
                "websocket_message_received",
                "Received message from WebSocket client",
                details={"message": data[:200]},
            )
    except WebSocketDisconnect:
        manager.disconnect(ws)
        _debug(
            "websocket_disconnected",
            "WebSocket client disconnected",
            details={"connectionCount": manager.count},
        )
