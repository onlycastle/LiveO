from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .detectors.gemini import GeminiHighlightResult


@dataclass
class HighlightScore:
    audio_score: float = 0.0
    keyword_score: float = 0.0
    killfeed_score: float = 0.0
    total: float = 0.0
    is_highlight: bool = False
    highlight_type: str = "none"
    title_suggestion: str = ""
    details: dict[str, Any] = field(default_factory=dict)


class HighlightAggregator:
    """Aggregate Gemini multimodal detection results.

    Accepts GeminiHighlightResult from the unified detector and converts
    to the HighlightScore used by the rest of the pipeline.
    """

    CONFIDENCE_THRESHOLD = 0.35

    def __init__(self, threshold: float = CONFIDENCE_THRESHOLD):
        self._threshold = threshold

    def aggregate(
        self,
        gemini_result: GeminiHighlightResult | None = None,
    ) -> HighlightScore:
        if gemini_result is None:
            return HighlightScore()

        # Use Gemini's own highlight judgment combined with our threshold
        is_highlight = gemini_result.is_highlight and gemini_result.confidence >= self._threshold

        return HighlightScore(
            audio_score=gemini_result.audio_excitement,
            keyword_score=gemini_result.keyword_relevance,
            killfeed_score=gemini_result.kill_event,
            total=gemini_result.confidence,
            is_highlight=is_highlight,
            highlight_type=gemini_result.highlight_type,
            title_suggestion=gemini_result.title_suggestion,
            details={
                "visual_action": gemini_result.visual_action,
                "highlight_type": gemini_result.highlight_type,
                "reasoning": gemini_result.reasoning,
                "threshold": self._threshold,
            },
        )
