"""Config (SystemConfig table) and report endpoints."""
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from src.db import repository as repo
from src.reports import exporter

router = APIRouter(tags=["system"])


@router.get("/stats")
def library_stats() -> dict:
    """Library-wide aggregates powering the Dashboard and Analytics screens."""
    return repo.get_library_stats()


@router.get("/vision-coverage")
def vision_coverage() -> dict:
    """What the configured detection weights can actually find.

    Surfaced in the interface so the tool never implies it is checking for
    something the loaded models cannot detect.
    """
    from src.vision.detector import coverage_report
    weights = repo.get_config("vision_weights") or ["yolov8n.pt"]
    return coverage_report(tuple(weights))


class ConfigPayload(BaseModel):
    profanity_dictionary: list[dict]
    frame_sample_fps: float
    min_ad_spot_duration_sec: float
    detection_confidence_threshold: float
    whisper_model: str
    analysis_mode: str = "demo"
    vision_weights: list[str] = ["yolov8n.pt"]


@router.get("/config")
def get_config() -> dict:
    return {
        "profanity_dictionary": repo.get_config("profanity_dictionary") or [],
        "frame_sample_fps": repo.get_config("frame_sample_fps") or 1.0,
        "min_ad_spot_duration_sec": repo.get_config("min_ad_spot_duration_sec") or 5.0,
        "detection_confidence_threshold": repo.get_config("detection_confidence_threshold") or 0.5,
        "whisper_model": repo.get_config("whisper_model") or "base.en",
        "analysis_mode": repo.get_config("analysis_mode") or "demo",
        "vision_weights": repo.get_config("vision_weights") or ["yolov8n.pt"],
    }


@router.put("/config")
def put_config(payload: ConfigPayload) -> dict:
    rules = [{"word": str(r.get("word", "")).strip(),
              "severity": r.get("severity") or "Medium"}
             for r in payload.profanity_dictionary if str(r.get("word", "")).strip()]
    repo.set_config("profanity_dictionary", rules, "json")
    repo.set_config("frame_sample_fps", payload.frame_sample_fps, "float")
    repo.set_config("min_ad_spot_duration_sec", payload.min_ad_spot_duration_sec, "float")
    repo.set_config("detection_confidence_threshold",
                    payload.detection_confidence_threshold, "float")
    repo.set_config("whisper_model", payload.whisper_model, "string")
    mode = payload.analysis_mode.lower()
    if mode not in ("demo", "real"):
        raise HTTPException(400, "analysis_mode must be 'demo' or 'real'")
    repo.set_config("analysis_mode", mode, "string")
    weights = [w.strip() for w in payload.vision_weights if w.strip()]
    repo.set_config("vision_weights", weights or ["yolov8n.pt"], "json")
    return get_config()


class ReportRequest(BaseModel):
    video_id: int
    format: str  # CSV | JSON


@router.get("/reports")
def list_reports(video_id: int | None = None) -> list[dict]:
    return repo.list_reports(video_id)


@router.post("/reports", status_code=201)
def create_report(req: ReportRequest) -> dict:
    fmt = req.format.upper()
    if fmt == "CSV":
        exporter.export_csv(req.video_id)
    elif fmt == "JSON":
        exporter.export_json(req.video_id)
    elif fmt == "PDF":
        exporter.export_pdf(req.video_id)
    else:
        raise HTTPException(400, f"Unknown format {req.format}")
    return repo.list_reports(req.video_id)[0]


@router.get("/reports/{report_id}/download")
def download_report(report_id: int):
    rows = [r for r in repo.list_reports() if r["report_id"] == report_id]
    if not rows:
        raise HTTPException(404, "report not found")
    path = Path(rows[0]["file_path"])
    if not path.exists():
        raise HTTPException(410, "report file no longer on disk")
    media = {".csv": "text/csv", ".json": "application/json",
             ".pdf": "application/pdf"}.get(path.suffix, "application/octet-stream")
    return FileResponse(path, media_type=media, filename=path.name)
