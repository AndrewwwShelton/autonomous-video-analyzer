from src.audio.compliance import match_transcript
from src.audio.transcriber import WordStamp


def _words(text: str, step: float = 0.5) -> list[WordStamp]:
    return [WordStamp(w, i * step, i * step + 0.3) for i, w in enumerate(text.split())]


DICT = [
    {"word": "damn", "severity": "Low"},
    {"word": "gun", "severity": "High"},
    {"word": "prop weapon", "severity": "Medium"},
]


def test_matches_single_word_with_timestamps():
    flags = match_transcript(_words("well damn that worked"), DICT)
    assert len(flags) == 1
    f = flags[0]
    assert f["word_flagged"] == "damn"
    assert f["severity"] == "Low"
    assert f["timestamp_start"] == 0.5
    assert f["timestamp_end"] == 0.8


def test_word_boundary_no_scunthorpe():
    # "gunmetal" must not fire the "gun" rule; "Gun!" (punctuation/case) must.
    flags = match_transcript(_words("the gunmetal finish looks great Gun!"), DICT)
    assert len(flags) == 1
    assert flags[0]["timestamp_start"] == _words("the gunmetal finish looks great Gun!")[5].start


def test_multiword_phrase():
    flags = match_transcript(_words("we moved the prop weapon off camera"), DICT)
    assert [f["word_flagged"] for f in flags] == ["prop weapon"]
    assert flags[0]["severity"] == "Medium"


def test_context_window_contains_match():
    flags = match_transcript(_words("zero one two three four five damn six seven"), DICT)
    assert "damn" in flags[0]["transcript_context"]
    assert "zero" not in flags[0]["transcript_context"]  # outside the ±5 window
