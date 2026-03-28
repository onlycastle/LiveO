from __future__ import annotations


HIGHLIGHT_KEYWORDS: dict[str, float] = {
    "ace": 1.0,
    "clutch": 1.0,
    "insane": 0.9,
    "incredible": 0.9,
    "unbelievable": 0.9,
    "triple kill": 1.0,
    "quadra kill": 1.0,
    "penta kill": 1.0,
    "headshot": 0.8,
    "no way": 0.7,
    "oh my god": 0.8,
    "omg": 0.7,
    "let's go": 0.6,
    "gg": 0.5,
    "clutched": 0.9,
    "crazy": 0.6,
    "insane play": 1.0,
    "highlight": 0.7,
    "clip that": 0.8,
    "clip it": 0.8,
}


class KeywordDetector:
    """Detect highlight keywords in transcript text."""

    def __init__(self, keywords: dict[str, float] | None = None):
        self._keywords = keywords or HIGHLIGHT_KEYWORDS

    def analyze(self, text: str) -> dict:
        """Analyze text for highlight keywords.

        Returns dict with keys: matched_keywords, max_score, score (0-1)
        """
        text_lower = text.lower()
        matched = []
        max_score = 0.0

        for keyword, weight in self._keywords.items():
            if keyword in text_lower:
                matched.append({"keyword": keyword, "weight": weight})
                max_score = max(max_score, weight)

        return {
            "matched_keywords": matched,
            "max_score": max_score,
            "score": max_score,
        }
