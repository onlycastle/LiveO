import io
import os
import tempfile
import threading
import time
from unittest.mock import MagicMock, patch

import pytest

from backend.capture import BaseCapture
from backend.events import SegmentReadyEvent, StreamEvent
from backend.pipeline import Pipeline
from backend.ring_buffer import RingBuffer


class FakeCapture(BaseCapture):
    def __init__(self, data_rate: int = 4096, chunk_interval: float = 0.05):
        self._data_rate = data_rate
        self._chunk_interval = chunk_interval
        self._alive = False
        self._pipe_r: int | None = None
        self._pipe_w: int | None = None
        self._proc = None
        self._writer: threading.Thread | None = None

    def start(self) -> None:
        r, w = os.pipe()
        self._pipe_r = r
        self._pipe_w = w
        self._alive = True
        self._proc = MagicMock()
        self._proc.stdout = os.fdopen(r, "rb")
        self._proc.poll.return_value = None
        self._writer = threading.Thread(target=self._write_data, daemon=True)
        self._writer.start()

    def _write_data(self) -> None:
        while self._alive and self._pipe_w is not None:
            try:
                os.write(self._pipe_w, b"\x00" * self._data_rate)
            except OSError:
                break
            time.sleep(self._chunk_interval)

    def stop(self) -> None:
        self._alive = False
        if self._pipe_w is not None:
            os.close(self._pipe_w)
            self._pipe_w = None
        if self._writer:
            self._writer.join(timeout=5)

    def is_alive(self) -> bool:
        return self._alive

    @property
    def video_stdout(self) -> MagicMock | None:
        return self._proc


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
    @patch.object(Pipeline, "_extract_audio", side_effect=lambda v, a: open(a, "wb").close())
    def test_produces_segments_and_fires_events(self, mock_extract):
        with tempfile.TemporaryDirectory() as seg_dir:
            fake = FakeCapture()
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
                assert evt.audio_path.endswith(".wav")
                assert evt.duration > 0

            assert mock_extract.call_count >= 1
            assert len(ring) >= 1

    @patch.object(Pipeline, "_extract_audio", side_effect=lambda v, a: open(a, "wb").close())
    def test_ring_buffer_receives_segments(self, mock_extract):
        with tempfile.TemporaryDirectory() as seg_dir:
            fake = FakeCapture()
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
            mock_cap = MagicMock(spec=BaseCapture)
            mock_cap.video_stdout = None
            pipeline = Pipeline(capture=mock_cap, output_dir=tmpdir)
            pipeline.start()
            time.sleep(0.1)
            pipeline.stop()
            mock_cap.start.assert_called_once()

    def test_stop_calls_capture_stop(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_cap = MagicMock(spec=BaseCapture)
            mock_cap.video_stdout = None
            pipeline = Pipeline(capture=mock_cap, output_dir=tmpdir)
            pipeline.start()
            time.sleep(0.1)
            pipeline.stop()
            mock_cap.stop.assert_called_once()
