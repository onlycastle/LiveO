import os
import time
from dataclasses import dataclass, field


@dataclass
class RingBuffer:
    max_duration_sec: int = 300
    segments: list[tuple[float, str]] = field(default_factory=list)

    def add_segment(self, timestamp: float, path: str) -> None:
        self.segments.append((timestamp, path))
        self._cleanup()

    def get_range(self, start: float, end: float) -> list[str]:
        return [p for t, p in self.segments if start <= t <= end]

    def _cleanup(self) -> None:
        if not self.segments:
            return
        cutoff = self.segments[-1][0] - self.max_duration_sec
        expired = [(t, p) for t, p in self.segments if t < cutoff]
        for t, p in expired:
            if os.path.exists(p):
                os.remove(p)
        self.segments = [(t, p) for t, p in self.segments if t >= cutoff]

    def __len__(self) -> int:
        return len(self.segments)

    def clear(self) -> None:
        for _, p in self.segments:
            if os.path.exists(p):
                os.remove(p)
        self.segments.clear()
