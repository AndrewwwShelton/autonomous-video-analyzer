"""Pipeline orchestrator (Module 3).

Runs the engines SEQUENTIALLY (decision D2): audio -> vision -> ad spots. Sequential
avoids GPU/RAM contention between Whisper and YOLO and keeps SQLite to one writer.

Demo mode (the default until M1/M2 land) swaps the model-backed engines for their
Demo twins. Note what stays REAL even in demo mode: the DB layer, the compliance
matcher, and the temporal tracker — demo engines only fake the model outputs.
"""
import traceback
from typing import Callable

from src.audio.compliance import match_transcript
from src.audio.transcriber import DemoTranscriber
from src.db import repository as repo
from src.vision.adspots import DemoAdSpotFinder
from src.vision.detector import DemoDetector
from src.vision.tracker import merge_candidates

ProgressCallback = Callable[[str, float], None]  # (stage_label, fraction 0..1)


def process_video(video_id: int, demo: bool = True,
                  progress: ProgressCallback | None = None) -> dict:
    """Run the full analysis pipeline for one uploaded video. Returns summary counts.

    Status transitions: pending -> processing -> completed | failed.
    Re-running clears previous flags first, so processing is idempotent.
    """
    def report(stage: str, frac: float) -> None:
        if progress:
            progress(stage, frac)

    video = repo.get_video(video_id)
    if video is None:
        raise ValueError(f"No video with id {video_id}")

    if not demo:
        raise NotImplementedError(
            "Real engines land in M1 (audio) and M2 (vision) — see PLAN.md. "
            "Run in demo mode until then."
        )

    repo.update_video_status(video_id, "processing")
    repo.clear_analysis(video_id)

    duration = video["duration_sec"]
    width = video["resolution_width"] or 1280
    height = video["resolution_height"] or 720

    try:
        # Stage 1 — Audio & NLP (Module 1)
        report("Transcribing audio", 0.10)
        words = DemoTranscriber(seed=video_id).transcribe(duration)
        report("Matching restricted keywords", 0.30)
        dictionary = repo.get_config("profanity_dictionary") or []
        audio_flags = match_transcript(words, dictionary, detection_model="demo-transcriber")
        repo.insert_audio_flags(video_id, audio_flags)

        # Stage 2 — Vision risks (Module 2)
        report("Scanning frames for visual risks", 0.55)
        visual_flags = DemoDetector(seed=video_id).detect(duration, width, height)
        threshold = repo.get_config("detection_confidence_threshold") or 0.5
        visual_flags = [f for f in visual_flags if f["confidence_score"] >= threshold]
        repo.insert_visual_flags(video_id, visual_flags)

        # Stage 3 — Ad spots: demo candidates feed the REAL temporal tracker
        report("Locating ad placement surfaces", 0.80)
        sample_fps = repo.get_config("frame_sample_fps") or 1.0
        min_dur = repo.get_config("min_ad_spot_duration_sec") or 5.0
        frames = DemoAdSpotFinder(seed=video_id).candidates_by_frame(
            duration, width, height, sample_fps)
        spots = merge_candidates(frames, min_duration_sec=min_dur)
        repo.insert_ad_spots(video_id, spots)

        repo.update_video_status(video_id, "completed")
        report("Done", 1.0)
        return {"audio": len(audio_flags), "visual": len(visual_flags), "ad_spots": len(spots)}

    except Exception:
        repo.update_video_status(video_id, "failed")
        traceback.print_exc()
        raise


def compliance_verdict(video_id: int) -> str:
    """DDD compliance_status: 'Restricted' if any High-severity audio flag or any
    Weapon-category visual flag exists; otherwise 'Monetizable'."""
    audio_high = any(f["severity"] == "High" for f in repo.get_audio_flags(video_id))
    visual_weapon = any(f["risk_category"] == "Weapon" for f in repo.get_visual_flags(video_id))
    return "Restricted" if (audio_high or visual_weapon) else "Monetizable"
