"""Central paths and constants. Every module gets its filesystem layout from here."""
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

DATA_DIR = PROJECT_ROOT / "data"
VIDEO_DIR = DATA_DIR / "videos"
REPORTS_DIR = DATA_DIR / "reports"
MODELS_DIR = PROJECT_ROOT / "models"
DB_PATH = DATA_DIR / "audit.db"

SUPPORTED_EXTENSIONS = {".mp4", ".mov", ".avi"}

# Pipeline defaults — runtime values live in the SystemConfig table (Settings page);
# these are only the seed values used on first launch.
DEFAULT_FRAME_SAMPLE_FPS = 1.0
DEFAULT_MIN_AD_SPOT_SEC = 5.0
DEFAULT_CONFIDENCE_THRESHOLD = 0.5
DEFAULT_WHISPER_MODEL = "base.en"


def ensure_dirs() -> None:
    for d in (DATA_DIR, VIDEO_DIR, REPORTS_DIR, MODELS_DIR):
        d.mkdir(parents=True, exist_ok=True)
