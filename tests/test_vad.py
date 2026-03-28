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


class TestSileroVADWaveLoader:
    def test_model_path_uses_builtin_wav_loader(self):
        vad = SileroVAD()
        vad._model = object()

        observed: dict[str, int | object] = {}

        def fake_get_speech_ts(wav, model, threshold, sampling_rate):
            observed["frame_count"] = int(wav.numel())
            observed["sampling_rate"] = sampling_rate
            observed["model"] = model
            return [{"start": 0, "end": int(wav.numel())}]

        vad._get_speech_ts = fake_get_speech_ts

        path = _make_wav([10000, -10000] * 8000)
        stamps = vad.get_speech_timestamps(path)

        assert stamps == [{"start": 0, "end": 16000}]
        assert observed["frame_count"] == 16000
        assert observed["sampling_rate"] == 16000
        assert observed["model"] is vad._model

    def test_model_path_resamples_to_16khz(self):
        vad = SileroVAD()
        vad._model = object()

        observed: dict[str, int] = {}

        def fake_get_speech_ts(wav, model, threshold, sampling_rate):
            observed["frame_count"] = int(wav.numel())
            observed["sampling_rate"] = sampling_rate
            return [{"start": 0, "end": int(wav.numel())}]

        vad._get_speech_ts = fake_get_speech_ts

        path = _make_wav([10000, -10000] * 4000, sample_rate=8000)
        stamps = vad.get_speech_timestamps(path)

        assert stamps == [{"start": 0, "end": 16000}]
        assert observed["frame_count"] == 16000
        assert observed["sampling_rate"] == 16000
