import os
from unittest.mock import MagicMock, patch

import pytest

from backend.stt import (
    BaseSTT,
    DeepgramSTT,
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


class TestDeepgramSTT:
    def test_init_with_api_key(self):
        stt = DeepgramSTT(api_key="test-key")
        assert stt._api_key == "test-key"

    @patch.dict(os.environ, {"DEEPGRAM_API_KEY": "env-key"})
    def test_init_from_env(self):
        stt = DeepgramSTT()
        assert stt._api_key == "env-key"

    def test_transcribe_parses_response(self):
        mock_word = MagicMock()
        mock_word.start = 0.5
        mock_word.end = 1.5

        mock_alt = MagicMock()
        mock_alt.transcript = "hello world"
        mock_alt.confidence = 0.99
        mock_alt.words = [mock_word]

        mock_channel = MagicMock()
        mock_channel.alternatives = [mock_alt]

        mock_response = MagicMock()
        mock_response.results.channels = [mock_channel]

        stt = DeepgramSTT(api_key="test")
        mock_client = MagicMock()
        mock_client.listen.rest.v.return_value.transcribe_file.return_value = mock_response
        stt._client = mock_client

        with patch("builtins.open", MagicMock(return_value=MagicMock(read=MagicMock(return_value=b"fake"), __enter__=MagicMock(), __exit__=MagicMock()))):
            segments = stt.transcribe("/fake/audio.wav", offset=10.0)
        assert len(segments) == 1
        assert segments[0].text == "hello world"
        assert segments[0].start == 10.5
        assert segments[0].end == 11.5
        assert segments[0].confidence == 0.99


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
    @patch.dict(os.environ, {"DEEPGRAM_API_KEY": "test"}, clear=False)
    def test_auto_selects_deepgram(self):
        with patch.dict(os.environ, {"LIVEO_STT_PROVIDER": ""}, clear=False):
            stt = create_stt("deepgram")
            assert isinstance(stt, DeepgramSTT)

    @patch("backend.stt.WhisperSTT", side_effect=ImportError)
    def test_auto_no_provider_returns_none(self, _):
        with patch.dict(os.environ, {}, clear=True):
            with patch.dict("sys.modules", {"faster_whisper": None}):
                stt = create_stt("auto")
                assert stt is None

    def test_explicit_unavailable_returns_none(self):
        stt = create_stt("nonexistent")
        assert stt is None
