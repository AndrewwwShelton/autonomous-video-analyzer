"""Benchmark runner — executes the pipeline over labelled clips and scores it.

Two guards matter here more than the plumbing:

1. **Isolation.** Evaluation runs against a throwaway database so a benchmark run
   never adds rows to the operator's real library.
2. **Honesty.** A metric computed over a stubbed engine is meaningless but looks
   exactly like a real one on a slide. Every engine's results are therefore tagged
   `valid` or `stubbed`, and stubbed scores are withheld from the headline figure.
"""
import contextlib
import json
import shutil
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from src import config
from src.benchmark.evaluator import (MatchResult, Metrics, match_events,
                                     match_intervals, per_category)
from src.db import repository as repo
from src.db.connection import init_db
from src.pipeline.orchestrator import process_video
from src.vision.sampler import probe_video

BENCHMARK_DIR = config.PROJECT_ROOT / "benchmark"
CLIPS_DIR = BENCHMARK_DIR / "clips"
LABELS_DIR = BENCHMARK_DIR / "labels"
RESULTS_DIR = BENCHMARK_DIR / "results"

AUDIO_TOLERANCE_SEC = 2.0   # ASR word boundaries drift
VISUAL_TOLERANCE_SEC = 1.5  # vision samples at 1 FPS
ADSPOT_IOU = 0.3
PRECISION_TARGET = 0.85     # the figure claimed in the SRS

# A precision figure is only worth quoting if it rests on enough labelled events
# and enough distinct clips. 100% over four events from one synthetic clip is not
# evidence of anything, and would not survive a question in the viva.
MIN_EVENTS_FOR_CLAIM = 30
MIN_REAL_CLIPS_FOR_CLAIM = 10


@dataclass
class ClipResult:
    clip: str
    audio: MatchResult = field(default_factory=MatchResult)
    visual: MatchResult = field(default_factory=MatchResult)
    ad_spots: MatchResult = field(default_factory=MatchResult)
    engines: dict = field(default_factory=dict)
    error: str | None = None


@contextlib.contextmanager
def _scratch_database(path: Path):
    """Point the data layer at a temporary database for the duration of the run.

    The repository resolves config.DB_PATH per call, so swapping it here isolates
    the benchmark without threading a db_path through the whole orchestrator.
    """
    original = config.DB_PATH
    config.DB_PATH = path
    try:
        init_db(path)
        yield
    finally:
        config.DB_PATH = original


def load_labels() -> list[dict]:
    """Read every label file, newest schema only. Raises on malformed input."""
    if not LABELS_DIR.exists():
        return []
    labels = []
    for f in sorted(LABELS_DIR.glob("*.json")):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            raise ValueError(f"{f.name} is not valid JSON: {e}") from e
        problems = validate_label(data)
        if problems:
            raise ValueError(f"{f.name}: " + "; ".join(problems))
        data["_label_file"] = f.name
        labels.append(data)
    return labels


def validate_label(data: dict) -> list[str]:
    """Return a list of problems; empty means the label is usable."""
    problems = []
    if not data.get("clip"):
        problems.append("missing 'clip'")
    for entry in data.get("audio", []):
        if "word" not in entry or "at" not in entry:
            problems.append(f"audio entry needs 'word' and 'at': {entry}")
    for entry in data.get("visual", []):
        if "category" not in entry or "at" not in entry:
            problems.append(f"visual entry needs 'category' and 'at': {entry}")
        elif entry["category"] not in ("Weapon", "Substance", "Graphic"):
            problems.append(f"unknown visual category '{entry['category']}'")
    for entry in data.get("ad_spots", []):
        if "start" not in entry or "end" not in entry:
            problems.append(f"ad_spot entry needs 'start' and 'end': {entry}")
        elif entry["end"] <= entry["start"]:
            problems.append(f"ad_spot ends before it starts: {entry}")
    return problems


def _evaluate_one(label: dict, mode: str) -> ClipResult:
    clip_path = CLIPS_DIR / label["clip"]
    result = ClipResult(clip=label["clip"])

    if not clip_path.exists():
        result.error = f"clip not found: {clip_path}"
        return result

    try:
        meta = probe_video(clip_path)
        video_id = repo.insert_video(
            clip_path.name, str(clip_path),
            round(clip_path.stat().st_size / 1_048_576, 2),
            meta["duration_sec"], meta["fps"], meta["width"], meta["height"],
        )
        summary = process_video(video_id, demo=(mode == "demo"))
        result.engines = summary.get("engines", {})
    except Exception as e:
        result.error = f"{type(e).__name__}: {e}"
        return result

    # Audio — keyed on the flagged word (severity comes from our dictionary, not
    # the model, so scoring it would measure the config rather than the engine).
    truth_audio = [{"key": e["word"], "time": float(e["at"])} for e in label.get("audio", [])]
    pred_audio = [{"key": f["word_flagged"], "time": f["timestamp_start"]}
                  for f in repo.get_audio_flags(video_id)]
    result.audio = match_events(truth_audio, pred_audio, AUDIO_TOLERANCE_SEC)

    # Visual — keyed on risk category, which is stable across models; the raw class
    # label is model-specific and would penalise a perfectly good detector.
    truth_visual = [{"key": e["category"], "time": float(e["at"])} for e in label.get("visual", [])]
    pred_visual = [{"key": f["risk_category"], "time": f["frame_timestamp"]}
                   for f in repo.get_visual_flags(video_id)]
    result.visual = match_events(truth_visual, pred_visual, VISUAL_TOLERANCE_SEC)

    # Ad spots — temporal overlap, since these are stretches rather than instants.
    truth_spots = [{"start": float(e["start"]), "end": float(e["end"])}
                   for e in label.get("ad_spots", [])]
    pred_spots = [{"start": s["timestamp_start"], "end": s["timestamp_end"]}
                  for s in repo.get_ad_spots(video_id)]
    result.ad_spots = match_intervals(truth_spots, pred_spots, ADSPOT_IOU)

    return result


def _engine_status(results: list[ClipResult]) -> dict[str, str]:
    """Classify each stage as measuring a real engine or a stand-in."""
    status = {}
    for stage in ("audio", "visual", "ad_spots"):
        names = {r.engines.get(stage, "") for r in results if r.engines}
        joined = " ".join(names).lower()
        if not joined:
            status[stage] = "unknown"
        elif "demo" in joined:
            status[stage] = "stubbed"
        else:
            status[stage] = "valid"
    return status


def run(mode: str = "real", keep_scratch: bool = False) -> dict:
    """Run the whole benchmark. Returns a report dict (also written to results/)."""
    labels = load_labels()
    if not labels:
        raise ValueError(
            f"No label files in {LABELS_DIR}. See benchmark/README.md for the format."
        )

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    scratch_dir = BENCHMARK_DIR / ".scratch"
    scratch_dir.mkdir(parents=True, exist_ok=True)
    scratch_db = scratch_dir / "benchmark.db"
    scratch_db.unlink(missing_ok=True)

    results: list[ClipResult] = []
    with _scratch_database(scratch_db):
        for label in labels:
            results.append(_evaluate_one(label, mode))

    if not keep_scratch:
        shutil.rmtree(scratch_dir, ignore_errors=True)

    engines = _engine_status(results)
    ok = [r for r in results if r.error is None]

    totals = {
        "audio": sum((r.audio.metrics for r in ok), Metrics()),
        "visual": sum((r.visual.metrics for r in ok), Metrics()),
        "ad_spots": sum((r.ad_spots.metrics for r in ok), Metrics()),
    }

    # Category breakdowns, recomputed across every clip at once.
    all_truth_audio, all_pred_audio = [], []
    all_truth_visual, all_pred_visual = [], []
    for label, r in zip(labels, results):
        if r.error:
            continue
        all_truth_audio += [{"key": e["word"], "time": float(e["at"])}
                            for e in label.get("audio", [])]
        all_truth_visual += [{"key": e["category"], "time": float(e["at"])}
                             for e in label.get("visual", [])]
        all_pred_audio += [{"key": t["key"], "time": t["time"]}
                           for t, _p, _d in r.audio.matched] + \
                          [{"key": p["key"], "time": p["time"]} for p in r.audio.false_positives]
        all_pred_visual += [{"key": t["key"], "time": t["time"]}
                            for t, _p, _d in r.visual.matched] + \
                           [{"key": p["key"], "time": p["time"]} for p in r.visual.false_positives]

    report = {
        "generated": datetime.now().isoformat(timespec="seconds"),
        "mode": mode,
        "clips_total": len(labels),
        "clips_evaluated": len(ok),
        "clips_failed": [{"clip": r.clip, "error": r.error} for r in results if r.error],
        "engine_status": engines,
        "precision_target": PRECISION_TARGET,
        "stages": {},
        "per_clip": [],
    }

    for stage, m in totals.items():
        report["stages"][stage] = {
            **m.as_dict(),
            "engine": engines.get(stage, "unknown"),
            "counts_toward_claim": engines.get(stage) == "valid",
            "meets_target": (m.precision >= PRECISION_TARGET) if m.support else None,
        }

    # Is there enough evidence to quote a figure at all?
    valid_support = sum(s["support"] for s in report["stages"].values()
                        if s["counts_toward_claim"])
    real_clips = [l for l, r in zip(labels, results)
                  if r.error is None and not l.get("synthetic")]
    shortfalls = []
    if valid_support < MIN_EVENTS_FOR_CLAIM:
        shortfalls.append(
            f"only {valid_support} labelled events on real engines "
            f"(want at least {MIN_EVENTS_FOR_CLAIM})")
    if len(real_clips) < MIN_REAL_CLIPS_FOR_CLAIM:
        shortfalls.append(
            f"only {len(real_clips)} non-synthetic clip(s) "
            f"(want at least {MIN_REAL_CLIPS_FOR_CLAIM})")
    report["evidence"] = {
        "labelled_events_on_real_engines": valid_support,
        "real_clips": len(real_clips),
        "synthetic_clips": len(labels) - len(real_clips),
        "sufficient": not shortfalls,
        "shortfalls": shortfalls,
    }

    report["by_category"] = {
        "audio": {k: v.as_dict() for k, v in
                  per_category(all_truth_audio, all_pred_audio, AUDIO_TOLERANCE_SEC).items()},
        "visual": {k: v.as_dict() for k, v in
                   per_category(all_truth_visual, all_pred_visual, VISUAL_TOLERANCE_SEC).items()},
    }

    for r in results:
        report["per_clip"].append({
            "clip": r.clip,
            "error": r.error,
            "audio": r.audio.metrics.as_dict(),
            "visual": r.visual.metrics.as_dict(),
            "ad_spots": r.ad_spots.metrics.as_dict(),
            "missed_audio": [t["key"] for t in r.audio.false_negatives],
            "spurious_audio": [p["key"] for p in r.audio.false_positives],
        })

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = RESULTS_DIR / f"benchmark_{stamp}.json"
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    report["_written_to"] = str(out)
    return report
