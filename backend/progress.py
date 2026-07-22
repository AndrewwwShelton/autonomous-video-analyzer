"""In-memory progress registry for pipeline runs.

The orchestrator's progress callback writes here; GET /api/videos/{id}/status reads
it. Process-local by design — this is a single-user desktop tool (NFR: offline).
"""
import threading

_lock = threading.Lock()
_progress: dict[int, dict] = {}


def update(video_id: int, stage: str, fraction: float) -> None:
    with _lock:
        _progress[video_id] = {"stage": stage, "progress": round(fraction, 3)}


def get(video_id: int) -> dict | None:
    with _lock:
        return _progress.get(video_id)


def clear(video_id: int) -> None:
    with _lock:
        _progress.pop(video_id, None)
