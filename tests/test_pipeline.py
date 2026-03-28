import os
import tempfile
import threading
import time
from unittest.mock import MagicMock, patch

import pytest

from apps.live_server.capture import BaseCapture
from apps.live_server.events import SegmentReadyEvent, StreamEvent
from apps.live_server.pipeline import Pipeline
from apps.live_server.ring_buffer import RingBuffer


class FakeCapture(BaseCapture):
    def __init__(self, tmpdir: str):
        self._tmpdir = tmpdir
        self._video_fifo = os.path.join(tmpdir, "video.ts")
        self._audio_fifo = os.path.join(tmpdir, "audio.wav")
        self._alive = False
        self._writer_thread: threading.Thread | None = None

    def start(self) -> None:
        os.mkfifo(self._video_fifo)
        os.mkfifo(self._audio_fifo)
        self._alive = True
        self._writer_thread = threading.Thread(target=self._write_data, daemon=True)
        self._writer_thread.start()

    def _write_data(self) -> None:
        try:
            vfd = os.open(self._video_fifo, os.O_WRONLY)
            seg = 0
            while self._alive:
                os.write(vfd, b"\x00" * 4096)
                time.sleep(0.1)
                seg += 1
            os.close(vfd)
        except OSError:
            pass

    def stop(self) -> None:
        self._alive = False
        if self._writer_thread:
            self._writer_thread.join(timeout=5)

    def is_alive(self) -> bool:
        return self._alive

    @property
    def video_pipe_path(self) -> str | None:
        return self._video_fifo if self._alive else None

    @property
    def audio_pipe_path(self) -> str | None:
        return self._audio_fifo if self._alive else None


class TestPipelineInit:
    def test_default_output_dir_created(self):
        mock_cap = MagicMock(spec=BaseCapture)
        pipeline = Pipeline(capture=mock_cap)
        assert pipeline.output_dir != ""
        assert os.path.isdir(pipeline.output_dir)
        os.rmdir(pipeline.output_dir)

    def test_custom_output_dir(self):
        mock_cap = MagicMock(spec=BaseCapture)
        with tempfile.TemporaryDirectory() as d:
            pipeline = Pipeline(capture=mock_cap, output_dir=d)
            assert pipeline.output_dir == d

    def test_default_segment_duration(self):
        mock_cap = MagicMock(spec=BaseCapture)
        pipeline = Pipeline(capture=mock_cap)
        assert pipeline.segment_duration == 5.0
        os.rmdir(pipeline.output_dir)


class TestPipelineCallbacks:
    def test_on_segment_registers_callback(self):
        mock_cap = MagicMock(spec=BaseCapture)
        pipeline = Pipeline(capture=mock_cap)
        cb = MagicMock()
        pipeline.on_segment(cb)
        assert cb in pipeline._listeners
        os.rmdir(pipeline.output_dir)


class TestPipelineSegmentation:
    def test_produces_segments_and_fires_events(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            fifo_dir = os.path.join(tmpdir, "fifos")
            os.makedirs(fifo_dir)
            seg_dir = os.path.join(tmpdir, "segments")
            os.makedirs(seg_dir)

            fake = FakeCapture(fifo_dir)
            ring = RingBuffer(max_duration_sec=60)
            pipeline = Pipeline(
                capture=fake,
                ring_buffer=ring,
                segment_duration=0.5,
                output_dir=seg_dir,
            )

            events_received: list[SegmentReadyEvent] = []
            pipeline.on_segment(lambda e: events_received.append(e))

            pipeline.start()
            time.sleep(2.0)
            pipeline.stop()

            assert len(events_received) >= 1
            for evt in events_received:
                assert evt.event == StreamEvent.SEGMENT_READY
                assert os.path.exists(evt.video_path)
                assert evt.duration > 0

            assert len(ring) >= 1

    def test_ring_buffer_receives_segments(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            fifo_dir = os.path.join(tmpdir, "fifos")
            os.makedirs(fifo_dir)
            seg_dir = os.path.join(tmpdir, "segments")
            os.makedirs(seg_dir)

            fake = FakeCapture(fifo_dir)
            ring = RingBuffer(max_duration_sec=60)
            pipeline = Pipeline(
                capture=fake,
                ring_buffer=ring,
                segment_duration=0.3,
                output_dir=seg_dir,
            )
            pipeline.start()
            time.sleep(1.5)
            pipeline.stop()

            assert len(ring) >= 1
            for _, path in ring.segments:
                assert os.path.exists(path)


class TestPipelineLifecycle:
    def test_start_calls_capture_start(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            fifo_dir = os.path.join(tmpdir, "fifos")
            os.makedirs(fifo_dir)

            mock_cap = MagicMock(spec=BaseCapture)
            mock_cap.video_pipe_path = None
            mock_cap.audio_pipe_path = None
            pipeline = Pipeline(capture=mock_cap, output_dir=tmpdir)
            pipeline.start()
            time.sleep(0.1)
            pipeline.stop()
            mock_cap.start.assert_called_once()

    def test_stop_calls_capture_stop(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_cap = MagicMock(spec=BaseCapture)
            mock_cap.video_pipe_path = None
            mock_cap.audio_pipe_path = None
            pipeline = Pipeline(capture=mock_cap, output_dir=tmpdir)
            pipeline.start()
            time.sleep(0.1)
            pipeline.stop()
            mock_cap.stop.assert_called_once()
