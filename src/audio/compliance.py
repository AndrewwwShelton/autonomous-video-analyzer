"""Keyword/dictionary compliance matcher (Module 1, stage 3) — REAL code, model-free.

Matches the word-timestamped transcript against the restricted-keyword dictionary
stored in SystemConfig. Produces AudioFlags-shaped dicts ready for the repository.

Design notes:
- Tokens are normalised (lowercase, punctuation stripped) before comparison, and rules
  match whole tokens only — "hell" must not fire inside "hello" (the Scunthorpe problem).
- Multi-word phrases are supported by matching consecutive tokens.
- transcript_context captures ±5 surrounding words for the reviewer.
"""
import re
from src.audio.transcriber import WordStamp

_NORMALISE = re.compile(r"[^a-z0-9']+")

CONTEXT_WINDOW = 5  # words on each side


def _norm(token: str) -> str:
    return _NORMALISE.sub("", token.lower())


def match_transcript(words: list[WordStamp], dictionary: list[dict],
                     detection_model: str = "demo") -> list[dict]:
    """dictionary: [{"word": "damn", "severity": "Low"}, ...] — phrases allowed."""
    tokens = [_norm(w.word) for w in words]
    rules = []
    for entry in dictionary:
        phrase = [_norm(p) for p in entry["word"].split()]
        if phrase and all(phrase):
            rules.append((phrase, entry["word"], entry.get("severity", "Medium")))

    flags: list[dict] = []
    for i in range(len(tokens)):
        for phrase, original, severity in rules:
            n = len(phrase)
            if tokens[i:i + n] == phrase:
                ctx_start = max(0, i - CONTEXT_WINDOW)
                ctx_end = min(len(words), i + n + CONTEXT_WINDOW)
                flags.append({
                    "timestamp_start": words[i].start,
                    "timestamp_end": words[i + n - 1].end,
                    "word_flagged": original,
                    "transcript_context": " ".join(w.word for w in words[ctx_start:ctx_end]),
                    "severity": severity,
                    "detection_model": detection_model,
                })
    flags.sort(key=lambda f: f["timestamp_start"])
    return flags
