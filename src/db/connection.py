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

# Seed values for SystemConfig on first launch. The Settings page edits these at runtime.
_DEFAULT_CONFIG = [
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
    ("analysis_mode", "demo", "string",
     "'real' runs implemented engines (audio as of M1); 'demo' uses deterministic "
     "stand-ins and needs no model weights"),
]


def get_connection(db_path: Path | None = None) -> sqlite3.Connection:
    path = Path(db_path) if db_path else config.DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


def init_db(db_path: Path | None = None) -> None:
    """Create all tables and seed default config. Idempotent — safe on every app start."""
    with get_connection(db_path) as conn:
        conn.executescript(_SCHEMA_PATH.read_text(encoding="utf-8"))
        conn.executemany(
            "INSERT OR IGNORE INTO SystemConfig (config_key, config_value, config_type, description) "
            "VALUES (?, ?, ?, ?)",
            _DEFAULT_CONFIG,
        )
