"""Pipeline orchestrator (Module 3).

Runs the engines SEQUENTIALLY (decision D2): audio -> vision -> ad spots. Sequential
avoids GPU/RAM contention between Whisper and YOLO and keeps SQLite to one writer.

Engine selection is per stage, not global. As of M1 the audio engine is real; vision
and ad-spots remain demo twins until M2/M3a. The returned summary names the engine
that produced each result, so a caller can never mistake demo output for real output.

What stays REAL in every mode: the database layer, the compliance matcher, and the
temporal ad-spot tracker. Demo engines only stand in for model inference.
"""
import os
import traceback
from pathlib import Path
from typing import Callable

from src import config
from src.audio.compliance import match_transcript
from src.audio.extractor import NoAudioTrackError, extract_audio
from src.audio.transcriber import (DemoTranscriber, FasterWhisperTranscriber,
                                   TranscriptionError)
from src.db import repository as repo
from src.vision.adspots import DemoAdSpotFinder, find_ad_spot_candidates
from src.vision.detector import (DemoDetector, DetectorError, YoloDetector,
                                 to_risk_flags)
from src.vision.overlay import DemoOverlayFinder, OverlayAccumulator
from src.vision.sampler import sample_frames
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
        # Unique per process. A fixed path meant two analyses of the same video --
        # the server's and a script run against the same database -- collided on
        # one scratch file, and whichever finished first deleted it in its
        # `finally`, leaving the other transcribing a path that no longer existed.
        wav_path = config.DATA_DIR / "audio" / f"video_{video_id}_{os.getpid()}.wav"
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


def _run_vision_stage(video: dict, demo: bool,
                      report: ProgressCallback) -> tuple[list, str, list]:
    """Sample frames once, producing both risk flags and ad-spot candidates.

    Decision D4: one inference pass, two consumers. Detections identify visual
    risks, and the same detections define the occupancy mask the free-space
    algorithm needs -- so the frames are decoded and the models run only once.

    Returns (visual_flag_dicts, engine_name, per_frame_adspot_candidates). The
    candidate list is empty in demo mode, where the demo finder supplies its own.
    """
    video_id = video["video_id"]
    duration = video["duration_sec"]
    threshold = repo.get_config("detection_confidence_threshold") or 0.5

    if demo:
        report("Scanning frames for visual risks (demo)", 0.55)
        detector = DemoDetector(seed=video_id)
        flags = detector.detect(duration,
                                video["resolution_width"] or 1280,
                                video["resolution_height"] or 720)
        flags = [f for f in flags if f["confidence_score"] >= threshold]
        repo.insert_visual_flags(video_id, flags)
        demo_overlay = DemoOverlayFinder(seed=video_id)
        repo.set_overlay_context(video_id, demo_overlay.report().as_dict())
        return flags, f"{detector.name} + {demo_overlay.name}", []

    sample_fps = repo.get_config("frame_sample_fps") or 1.0
    weights = repo.get_config("vision_weights") or ["yolov8n.pt"]
    detector = YoloDetector(tuple(weights), confidence_threshold=threshold)

    flags: list = []
    frames_candidates: list[tuple[float, list[dict]]] = []
    expected = max(1, int(duration * sample_fps))
    # Third consumer of the same decoded frame (D4). Overlay detection needs the
    # whole sequence, not one image, but it accumulates in constant memory so it
    # costs a running sum per frame rather than a second pass over the file.
    overlay = OverlayAccumulator()

    for i, (timestamp, frame) in enumerate(sample_frames(Path(video["filepath"]),
                                                         sample_fps)):
        detections = detector.detect_frame(frame, timestamp)
        flags += to_risk_flags(detections, detection_model=detector.name)
        frames_candidates.append((timestamp, find_ad_spot_candidates(frame, detections)))
        overlay.add(frame)
        if i % 5 == 0:
            # Vision dominates runtime, so it owns the 0.40-0.75 progress band.
            report(f"Scanning frames ({i + 1}/{expected})",
                   0.40 + 0.35 * min(1.0, (i + 1) / expected))

    repo.insert_visual_flags(video_id, flags)
    repo.set_overlay_context(video_id, overlay.report().as_dict())
    return flags, detector.name, frames_candidates


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

        # Stage 2 — Vision risks (Module 2). Real as of M2. Also yields the
        # per-frame ad-spot candidates, from the same inference pass.
        visual_flags, engines["visual"], frame_candidates = _run_vision_stage(
            video, demo, report)

        # Stage 3 — Ad spots (Module 2). Real as of M3a. The temporal tracker was
        # already real; this now feeds it genuine free-space geometry.
        report("Locating ad placement surfaces", 0.80)
        sample_fps = repo.get_config("frame_sample_fps") or 1.0
        min_dur = repo.get_config("min_ad_spot_duration_sec") or 5.0
        if demo:
            frame_candidates = DemoAdSpotFinder(seed=video_id).candidates_by_frame(
                duration, width, height, sample_fps)
            engines["ad_spots"] = "demo-adspots + real tracker"
        else:
            engines["ad_spots"] = "free-space + real tracker"
        spots = merge_candidates(frame_candidates, min_duration_sec=min_dur)
        repo.insert_ad_spots(video_id, spots)

        repo.update_video_status(video_id, "completed")
        report("Done", 1.0)
        return {"audio": len(audio_flags), "visual": len(visual_flags),
                "ad_spots": len(spots), "engines": engines}

    except (TranscriptionError, DetectorError) as e:
        repo.update_video_status(video_id, "failed")
        report(str(e), 1.0)
        raise
    except Exception:
        repo.update_video_status(video_id, "failed")
        traceback.print_exc()
        raise


# An overlay downgrades a weapon finding only when the evidence looks like an
# interface rather than a badge. A single region is a channel watermark and says
# nothing about whether the footage is rendered; several regions covering part of
# the frame is a heads-up display. See src/vision/overlay.py.
MIN_OVERLAY_CONFIDENCE = 0.5
MIN_OVERLAY_REGIONS = 2


def _looks_like_rendered_gameplay(overlay: dict | None) -> bool:
    if not overlay or overlay.get("verdict") != "overlay":
        return False
    return (overlay.get("confidence", 0.0) >= MIN_OVERLAY_CONFIDENCE
            and overlay.get("region_count", 0) >= MIN_OVERLAY_REGIONS)


def assess_compliance(video_id: int) -> dict:
    """Compliance status with the reasoning that produced it.

    The original rule was a bare `any()`: one Weapon detection in one frame
    restricted the whole video. On a ten-minute video that is 0.17% of the
    runtime deciding the outcome, and it restricted gameplay footage for weapons
    that were rendered rather than real — exactly the context-blind over-flagging
    this project set out to criticise.

    Two changes fix it. Weapon findings are now weighed against persistent-overlay
    evidence, and the outcome has a third state. Binary was the original flaw:
    'Monetizable' over-claims when weapons are genuinely present, and 'Restricted'
    over-punishes when they are drawn. 'Review' says what is actually true — a
    human should look.

    Nothing is ever suppressed. Every flag remains recorded and visible; only the
    verdict weighs context, and it always explains itself.
    """
    audio_flags = repo.get_audio_flags(video_id)
    visual_flags = repo.get_visual_flags(video_id)
    overlay = repo.get_overlay_context(video_id)

    audio_high = [f for f in audio_flags if f["severity"] == "High"]
    weapons = [f for f in visual_flags if f["risk_category"] == "Weapon"]

    def result(verdict: str, reason: str) -> dict:
        return {"verdict": verdict, "reason": reason,
                "high_severity_audio": len(audio_high), "weapon_flags": len(weapons),
                "overlay": overlay}

    # Spoken words are judged on their own terms. What is drawn over the picture
    # says nothing about what was said, so an overlay never excuses audio.
    if audio_high:
        words = ", ".join(sorted({f["word_flagged"] for f in audio_high})[:3])
        return result("Restricted",
                      f"{len(audio_high)} high-severity spoken term(s) ({words}). "
                      f"Spoken content is judged independently of any overlay.")

    if not weapons:
        return result("Monetizable",
                      "No high-severity spoken terms and no weapon detections.")

    if _looks_like_rendered_gameplay(overlay):
        return result("Review",
                      f"{len(weapons)} weapon detection(s), but {overlay['reason']} "
                      f"Weapons rendered inside a game are not the same as real "
                      f"ones, and this tool cannot tell them apart with certainty — "
                      f"a human should confirm before any action is taken.")

    return result("Restricted",
                  f"{len(weapons)} weapon detection(s) with no evidence of a game "
                  f"interface, so the footage is treated as real.")


def compliance_verdict(video_id: int) -> str:
    """'Monetizable' | 'Review' | 'Restricted'. See assess_compliance for why."""
    return assess_compliance(video_id)["verdict"]
