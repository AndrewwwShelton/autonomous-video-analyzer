"""CRUD layer over the six DDD tables.

Every function opens its own short-lived connection (WAL makes this cheap) and takes
an optional db_path so tests can run against a temp database.
"""
import json
from pathlib import Path

from src.db.connection import get_connection

# ---------------------------------------------------------------- VideoMetadata

def insert_video(filename: str, filepath: str, file_size_mb: float, duration_sec: float,
                 fps: float, width: int, height: int, db_path: Path | None = None) -> int:
    with get_connection(db_path) as conn:
        cur = conn.execute(
            "INSERT INTO VideoMetadata (filename, filepath, file_size_mb, duration_sec, fps, "
            "resolution_width, resolution_height) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (filename, filepath, file_size_mb, duration_sec, fps, width, height),
        )
        return cur.lastrowid


def get_video(video_id: int, db_path: Path | None = None) -> dict | None:
    with get_connection(db_path) as conn:
        row = conn.execute(
            "SELECT * FROM VideoMetadata WHERE video_id = ?", (video_id,)
        ).fetchone()
        return dict(row) if row else None


def list_videos(db_path: Path | None = None) -> list[dict]:
    with get_connection(db_path) as conn:
        rows = conn.execute(
            "SELECT * FROM VideoMetadata ORDER BY upload_timestamp DESC, video_id DESC"
        ).fetchall()
        return [dict(r) for r in rows]


def update_video_status(video_id: int, status: str, db_path: Path | None = None) -> None:
    with get_connection(db_path) as conn:
        conn.execute(
            "UPDATE VideoMetadata SET processed_status = ? WHERE video_id = ?",
            (status, video_id),
        )


def set_overlay_context(video_id: int, report: dict | None,
                        db_path: Path | None = None) -> None:
    """Store persistent-overlay evidence for one video (src/vision/overlay.py)."""
    with get_connection(db_path) as conn:
        conn.execute(
            "UPDATE VideoMetadata SET overlay_context = ? WHERE video_id = ?",
            (json.dumps(report) if report is not None else None, video_id),
        )


def get_overlay_context(video_id: int, db_path: Path | None = None) -> dict | None:
    """None when the video predates overlay analysis or was run in demo mode."""
    video = get_video(video_id, db_path)
    raw = (video or {}).get("overlay_context")
    if not raw:
        return None
    try:
        return json.loads(raw)
    except (TypeError, ValueError):
        return None


def delete_video(video_id: int, db_path: Path | None = None) -> None:
    """Cascades to all child flag/spot/report rows via FK ON DELETE CASCADE."""
    with get_connection(db_path) as conn:
        conn.execute("DELETE FROM VideoMetadata WHERE video_id = ?", (video_id,))

# ---------------------------------------------------------------- Flags & spots

def insert_audio_flags(video_id: int, flags: list[dict], db_path: Path | None = None) -> None:
    with get_connection(db_path) as conn:
        conn.executemany(
            "INSERT INTO AudioFlags (video_id, timestamp_start, timestamp_end, word_flagged, "
            "transcript_context, severity, detection_model) VALUES (?, ?, ?, ?, ?, ?, ?)",
            [(video_id, f["timestamp_start"], f["timestamp_end"], f["word_flagged"],
              f.get("transcript_context"), f.get("severity"),
              f.get("detection_model", "faster-whisper-base.en")) for f in flags],
        )


def insert_visual_flags(video_id: int, flags: list[dict], db_path: Path | None = None) -> None:
    with get_connection(db_path) as conn:
        conn.executemany(
            "INSERT INTO VisualFlags (video_id, frame_timestamp, object_detected, "
            "bounding_box_json, confidence_score, risk_category) VALUES (?, ?, ?, ?, ?, ?)",
            [(video_id, f["frame_timestamp"], f["object_detected"],
              json.dumps(f["bounding_box"]), f["confidence_score"],
              f.get("risk_category")) for f in flags],
        )


def insert_ad_spots(video_id: int, spots: list[dict], db_path: Path | None = None) -> None:
    with get_connection(db_path) as conn:
        conn.executemany(
            "INSERT INTO AdSpots (video_id, timestamp_start, timestamp_end, spot_type, "
            "bounding_box_json, area_pixels, suitability_score) VALUES (?, ?, ?, ?, ?, ?, ?)",
            [(video_id, s["timestamp_start"], s["timestamp_end"], s.get("spot_type"),
              json.dumps(s["bounding_box"]), s.get("area_pixels"),
              s.get("suitability_score")) for s in spots],
        )


def get_audio_flags(video_id: int, db_path: Path | None = None) -> list[dict]:
    with get_connection(db_path) as conn:
        rows = conn.execute(
            "SELECT * FROM AudioFlags WHERE video_id = ? ORDER BY timestamp_start",
            (video_id,),
        ).fetchall()
        return [dict(r) for r in rows]


def get_visual_flags(video_id: int, db_path: Path | None = None) -> list[dict]:
    with get_connection(db_path) as conn:
        rows = conn.execute(
            "SELECT * FROM VisualFlags WHERE video_id = ? ORDER BY frame_timestamp",
            (video_id,),
        ).fetchall()
        return [dict(r) for r in rows]


def get_ad_spots(video_id: int, db_path: Path | None = None) -> list[dict]:
    with get_connection(db_path) as conn:
        rows = conn.execute(
            "SELECT * FROM AdSpots WHERE video_id = ? ORDER BY timestamp_start",
            (video_id,),
        ).fetchall()
        return [dict(r) for r in rows]


def clear_analysis(video_id: int, db_path: Path | None = None) -> None:
    """Wipe flags/spots for a video so it can be re-processed cleanly."""
    with get_connection(db_path) as conn:
        conn.execute("DELETE FROM AudioFlags WHERE video_id = ?", (video_id,))
        conn.execute("DELETE FROM VisualFlags WHERE video_id = ?", (video_id,))
        conn.execute("DELETE FROM AdSpots WHERE video_id = ?", (video_id,))
        # Overlay evidence belongs to the run that produced it. Leaving it behind
        # would let a stale "this is gameplay" finding soften the verdict on a
        # re-analysis that never established it.
        conn.execute("UPDATE VideoMetadata SET overlay_context = NULL "
                     "WHERE video_id = ?", (video_id,))

# ---------------------------------------------------------------- Reports

def insert_report(video_id: int, report_type: str, file_path: str, totals: dict,
                  compliance_status: str, db_path: Path | None = None) -> int:
    with get_connection(db_path) as conn:
        cur = conn.execute(
            "INSERT INTO AuditReports (video_id, report_type, file_path, total_audio_risks, "
            "total_visual_risks, total_ad_spots, compliance_status) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (video_id, report_type, file_path, totals.get("audio", 0),
             totals.get("visual", 0), totals.get("ad_spots", 0), compliance_status),
        )
        return cur.lastrowid


def list_reports(video_id: int | None = None, db_path: Path | None = None) -> list[dict]:
    with get_connection(db_path) as conn:
        if video_id is None:
            rows = conn.execute(
                "SELECT * FROM AuditReports ORDER BY generation_timestamp DESC"
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM AuditReports WHERE video_id = ? ORDER BY generation_timestamp DESC",
                (video_id,),
            ).fetchall()
        return [dict(r) for r in rows]

# ---------------------------------------------------------------- SystemConfig

def get_config(key: str, db_path: Path | None = None):
    """Return the config value coerced to its declared type (int/float/json/string)."""
    with get_connection(db_path) as conn:
        row = conn.execute(
            "SELECT config_value, config_type FROM SystemConfig WHERE config_key = ?", (key,)
        ).fetchone()
    if row is None:
        return None
    value, ctype = row["config_value"], row["config_type"]
    if ctype == "int":
        return int(value)
    if ctype == "float":
        return float(value)
    if ctype == "json":
        return json.loads(value)
    return value


def set_config(key: str, value, config_type: str = "string", description: str | None = None,
               db_path: Path | None = None) -> None:
    stored = json.dumps(value) if config_type == "json" else str(value)
    with get_connection(db_path) as conn:
        conn.execute(
            "INSERT INTO SystemConfig (config_key, config_value, config_type, description) "
            "VALUES (?, ?, ?, ?) "
            "ON CONFLICT(config_key) DO UPDATE SET config_value = excluded.config_value, "
            "last_updated = CURRENT_TIMESTAMP",
            (key, stored, config_type, description),
        )

# ---------------------------------------------------------------- Aggregates

# The same rule as orchestrator.assess_compliance(), expressed in SQL so the whole
# library can be summarised in one pass instead of one query per video.
#
# This is a deliberate second copy of the compliance rule, and the two drifting
# apart would make the dashboard disagree with the video pages. Order matters and
# mirrors the Python exactly: spoken terms first (an overlay never excuses audio),
# then the absence of weapons, then the overlay context.
# tests/test_compliance_verdict.py asserts the two implementations agree.
_VERDICT_SQL = """
    SELECT v.video_id,
           CASE
             WHEN EXISTS (SELECT 1 FROM AudioFlags a
                          WHERE a.video_id = v.video_id AND a.severity = 'High')
               THEN 'Restricted'
             WHEN NOT EXISTS (SELECT 1 FROM VisualFlags f
                              WHERE f.video_id = v.video_id AND f.risk_category = 'Weapon')
               THEN 'Monetizable'
             WHEN json_extract(v.overlay_context, '$.verdict') = 'overlay'
              AND COALESCE(json_extract(v.overlay_context, '$.confidence'), 0) >= 0.5
              AND COALESCE(json_extract(v.overlay_context, '$.region_count'), 0) >= 2
               THEN 'Review'
             ELSE 'Restricted'
           END AS verdict
    FROM VideoMetadata v
    WHERE v.processed_status = 'completed'
"""


def get_library_stats(db_path: Path | None = None) -> dict:
    """Library-wide aggregates for the Dashboard and Analytics screens."""
    with get_connection(db_path) as conn:
        def rows(sql, params=()):
            return [dict(r) for r in conn.execute(sql, params).fetchall()]

        status_counts = {r["processed_status"]: r["n"] for r in rows(
            "SELECT processed_status, COUNT(*) n FROM VideoMetadata GROUP BY processed_status")}

        verdicts = {r["verdict"]: r["n"] for r in rows(
            f"SELECT verdict, COUNT(*) n FROM ({_VERDICT_SQL}) GROUP BY verdict")}

        totals = dict(conn.execute("""
            SELECT (SELECT COUNT(*) FROM VideoMetadata)                     AS videos,
                   (SELECT COALESCE(SUM(duration_sec), 0) FROM VideoMetadata) AS duration_sec,
                   (SELECT COUNT(*) FROM AudioFlags)                        AS audio_flags,
                   (SELECT COUNT(*) FROM VisualFlags)                       AS visual_flags,
                   (SELECT COUNT(*) FROM AdSpots)                           AS ad_spots,
                   (SELECT COALESCE(SUM(timestamp_end - timestamp_start), 0)
                      FROM AdSpots)                                         AS ad_inventory_sec
        """).fetchone())

        return {
            "totals": totals,
            "status_counts": status_counts,
            "verdicts": {"Monetizable": verdicts.get("Monetizable", 0),
                         "Review": verdicts.get("Review", 0),
                         "Restricted": verdicts.get("Restricted", 0)},
            "severity_breakdown": rows(
                "SELECT severity AS label, COUNT(*) AS value FROM AudioFlags "
                "GROUP BY severity ORDER BY value DESC"),
            "risk_category_breakdown": rows(
                "SELECT risk_category AS label, COUNT(*) AS value FROM VisualFlags "
                "GROUP BY risk_category ORDER BY value DESC"),
            "top_words": rows(
                "SELECT word_flagged AS label, COUNT(*) AS value, "
                "       MAX(severity) AS severity FROM AudioFlags "
                "GROUP BY word_flagged ORDER BY value DESC, label LIMIT 8"),
            "top_objects": rows(
                "SELECT object_detected AS label, COUNT(*) AS value, "
                "       ROUND(AVG(confidence_score), 3) AS avg_confidence FROM VisualFlags "
                "GROUP BY object_detected ORDER BY value DESC, label LIMIT 8"),
            "spot_types": rows(
                "SELECT spot_type AS label, COUNT(*) AS value, "
                "       ROUND(SUM(timestamp_end - timestamp_start), 1) AS seconds FROM AdSpots "
                "GROUP BY spot_type ORDER BY value DESC"),
            "recent_videos": rows(
                "SELECT video_id, filename, processed_status, upload_timestamp, duration_sec "
                "FROM VideoMetadata ORDER BY video_id DESC LIMIT 5"),
            "recent_reports": rows(
                "SELECT report_id, video_id, report_type, generation_timestamp, "
                "       compliance_status FROM AuditReports "
                "ORDER BY report_id DESC LIMIT 5"),
        }
