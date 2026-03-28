from __future__ import annotations

import struct
import wave
from pathlib import Path


class AudioExcitementDetector:
    """Detect audio excitement spikes using EMA-smoothed RMS."""

    def __init__(self, ema_alpha: float = 0.1, sigma_threshold: float = 3.0):
        self._ema_alpha = ema_alpha
        self._sigma_threshold = sigma_threshold
        self._ema: float = 0.0
        self._ema_sq: float = 0.0
        self._initialized = False

    def analyze(self, audio_path: str) -> dict:
        """Analyze audio file and return spike detection result.

        Returns dict with keys: rms, ema_baseline, sigma, is_spike, score (0-1)
        """
        samples = self._read_wav_samples(audio_path)
        if not samples:
            return {"rms": 0.0, "ema_baseline": 0.0, "sigma": 0.0, "is_spike": False, "score": 0.0}

        rms = self._compute_rms(samples)

        if not self._initialized:
            self._ema = rms
            self._ema_sq = rms * rms
            self._initialized = True
            return {"rms": rms, "ema_baseline": self._ema, "sigma": 0.0, "is_spike": False, "score": 0.0}

        # Update EMA
        self._ema = self._ema_alpha * rms + (1 - self._ema_alpha) * self._ema
        self._ema_sq = self._ema_alpha * (rms * rms) + (1 - self._ema_alpha) * self._ema_sq

        variance = max(0.0, self._ema_sq - self._ema * self._ema)
        std = variance ** 0.5

        if std < 1e-6:
            sigma = 0.0
        else:
            sigma = (rms - self._ema) / std

        is_spike = sigma >= self._sigma_threshold
        # Score: normalize sigma to 0-1 range (cap at 6 sigma)
        score = min(1.0, max(0.0, sigma / 6.0))

        return {
            "rms": rms,
            "ema_baseline": self._ema,
            "sigma": sigma,
            "is_spike": is_spike,
            "score": score,
        }

    @staticmethod
    def _read_wav_samples(path: str) -> list[float]:
        try:
            with wave.open(path, "rb") as wf:
                n = wf.getnframes()
                raw = wf.readframes(n)
                fmt = f"<{n * wf.getnchannels()}h"
                ints = struct.unpack(fmt, raw)
                return [s / 32768.0 for s in ints]
        except Exception:
            return []

    @staticmethod
    def _compute_rms(samples: list[float]) -> float:
        if not samples:
            return 0.0
        sq_sum = sum(s * s for s in samples)
        return (sq_sum / len(samples)) ** 0.5
