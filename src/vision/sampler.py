"""Frame sampling (Module 2, stage 1) — REAL code.

Yields (timestamp_sec, frame) pairs at the configured sample rate (default 1 FPS per
SRS FR3). Seeks by frame index rather than decoding every frame, so a 1-hour video
costs ~3600 decodes, not ~86,000.
"""
from pathlib import Path
from typing import Iterator

import cv2
import numpy as np


def probe_video(video_path: Path) -> dict:
    """Return duration/fps/resolution for VideoMetadata. Raises ValueError if unreadable."""
    cap = cv2.VideoCapture(str(video_path))
    try:
        if not cap.isOpened():
            raise ValueError(f"OpenCV could not open video: {video_path}")
        fps = cap.get(cv2.CAP_PROP_FPS) or 0.0
        frames = cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0.0
        return {
            "fps": round(fps, 3),
            "duration_sec": round(frames / fps, 3) if fps > 0 else 0.0,
            "width": int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
            "height": int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
        }
    finally:
        cap.release()


def save_thumbnail(video_path: Path, out_jpg: Path, at_sec: float = 1.0,
                   width: int = 480) -> Path | None:
    """Grab one frame and save a resized JPEG thumbnail. Returns None on failure."""
    cap = cv2.VideoCapture(str(video_path))
    try:
        if not cap.isOpened():
            return None
        fps = cap.get(cv2.CAP_PROP_FPS) or 24.0
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(at_sec * fps))
        ok, frame = cap.read()
        if not ok:  # very short clip — fall back to the first frame
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            ok, frame = cap.read()
        if not ok:
            return None
        h, w = frame.shape[:2]
        thumb = cv2.resize(frame, (width, max(1, round(h * width / w))))
        out_jpg.parent.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(out_jpg), thumb, [cv2.IMWRITE_JPEG_QUALITY, 85])
        return out_jpg
    finally:
        cap.release()


def sample_frames(video_path: Path, sample_fps: float = 1.0) -> Iterator[tuple[float, np.ndarray]]:
    cap = cv2.VideoCapture(str(video_path))
    try:
        if not cap.isOpened():
            raise ValueError(f"OpenCV could not open video: {video_path}")
        native_fps = cap.get(cv2.CAP_PROP_FPS)
        total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        if native_fps <= 0:
            return
        step = max(1, round(native_fps / sample_fps))
        for frame_idx in range(0, total, step):
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
            ok, frame = cap.read()
            if not ok:
                break
            yield round(frame_idx / native_fps, 3), frame
    finally:
        cap.release()
