"""API smoke tests — does the application actually start, and do its routes work?

These exist because of a real gap. A missing import in `backend/routes/system.py`
left the whole application unable to start, and the full suite passed anyway:
nothing imported the FastAPI app, so no test could have caught it. Every other
test here exercises `src/` directly.

Kept deliberately shallow. The point is to fail on "the server will not come up"
and on obvious contract breaks, not to re-test logic covered elsewhere.
"""
import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402


@pytest.fixture(scope="module")
def client(tmp_path_factory):
    """A client backed by a scratch database, so the real library is untouched."""
    from src import config
    from src.db.connection import init_db

    original = config.DB_PATH
    config.DB_PATH = tmp_path_factory.mktemp("api") / "smoke.db"
    init_db(config.DB_PATH)
    try:
        from backend.main import app          # import AFTER the path is swapped
        yield TestClient(app)
    finally:
        config.DB_PATH = original


def test_the_application_imports_and_starts(client):
    """The regression: a NameError at import time takes the server down entirely."""
    assert client.get("/api/stats").status_code == 200


def test_config_round_trips(client):
    original = client.get("/api/config")
    assert original.status_code == 200
    cfg = original.json()

    for key in ("profanity_dictionary", "frame_sample_fps", "whisper_model",
                "analysis_mode", "vision_weights", "detection_max_imgsz"):
        assert key in cfg, f"{key} missing from GET /config"

    cfg["detection_max_imgsz"] = 1600
    saved = client.put("/api/config", json=cfg)
    assert saved.status_code == 200
    assert saved.json()["detection_max_imgsz"] == 1600


@pytest.mark.parametrize("sent,expected", [
    (5000, 3840),   # clamped to the ceiling
    (100, 640),     # raised to the floor
    (999, 992),     # aligned to the model stride
])
def test_detection_resolution_is_clamped_and_stride_aligned(client, sent, expected):
    """A typo here would otherwise make every analysis silently slow or blind."""
    cfg = client.get("/api/config").json()
    cfg["detection_max_imgsz"] = sent
    assert client.put("/api/config", json=cfg).json()["detection_max_imgsz"] == expected


def test_unknown_analysis_mode_is_rejected(client):
    cfg = client.get("/api/config").json()
    cfg["analysis_mode"] = "turbo"
    assert client.put("/api/config", json=cfg).status_code == 400


def test_missing_video_returns_404(client):
    assert client.get("/api/videos/99999").status_code == 404
    assert client.get("/api/videos/99999/flags").status_code == 404


def test_unsupported_upload_format_is_rejected(client):
    resp = client.post("/api/videos",
                       files={"file": ("notes.txt", b"not a video", "text/plain")})
    assert resp.status_code == 400
    assert "MP4" in resp.json()["detail"]


def test_vision_coverage_reports_without_crashing(client):
    """Reports what the loaded weights can detect. Must degrade rather than raise
    when the weights are absent, since it is read on the Settings page."""
    body = client.get("/api/vision-coverage").json()
    assert "by_category" in body and "loaded" in body
