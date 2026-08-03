# Roadmap — What's Next

> Tactical, task-level plan for the remaining work. Current state is described in
> [`context.md`](context.md); strategy and decision rationale in [`PLAN.md`](PLAN.md).
>
> Last updated: **2026-08-01** · Status: **application complete, AI engines pending**

---

## 1. Status snapshot

Roughly three weeks of build. The application is finished end-to-end — ingestion,
orchestration, database, API, a seven-screen interface, and reporting all work. What
remains is the part that makes it *intelligent*: three model-backed engines that are
currently deterministic stubs.

A useful one-line summary: **the body is built, the brains are stubbed.**

### Done

| Area | Evidence |
|---|---|
| SQLite schema (6 DDD tables), WAL, FK, config seeding | tested |
| Repository / CRUD layer | tested |
| Keyword compliance matcher (word-boundary + phrases) | tested |
| Temporal ad-spot tracker (IoU merge, ≥5 s rule) | tested |
| Sequential orchestrator, background runs, progress reporting | working |
| Audio extraction → 16 kHz mono WAV (bundled ffmpeg) | working |
| Frame sampler + thumbnailer (OpenCV) | working |
| CSV / JSON export + `AuditReports` archive | working |
| REST API — 12 endpoints incl. `/stats`, range-served media | working |
| React UI — 7 screens, 4 breakpoints, light+dark, a11y pass | working |
| Deliverables: Synopsis · SRS · DDD · **UID** · Justification | submitted |

~1,340 lines Python, ~2,140 lines frontend, 15 passing tests, 4 commits pushed.

### Not done

| Milestone | Blocking dependency | State |
|---|---|---|
| **M2** YOLO risk detection | `ultralytics` not installed; no risk weights | stub |
| **M3a** Ad-spot free-space algorithm | none — pure OpenCV work | stub |
| **M5** PDF export | `reportlab` not installed | stub |
| **M5** Accuracy benchmark | `benchmark/` does not exist | **not started** |
| Orchestrator real path (`demo=False`) | — | ✅ working (audio real) |

---

## 2. What changed since the last update

- **M4 (interface) was completed out of order**, ahead of M1–M3. This was driven by the
  Stage-4 UID document deadline and was the right call — the document needed a real
  interface to photograph, and the UI is now fixed while the engines land behind it.
- The interface grew from 4 screens to **7** (Dashboard and Analytics added), gained a
  `/api/stats` aggregate endpoint, four responsive breakpoints, an accessibility pass,
  and inline validation.
- **The benchmark still has not been started.** It was flagged as "start now, in the
  background" in the previous revision and did not happen. See §4.

---

## 3. Remaining milestones

Each milestone swaps one stub for a real engine. Because demo mode keeps the pipeline
running throughout, every milestone is independently shippable — there is no
integration cliff at the end.

### ~~M1 — Audio engine~~ ✅ **DONE** (2026-08-01)

Real speech-to-text via faster-whisper. Verified against a generated speech clip:
the transcript was word-perfect, timestamps accurate, and all three planted dictionary
terms flagged at the right severities (`damn`/Low, `hell`/Low, `gun`/High) with
`detection_model=faster-whisper-base.en` recorded for provenance.

- [x] `faster-whisper` installed and promoted in `requirements.txt`
- [x] `FasterWhisperTranscriber` — lazy load, `word_timestamps=True`, VAD filter,
      weights cached under `models/`
- [x] Real branch in `orchestrator.process_video()`, engine chosen **per stage**
- [x] `analysis_mode` setting (demo | real) wired through config, API and Settings UI
- [x] Silent videos degrade gracefully — no audio flags, run still completes
- [x] 7 new tests (22 total, all passing)

Notes for later: weights download once (~140 MB, needs network); inference is offline
thereafter. `base.en` transcribed a 15 s clip in roughly 20 s on CPU — worth
re-measuring on the demo machine before the review, and `tiny.en` is available if
speed matters more than accuracy.

### M2 — Vision risk detection · ~4–5 days · **highest risk**

Replace `DemoDetector` with real object detection. Per decision D1, integrate community
pretrained weights first; a custom fine-tune is a later upgrade, not a dependency.

- [ ] **Source community risk weights** (Roboflow Universe / HuggingFace) covering
      gun / knife / cigarette / alcohol → `models/risk_yolov8.pt`
- [ ] Confirm the licence permits academic use; record the source in `PLAN.md`
- [ ] `pip install ultralytics`
- [ ] Implement `YoloRiskDetector.detect()`
- [ ] Extend `RISK_CATEGORY_MAP` to normalise the model's actual class names into our
      `Weapon` / `Substance` / `Graphic` vocabulary at the detector boundary
- [ ] Apply the confidence threshold from `SystemConfig`

**Done when:** a clip containing a knife, bottle or cigarette yields correct
`VisualFlags`, and the verdict flips to `Restricted` when a weapon appears.

> **Start the weights search first, before writing any code.** It is the only task in
> the project with an external dependency that can stall, and everything in M2 waits on
> it. Pair a second person here.

### M3a — Ad-spot free-space algorithm · ~5–7 days · ★ where the marks are

Replace `DemoAdSpotFinder` with the real per-frame algorithm. The temporal tracker that
merges candidates into ≥5 s spots is already real and tested — this milestone only
produces the per-frame candidates it consumes.

Implement `find_ad_spot_candidates()` (spec in its docstring and `PLAN.md` §2.2):

- [ ] COCO YOLOv8n pass for scene occupancy → union boxes into an occupancy mask
- [ ] Busy mask — Canny edge density + local colour variance
- [ ] Free space = `NOT occupied AND NOT busy`
- [ ] Largest inscribed rectangles (maximal-rectangle DP, `O(w·h)`)
- [ ] Classify `spot_type` — screen / blank wall / empty desk
- [ ] Score `area × uniformity × centrality` → `suitability_score`

**Done when:** on real footage, stable blank surfaces persisting ≥5 s become `AdSpots`
with plausible geometry, and short-lived surfaces are correctly discarded.

> This is the project's novel contribution. Detecting the *absence* of objects is not an
> object-detection problem, which is exactly what makes it defensible in the viva.
> Budget time accordingly and keep notes on the algorithm design as you go.

### M5 — Reports and evaluation · ~1 week · **schedule risk**

**PDF export**
- [ ] `pip install reportlab`; implement `exporter.export_pdf()` from the `_gather()` dict
- [ ] Enable the PDF option on the Reports screen (currently disabled)

**Accuracy benchmark** — harness ✅ done, labelling ⏳ outstanding
- [x] `benchmark/` harness: matching rules, metrics, CLI, label validator
- [x] Isolation — runs against a throwaway database, never the real library
- [x] Stubbed engines excluded from the headline figure automatically
- [x] Small-sample guard — prints `NOT YET PUBLISHABLE` below 30 events / 10 real clips
- [x] Synthetic fixture generator for harness validation (not for the claim)
- [x] 18 tests covering the matching rules
- [ ] **Collect and label 20–30 real clips** ← the remaining work
- [ ] Record results; if precision falls below 85 %, tune thresholds, dictionary or
      model **before** repeating the claim

Current reading: audio 100 % precision / 100 % recall, but on only 4 events from a
single synthetic clip — correctly reported as not publishable. Vision is excluded
until M2 lands.

### ~~M3b — Custom fine-tune~~ ✅ **first run done** (2026-08-03)

Promoted from optional and completed early: the weights research (`PLAN.md` §6a) found
every community candidate paywalled, unlicensed, wrong-domain or unverifiable, so
training our own turned out to be the *lower*-risk route.

- [x] Open Images V7 subset, CC BY 4.0 — 1,516 train / 500 val images, 10 classes
- [x] `download_dataset.py` (isolated env) · `prune_classes.py` · `train.py`
- [x] Fine-tuned `yolov8n`, 12 epochs — **mAP@50 0.566**, weights in `models/`
- [x] Verified end-to-end: rifle + shotgun detected on a held-out image, verdict
      correctly flipped to Restricted
- [ ] **Quality run on a GPU** — 12 epochs on CPU took 10.8 hours; 40+ epochs at
      640 px is ~20 minutes on a free Colab T4
- [ ] Resolve the `Wine` class before adding any more images

Full numbers: [`training/RESULTS.md`](training/RESULTS.md).

**The finding that matters:** more data did not mean better performance. `Wine` had the
most training data (1,175 instances) and scored *worst* (mAP@50 0.250); `Handgun` had
the least (84) and scored nearly double (0.487). `Wine` is semantically ambiguous in
Open Images — applied to bottles, filled glasses and the liquid — and overlaps the
separate `Wine glass` and `Cocktail` classes. **Fix ambiguous classes before adding
images.**

Coverage now includes firearms and blades alongside alcohol. `Graphic` remains
uncovered, and **smoking is still uncovered by any reputable source found** — Open
Images has no cigarette or tobacco class.

### M6 — Polish and viva preparation · ~2–3 days

- [ ] Apply the pending SRS amendments (below)
- [ ] Rehearse `demo_setup.py` + `RUN_DEMO.bat` on a clean machine
- [ ] Update the presentation with real results and benchmark numbers
- [ ] Re-read `context.md` / `PLAN.md` against the final code

---

## 4. Risks

### 🟠 Benchmark labelling (harness now built)

The SRS promises *"a precision rate greater than 85 % on benchmark testing sets."* The
harness that produces that figure is now complete and tested — **but it has almost
nothing to measure.** One synthetic clip with four labelled events is not evidence.

The risk has shifted from "no harness" to "no data", which is the better problem to
have, but the slow half:

- Labelling 20–30 clips is manual work that cannot be compressed at the end.
- It can proceed **entirely in parallel** with M2 and M3a — nothing blocks it.
- The harness refuses to publish a figure until the evidence base is adequate, so
  under-labelling will be caught rather than quietly shipped.

**Action:** label roughly one clip per sitting alongside the M2 work. See
`benchmark/README.md` for the format and the rules that keep the numbers honest.

### 🟠 M2 has the only external dependency

Community weights must be found, licence-checked and downloaded. If nothing suitable
exists, the fallback is a fine-tune — which is a multi-week job that was explicitly
descoped to an optional upgrade. Search early so there is time to react.

### 🟢 Retired risks

- *Integration cliff* — avoided. Demo mode has kept the pipeline running end-to-end from
  day one, so each engine drops into a working system.
- *Streamlit rerun contention* — obsolete. Replaced by FastAPI with background tasks.
- *ffmpeg dependency* — solved by the bundled `imageio-ffmpeg` binary.

---

## 5. Suggested order

| # | Work | Effort | Notes |
|---|---|---|---|
| ~~0~~ | ~~M1 — audio engine~~ | ✅ done | demo→real swap pattern now proven |
| 0 | **Start collecting benchmark clips** | ongoing | background task, start today |
| 0 | **Start sourcing M2 weights** | ongoing | external dependency, start today |
| 1 | M2 — vision detection | 4–5 days | needs weights in hand |
| 2 | M3a — ad-spot algorithm | 5–7 days | the novel contribution |
| 3 | M5 — PDF + benchmark evaluation | ~1 week | labelling should already be underway |
| 4 | M3b — fine-tune | optional | only with spare time |
| 5 | M6 — polish and viva prep | 2–3 days | last |

**Roughly 3–4 weeks of remaining work**, excluding the optional fine-tune.

**Immediate next action:** start the two background tasks above, then M2 — beginning
with the weights search, not the code.

M1 established the pattern the remaining engines follow: implement the engine behind
its existing contract, select it per stage in the orchestrator, keep the demo twin
working, and report which engine produced each result.

---

## 6. Pending SRS amendments (from `PLAN.md` §0)

Documentation fixes that keep the design documents consistent with what was built:

- [ ] **Parallel → sequential** processing (§0.3) — the implementation is sequential
- [ ] **Soften the YOLO ad-spot claim** (§0.2) — ad-spots use a free-space algorithm,
      not object detection
- [ ] **`detection_model` default** → faster-whisper (§0.4)

Optionally worth adding, since the UID document now states it: authentication is
deliberately out of scope for an offline single-user tool.

---

## 7. Backlog (unscheduled)

- Integration tests for the FastAPI routes (currently only unit tests on pure logic)
- Library search filters client-side only — acceptable at current scale
- Progress registry is process-local — fine for a single-user desktop tool
- A `.gitattributes` to normalise CRLF/LF across machines
