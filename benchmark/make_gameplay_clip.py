"""Generate a synthetic gameplay clip for demonstrating overlay detection.

    python benchmark/make_gameplay_clip.py

Produces footage with the two properties that distinguish rendered gameplay from
filmed video, and nothing else:

  * a world that moves continuously, as a first-person camera does; and
  * a heads-up display pinned to fixed pixels — crosshair, health bar, minimap,
    ammo counter — that never moves with it.

IMPORTANT -- what this is and is not:

  IS  : a way to demonstrate and regression-test src/vision/overlay.py without
        needing a copyrighted capture of a commercial game.
  NOT : evidence that the detector works on real gameplay. It is drawn to match
        the very signal the detector looks for, so passing on it proves the code
        runs, not that the thresholds hold against Call of Duty or Fortnite.
        Validating that needs real captures, which this project does not have and
        cannot lawfully redistribute. Stated plainly because the distinction is
        exactly the sort a viva question lands on.
"""
import sys
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.demo_media import _transcode_h264      # noqa: E402

CLIPS_DIR = ROOT / "benchmark" / "clips"
CLIP_NAME = "synthetic_gameplay_01.mp4"

W, H = 960, 540
FPS = 24
DURATION = 20

INK = (236, 236, 236)


def _build_world(rng: np.random.Generator) -> np.ndarray:
    """One wide, fully textured panorama. The camera pans across it.

    Rendering the world once and cropping a moving window is what makes the
    motion realistic. A first attempt drew flat sky and flat ground each frame
    and scrolled shapes across them; large uniform areas look identical however
    far they slide, so only 34% of pixels changed and the detector correctly
    refused to judge. Texture everywhere is the point -- it is what a real camera
    moving through a real scene produces.
    """
    world_w = W * 4
    world = np.zeros((H, world_w, 3), dtype=np.uint8)

    # Sky and ground, each with their own grain. The sky carries real features
    # too: a smooth gradient pans without changing any pixel by much, and the
    # detector would then see too little motion to judge the frame at all.
    horizon = int(H * 0.52)
    world[:horizon] = (52, 40, 34)
    world[horizon:] = (44, 38, 33)
    world = cv2.add(world, rng.integers(0, 55, world.shape, dtype=np.uint8))

    for _ in range(220):                       # cloud banks and distant relief
        cx, cy = int(rng.integers(0, world_w)), int(rng.integers(0, horizon))
        axes = (int(rng.integers(40, 150)), int(rng.integers(10, 40)))
        shade = int(rng.integers(56, 104))
        cv2.ellipse(world, (cx, cy), axes, float(rng.integers(0, 180)), 0, 360,
                    (shade - 8, shade - 2, shade + 6), -1)

    # Scattered structures and debris, dense enough that any window holds detail.
    for i in range(60):
        bx = int(rng.integers(0, world_w))
        bh = int(rng.integers(60, 210))
        bw = int(rng.integers(70, 190))
        shade = int(rng.integers(70, 130))
        cv2.rectangle(world, (bx, horizon - bh), (bx + bw, horizon),
                      (shade - 14, shade - 6, shade), -1)
        cv2.rectangle(world, (bx, horizon - bh), (bx + bw, horizon),
                      (shade + 26, shade + 34, shade + 40), 1)
        for wy in range(horizon - bh + 14, horizon - 14, 34):
            for wx in range(bx + 12, bx + bw - 16, 30):
                cv2.rectangle(world, (wx, wy), (wx + 14, wy + 18),
                              (shade + 46, shade + 40, shade + 30), -1)

    for _ in range(500):
        px, py = int(rng.integers(0, world_w)), int(rng.integers(horizon, H))
        cv2.circle(world, (px, py), int(rng.integers(1, 4)),
                   tuple(int(v) for v in rng.integers(50, 110, 3)), -1)
    return world


def _world_view(world: np.ndarray, t: float, rng: np.random.Generator) -> np.ndarray:
    """Crop a moving window, with a slight vertical bob as a held camera has."""
    world_w = world.shape[1]
    x = int(t * 300) % (world_w - W)
    bob = int(6 * np.sin(t * 3.1))
    view = world[:, x:x + W].copy()
    view = np.roll(view, bob, axis=0)
    # Sensor noise, as a real capture carries.
    return cv2.add(view, rng.integers(0, 12, view.shape, dtype=np.uint8))


def _hud(frame: np.ndarray) -> np.ndarray:
    """Fixed interface furniture. Identical pixels in every single frame."""
    cx, cy = W // 2, H // 2
    cv2.line(frame, (cx - 14, cy), (cx - 5, cy), INK, 2)
    cv2.line(frame, (cx + 5, cy), (cx + 14, cy), INK, 2)
    cv2.line(frame, (cx, cy - 14), (cx, cy - 5), INK, 2)
    cv2.line(frame, (cx, cy + 5), (cx, cy + 14), INK, 2)

    cv2.rectangle(frame, (34, H - 58), (274, H - 38), (70, 70, 70), -1)
    cv2.rectangle(frame, (34, H - 58), (208, H - 38), (60, 190, 60), -1)
    cv2.rectangle(frame, (34, H - 58), (274, H - 38), INK, 1)
    cv2.putText(frame, "HEALTH", (34, H - 66), cv2.FONT_HERSHEY_SIMPLEX, 0.45, INK, 1)

    cv2.rectangle(frame, (W - 186, 24), (W - 34, 152), (24, 24, 24), -1)
    cv2.rectangle(frame, (W - 186, 24), (W - 34, 152), INK, 1)
    cv2.circle(frame, (W - 110, 88), 4, (60, 190, 60), -1)
    cv2.putText(frame, "N", (W - 114, 44), cv2.FONT_HERSHEY_SIMPLEX, 0.45, INK, 1)

    cv2.putText(frame, "27 / 90", (W - 220, H - 40), cv2.FONT_HERSHEY_SIMPLEX,
                0.95, INK, 2)
    return frame


def main() -> int:
    CLIPS_DIR.mkdir(parents=True, exist_ok=True)
    raw = CLIPS_DIR / "_gameplay_raw.mp4"
    out = CLIPS_DIR / CLIP_NAME

    rng = np.random.default_rng(11)
    world = _build_world(rng)
    writer = cv2.VideoWriter(str(raw), cv2.VideoWriter_fourcc(*"mp4v"), FPS, (W, H))
    if not writer.isOpened():
        print("Could not open a video writer.")
        return 1
    try:
        for i in range(DURATION * FPS):
            writer.write(_hud(_world_view(world, i / FPS, rng)))
    finally:
        writer.release()

    # mp4v does not play in browsers; the app serves this to a <video> element.
    _transcode_h264(raw, out)
    raw.unlink(missing_ok=True)

    print(f"wrote {out.relative_to(ROOT)}  ({DURATION}s, {W}x{H})")
    print("\nUpload it with the Create button and run checks in 'real' mode.")
    print("Expected: weapon-free, but reported as a persistent overlay.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
