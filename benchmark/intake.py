"""Bring a source video into the benchmark set.

    python benchmark/intake.py path/to/source.mp4
    python benchmark/intake.py source.mp4 --start 2:15 --end 3:30
    python benchmark/intake.py source.mp4 --name kitchen_knife_demo --source "CC-BY, ..."

Trims the requested span, re-encodes to a consistent browser-playable H.264 clip in
benchmark/clips/, and writes a matching label skeleton in benchmark/labels/ so you
can go straight to labelling.

Why trim: labelling a twenty-minute video is impractical and produces a benchmark
weighted toward one recording. Thirty to ninety second clips are the sweet spot --
long enough to contain a few events, short enough to label in one sitting.

Timestamps in the label are relative to the TRIMMED clip, which is what the
pipeline sees.
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import imageio_ffmpeg  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

CLIPS_DIR = ROOT / "benchmark" / "clips"
LABELS_DIR = ROOT / "benchmark" / "labels"


def parse_timecode(value: str | None) -> float | None:
    """Accept 90, 1:30 or 00:01:30.5 and return seconds."""
    if value is None:
        return None
    value = value.strip()
    if not value:
        return None
    if not re.fullmatch(r"(\d+:)?(\d+:)?\d+(\.\d+)?", value):
        raise ValueError(f"Cannot read timecode '{value}' -- use 90, 1:30 or 00:01:30")
    parts = [float(p) for p in value.split(":")]
    seconds = 0.0
    for p in parts:
        seconds = seconds * 60 + p
    return seconds


def safe_name(text: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", text).strip("_").lower()
    return slug or "clip"


def _probe_duration(path: Path) -> float | None:
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    proc = subprocess.run([ffmpeg, "-hide_banner", "-i", str(path)],
                          capture_output=True, text=True, errors="replace")
    m = re.search(r"Duration: (\d+):(\d+):(\d+\.?\d*)", proc.stderr)
    if not m:
        return None
    h, mnt, s = m.groups()
    return int(h) * 3600 + int(mnt) * 60 + float(s)


def main() -> int:
    ap = argparse.ArgumentParser(description="Add a clip to the benchmark set.")
    ap.add_argument("source", type=Path, help="source video file")
    ap.add_argument("--start", help="trim start (e.g. 2:15). Default: beginning")
    ap.add_argument("--end", help="trim end (e.g. 3:30). Default: end of file")
    ap.add_argument("--name", help="clip name without extension. Default: from filename")
    ap.add_argument("--source", dest="attribution", default="",
                    help="where the clip came from -- recorded in the label")
    ap.add_argument("--notes", default="", help="anything that affects difficulty")
    ap.add_argument("--no-violations", action="store_true",
                    help="mark as a clean clip: no violations expected anywhere in it")
    args = ap.parse_args()

    if not args.source.exists():
        print(f"Source not found: {args.source}")
        return 1

    try:
        start = parse_timecode(args.start)
        end = parse_timecode(args.end)
    except ValueError as e:
        print(e)
        return 1
    if start is not None and end is not None and end <= start:
        print("--end must be after --start")
        return 1

    CLIPS_DIR.mkdir(parents=True, exist_ok=True)
    LABELS_DIR.mkdir(parents=True, exist_ok=True)

    name = safe_name(args.name or args.source.stem)
    clip_path = CLIPS_DIR / f"{name}.mp4"
    label_path = LABELS_DIR / f"{name}.json"

    if label_path.exists():
        print(f"A label already exists at {label_path.relative_to(ROOT)} -- "
              f"choose a different --name so existing work is not overwritten.")
        return 1

    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    cmd = [ffmpeg, "-y"]
    if start is not None:
        cmd += ["-ss", str(start)]
    cmd += ["-i", str(args.source)]
    if end is not None:
        cmd += ["-t", str(end - (start or 0.0))]
    # Re-encode rather than stream-copy: a copy can only cut on keyframes, which
    # shifts every timestamp in the clip and would silently corrupt the labels.
    cmd += ["-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-movflags", "+faststart", str(clip_path)]

    print(f"trimming -> {clip_path.name} ...")
    proc = subprocess.run(cmd, capture_output=True, text=True, errors="replace")
    if proc.returncode != 0 or not clip_path.exists():
        tail = (proc.stderr or "").strip().splitlines()[-3:]
        print("ffmpeg failed:\n  " + "\n  ".join(tail))
        return 1

    duration = _probe_duration(clip_path)
    label = {
        "clip": clip_path.name,
        "source": args.attribution,
        "notes": args.notes,
        "duration_sec": round(duration, 2) if duration else None,
        "audio": [],
        "visual": [],
        "ad_spots": [],
    }
    if args.no_violations:
        label["notes"] = (label["notes"] + " " if label["notes"] else "") + \
            "Clean clip -- no violations expected. Exists to catch false positives."
    label_path.write_text(json.dumps(label, indent=2), encoding="utf-8")

    print(f"clip   : {clip_path.relative_to(ROOT)}"
          + (f"  ({duration:.1f}s)" if duration else ""))
    print(f"label  : {label_path.relative_to(ROOT)}  (empty -- ready to label)")
    if not args.attribution:
        print("\nNote: no --source given. Record where each clip came from; you will be "
              "asked about provenance.")
    print("\nNext:  open benchmark/labeller.html and label it.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
