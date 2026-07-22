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
