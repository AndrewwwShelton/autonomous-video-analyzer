"""FastAPI application — Module 4 backend.

Dev:   uvicorn backend.main:app --reload --port 8000   (frontend on Vite :5173)
Prod:  build the frontend (npm run build) and this app serves frontend/dist too.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from backend.routes import system, videos
from src import config
from src.db.connection import init_db

config.ensure_dirs()
init_db()

app = FastAPI(title="Ad-Placement & Safety Analyzer API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(videos.router, prefix="/api")
app.include_router(system.router, prefix="/api")

# Media: StaticFiles supports HTTP Range, which <video> needs for seeking.
THUMBS_DIR = config.DATA_DIR / "thumbs"
THUMBS_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/media/videos", StaticFiles(directory=config.VIDEO_DIR), name="videos")
app.mount("/media/thumbs", StaticFiles(directory=THUMBS_DIR), name="thumbs")

# Serve the built frontend when it exists (production mode); SPA fallback for
# client-side routes like /video/3.
DIST = ROOT / "frontend" / "dist"
if DIST.exists():
    app.mount("/assets", StaticFiles(directory=DIST / "assets"), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    def spa(full_path: str):
        candidate = DIST / full_path
        if full_path and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(DIST / "index.html")
