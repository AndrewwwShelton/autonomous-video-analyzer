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
             # SEVERITY IS A CONTRACT, not a vibe. A single High-severity spoken
             # term restricts the whole video on its own (assess_compliance), so
             # High is reserved for terms that cannot plausibly mean anything
             # else. Everything ambiguous sits at Medium or Low, where it is
             # surfaced for a human without deciding the outcome.
             #
             # Measured against ordinary creator speech, the earlier list failed
             # this badly: "we were shooting all day", "kill the lights" and "the
             # render killed my laptop" each produced a HIGH flag and would have
             # restricted the video outright. Those are not edge cases -- they
             # are how video creators talk. Ambiguous single words are therefore
             # demoted, and the specific sense is captured as a phrase instead.
             #
             # Editable in Settings. It is the cheapest lever in the system and
             # the only one covering risks the vision model misses entirely.

             # --- Profanity -------------------------------------------------
             {"word": "damn",             "severity": "Low"},
             {"word": "hell",             "severity": "Low"},
             {"word": "crap",             "severity": "Low"},
             {"word": "piss",             "severity": "Medium"},
             {"word": "bastard",          "severity": "Medium"},

             # --- Firearms: unambiguous in isolation ------------------------
             # Added after a real test. An ATF firing-range clip transcribed
             # cleanly as "this is semi-automatic ... turning it on fully auto"
             # and matched NOTHING, because the list held only profanity plus
             # three risk words. Advertiser guidelines treat firearms discussion
             # as restricted, so the vocabulary must cover how people actually
             # talk about them, not just the word "gun".
             {"word": "handgun",          "severity": "High"},
             {"word": "firearm",          "severity": "High"},
             {"word": "shotgun",          "severity": "High"},
             {"word": "semi automatic",   "severity": "High"},
             {"word": "semi-automatic",   "severity": "High"},
             {"word": "fully auto",       "severity": "High"},
             {"word": "full auto",        "severity": "High"},
             {"word": "automatic weapon", "severity": "High"},
             {"word": "assault rifle",    "severity": "High"},
             {"word": "assault weapon",   "severity": "High"},
             {"word": "gunshot",          "severity": "High"},
             {"word": "gunfire",          "severity": "High"},
             {"word": "silencer",         "severity": "High"},
             {"word": "shooting range",   "severity": "High"},

             # --- Firearms: real but ambiguous ------------------------------
             # "gun it", "rifle through a drawer", "weapon of choice" all exist.
             # Worth surfacing, not worth restricting a video over on their own.
             {"word": "gun",              "severity": "Medium"},
             {"word": "guns",             "severity": "Medium"},
             {"word": "pistol",           "severity": "Medium"},
             {"word": "rifle",            "severity": "Medium"},
             {"word": "weapon",           "severity": "Medium"},
             {"word": "ammunition",       "severity": "Medium"},
             {"word": "ammo",             "severity": "Medium"},
             {"word": "magazine clip",    "severity": "Medium"},
             {"word": "suppressor",       "severity": "Low"},

             # --- Violence --------------------------------------------------
             # The specific sense as a phrase; the bare verb demoted. "killing
             # it", "kill the lights" and "that shot killed me" are ubiquitous.
             {"word": "murder",           "severity": "High"},
             {"word": "mass shooting",    "severity": "High"},
             {"word": "school shooting",  "severity": "High"},
             {"word": "shot him",         "severity": "High"},
             {"word": "shot her",         "severity": "High"},
             {"word": "stabbed",          "severity": "Medium"},
             {"word": "kill",             "severity": "Low"},
             {"word": "killed",           "severity": "Low"},

             # --- Substances ------------------------------------------------
             {"word": "cocaine",          "severity": "High"},
             {"word": "heroin",           "severity": "High"},
             {"word": "overdose",         "severity": "Medium"},
             {"word": "drugs",            "severity": "Medium"},
             {"word": "meth",             "severity": "Medium"},
             {"word": "vape",             "severity": "Low"},
             {"word": "cigarette",        "severity": "Low"},
         ]),
         "json", "Restricted keyword dictionary matched against the transcript. "
                 "High severity restricts a video on its own, so it is reserved "
                 "for unambiguous terms; ambiguous words sit lower and are "
                 "surfaced for review instead. Editable in Settings"),
        ("frame_sample_fps", str(config.DEFAULT_FRAME_SAMPLE_FPS), "float",
         "Frames per second sampled from video for vision analysis (SRS FR3)"),
        ("min_ad_spot_duration_sec", str(config.DEFAULT_MIN_AD_SPOT_SEC), "float",
         "Minimum persistence for a surface to count as a Premium Ad Spot"),
        ("detection_confidence_threshold", str(config.DEFAULT_CONFIDENCE_THRESHOLD), "float",
         "Minimum YOLO confidence for a visual flag to be recorded"),
        ("whisper_model", config.DEFAULT_WHISPER_MODEL, "string",
         "faster-whisper model size used for transcription (D3)"),
        ("detection_max_imgsz", str(config.DEFAULT_MAX_IMGSZ), "int",
         "Cap on detection resolution. Ultralytics defaults to 640, which halves "
         "720p footage and made a pistol in real video undetectable; raising it to "
         "the source resolution recovered the detection. Higher finds smaller "
         "objects and costs proportionally more time"),
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


# Every dictionary this project has shipped, so an existing database can be
# recognised as never having been edited. A stored list matching ANY of these was
# seeded, not curated, and is safe to replace; anything else is the user's own
# work and is left alone. Append here when the default changes -- comparing
# against only the most recent one would strand databases a version behind.
_SHIPPED_DICTIONARIES = [
    # v1 -- profanity plus three risk words.
    {"damn", "hell", "crap", "piss", "bastard", "drugs", "gun", "kill", "weapon"},
    # v2 -- widened for firearms, but with ambiguous words at High severity.
    {"damn", "hell", "crap", "piss", "bastard", "gun", "guns", "handgun", "firearm",
     "pistol", "rifle", "shotgun", "weapon", "ammunition", "ammo", "magazine clip",
     "semi automatic", "semi-automatic", "fully auto", "full auto",
     "automatic weapon", "silencer", "suppressor", "trigger", "gunshot", "gunfire",
     "kill", "killed", "murder", "shooting", "stabbed", "assault", "drugs",
     "cocaine", "heroin", "meth", "overdose", "vape", "cigarette"},
]
_ORIGINAL_DICTIONARY_WORDS = _SHIPPED_DICTIONARIES[0]   # kept for existing tests


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
    if not any(current == shipped for shipped in _SHIPPED_DICTIONARIES):
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
