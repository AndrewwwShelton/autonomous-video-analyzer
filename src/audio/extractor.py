"""Audio extraction (Module 1, stage 1). Fully functional — no system ffmpeg needed.

Extracts the audio track to 16 kHz mono WAV — the input format Whisper expects.
Uses the ffmpeg binary bundled with imageio-ffmpeg, so there is no PATH dependency
(see PLAN.md §2.1 note on skipping MoviePy).
"""
import subprocess
from pathlib import Path

import imageio_ffmpeg


class NoAudioTrackError(RuntimeError):
    """The source file carries no decodable audio stream."""


def has_audio_stream(video_path: Path) -> bool:
    """True if ffmpeg reports at least one audio stream.

    ffmpeg writes its stream summary to stderr and exits non-zero when asked to run
    without an output, so we inspect the text rather than the return code.
    """
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    proc = subprocess.run(
        [ffmpeg, "-hide_banner", "-i", str(video_path)],
        capture_output=True, text=True, errors="replace",
    )
    return "Stream #" in proc.stderr and "Audio:" in proc.stderr


def extract_audio(video_path: Path, out_wav: Path, sample_rate: int = 16000) -> Path:
    """Extract mono WAV from a video file using the bundled ffmpeg.

    Raises NoAudioTrackError when the file is silent — a real case, since footage
    captured without a microphone (and our synthetic demo clip) has no audio stream.
    """
    if not has_audio_stream(video_path):
        raise NoAudioTrackError(
            f"'{video_path.name}' contains no audio track, so there is nothing to "
            f"transcribe. Visual analysis is unaffected."
        )

    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    out_wav.parent.mkdir(parents=True, exist_ok=True)
    proc = subprocess.run(
        [ffmpeg, "-y", "-i", str(video_path),
         "-vn", "-ac", "1", "-ar", str(sample_rate), "-f", "wav", str(out_wav)],
        capture_output=True, text=True, errors="replace",
    )
    if proc.returncode != 0 or not out_wav.exists():
        raise RuntimeError(
            f"Audio extraction failed for '{video_path.name}'. "
            f"ffmpeg said: {proc.stderr.strip().splitlines()[-1] if proc.stderr else 'unknown error'}"
        )
    return out_wav
