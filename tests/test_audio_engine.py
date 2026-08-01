"""M1 tests — the real audio path, without requiring model weights.

Transcription itself is exercised by an integration check against a generated speech
clip (see ROADMAP M1); these tests cover the surrounding contract, which is where
regressions actually hide.
"""
from pathlib import Path

import pytest

from src.audio.transcriber import (DemoTranscriber, FasterWhisperTranscriber,
                                   TranscriptionError, WordStamp)
from src.db import repository as repo
from src.db.connection import init_db


@pytest.fixture()
def db(tmp_path):
    path = tmp_path / "test.db"
    init_db(path)
    return path


def test_both_transcribers_share_the_wordstamp_contract():
    """Demo and real engines must be drop-in replaceable for the matcher."""
    demo = DemoTranscriber(seed=1)
    words = demo.transcribe(20.0)
    assert words and all(isinstance(w, WordStamp) for w in words)
    assert all(w.end >= w.start for w in words)
    # Stamps advance monotonically — the timeline depends on it.
    assert all(b.start >= a.start for a, b in zip(words, words[1:]))


def test_engine_names_are_recorded_for_provenance():
    """detection_model must identify which engine produced a flag."""
    assert DemoTranscriber().name == "demo-transcriber"
    assert FasterWhisperTranscriber("base.en").name == "faster-whisper-base.en"
    assert FasterWhisperTranscriber("small.en").name == "faster-whisper-small.en"


def test_missing_audio_file_raises_transcription_error():
    tr = FasterWhisperTranscriber("base.en")
    with pytest.raises(TranscriptionError):
        tr.transcribe(Path("does_not_exist_anywhere.wav"))


def test_model_is_loaded_lazily():
    """Constructing must not pull hundreds of megabytes of weights."""
    tr = FasterWhisperTranscriber("base.en")
    assert tr._model is None


def test_analysis_mode_defaults_to_demo(db):
    """Demo is the safe default so a fresh install runs with no weights present."""
    assert repo.get_config("analysis_mode", db_path=db) == "demo"


def test_analysis_mode_is_persisted(db):
    repo.set_config("analysis_mode", "real", "string", db_path=db)
    assert repo.get_config("analysis_mode", db_path=db) == "real"


def test_whisper_model_setting_drives_engine_name(db):
    """The Settings value must reach the engine, not just sit in the database."""
    repo.set_config("whisper_model", "small.en", "string", db_path=db)
    size = repo.get_config("whisper_model", db_path=db)
    assert FasterWhisperTranscriber(size).name == "faster-whisper-small.en"
