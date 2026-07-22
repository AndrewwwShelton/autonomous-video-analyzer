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
