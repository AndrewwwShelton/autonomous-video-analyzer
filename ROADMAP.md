# Roadmap — What's Next

> Tactical, task-level plan for the remaining work. Assumes the current state described
> in [`context.md`](context.md) (**M0+ complete**). Strategy and decision rationale live
> in [`PLAN.md`](PLAN.md); this file is the checklist that turns each stub into a real
> engine and gets the project review-ready.
>
> Last updated: 2026-07-22

---

## Where we are

The walking skeleton is done and runs end-to-end offline: upload → analyze → timeline →
report, with a full YouTube-Studio web UI. Four things are still deterministic **demo
stubs**: audio transcription, visual risk detection, the ad-spot free-space algorithm,
and PDF export. Turning each into the real thing is the remaining work, plus the
evaluation benchmark and demo polish.

**Sequencing principle:** the pipeline already works, so we deepen one engine at a time
and verify each against the same UI. No big-bang integration.

---

## Milestone M1 — Audio engine (real)

**Goal:** replace `DemoTranscriber` with real speech-to-text; the compliance matcher and
DB are already real, so only the transcriber changes.

**Prerequisites**
- [ ] `pip install faster-whisper` (add to `requirements.txt`, uncomment the M1 line).
- [ ] First run downloads the model weights (~140 MB for `base.en`) — cache to `models/`.

**Tasks**
- [ ] Implement `FasterWhisperTranscriber.transcribe()` in `src/audio/transcriber.py`
      per its docstring sketch (`word_timestamps=True`, flatten segments → `WordStamp`).
- [ ] Wire the real transcriber into `orchestrator.py` behind the existing `demo` flag
      (add a `demo=False` real path; keep demo mode working).
- [ ] Use `extractor.extract_audio()` (already real) to make the 16 kHz mono WAV first.
- [ ] Respect the `whisper_model` SystemConfig value (Settings page already sets it).
- [ ] Handle videos with no/failed audio track gracefully → status `failed`, clear error.

**Acceptance**
- A real uploaded clip with known profanity produces correct `AudioFlags` with accurate
  per-word timestamps, visible on the timeline and audio table.
- Demo mode still runs with no model present.

**Effort:** ~2–3 days. **Owner:** Module 1.

---

## Milestone M2 — Vision risk detection (real)

**Goal:** replace `DemoDetector` with a real object detector for the risk taxonomy
(weapons, smoking, alcohol). **Decision D1:** community weights first, not a fine-tune.

**Prerequisites**
- [ ] `pip install ultralytics`.
- [ ] Source community risk weights (Roboflow Universe / HuggingFace) — a model that
      actually covers gun/knife/cigarette/alcohol. Save to `models/risk_yolov8.pt`.
- [ ] Confirm the weights' license permits academic use; record the source in PLAN.md.

**Tasks**
- [ ] Implement `YoloRiskDetector.detect()` in `src/vision/detector.py` per its sketch.
- [ ] Extend `RISK_CATEGORY_MAP` to cover the community model's actual class names →
      our `Weapon`/`Substance`/`Graphic` vocabulary (label normalization at the boundary,
      PLAN.md §5.5).
- [ ] Feed `sampler.sample_frames()` (already real, 1 FPS) into the detector.
- [ ] Apply the `detection_confidence_threshold` from SystemConfig.
- [ ] Wire into the orchestrator's real path.

**Acceptance**
- A clip containing a knife/bottle/cigarette yields correct `VisualFlags` with sane
  bounding boxes and confidences; verdict flips to `Restricted` when a weapon appears.

**Effort:** ~4–5 days (the heaviest module — pair two people). **Owner:** Module 2.

---

## Milestone M3a — Ad-spot free-space algorithm (real) ★ the novel bit

**Goal:** replace `DemoAdSpotFinder` with the real per-frame algorithm. The temporal
tracker (`tracker.py`) that merges candidates into ≥5 s spots is **already real and
tested** — this milestone only produces the per-frame candidates it consumes.

**Tasks** (implement `find_ad_spot_candidates()` in `src/vision/adspots.py`, spec in its
docstring / PLAN.md §2.2)
- [ ] Add a **COCO YOLOv8n** pass (Decision D4) for scene occupancy — union all boxes
      into a binary occupancy mask.
- [ ] Build a **busy mask** — Canny edge density + local color variance.
- [ ] Free space = `NOT occupied AND NOT busy`.
- [ ] **Largest inscribed rectangles** via maximal-rectangle-in-binary-matrix DP.
- [ ] Classify `spot_type`: overlaps tv/laptop → `screen`; large uniform → `blank_wall`;
      adjacent to dining table → `empty_desk`.
- [ ] Score `area × uniformity × centrality` → `suitability_score`.
- [ ] Feed candidates into the existing `merge_candidates()`.

**Acceptance**
- On real footage, stable blank surfaces persisting ≥5 s become `AdSpots` with plausible
  boxes and types; short-lived surfaces are correctly dropped (tracker already enforces).

**Effort:** ~5–7 days. **Owner:** Module 2. *This is where the viva marks are — budget
accordingly.*

---

## Milestone M3b — Custom fine-tune (optional upgrade)

**Goal:** replace community risk weights with a fine-tuned YOLOv8 for better accuracy.
**Strictly optional (D1)** — if it slips, the project still ships on community weights.

**Tasks**
- [ ] Assemble/annotate a risk-class dataset (Roboflow).
- [ ] Fine-tune YOLOv8, evaluate against the M5 benchmark, swap weights only if it wins.

**Effort:** ~1–2 weeks if attempted. **Owner:** Module 2. **Gate:** only after M3a ships.

---

## Milestone M5 — Reports + evaluation

**Goal:** finish report export and produce the accuracy numbers the SRS promises.

**PDF export**
- [ ] `pip install reportlab`; implement `exporter.export_pdf()` from the `_gather()` dict
      (summary header, verdict, per-category tables, ad-inventory total).
- [ ] Enable the PDF option in the Reports page (currently disabled).

**Benchmark & accuracy (SRS claims >85% precision — PLAN.md §5.2)** 🔴
- [ ] Collect ~20–30 short clips with **hand-labeled ground truth** for audio + visual
      flags → `benchmark/`.
- [ ] Write an eval script: run the pipeline, compare to ground truth, report
      precision/recall per category.
- [ ] Record results; if precision <85%, tune thresholds/dictionary/model before claiming.

**Effort:** ~1 week. **Owner:** Module 1 + 2 (benchmark), Module 3 (PDF). *Start
collecting clips NOW in the background — it's the easiest thing to defer and the most
painful to rush.*

---

## Milestone M6 — Polish & viva prep

- [ ] Amend the **SRS** for the §0 gaps (see below) so docs match the build.
- [ ] Finalize the demo script and rehearse `demo_setup.py` + `RUN_DEMO.bat` on a clean
      machine.
- [ ] README/context/PLAN cross-checked against the code.
- [ ] Update `Presentation_I_AdSafe.pptx` with real result screenshots + benchmark numbers.

---

## Cross-cutting: pending SRS amendments (PLAN.md §0)

These are documentation fixes, cheap now, that keep the design docs honest:
- [ ] **Parallel → sequential** processing (§0.3) — the code is sequential; the SRS says
      parallel.
- [ ] **Soften the YOLO ad-spot claim** (§0.2) — ad-spots use a free-space algorithm, not
      object detection.
- [ ] **detection_model default** → faster-whisper (§0.4) — already reflected in the
      schema default; align the SRS prose.

---

## Backlog / smaller improvements (nice-to-have, unscheduled)

- Search box currently filters the content table client-side only — fine for now.
- No auth (single-user desktop tool by design — an NFR, not a gap).
- Progress registry is in-memory/process-local — acceptable for one user; note it if the
  deployment model ever changes.
- Consider a `.gitattributes` to normalize CRLF/LF across machines.
- Add a couple of integration tests for the FastAPI routes (currently only unit tests on
  the pure-logic modules).

---

## Suggested order & rough calendar

Following the PLAN.md milestone weeks, adjusted to where we actually are:

| Order | Milestone | Rough effort | Blocking? |
|---|---|---|---|
| 1 | M1 audio | 2–3 days | no |
| 2 | M2 vision (community weights) | 4–5 days | needs weights sourced |
| 3 | M3a ad-spots | 5–7 days | needs COCO model (trivial) |
| 4 | M5 PDF + benchmark | ~1 week | benchmark collection runs in parallel from now |
| 5 | M3b fine-tune | optional | gated on M3a + spare time |
| 6 | M6 polish + SRS amendments | few days | last |

**Immediate next action:** pick M1 and implement `FasterWhisperTranscriber` — it's the
smallest, lowest-risk real engine and proves the demo→real swap pattern for the rest.
