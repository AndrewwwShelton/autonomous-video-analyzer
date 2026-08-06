"""Compliance verdict, including the gameplay-context rule.

The original rule was a bare `any()`: one weapon detection in one frame of a
ten-minute video restricted the whole thing, whether the weapon was real or
rendered inside a game. These tests pin the replacement, and in particular pin
the things it must NOT do — a context rule that is too eager would dismiss real
weapon footage as gameplay, which is worse than the over-flagging it replaces.
"""
import pytest

from src import config
from src.db import repository as repo
from src.db.connection import init_db
from src.pipeline.orchestrator import assess_compliance, compliance_verdict


@pytest.fixture()
def tmp_db(tmp_path):
    """A scratch database that assess_compliance() will also see.

    The verdict helpers take no db_path — they resolve config.DB_PATH per call —
    so the module constant is swapped for the test, the same approach the
    benchmark runner uses to isolate its scratch runs.
    """
    path = tmp_path / "verdict.db"
    init_db(path)
    original = config.DB_PATH
    config.DB_PATH = path
    try:
        yield path
    finally:
        config.DB_PATH = original


@pytest.fixture()
def video(tmp_db):
    return repo.insert_video("clip.mp4", "clip.mp4", 1.0, 600.0, 30.0, 1920, 1080,
                             db_path=tmp_db)


def _weapon(ts=312.0):
    return {"frame_timestamp": ts, "object_detected": "Rifle",
            "bounding_box": [800, 400, 1000, 520], "confidence_score": 0.71,
            "risk_category": "Weapon"}


def _hud(confidence=0.9, regions=3):
    return {"verdict": "overlay", "confidence": confidence, "region_count": regions,
            "reason": "3 fixed graphical regions persist while 98% of the picture moves.",
            "overlay_coverage": 0.07, "motion_ratio": 0.98, "frames_analysed": 40,
            "regions": []}


# ------------------------------------------------------------- the core change

def test_weapon_without_overlay_context_is_restricted(video, tmp_db):
    """Unchanged behaviour for ordinary footage."""
    repo.insert_visual_flags(video, [_weapon()], db_path=tmp_db)
    assert compliance_verdict(video) == "Restricted"


def test_weapon_with_game_interface_is_sent_for_review(video, tmp_db):
    """The Fortnite case: weapons present, but drawn inside a game."""
    repo.insert_visual_flags(video, [_weapon()], db_path=tmp_db)
    repo.set_overlay_context(video, _hud(), db_path=tmp_db)
    result = assess_compliance(video)
    assert result["verdict"] == "Review"
    assert "human should confirm" in result["reason"]


def test_review_still_records_every_flag(video, tmp_db):
    """Context changes the verdict, never the evidence. A weapon that was
    detected must remain visible whatever the verdict says."""
    repo.insert_visual_flags(video, [_weapon(), _weapon(400.0)], db_path=tmp_db)
    repo.set_overlay_context(video, _hud(), db_path=tmp_db)
    assert compliance_verdict(video) == "Review"
    assert len(repo.get_visual_flags(video, db_path=tmp_db)) == 2
    assert assess_compliance(video)["weapon_flags"] == 2


def test_clean_video_is_monetizable(video, tmp_db):
    assert compliance_verdict(video) == "Monetizable"


# --------------------------------------------------- limits of the exemption

def test_overlay_never_excuses_spoken_terms(video, tmp_db):
    """A HUD says nothing about what was said. Gameplay commentary containing a
    high-severity term is still restricted."""
    repo.insert_audio_flags(video, [{
        "timestamp_start": 10.0, "timestamp_end": 10.4, "word_flagged": "kill",
        "transcript_context": "...", "severity": "High",
        "detection_model": "faster-whisper-base.en",
    }], db_path=tmp_db)
    repo.set_overlay_context(video, _hud(), db_path=tmp_db)
    assert compliance_verdict(video) == "Restricted"


def test_single_region_watermark_does_not_excuse_a_weapon(video, tmp_db):
    """A channel bug is an overlay but not evidence of rendered content. Treating
    it as such would let any watermarked video carry weapons unchallenged."""
    repo.insert_visual_flags(video, [_weapon()], db_path=tmp_db)
    repo.set_overlay_context(video, _hud(confidence=0.9, regions=1), db_path=tmp_db)
    assert compliance_verdict(video) == "Restricted"


def test_low_confidence_overlay_does_not_excuse_a_weapon(video, tmp_db):
    repo.insert_visual_flags(video, [_weapon()], db_path=tmp_db)
    repo.set_overlay_context(video, _hud(confidence=0.2), db_path=tmp_db)
    assert compliance_verdict(video) == "Restricted"


def test_inconclusive_overlay_does_not_excuse_a_weapon(video, tmp_db):
    """Low-motion footage cannot be judged, and 'cannot tell' must never be read
    as 'it is a game'."""
    repo.insert_visual_flags(video, [_weapon()], db_path=tmp_db)
    repo.set_overlay_context(video, {
        "verdict": "inconclusive", "confidence": 0.0, "region_count": 0,
        "reason": "only 13% of the picture changes over time.",
    }, db_path=tmp_db)
    assert compliance_verdict(video) == "Restricted"


def test_reanalysis_clears_stale_overlay_evidence(video, tmp_db):
    """Otherwise a gameplay finding from an earlier run would soften the verdict
    on a re-run that never established it."""
    repo.set_overlay_context(video, _hud(), db_path=tmp_db)
    repo.clear_analysis(video, db_path=tmp_db)
    assert repo.get_overlay_context(video, db_path=tmp_db) is None


# ------------------------------------------------- the SQL copy of the rule

@pytest.mark.parametrize("visual,overlay,expected", [
    ([], None, "Monetizable"),
    ([_weapon()], None, "Restricted"),
    ([_weapon()], _hud(), "Review"),
    ([_weapon()], _hud(regions=1), "Restricted"),
    ([_weapon()], _hud(confidence=0.1), "Restricted"),
])
def test_sql_and_python_rules_agree(tmp_db, visual, overlay, expected):
    """get_library_stats() re-expresses the rule in SQL for one-pass aggregation.
    The dashboard disagreeing with the video page would be a silent, confusing
    bug, so the two implementations are checked against each other directly.
    """
    vid = repo.insert_video("c.mp4", "c.mp4", 1.0, 60.0, 30.0, 1920, 1080,
                            db_path=tmp_db)
    repo.update_video_status(vid, "completed", db_path=tmp_db)
    if visual:
        repo.insert_visual_flags(vid, visual, db_path=tmp_db)
    if overlay:
        repo.set_overlay_context(vid, overlay, db_path=tmp_db)

    assert compliance_verdict(vid) == expected                 # Python
    stats = repo.get_library_stats(db_path=tmp_db)             # SQL
    assert stats["verdicts"][expected] == 1, stats["verdicts"]


def test_overlay_context_survives_a_round_trip(video, tmp_db):
    repo.set_overlay_context(video, _hud(), db_path=tmp_db)
    stored = repo.get_overlay_context(video, db_path=tmp_db)
    assert stored["verdict"] == "overlay"
    assert stored["region_count"] == 3


def test_corrupt_overlay_context_is_ignored_not_fatal(video, tmp_db):
    """Hand-edited or truncated JSON must not take the video page down."""
    from src.db.connection import get_connection
    with get_connection(tmp_db) as conn:
        conn.execute("UPDATE VideoMetadata SET overlay_context = ? WHERE video_id = ?",
                     ("{not json", video))
    assert repo.get_overlay_context(video, db_path=tmp_db) is None
    repo.insert_visual_flags(video, [_weapon()], db_path=tmp_db)
    assert compliance_verdict(video) == "Restricted"
