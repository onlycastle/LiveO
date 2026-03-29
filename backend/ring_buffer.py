import os
from dataclasses import dataclass, field

from .debug import record_debug_log


@dataclass
class BufferedSegment:
    timestamp_start: float
    timestamp_end: float
    path: str
    is_ad: bool = False


@dataclass
class RingBuffer:
    max_duration_sec: int = 300
    segments: list[BufferedSegment] = field(default_factory=list)

    def add_segment(self, timestamp_start: float, timestamp_end: float, path: str) -> None:
        self.segments.append(BufferedSegment(timestamp_start, timestamp_end, path))
        record_debug_log(
            "backend.ring_buffer",
            "segment_added",
            "Added segment to ring buffer",
            details={
                "timestampStart": round(timestamp_start, 3),
                "timestampEnd": round(timestamp_end, 3),
                "path": path,
                "segmentCount": len(self.segments),
                "maxDurationSec": self.max_duration_sec,
            },
        )
        self._cleanup()

    def get_segments(self, start: float, end: float) -> list[BufferedSegment]:
        return [
            seg for seg in self.segments
            if seg.timestamp_start <= end and seg.timestamp_end >= start
        ]

    def get_range(self, start: float, end: float) -> list[str]:
        return [seg.path for seg in self.get_segments(start, end)]

    def _cleanup(self) -> None:
        if not self.segments:
            return
        cutoff = self.segments[-1].timestamp_end - self.max_duration_sec
        expired = [seg for seg in self.segments if seg.timestamp_end < cutoff]
        for seg in expired:
            if os.path.exists(seg.path):
                os.remove(seg.path)
        self.segments = [seg for seg in self.segments if seg.timestamp_end >= cutoff]
        if expired:
            record_debug_log(
                "backend.ring_buffer",
                "segments_expired",
                "Expired old segments from ring buffer",
                details={
                    "expiredCount": len(expired),
                    "cutoff": round(cutoff, 3),
                    "remainingCount": len(self.segments),
                },
            )

    def __len__(self) -> int:
        return len(self.segments)

    def clear(self) -> None:
        for seg in self.segments:
            if os.path.exists(seg.path):
                os.remove(seg.path)
        self.segments.clear()
        record_debug_log(
            "backend.ring_buffer",
            "buffer_cleared",
            "Cleared all ring buffer segments",
        )
