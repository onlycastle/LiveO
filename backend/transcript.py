from __future__ import annotations

import logging
import queue
import threading
import uuid
from collections.abc import Callable
from dataclasses import dataclass

from .debug import record_debug_log
from .stt import BaseSTT, TranscriptSegment, create_stt
from .vad import SileroVAD

logger = logging.getLogger(__name__)


@dataclass
class TranscriptLine:
    id: str
    timestamp: str
    text: str
    start: float
    end: float
    confidence: float
    is_highlight: bool = False


def _format_timestamp(seconds: float) -> str:
    h = int(seconds) // 3600
    m = (int(seconds) % 3600) // 60
    s = int(seconds) % 60
    return f"{h:02d}:{m:02d}:{s:02d}"


class TranscriptProcessor:
    def __init__(
        self,
        on_transcript: Callable[[TranscriptLine], None],
        stt: BaseSTT | None = None,
        vad: SileroVAD | None = None,
        on_segment_complete: Callable[[str, float, str, int], None] | None = None,
    ):
        self._on_transcript = on_transcript
        self._stt = stt or create_stt()
        self._vad = vad or SileroVAD()
        self._on_segment_complete = on_segment_complete
        self._queue: queue.Queue[tuple[str, float] | None] = queue.Queue()
        self._thread: threading.Thread | None = None
        self._running = False

    @property
    def available(self) -> bool:
        return self._stt is not None

    def start(self) -> None:
        if not self.available:
            logger.warning("TranscriptProcessor started without STT provider — no transcription will occur")
            record_debug_log(
                "backend.transcript",
                "processor_start_without_stt",
                "Transcript processor started without an STT provider",
                level="warning",
            )
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True, name="transcript-worker")
        self._thread.start()
        record_debug_log(
            "backend.transcript",
            "processor_started",
            "Transcript processor started",
            details={"threadName": self._thread.name, "sttAvailable": self.available},
        )

    def stop(self) -> None:
        self._running = False
        self._queue.put(None)
        if self._thread:
            self._thread.join(timeout=10)
            self._thread = None
        record_debug_log(
            "backend.transcript",
            "processor_stopped",
            "Transcript processor stopped",
        )

    def submit(self, audio_path: str, timestamp_start: float) -> None:
        self._queue.put((audio_path, timestamp_start))
        record_debug_log(
            "backend.transcript",
            "segment_submitted",
            "Queued audio segment for transcription",
            details={
                "audioPath": audio_path,
                "timestampStart": round(timestamp_start, 3),
                "queueSize": self._queue.qsize(),
            },
        )

    def _complete_segment(
        self,
        audio_path: str,
        ts_start: float,
        *,
        outcome: str,
        transcript_count: int,
    ) -> None:
        record_debug_log(
            "backend.transcript",
            "segment_processing_completed",
            "Finished transcript processing for segment",
            details={
                "audioPath": audio_path,
                "timestampStart": round(ts_start, 3),
                "outcome": outcome,
                "transcriptCount": transcript_count,
            },
        )
        if self._on_segment_complete is not None:
            self._on_segment_complete(audio_path, ts_start, outcome, transcript_count)

    def _loop(self) -> None:
        while self._running:
            item = self._queue.get()
            if item is None:
                record_debug_log(
                    "backend.transcript",
                    "processor_loop_exit",
                    "Transcript worker received stop signal",
                )
                break
            audio_path, ts_start = item
            try:
                self._process(audio_path, ts_start)
            except Exception:
                logger.exception("Transcript processing failed for %s", audio_path)
                record_debug_log(
                    "backend.transcript",
                    "segment_processing_failed",
                    "Transcript processing failed",
                    level="error",
                    details={"audioPath": audio_path, "timestampStart": round(ts_start, 3)},
                )

    def _process(self, audio_path: str, ts_start: float) -> None:
        record_debug_log(
            "backend.transcript",
            "segment_processing_started",
            "Processing audio segment for transcription",
            details={"audioPath": audio_path, "timestampStart": round(ts_start, 3)},
        )

        speech_detected = self._vad.has_speech(audio_path)
        record_debug_log(
            "backend.transcript",
            "vad_completed",
            "Finished VAD analysis",
            details={"audioPath": audio_path, "speechDetected": speech_detected},
        )
        if not speech_detected:
            record_debug_log(
                "backend.transcript",
                "segment_skipped_no_speech",
                "Skipping transcription because no speech was detected",
                details={"audioPath": audio_path},
            )
            self._complete_segment(
                audio_path,
                ts_start,
                outcome="no_speech",
                transcript_count=0,
            )
            return

        if self._stt is None:
            record_debug_log(
                "backend.transcript",
                "segment_skipped_no_stt",
                "Skipping transcription because no STT provider is available",
                level="warning",
                details={"audioPath": audio_path},
            )
            self._complete_segment(
                audio_path,
                ts_start,
                outcome="no_stt",
                transcript_count=0,
            )
            return

        segments = self._stt.transcribe(audio_path, offset=ts_start)
        record_debug_log(
            "backend.transcript",
            "stt_completed",
            "STT transcription finished for segment",
            details={"audioPath": audio_path, "segmentCount": len(segments)},
        )
        transcript_count = 0
        for seg in segments:
            line = TranscriptLine(
                id=f"t-{uuid.uuid4().hex[:8]}",
                timestamp=_format_timestamp(seg.start),
                text=seg.text,
                start=seg.start,
                end=seg.end,
                confidence=seg.confidence,
            )
            self._on_transcript(line)
            transcript_count += 1
            record_debug_log(
                "backend.transcript",
                "transcript_line_emitted",
                "Emitted transcript line",
                details={
                    "lineId": line.id,
                    "timestamp": line.timestamp,
                    "textPreview": line.text[:80],
                    "confidence": round(line.confidence, 4),
                },
            )
        self._complete_segment(
            audio_path,
            ts_start,
            outcome="transcribed" if transcript_count else "empty_stt",
            transcript_count=transcript_count,
        )
