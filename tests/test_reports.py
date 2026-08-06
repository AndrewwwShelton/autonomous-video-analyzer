"""M5 tests — PDF report rendering.

build_pdf is exercised directly with synthetic data so these stay fast and never
touch the real database.
"""
import pytest

from src.reports.pdf_report import _fmt_time, _provenance, build_pdf


def sample(audio=None, visual=None, spots=None, verdict="Restricted") -> dict:
    return {
        "video": {"filename": "clip.mp4", "duration_sec": 40.0,
                  "resolution_width": 960, "resolution_height": 540},
        "audio_flags": audio if audio is not None else [
            {"timestamp_start": 8.0, "timestamp_end": 8.4, "word_flagged": "damn",
             "transcript_context": "it looks damn good", "severity": "Low",
             "detection_model": "faster-whisper-base.en"},
            {"timestamp_start": 15.0, "timestamp_end": 15.5, "word_flagged": "kill",
             "transcript_context": "would kill someone", "severity": "High",
             "detection_model": "faster-whisper-base.en"},
        ],
        "visual_flags": visual if visual is not None else [
            {"frame_timestamp": 7.0, "object_detected": "knife",
             "bounding_box_json": "[1, 2, 3, 4]", "confidence_score": 0.83,
             "risk_category": "Weapon"},
        ],
        "ad_spots": spots if spots is not None else [
            {"timestamp_start": 4.0, "timestamp_end": 16.0, "spot_type": "blank_wall",
             "bounding_box_json": "[5, 6, 7, 8]", "area_pixels": 1000,
             "suitability_score": 0.38},
        ],
        "compliance_status": verdict,
    }


def read(path) -> bytes:
    return path.read_bytes()


# ----------------------------------------------------------------- helpers

def test_time_formatting():
    assert _fmt_time(0) == "0:00"
    assert _fmt_time(8.4) == "0:08"
    assert _fmt_time(75) == "1:15"
    assert _fmt_time(None) == "0:00"


def test_provenance_names_the_engine():
    text = _provenance(sample())
    assert "faster-whisper-base.en" in text


def test_provenance_warns_loudly_about_demo_output():
    """A demo-generated report must say so — it is not an audit result."""
    data = sample(audio=[{"timestamp_start": 1.0, "timestamp_end": 1.2,
                          "word_flagged": "damn", "transcript_context": "x",
                          "severity": "Low", "detection_model": "demo-transcriber"}])
    text = _provenance(data)
    assert "demonstration stand-ins" in text
    assert "<b>" in text          # emphasised, not buried in prose


def test_provenance_handles_no_speech_findings():
    assert "no transcription engine" in _provenance(sample(audio=[]))


# ------------------------------------------------------------------- render

def test_writes_a_valid_pdf(tmp_path):
    out = tmp_path / "r.pdf"
    build_pdf(sample(), out)
    assert out.exists()
    assert read(out).startswith(b"%PDF")
    assert out.stat().st_size > 1500


def test_findings_appear_in_the_document(tmp_path):
    """Content must actually reach the page, not just the data structure."""
    pytest.importorskip("fitz", reason="pymupdf not installed in this environment")
    import fitz
    out = tmp_path / "r.pdf"
    build_pdf(sample(), out)
    text = "\n".join(page.get_text() for page in fitz.open(out))
    for expected in ("clip.mp4", "Restricted", "damn", "kill", "knife",
                     "blank wall", "Provenance"):
        assert expected in text, f"missing from rendered PDF: {expected}"


def test_monetizable_verdict_renders(tmp_path):
    out = tmp_path / "clean.pdf"
    build_pdf(sample(audio=[], visual=[], verdict="Monetizable"), out)
    assert read(out).startswith(b"%PDF")


def test_empty_report_does_not_crash(tmp_path):
    """A video with no findings at all is a normal outcome, not an error."""
    out = tmp_path / "empty.pdf"
    build_pdf(sample(audio=[], visual=[], spots=[], verdict="Monetizable"), out)
    assert read(out).startswith(b"%PDF")


def test_zero_duration_video_does_not_divide_by_zero(tmp_path):
    data = sample()
    data["video"]["duration_sec"] = 0
    out = tmp_path / "zero.pdf"
    build_pdf(data, out)
    assert read(out).startswith(b"%PDF")


def test_missing_optional_fields_are_tolerated(tmp_path):
    """Older rows may lack severity, category or score."""
    data = sample(
        audio=[{"timestamp_start": 1.0, "timestamp_end": 1.4, "word_flagged": "x",
                "transcript_context": None, "severity": None, "detection_model": None}],
        visual=[{"frame_timestamp": 2.0, "object_detected": "y",
                 "bounding_box_json": None, "confidence_score": 0.5,
                 "risk_category": None}],
        spots=[{"timestamp_start": 1.0, "timestamp_end": 9.0, "spot_type": None,
                "bounding_box_json": None, "area_pixels": 0,
                "suitability_score": None}],
    )
    out = tmp_path / "sparse.pdf"
    build_pdf(data, out)
    assert read(out).startswith(b"%PDF")


def test_many_findings_paginate(tmp_path):
    """Long reports must flow onto further pages rather than overflow one."""
    pytest.importorskip("fitz", reason="pymupdf not installed in this environment")
    import fitz
    audio = [{"timestamp_start": i, "timestamp_end": i + 0.4, "word_flagged": f"w{i}",
              "transcript_context": "some surrounding transcript text " * 2,
              "severity": "Low", "detection_model": "faster-whisper-base.en"}
             for i in range(60)]
    out = tmp_path / "long.pdf"
    build_pdf(sample(audio=audio), out)
    assert fitz.open(out).page_count > 1


# ------------------------------------------------- three-state verdict (M6)

@pytest.mark.parametrize("verdict", ["Monetizable", "Review", "Restricted"])
def test_every_verdict_state_renders(tmp_path, verdict):
    """'Review' was added after the first release; an unhandled state previously
    fell through to the Restricted styling and mislabelled the report."""
    out = tmp_path / f"{verdict}.pdf"
    build_pdf(sample(verdict=verdict), out)
    assert out.exists() and out.stat().st_size > 1000


def test_verdict_reason_is_printed_in_the_report(tmp_path):
    """A PDF is read away from the interface, so it must carry its own reasoning."""
    pypdf = pytest.importorskip("pypdf")

    data = sample(verdict="Review")
    data["compliance_reason"] = "UNIQUEMARKERPHRASE weapons appear to be rendered"
    out = tmp_path / "review.pdf"
    build_pdf(data, out)

    text = "".join(page.extract_text() or ""
                   for page in pypdf.PdfReader(str(out)).pages)
    assert "UNIQUEMARKERPHRASE" in text
    assert "Review" in text
