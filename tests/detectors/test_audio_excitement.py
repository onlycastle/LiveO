import struct
import tempfile
import wave

import pytest

from backend.detectors.audio_excitement import AudioExcitementDetector


def _make_wav(path: str, samples: list[float], sample_rate: int = 16000) -> str:
    int_samples = [int(s * 32767) for s in samples]
    with wave.open(path, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(struct.pack(f"<{len(int_samples)}h", *int_samples))
    return path


def test_silent_audio_no_spike():
    det = AudioExcitementDetector()
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        _make_wav(f.name, [0.0] * 16000)
        result = det.analyze(f.name)
    assert result["is_spike"] is False
    assert result["score"] == 0.0


def test_loud_audio_spike():
    det = AudioExcitementDetector()
    # First, establish baseline with quiet audio
    for _ in range(10):
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            _make_wav(f.name, [0.01] * 16000)
            det.analyze(f.name)
    # Then send loud audio
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        _make_wav(f.name, [0.8] * 16000)
        result = det.analyze(f.name)
    assert result["is_spike"] is True
    assert result["score"] > 0.0


def test_rms_computation():
    det = AudioExcitementDetector()
    rms = det._compute_rms([0.5, -0.5, 0.5, -0.5])
    assert abs(rms - 0.5) < 0.01


def test_empty_audio():
    det = AudioExcitementDetector()
    result = det.analyze("/nonexistent/path.wav")
    assert result["is_spike"] is False
    assert result["score"] == 0.0
