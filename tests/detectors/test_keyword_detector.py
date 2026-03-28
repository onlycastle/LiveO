from backend.detectors.keyword import KeywordDetector


def test_ace_keyword():
    det = KeywordDetector()
    result = det.analyze("Oh my god ACE!!!")
    assert result["score"] == 1.0
    keywords = [m["keyword"] for m in result["matched_keywords"]]
    assert "ace" in keywords
    assert "oh my god" in keywords


def test_no_keywords():
    det = KeywordDetector()
    result = det.analyze("Just walking around the map")
    assert result["score"] == 0.0
    assert len(result["matched_keywords"]) == 0


def test_multiple_keywords():
    det = KeywordDetector()
    result = det.analyze("Insane clutch! No way that just happened!")
    assert result["score"] >= 0.7
    assert len(result["matched_keywords"]) >= 2


def test_case_insensitive():
    det = KeywordDetector()
    result = det.analyze("HEADSHOT!!!")
    assert result["score"] > 0.0


def test_custom_keywords():
    det = KeywordDetector(keywords={"pogchamp": 1.0, "sadge": 0.5})
    result = det.analyze("POGCHAMP moment")
    assert result["score"] == 1.0
