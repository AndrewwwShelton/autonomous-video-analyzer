import sqlite3

import pytest

from src.db import repository as repo
from src.db.connection import init_db


@pytest.fixture()
def db(tmp_path):
    path = tmp_path / "test.db"
    init_db(path)
    return path


def _video(db) -> int:
    return repo.insert_video("clip.mp4", "/tmp/clip.mp4", 12.5, 36.0, 24.0, 960, 540,
                             db_path=db)


def test_video_roundtrip_and_status(db):
    vid = _video(db)
    v = repo.get_video(vid, db_path=db)
    assert v["filename"] == "clip.mp4"
    assert v["processed_status"] == "pending"
    repo.update_video_status(vid, "completed", db_path=db)
    assert repo.get_video(vid, db_path=db)["processed_status"] == "completed"


def test_flags_roundtrip(db):
    vid = _video(db)
    repo.insert_audio_flags(vid, [{
        "timestamp_start": 1.0, "timestamp_end": 1.4, "word_flagged": "damn",
        "transcript_context": "well damn", "severity": "Low"}], db_path=db)
    repo.insert_visual_flags(vid, [{
        "frame_timestamp": 5.0, "object_detected": "knife",
        "bounding_box": [1, 2, 3, 4], "confidence_score": 0.9,
        "risk_category": "Weapon"}], db_path=db)
    repo.insert_ad_spots(vid, [{
        "timestamp_start": 3.0, "timestamp_end": 9.0, "spot_type": "blank_wall",
        "bounding_box": [10, 20, 30, 40], "area_pixels": 400.0,
        "suitability_score": 0.8}], db_path=db)

    assert repo.get_audio_flags(vid, db_path=db)[0]["severity"] == "Low"
    assert repo.get_visual_flags(vid, db_path=db)[0]["bounding_box_json"] == "[1, 2, 3, 4]"
    assert repo.get_ad_spots(vid, db_path=db)[0]["spot_type"] == "blank_wall"

    repo.clear_analysis(vid, db_path=db)
    assert repo.get_audio_flags(vid, db_path=db) == []


def test_fk_enforced(db):
    with pytest.raises(sqlite3.IntegrityError):
        repo.insert_audio_flags(9999, [{
            "timestamp_start": 0, "timestamp_end": 1,
            "word_flagged": "x", "severity": "Low"}], db_path=db)


def test_severity_check_constraint(db):
    vid = _video(db)
    with pytest.raises(sqlite3.IntegrityError):
        repo.insert_audio_flags(vid, [{
            "timestamp_start": 0, "timestamp_end": 1,
            "word_flagged": "x", "severity": "Catastrophic"}], db_path=db)


def test_config_type_coercion(db):
    assert repo.get_config("frame_sample_fps", db_path=db) == 1.0
    assert isinstance(repo.get_config("profanity_dictionary", db_path=db), list)
    repo.set_config("frame_sample_fps", 2.0, "float", db_path=db)
    assert repo.get_config("frame_sample_fps", db_path=db) == 2.0


def test_cascade_delete(db):
    vid = _video(db)
    repo.insert_audio_flags(vid, [{
        "timestamp_start": 0, "timestamp_end": 1,
        "word_flagged": "x", "severity": "Low"}], db_path=db)
    repo.delete_video(vid, db_path=db)
    assert repo.get_audio_flags(vid, db_path=db) == []


# --------------------------------------------- dictionary upgrade migration

def _dict_words(db):
    return {e["word"].lower() for e in repo.get_config("profanity_dictionary", db_path=db)}


def test_untouched_dictionary_is_upgraded_in_place(db, tmp_path):
    """Config seeds with INSERT OR IGNORE, so a widened vocabulary would never
    reach an existing library — the only place it matters."""
    import json
    from src.db.connection import (_ORIGINAL_DICTIONARY_WORDS, get_connection,
                                   init_db)
    with get_connection(db) as conn:
        conn.execute(
            "UPDATE SystemConfig SET config_value = ? WHERE config_key = 'profanity_dictionary'",
            (json.dumps([{"word": w, "severity": "Low"}
                         for w in sorted(_ORIGINAL_DICTIONARY_WORDS)]),))
    init_db(db)
    words = _dict_words(db)
    assert "semi automatic" in words and "fully auto" in words, words
    assert len(words) > len(_ORIGINAL_DICTIONARY_WORDS)


def test_a_customised_dictionary_is_never_overwritten(db):
    """Silently discarding somebody's curated list is worse than leaving it stale."""
    import json
    from src.db.connection import get_connection, init_db
    mine = [{"word": "sponsorname", "severity": "High"}]
    with get_connection(db) as conn:
        conn.execute(
            "UPDATE SystemConfig SET config_value = ? WHERE config_key = 'profanity_dictionary'",
            (json.dumps(mine),))
    init_db(db)
    assert _dict_words(db) == {"sponsorname"}


def test_firearms_vocabulary_covers_how_people_actually_speak(db):
    """Regression from a real clip: an ATF firing-range video transcribed cleanly
    as "this is semi-automatic ... pull of the trigger ... fully auto" and matched
    nothing, because the list held only profanity plus three risk words.

    `trigger` is deliberately absent — see
    test_high_severity_is_reserved_for_unambiguous_terms."""
    words = _dict_words(db)
    for phrase in ("semi automatic", "fully auto", "gunshot", "handgun"):
        assert phrase in words, f"{phrase!r} missing from the default dictionary"


def test_high_severity_is_reserved_for_unambiguous_terms(db):
    """A single High-severity spoken term restricts a video on its own, so an
    ambiguous word carrying High severity is a false-positive machine.

    Measured against ordinary creator speech, the previous list produced HIGH
    flags for "we were shooting all day", "kill the lights" and "the render
    killed my laptop" -- all of which would have restricted the video.
    """
    from src.audio.compliance import match_transcript
    from src.audio.transcriber import WordStamp

    benign = [
        "that will trigger a rebuild once the pipeline finishes",
        "we were shooting all day and the lighting was gorgeous",
        "this colour grade is absolutely killing it right now",
        "kill the lights and we will go again from the top",
        "the render killed my laptop but the output looks clean",
        "this soundtrack is an assault on the ears honestly",
        "let me shoot you a message after the stream",
    ]
    dictionary = repo.get_config("profanity_dictionary", db_path=db)
    for line in benign:
        words = [WordStamp(w, i * 0.4, i * 0.4 + 0.3)
                 for i, w in enumerate(line.split())]
        flags = match_transcript(words, dictionary, detection_model="test")
        high = [f["word_flagged"] for f in flags if f["severity"] == "High"]
        assert not high, f"{high} restricts an innocent clip: {line!r}"


def test_firearms_discussion_still_restricts(db):
    """The counterpart: demoting ambiguous words must not disarm the dictionary.
    This is the real ATF firing-range transcript."""
    from src.audio.compliance import match_transcript
    from src.audio.transcriber import WordStamp

    line = ("So this is semi -automatic, a single pull of the trigger, and I will "
            "do three shots, and then this, again, is turning it on fully auto.")
    words = [WordStamp(w, i * 0.4, i * 0.4 + 0.3) for i, w in enumerate(line.split())]
    flags = match_transcript(words, repo.get_config("profanity_dictionary", db_path=db),
                             detection_model="test")
    high = {f["word_flagged"] for f in flags if f["severity"] == "High"}
    assert high == {"semi automatic", "fully auto"}, high


def test_the_previous_shipped_dictionary_is_also_upgraded(db):
    """Recognising only the first-ever default would strand every database
    seeded by an intermediate version one release behind."""
    import json

    from src.db.connection import _SHIPPED_DICTIONARIES, get_connection, init_db
    assert len(_SHIPPED_DICTIONARIES) >= 2
    with get_connection(db) as conn:
        conn.execute(
            "UPDATE SystemConfig SET config_value = ? WHERE config_key = 'profanity_dictionary'",
            (json.dumps([{"word": w, "severity": "High"}
                         for w in sorted(_SHIPPED_DICTIONARIES[1])]),))
    init_db(db)
    words = {e["word"] for e in repo.get_config("profanity_dictionary", db_path=db)}
    assert "shooting range" in words and "shooting" not in words
