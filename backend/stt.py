from __future__ import annotations

import logging
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class TranscriptSegment:
    text: str
    start: float
    end: float
    confidence: float = 1.0


class BaseSTT(ABC):
    @abstractmethod
    def transcribe(self, audio_path: str, offset: float = 0.0) -> list[TranscriptSegment]:
        ...


class WhisperSTT(BaseSTT):
    def __init__(self, model_size: str = "base", device: str = "auto", compute_type: str = "int8"):
        self._model_size = model_size
        self._device = device
        self._compute_type = compute_type
        self._model = None

    def _load_model(self):
        if self._model is None:
            from faster_whisper import WhisperModel
            self._model = WhisperModel(self._model_size, device=self._device, compute_type=self._compute_type)

    def transcribe(self, audio_path: str, offset: float = 0.0) -> list[TranscriptSegment]:
        self._load_model()
        raw_segments, info = self._model.transcribe(audio_path, beam_size=5, language="en")

        segments: list[TranscriptSegment] = []
        for seg in raw_segments:
            text = seg.text.strip()
            if not text:
                continue
            segments.append(TranscriptSegment(
                text=text,
                start=offset + seg.start,
                end=offset + seg.end,
                confidence=seg.avg_logprob,
            ))
        return segments


def create_stt(provider: str | None = None) -> BaseSTT | None:
    if provider is None:
        provider = os.environ.get("LIVEO_STT_PROVIDER", "auto")

    if provider in ("whisper", "auto"):
        try:
            import faster_whisper  # noqa: F401
            logger.info("Using faster-whisper STT (local)")
            return WhisperSTT()
        except ImportError:
            pass

    if provider != "auto":
        logger.warning("Requested STT provider '%s' not available", provider)
    else:
        logger.warning("No STT provider available (install faster-whisper)")
    return None
