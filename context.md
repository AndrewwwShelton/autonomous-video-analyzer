# Project Context — AdSafe Studio

> **Single source of truth: what this project is, what has been built, and why it is
> shaped the way it is.** Read this first when picking the work back up.
> For the original design-to-build reasoning and decision log see [`PLAN.md`](PLAN.md);
> for what remains see [`ROADMAP.md`](ROADMAP.md).
>
> Last updated: **2026-08-07** · Status: **every AI engine is real; evidence outstanding**

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
| Python (src + backend) | ~3,630 lines |
| Frontend (jsx/js/css) | ~2,350 lines |
| Tests | **169 passing** across 12 files |
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
| **M3b Fine-tune** *(promoted)* | Own risk model trained on Open Images V7 — run 1 **mAP@50 0.566** |
| **M3a Ad-spots ★** | The **free-space algorithm** — the project's novel contribution |
| **M5 Reports** | Formatted **PDF** compliance report with drawn timeline |
| **Branding** | Original logo replacing a YouTube-derived mark |
| **M6 Overlay context ★** | **Persistent-overlay detection** + a three-state verdict, so rendered weapons stop restricting gameplay footage |
| **M7 Real-video hardening** | Multi-scale detection, grouped finding names, per-flag provenance, relative overlay stability — all driven by testing four real clips |
| **M3b run 2** | Retrained on a Colab T4 — better on every headline metric, **rejected**: it detected the ATF pistol zero times where run 1 found it 13 |

Milestones were deliberately not built in numeric order. M4 came early because the UID
document needed a real interface to photograph; M3b was promoted from "optional" once
research showed community weights were unusable.

**M6 was not planned at all.** It came from a question with no good answer: *if a video
is Call of Duty, and the guns are in the game, does the tool flag it?* It did — one
weapon detection in one frame of a ten-minute video was enough. That is the same
context-blind over-flagging `Project_Justification.docx` criticises YouTube for, which
made it worth stopping to fix rather than noting as future work.

**M7 was not planned either, and mattered more.** Until then everything had been
verified on synthetic footage. Four real clips were then run through the tool, and
**every one of them broke something** — see §18 for the table. Nothing about the
architecture changed; what changed was a set of defaults and thresholds that were
quietly wrong for real video and invisible on generated video.

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
              │ scribe → match  │   │              │    ├──►│ ad-spots → track
              │                 │   │              └────┴──►│ overlay context
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

**One inference pass, three consumers** (decision D4): the same decoded frame feeds risk
flags, the ad-spot occupancy mask, and the overlay accumulator — so frames decode and
models run once. Overlay detection needs the whole sequence rather than one image, but
accumulates in constant memory, so it rides the existing pass instead of adding one.

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
| **M2** Visual risk detection (COCO + fine-tune, multi-scale) | ✅ real |
| **M3a** Ad-spot free-space algorithm ★ | ✅ real (tested) |
| **M3b** Fine-tuned risk model (Open Images, mAP@50 0.566) | ✅ real |
| **M5** CSV / JSON / PDF export + `AuditReports` archive | ✅ real (tested) |
| **M6** Persistent-overlay detection ★ | ✅ real (tested) |
| **M6** Three-state verdict with printed reasoning | ✅ real (tested) |
| REST API — 15 endpoints, range-served media | ✅ real |
| React UI — 7 screens, 4 breakpoints, light+dark, a11y | ✅ real |
| Benchmark harness + labelling tooling | ✅ real (tested) |
| **Benchmark data — labelled clips** | 🔴 **0 of 20** |

### Honesty guards (deliberate — do not remove)

Seven places where the system refuses to let demo, thin, or unexplained evidence pass
as real:

1. **Run summary** names the engine behind each stage (`faster-whisper-base.en`,
   `demo-detector`, …).
2. **PDF report** prints provenance and states in bold when findings came from demo
   stand-ins — a report gets forwarded to people who weren't there when it was made.
3. **Benchmark** excludes stubbed stages from the headline figure, and prints
   `NOT YET PUBLISHABLE` below 30 events / 10 real clips.
4. **Overlay detection returns `inconclusive`** rather than guessing when the scene is
   too static to judge, and "cannot tell" is never read downstream as "it is a game".
   Demo overlay output carries a literal `DEMO OUTPUT —` prefix in its reason.
5. **Every verdict states its reasoning**, on screen and in the PDF. An unexplained
   "Restricted" is precisely the creator complaint this project is built around, so the
   tool is not permitted to issue one.
6. **Every visual flag records the engine that produced it**, shown beside the audio
   one. Added after a real failure: a news clip analysed in demo mode produced invented
   findings that were indistinguishable from measured ones in the table, and were
   reasonably read as genuine misclassifications. A demo run now also opens the page
   with a banner saying outright that nothing was analysed.
7. **Findings are named at the confidence the evidence supports** — "Handheld weapon",
   not "Knife" — with the model's own class kept visible beneath so a wrong *grouping*
   stays distinguishable from a wrong *detection*.

---

## 7. The novel contributions

Everything else in the project is competent integration of existing models. These two
parts are genuinely original, and are where a viva will push hardest.

### 7a. Ad-spot free-space detection

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

### 7b. Persistent-overlay detection (M6)

**The problem:** a rifle in Call of Duty and a rifle on a table produce the same
detection. Before this, one weapon flag in one frame restricted the entire video —
0.17% of a ten-minute runtime deciding the outcome. Measured: *300 frames of alcohol
passed; one frame with a rifle did not.*

**The insight:** the distinguishing signal is not the weapon, it is the **interface
drawn on top of it**. Gameplay carries a HUD — crosshair, health bar, minimap, ammo
counter — which occupies fixed pixels while the world behind it moves. Nothing in
filmed footage does that.

Two measurements, in `src/vision/overlay.py`:

1. **Per-pixel temporal variance** — overlay pixels are markedly steadier than the
   scene. Accumulated streaming (running sum and sum-of-squares), so memory is
   independent of video length: a 1-hour video costs the same ~1 MB as a 30-second one.
2. **Edges surviving in the temporal mean** — the discriminating step. A static overlay
   stays *sharp* under averaging because it lands on the same pixels every frame;
   moving content blurs away. A crisp edge at a pixel that barely varies is drawn, not
   filmed.

Neither alone suffices, and each prevents a specific failure: variance alone flags
letterbox bars and tripod shots; edges alone flag every still object in a static scene.

**Stability is relative, not absolute — and that took real gameplay to learn.** The
first version demanded a per-pixel standard deviation ≤ 4.0. Tested on genuine
Counter-Strike footage it found *nothing*: 0.04% coverage against a 1% threshold, so a
video with a minimap, health bar and ammo counter on screen throughout was treated as
real and restricted. A real HUD is **semi-transparent**, so the moving scene shows
through it, and its contents change as ammo counts down and radar dots move. The 1st
percentile of per-pixel variance on that clip was 6.19 — above the threshold — and only
0.32% of the frame qualified as static. The threshold is now the looser of the absolute
floor and the frame's own **10th percentile**, so an overlay need only be steadier than
what is behind it.

It is the **third consumer of the same decoded frame** (decision D4), so it adds a
running sum per frame rather than a second pass over the file.

**Naming is deliberate: it detects overlays, not games.** A channel watermark, a news
lower-third and a donation bar all trigger it. Gameplay is an *inference* the evidence
supports — which is why the report carries region count and coverage rather than a
boolean, and why a lone small region is described as a watermark rather than an
interface.

**The verdict gained a third state.** Binary was the original flaw: `Monetizable`
over-claims when weapons are genuinely present, `Restricted` over-punishes when they
are drawn, and **`Review`** says what is actually true — a human should look. Nothing is
ever suppressed: every flag stays recorded and visible, and only the verdict weighs
context. The exemption is narrow by design, each limit pinned by a test:

- spoken terms are **never** excused (an overlay says nothing about what was said);
- a **single** region is a watermark, not evidence of rendered content;
- `inconclusive` never reads as "it is a game".

**Validated against real gameplay**, which was an open question when the module landed:

| Clip | motion | coverage | verdict |
|---|---|---|---|
| Counter-Strike capture (real) | 97% | 3.49%, 8 regions | `overlay` → **Review** |
| ATF news clip (filmed, moving camera) | 79% | 0.00% | `none` |
| locked-off demo footage | 13% | — | `inconclusive` (motion gate) |
| synthetic gameplay clip | 52% | 7.87%, 5 regions | `overlay` |

The negative rows matter as much as the positive one: a detector that called everything
an overlay would dismiss genuine weapon footage as gameplay, which is worse than the
over-flagging it replaced.

---

## 8. Data model (6 tables, 3NF — per DDD)

- **VideoMetadata** (parent) — filename, path, size, duration, fps, resolution, status
  (`pending`/`processing`/`completed`/`failed`), **overlay_context** (JSON)
- **AudioFlags** — timestamps, word_flagged, transcript_context, severity, detection_model
- **VisualFlags** — frame_timestamp, object_detected, bounding_box_json, confidence,
  risk_category (Weapon/Substance/Graphic), **detection_model**
- **AdSpots** — timestamps, spot_type, bounding_box_json, area_pixels, suitability_score
- **AuditReports** — generation_timestamp, report_type (CSV/JSON/PDF), file_path, totals,
  compliance_status
- **SystemConfig** (singleton) — profanity dictionary, frame_sample_fps,
  min_ad_spot_duration_sec, detection_confidence_threshold, whisper_model,
  **analysis_mode**, **vision_weights**, **detection_max_imgsz** — all editable
  in Settings

Children cascade on delete. Boxes stored as JSON `[x1, y1, x2, y2]`.

`overlay_context` and `VisualFlags.detection_model` are the **extensions to the DDD
schema** (M6/M7). Both are added by migrations in `connection.py`, not just to
`schema.sql`: `CREATE TABLE IF NOT EXISTS` silently does nothing when the table already
exists, so a new column would never reach a database made by an earlier build. The same
mechanism upgrades the keyword dictionary — but only where it exactly matches the
original nine words, since silently discarding a curated list would be worse than
leaving it stale.

**Compliance verdict** (`orchestrator.assess_compliance`), in order:

1. any **High-severity audio** flag → `Restricted` — speech is judged on its own terms,
   and an overlay never excuses it;
2. else no **Weapon** visual flag → `Monetizable`;
3. else **overlay evidence** looks like an interface (confidence ≥ 0.5 **and** ≥ 2
   regions) → `Review`;
4. else → `Restricted`.

Drives the green/amber/red `$` badge, the verdict banner in the PDF, and the split on
the Dashboard. The rule exists **twice** — in Python per video, and as SQL in
`repository._VERDICT_SQL` so the library summarises in one pass.
`tests/test_compliance_verdict.py` asserts the two agree; a drift would make the
dashboard silently disagree with the video pages.

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
| GET | `/videos/{id}/status` · `/flags` | live progress / findings + verdict + full assessment |
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
├── Project_Justification.docx · Presentation_I/II_AdSafe.pptx
│
├── backend/              FastAPI: main.py, progress.py, routes/{videos,system}.py
├── frontend/src/         App.jsx, api.js, styles.css, components/, pages/
│
├── src/
│   ├── config.py · demo_media.py
│   ├── db/               schema.sql, connection.py (WAL/FK), repository.py
│   ├── audio/            extractor → transcriber → compliance
│   ├── vision/           sampler → detector → adspots ★ → overlay ★ → tracker
│   ├── pipeline/         orchestrator.py (sequential, per-stage engines)
│   ├── reports/          exporter.py + pdf_report.py
│   └── benchmark/        evaluator.py (scoring) + runner.py
│
├── benchmark/            evaluate.py · intake.py · labeller.html · status.py
│   │                     make_synthetic_clip.py · make_gameplay_clip.py
│   ├── labels/           ground truth — COMMITTED, this is the deliverable
│   └── clips/            media — gitignored
│
├── training/             download_dataset.py · prune_classes.py · train.py · RESULTS.md
├── docs/UID/main.tex · docs/screens/ (14 captures) · docs/SCREENSHOT_CHECKLIST.md
├── tests/                169 tests across 12 files
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

**Smoking is uncovered by any reputable source found.** Verified against the full
601-class Open Images V7 boxable vocabulary, not assumed: there is no cigarette,
tobacco, smoking, drug, pill, blood or gore class. Must be described as out of scope,
not implied.

**A class can exist in a dataset and still be unusable.** `Axe` (2 training instances,
0 validation) and `Syringe` (19 / 0) *are* Open Images classes, but are near-absent
from the `test`/`validation` splits this project sources from — so raising the download
quota does nothing. Zero validation instances is the sharper problem: the class cannot
be scored at all, and would publish a meaningless per-class mAP while detecting
nothing. This is a different failure from cigarette, and the two are recorded
separately.

**Detecting an object says nothing about whether it is real.** The finding that
prompted M6. A weapon detection alone cannot separate gameplay from footage, and the
original `any()` rule restricted a whole video on one frame — measured, *300 frames of
alcohol passed while one frame with a rifle did not*. Context has to come from
somewhere other than the detector.

**First real-world test, and all three engines behaved differently.** A 25 s ATF
firing-range news clip (720p, officer shooting at a range, pistol in hand
throughout) was run in `real` mode:

- **The fine-tuned `Handgun` class never fired at all** — not one detection, at any
  confidence, down to 0.01. This is the domain gap `RESULTS.md` warned about
  becoming concrete: it was trained on Open Images *photographs* (clean, centred,
  well-lit) and applied to compressed video of a small, motion-blurred, partly
  occluded weapon held at arm's length. **More epochs will not fix this; different
  training data would.**
- **COCO confidently called the pistol a `cell phone` at 0.65** — a dark rectangle
  in an extended hand. `cell phone` maps to no risk category, so it was discarded
  in silence. The single most useful frame in the project for explaining what
  object detection actually does.
- **Whisper was flawless** — *"this is semi-automatic, a single pull of the
  trigger... turning it on fully auto"* — and matched **nothing**, because the
  dictionary held nine words: profanity plus `gun`, `kill`, `weapon`. A firearms
  demonstration where nobody says the word "gun" passed as `Monetizable`.

The lesson is about where effort pays. The dictionary is the **cheapest lever in
the system** and the only one that covers what the vision model misses; widening it
to real firearms, violence and substance vocabulary caught this clip on the audio
path (`Restricted`, 2 high-severity terms) while the expensive model stayed blind.

**The weapon detector was not blind — the weapon was being shrunk.** The finding above
looked like a dead end for the whole vision module. It was not. Ultralytics infers at
640 px by default, which halves 720p footage and puts a pistol at arm's length below
what YOLOv8n can resolve; cropping the pistol and running it alone fired immediately.
Raising the resolution then fixed that clip and **broke a second one**, a review video
with the pistol filling the frame:

| imgsz | distant pistol | close-up pistol |
|---|---|---|
| 640 | **0 flags** | 10 flags |
| 960 | 1 | 4 |
| 1280 | 13 | 1 |
| 1600 | 15 | **0 flags** |

The relationship is **inverted**, so no single resolution serves both — the fine-tune
was trained at 512 px, so shrink the frame and a distant weapon vanishes, enlarge it and
a near one grows past any scale the model saw. Detection therefore runs at **two
scales** and merges, which recovers both (0→13 and 10→10). It costs roughly double the
inference time; that is the honest price of the recall.

**The label is unreliable even when the category is right.** The same pistol came back
as `Knife` in one clip and `Rifle` in another — correct category twice, correct class
neither time. Findings are therefore reported as **"Handheld weapon"** with the raw
class shown beneath, in the interface and the PDF. The compliance verdict was always
driven by the category, never the class name, so nothing about the logic changed —
only what it claims out loud. `bottle` stays "Drink container" rather than "Alcohol",
because COCO's bottle is as often water.

**Two overlay false positives, both found by measuring rather than reasoning.**
*Letterbox bars*: perfectly stationary, and the boundary where they meet the picture
was the strongest overlay signal in the frame — 2.22% coverage, reported as a HUD. The
first fix (reject uniform edge bands) then broke detection outright, because busy
content averages to flat grey, so a mean-only flatness test chewed inward from every
edge and deleted the corners where a HUD lives; the test must require flatness **and**
temporal stillness. *Real locked-off footage*: 13% motion, 29% coverage, confidently
called gameplay — a fixed physical object holds the same unchanging edges as a drawn
overlay when nothing moves behind it. Dynamic footage measures 98–100% motion, so the
gate sits at 35%, in the empty space between the two populations.

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

**Run 2 was trained and rejected — the most instructive result in the project.** 40
epochs @ 640 px on a free Colab T4, ~20 minutes against 10.8 hours on CPU. It improved
*every* headline metric: mAP@50 0.566 → 0.591, precision +0.046, recall +0.018, and
`Handgun` — the weakest and most consequential class — 0.487 → **0.546**.

Then it was tested on the clip that prompted the retrain, and **detected the pistol
zero times where run 1 found it 13 times**. With no threshold at all, its strongest
response on those frames was `Beer` at 0.464; every weapon class collapsed below 0.12.
Run 1 is restored as `models/risk_yolov8.pt`; run 2 is kept as `risk_yolov8.run2.pt`.

The likely cause is a change made *to help*: `scale=0.75`, set well above the 0.5
default precisely because the earlier failure looked like a scale problem. Aggressive
jitter plus 40 epochs appears to have specialised the model onto Open Images'
photographic domain rather than generalising it. A third run should revert `scale` and
change one thing at a time. Full comparison in `RESULTS.md`; reproduce with
`training/package_for_colab.py` then `training/colab_train.ipynb`.

**Current class set: 11** (1,508 train / 488 val images), revised after run 1 —
`Wine` dropped for ambiguity, `Kitchen knife` and `Bow and arrow` added, `Axe` and
`Syringe` requested but unlearnable from these splits (§12). `train.py` preserves the
previous weights as `risk_yolov8.prev.pt` and never reuses a run directory, so a worse
run cannot cost you a working model or overwrite the artefacts `RESULTS.md` cites.

Results for both runs, with the per-class comparison: `training/RESULTS.md`.

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

**Tests:** `python -m pytest tests/ -q` (169 passing).

**Demo vs real:** Settings → Analysis engines. `demo` needs no weights and is instant —
the safer choice in front of a panel. `real` runs the models.

**Showing real inference:** both seeded videos are synthetic — no speech track, no
real objects — so in `real` mode they correctly find nothing, which looks broken on a
projector. Upload `benchmark/clips/synthetic_speech_01.mp4` instead: ~31 s for a 28 s
clip, all four restricted words recovered with correct timestamps. For overlay
detection, generate and upload the gameplay clip:

```bash
python benchmark/make_gameplay_clip.py
```

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
- Latest commit `8dc9f78` — "Weigh weapon findings against overlay evidence instead of flagging on sight"
- Local identity: AndrewShelton01
- Committed: source, tests, docs, **benchmark labels**
- Ignored: `data/`, `models/`, `datasets/`, `benchmark/clips/`, `node_modules/`,
  `.venv-data/`, `training/runs/`

---

## 18. For the viva

**Strongest ground.** The two original components (§7). The ad-spot algorithm — be ready
to explain why detecting *absence* is not object detection. And overlay context — be
ready to explain why the discriminating signal is edges surviving in the temporal
**mean**, not variance alone.

**The best story you have.** *"If the video is Call of Duty and the guns are in the
game, does it flag it?"* The honest answer is that **it used to**, that this was found
by asking the question rather than by a test failing, and that the fix required
admitting the verdict itself was wrong-shaped — not just the threshold. A binary
verdict is exactly the flaw the project criticises YouTube for, and it was reproduced
before it was noticed. Say so; it is far stronger than pretending the design was right
from the start.

**The second-best story: every real video broke something, and the breakages were
instructive.** Four clips were tested, and none behaved as expected.

| Clip | What it exposed |
|---|---|
| ATF news (demo mode) | Invented findings looked identical to measured ones — no provenance on visual flags |
| ATF news (real mode) | Weapon undetected: 640 px inference shrank it below resolvable. Whisper was perfect; the *dictionary* held nine words |
| Umarex review | Raising resolution to fix the above **broke this one** — the relationship is inverted |
| Counter-Strike | Real HUDs are translucent and change, so the absolute variance gate found nothing |

Each was fixed at the layer where fixing was cheap, and the cheapest lever — the
keyword dictionary — turned out to catch what the expensive model missed. That is a
better engineering narrative than a system that worked first time.

**Also defensible.** The honesty guards (§6): the system refuses to let demo output, a
four-event sample, or an unexplained verdict pass as a result. A deliberate engineering
position, not timidity.

**Expect to be asked.**

- *"How did you get the accuracy figure?"* — the weak point until clips are labelled.
- *"Does the overlay detector work on real gameplay?"* — **yes, now measured.** A real
  Counter-Strike capture reports `overlay` at 3.49% coverage over 8 regions and comes
  back `Review`, while filmed footage stays at 0.00%. It did **not** work on the first
  attempt, and saying so is the stronger answer (§7b).
- *"So your weapon detector doesn't detect weapons?"* — it detects them at 0.487 mAP on
  photographs and failed on compressed video of a partly-occluded one until the
  inference resolution was fixed. A **measured domain-shift result**, not a mystery.
- *"Did retraining help?"* — **no, and that is the most useful thing measured.** Run 2
  beat run 1 on mAP@50, precision, recall and on `Handgun` specifically, then detected
  the ATF pistol zero times where run 1 found it 13. It was rejected on that evidence
  and run 1 restored. A validation set drawn from the training distribution cannot
  tell you whether a model works; only video can. Be ready to say which single change
  probably caused it (`scale=0.75`) and what a third run would do differently.
- *"Why does it say 'Handheld weapon' instead of the object?"* — because the category is
  reliable and the class is not; the raw class is printed beneath. Claiming "Knife" as
  fact would assert precision never measured.
- *"What else triggers the overlay detector?"* — a channel watermark, a news
  lower-third, a donation bar. It detects **overlays**, not games; gameplay is an
  inference from the evidence.
- Model provenance and licensing (§12), and why smoking is not covered.

**Do not overclaim.** Coverage is partial and the interface says so. Partial coverage,
accurately described, beats a broad claim that collapses under one question.
