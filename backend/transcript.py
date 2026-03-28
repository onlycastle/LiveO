from __future__ import annotations

import logging
import queue
import threading
import uuid
from collections.abc import Callable
from dataclasses import dataclass

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
    ):
        self._on_transcript = on_transcript
        self._stt = stt or create_stt()
        self._vad = vad or SileroVAD()
        self._queue: queue.Queue[tuple[str, float] | None] = queue.Queue()
        self._thread: threading.Thread | None = None
        self._running = False

    @property
    def available(self) -> bool:
        return self._stt is not None

    def start(self) -> None:
        if not self.available:
            logger.warning("TranscriptProcessor started without STT provider — no transcription will occur")
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True, name="transcript-worker")
        self._thread.start()

    def stop(self) -> None:
        self._running = False
        self._queue.put(None)
        if self._thread:
            self._thread.join(timeout=10)
            self._thread = None

    def submit(self, audio_path: str, timestamp_start: float) -> None:
        self._queue.put((audio_path, timestamp_start))

    def _loop(self) -> None:
        while self._running:
            item = self._queue.get()
            if item is None:
                break
            audio_path, ts_start = item
            try:
                self._process(audio_path, ts_start)
            except Exception:
                logger.exception("Transcript processing failed for %s", audio_path)

    def _process(self, audio_path: str, ts_start: float) -> None:
        if not self._vad.has_speech(audio_path):
            return

        if self._stt is None:
            return

        segments = self._stt.transcribe(audio_path, offset=ts_start)
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
