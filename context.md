# Project Context — AdSafe Studio

> **Single source of truth: what this project is, what has been built, and why it is
> shaped the way it is.** Read this first when picking the work back up.
> For the original design-to-build reasoning and decision log see [`PLAN.md`](PLAN.md);
> for what remains see [`ROADMAP.md`](ROADMAP.md).
>
> Last updated: **2026-08-03** · Status: **every AI engine is real; evidence outstanding**

**One-line state:** the tool works end to end — what it lacks is proof. The SRS claims
">85% precision" and the benchmark that would substantiate it has zero labelled clips.

---

## 1. What this project is

**Autonomous Video Ad-Placement & Contextual Safety Analyzer** (branded **AdSafe
Studio** in the interface). An **offline, local** desktop web app that audits long-form
video for two things at once:

1. **Brand-safety risks** — restricted speech via audio, plus visual hazards (weapons,
   alcohol) via computer vision — the things that get a video demonetized.
2. **Premium ad-placement surfaces** — continuous empty regions (blank walls, screens,
   empty desks) suitable for sponsor overlays.

Everything runs on local hardware: no cloud APIs, no footage leaving the machine
(privacy for unreleased/NDA content, zero recurring cost). The justification, backed by
real YouTube demonetization data, is in `Project_Justification.docx`.

**Academic frame:** Specialization Project, course **BCA482-5**, CHRIST (Deemed to be
University), AY 2026–2027.
Team: Andrew Shelton S (2441609) · Akash Ganesh (2441604) · Andrew Judah (2441608) ·
Ramona Elisha Mary (2441646). Guide: Dr. Chanti.

---

## 2. Current state at a glance

| | |
|---|---|
| Python (src + backend) | ~2,720 lines |
| Frontend (jsx/js/css) | ~2,240 lines |
| Tests | **95 passing** across 8 files |
| Screens | 7, responsive over 4 breakpoints, light + dark |
| REST endpoints | 15 |
| Stage deliverables | Synopsis · SRS · DDD · UID — all submitted |
| Remaining blocker | **benchmark labelling: 0 of 20 clips** |

---

## 3. Build history — what was done, in order

| Milestone | Outcome |
|---|---|
| **M0 Skeleton** | SQLite schema (6 DDD tables), repository, orchestrator, REST API, Streamlit UI |
| **Re-platform** | Streamlit dropped for **FastAPI + React** on request; YouTube-Studio design language |
| **M4 UI** *(early)* | 4 → **7 screens**, responsive, accessibility pass, inline validation — pulled forward to support the UID document |
| **UID document** | Stage-4 LaTeX doc written from 14 live screen captures |
| **M1 Audio** | Real speech-to-text via **faster-whisper**, word-level timestamps |
| **Benchmark harness** | Scoring, matching rules, CLI, honesty guards — plus intake/labelling/coverage tooling |
| **M2 Vision** | Real detection: COCO YOLOv8 + label normalisation + coverage reporting |
| **M3b Fine-tune** *(promoted)* | Own risk model trained on Open Images V7 — **mAP@50 0.566** |
| **M3a Ad-spots ★** | The **free-space algorithm** — the project's novel contribution |
| **M5 Reports** | Formatted **PDF** compliance report with drawn timeline |
| **Branding** | Original logo replacing a YouTube-derived mark |

Milestones were deliberately not built in numeric order. M4 came early because the UID
document needed a real interface to photograph; M3b was promoted from "optional" once
research showed community weights were unusable.

---

## 4. Tech stack

| Layer | Choice |
|---|---|
| Backend API | **FastAPI** (Python 3.12) + Uvicorn |
| Database | **SQLite**, WAL journal mode, FK enforcement |
| Speech-to-text | **faster-whisper** (CTranslate2), word timestamps, VAD filter |
| Detection | **Ultralytics YOLOv8** — COCO + our fine-tune |
| Ad-spots | **OpenCV** free-space algorithm (own work) |
| Reports | **reportlab** (PDF), pandas (CSV), stdlib (JSON) |
| Media/ffmpeg | **imageio-ffmpeg** bundled binary — no system ffmpeg needed |
| Frontend | **React 18 + Vite 5 + react-router 6**, hand-rolled CSS design system |
| Design language | YouTube Studio *conventions* (own logo), Roboto, Material Symbols, dark default |

---

## 5. Architecture — four modules

Mirrors the SRS layer model (Presentation → Controller → AI Engine → Data). The pipeline
runs **sequentially** (decision D2), never in parallel.

```
                       ┌─────────────────────────────┐
  React UI  ──HTTP──►  │  FastAPI (backend/)         │
  (frontend/)          │  routes: videos, system     │
                       └──────────────┬──────────────┘
                         ┌────────────▼────────────┐
                         │  Orchestrator (Module 3)│  sequential, per-stage engines
                         │  src/pipeline/          │
                         └───┬───────────┬─────────┘
              ┌──────────────▼──┐   ┌────▼──────────────────┐
              │ Audio (Module 1)│   │ Vision (Module 2)     │
              │ extract → tran- │   │ sample → detect ──┬──►│ risk flags
              │ scribe → match  │   │                   └──►│ ad-spots → track
              └────────┬────────┘   └────────┬──────────────┘
                       └──────────┬──────────┘
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

**One inference pass, two consumers** (decision D4): the same frame detections feed both
risk flags and the ad-spot occupancy mask, so frames decode and models run once.

---

## 6. What is built

Every engine is real. The deterministic `Demo*` twins remain and still drive **demo
mode**, which needs no model weights and is the safer choice for a live demonstration.

| Component | State |
|---|---|
| SQLite schema (6 DDD tables), WAL, FKs, config seeding | ✅ real (tested) |
| Repository / CRUD layer | ✅ real (tested) |
| Keyword compliance matcher — word-boundary + phrases | ✅ real (tested) |
| Temporal ad-spot tracker — IoU merge, ≥5 s rule | ✅ real (tested) |
| Sequential orchestrator, background runs, progress registry | ✅ real |
| Audio extraction → 16 kHz mono WAV (bundled ffmpeg) | ✅ real |
| Frame sampler + thumbnailer (OpenCV, seek-based) | ✅ real |
| **M1** Speech-to-text (faster-whisper, word timestamps) | ✅ real |
| **M2** Visual risk detection (COCO + fine-tune, 13 labels) | ✅ real |
| **M3a** Ad-spot free-space algorithm ★ | ✅ real (tested) |
| **M3b** Fine-tuned risk model (Open Images, mAP@50 0.566) | ✅ real |
| **M5** CSV / JSON / PDF export + `AuditReports` archive | ✅ real (tested) |
| REST API — 15 endpoints, range-served media | ✅ real |
| React UI — 7 screens, 4 breakpoints, light+dark, a11y | ✅ real |
| Benchmark harness + labelling tooling | ✅ real (tested) |
| **Benchmark data — labelled clips** | 🔴 **0 of 20** |

### Honesty guards (deliberate — do not remove)

Three places where the system refuses to let demo or thin evidence pass as real:

1. **Run summary** names the engine behind each stage (`faster-whisper-base.en`,
   `demo-detector`, …).
2. **PDF report** prints provenance and states in bold when findings came from demo
   stand-ins — a report gets forwarded to people who weren't there when it was made.
3. **Benchmark** excludes stubbed stages from the headline figure, and prints
   `NOT YET PUBLISHABLE` below 30 events / 10 real clips.

---

## 7. The novel contribution — ad-spot free-space detection

Everything else in the project is competent integration of existing models. This is the
part that is genuinely original, and the part a viva will push hardest on.

**The insight:** finding an advertisement surface is *not* an object-detection problem.
A blank wall is the **absence** of objects, and no detector can be trained to find
nothing. The algorithm inverts the question to *"where is nothing, for long enough to
matter?"*

Per sampled frame (`src/vision/adspots.py`):

1. **Occupancy mask** — union of detection boxes, slightly dilated (objects cast shadows)
2. **Busy mask** — Canny edge density **and** local intensity variance. Two signals
   because each catches what the other misses: edges find hard structure like shelving,
   variance finds soft clutter. A patterned rug is unoccupied and still unusable.
3. **Free space** = NOT occupied AND NOT busy
4. **Largest inscribed rectangle** — histogram/monotonic-stack method, O(w·h); top-K
   disjoint by greedy erase (optimal packing is NP-hard and not worth it)
5. **Classify** from neighbours — screen / empty desk / blank wall
6. **Score** = area × uniformity × centrality, multiplicative so a rectangle must be
   reasonable on every axis

Runs at ~320 px working width: the DP is linear in pixel count, so ~30× cheaper with no
practical loss. The **temporal tracker** then requires ≥5 s persistence before a surface
becomes a Premium Ad Spot.

---

## 8. Data model (6 tables, 3NF — per DDD)

- **VideoMetadata** (parent) — filename, path, size, duration, fps, resolution, status
  (`pending`/`processing`/`completed`/`failed`)
- **AudioFlags** — timestamps, word_flagged, transcript_context, severity, detection_model
- **VisualFlags** — frame_timestamp, object_detected, bounding_box_json, confidence,
  risk_category (Weapon/Substance/Graphic)
- **AdSpots** — timestamps, spot_type, bounding_box_json, area_pixels, suitability_score
- **AuditReports** — generation_timestamp, report_type (CSV/JSON/PDF), file_path, totals,
  compliance_status
- **SystemConfig** (singleton) — profanity dictionary, frame_sample_fps,
  min_ad_spot_duration_sec, detection_confidence_threshold, whisper_model,
  **analysis_mode**, **vision_weights**

Children cascade on delete. Boxes stored as JSON `[x1, y1, x2, y2]`.

**Compliance verdict:** `Restricted` if any High-severity audio flag **or** any
Weapon-category visual flag exists, else `Monetizable` — drives the green/amber `$`
badge in the UI and the PDF verdict banner.

---

## 9. Screens (7)

| # | Screen | Route | Purpose |
|---|---|---|---|
| 1 | Dashboard | `/` | Library health: totals, monetizable/restricted split, recent uploads |
| 2 | Content | `/content` | Library table — thumbnails, monetization badge, live progress |
| 3 | Video Detail | `/video/:id` | Player + audit timeline + flag tables, click-to-seek |
| 4 | Analytics | `/analytics` | Aggregate charts across the whole library |
| 5 | Reports | `/reports` | Generate + download PDF/CSV/JSON; report history |
| 6 | Settings | `/settings` | Dictionary, thresholds, analysis mode, vision coverage |
| 7 | Upload dialog | modal | Drag-and-drop with client-side validation and progress |

**Breakpoints:** Desktop ≥1200 · Laptop 900–1199 (icon rail) · Tablet 600–899 (drawer) ·
Mobile <600 (table → card list).

**No authentication by design** — single-user offline tool (privacy NFR). The SRS's user
characteristics are *personas*, not authenticated roles. Documented in the UID.

---

## 10. REST API (prefix `/api`)

| Method | Path | Purpose |
|---|---|---|
| GET | `/videos` · `/videos/{id}` | list (enriched with counts + verdict) / single |
| POST | `/videos` · `/videos/demo` | multipart upload / generate synthetic clip |
| DELETE | `/videos/{id}` | delete (cascades) |
| POST | `/videos/{id}/analyze` | run pipeline in background; `?mode=demo\|real` |
| GET | `/videos/{id}/status` · `/flags` | live progress / findings + verdict |
| GET | `/stats` | library-wide aggregates (Dashboard + Analytics) |
| GET | `/vision-coverage` | what the loaded weights can actually detect |
| GET/PUT | `/config` | read/update SystemConfig |
| GET/POST | `/reports` · GET `/reports/{id}/download` | list / generate / download |

Media served with HTTP Range at `/media/videos/*` and `/media/thumbs/*`. Interactive
docs at `http://localhost:8000/docs`.

---

## 11. Repository map

```
specproj/
├── context.md · PLAN.md · ROADMAP.md · README.md
├── requirements.txt · demo_setup.py · RUN_DEMO.bat
├── Synopsis.pdf · SRS (1).pdf · DDD_Final.pdf · UID_Final.pdf   stages 1–4
├── Project_Justification.docx · Presentation_I_AdSafe.pptx
│
├── backend/              FastAPI: main.py, progress.py, routes/{videos,system}.py
├── frontend/src/         App.jsx, api.js, styles.css, components/, pages/
│
├── src/
│   ├── config.py · demo_media.py
│   ├── db/               schema.sql, connection.py (WAL/FK), repository.py
│   ├── audio/            extractor → transcriber → compliance
│   ├── vision/           sampler → detector → adspots ★ → tracker
│   ├── pipeline/         orchestrator.py (sequential, per-stage engines)
│   ├── reports/          exporter.py + pdf_report.py
│   └── benchmark/        evaluator.py (scoring) + runner.py
│
├── benchmark/            evaluate.py · intake.py · labeller.html · status.py
│   ├── labels/           ground truth — COMMITTED, this is the deliverable
│   └── clips/            media — gitignored
│
├── training/             download_dataset.py · prune_classes.py · train.py · RESULTS.md
├── docs/UID/main.tex · docs/screens/ (14 captures) · docs/SCREENSHOT_CHECKLIST.md
├── tests/                95 tests across 8 files
├── data/ · models/ · datasets/ · .venv-data/        gitignored
```

---

## 12. Key decisions and findings

### Original decisions (PLAN.md §6)

- **D1 — Hybrid risk model.** *Superseded* — see the research finding below.
- **D2 — Sequential processing**, not parallel. Resolves a Synopsis/SRS contradiction;
  avoids GPU contention and SQLite lock errors.
- **D3 — faster-whisper** over stock Whisper: faster, lower memory, and native
  word-level timestamps, which `AudioFlags` requires.
- **D4 — Two vision models** — COCO for occupancy/ad-spots, a separate model for risk
  classes. COCO's 80 classes contain no gun, cigarette or drug.

### Findings from the work

**Community risk weights were unusable (PLAN.md §6a).** Roboflow's trained weights are
paywalled and its free tier is a hosted API that would break the offline requirement
outright. Public weapon models on HuggingFace had negligible adoption, wrong-domain
bases (aerial imagery), or **no licence at all**. Training our own became the *lower*-risk
route — which inverted D1.

**Ultralytics YOLOv8 is AGPL-3.0**, and the licence covers models produced by the
training code, not just the code. Fine for academic use; state it in the report.

**More data did not mean better performance.** In the fine-tune, `Wine` had the most
training data (1,175 instances) and scored *worst* (mAP@50 0.250); `Handgun` had the
least (84) and scored nearly double (0.487). `Wine` is semantically ambiguous in Open
Images — bottles, filled glasses and the liquid all carry the label, overlapping the
separate `Wine glass` and `Cocktail` classes. **Fix ambiguous classes before adding
images.**

**Smoking is uncovered by any reputable source found.** Open Images has no cigarette or
tobacco class. Must be described as out of scope, not implied.

**Colour is computed, not eyeballed.** The action blue swaps by theme because `#065fd4`
measures 2.76:1 on the dark card and fails WCAG; dark mode uses `#3ea6ff` (6.21:1). The
severity palette is fixed across themes and verified for contrast and colour-blind
separation.

**Label normalisation lives at the detector boundary.** Model class names map to our
`risk_category` vocabulary in `detector.py`, so swapping weights never reaches the
database or UI. A test compares the training class list against the map — five classes
were once trained but unmapped, and their detections were being silently discarded.

---

## 13. Benchmark (the outstanding work)

Substantiates the SRS ">85% precision" claim. **The harness is finished; the labelling
is not.**

```bash
python benchmark/status.py                 # coverage vs 20 clips / 30 events
python benchmark/intake.py <video> --start 1:10 --end 2:00 --source "..."
#  then label in benchmark/labeller.html   (browser, no server needed)
python benchmark/evaluate.py               # score the real engines
```

**Scoring rules that matter:** greedy one-to-one matching (a repeated flag cannot farm
true positives); audio keys on the word within ±2 s — severity is *not* scored because
it is a dictionary lookup, not a prediction; visual keys on risk category within ±1.5 s,
not the model-specific class name; ad spots on temporal IoU ≥ 0.3.

**The rule that protects the numbers:** label from the source, **never** from the tool's
output. Grading a model against its own predictions measures nothing and is invisible in
the final figure. Include clips with **no** violations, or false positives cannot be
caught.

Synthetic TTS fixtures validate the harness only — pristine diction with no music,
noise or accents. Never evidence for the claim.

---

## 14. Training pipeline

`training/` fine-tunes the risk detector on **Open Images V7** (annotations CC BY 4.0).

```bash
.venv-data\Scripts\python.exe training/download_dataset.py   # isolated env
python training/train.py --check                             # class counts first
python training/train.py --epochs 40
```

**Two environments on purpose:** `fiftyone` pulls numpy 2.x and MongoDB and conflicts
with the project stack — installing it into the main environment broke `scikit-image`
and `streamlit`. It now lives in `.venv-data` and only writes files to disk.

Sampling is **per class**, not a global cap: a trial run asking for "any of these
classes" returned 393 Wine instances and **zero Handgun**. Sourced from the `test` and
`validation` splits (the `train` split needs ~7 GB of metadata before a single image);
`test` is the larger, so it feeds training.

Results: `training/RESULTS.md`.

---

## 15. How to run

**Development (two servers):**
```bash
pip install -r requirements.txt          # once
cd frontend && npm install && cd ..      # once
python -m uvicorn backend.main:app --port 8000
npm run dev --prefix frontend            # → http://localhost:5173
```

**Demo / single server (for the review):** `python demo_setup.py` once to seed a clean
2-video library, then double-click `RUN_DEMO.bat`. Stop the server before re-running
`demo_setup.py` — it cannot delete an open database.

**Tests:** `python -m pytest tests/ -q` (95 passing).

**Demo vs real:** Settings → Analysis engines. `demo` needs no weights and is instant —
the safer choice in front of a panel. `real` runs the models.

---

## 16. Environment notes

- **Python** anaconda 3.12 · **Node** 22 · Windows 11 · **CPU only** (no CUDA)
- **No system ffmpeg** — imageio-ffmpeg's bundled binary is used throughout. Do not
  reintroduce a PATH dependency.
- Demo videos are transcoded to **H.264** so they play inline (OpenCV's mp4v does not).
- CPU training is slow: 12 epochs took **10.8 hours**. Use a cloud GPU for quality runs.
- Model weights (~150 MB) live in `models/`, gitignored.
- `pymupdf` is installed in `.venv-data` only, for rendering PDFs during review.

---

## 17. Git

- Remote **`meeeee21/autonomous-video-analyzer`** (private), branch `main`
- Latest commit `aaa8986` — "Replace the logo with an original mark"
- Local identity: AndrewShelton01
- Committed: source, tests, docs, **benchmark labels**
- Ignored: `data/`, `models/`, `datasets/`, `benchmark/clips/`, `node_modules/`,
  `.venv-data/`, `training/runs/`

---

## 18. For the viva

**Strongest ground.** The ad-spot free-space algorithm (§7) — the one component that
could not be solved by pointing another pretrained model at it. Be ready to explain why
detecting absence is not object detection.

**Also defensible.** The honesty guards (§6): the system refuses to let demo output or a
four-event sample pass as a result. That is a deliberate engineering position, not
timidity.

**Expect to be asked.** *"How did you get the accuracy figure?"* — this is the weak
point until clips are labelled. Also: model provenance and licensing (§12), and why
smoking is not covered.

**Do not overclaim.** Coverage is partial and the interface says so. Partial coverage,
accurately described, beats a broad claim that collapses under one question.
