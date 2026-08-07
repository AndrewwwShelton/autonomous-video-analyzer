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
             # --- Profanity -------------------------------------------------
             {"word": "damn",           "severity": "Low"},
             {"word": "hell",           "severity": "Low"},
             {"word": "crap",           "severity": "Low"},
             {"word": "piss",           "severity": "Medium"},
             {"word": "bastard",        "severity": "Medium"},
             # --- Firearms --------------------------------------------------
             # Added after a real test: an ATF firing-range clip transcribed
             # cleanly as "this is semi-automatic ... a single pull of the
             # trigger ... turning it on fully auto" and matched NOTHING,
             # because the list held only profanity plus three risk words.
             # Advertiser guidelines treat firearms *discussion* as restricted,
             # so the vocabulary has to cover how people actually talk about
             # them, not just the word "gun".
             {"word": "gun",            "severity": "High"},
             {"word": "guns",           "severity": "High"},
             {"word": "handgun",        "severity": "High"},
             {"word": "firearm",        "severity": "High"},
             {"word": "pistol",         "severity": "High"},
             {"word": "rifle",          "severity": "High"},
             {"word": "shotgun",        "severity": "High"},
             {"word": "weapon",         "severity": "High"},
             {"word": "ammunition",     "severity": "Medium"},
             {"word": "ammo",           "severity": "Medium"},
             {"word": "magazine clip",  "severity": "Medium"},
             {"word": "semi automatic", "severity": "High"},
             {"word": "semi-automatic", "severity": "High"},
             {"word": "fully auto",     "severity": "High"},
             {"word": "full auto",      "severity": "High"},
             {"word": "automatic weapon", "severity": "High"},
             {"word": "silencer",       "severity": "High"},
             {"word": "suppressor",     "severity": "Medium"},
             {"word": "trigger",        "severity": "Low"},
             {"word": "gunshot",        "severity": "High"},
             {"word": "gunfire",        "severity": "High"},
             # --- Violence --------------------------------------------------
             {"word": "kill",           "severity": "High"},
             {"word": "killed",         "severity": "High"},
             {"word": "murder",         "severity": "High"},
             {"word": "shooting",       "severity": "High"},
             {"word": "stabbed",        "severity": "High"},
             {"word": "assault",        "severity": "Medium"},
             # --- Substances ------------------------------------------------
             {"word": "drugs",          "severity": "Medium"},
             {"word": "cocaine",        "severity": "High"},
             {"word": "heroin",         "severity": "High"},
             {"word": "meth",           "severity": "High"},
             {"word": "overdose",       "severity": "Medium"},
             {"word": "vape",           "severity": "Low"},
             {"word": "cigarette",      "severity": "Low"},
         ]),
         "json", "Restricted keyword dictionary matched against the transcript. "
                 "Editable in Settings -- it is the cheapest lever in the system, "
                 "and the only one that covers risks the vision model misses"),
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
    ("VisualFlags", "detection_model", "TEXT"),
]


def _apply_migrations(conn: sqlite3.Connection) -> None:
    for table, column, decl in _MIGRATIONS:
        existing = {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}
        if column not in existing:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {decl}")
    _upgrade_untouched_dictionary(conn)


# The original seed: profanity plus three risk words. Kept so an existing database
# can be recognised as never having been edited.
_ORIGINAL_DICTIONARY_WORDS = {
    "damn", "hell", "crap", "piss", "bastard", "drugs", "gun", "kill", "weapon",
}


def _upgrade_untouched_dictionary(conn: sqlite3.Connection) -> None:
    """Replace the old nine-word list, but only where nobody has edited it.

    Config is seeded with INSERT OR IGNORE, so an existing database keeps whatever
    it already had — meaning the widened firearms vocabulary would never reach the
    one place it matters: a library someone has been using. But the dictionary is
    user-editable, and silently overwriting somebody's curated list would be worse
    than leaving it stale. Upgrading only an exact, unmodified match of the
    original resolves both.
    """
    row = conn.execute(
        "SELECT config_value FROM SystemConfig WHERE config_key = 'profanity_dictionary'"
    ).fetchone()
    if row is None:
        return
    try:
        current = {str(e.get("word", "")).lower() for e in json.loads(row[0])}
    except (TypeError, ValueError):
        return                      # hand-edited into something unparseable; leave it
    if current != _ORIGINAL_DICTIONARY_WORDS:
        return                      # customised — the user's list wins

    default = next(c for c in _default_config() if c[0] == "profanity_dictionary")
    conn.execute(
        "UPDATE SystemConfig SET config_value = ? WHERE config_key = 'profanity_dictionary'",
        (default[1],),
    )


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
