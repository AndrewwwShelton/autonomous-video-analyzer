"""Generate a synthetic labelled clip for validating the harness itself.

    python benchmark/make_synthetic_clip.py

Each phrase is synthesised to its own WAV, so the exact start and end of every
phrase is known from measured audio durations -- ground truth that is derived from
the text-to-speech engine, never from Whisper. Grading a model against its own
output would be circular and worthless.

IMPORTANT -- what this is and is not:

  IS  : a way to prove the harness end-to-end, and a clean-speech floor for the
        audio engine.
  NOT : evidence for the SRS accuracy claim. Text-to-speech is pristine studio
        diction with no music, noise, accents, or overlapping speakers. Real
        creator audio is far harder, and a precision figure measured here would
        be optimistic. The headline number must come from real clips.

Windows only (uses System.Speech). On other platforms, label real clips by hand.
"""
import json
import shutil
import subprocess
import sys
import tempfile
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import imageio_ffmpeg                      # noqa: E402
from src import config                     # noqa: E402
from src.demo_media import generate_demo_video  # noqa: E402

CLIPS_DIR = ROOT / "benchmark" / "clips"
LABELS_DIR = ROOT / "benchmark" / "labels"
CLIP_NAME = "synthetic_speech_01.mp4"

# (spoken phrase, dictionary word it contains or None). Phrases stay short so the
# midpoint estimate sits comfortably inside the matcher's tolerance.
PHRASES = [
    ("Welcome back to the studio review.", None),
    ("Honestly, this new lighting rig looks damn good.", "damn"),
    ("The mounting bracket nearly fell on someone.", None),
    ("There is no way in hell we are shipping this today.", "hell"),
    ("Please move the prop gun off the desk.", "gun"),
    ("The battery numbers are absolute crap right now.", "crap"),
    ("That is everything for this session, thanks for watching.", None),
]
GAP_SEC = 0.45


def _synthesise(phrases: list[str], out_dir: Path) -> list[Path]:
    """Speak each phrase to its own WAV via Windows SAPI."""
    lines = [
        "Add-Type -AssemblyName System.Speech",
        "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer",
        "$s.Rate = -1",
    ]
    paths = []
    for i, text in enumerate(phrases):
        p = out_dir / f"phrase_{i:02d}.wav"
        paths.append(p)
        safe = text.replace("'", "''")
        lines.append(f"$s.SetOutputToWaveFile('{p}')")
        lines.append(f"$s.Speak('{safe}')")
    lines.append("$s.Dispose()")

    script = out_dir / "speak.ps1"
    script.write_text("\n".join(lines), encoding="utf-8")
    proc = subprocess.run(
        ["powershell.exe", "-NoProfile", "-NonInteractive",
         "-ExecutionPolicy", "Bypass", "-File", str(script)],
        capture_output=True, text=True,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"Speech synthesis failed:\n{proc.stderr}")
    missing = [p.name for p in paths if not p.exists()]
    if missing:
        raise RuntimeError(f"Speech synthesis produced no audio for: {missing}")
    return paths


def _wav_duration(path: Path) -> float:
    with wave.open(str(path), "rb") as w:
        return w.getnframes() / float(w.getframerate())


def _concat_wavs(paths: list[Path], gap_sec: float, out: Path) -> list[tuple[float, float]]:
    """Join WAVs with silence between them. Returns each phrase's (start, end)."""
    with wave.open(str(paths[0]), "rb") as first:
        params = first.getparams()
    silence = b"\x00" * int(params.framerate * gap_sec) * params.sampwidth * params.nchannels

    spans, cursor = [], 0.0
    with wave.open(str(out), "wb") as w:
        w.setparams(params)
        for i, p in enumerate(paths):
            with wave.open(str(p), "rb") as src:
                frames = src.readframes(src.getnframes())
            dur = _wav_duration(p)
            spans.append((round(cursor, 3), round(cursor + dur, 3)))
            w.writeframes(frames)
            cursor += dur
            if i < len(paths) - 1:
                w.writeframes(silence)
                cursor += gap_sec
    return spans


def main() -> int:
    if sys.platform != "win32":
        print("This generator needs Windows text-to-speech. Label real clips by hand "
              "instead -- see benchmark/README.md.")
        return 1

    CLIPS_DIR.mkdir(parents=True, exist_ok=True)
    LABELS_DIR.mkdir(parents=True, exist_ok=True)
    config.ensure_dirs()

    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        print("synthesising speech ...")
        wavs = _synthesise([t for t, _ in PHRASES], tmp_dir)

        joined = tmp_dir / "joined.wav"
        spans = _concat_wavs(wavs, GAP_SEC, joined)
        total = spans[-1][1]
        print(f"speech track: {total:.1f}s across {len(spans)} phrases")

        print("rendering video ...")
        silent_video = generate_demo_video(duration_sec=int(total) + 2)

        clip = CLIPS_DIR / CLIP_NAME
        ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
        subprocess.run(
            [ffmpeg, "-y", "-i", str(silent_video), "-i", str(joined),
             "-c:v", "copy", "-c:a", "aac", "-shortest", str(clip)],
            check=True, capture_output=True,
        )

    # Ground truth: the midpoint of the phrase containing each target word. Derived
    # from measured phrase durations, so it is independent of the ASR under test.
    audio_truth = []
    for (text, word), (start, end) in zip(PHRASES, spans):
        if word:
            audio_truth.append({
                "word": word,
                "at": round((start + end) / 2, 2),
                "phrase": text,
                "phrase_span": [start, end],
            })

    label = {
        "clip": CLIP_NAME,
        "source": "synthetic -- generated by benchmark/make_synthetic_clip.py",
        "notes": ("Clean text-to-speech. Validates the harness and gives a best-case "
                  "floor for the audio engine. NOT evidence for the accuracy claim -- "
                  "that requires real clips."),
        "synthetic": True,
        "audio": audio_truth,
        "visual": [],
        "ad_spots": [],
    }
    label_path = LABELS_DIR / "synthetic_speech_01.json"
    label_path.write_text(json.dumps(label, indent=2), encoding="utf-8")

    print(f"\nclip  : {clip.relative_to(ROOT)}")
    print(f"label : {label_path.relative_to(ROOT)}  ({len(audio_truth)} audio events)")
    for e in audio_truth:
        print(f"          {e['at']:6.2f}s  {e['word']}")
    print("\nnow run:  python benchmark/evaluate.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
