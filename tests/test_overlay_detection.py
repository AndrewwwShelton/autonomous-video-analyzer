"""Persistent-overlay detection.

Each synthetic scene here stands for a real failure mode. The negative cases
matter more than the positive one: a detector that calls everything an overlay
would let genuine weapon footage be dismissed as gameplay, which is a worse
outcome than the over-flagging it was built to fix.
"""
import cv2
import numpy as np
import pytest

from src.vision.overlay import (OverlayAccumulator, OverlayParams, analyse_frames,
                                _position_of)

W, H = 640, 360
FRAMES = 30


def _moving_scene(n: int = FRAMES, seed: int = 7) -> list[np.ndarray]:
    """Filmed-footage stand-in: every pixel changes frame to frame."""
    rng = np.random.default_rng(seed)
    return [rng.integers(0, 256, (H, W, 3), dtype=np.uint8) for _ in range(n)]


def _draw_hud(frame: np.ndarray) -> np.ndarray:
    """A game interface: several fixed elements at the frame edges."""
    f = frame.copy()
    cv2.rectangle(f, (30, H - 50), (200, H - 30), (255, 255, 255), -1)   # health bar
    cv2.rectangle(f, (W - 150, 20), (W - 30, 120), (255, 255, 255), 2)   # minimap
    cv2.putText(f, "27 / 90", (W - 190, H - 30), cv2.FONT_HERSHEY_SIMPLEX,
                0.9, (255, 255, 255), 2)                                  # ammo
    cv2.line(f, (W // 2 - 12, H // 2), (W // 2 + 12, H // 2), (255, 255, 255), 2)
    cv2.line(f, (W // 2, H // 2 - 12), (W // 2, H // 2 + 12), (255, 255, 255), 2)
    return f


# --------------------------------------------------------------- positive case

def test_gameplay_hud_is_detected():
    frames = [_draw_hud(f) for f in _moving_scene()]
    r = analyse_frames(frames)
    assert r.verdict == "overlay", r.reason
    assert len(r.regions) >= 2, f"expected several HUD elements, got {r.regions}"
    assert r.confidence > 0.4
    assert "heads-up display" in r.reason


def test_detected_regions_are_in_original_frame_coordinates():
    """Analysis runs downscaled; boxes must come back in source pixels or the
    interface would draw them in the wrong place."""
    frames = [_draw_hud(f) for f in _moving_scene()]
    r = analyse_frames(frames)
    for region in r.regions:
        x1, y1, x2, y2 = region["box"]
        assert 0 <= x1 < x2 <= W, region
        assert 0 <= y1 < y2 <= H, region
    assert any(x2 > W * 0.6 for x1, y1, x2, y2 in (rg["box"] for rg in r.regions)), (
        "the minimap sits in the right third; no region reached there"
    )


# --------------------------------------------------------------- negative cases

def test_plain_moving_footage_has_no_overlay():
    r = analyse_frames(_moving_scene())
    assert r.verdict == "none", r.reason
    assert r.confidence == 0.0


def test_letterbox_bars_are_not_an_overlay():
    """Black bars are perfectly static, so a variance-only test calls them an
    overlay. The mean-image edge test is what rejects them: they have no
    internal structure."""
    frames = []
    for f in _moving_scene():
        f = f.copy()
        f[:45, :] = 0
        f[-45:, :] = 0
        frames.append(f)
    r = analyse_frames(frames)
    assert r.verdict == "none", f"letterboxing misread as overlay: {r.reason}"


def test_static_camera_is_inconclusive_not_overlay():
    """A locked-off shot of a still scene is stable everywhere. Claiming the whole
    frame is an overlay would be worse than admitting we cannot tell."""
    rng = np.random.default_rng(3)
    base = rng.integers(0, 256, (H, W, 3), dtype=np.uint8)
    frames = [base.copy() for _ in range(FRAMES)]
    r = analyse_frames(frames)
    assert r.verdict == "inconclusive", r.reason
    assert "static" in r.reason


def test_too_few_frames_is_inconclusive():
    """Persistence cannot be established from a handful of frames."""
    r = analyse_frames([_draw_hud(f) for f in _moving_scene(n=4)])
    assert r.verdict == "inconclusive"
    assert "persistence" in r.reason


def test_single_small_watermark_is_reported_as_such():
    """A channel bug is a genuine overlay but implies something different from a
    HUD. The report must not call it a game interface."""
    frames = []
    for f in _moving_scene():
        f = f.copy()
        cv2.putText(f, "ABC", (W - 90, 32), cv2.FONT_HERSHEY_SIMPLEX,
                    0.7, (255, 255, 255), 2)
        frames.append(f)
    r = analyse_frames(frames)
    if r.verdict == "overlay":
        assert "watermark" in r.reason, r.reason
        assert "heads-up display" not in r.reason


# ------------------------------------------------------------------- mechanics

def test_memory_does_not_grow_with_video_length():
    """The accumulator is streaming; a long video must not retain frames."""
    acc = OverlayAccumulator()
    for f in _moving_scene(n=FRAMES):
        acc.add(f)
    small = acc._sum.nbytes + acc._sumsq.nbytes
    acc2 = OverlayAccumulator()
    for f in _moving_scene(n=FRAMES * 4):
        acc2.add(f)
    assert acc2._sum.nbytes + acc2._sumsq.nbytes == small


def test_frames_of_differing_size_are_conformed():
    """Resolution changes mid-video must not abandon the measurement."""
    acc = OverlayAccumulator()
    for i, f in enumerate(_moving_scene()):
        acc.add(cv2.resize(f, (W // 2, H // 2)) if i % 3 == 0 else f)
    r = acc.report()
    assert r.frames_analysed == FRAMES
    assert r.verdict in {"none", "overlay", "inconclusive"}


def test_empty_accumulator_reports_inconclusive():
    assert OverlayAccumulator().report().verdict == "inconclusive"


@pytest.mark.parametrize("cx,cy,expected", [
    (10, 10, "top-left"), (315, 180, "centre"), (630, 350, "bottom-right"),
    (320, 10, "top-centre"), (10, 180, "middle-left"),
])
def test_position_labels(cx, cy, expected):
    assert _position_of(cx, cy, 640, 360) == expected


def test_real_locked_off_footage_is_not_called_gameplay():
    """Regression, from real video rather than a synthetic scene.

    data/videos/demo_source.mp4 is a locked-off shot: two fixed panels, burned-in
    caption text, one moving ball. At the original 12% motion gate it measured
    13% motion and 29% coverage, and was confidently reported as a heads-up
    display. Fixed objects in a still scene hold the same unchanging edges as an
    overlay; only the motion gate separates them.
    """
    from pathlib import Path

    from src.vision.sampler import sample_frames

    clip = Path("data/videos/demo_source.mp4")
    if not clip.exists():
        pytest.skip("demo video not generated (run demo_setup.py)")

    acc = OverlayAccumulator()
    for _, frame in sample_frames(clip, 2.0):
        acc.add(frame)
    r = acc.report()
    assert r.verdict != "overlay", (
        f"locked-off footage reported as an overlay: {r.reason}"
    )


def test_synthetic_gameplay_clip_is_detected_end_to_end():
    """The demonstrator clip, decoded from disk rather than built in memory.

    Guards the whole path -- H.264 decode, downscale, accumulate -- not just the
    arithmetic. Regenerate with: python benchmark/make_gameplay_clip.py
    """
    from pathlib import Path

    from src.vision.sampler import sample_frames

    clip = Path("benchmark/clips/synthetic_gameplay_01.mp4")
    if not clip.exists():
        pytest.skip("run benchmark/make_gameplay_clip.py to generate it")

    acc = OverlayAccumulator()
    for _, frame in sample_frames(clip, 1.0):
        acc.add(frame)
    r = acc.report()
    assert r.verdict == "overlay", r.reason
    assert r.motion_ratio > 0.40, (
        f"motion {r.motion_ratio:.0%} is too near the {OverlayParams().min_motion_ratio:.0%} "
        f"gate for this to be a stable regression case"
    )
    assert len(r.regions) >= 2


def test_report_serialises_for_the_api():
    r = analyse_frames([_draw_hud(f) for f in _moving_scene()])
    d = r.as_dict()
    assert d["region_count"] == len(d["regions"])
    assert set(d) >= {"verdict", "confidence", "reason", "motion_ratio",
                      "overlay_coverage", "frames_analysed"}


def test_params_are_tunable():
    """An impossible threshold must suppress detection, proving the knob is live."""
    frames = [_draw_hud(f) for f in _moving_scene()]
    acc = OverlayAccumulator(OverlayParams(min_coverage_frac=0.9))
    for f in frames:
        acc.add(f)
    assert acc.report().verdict == "none"
