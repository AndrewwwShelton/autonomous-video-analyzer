"""Pipeline orchestrator (Module 3).

Runs the engines SEQUENTIALLY (decision D2): audio -> vision -> ad spots. Sequential
avoids GPU/RAM contention between Whisper and YOLO and keeps SQLite to one writer.

Engine selection is per stage, not global. As of M1 the audio engine is real; vision
and ad-spots remain demo twins until M2/M3a. The returned summary names the engine
that produced each result, so a caller can never mistake demo output for real output.

What stays REAL in every mode: the database layer, the compliance matcher, and the
temporal ad-spot tracker. Demo engines only stand in for model inference.
"""
import traceback
from pathlib import Path
from typing import Callable

from src import config
from src.audio.compliance import match_transcript
from src.audio.extractor import NoAudioTrackError, extract_audio
from src.audio.transcriber import (DemoTranscriber, FasterWhisperTranscriber,
                                   TranscriptionError)
from src.db import repository as repo
from src.vision.adspots import DemoAdSpotFinder
from src.vision.detector import DemoDetector
from src.vision.tracker import merge_candidates

ProgressCallback = Callable[[str, float], None]  # (stage_label, fraction 0..1)


def _run_audio_stage(video: dict, demo: bool, report: ProgressCallback) -> tuple[list, str]:
    """Transcribe and match. Returns (audio_flag_dicts, engine_name).

    A video with no audio track is not a failure — it simply yields no audio flags,
    and the rest of the pipeline continues.
    """
    video_id = video["video_id"]

    if demo:
        report("Transcribing audio (demo)", 0.10)
        transcriber = DemoTranscriber(seed=video_id)
        words = transcriber.transcribe(video["duration_sec"])
        engine = transcriber.name
    else:
        model_size = repo.get_config("whisper_model") or config.DEFAULT_WHISPER_MODEL
        transcriber = FasterWhisperTranscriber(model_size)
        engine = transcriber.name

        report("Extracting audio track", 0.05)
        wav_path = config.DATA_DIR / "audio" / f"video_{video_id}.wav"
        try:
            extract_audio(Path(video["filepath"]), wav_path)
        except NoAudioTrackError:
            report("No audio track — skipping transcription", 0.30)
            return [], f"{engine} (no audio track)"

        report(f"Transcribing audio ({model_size})", 0.10)
        try:
            words = transcriber.transcribe(wav_path)
        finally:
            wav_path.unlink(missing_ok=True)   # intermediate artefact, not kept

    report("Matching restricted keywords", 0.30)
    dictionary = repo.get_config("profanity_dictionary") or []
    flags = match_transcript(words, dictionary, detection_model=engine)
    repo.insert_audio_flags(video_id, flags)
    return flags, engine


def process_video(video_id: int, demo: bool = True,
                  progress: ProgressCallback | None = None) -> dict:
    """Run the full analysis pipeline for one uploaded video.

    demo=True  -> every engine is a deterministic stand-in; needs no models.
    demo=False -> real engines where implemented (audio, as of M1), demo elsewhere.

    Status transitions: pending -> processing -> completed | failed.
    Re-running clears previous flags first, so processing is idempotent.
    """
    def report(stage: str, frac: float) -> None:
        if progress:
            progress(stage, frac)

    video = repo.get_video(video_id)
    if video is None:
        raise ValueError(f"No video with id {video_id}")

    repo.update_video_status(video_id, "processing")
    repo.clear_analysis(video_id)

    duration = video["duration_sec"]
    width = video["resolution_width"] or 1280
    height = video["resolution_height"] or 720
    engines: dict[str, str] = {}

    try:
        # Stage 1 — Audio & NLP (Module 1). Real as of M1.
        audio_flags, engines["audio"] = _run_audio_stage(video, demo, report)

        # Stage 2 — Vision risks (Module 2). Demo until M2.
        report("Scanning frames for visual risks", 0.55)
        visual_flags = DemoDetector(seed=video_id).detect(duration, width, height)
        threshold = repo.get_config("detection_confidence_threshold") or 0.5
        visual_flags = [f for f in visual_flags if f["confidence_score"] >= threshold]
        repo.insert_visual_flags(video_id, visual_flags)
        engines["visual"] = "demo-detector"

        # Stage 3 — Ad spots. Demo candidates feed the REAL temporal tracker until M3a.
        report("Locating ad placement surfaces", 0.80)
        sample_fps = repo.get_config("frame_sample_fps") or 1.0
        min_dur = repo.get_config("min_ad_spot_duration_sec") or 5.0
        frames = DemoAdSpotFinder(seed=video_id).candidates_by_frame(
            duration, width, height, sample_fps)
        spots = merge_candidates(frames, min_duration_sec=min_dur)
        repo.insert_ad_spots(video_id, spots)
        engines["ad_spots"] = "demo-adspots + real tracker"

        repo.update_video_status(video_id, "completed")
        report("Done", 1.0)
        return {"audio": len(audio_flags), "visual": len(visual_flags),
                "ad_spots": len(spots), "engines": engines}

    except TranscriptionError as e:
        repo.update_video_status(video_id, "failed")
        report(str(e), 1.0)
        raise
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
