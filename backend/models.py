from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class IndicatorType(str, Enum):
    MANUAL = "manual"
    CHAT_VELOCITY = "chat_velocity"
    SUPERCHAT = "superchat"
    AUDIO_SPIKE = "audio_spike"
    EMOTE_FLOOD = "emote_flood"
    SENTIMENT_SHIFT = "sentiment_shift"
    VIEWER_SPIKE = "viewer_spike"
    CLIP_BURST = "clip_burst"
    KILL_EVENT = "kill_event"
    KEYWORD = "keyword"
    GIFT_WAVE = "gift_wave"
    POLL_MOMENT = "poll_moment"
    OVERLAY_ALERT = "overlay_alert"


class CandidateStatus(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    DISMISSED = "dismissed"
    GENERATING = "generating"
    DONE = "done"


class Indicator(BaseModel):
    id: str
    type: IndicatorType
    label: str
    icon: str
    value: int = Field(ge=0, le=100)
    color: str
    active: bool


class TranscriptLine(BaseModel):
    id: str
    timestamp: str
    text: str
    speaker: Optional[str] = None
    is_highlight: Optional[bool] = Field(default=None, alias="isHighlight")

    model_config = {"populate_by_name": True}


class ShortsCandidate(BaseModel):
    id: str
    start_time: str = Field(alias="startTime")
    end_time: str = Field(alias="endTime")
    duration: str
    thumbnail_url: str = Field(default="", alias="thumbnailUrl")
    title: str
    indicators: list[IndicatorType]
    confidence: int = Field(ge=0, le=100)
    status: CandidateStatus = CandidateStatus.PENDING
    progress: Optional[int] = None
    is_manual: Optional[bool] = Field(default=None, alias="isManual")
    captured_transcript: Optional[str] = Field(default=None, alias="capturedTranscript")

    model_config = {"populate_by_name": True}


class GeneratedShort(BaseModel):
    id: str
    title: str
    thumbnail_url: str = Field(default="", alias="thumbnailUrl")
    artifact_url: str = Field(default="", alias="artifactUrl")
    duration: str
    created_at: str = Field(alias="createdAt")
    indicators: list[IndicatorType]
    template: str = Field(default="blur_fill")
    caption: str = Field(default="")

    model_config = {"populate_by_name": True}


class TimelineEvent(BaseModel):
    id: str
    time: float
    type: IndicatorType
    intensity: float = Field(ge=0, le=1)


class StreamStartRequest(BaseModel):
    source: str = Field(pattern="^(obs|demo)$")
    url: Optional[str] = None


class StreamStatus(BaseModel):
    is_live: bool = Field(alias="isLive")
    elapsed: float = 0
    capture_method: str = Field(default="", alias="captureMethod")
    error: Optional[str] = None
    segment_count: int = Field(default=0, alias="segmentCount")
    stt_available: bool = Field(default=True, alias="sttAvailable")

    model_config = {"populate_by_name": True}


class ShortsCandidateCreate(BaseModel):
    start_time: str = Field(alias="startTime")
    end_time: str = Field(alias="endTime")
    duration: str
    title: str
    indicators: list[IndicatorType] = []
    confidence: int = 100
    is_manual: bool = Field(default=False, alias="isManual")
    captured_transcript: Optional[str] = Field(default=None, alias="capturedTranscript")

    model_config = {"populate_by_name": True}


class ShortsCandidateUpdate(BaseModel):
    status: Optional[CandidateStatus] = None
    title: Optional[str] = None
    start_time: Optional[str] = Field(default=None, alias="startTime")
    end_time: Optional[str] = Field(default=None, alias="endTime")

    model_config = {"populate_by_name": True}


class GenerateRequest(BaseModel):
    candidate_id: str = Field(alias="candidateId")
    template: str = Field(pattern="^(blur_fill|letterbox|cam_split)$")
    crop_position: Optional[str] = Field(default="center", alias="cropPosition")
    trim_start: Optional[float] = Field(default=None, alias="trimStart")
    trim_end: Optional[float] = Field(default=None, alias="trimEnd")
    caption: str = ""
    export_format: str = Field(default="mp4", alias="exportFormat")

    model_config = {"populate_by_name": True}


class Settings(BaseModel):
    shorts_duration: str = Field(default="30s", alias="shortsDuration")
    auto_confirm_threshold: int = Field(default=85, alias="autoConfirmThreshold")
    indicator_sensitivity: dict[str, int] = Field(
        default_factory=lambda: {
            "chat_velocity": 50,
            "audio_spike": 50,
            "superchat": 50,
            "emote_flood": 50,
            "sentiment_shift": 50,
            "viewer_spike": 50,
            "kill_event": 50,
            "keyword": 50,
        },
        alias="indicatorSensitivity",
    )

    model_config = {"populate_by_name": True}


class WSMessage(BaseModel):
    type: str
    data: dict
