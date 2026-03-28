from dataclasses import dataclass
from enum import Enum


class StreamEvent(Enum):
    STREAM_STARTED = "stream_started"
    SEGMENT_READY = "segment_ready"
    AUDIO_READY = "audio_ready"
    STREAM_ERROR = "stream_error"


@dataclass
class SegmentReadyEvent:
    event: StreamEvent
    video_path: str
    audio_path: str
    timestamp_start: float
    timestamp_end: float
    duration: float
