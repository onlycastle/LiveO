from __future__ import annotations

import os
import subprocess
import tempfile
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field

from .capture import BaseCapture
from .debug import record_debug_log
from .events import SegmentReadyEvent, StreamEvent
from .ring_buffer import RingBuffer

SEGMENT_DURATION_SEC = 5


@dataclass
class Pipeline:
    capture: BaseCapture
    ring_buffer: RingBuffer = field(default_factory=RingBuffer)
    segment_duration: float = SEGMENT_DURATION_SEC
    output_dir: str = ""
    _listeners: list[Callable[[SegmentReadyEvent], None]] = field(
        default_factory=list, init=False,
    )
    _running: bool = field(default=False, init=False)
    _segment_thread: threading.Thread | None = field(default=None, init=False)

    def __post_init__(self) -> None:
        if not self.output_dir:
            self.output_dir = tempfile.mkdtemp(prefix="liveo_segments_")
        record_debug_log(
            "backend.pipeline",
            "pipeline_initialized",
            "Pipeline initialized",
            details={
                "outputDir": self.output_dir,
                "segmentDuration": self.segment_duration,
                "bufferDuration": self.ring_buffer.max_duration_sec,
            },
        )

    def on_segment(self, callback: Callable[[SegmentReadyEvent], None]) -> None:
        self._listeners.append(callback)
        record_debug_log(
            "backend.pipeline",
            "segment_listener_registered",
            "Registered segment listener",
            details={"listenerCount": len(self._listeners)},
        )

    def start(self) -> None:
        os.makedirs(self.output_dir, exist_ok=True)
        record_debug_log(
            "backend.pipeline",
            "pipeline_start",
            "Starting capture pipeline",
            details={"outputDir": self.output_dir},
        )
        self.capture.start()
        self._running = True
        self._segment_thread = threading.Thread(
            target=self._segment_loop, daemon=True,
        )
        self._segment_thread.start()
        record_debug_log(
            "backend.pipeline",
            "pipeline_started",
            "Capture pipeline started",
            details={"segmentThread": self._segment_thread.name},
        )

    def stop(self) -> None:
        self._running = False
        record_debug_log(
            "backend.pipeline",
            "pipeline_stop",
            "Stopping capture pipeline",
            details={"bufferedSegments": len(self.ring_buffer)},
        )
        if self._segment_thread:
            self._segment_thread.join(timeout=10)
            self._segment_thread = None
        self.capture.stop()
        record_debug_log(
            "backend.pipeline",
            "pipeline_stopped",
            "Capture pipeline stopped",
            details={"bufferedSegments": len(self.ring_buffer)},
        )

    @staticmethod
    def _probe_segment_streams(video_path: str) -> set[str]:
        result = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "stream=codec_type",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                video_path,
            ],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            return set()
        return {line.strip() for line in result.stdout.splitlines() if line.strip()}

    @staticmethod
    def _get_audio_channel_count(video_path: str) -> int | None:
        """Return the first detected audio channel count, or None if it cannot be read."""
        result = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-select_streams",
                "a:0",
                "-show_entries",
                "stream=channels",
                "-of",
                "default=nokey=1:noprint_wrappers=1",
                video_path,
            ],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            return None

        for line in result.stdout.splitlines():
            value = line.strip()
            if not value:
                continue
            try:
                return int(value)
            except ValueError:
                continue
        return None

    @staticmethod
    def _extract_audio(video_path: str, audio_path: str) -> bool:
        """Extract audio from video segment. Returns True on success."""
        record_debug_log(
            "backend.pipeline",
            "audio_extract_start",
            "Extracting audio for segment",
            details={"videoPath": video_path, "audioPath": audio_path},
        )
        channel_count = Pipeline._get_audio_channel_count(video_path)
        if channel_count == 0:
            record_debug_log(
                "backend.pipeline",
                "segment_audio_channelless",
                "Skipping audio extraction for segment with no-audio channels",
                level="warning",
                details={
                    "videoPath": video_path,
                    "audioPath": audio_path,
                    "channels": channel_count,
                },
            )
            return False
        if channel_count is not None:
            details = {"videoPath": video_path, "audioPath": audio_path, "channels": channel_count}
            record_debug_log(
                "backend.pipeline",
                "segment_audio_channel_counted",
                "Audio stream channel count detected",
                details=details,
            )
        result = subprocess.run(
            [
                "ffmpeg",
                "-fflags", "+discardcorrupt",
                "-err_detect", "ignore_err",
                "-i", video_path,
                "-vn", "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1",
                "-y", audio_path,
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
        )
        if result.returncode != 0 or not os.path.isfile(audio_path):
            record_debug_log(
                "backend.pipeline",
                "audio_extract_failed",
                "FFmpeg audio extraction failed",
                level="error",
                details={
                    "videoPath": video_path,
                    "audioPath": audio_path,
                    "returncode": result.returncode,
                    "stderr": (result.stderr or b"")[-500:].decode("utf-8", errors="replace"),
                },
            )
            return False
        record_debug_log(
            "backend.pipeline",
            "audio_extract_complete",
            "Finished extracting audio for segment",
            details={"videoPath": video_path, "audioPath": audio_path},
        )
        return True

    def _finalize_segment(
        self,
        seg_index: int,
        timeline_position: float,
        elapsed: float,
        payload: bytes,
    ) -> SegmentReadyEvent | None:
        segment_bytes = len(payload)
        seg_path = os.path.join(self.output_dir, f"seg_{seg_index:06d}.ts")
        with open(seg_path, "wb") as f:
            f.write(payload)

        streams = self._probe_segment_streams(seg_path)
        if "video" not in streams:
            record_debug_log(
                "backend.pipeline",
                "segment_validation_failed",
                "Segment did not contain a decodable video stream; keeping buffer open",
                level="warning",
                details={
                    "segmentIndex": seg_index,
                    "videoPath": seg_path,
                    "bufferedBytes": segment_bytes,
                    "elapsed": round(elapsed, 3),
                    "streams": sorted(streams),
                },
            )
            if os.path.exists(seg_path):
                os.remove(seg_path)
            return None

        audio_path = os.path.join(self.output_dir, f"seg_{seg_index:06d}.wav")
        audio_ok = False
        if "audio" in streams:
            audio_ok = self._extract_audio(seg_path, audio_path)
        else:
            record_debug_log(
                "backend.pipeline",
                "segment_without_audio",
                "Segment contained no audio stream; continuing without transcript audio",
                level="warning",
                details={"segmentIndex": seg_index, "videoPath": seg_path},
            )

        ts_start = timeline_position
        ts_end = ts_start + elapsed
        self.ring_buffer.add_segment(ts_start, ts_end, seg_path)

        return SegmentReadyEvent(
            event=StreamEvent.SEGMENT_READY,
            video_path=seg_path,
            audio_path=audio_path if audio_ok else None,
            timestamp_start=ts_start,
            timestamp_end=ts_end,
            duration=elapsed,
        )

    def _segment_loop(self) -> None:
        proc = self.capture.video_stdout
        if not proc or not proc.stdout:
            record_debug_log(
                "backend.pipeline",
                "segment_loop_no_stdout",
                "Capture process has no stdout; segment loop exiting",
                level="warning",
            )
            return

        seg_index = 0
        timeline_position = 0.0
        buf = bytearray()
        last_flush = time.monotonic()
        record_debug_log(
            "backend.pipeline",
            "segment_loop_started",
            "Segment loop started",
            details={"segmentDuration": self.segment_duration},
        )

        while self._running and self.capture.is_alive():
            data = proc.stdout.read(65536)
            if not data:
                record_debug_log(
                    "backend.pipeline",
                    "segment_loop_stream_ended",
                    "Capture stream produced no more data",
                    level="warning",
                    details={"segmentIndex": seg_index},
                )
                break

            buf.extend(data)
            now = time.monotonic()
            elapsed = now - last_flush

            if elapsed >= self.segment_duration and buf:
                segment_bytes = len(buf)
                event = self._finalize_segment(
                    seg_index=seg_index,
                    timeline_position=timeline_position,
                    elapsed=elapsed,
                    payload=bytes(buf),
                )
                if event is None:
                    continue

                buf.clear()
                timeline_position = event.timestamp_end
                record_debug_log(
                    "backend.pipeline",
                    "segment_ready",
                    "Segment ready for downstream processing",
                    details={
                        "segmentIndex": seg_index,
                        "videoPath": event.video_path,
                        "audioPath": event.audio_path,
                        "timestampStart": event.timestamp_start,
                        "timestampEnd": event.timestamp_end,
                        "duration": round(elapsed, 3),
                        "bufferedBytes": segment_bytes,
                        "listenerCount": len(self._listeners),
                    },
                )
                for cb in self._listeners:
                    cb(event)

                seg_index += 1
                last_flush = now

        record_debug_log(
            "backend.pipeline",
            "segment_loop_stopped",
            "Segment loop stopped",
            details={"segmentCount": seg_index, "running": self._running},
        )
