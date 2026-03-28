from backend.detectors.gemini import GeminiHighlightResult
from backend.highlight_aggregator import HighlightAggregator


def _make_result(**overrides) -> GeminiHighlightResult:
    defaults = {
        "is_highlight": False,
        "confidence": 0.0,
        "audio_excitement": 0.0,
        "visual_action": 0.0,
        "keyword_relevance": 0.0,
        "kill_event": 0.0,
        "highlight_type": "none",
        "title_suggestion": "",
        "reasoning": "test",
    }
    defaults.update(overrides)
    return GeminiHighlightResult(**defaults)


def test_none_result_returns_empty():
    agg = HighlightAggregator()
    result = agg.aggregate(gemini_result=None)
    assert result.total == 0.0
    assert result.is_highlight is False


def test_low_confidence_not_highlight():
    agg = HighlightAggregator()
    result = agg.aggregate(gemini_result=_make_result(
        is_highlight=True,
        confidence=0.2,
    ))
    assert result.is_highlight is False


def test_high_confidence_highlight():
    agg = HighlightAggregator()
    result = agg.aggregate(gemini_result=_make_result(
        is_highlight=True,
        confidence=0.8,
        audio_excitement=0.7,
        keyword_relevance=0.5,
        highlight_type="epic_play",
        title_suggestion="Insane Clutch!",
    ))
    assert result.is_highlight is True
    assert result.total == 0.8
    assert result.audio_score == 0.7
    assert result.keyword_score == 0.5
    assert result.highlight_type == "epic_play"
    assert result.title_suggestion == "Insane Clutch!"


def test_gemini_says_no_highlight():
    agg = HighlightAggregator()
    result = agg.aggregate(gemini_result=_make_result(
        is_highlight=False,
        confidence=0.6,
        audio_excitement=0.4,
    ))
    assert result.is_highlight is False


def test_scores_propagated():
    agg = HighlightAggregator()
    result = agg.aggregate(gemini_result=_make_result(
        is_highlight=True,
        confidence=0.9,
        audio_excitement=0.8,
        keyword_relevance=0.6,
        kill_event=0.5,
        visual_action=0.7,
    ))
    assert result.audio_score == 0.8
    assert result.keyword_score == 0.6
    assert result.killfeed_score == 0.5
    assert result.details["visual_action"] == 0.7


def test_custom_threshold():
    agg = HighlightAggregator(threshold=0.9)
    result = agg.aggregate(gemini_result=_make_result(
        is_highlight=True,
        confidence=0.8,
    ))
    assert result.is_highlight is False

    result2 = agg.aggregate(gemini_result=_make_result(
        is_highlight=True,
        confidence=0.95,
    ))
    assert result2.is_highlight is True
