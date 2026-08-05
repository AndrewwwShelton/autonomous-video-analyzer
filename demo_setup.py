"""Prepare a clean, presentation-ready demo.

Wipes previous runs, generates the sample video, ingests it and analyses it — so at
review time the library already has one completed video to talk about, and a second
copy sitting un-analysed that you can run live in front of the panel.

    python demo_setup.py
"""
import shutil
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from src import config                                    # noqa: E402
from src.db.connection import init_db                     # noqa: E402
from src.db import repository as repo                     # noqa: E402
from src.demo_media import generate_demo_video            # noqa: E402
from src.pipeline.orchestrator import compliance_verdict, process_video  # noqa: E402
from src.vision.sampler import probe_video, save_thumbnail  # noqa: E402

THUMBS = config.DATA_DIR / "thumbs"


def reset():
    """Remove the previous database, videos and reports for a clean start."""
    if config.DATA_DIR.exists():
        try:
            shutil.rmtree(config.DATA_DIR)
        except PermissionError:
            sys.exit(
                "\n  Could not reset: the database is open in another process.\n"
                "  Stop the server first (close the RUN_DEMO window, or press\n"
                "  Ctrl+C in the terminal running uvicorn), then run this again.\n"
            )
    config.ensure_dirs()
    THUMBS.mkdir(parents=True, exist_ok=True)
    init_db()


def ingest(path: Path, display_name: str) -> int:
    meta = probe_video(path)
    vid = repo.insert_video(
        filename=display_name, filepath=str(path),
        file_size_mb=round(path.stat().st_size / 1_048_576, 2),
        duration_sec=meta["duration_sec"], fps=meta["fps"],
        width=meta["width"], height=meta["height"],
    )
    save_thumbnail(path, THUMBS / f"video_{vid}.jpg")
    return vid


def main():
    print("Resetting demo data...")
    reset()

    print("Rendering sample footage...")
    source = generate_demo_video()

    # Copy so the two library rows point at separate files.
    second = config.VIDEO_DIR / "studio_review_cut.mp4"
    shutil.copyfile(source, second)

    print("Ingesting...")
    analysed = ingest(source, "brand_review_final.mp4")
    repo.get_video(analysed)
    live = ingest(second, "studio_review_cut.mp4")

    print(f"Analysing video #{analysed} (pre-run, so the library isn't empty)...")
    t0 = time.time()
    counts = process_video(analysed, demo=True)
    print(f"   done in {time.time() - t0:.1f}s - "
          f"{counts['audio']} audio flags, {counts['visual']} visual risks, "
          f"{counts['ad_spots']} ad spots, verdict {compliance_verdict(analysed)}")

    print(f"\nReady. Video #{live} ('studio_review_cut.mp4') is left UN-analysed:")
    print("run that one live in front of the panel to show the progress bar.\n")


if __name__ == "__main__":
    main()
