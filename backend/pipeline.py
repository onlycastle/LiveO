from __future__ import annotations

import os
import shutil
import signal
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

    def _segment_loop(self) -> None:
        video_fifo = self.capture.video_pipe_path
        audio_fifo = self.capture.audio_pipe_path
        if not video_fifo or not audio_fifo:
            return

        seg_index = 0
        try:
            video_fd = os.open(video_fifo, os.O_RDONLY | os.O_NONBLOCK)
        except OSError:
            return

        buf = bytearray()
        last_flush = time.monotonic()

        while self._running and self.capture.is_alive():
            try:
                chunk = os.read(video_fd, 65536)
            except BlockingIOError:
                time.sleep(0.05)
                continue

            if not chunk:
                time.sleep(0.1)
                continue

            buf.extend(chunk)
            now = time.monotonic()
            elapsed = now - last_flush

            if elapsed >= self.segment_duration and buf:
                seg_path = os.path.join(
                    self.output_dir, f"seg_{seg_index:06d}.ts",
                )
                with open(seg_path, "wb") as f:
                    f.write(buf)
                buf.clear()

                ts_start = seg_index * self.segment_duration
                ts_end = ts_start + elapsed
                self.ring_buffer.add_segment(ts_start, seg_path)

                event = SegmentReadyEvent(
                    event=StreamEvent.SEGMENT_READY,
                    video_path=seg_path,
                    audio_path="",
                    timestamp_start=ts_start,
                    timestamp_end=ts_end,
                    duration=elapsed,
                )
                for cb in self._listeners:
                    cb(event)

                seg_index += 1
                last_flush = now

        os.close(video_fd)
