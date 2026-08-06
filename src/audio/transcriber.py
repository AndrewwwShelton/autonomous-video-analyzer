"""Speech-to-text (Module 1, stage 2).

Contract: a transcriber returns a list of WordStamp — one entry per spoken word,
with start/end times in seconds. The compliance matcher consumes exactly this shape,
so DemoTranscriber and FasterWhisperTranscriber are interchangeable.

Decision D3: faster-whisper over stock Whisper — 2-4x faster, lower memory, and native
word-level timestamps, which the AudioFlags schema requires.
"""
import random
from dataclasses import dataclass
from pathlib import Path

from src import config


@dataclass
class WordStamp:
    word: str
    start: float
    end: float


class TranscriptionError(RuntimeError):
    """Raised when audio cannot be transcribed, with a message fit for the UI."""


class FasterWhisperTranscriber:
    """Local speech-to-text via faster-whisper (CTranslate2 backend).

    Weights are cached under models/ so a given size is downloaded once. That first
    download needs a network connection; every transcription afterwards is fully
    offline, which is what the project's privacy requirement actually turns on.

    The model is loaded lazily and reused, so repeated calls on one instance do not
    reload several hundred megabytes of weights.
    """

    def __init__(self, model_size: str = "base.en", device: str = "auto",
                 compute_type: str = "int8"):
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self._model = None

    def _load(self):
        if self._model is None:
            try:
                from faster_whisper import WhisperModel
            except ImportError as e:  # pragma: no cover - environment guard
                raise TranscriptionError(
                    "faster-whisper is not installed. Run: pip install faster-whisper"
                ) from e
            config.MODELS_DIR.mkdir(parents=True, exist_ok=True)
            try:
                self._model = WhisperModel(
                    self.model_size,
                    device=self.device,
                    compute_type=self.compute_type,
                    download_root=str(config.MODELS_DIR),
                )
            except Exception as e:
                raise TranscriptionError(
                    f"Could not load the '{self.model_size}' model. If this is the first "
                    f"run the weights must be downloaded once, which needs a network "
                    f"connection. Underlying error: {e}"
                ) from e
        return self._model

    def transcribe(self, wav_path: Path) -> list[WordStamp]:
        """Transcribe a 16 kHz mono WAV into word-level stamps."""
        # Check the input before loading several hundred megabytes of weights.
        wav_path = Path(wav_path)
        if not wav_path.exists():
            raise TranscriptionError(f"Audio file not found: {wav_path}")

        model = self._load()
        try:
            segments, _info = model.transcribe(
                str(wav_path),
                word_timestamps=True,   # required — AudioFlags stores per-word times
                vad_filter=True,        # skip silence; avoids hallucinated text
            )
            words: list[WordStamp] = []
            for segment in segments:          # generator — consumed here
                for w in (segment.words or []):
                    text = w.word.strip()
                    if text:
                        words.append(WordStamp(text, round(w.start, 2), round(w.end, 2)))
            return words
        except TranscriptionError:
            raise
        except Exception as e:
            raise TranscriptionError(f"Transcription failed: {e}") from e

    @property
    def name(self) -> str:
        """Value recorded in AudioFlags.detection_model for provenance."""
        return f"faster-whisper-{self.model_size}"


class DemoTranscriber:
    """Generates a plausible word-timestamped transcript spread across the video duration.

    Deterministic per seed so repeated runs of the same video give identical results.
    Intentionally includes words from the default restricted dictionary so the
    compliance matcher (real code) produces flags for the UI to render.
    """

    # Two scripts, chosen by seed parity and paired with the overlay demo engine
    # (src/vision/overlay.py DemoOverlayFinder) which alternates on the same
    # parity. A single script made every demo video identical in outcome:
    # 'kill', 'gun' and 'weapon' are all High severity, so every library entry
    # came back Restricted and the interface's other verdict states could never
    # be shown. The pairing is deliberate -- commentary that reads as gameplay
    # goes with the seed that reports a heads-up display, so demo mode can
    # demonstrate the Review verdict rather than only describe it.
    _SCRIPTS = [
        # Even seeds: filmed studio footage, high-severity speech -> Restricted.
        ("studio",
         "welcome back everyone today we are reviewing the new studio setup and honestly "
         "it looks damn good the lighting rig nearly fell and I thought it would kill "
         "someone but we bolted it down there is no way in hell we ship this without "
         "testing the desk is empty right now which is perfect for sponsors we moved the "
         "prop weapon from the shelf because it kept showing up on camera and the fake "
         "gun goes back to the props department after this shoot anyway let us get into "
         "the benchmarks the numbers are crap on battery but plugged in it flies"),
        # Odd seeds: gameplay commentary. Mild language only, so the verdict turns
        # on the visual findings and the overlay context rather than on speech.
        ("gameplay",
         "alright we are dropping in at the north ridge again and honestly this loadout "
         "has been carrying me all week the storm is closing early so we need to rotate "
         "before it clips us damn that was close I thought we were done there the loot "
         "here is usually decent and the sight lines across the bridge are excellent if "
         "you hold the high ground keep an eye on the mini map because they are pushing "
         "from the east side and our shields are low right now this run has been crap "
         "for materials but the placement is looking really strong going into the end"),
    ]

    def __init__(self, seed: int = 0):
        self.seed = seed

    @property
    def _script(self) -> list[str]:
        return self._SCRIPTS[self.seed % len(self._SCRIPTS)][1].split()

    @property
    def name(self) -> str:
        return "demo-transcriber"

    def transcribe(self, duration_sec: float) -> list[WordStamp]:
        rng = random.Random(self.seed)
        words: list[WordStamp] = []
        script = self._script
        # Fill the duration by looping the script; ~2.5 words/sec with natural jitter.
        t = rng.uniform(0.5, 1.5)
        i = 0
        while t < duration_sec - 1.0:
            word = script[i % len(script)]
            length = 0.25 + rng.random() * 0.35
            words.append(WordStamp(word, round(t, 2), round(t + length, 2)))
            t += length + rng.uniform(0.05, 0.25)
            if rng.random() < 0.06:  # occasional pause between sentences
                t += rng.uniform(0.5, 1.8)
            i += 1
        return words
