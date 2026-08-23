"""Uploads must not be able to write outside the video directory.

The handler interpolated the client-supplied filename straight into the
destination path. A crafted multipart request with filename
"a/../../../../evil.mp4" normalised to a path outside the repository, and the
extension check did not catch it because only the last component is inspected.

These tests upload a REAL video. An earlier version sent junk bytes, which made
every traversal test pass against the vulnerable code: ingestion rejected the
junk and the handler deleted the file it had just written, erasing the evidence
before the assertions ran. The escape has to survive for the test to see it.
"""
import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.main import app
from src import config

client = TestClient(app)

REAL_CLIP = Path(__file__).resolve().parents[1] / "benchmark" / "clips" / \
    "synthetic_speech_01.mp4"

TRAVERSAL_NAMES = [
    "a/../../../../evil.mp4",
    "../../evil.mp4",
    "..\\..\\evil.mp4",
    "dir/sub/../../../evil.mp4",
]


def _ancestors():
    here = Path(config.VIDEO_DIR).resolve()
    return [here, *here.parents[:4]]


def _cleanup(video_id):
    if video_id is not None:
        client.delete(f"/api/videos/{video_id}")


@pytest.mark.skipif(not REAL_CLIP.exists(), reason="sample clip not present")
@pytest.mark.parametrize("name", TRAVERSAL_NAMES)
def test_upload_cannot_escape_the_video_directory(name):
    payload = REAL_CLIP.read_bytes()
    video_id = None
    try:
        r = client.post("/api/videos",
                        files={"file": (name, payload, "video/mp4")})
        if r.status_code == 201:
            video_id = r.json()["video_id"]
            stored = Path(r.json()["filepath"]).resolve()
            assert Path(config.VIDEO_DIR).resolve() in stored.parents, (
                f"{name} stored at {stored}, outside the video directory")

        for ancestor in _ancestors():
            escaped = ancestor / "evil.mp4"
            assert not escaped.exists(), f"{name} escaped to {escaped}"
    finally:
        _cleanup(video_id)


def test_unsupported_extension_is_rejected():
    r = client.post("/api/videos",
                    files={"file": ("payload.exe", b"MZ",
                                    "application/octet-stream")})
    assert r.status_code == 400
    assert "Unsupported format" in r.json()["detail"]


@pytest.mark.skipif(not REAL_CLIP.exists(), reason="sample clip not present")
def test_directory_part_is_stripped_not_rejected():
    """A name inside a directory still uploads; only the path part is dropped."""
    video_id = None
    try:
        r = client.post("/api/videos",
                        files={"file": ("folder/clip.mp4",
                                        REAL_CLIP.read_bytes(), "video/mp4")})
        assert r.status_code == 201, r.text
        video_id = r.json()["video_id"]
        assert r.json()["filename"] == "clip.mp4"
        assert not list(Path(config.VIDEO_DIR).glob("*folder*"))
    finally:
        _cleanup(video_id)
