"""Compliance report export (Module 4 / SRS Use Case 2).

CSV, JSON and PDF. Every export is archived as an AuditReports row per the DDD.
Rendering for the PDF lives in pdf_report.py — this module assembles data, that one
presents it.
"""
import json
from datetime import datetime
from pathlib import Path

import pandas as pd

from src import config
from src.db import repository as repo
from src.pipeline.orchestrator import compliance_verdict


def _gather(video_id: int) -> dict:
    video = repo.get_video(video_id)
    if video is None:
        raise ValueError(f"No video with id {video_id}")
    return {
        "video": video,
        "audio_flags": repo.get_audio_flags(video_id),
        "visual_flags": repo.get_visual_flags(video_id),
        "ad_spots": repo.get_ad_spots(video_id),
        "compliance_status": compliance_verdict(video_id),
    }


def _archive(video_id: int, report_type: str, out_path: Path, data: dict) -> None:
    repo.insert_report(
        video_id, report_type, str(out_path),
        totals={"audio": len(data["audio_flags"]), "visual": len(data["visual_flags"]),
                "ad_spots": len(data["ad_spots"])},
        compliance_status=data["compliance_status"],
    )


def export_csv(video_id: int) -> Path:
    """Single CSV: all flags/spots unioned, distinguished by a record_type column."""
    data = _gather(video_id)
    rows = []
    for f in data["audio_flags"]:
        rows.append({"record_type": "audio_flag", "timestamp_start": f["timestamp_start"],
                     "timestamp_end": f["timestamp_end"], "label": f["word_flagged"],
                     "severity_or_category": f["severity"], "detail": f["transcript_context"],
                     "confidence": None})
    for f in data["visual_flags"]:
        rows.append({"record_type": "visual_flag", "timestamp_start": f["frame_timestamp"],
                     "timestamp_end": f["frame_timestamp"], "label": f["object_detected"],
                     "severity_or_category": f["risk_category"], "detail": f["bounding_box_json"],
                     "confidence": f["confidence_score"]})
    for s in data["ad_spots"]:
        rows.append({"record_type": "ad_spot", "timestamp_start": s["timestamp_start"],
                     "timestamp_end": s["timestamp_end"], "label": s["spot_type"],
                     "severity_or_category": None, "detail": s["bounding_box_json"],
                     "confidence": s["suitability_score"]})

    config.ensure_dirs()
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = config.REPORTS_DIR / f"audit_video{video_id}_{stamp}.csv"
    df = pd.DataFrame(rows).sort_values("timestamp_start") if rows else pd.DataFrame(rows)
    df.to_csv(out, index=False)
    _archive(video_id, "CSV", out, data)
    return out


def export_json(video_id: int) -> Path:
    data = _gather(video_id)
    config.ensure_dirs()
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = config.REPORTS_DIR / f"audit_video{video_id}_{stamp}.json"
    out.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
    _archive(video_id, "JSON", out, data)
    return out


def export_pdf(video_id: int) -> Path:
    """Formatted compliance report — the format an auditor actually sends on."""
    from src.reports.pdf_report import build_pdf

    data = _gather(video_id)
    config.ensure_dirs()
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = config.REPORTS_DIR / f"audit_video{video_id}_{stamp}.pdf"
    build_pdf(data, out)
    _archive(video_id, "PDF", out, data)
    return out
