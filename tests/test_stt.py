import os
from unittest.mock import MagicMock, patch

import pytest

from backend.stt import (
    BaseSTT,
    TranscriptSegment,
    WhisperSTT,
    create_stt,
)


class TestTranscriptSegment:
    def test_creation(self):
        seg = TranscriptSegment(text="hello", start=1.0, end=2.0, confidence=0.95)
        assert seg.text == "hello"
        assert seg.start == 1.0
        assert seg.end == 2.0
        assert seg.confidence == 0.95

    def test_default_confidence(self):
        seg = TranscriptSegment(text="test", start=0.0, end=1.0)
        assert seg.confidence == 1.0


class TestWhisperSTT:
    def test_init_defaults(self):
        stt = WhisperSTT()
        assert stt._model_size == "base"
        assert stt._model is None

    def test_transcribe_parses_segments(self):
        mock_seg = MagicMock()
        mock_seg.text = "  hello world  "
        mock_seg.start = 0.0
        mock_seg.end = 2.0
        mock_seg.avg_logprob = -0.3

        stt = WhisperSTT()
        mock_model = MagicMock()
        mock_model.transcribe.return_value = ([mock_seg], MagicMock())
        stt._model = mock_model

        segments = stt.transcribe("/fake/audio.wav", offset=5.0)
        assert len(segments) == 1
        assert segments[0].text == "hello world"
        assert segments[0].start == 5.0
        assert segments[0].end == 7.0

    def test_transcribe_skips_empty(self):
        mock_seg = MagicMock()
        mock_seg.text = "   "
        mock_seg.start = 0.0
        mock_seg.end = 1.0
        mock_seg.avg_logprob = -0.5

        stt = WhisperSTT()
        mock_model = MagicMock()
        mock_model.transcribe.return_value = ([mock_seg], MagicMock())
        stt._model = mock_model

        segments = stt.transcribe("/fake/audio.wav")
        assert len(segments) == 0


class TestCreateSTT:
    @patch("backend.stt.WhisperSTT")
    def test_faster_whisper_alias_uses_whisper_provider(self, mock_whisper_cls):
        sentinel = object()
        mock_whisper_cls.return_value = sentinel

        with patch.dict(os.environ, {"LIVEO_STT_PROVIDER": "faster-whisper"}, clear=True):
            with patch.dict("sys.modules", {"faster_whisper": MagicMock()}):
                stt = create_stt()

        assert stt is sentinel
        mock_whisper_cls.assert_called_once_with()

    @patch("backend.stt.WhisperSTT", side_effect=ImportError)
    def test_auto_no_provider_returns_none(self, _):
        with patch.dict(os.environ, {}, clear=True):
            with patch.dict("sys.modules", {"faster_whisper": None}):
                stt = create_stt("auto")
                assert stt is None

    def test_explicit_unavailable_returns_none(self):
        stt = create_stt("nonexistent")
        assert stt is None

    def test_auto_missing_provider_warning_includes_install_command(self, caplog):
        with patch.dict(os.environ, {}, clear=True):
            with patch.dict("sys.modules", {"faster_whisper": None}):
                with caplog.at_level("WARNING"):
                    stt = create_stt("auto")

        assert stt is None
        assert 'pip install -e ".[stt]"' in caplog.text
