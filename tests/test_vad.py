import struct
import tempfile
import wave

import pytest

from backend.vad import SileroVAD


def _make_wav(samples: list[int], sample_rate: int = 16000) -> str:
    f = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    with wave.open(f.name, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(struct.pack(f"<{len(samples)}h", *samples))
    return f.name


class TestEnergyVAD:
    def test_silence_has_no_speech(self):
        path = _make_wav([0] * 16000)
        assert SileroVAD._energy_vad(path) == []

    def test_loud_audio_has_speech(self):
        path = _make_wav([10000, -10000] * 8000)
        result = SileroVAD._energy_vad(path)
        assert len(result) == 1

    def test_custom_threshold(self):
        path = _make_wav([300] * 16000)
        assert SileroVAD._energy_vad(path, rms_threshold=200) != []
        assert SileroVAD._energy_vad(path, rms_threshold=400) == []

    def test_empty_wav(self):
        path = _make_wav([])
        assert SileroVAD._energy_vad(path) == []


class TestSileroVADFallback:
    def test_has_speech_fallback_loud(self):
        vad = SileroVAD()
        vad._model = False
        path = _make_wav([10000, -10000] * 8000)
        assert vad.has_speech(path) is True

    def test_has_speech_fallback_silent(self):
        vad = SileroVAD()
        vad._model = False
        path = _make_wav([0] * 16000)
        assert vad.has_speech(path) is False

    def test_get_speech_timestamps_fallback(self):
        vad = SileroVAD()
        vad._model = False
        path = _make_wav([5000] * 16000)
        stamps = vad.get_speech_timestamps(path)
        assert len(stamps) == 1
        assert "start" in stamps[0]
        assert "end" in stamps[0]
