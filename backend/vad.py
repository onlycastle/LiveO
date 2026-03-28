from __future__ import annotations

import logging
import struct
import wave

logger = logging.getLogger(__name__)


class SileroVAD:
    def __init__(self, threshold: float = 0.5):
        self._threshold = threshold
        self._model = None
        self._get_speech_ts = None

    def _load_model(self) -> None:
        if self._model is not None:
            return
        try:
            import torch
            model, utils = torch.hub.load(
                repo_or_dir="snakers4/silero-vad",
                model="silero_vad",
                force_reload=False,
                trust_repo=True,
            )
            self._model = model
            self._get_speech_ts = utils[0]
        except Exception:
            logger.warning("Silero VAD unavailable, falling back to energy-based VAD")
            self._model = False

    def get_speech_timestamps(self, audio_path: str) -> list[dict]:
        self._load_model()
        if self._model is False:
            return self._energy_vad(audio_path)

        import torch
        import torchaudio

        wav, sr = torchaudio.load(audio_path)
        if sr != 16000:
            wav = torchaudio.functional.resample(wav, sr, 16000)
        wav = wav.squeeze()
        return self._get_speech_ts(wav, self._model, threshold=self._threshold, sampling_rate=16000)

    def has_speech(self, audio_path: str) -> bool:
        return len(self.get_speech_timestamps(audio_path)) > 0

    @staticmethod
    def _energy_vad(audio_path: str, rms_threshold: float = 500.0) -> list[dict]:
        try:
            with wave.open(audio_path, "rb") as wf:
                frames = wf.readframes(wf.getnframes())
                if not frames:
                    return []
                samples = struct.unpack(f"<{len(frames) // 2}h", frames)
                rms = (sum(s * s for s in samples) / len(samples)) ** 0.5
                if rms > rms_threshold:
                    return [{"start": 0, "end": len(samples)}]
        except Exception:
            pass
        return []
