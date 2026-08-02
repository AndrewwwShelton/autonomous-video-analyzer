# Implementation Plan
## Autonomous Video Ad-Placement & Contextual Safety Analyzer

**Specialization Project · BCA482-5 · CHRIST (Deemed to be University)**
Team: Andrew Shelton S (2441609) · Akash Ganesh (2441604) · Andrew Judah (2441608) · Ramona Elisha Mary (2441646)
Guide: Dr. Chanti

> **Status:** Design docs complete (Synopsis, SRS, DDD). No code written yet. This document is the bridge from design to implementation.

---

## 0. Read This First — Gaps Between the Design Docs and Reality

Three things in the current SRS/DDD **will not work as written**. They are cheap to fix now and expensive to fix in week 9.

### 0.1 Stock YOLOv8 cannot detect our risk classes ⚠️ *load-bearing*

The SRS and DDD repeatedly specify detecting **weapons, smoking, alcohol, illicit substances**. Stock YOLOv8 (`yolov8n.pt`) is trained on the **COCO 80 classes**, which contain:

- **No gun. No cigarette. No drugs.**
- Only adjacent classes: `knife`, `scissors`, `baseball bat`, `bottle`, `wine glass`.

So the pretrained model detects approximately **none** of our stated risk taxonomy out of the box. This requires community-trained weights or our own fine-tune — a workstream that was not scheduled anywhere in the original 12-week plan.

**→ Resolved by Decision D1 (§6).**

### 0.2 Ad-spot detection is not an object-detection problem

The docs state that YOLOv8 will *"compute continuous planar area dimensions to identify prime ad placement zones (blank walls, screens)."*

YOLO detects **objects**. A blank wall is the **absence** of objects. You cannot train YOLO to detect nothing. This needs a real algorithm — see §2.2. It is currently one underspecified sentence in the SRS, yet it is arguably the most novel contribution of the project.

### 0.3 The Synopsis and SRS contradict each other on concurrency

| Document | Claim |
|---|---|
| Synopsis | *"processes multimedia files **sequentially** to optimize system memory"* |
| SRS | *"triggers **parallel** engines"*, *"concurrent write operations from audio and vision threads"* |

**Sequential is correct.** Reasons:
- Whisper and YOLO contend for the same GPU VRAM / system RAM.
- Python's GIL limits true parallelism for CPU-bound inference anyway.
- Concurrent SQLite writers produce `database is locked` errors.

**Action:** amend the SRS to say sequential. Keep `PRAGMA journal_mode=WAL` and a single writer connection regardless.

### 0.4 Minor: use faster-whisper, not stock Whisper

The DDD hardcodes `Whisper-base.en` as the `detection_model` default. Prefer **faster-whisper**:

- ~2.3–4× faster, less memory, identical accuracy (CTranslate2 backend).
- Supports `word_timestamps=True` **natively**.

That last point is not optional: our `AudioFlags` schema requires per-word `timestamp_start` / `timestamp_end`, and stock Whisper returns **segment-level** timestamps by default.

```python
segments, _ = model.transcribe("audio.wav", word_timestamps=True)
for segment in segments:
    for word in segment.words:
        print(f"[{word.start:.2f}s -> {word.end:.2f}s] {word.word}")
```

---

## 1. Architecture

Unchanged from the SRS at the layer level — Presentation → Controller → AI Engine → Data. The change is **inside the AI Engine layer**.

### 1.1 Two vision models, not one

This resolves §0.1 and §0.2 together:

| Model | Job | Why |
|---|---|---|
| **COCO YOLOv8n** | Scene occupancy — where are people, furniture, TVs, laptops? | Feeds ad-spot detection. This is what COCO is genuinely *good* at. |
| **Risk model** (community weights → later fine-tuned) | Weapons, smoking, alcohol | COCO cannot do this. See D1. |

Both run on the same sampled frame. One pass, two outputs.

---

## 2. The Two Algorithms That Need Designing

### 2.1 Audio compliance (Module 1)

```
video ──ffmpeg──► 16kHz mono WAV ──faster-whisper──► word-level transcript
                                                            │
                                              keyword/regex dictionary match
                                                            │
                                                      AudioFlags rows
```

- Extract to **16 kHz mono WAV** (what Whisper wants).
- `word_timestamps=True` → exact `timestamp_start` / `timestamp_end` per flagged word.
- Match against a **customisable dictionary** (per SRS) with word-boundary regex to avoid the Scunthorpe problem.
- Store surrounding sentence in `transcript_context`; tier severity Low/Medium/High.

> **Note:** faster-whisper reads video files directly via PyAV/ffmpeg, so a separate MoviePy extraction step is technically optional. The SRS mandates MoviePy — keep a thin `extractor.py` wrapper for document fidelity, but consider ffmpeg directly (MoviePy 2.x has breaking API changes and is heavier than needed).

### 2.2 Ad-spot detection (Module 2) — the novel bit

Per sampled frame:

1. **Occupancy mask** — run COCO YOLO, union all bounding boxes into a binary mask.
2. **Busy mask** — Canny edge density + local colour variance. Textured regions make bad ad surfaces.
3. **Free space** = `NOT occupied AND NOT busy`.
4. **Largest inscribed rectangles** in the free space — classic maximal-rectangle-in-binary-matrix DP, `O(w·h)`, fast.
5. **Classify `spot_type`** (maps directly onto our existing DDD field):
   - overlaps a `tv` / `laptop` box → **screen**
   - large uniform region, no detections → **blank wall**
   - adjacent to `dining table` → **empty desk**
6. **Score** by `area × uniformity × centrality` → our `suitability_score` field.
7. **Temporal pass** — track rectangles across consecutive frames. Persistence **≥ 5 s** → the Synopsis's *"continuous 5-second Premium Ad Spot."*

Implementable in ~200 lines of OpenCV. Defensible in a viva. This is where the marks are.

---

## 3. Repository Structure

```
specproj/
├── app/
│   └── streamlit_app.py            # Module 4 entry point
├── src/
│   ├── config.py
│   ├── db/
│   │   ├── schema.sql              # DDL straight from the DDD
│   │   ├── connection.py           # WAL, single writer, FK pragma
│   │   └── repository.py           # CRUD per table
│   ├── audio/                      # Module 1
│   │   ├── extractor.py            # → 16kHz mono WAV
│   │   ├── transcriber.py          # faster-whisper, word_timestamps=True
│   │   └── compliance.py           # dictionary/regex matching
│   ├── vision/                     # Module 2
│   │   ├── sampler.py              # OpenCV, 1 FPS
│   │   ├── detector.py             # COCO + risk model
│   │   ├── adspots.py              # free-space algorithm (§2.2)
│   │   └── tracker.py              # temporal merge → 5s spots
│   ├── pipeline/
│   │   └── orchestrator.py         # Module 3, sequential
│   └── reports/
│       └── exporter.py             # CSV / PDF
├── models/                         # weights — gitignored
├── data/                           # videos + audit.db — gitignored
├── benchmark/                      # labelled test set — see §5.2
├── tests/
├── requirements.txt
└── README.md
```

---

## 4. Build Order — Walking Skeleton First

> **The single biggest failure mode** for a 4-person, 12-week project is building four modules in isolation and integrating in week 10. Get a vertical slice running end-to-end in week 1 **with stubs**, then deepen each layer.

| Milestone | Weeks | Definition of done |
|---|---|---|
| **M0 — Skeleton** | 1 | Upload video → row in `VideoMetadata` → appears in Streamlit. **Zero AI.** |
| **M1 — Audio real** | 2–3 | Extract → faster-whisper → keyword match → `AudioFlags` populated, table renders |
| **M2 — Vision real** | 4–5 | 1 FPS sample → COCO YOLO + **community risk weights** → `VisualFlags` populated |
| **M3a — Ad spots** | 5–7 | Free-space algorithm + temporal tracking → `AdSpots` populated |
| **M3b — Fine-tune** | 7–9 | *Optional upgrade.* Custom risk model replaces community weights (see D1) |
| **M4 — Timeline UI** | 8–9 | Video player synced to clickable, colour-coded flags |
| **M5 — Reports + eval** | 10–11 | CSV/PDF export, `SystemConfig`, **accuracy benchmark** |
| **M6 — Polish** | 12 | Docs, demo, viva prep |

### 4.1 Team split

Maps cleanly onto the four modules already numbered in the SRS:

| Module | Scope | Notes |
|---|---|---|
| **Module 1** | Audio / NLP engine | Self-contained, low risk |
| **Module 2** | Vision + ad-spots | **Heaviest.** Owns the risk-model workstream — pair a second person here |
| **Module 3** | Orchestrator + DB | Blocks everyone at M0 — must land first |
| **Module 4** | Streamlit dashboard | Can build against stub data from week 1 |

*(Assign names yourselves — the module boundaries are what matter.)*

---

## 5. Risks

### 5.1 The risk model is the critical path
Mitigated by D1 (hybrid). Community weights unblock the pipeline at M2; the fine-tune becomes an *upgrade*, not a *dependency*. **If the fine-tune slips, the project still ships.**

### 5.2 The ">85% precision" claim needs a benchmark set 🔴
The SRS promises *"a precision rate greater than 85% on benchmark testing sets."* **You cannot claim this without a labelled benchmark.** Budget ~20–30 clips with hand-annotated ground truth (that's what `benchmark/` is for). Nobody ever schedules this and examiners always ask.

### 5.3 Streamlit reruns its entire script on every interaction
A long pipeline run will fight the UI. Run the pipeline as a **background thread/subprocess** and have Streamlit **poll `processed_status`** from the DB rather than blocking.

### 5.4 SQLite hygiene
`PRAGMA journal_mode=WAL` + `PRAGMA foreign_keys=ON` + a single writer connection. Even sequential, this saves pain.

### 5.5 Inherited label schemas
Community weights come with someone else's class names. Normalise them to our `risk_category` values (`Weapon`, `Substance`, `Graphic`) at the `detector.py` boundary so swapping models later doesn't ripple into the DB.

---

## 6. Decision Log

| ID | Decision | Rationale | Date |
|---|---|---|---|
| **D1** | **Hybrid risk model** — integrate community pretrained weights (Roboflow Universe / HuggingFace) at M2 so the pipeline is unblocked end-to-end; fine-tune our own YOLOv8 in weeks 7–9 as an upgrade if time allows. | Keeps the schedule safe while preserving the option for a stronger academic result. The fine-tune stops being a single point of failure. | 2026-07-11 |
| **D2** | **Sequential processing**, not parallel. | Resolves the Synopsis/SRS contradiction (§0.3). Avoids GPU contention and SQLite lock errors. | 2026-07-11 |
| **D3** | **faster-whisper** over stock Whisper. | ~2.3–4× faster, less memory, native word-level timestamps required by the `AudioFlags` schema. | 2026-07-11 |
| **D4** | **Two vision models** — COCO for occupancy/ad-spots, separate model for risk classes. | COCO is good at furniture/screens and useless at weapons. Play to its strengths. | 2026-07-11 |

---

## 6a. Risk-Weights Research (2026-08-01) — D1 revisited

D1 assumed community pretrained weights would be readily available. Investigation at
M2 shows that assumption was **partly wrong**, and the findings change the recommended
route. Recorded here because provenance and licensing are viva questions.

### Finding 1 — the framework itself is AGPL-3.0 ⚠️ *applies regardless of weights*

Ultralytics YOLOv8 is licensed **AGPL-3.0**, and Ultralytics state the licence covers
**the models produced by the training code**, not just the code. Implications:

- Academic and educational use is explicitly endorsed — fine for this project.
- AGPL is *copyleft*: publishing a derivative obliges you to publish source under the
  same terms. Our repository is currently private; if it is ever made public or the
  tool distributed, AGPL applies to it.
- **Action:** state the AGPL dependency in the final report. It is a normal, defensible
  choice for a student project, and being caught unaware of it is worse than the
  obligation itself.

### Finding 2 — Roboflow trained weights are paywalled, but the datasets are free

The D1 plan named Roboflow Universe as a weights source. In fact:

- **Downloading trained `.pt` weights requires a paid plan.** The free tier offers
  hosted inference over their API — which needs an internet round trip and therefore
  **violates the project's offline requirement outright**. This route is unusable.
- **Datasets, however, are free**, commonly under **CC BY 4.0**, and export directly in
  YOLOv8 format. Examples found: a 5,758-image weapons set, a 10,066-image weapons set,
  and a 671-image 7-class set (handgun, rifle, knife, shotgun, sword, …).

That inverts the original assumption: the *data* is available, the *weights* are not.

### Finding 3 — public weapon weights are weak and largely unusable

Every gun-detection model surveyed on HuggingFace had negligible adoption (0–13
downloads, 0 likes), meaning none has been meaningfully vetted:

| Model | Licence | Assessment |
|---|---|---|
| `Dricz/gun-obj-detection-5` | OpenRAIL | YOLOv8, `best.pt` present, but **mAP@0.5 = 0.47** and derived from a **VisDrone** (aerial) base — the wrong visual domain for creator video |
| `Dricz/gun-obj-detection` … `-4`, `-6` | Apache-2.0 | DETR, not YOLO; would need a separate inference path |
| `minkhantnaing/…`, `obelus0/…` | **none stated** | No licence means all rights reserved — **legally unusable** |

### Finding 4 — the obvious smoking model does not mean what its name suggests

`kittendev/YOLOv8m-smoke-detection` (AGPL-3.0, `best.pt` present) has a single class,
`smoke`, and was trained on a **140-image** dataset. Its self-reported **mAP@0.5 =
0.995** is implausible at that scale and points to evaluation on near-training data. It
is also ambiguous whether it detects *cigarette smoking* or *fire smoke* — a semantic
mismatch that would produce confident, wrong flags.

### Finding 5 — third-party `.pt` files execute code on load

PyTorch checkpoints are pickle-based, so loading one runs arbitrary code. Weights from
an unvetted account are executable content, not inert data. Any adopted file should
come from a named source with a stated licence.

### Consequence for D1

Community weights are **not** the low-risk unblock D1 assumed: they are variously
paywalled, unlicensed, wrong-domain, or unverifiable. Because the *datasets* are freely
licensed, **fine-tuning our own model (previously the optional M3b upgrade) is now the
stronger path** — better provenance, a clear CC BY 4.0 licence to cite, a defensible
academic contribution, and no trust problem. Meanwhile the shipped COCO weights already
provide partial, honestly-reported coverage, so the pipeline is not blocked either way.

---

## 7. Immediate Next Actions

1. **Amend the SRS**: parallel → sequential (§0.3); soften the YOLO ad-spot claim (§0.2); update `detection_model` default (§0.4).
2. **Scaffold the repo** (§3) and land **M0** — the walking skeleton — before any AI work starts.
3. **Source community risk weights** and normalise their label schema (§5.5).
4. **Start collecting the benchmark clips** (§5.2) now, in the background. It is the easiest thing to defer and the most painful to rush.

---

## 8. Document Cross-References

| Doc | What it still governs |
|---|---|
| `Synopsis.pdf` | Scope, objectives, 12-week timeline, "5-second Premium Ad Spot" definition |
| `SRS (1).pdf` | FR1–FR4, NFRs, use cases, layer architecture — **needs the §0 amendments** |
| `DDD_Final.pdf` | 6-table schema, DDL, 3NF proof, data dictionary — **still accurate, implement as-is** |
| `Project_Justification.docx` | Real-world data backing the problem statement |
