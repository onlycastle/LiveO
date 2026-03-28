from backend.detectors.killfeed_ocr import KillfeedOCRDetector


def test_analyze_text_with_kill():
    det = KillfeedOCRDetector()
    result = det.analyze_text("Player1 killed Player2")
    assert result["kill_detected"] is True
    assert result["score"] > 0.0


def test_analyze_text_no_kill():
    det = KillfeedOCRDetector()
    result = det.analyze_text("Player1 picked up AWP")
    assert result["kill_detected"] is False
    assert result["score"] == 0.0


def test_analyze_text_multiple_kills():
    det = KillfeedOCRDetector()
    result = det.analyze_text("Player1 eliminated Player2, headshot!")
    assert result["kill_detected"] is True
    assert result["score"] >= 0.5


def test_analyze_nonexistent_image():
    det = KillfeedOCRDetector()
    result = det.analyze("/nonexistent/frame.png")
    assert result["kill_detected"] is False
