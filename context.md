# Project Context — AdSafe Studio

> **Single source of truth for the current state of the project.** Read this first when
> picking the work back up. For *why* the design is shaped this way see [`PLAN.md`](PLAN.md);
> for *what happens next* see [`ROADMAP.md`](ROADMAP.md).
>
> Last updated: 2026-07-22 · Milestone: **M0+ complete** (walking skeleton + full web UI)

---

## 1. What this project is

**Autonomous Video Ad-Placement & Contextual Safety Analyzer** (product name: **AdSafe
Studio**). An **offline, local** desktop web app that audits long-form video for two
things at once:

1. **Brand-safety / compliance risks** — restricted speech (profanity, sensitive
   words) via audio, plus visual hazards (weapons, smoking, alcohol) via computer
   vision — the things that get a video demonetized.
2. **Premium ad-placement surfaces** — continuous empty regions (blank walls, screens,
   empty desks) suitable for sponsor overlays.

Everything runs on local hardware: no cloud APIs, no footage leaving the machine
(privacy for unreleased/NDA content, zero recurring cost). The justification with
real-world YouTube demonetization data is in `Project_Justification.docx`.

**Academic frame:** Specialization Project, course **BCA482-5**, CHRIST (Deemed to be
University), AY 2026–2027.
Team: Andrew Shelton S (2441609) · Akash Ganesh (2441604) · Andrew Judah (2441608) ·
Ramona Elisha Mary (2441646). Guide: Dr. Chanti.

---

## 2. Tech stack

| Layer | Choice |
|---|---|
| Backend API | **FastAPI** (Python 3.12) + Uvicorn |
| Database | **SQLite** with WAL journal mode, FK enforcement |
| AI pipeline | Plain Python modules under `src/` (OpenCV now; faster-whisper + YOLOv8 later) |
| Media/ffmpeg | **imageio-ffmpeg** bundled binary (no system ffmpeg dependency) |
| Frontend | **React 18 + Vite 5 + react-router 6**, hand-rolled CSS design system |
| Design language | **YouTube Studio** — Roboto, Material Symbols, dark theme default |

No component/UI framework — the YT-Studio look is a bespoke token system in
`frontend/src/styles.css`.

---

## 3. Architecture — four modules

Mirrors the SRS layer model (Presentation → Controller → AI Engine → Data). The DB is
the central orchestrator between engines; the pipeline runs **sequentially** (Decision
D2), never in parallel.

```
                       ┌─────────────────────────────┐
  React UI  ──HTTP──►  │  FastAPI (backend/)          │
  (frontend/)          │  routes: videos, system      │
                       └──────────────┬──────────────┘
                                      │ calls
                         ┌────────────▼────────────┐
                         │  Orchestrator (Module 3) │  sequential
                         │  src/pipeline/           │
                         └───┬───────────┬──────────┘
              ┌──────────────▼──┐   ┌────▼──────────────────┐
              │ Audio (Module 1)│   │ Vision (Module 2)     │
              │ src/audio/      │   │ src/vision/           │
              │ extract→trans-  │   │ sample→detect→adspot  │
              │ cribe→match     │   │ →track                │
              └────────┬────────┘   └────────┬──────────────┘
                       └──────────┬───────────┘
                          ┌───────▼────────┐
                          │ SQLite (src/db)│  6 tables, WAL
                          └────────────────┘
```

| Module | Owns | Code |
|---|---|---|
| 1 | Audio & NLP engine | `src/audio/` |
| 2 | Vision + ad-spots | `src/vision/` |
| 3 | Orchestrator + DB + API | `src/pipeline/`, `src/db/`, `backend/` |
| 4 | Web UI | `frontend/` |

---

## 4. What is built — real vs. stub

The guiding principle: **everything downstream of the AI models is real.** The
model-backed engines are stubbed with deterministic `Demo*` twins (seeded by
`video_id`) that emit realistic output, so the whole pipeline runs end-to-end **offline
with zero model downloads**. Swapping a stub for the real engine changes nothing
downstream.

| Component | State |
|---|---|
| SQLite schema (6 DDD tables), WAL, FKs, config seeding | ✅ **real** |
| Repository / CRUD layer | ✅ **real** (tested) |
| Keyword compliance matcher — word-boundary + phrase matching | ✅ **real** (tested) |
| Temporal ad-spot tracker — IoU merge, ≥5 s persistence rule | ✅ **real** (tested) |
| Sequential orchestrator + background runs + progress registry | ✅ **real** |
| Audio extraction → 16 kHz mono WAV (bundled ffmpeg) | ✅ **real** |
| Frame sampler + thumbnailer (OpenCV, seek-based 1 FPS) | ✅ **real** |
| CSV / JSON report export + `AuditReports` archive | ✅ **real** |
| FastAPI REST API (videos, analyze, flags, config, reports, media+range) | ✅ **real** |
| React UI — 7 screens, responsive (4 breakpoints), light+dark, a11y pass | ✅ **real** |
| Synthetic H.264 demo-video generator | ✅ **real** |
| **Whisper transcription** | 🔲 **stub → M1** (`faster-whisper`, D3) |
| **YOLO risk detection** | 🔲 **stub → M2** (community weights, D1) |
| **Ad-spot frame algorithm** (free-space detection) | 🔲 **stub → M3a** (spec in `src/vision/adspots.py`) |
| **PDF export** | 🔲 **stub → M5** (`reportlab`) |

Each stub raises a clear `NotImplementedError` pointing at its milestone and carries the
full implementation sketch in its docstring.

---

## 5. Repository map

```
specproj/
├── context.md            ← this file
├── PLAN.md               strategic design→build plan + decision log
├── ROADMAP.md            tactical go-forward plan (next parts)
├── README.md             quick start + demo-run instructions
├── requirements.txt      backend deps (AI engines commented until their milestone)
├── demo_setup.py         seeds a clean 2-video library for the review demo
├── RUN_DEMO.bat          one-click build+serve for the panel (Windows)
├── Synopsis.pdf · SRS (1).pdf · DDD_Final.pdf   design docs
├── Project_Justification.docx · Presentation_I_AdSafe.pptx
├── .claude/launch.json   dev-server launch config (api :8000, web :5173)
│
├── backend/              FastAPI app (Module 4 backend)
│   ├── main.py           app, CORS, media mounts, SPA fallback for built frontend
│   ├── progress.py       in-memory progress registry for background runs
│   └── routes/
│       ├── videos.py     ingest, list, analyze, status, flags, delete, demo
│       └── system.py     config (SystemConfig), reports (create/list/download)
│
├── frontend/             React + Vite (Module 4 UI)
│   └── src/
│       ├── App.jsx        shell, routing, theme toggle (dark default), mobile drawer
│       ├── api.js         fetch/XHR client + formatting helpers
│       ├── useMediaQuery.js  breakpoint hook (behaviour agrees with the CSS)
│       ├── styles.css     the YT-Studio design system (tokens, light+dark, responsive)
│       ├── components/    TopBar, Sidebar, Badges, Charts, UploadDialog, Timeline (SVG)
│       └── pages/         Dashboard, Content, VideoDetail, Analytics, Reports, Settings
│
├── src/                  AI pipeline + data (Modules 1–3)
│   ├── config.py         paths, constants, seed defaults
│   ├── demo_media.py     synthetic H.264 test footage
│   ├── db/               schema.sql, connection.py (WAL/FK), repository.py
│   ├── audio/            extractor.py → transcriber.py → compliance.py
│   ├── vision/           sampler.py → detector.py → adspots.py → tracker.py
│   ├── pipeline/         orchestrator.py (sequential, demo/real split)
│   └── reports/          exporter.py (CSV/JSON real, PDF stub)
│
├── tests/                15 pytest tests (compliance, tracker, repository)
├── data/                 gitignored — videos, thumbs, audit.db
└── models/               gitignored — future weights
```

---

## 6. Data model (6 tables, 3NF — per DDD)

- **VideoMetadata** (parent) — filename, path, size, duration, fps, resolution, status
  (`pending`/`processing`/`completed`/`failed`).
- **AudioFlags** — timestamp_start/end, word_flagged, transcript_context, severity
  (Low/Medium/High), detection_model. FK → video, `ON DELETE CASCADE`.
- **VisualFlags** — frame_timestamp, object_detected, bounding_box_json, confidence,
  risk_category (Weapon/Substance/Graphic). FK → video.
- **AdSpots** — timestamp_start/end, spot_type, bounding_box_json, area_pixels,
  suitability_score. FK → video.
- **AuditReports** — generation_timestamp, report_type (CSV/JSON/PDF), file_path,
  totals, compliance_status. FK → video.
- **SystemConfig** (singleton table) — the profanity dictionary, frame_sample_fps,
  min_ad_spot_duration_sec, detection_confidence_threshold, whisper_model. Editable
  from the Settings page.

Bounding boxes stored as JSON arrays `[x1, y1, x2, y2]`. **Compliance verdict**:
`Restricted` if any High-severity audio flag OR any Weapon-category visual flag exists,
else `Monetizable` (drives the yellow/green `$` badge in the UI).

---

## 6a. Screens (7) — for the UID document

| # | Screen | Route | Purpose |
|---|---|---|---|
| 1 | Dashboard | `/` | Library health at a glance: totals, monetizable/restricted split, recent uploads |
| 2 | Content | `/content` | The library table — thumbnails, monetization badge, live check progress |
| 3 | Video Detail | `/video/:id` | Player + audit timeline + per-category flag tables, click-to-seek |
| 4 | Analytics | `/analytics` | Aggregate charts: severity, risk category, top words/objects, ad inventory |
| 5 | Reports | `/reports` | Generate + download CSV/JSON audits; report history |
| 6 | Settings | `/settings` | Keyword dictionary + pipeline thresholds, with inline validation |
| 7 | Upload dialog | modal | Drag-and-drop upload with client-side validation and progress |

**Responsive breakpoints:** Desktop ≥1200 · Laptop 900–1199 (icon rail, 2-col stats) ·
Tablet 600–899 (sidebar → overlay drawer) · Mobile <600 (content table → card list).

**No authentication by design** — single-user offline desktop tool (privacy NFR). The
SRS's user characteristics (agencies, creators, compliance officers) are *personas*,
not authenticated roles.

## 7. REST API surface (prefix `/api`)

| Method | Path | Purpose |
|---|---|---|
| GET | `/videos` | list, enriched with counts + verdict + thumb/video URLs |
| GET | `/videos/{id}` | single video |
| POST | `/videos` | multipart upload → ingest |
| POST | `/videos/demo` | generate + ingest synthetic demo video |
| DELETE | `/videos/{id}` | delete (cascades) |
| POST | `/videos/{id}/analyze` | run pipeline in background |
| GET | `/videos/{id}/status` | processed_status + live stage/progress |
| GET | `/videos/{id}/flags` | audio/visual/ad_spots + verdict |
| GET | `/stats` | library-wide aggregates (Dashboard + Analytics) |
| GET/PUT | `/config` | read/update SystemConfig |
| GET/POST | `/reports` | list / generate (CSV, JSON) |
| GET | `/reports/{id}/download` | download an exported report file |

Media served with HTTP Range support at `/media/videos/*` and `/media/thumbs/*` (so the
`<video>` element can seek). Interactive API docs at `http://localhost:8000/docs`.

---

## 8. How to run

**Development (two servers, hot reload):**
```bash
pip install -r requirements.txt          # once
cd frontend && npm install && cd ..      # once
python -m uvicorn backend.main:app --port 8000   # terminal 1
npm run dev --prefix frontend                    # terminal 2  → http://localhost:5173
```
Vite proxies `/api` and `/media` to the backend on :8000.

**Demo / single-server (for the review):** `python demo_setup.py` once to seed a clean
2-video library, then double-click `RUN_DEMO.bat` (builds the frontend, serves
everything from uvicorn on :8000). Stop the server before re-running `demo_setup.py` —
it can't delete an open database.

**Tests:** `python -m pytest tests/ -q` (15 passing).

---

## 9. Key engineering decisions (see PLAN.md §6 for full rationale)

- **D1 — Hybrid risk model.** Use community pretrained weights at M2 to unblock the
  pipeline; fine-tune our own YOLOv8 later as an *upgrade*, not a dependency.
- **D2 — Sequential processing**, not parallel (resolves a Synopsis/SRS contradiction;
  avoids GPU contention + SQLite lock errors). WAL + single writer regardless.
- **D3 — faster-whisper** over stock Whisper (faster, less memory, native word-level
  timestamps that `AudioFlags` requires).
- **D4 — Two vision models** — COCO YOLOv8 for scene occupancy/ad-spots, a separate risk
  model for weapons/substances (COCO's 80 classes contain no gun/cigarette/drug).
- **UI: dark theme by default**, validated colors. Action blue swaps by theme because
  `#065fd4` fails WCAG contrast (2.76:1) on the dark card — dark mode uses `#3ea6ff`
  (6.21:1), exactly what YouTube does. Severity palette is fixed across themes and
  passes contrast + colorblind-separation checks.
- **Label normalization at the detector boundary** — community weights' class names map
  to our `risk_category` vocabulary in `detector.py` so swapping models never ripples
  into the DB.

---

## 10. Environment notes / gotchas

- **Python** anaconda 3.12; **Node** 22. Windows 11.
- **No system ffmpeg** — solved by using imageio-ffmpeg's bundled binary in
  `extractor.py` and `demo_media.py`. Do not reintroduce a system-ffmpeg dependency.
- Demo videos are **transcoded to H.264** so they play inline in the browser
  (OpenCV's default mp4v codec does not).
- `data/`, `models/`, `frontend/node_modules/` and caches are gitignored.

---

## 11. Git / repo state

- Remote: **`meeeee21/autonomous-video-analyzer`** (private), branch `main`.
- Latest commit `534ebfb` — "Add AdSafe Studio: FastAPI + React video safety analyzer"
  (the full M0+ skeleton, layered on top of the repo's original stub `README.md`).
- Local git identity: AndrewShelton01.

---

## 12. Where the marks are (for the viva)

The **ad-spot free-space algorithm** (M3a, currently stubbed in `src/vision/adspots.py`)
is the project's most novel contribution — detecting the *absence* of objects is not an
object-detection problem, so it needs the real OpenCV algorithm described in PLAN.md
§2.2. The **>85% precision claim** in the SRS also requires a labelled benchmark set
that does not exist yet (PLAN.md §5.2). Both are called out in `ROADMAP.md`.
