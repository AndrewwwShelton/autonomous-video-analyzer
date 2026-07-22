"""Audio extraction (Module 1, stage 1). Fully functional — no system ffmpeg needed.

Extracts the audio track to 16 kHz mono WAV — the input format Whisper expects.
Uses the ffmpeg binary bundled with imageio-ffmpeg, so there is no PATH dependency
(see PLAN.md §2.1 note on skipping MoviePy).
"""
import subprocess
from pathlib import Path

import imageio_ffmpeg


def extract_audio(video_path: Path, out_wav: Path, sample_rate: int = 16000) -> Path:
    """Extract mono WAV from a video file using the bundled ffmpeg."""
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    out_wav.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [ffmpeg, "-y", "-i", str(video_path),
         "-vn", "-ac", "1", "-ar", str(sample_rate), "-f", "wav", str(out_wav)],
        check=True, capture_output=True,
    )
    return out_wav
