"""Speech-to-text (Module 1, stage 2).

Contract: a transcriber returns a list of WordStamp — one entry per spoken word,
with start/end times in seconds. The compliance matcher consumes exactly this shape,
so swapping DemoTranscriber for FasterWhisperTranscriber at M1 changes nothing else.
"""
import random
from dataclasses import dataclass
from pathlib import Path


@dataclass
class WordStamp:
    word: str
    start: float
    end: float


class FasterWhisperTranscriber:
    """Real engine — lands in M1. Kept as a documented shell so the contract is visible.

    Implementation sketch (decision D3, PLAN.md):
        from faster_whisper import WhisperModel
        model = WhisperModel(model_size, device="auto", compute_type="int8")
        segments, _ = model.transcribe(str(wav_path), word_timestamps=True)
        return [WordStamp(w.word.strip(), w.start, w.end)
                for seg in segments for w in seg.words]
    """

    def __init__(self, model_size: str = "base.en"):
        self.model_size = model_size

    def transcribe(self, wav_path: Path) -> list[WordStamp]:
        raise NotImplementedError(
            "FasterWhisperTranscriber lands in M1 — `pip install faster-whisper` and "
            "implement per the class docstring. Until then run the pipeline in demo mode."
        )


class DemoTranscriber:
    """Generates a plausible word-timestamped transcript spread across the video duration.

    Deterministic per seed so repeated runs of the same video give identical results.
    Intentionally includes words from the default restricted dictionary so the
    compliance matcher (real code) produces flags for the UI to render.
    """

    _SCRIPT = (
        "welcome back everyone today we are reviewing the new studio setup and honestly "
        "it looks damn good the lighting rig nearly fell and I thought it would kill "
        "someone but we bolted it down there is no way in hell we ship this without "
        "testing the desk is empty right now which is perfect for sponsors we moved the "
        "prop weapon from the shelf because it kept showing up on camera and the fake "
        "gun goes back to the props department after this shoot anyway let us get into "
        "the benchmarks the numbers are crap on battery but plugged in it flies"
    ).split()

    def __init__(self, seed: int = 0):
        self.seed = seed

    def transcribe(self, duration_sec: float) -> list[WordStamp]:
        rng = random.Random(self.seed)
        words: list[WordStamp] = []
        # Fill the duration by looping the script; ~2.5 words/sec with natural jitter.
        t = rng.uniform(0.5, 1.5)
        i = 0
        while t < duration_sec - 1.0:
            word = self._SCRIPT[i % len(self._SCRIPT)]
            length = 0.25 + rng.random() * 0.35
            words.append(WordStamp(word, round(t, 2), round(t + length, 2)))
            t += length + rng.uniform(0.05, 0.25)
            if rng.random() < 0.06:  # occasional pause between sentences
                t += rng.uniform(0.5, 1.8)
            i += 1
        return words
