from __future__ import annotations

import importlib.util
from pathlib import Path


class KillfeedOCRDetector:
    """Detect kill events via OCR on game killfeed region."""

    # Killfeed keywords to detect
    KILL_KEYWORDS = ["killed", "eliminated", "headshot", "knocked", "finished"]

    def __init__(self):
        self._reader = None

    def _get_reader(self):
        if self._reader is None:
            if not importlib.util.find_spec("easyocr"):
                return None
            import easyocr
            self._reader = easyocr.Reader(["en"], gpu=False, verbose=False)
        return self._reader

    def analyze(self, frame_path: str, roi: tuple[int, int, int, int] | None = None) -> dict:
        """Analyze a frame image for killfeed text.

        Args:
            frame_path: Path to frame image
            roi: Optional (x, y, w, h) region of interest for killfeed area

        Returns dict with keys: texts, kill_detected, score (0-1)
        """
        reader = self._get_reader()
        if reader is None:
            return {"texts": [], "kill_detected": False, "score": 0.0}

        try:
            import cv2
            img = cv2.imread(frame_path)
            if img is None:
                return {"texts": [], "kill_detected": False, "score": 0.0}

            if roi:
                x, y, w, h = roi
                img = img[y:y+h, x:x+w]

            results = reader.readtext(img)
            texts = [text for _, text, conf in results if conf > 0.3]

            # Check for kill keywords
            combined = " ".join(texts).lower()
            kills_found = sum(1 for kw in self.KILL_KEYWORDS if kw in combined)
            kill_detected = kills_found > 0
            score = min(1.0, kills_found * 0.5)

            return {
                "texts": texts,
                "kill_detected": kill_detected,
                "score": score,
            }
        except Exception:
            return {"texts": [], "kill_detected": False, "score": 0.0}

    def analyze_text(self, text: str) -> dict:
        """Analyze pre-extracted text for kill events (no OCR needed)."""
        text_lower = text.lower()
        kills_found = sum(1 for kw in self.KILL_KEYWORDS if kw in text_lower)
        kill_detected = kills_found > 0
        score = min(1.0, kills_found * 0.5)
        return {
            "texts": [text],
            "kill_detected": kill_detected,
            "score": score,
        }
