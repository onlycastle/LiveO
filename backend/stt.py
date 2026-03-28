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


class DeepgramSTT(BaseSTT):
    def __init__(self, api_key: str | None = None, model: str = "nova-3", language: str = "en"):
        self._api_key = api_key or os.environ.get("DEEPGRAM_API_KEY", "")
        self._model = model
        self._language = language
        self._client = None

    def _get_client(self):
        if self._client is None:
            from deepgram import DeepgramClient
            self._client = DeepgramClient(self._api_key)
        return self._client

    def transcribe(self, audio_path: str, offset: float = 0.0) -> list[TranscriptSegment]:
        client = self._get_client()
        with open(audio_path, "rb") as f:
            source = {"buffer": f.read(), "mimetype": "audio/wav"}
        options = {"model": self._model, "language": self._language, "punctuate": True}
        response = client.listen.rest.v("1").transcribe_file(source, options)

        segments: list[TranscriptSegment] = []
        for channel in response.results.channels:
            for alt in channel.alternatives:
                if not alt.transcript:
                    continue
                for word in alt.words:
                    pass
                segments.append(TranscriptSegment(
                    text=alt.transcript,
                    start=offset + (alt.words[0].start if alt.words else 0),
                    end=offset + (alt.words[-1].end if alt.words else 0),
                    confidence=alt.confidence,
                ))
        return segments


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

    if provider == "deepgram" or (provider == "auto" and os.environ.get("DEEPGRAM_API_KEY")):
        logger.info("Using Deepgram STT (Nova-3)")
        return DeepgramSTT()

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
        logger.warning("No STT provider available (set DEEPGRAM_API_KEY or install faster-whisper)")
    return None
