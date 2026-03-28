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

        try:
            wav, sr = self._load_audio_tensor(audio_path)
            if sr != 16000:
                wav = self._resample(wav, sr, 16000)
            if wav.ndim > 1:
                wav = wav.mean(dim=0)
            wav = wav.squeeze()
            return self._get_speech_ts(wav, self._model, threshold=self._threshold, sampling_rate=16000)
        except Exception:
            logger.warning(
                "Silero VAD audio loading failed for %s, falling back to energy-based VAD",
                audio_path,
                exc_info=True,
            )
            return self._energy_vad(audio_path)

    def has_speech(self, audio_path: str) -> bool:
        return len(self.get_speech_timestamps(audio_path)) > 0

    @staticmethod
    def _load_audio_tensor(audio_path: str):
        import torch

        with wave.open(audio_path, "rb") as wf:
            channels = wf.getnchannels()
            sample_width = wf.getsampwidth()
            sample_rate = wf.getframerate()
            frames = wf.readframes(wf.getnframes())

        if not frames:
            return torch.zeros((1, 0), dtype=torch.float32), sample_rate

        if sample_width == 1:
            wav = torch.tensor(list(frames), dtype=torch.float32)
            wav = (wav - 128.0) / 128.0
        elif sample_width == 2:
            sample_count = len(frames) // 2
            wav = torch.tensor(struct.unpack(f"<{sample_count}h", frames), dtype=torch.float32)
            wav = wav / 32768.0
        elif sample_width == 4:
            sample_count = len(frames) // 4
            wav = torch.tensor(struct.unpack(f"<{sample_count}i", frames), dtype=torch.float32)
            wav = wav / 2147483648.0
        else:
            raise ValueError(f"Unsupported WAV sample width: {sample_width}")

        if channels > 1:
            wav = wav.view(-1, channels).transpose(0, 1)
        else:
            wav = wav.unsqueeze(0)

        return wav, sample_rate

    @staticmethod
    def _resample(wav, src_rate: int, target_rate: int):
        import torch.nn.functional as F

        if src_rate == target_rate or wav.shape[-1] == 0:
            return wav

        target_length = max(1, round(wav.shape[-1] * target_rate / src_rate))
        return F.interpolate(
            wav.unsqueeze(0),
            size=target_length,
            mode="linear",
            align_corners=False,
        ).squeeze(0)

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
