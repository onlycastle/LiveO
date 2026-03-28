from dataclasses import dataclass
from enum import Enum


class StreamEvent(Enum):
    STREAM_STARTED = "stream_started"
    STREAM_STOPPED = "stream_stopped"
    SEGMENT_READY = "segment_ready"
    AUDIO_READY = "audio_ready"
    STREAM_ERROR = "stream_error"
    HIGHLIGHT_DETECTED = "highlight_detected"
    TRANSCRIPT_UPDATE = "transcript_update"
    INDICATOR_UPDATE = "indicator_update"
    CANDIDATE_CREATED = "candidate_created"
    CANDIDATE_UPDATED = "candidate_updated"
    GENERATE_PROGRESS = "generate_progress"
    GENERATE_COMPLETE = "generate_complete"


@dataclass
class SegmentReadyEvent:
    event: StreamEvent
    video_path: str
    audio_path: str | None
    timestamp_start: float
    timestamp_end: float
    duration: float
