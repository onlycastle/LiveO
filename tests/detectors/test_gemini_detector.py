from __future__ import annotations

import sys
from types import ModuleType, SimpleNamespace
from unittest.mock import MagicMock

import pytest

import backend.detectors.gemini as gemini_mod
from backend.detectors.gemini import GeminiDetector, GeminiHighlightResult


def _install_fake_google_genai(monkeypatch, *, supports_response_json_schema: bool = True):
    class FakePart:
        @staticmethod
        def from_bytes(*, data, mime_type):
            return {
                "kind": "bytes",
                "data": data,
                "mime_type": mime_type,
            }

        @staticmethod
        def from_text(*, text):
            return {
                "kind": "text",
                "text": text,
            }

    class FakeThinkingConfig:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    model_fields = {
        "system_instruction": object(),
        "response_mime_type": object(),
        "thinking_config": object(),
        "response_json_schema" if supports_response_json_schema else "response_schema": object(),
    }

    class FakeGenerateContentConfig:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    FakeGenerateContentConfig.model_fields = model_fields

    fake_types = SimpleNamespace(
        Part=FakePart,
        ThinkingConfig=FakeThinkingConfig,
        GenerateContentConfig=FakeGenerateContentConfig,
    )
    fake_genai = ModuleType("google.genai")
    fake_genai.types = fake_types
    fake_google = ModuleType("google")
    fake_google.genai = fake_genai

    monkeypatch.setitem(sys.modules, "google", fake_google)
    monkeypatch.setitem(sys.modules, "google.genai", fake_genai)

    return fake_types


def test_not_available_without_api_key(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    detector = GeminiDetector(api_key="")
    assert detector.available is False


def test_available_with_api_key():
    detector = GeminiDetector(api_key="test-key")
    assert detector.available is True


def test_analyze_returns_empty_when_no_inputs():
    detector = GeminiDetector(api_key="test-key")
    result = detector.analyze(audio_path=None, frame_path=None)
    assert result.is_highlight is False
    assert result.confidence == 0.0
    assert result.reasoning == "No audio or video input provided"


def test_analyze_returns_empty_for_nonexistent_files():
    detector = GeminiDetector(api_key="test-key")
    result = detector.analyze(
        audio_path="/nonexistent/audio.wav",
        frame_path="/nonexistent/frame.jpg",
    )
    assert result.is_highlight is False
    assert result.confidence == 0.0


def test_analyze_calls_gemini_api(monkeypatch, tmp_path):
    _install_fake_google_genai(monkeypatch)

    audio_file = tmp_path / "test.wav"
    audio_file.write_bytes(b"\x00" * 100)
    frame_file = tmp_path / "test.jpg"
    frame_file.write_bytes(b"\x00" * 100)

    mock_response = MagicMock()
    mock_response.parsed = None
    mock_response.text = GeminiHighlightResult(
        is_highlight=True,
        confidence=0.9,
        audio_excitement=0.8,
        visual_action=0.7,
        keyword_relevance=0.5,
        kill_event=0.6,
        highlight_type="epic_play",
        title_suggestion="Amazing Play!",
        reasoning="High excitement audio with visual action",
    ).model_dump_json()

    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = mock_response

    detector = GeminiDetector(api_key="test-key")
    detector._client = mock_client

    result = detector.analyze(
        audio_path=str(audio_file),
        frame_path=str(frame_file),
    )

    assert result.is_highlight is True
    assert result.confidence == 0.9
    assert result.highlight_type == "epic_play"
    mock_client.models.generate_content.assert_called_once()

    call = mock_client.models.generate_content.call_args
    assert call.kwargs["model"] == "gemini-3-flash-preview"

    contents = call.kwargs["contents"]
    assert contents[0]["text"] == gemini_mod._MULTIMODAL_USER_PROMPT
    assert contents[1]["mime_type"] == "audio/wav"
    assert contents[2]["mime_type"] == "image/jpeg"

    config = call.kwargs["config"]
    assert config.kwargs["system_instruction"] == gemini_mod._MULTIMODAL_SYSTEM_PROMPT
    assert config.kwargs["response_mime_type"] == "application/json"
    assert config.kwargs["response_json_schema"] == GeminiHighlightResult.model_json_schema()
    assert config.kwargs["thinking_config"].kwargs == {"thinking_level": "minimal"}


def test_analyze_text_calls_gemini_api(monkeypatch):
    _install_fake_google_genai(monkeypatch)

    mock_response = MagicMock()
    mock_response.parsed = None
    mock_response.text = GeminiHighlightResult(
        is_highlight=True,
        confidence=0.7,
        audio_excitement=0.3,
        visual_action=0.0,
        keyword_relevance=0.9,
        kill_event=0.0,
        highlight_type="hype_moment",
        title_suggestion="Let's Go!",
        reasoning="High keyword relevance from excited speech",
    ).model_dump_json()

    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = mock_response

    detector = GeminiDetector(api_key="test-key")
    detector._client = mock_client

    result = detector.analyze_text("OH MY GOD ACE! CLIP THAT!")

    assert result.is_highlight is True
    assert result.keyword_relevance == 0.9
    mock_client.models.generate_content.assert_called_once()

    call = mock_client.models.generate_content.call_args
    assert call.kwargs["model"] == "gemini-3-flash-preview"
    assert "OH MY GOD ACE! CLIP THAT!" in call.kwargs["contents"][0]["text"]

    config = call.kwargs["config"]
    assert config.kwargs["system_instruction"] == gemini_mod._TEXT_ONLY_SYSTEM_PROMPT
    assert config.kwargs["thinking_config"].kwargs == {"thinking_level": "minimal"}


def test_analyze_uses_parsed_response_when_available(monkeypatch, tmp_path):
    _install_fake_google_genai(monkeypatch)

    audio_file = tmp_path / "test.wav"
    audio_file.write_bytes(b"\x00" * 100)

    mock_response = MagicMock()
    mock_response.parsed = {
        "is_highlight": True,
        "confidence": 0.65,
        "audio_excitement": 0.5,
        "visual_action": 0.2,
        "keyword_relevance": 0.4,
        "kill_event": 0.1,
        "highlight_type": "hype_moment",
        "title_suggestion": "Big Reaction",
        "reasoning": "Transcript and audio suggest excitement",
    }
    mock_response.text = None

    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = mock_response

    detector = GeminiDetector(api_key="test-key")
    detector._client = mock_client

    result = detector.analyze(audio_path=str(audio_file), frame_path=None)

    assert result.is_highlight is True
    assert result.highlight_type == "hype_moment"


def test_analyze_falls_back_to_response_schema_for_older_sdk(monkeypatch, tmp_path):
    _install_fake_google_genai(monkeypatch, supports_response_json_schema=False)

    audio_file = tmp_path / "test.wav"
    audio_file.write_bytes(b"\x00" * 100)

    mock_response = MagicMock()
    mock_response.parsed = None
    mock_response.text = GeminiHighlightResult(
        is_highlight=False,
        confidence=0.2,
        audio_excitement=0.1,
        visual_action=0.0,
        keyword_relevance=0.2,
        kill_event=0.0,
        highlight_type="none",
        title_suggestion="",
        reasoning="Low signal",
    ).model_dump_json()

    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = mock_response

    detector = GeminiDetector(api_key="test-key")
    detector._client = mock_client

    detector.analyze(audio_path=str(audio_file), frame_path=None)

    config = mock_client.models.generate_content.call_args.kwargs["config"]
    assert config.kwargs["response_schema"] is GeminiHighlightResult


def test_highlight_result_validation():
    result = GeminiHighlightResult(
        is_highlight=True,
        confidence=0.85,
        audio_excitement=0.7,
        visual_action=0.6,
        keyword_relevance=0.5,
        kill_event=0.4,
        highlight_type="clutch",
        title_suggestion="1v5 Clutch!",
        reasoning="test",
    )
    assert result.confidence == 0.85
    assert result.highlight_type == "clutch"

    # Test JSON roundtrip
    json_str = result.model_dump_json()
    parsed = GeminiHighlightResult.model_validate_json(json_str)
    assert parsed == result
