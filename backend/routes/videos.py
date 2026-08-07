"""Video endpoints: ingest, list, analyze (background), status, flags, delete."""
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, HTTPException, UploadFile

from backend import progress
from src import config
from src.db import repository as repo
from src.demo_media import generate_demo_video
from src.pipeline.orchestrator import (assess_compliance, compliance_verdict,
                                       process_video)
from src.vision.detector import display_label
from src.vision.sampler import probe_video, save_thumbnail

router = APIRouter(tags=["videos"])

THUMBS_DIR = config.DATA_DIR / "thumbs"


def _thumb_name(video_id: int) -> str:
    return f"video_{video_id}.jpg"


def _enrich(v: dict) -> dict:
    """Attach per-video aggregates the Content table renders."""
    vid = v["video_id"]
    out = dict(v)
    out["thumbnail_url"] = (
        f"/media/thumbs/{_thumb_name(vid)}" if (THUMBS_DIR / _thumb_name(vid)).exists() else None
    )
    out["video_url"] = f"/media/videos/{Path(v['filepath']).name}"
    if v["processed_status"] == "completed":
        out["counts"] = {
            "audio": len(repo.get_audio_flags(vid)),
            "visual": len(repo.get_visual_flags(vid)),
            "ad_spots": len(repo.get_ad_spots(vid)),
        }
        out["verdict"] = compliance_verdict(vid)
    else:
        out["counts"] = None
        out["verdict"] = None
    return out


def _ingest_file(dest: Path, original_name: str) -> dict:
    meta = probe_video(dest)  # raises ValueError on unreadable files
    video_id = repo.insert_video(
        filename=original_name, filepath=str(dest),
        file_size_mb=round(dest.stat().st_size / 1_048_576, 2),
        duration_sec=meta["duration_sec"], fps=meta["fps"],
        width=meta["width"], height=meta["height"],
    )
    save_thumbnail(dest, THUMBS_DIR / _thumb_name(video_id))
    return _enrich(repo.get_video(video_id))


@router.get("/videos")
def list_videos() -> list[dict]:
    return [_enrich(v) for v in repo.list_videos()]


@router.get("/videos/{video_id}")
def get_video(video_id: int) -> dict:
    v = repo.get_video(video_id)
    if v is None:
        raise HTTPException(404, "video not found")
    return _enrich(v)


@router.post("/videos", status_code=201)
async def upload_video(file: UploadFile) -> dict:
    suffix = Path(file.filename or "upload.mp4").suffix.lower()
    if suffix not in config.SUPPORTED_EXTENSIONS:
        raise HTTPException(400, f"Unsupported format {suffix} — use MP4, MOV or AVI.")
    config.ensure_dirs()
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = config.VIDEO_DIR / f"{stamp}_{file.filename}"
    with dest.open("wb") as out:
        while chunk := await file.read(1 << 20):
            out.write(chunk)
    try:
        return _ingest_file(dest, file.filename)
    except ValueError as e:
        dest.unlink(missing_ok=True)
        raise HTTPException(400, str(e))


@router.post("/videos/demo", status_code=201)
def create_demo_video() -> dict:
    path = generate_demo_video()
    return _ingest_file(path, path.name)


@router.delete("/videos/{video_id}", status_code=204)
def delete_video(video_id: int) -> None:
    v = repo.get_video(video_id)
    if v is None:
        raise HTTPException(404, "video not found")
    repo.delete_video(video_id)  # cascades to flags/spots/reports
    Path(v["filepath"]).unlink(missing_ok=True)
    (THUMBS_DIR / _thumb_name(video_id)).unlink(missing_ok=True)
    progress.clear(video_id)


@router.post("/videos/{video_id}/analyze", status_code=202)
def analyze(video_id: int, tasks: BackgroundTasks, mode: str | None = None) -> dict:
    """Queue analysis. `mode` overrides the stored analysis_mode for this run only."""
    v = repo.get_video(video_id)
    if v is None:
        raise HTTPException(404, "video not found")
    if v["processed_status"] == "processing":
        raise HTTPException(409, "analysis already running")

    resolved = (mode or repo.get_config("analysis_mode") or "demo").lower()
    if resolved not in ("demo", "real"):
        raise HTTPException(400, f"Unknown analysis mode '{resolved}' — use 'demo' or 'real'.")

    progress.update(video_id, "Queued", 0.0)
    tasks.add_task(process_video, video_id, resolved == "demo",
                   lambda stage, frac: progress.update(video_id, stage, frac))
    return {"video_id": video_id, "status": "processing", "mode": resolved}


@router.get("/videos/{video_id}/status")
def status(video_id: int) -> dict:
    v = repo.get_video(video_id)
    if v is None:
        raise HTTPException(404, "video not found")
    return {"video_id": video_id, "status": v["processed_status"],
            **(progress.get(video_id) or {})}


@router.get("/videos/{video_id}/flags")
def flags(video_id: int) -> dict:
    v = repo.get_video(video_id)
    if v is None:
        raise HTTPException(404, "video not found")
    done = v["processed_status"] == "completed"
    # The full assessment, not just the label: a verdict the interface cannot
    # explain is no more accountable than the binary rule it replaced.
    assessment = assess_compliance(video_id) if done else None
    return {
        "audio": repo.get_audio_flags(video_id),
        # display_label is derived on read, not stored, so findings recorded
        # before the wording existed are presented the same way as new ones.
        "visual": [{**f, "display_label": display_label(f["object_detected"])}
                   for f in repo.get_visual_flags(video_id)],
        "ad_spots": repo.get_ad_spots(video_id),
        "verdict": assessment["verdict"] if assessment else None,
        "assessment": assessment,
    }
