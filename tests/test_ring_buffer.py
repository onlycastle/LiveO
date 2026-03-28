import os
import tempfile

import pytest

from apps.live_server.ring_buffer import RingBuffer


@pytest.fixture
def tmp_dir():
    with tempfile.TemporaryDirectory() as d:
        yield d


def _create_segment(tmp_dir: str, name: str) -> str:
    path = os.path.join(tmp_dir, name)
    with open(path, "wb") as f:
        f.write(b"\x00" * 1024)
    return path


class TestRingBufferBasic:
    def test_empty_buffer(self):
        buf = RingBuffer()
        assert len(buf) == 0
        assert buf.get_range(0, 100) == []

    def test_add_segment(self, tmp_dir):
        buf = RingBuffer()
        path = _create_segment(tmp_dir, "seg_001.ts")
        buf.add_segment(1.0, path)
        assert len(buf) == 1

    def test_get_range_returns_matching(self, tmp_dir):
        buf = RingBuffer()
        p1 = _create_segment(tmp_dir, "seg_001.ts")
        p2 = _create_segment(tmp_dir, "seg_002.ts")
        p3 = _create_segment(tmp_dir, "seg_003.ts")
        buf.add_segment(10.0, p1)
        buf.add_segment(20.0, p2)
        buf.add_segment(30.0, p3)
        result = buf.get_range(15.0, 25.0)
        assert result == [p2]

    def test_get_range_inclusive(self, tmp_dir):
        buf = RingBuffer()
        p1 = _create_segment(tmp_dir, "seg_001.ts")
        buf.add_segment(10.0, p1)
        assert buf.get_range(10.0, 10.0) == [p1]

    def test_get_range_no_match(self, tmp_dir):
        buf = RingBuffer()
        p1 = _create_segment(tmp_dir, "seg_001.ts")
        buf.add_segment(10.0, p1)
        assert buf.get_range(20.0, 30.0) == []


class TestRingBufferCleanup:
    def test_cleanup_removes_old_segments(self, tmp_dir):
        buf = RingBuffer(max_duration_sec=10)
        p1 = _create_segment(tmp_dir, "old.ts")
        p2 = _create_segment(tmp_dir, "new.ts")
        buf.add_segment(0.0, p1)
        buf.add_segment(15.0, p2)
        assert len(buf) == 1
        assert not os.path.exists(p1)
        assert os.path.exists(p2)

    def test_cleanup_keeps_within_window(self, tmp_dir):
        buf = RingBuffer(max_duration_sec=100)
        paths = []
        for i in range(5):
            p = _create_segment(tmp_dir, f"seg_{i}.ts")
            buf.add_segment(float(i * 10), p)
            paths.append(p)
        assert len(buf) == 5
        for p in paths:
            assert os.path.exists(p)

    def test_cleanup_with_missing_file(self, tmp_dir):
        buf = RingBuffer(max_duration_sec=10)
        fake_path = os.path.join(tmp_dir, "ghost.ts")
        buf.add_segment(0.0, fake_path)
        p2 = _create_segment(tmp_dir, "new.ts")
        buf.add_segment(15.0, p2)
        assert len(buf) == 1

    def test_default_max_duration_is_300(self):
        buf = RingBuffer()
        assert buf.max_duration_sec == 300


class TestRingBufferClear:
    def test_clear_removes_all(self, tmp_dir):
        buf = RingBuffer()
        for i in range(3):
            p = _create_segment(tmp_dir, f"seg_{i}.ts")
            buf.add_segment(float(i), p)
        buf.clear()
        assert len(buf) == 0
        remaining = os.listdir(tmp_dir)
        assert remaining == []

    def test_clear_empty_buffer(self):
        buf = RingBuffer()
        buf.clear()
        assert len(buf) == 0


class TestRingBufferStress:
    def test_many_segments_within_window(self, tmp_dir):
        buf = RingBuffer(max_duration_sec=300)
        for i in range(100):
            p = _create_segment(tmp_dir, f"seg_{i:04d}.ts")
            buf.add_segment(float(i), p)
        assert len(buf) == 100

    def test_sliding_window(self, tmp_dir):
        buf = RingBuffer(max_duration_sec=5)
        for i in range(20):
            p = _create_segment(tmp_dir, f"seg_{i:04d}.ts")
            buf.add_segment(float(i), p)
        assert len(buf) <= 6
        oldest_ts = buf.segments[0][0]
        newest_ts = buf.segments[-1][0]
        assert newest_ts - oldest_ts <= 5
