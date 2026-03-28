from __future__ import annotations

import importlib.util
import os
import struct
import tempfile
import wave

import pytest

from backend.stt import TranscriptSegment, WhisperSTT, create_stt
from backend.vad import SileroVAD

requires_whisper = pytest.mark.skipif(
    not importlib.util.find_spec("faster_whisper"),
    reason="faster-whisper not installed (optional STT dependency)",
)


def _make_wav(path: str, duration_sec: float = 1.0, sample_rate: int = 16000) -> str:
    n_samples = int(sample_rate * duration_sec)
    samples = struct.pack(f"<{n_samples}h", *([0] * n_samples))
    with wave.open(path, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(samples)
    return path


class TestTranscriptSegment:
    def test_creation(self):
        seg = TranscriptSegment(text="oh my god ace", start=10.0, end=12.5, confidence=0.92)
        assert seg.text == "oh my god ace"
        assert seg.start == 10.0
        assert seg.end == 12.5
        assert seg.confidence == 0.92

    def test_default_confidence(self):
        seg = TranscriptSegment(text="test", start=0.0, end=1.0)
        assert seg.confidence == 1.0


class TestWhisperSTT:
    def test_init(self):
        stt = WhisperSTT(model_size="tiny")
        assert stt._model_size == "tiny"

    @requires_whisper
    def test_transcribe_silent_audio(self):
        stt = WhisperSTT(model_size="tiny")
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            _make_wav(f.name, duration_sec=1.0)
            results = stt.transcribe(f.name, offset=0.0)
            os.unlink(f.name)
        assert isinstance(results, list)

    @requires_whisper
    def test_transcribe_with_offset(self):
        stt = WhisperSTT(model_size="tiny")
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            _make_wav(f.name, duration_sec=2.0)
            results = stt.transcribe(f.name, offset=500.0)
            os.unlink(f.name)
        for seg in results:
            assert seg.start >= 500.0
            assert seg.end >= seg.start


class TestCreateSTT:
    @requires_whisper
    def test_whisper_provider(self):
        stt = create_stt("whisper")
        assert isinstance(stt, WhisperSTT)

    @requires_whisper
    def test_auto_provider_without_deepgram_key(self):
        old = os.environ.pop("DEEPGRAM_API_KEY", None)
        try:
            stt = create_stt("auto")
            assert isinstance(stt, WhisperSTT)
        finally:
            if old:
                os.environ["DEEPGRAM_API_KEY"] = old


class TestSileroVAD:
    def test_silent_audio_no_speech(self):
        vad = SileroVAD()
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            _make_wav(f.name, duration_sec=1.0)
            has = vad.has_speech(f.name)
            os.unlink(f.name)
        assert has is False

    def test_energy_vad_fallback(self):
        timestamps = SileroVAD._energy_vad("/nonexistent.wav")
        assert timestamps == []


class TestTranscriptProcessor:
    def test_processor_submits_and_processes(self):
        from unittest.mock import MagicMock
        from backend.transcript import TranscriptProcessor

        results = []
        callback = lambda line: results.append(line)

        mock_stt = MagicMock()
        mock_stt.transcribe.return_value = [
            TranscriptSegment(text="headshot", start=1.0, end=2.0, confidence=0.9),
        ]

        mock_vad = MagicMock()
        mock_vad.has_speech.return_value = True

        proc = TranscriptProcessor(on_transcript=callback, stt=mock_stt, vad=mock_vad)
        proc.start()

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            _make_wav(f.name)
            proc.submit(f.name, 100.0)

        import time
        time.sleep(1.0)
        proc.stop()
        os.unlink(f.name)

        assert len(results) == 1
        assert results[0].text == "headshot"
        assert results[0].start == 1.0

    def test_processor_skips_when_no_speech(self):
        from unittest.mock import MagicMock
        from backend.transcript import TranscriptProcessor

        results = []
        mock_vad = MagicMock()
        mock_vad.has_speech.return_value = False

        proc = TranscriptProcessor(
            on_transcript=lambda line: results.append(line),
            stt=MagicMock(),
            vad=mock_vad,
        )
        proc.start()

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            _make_wav(f.name)
            proc.submit(f.name, 0.0)

        import time
        time.sleep(1.0)
        proc.stop()
        os.unlink(f.name)

        assert len(results) == 0
