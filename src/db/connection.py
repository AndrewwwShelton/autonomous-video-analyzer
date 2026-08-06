"""SQLite connection handling.

Decisions baked in here (PLAN.md §5.4 / D2):
- WAL journal mode: readers (dashboard) never block the single writer (pipeline).
- foreign_keys ON per connection — SQLite defaults it OFF.
- One connection per operation, never shared across threads.
"""
import json
import sqlite3
from pathlib import Path

from src import config

_SCHEMA_PATH = Path(__file__).parent / "schema.sql"

def _default_vision_weights() -> list[str]:
    """Stock COCO, plus the fine-tuned risk model when it has been built.

    Resolved at seed time rather than hard-coded: demo_setup.py wipes data/ and
    re-seeds, so a static list would silently drop the fine-tune (M3b) from the
    config and quietly downgrade 'real' mode back to COCO-only coverage. Naming a
    weight file that does not exist is worse than omitting it — ultralytics would
    try to download it by name and fail.
    """
    weights = ["yolov8n.pt"]
    if (config.MODELS_DIR / "risk_yolov8.pt").exists():
        weights.append("risk_yolov8.pt")
    return weights


# Seed values for SystemConfig on first launch. The Settings page edits these at runtime.
def _default_config() -> list[tuple[str, str, str, str]]:
    return [
        ("profanity_dictionary",
         json.dumps([
             {"word": "damn",       "severity": "Low"},
             {"word": "hell",       "severity": "Low"},
             {"word": "crap",       "severity": "Low"},
             {"word": "piss",       "severity": "Medium"},
             {"word": "bastard",    "severity": "Medium"},
             {"word": "drugs",      "severity": "Medium"},
             {"word": "gun",        "severity": "High"},
             {"word": "kill",       "severity": "High"},
             {"word": "weapon",     "severity": "High"},
         ]),
         "json", "Restricted keyword dictionary matched against the transcript"),
        ("frame_sample_fps", str(config.DEFAULT_FRAME_SAMPLE_FPS), "float",
         "Frames per second sampled from video for vision analysis (SRS FR3)"),
        ("min_ad_spot_duration_sec", str(config.DEFAULT_MIN_AD_SPOT_SEC), "float",
         "Minimum persistence for a surface to count as a Premium Ad Spot"),
        ("detection_confidence_threshold", str(config.DEFAULT_CONFIDENCE_THRESHOLD), "float",
         "Minimum YOLO confidence for a visual flag to be recorded"),
        ("whisper_model", config.DEFAULT_WHISPER_MODEL, "string",
         "faster-whisper model size used for transcription (D3)"),
        ("vision_weights", json.dumps(_default_vision_weights()), "json",
         "YOLO weight files used for visual detection, resolved from models/. Stock COCO "
         "covers knife/scissors/bat/bottle/wine glass but has no gun, cigarette or drugs; "
         "risk_yolov8.pt is the fine-tune that adds them (M3b, PLAN.md D1)"),
        ("analysis_mode", "demo", "string",
         "'real' runs every implemented engine — audio, vision and ad spots; 'demo' uses "
         "deterministic stand-ins and needs no model weights"),
    ]


def get_connection(db_path: Path | None = None) -> sqlite3.Connection:
    path = Path(db_path) if db_path else config.DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


# Columns added after the first release. CREATE TABLE IF NOT EXISTS silently does
# nothing when the table already exists, so a new column never reaches a database
# created by an earlier version -- the app would then fail on every read of it.
_MIGRATIONS = [
    ("VideoMetadata", "overlay_context", "TEXT"),
]


def _apply_migrations(conn: sqlite3.Connection) -> None:
    for table, column, decl in _MIGRATIONS:
        existing = {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}
        if column not in existing:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {decl}")


def init_db(db_path: Path | None = None) -> None:
    """Create all tables and seed default config. Idempotent — safe on every app start."""
    with get_connection(db_path) as conn:
        conn.executescript(_SCHEMA_PATH.read_text(encoding="utf-8"))
        _apply_migrations(conn)
        conn.executemany(
            "INSERT OR IGNORE INTO SystemConfig (config_key, config_value, config_type, description) "
            "VALUES (?, ?, ?, ?)",
            _default_config(),
        )
