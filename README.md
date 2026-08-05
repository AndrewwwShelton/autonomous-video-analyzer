# Autonomous Video Ad-Placement & Contextual Safety Analyzer

Offline desktop tool that audits long-form video for brand-safety risks (restricted
speech, visual hazards) and finds premium ad-placement surfaces — entirely on local
hardware. Specialization Project BCA482-5, CHRIST (Deemed to be University).

**Design docs:** `Synopsis.pdf` · `SRS (1).pdf` · `DDD_Final.pdf` · `PLAN.md` (implementation plan) · `Project_Justification.docx`

## Stack

- **Backend** — FastAPI + SQLite (WAL), serving a REST API plus video/thumbnail media
  with HTTP range support. AI pipeline in plain Python modules under `src/`.
- **Frontend** — React + Vite, styled after YouTube Studio (Roboto, Material Symbols,
  the Content-table layout, monetization `$` badges).

## Running the demo (for the review)

Use **one** server, not two — fewer moving parts on the day.

```bash
python demo_setup.py     # once, beforehand: seeds a clean library
```
Then **double-click `RUN_DEMO.bat`**. It builds the interface if needed, starts the
server on http://localhost:8000 and opens the browser. Leave the window open.

`demo_setup.py` leaves the library with two videos:
- `brand_review_final.mp4` — already analysed, so nothing is empty on screen
- `studio_review_cut.mp4` — **not** analysed, so you can run checks live

Stop the server before re-running `demo_setup.py` — it can't delete a database that
is still open.

### Showing the *real* engines

Both seeded videos are synthetic footage: no speech track, no real objects. They
exercise the whole pipeline, but in **real** mode they correctly find nothing, which
looks broken on a projector. To demonstrate real inference:

1. Set **Settings → Analysis mode → real**.
2. Upload `benchmark/clips/synthetic_speech_01.mp4` with the **Create** button.
3. Run checks on it from the row's action menu.

Measured on this machine (CPU only): **~31 s for a 28 s clip**, real Whisper
recovering all four restricted words with correct timestamps and context, verdict
`Restricted`. Vision alone runs ~2.2 frames/s, so plan roughly the clip's own
duration as wall-clock time.

Manual equivalent, if the batch file misbehaves:

```bash
npm run build --prefix frontend
python -m uvicorn backend.main:app --port 8000
```

## Quick start (development)

```bash
# 1. Backend deps (once)
pip install -r requirements.txt

# 2. Frontend deps (once)
cd frontend && npm install && cd ..

# 3. Run both (two terminals)
python -m uvicorn backend.main:app --port 8000
npm run dev --prefix frontend
```

Open http://localhost:5173 — on the empty Content page click **Generate a demo
video**, then run checks from the row's refresh action. The full flow works with
zero model downloads. API docs live at http://localhost:8000/docs.

**Production-ish mode:** `npm run build --prefix frontend` then run only uvicorn —
FastAPI serves `frontend/dist` at http://localhost:8000.

Tests: `python -m pytest tests/ -q`

## Current status (M0–M5 complete)

Every engine is implemented. What remains is evidence, not code — see `ROADMAP.md`.

| Component | Status |
|---|---|
| SQLite schema (6 DDD tables), WAL, FKs, config seeding | ✅ real |
| Repository/CRUD layer | ✅ real (tested) |
| Keyword compliance matcher (word-boundary + phrases) | ✅ real (tested) |
| Temporal ad-spot tracker (IoU merge, ≥5 s rule) | ✅ real (tested) |
| Sequential pipeline orchestrator + background runs + progress | ✅ real |
| Audio extraction to 16 kHz WAV (bundled ffmpeg) | ✅ real |
| CSV / JSON report export + AuditReports archive | ✅ real |
| FastAPI REST API (videos, analyze, flags, config, reports, media) | ✅ real |
| React UI (content table, detail + timeline + player, reports, settings) | ✅ real |
| Frame sampler + thumbnailer (OpenCV) | ✅ real |
| Whisper transcription (M1) | ✅ real — `faster-whisper` base.en, word timestamps |
| YOLO risk detection (M2) | ✅ real — COCO + fine-tuned `risk_yolov8.pt` (M3b) |
| Ad-spot free-space algorithm (M3a) | ✅ real — `src/vision/adspots.py` |
| PDF compliance report (M5) | ✅ real — `src/reports/pdf_report.py` |
| Benchmark harness (evaluator + runner + labeller) | ✅ real — but only 1 clip labelled |
| Accuracy claim evidenced against real footage | ❌ **not yet** — 20 clips to label |

**Demo mode:** model-backed engines are swapped for deterministic `Demo*` twins that
produce realistic output on any video. Everything downstream of the models — matching,
tracking, DB, API, UI — is the real code path either way. The run summary names the
engine that produced each result, so demo output can never be mistaken for real output.

## Layout

```
backend/              FastAPI app: main.py, routes/ (videos, system), progress.py
frontend/             React + Vite UI (YT Studio design), src/{components,pages}
src/db/               schema.sql, connection (WAL/FK), repository
src/audio/            extractor → transcriber → compliance   (Module 1)
src/vision/           sampler → detector → adspots → tracker (Module 2)
src/pipeline/         orchestrator (Module 3, sequential per D2)
src/reports/          CSV/JSON/PDF exporters
src/demo_media.py     synthetic H.264 test-footage generator
tests/                pytest suite for the real logic
data/, models/        gitignored artifacts (videos, thumbs, audit.db, weights)
```

## Team modules

| Module | Scope | Code |
|---|---|---|
| 1 | Audio & NLP engine | `src/audio/` |
| 2 | Vision & ad-spots | `src/vision/` |
| 3 | Orchestrator + DB + API | `src/pipeline/`, `src/db/`, `backend/` |
| 4 | Web UI | `frontend/` |
