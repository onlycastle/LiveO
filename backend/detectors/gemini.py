from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class GeminiHighlightResult(BaseModel):
    """Structured result from Gemini multimodal highlight analysis."""

    is_highlight: bool = Field(description="Whether this segment is a highlight worth clipping")
    confidence: float = Field(ge=0.0, le=1.0, description="Overall highlight confidence 0-1")
    audio_excitement: float = Field(ge=0.0, le=1.0, description="Audio excitement level: caster hype, crowd noise, streamer reaction")
    visual_action: float = Field(ge=0.0, le=1.0, description="Visual intensity: kill feed, explosions, fast action, HUD changes")
    keyword_relevance: float = Field(ge=0.0, le=1.0, description="Keyword/phrase relevance from speech: ace, clutch, clip-worthy callouts")
    kill_event: float = Field(ge=0.0, le=1.0, description="Kill/elimination event confidence from killfeed or announcements")
    highlight_type: str = Field(description="Category: kill_streak, clutch, funny_moment, epic_play, fail, hype_moment, none")
    title_suggestion: str = Field(description="Short catchy title for this highlight clip, max 60 chars")
    reasoning: str = Field(description="Brief explanation of the analysis in 1-2 sentences")


_MULTIMODAL_SYSTEM_PROMPT = """\
You are a live-stream highlight detector for gaming content. You receive a short audio clip \
and a video frame from the same stream segment.

Analyze BOTH the audio (streamer voice, crowd noise, game sounds, excitement level) \
and the video frame (kill feed, HUD state, action intensity, visual events) together.

Score each dimension independently on a 0.0-1.0 scale:
- audio_excitement: voice pitch/volume spikes, crowd reactions, hype sounds
- visual_action: kill feed entries, explosions, fast movement, dramatic HUD changes
- keyword_relevance: highlight-worthy phrases ("ace", "clutch", "let's go", "clip that", etc.)
- kill_event: confirmed kill/elimination events visible or audible

Set is_highlight=true if the segment is clip-worthy. Be selective — only flag genuine highlights, \
not routine gameplay. A score of 0.5+ on any single dimension with supporting evidence from \
another dimension is a good highlight.

For highlight_type, choose the most fitting category:
kill_streak, clutch, funny_moment, epic_play, fail, hype_moment, none

Provide a catchy title_suggestion (max 60 chars) suitable for a YouTube Short."""

_MULTIMODAL_USER_PROMPT = (
    "Analyze this stream segment using the provided media and return only JSON that matches "
    "the supplied schema."
)

_TEXT_ONLY_SYSTEM_PROMPT = """\
You are a live-stream highlight detector for gaming content. You receive only a transcript \
line from a short stream segment, with no audio waveform or video frame attached.

Infer keyword_relevance from the transcript content. Infer audio_excitement only from explicit \
textual cues such as shouted phrases, all-caps, excited wording, or celebratory language.

Because no image or raw audio is provided, keep visual_action and kill_event low unless the \
transcript explicitly confirms a visual or kill event. If the transcript contains no clear \
highlight signal, set is_highlight=false and highlight_type=none.

For highlight_type, choose the most fitting category:
kill_streak, clutch, funny_moment, epic_play, fail, hype_moment, none

Provide a catchy title_suggestion (max 60 chars) only when the text suggests a real highlight."""


class GeminiDetector:
    """Multimodal highlight detector using Google Gemini API.

    Sends audio + video frame to Gemini for unified analysis.
    Replaces separate AudioExcitement, Keyword, and KillfeedOCR detectors.
    """

    MODEL = "gemini-3-flash-preview"

    def __init__(self, api_key: str | None = None):
        self._api_key = api_key or os.environ.get("GEMINI_API_KEY", "")
        self._client = None

    def _get_client(self):
        if self._client is None:
            from google import genai

            self._client = genai.Client(api_key=self._api_key)
        return self._client

    @property
    def available(self) -> bool:
        return bool(self._api_key)

    @staticmethod
    def _supports_config_field(config_cls: Any, field_name: str) -> bool:
        model_fields = getattr(config_cls, "model_fields", None)
        return isinstance(model_fields, dict) and field_name in model_fields

    @classmethod
    def _build_generation_config(cls, types_module: Any, *, system_instruction: str) -> Any:
        config_kwargs: dict[str, Any] = {
            "system_instruction": system_instruction,
            "response_mime_type": "application/json",
        }

        if cls._supports_config_field(types_module.GenerateContentConfig, "thinking_config") and hasattr(types_module, "ThinkingConfig"):
            if cls.MODEL.startswith("gemini-3"):
                config_kwargs["thinking_config"] = types_module.ThinkingConfig(thinking_level="minimal")
            else:
                config_kwargs["thinking_config"] = types_module.ThinkingConfig(thinking_budget=0)

        if cls._supports_config_field(types_module.GenerateContentConfig, "response_json_schema"):
            config_kwargs["response_json_schema"] = GeminiHighlightResult.model_json_schema()
        else:
            config_kwargs["response_schema"] = GeminiHighlightResult

        return types_module.GenerateContentConfig(**config_kwargs)

    @staticmethod
    def _parse_response(response: Any) -> GeminiHighlightResult:
        parsed = getattr(response, "parsed", None)
        if isinstance(parsed, GeminiHighlightResult):
            return parsed
        if isinstance(parsed, dict):
            return GeminiHighlightResult.model_validate(parsed)
        if isinstance(parsed, str) and parsed:
            return GeminiHighlightResult.model_validate_json(parsed)

        text = getattr(response, "text", None)
        if isinstance(text, str) and text:
            return GeminiHighlightResult.model_validate_json(text)

        raise ValueError("Gemini response did not include structured JSON output")

    def analyze(
        self,
        audio_path: str | None = None,
        frame_path: str | None = None,
    ) -> GeminiHighlightResult:
        """Analyze audio and/or video frame for highlight signals.

        At least one of audio_path or frame_path must be provided.
        """
        from google.genai import types

        client = self._get_client()
        media_parts: list[Any] = []

        if audio_path and Path(audio_path).is_file():
            audio_bytes = Path(audio_path).read_bytes()
            media_parts.append(types.Part.from_bytes(data=audio_bytes, mime_type="audio/wav"))

        if frame_path and Path(frame_path).is_file():
            frame_bytes = Path(frame_path).read_bytes()
            suffix = Path(frame_path).suffix.lower()
            mime = "image/png" if suffix == ".png" else "image/jpeg"
            media_parts.append(types.Part.from_bytes(data=frame_bytes, mime_type=mime))

        if not media_parts:
            return GeminiHighlightResult(
                is_highlight=False,
                confidence=0.0,
                audio_excitement=0.0,
                visual_action=0.0,
                keyword_relevance=0.0,
                kill_event=0.0,
                highlight_type="none",
                title_suggestion="",
                reasoning="No audio or video input provided",
            )

        contents = [
            types.Part.from_text(text=_MULTIMODAL_USER_PROMPT),
            *media_parts,
        ]

        response = client.models.generate_content(
            model=self.MODEL,
            contents=contents,
            config=self._build_generation_config(
                types,
                system_instruction=_MULTIMODAL_SYSTEM_PROMPT,
            ),
        )

        return self._parse_response(response)

    def analyze_text(self, text: str) -> GeminiHighlightResult:
        """Analyze transcript text only (no audio/video).

        Lightweight fallback for keyword-style detection on STT output.
        """
        from google.genai import types

        client = self._get_client()

        transcript = text.strip()
        if not transcript:
            return GeminiHighlightResult(
                is_highlight=False,
                confidence=0.0,
                audio_excitement=0.0,
                visual_action=0.0,
                keyword_relevance=0.0,
                kill_event=0.0,
                highlight_type="none",
                title_suggestion="",
                reasoning="No transcript text provided",
            )

        prompt = (
            "Analyze this transcript-only stream segment and return only JSON that matches the "
            "supplied schema.\n\n"
            f'Transcript: "{transcript}"'
        )

        response = client.models.generate_content(
            model=self.MODEL,
            contents=[types.Part.from_text(text=prompt)],
            config=self._build_generation_config(
                types,
                system_instruction=_TEXT_ONLY_SYSTEM_PROMPT,
            ),
        )

        return self._parse_response(response)
