from __future__ import annotations

import os
import subprocess
import tempfile
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field

from .capture import BaseCapture
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

    def on_segment(self, callback: Callable[[SegmentReadyEvent], None]) -> None:
        self._listeners.append(callback)

    def start(self) -> None:
        os.makedirs(self.output_dir, exist_ok=True)
        self.capture.start()
        self._running = True
        self._segment_thread = threading.Thread(
            target=self._segment_loop, daemon=True,
        )
        self._segment_thread.start()

    def stop(self) -> None:
        self._running = False
        if self._segment_thread:
            self._segment_thread.join(timeout=10)
            self._segment_thread = None
        self.capture.stop()

    @staticmethod
    def _extract_audio(video_path: str, audio_path: str) -> None:
        subprocess.run(
            [
                "ffmpeg", "-i", video_path,
                "-vn", "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1",
                "-y", audio_path,
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    def _segment_loop(self) -> None:
        proc = self.capture.video_stdout
        if not proc or not proc.stdout:
            return

        seg_index = 0
        buf = bytearray()
        last_flush = time.monotonic()

        while self._running and self.capture.is_alive():
            data = proc.stdout.read(65536)
            if not data:
                break

            buf.extend(data)
            now = time.monotonic()
            elapsed = now - last_flush

            if elapsed >= self.segment_duration and buf:
                seg_path = os.path.join(
                    self.output_dir, f"seg_{seg_index:06d}.ts",
                )
                with open(seg_path, "wb") as f:
                    f.write(buf)
                buf.clear()

                audio_path = os.path.join(
                    self.output_dir, f"seg_{seg_index:06d}.wav",
                )
                self._extract_audio(seg_path, audio_path)

                ts_start = seg_index * self.segment_duration
                ts_end = ts_start + elapsed
                self.ring_buffer.add_segment(ts_start, seg_path)

                event = SegmentReadyEvent(
                    event=StreamEvent.SEGMENT_READY,
                    video_path=seg_path,
                    audio_path=audio_path,
                    timestamp_start=ts_start,
                    timestamp_end=ts_end,
                    duration=elapsed,
                )
                for cb in self._listeners:
                    cb(event)

                seg_index += 1
                last_flush = now
