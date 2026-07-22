"""Synthetic demo footage generator — dev tooling so the UI can be exercised without
hunting for test videos. Draws a simple animated 'studio scene' with OpenCV, then
transcodes to H.264 (browser-playable) with the ffmpeg bundled in imageio-ffmpeg.
"""
import subprocess
from pathlib import Path

import cv2
import imageio_ffmpeg
import numpy as np

from src import config


def _transcode_h264(src: Path, dst: Path) -> None:
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    subprocess.run(
        [ffmpeg, "-y", "-i", str(src), "-c:v", "libx264", "-pix_fmt", "yuv420p",
         "-movflags", "+faststart", str(dst)],
        check=True, capture_output=True,
    )


def generate_demo_video(duration_sec: int = 36, fps: int = 24,
                        size: tuple[int, int] = (960, 540)) -> Path:
    config.ensure_dirs()
    raw = config.VIDEO_DIR / "demo_source_raw.mp4"
    out = config.VIDEO_DIR / "demo_source.mp4"
    w, h = size

    writer = cv2.VideoWriter(str(raw), cv2.VideoWriter_fourcc(*"mp4v"), fps, size)
    if not writer.isOpened():
        raise RuntimeError("OpenCV could not open a video writer for mp4 output.")

    total = duration_sec * fps
    for i in range(total):
        t = i / fps
        frame = np.full((h, w, 3), (46, 38, 34), dtype=np.uint8)  # dark studio backdrop

        # "Wall" — the stable blank region the ad-spot demo points at (right side)
        cv2.rectangle(frame, (int(w * 0.60), int(h * 0.08)), (w - 8, int(h * 0.58)),
                      (74, 66, 60), -1)
        # "Desk" along the bottom
        cv2.rectangle(frame, (int(w * 0.28), int(h * 0.62)), (int(w * 0.82), h - 10),
                      (96, 76, 58), -1)
        # "Screen" that appears mid-video
        if duration_sec * 0.5 <= t <= duration_sec * 0.7:
            cv2.rectangle(frame, (int(w * 0.14), int(h * 0.18)), (int(w * 0.44), int(h * 0.52)),
                          (200, 180, 90), -1)
        # A moving "presenter" blob so the footage isn't static
        cx = int(w * (0.25 + 0.18 * np.sin(t * 0.9)))
        cv2.circle(frame, (cx, int(h * 0.45)), 46, (150, 130, 210), -1)

        cv2.putText(frame, f"DEMO FOOTAGE  t={t:5.1f}s", (24, h - 24),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (230, 230, 230), 2, cv2.LINE_AA)
        writer.write(frame)

    writer.release()
    _transcode_h264(raw, out)
    raw.unlink(missing_ok=True)
    return out


if __name__ == "__main__":
    print(generate_demo_video())
