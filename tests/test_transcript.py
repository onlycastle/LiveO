import struct
import tempfile
import time
import wave
from unittest.mock import MagicMock

import pytest

from backend.stt import BaseSTT, TranscriptSegment
from backend.transcript import TranscriptLine, TranscriptProcessor, _format_timestamp
from backend.vad import SileroVAD


def _make_wav(samples: list[int], sample_rate: int = 16000) -> str:
    f = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    with wave.open(f.name, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(struct.pack(f"<{len(samples)}h", *samples))
    return f.name


class FakeSTT(BaseSTT):
    def __init__(self, segments: list[TranscriptSegment] | None = None):
        self._segments = segments or [
            TranscriptSegment(text="hello world", start=0.0, end=2.0, confidence=0.95),
        ]

    def transcribe(self, audio_path: str, offset: float = 0.0) -> list[TranscriptSegment]:
        return [
            TranscriptSegment(
                text=s.text,
                start=s.start + offset,
                end=s.end + offset,
                confidence=s.confidence,
            )
            for s in self._segments
        ]


class TestFormatTimestamp:
    def test_zero(self):
        assert _format_timestamp(0) == "00:00:00"

    def test_seconds(self):
        assert _format_timestamp(45) == "00:00:45"

    def test_minutes(self):
        assert _format_timestamp(125) == "00:02:05"

    def test_hours(self):
        assert _format_timestamp(3661) == "01:01:01"


class TestTranscriptProcessor:
    def test_processes_audio_with_speech(self):
        received: list[TranscriptLine] = []
        vad = SileroVAD()
        vad._model = False
        proc = TranscriptProcessor(
            on_transcript=lambda line: received.append(line),
            stt=FakeSTT(),
            vad=vad,
        )
        proc.start()

        loud_wav = _make_wav([10000, -10000] * 8000)
        proc.submit(loud_wav, timestamp_start=60.0)
        time.sleep(0.5)
        proc.stop()

        assert len(received) == 1
        assert received[0].text == "hello world"
        assert received[0].start == 60.0
        assert received[0].timestamp == "00:01:00"

    def test_skips_silent_audio(self):
        received: list[TranscriptLine] = []
        vad = SileroVAD()
        vad._model = False
        proc = TranscriptProcessor(
            on_transcript=lambda line: received.append(line),
            stt=FakeSTT(),
            vad=vad,
        )
        proc.start()

        silent_wav = _make_wav([0] * 16000)
        proc.submit(silent_wav, timestamp_start=0.0)
        time.sleep(0.5)
        proc.stop()

        assert len(received) == 0

    def test_available_with_stt(self):
        proc = TranscriptProcessor(
            on_transcript=lambda _: None,
            stt=FakeSTT(),
        )
        assert proc.available is True

    def test_not_available_without_stt(self):
        proc = TranscriptProcessor(
            on_transcript=lambda _: None,
        )
        proc._stt = None
        assert proc.available is False

    def test_start_stop_lifecycle(self):
        proc = TranscriptProcessor(
            on_transcript=lambda _: None,
            stt=FakeSTT(),
        )
        proc.start()
        assert proc._thread is not None
        assert proc._thread.is_alive()
        proc.stop()
        assert proc._thread is None

    def test_multiple_segments(self):
        received: list[TranscriptLine] = []
        vad = SileroVAD()
        vad._model = False
        stt = FakeSTT(segments=[
            TranscriptSegment(text="first", start=0.0, end=1.0),
            TranscriptSegment(text="second", start=1.0, end=2.0),
        ])
        proc = TranscriptProcessor(
            on_transcript=lambda line: received.append(line),
            stt=stt,
            vad=vad,
        )
        proc.start()

        loud_wav = _make_wav([10000] * 16000)
        proc.submit(loud_wav, timestamp_start=0.0)
        time.sleep(0.5)
        proc.stop()

        assert len(received) == 2
        assert received[0].text == "first"
        assert received[1].text == "second"

    def test_transcript_line_has_unique_id(self):
        received: list[TranscriptLine] = []
        vad = SileroVAD()
        vad._model = False
        proc = TranscriptProcessor(
            on_transcript=lambda line: received.append(line),
            stt=FakeSTT(),
            vad=vad,
        )
        proc.start()

        loud_wav = _make_wav([10000] * 16000)
        proc.submit(loud_wav, timestamp_start=0.0)
        proc.submit(loud_wav, timestamp_start=5.0)
        time.sleep(0.5)
        proc.stop()

        assert len(received) == 2
        assert received[0].id != received[1].id
        assert received[0].id.startswith("t-")
