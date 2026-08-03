# Roadmap — What's Next

> Tactical, task-level plan for the remaining work. Current state is described in
> [`context.md`](context.md); strategy and decision rationale in [`PLAN.md`](PLAN.md).
>
> Last updated: **2026-08-03** · Status: **every AI engine is real; evidence outstanding**

---

## 1. Status snapshot

The pipeline is complete. Audio transcribes, vision detects, ad-spots are found by the
free-space algorithm, and all of it lands in the database and the interface.

The one-line summary has changed: **the tool works — what it lacks is proof.** The SRS
claims ">85% precision" and the benchmark that would substantiate it still has zero
labelled clips.

### Done

| Area | Evidence |
|---|---|
| SQLite schema (6 DDD tables), WAL, FK, config seeding | tested |
| Repository / CRUD layer | tested |
| Keyword compliance matcher (word-boundary + phrases) | tested |
| **M1** Audio — faster-whisper, word timestamps, graceful on silent video | tested |
| **M2** Vision — COCO + fine-tuned risk model, 13 risk labels | tested |
| **M3a** Ad-spot free-space algorithm ★ | tested |
| **M3b** Fine-tune — Open Images, mAP@50 0.566 | measured |
| Temporal ad-spot tracker (IoU merge, ≥5 s rule) | tested |
| Sequential orchestrator, background runs, per-stage engine reporting | working |
| REST API — 13 endpoints incl. `/stats`, `/vision-coverage` | working |
| React UI — 7 screens, 4 breakpoints, light+dark, a11y pass | working |
| Benchmark harness with stub-exclusion and small-sample guards | tested |
| Deliverables: Synopsis · SRS · DDD · **UID** · Justification | submitted |

84 passing tests.

### Not done

| Item | State |
|---|---|
| **Benchmark labelling — 0 of 20 clips** | 🔴 the blocker |
| ~~**M5** PDF export~~ | ✅ done |
| GPU quality run for the fine-tune | optional |
| SRS amendments (PLAN §0) | pending |
| Resolve the ambiguous `Wine` class | pending |

---

## 2. What changed since the last update

- **M1, M2, M3a and M3b all landed.** The last stub of substance is PDF export.
- **M3b was promoted from optional and done early.** The weights research
  (`PLAN.md` §6a) found every community candidate paywalled, unlicensed,
  wrong-domain or unverifiable, so training our own became the *lower*-risk route.
- **M3a is complete** — the novel contribution is built and verified, not just planned.
- **The benchmark still has no labelled clips.** Flagged as the top risk in the
  previous two revisions. It is now the only thing standing between the project and a
  defensible accuracy claim.

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

### ~~M2 — Vision risk detection~~ ✅ **DONE** (2026-08-01 → 08-03)

Real object detection over sampled frames. Two models per decision D4: COCO for scene
understanding and occupancy, a fine-tuned model for the risk taxonomy COCO cannot see.

- [x] `ultralytics` installed; COCO weights cached in `models/`
- [x] `YoloDetector` — lazy load, several weight files at once, raw detections with
      risk classification as a separate step
- [x] `RISK_CATEGORY_MAP` normalises class names at the detector boundary
- [x] Confidence threshold honoured from `SystemConfig`
- [x] `/api/vision-coverage` reports what the loaded weights can actually find,
      surfaced on the Settings screen
- [x] Community weights route abandoned after research — see `PLAN.md` §6a — and
      replaced by our own fine-tune (M3b)

**Coverage:** 13 risk labels — handgun, rifle, shotgun, dagger, sword, knife,
scissors, baseball bat, beer, wine, cocktail, wine glass, bottle. `Graphic` remains
uncovered, and **smoking is uncovered by any reputable source found**.

Verified end-to-end: a held-out image containing a rifle and shotgun produced both
detections and flipped the verdict to `Restricted`.

### ~~M3a — Ad-spot free-space algorithm~~ ✅ **DONE** (2026-08-03) ★

The project's novel contribution. Detecting the *absence* of objects is not an
object-detection problem, so this is the one component that could not be solved by
pointing another pretrained model at it.

Implemented in `src/vision/adspots.py`:
- Occupancy mask from the detection boxes; **busy mask** from Canny edge density
  *and* local intensity variance (each catches what the other misses — hard
  structure versus soft clutter)
- Free space = NOT occupied AND NOT busy
- **Maximal rectangle in a binary matrix**, histogram/monotonic-stack method, O(w·h);
  top-K disjoint rectangles by greedy erase
- Classification from neighbouring detections (screen / empty desk / blank wall)
- Multiplicative score over area × uniformity × centrality, so a rectangle must be
  reasonable on every axis
- Runs at ~320 px working width: the DP is linear in pixel count, so this is ~30×
  cheaper with no practical loss for ad geometry

Wired into the orchestrator as **one inference pass, two consumers** (decision D4) —
the same detections feed risk flags and the occupancy mask, so frames are decoded and
models run once.

**Verified end-to-end** on a clip with a flat wall on one side and random texture on
the other: found a single 13-second `blank_wall` spot at x≥453, clear of the 403 px
textured region and stopping above a moving figure. 27 tests cover the geometry.

### M5 — Reports and evaluation · ~1 week · **schedule risk**

**PDF export** ✅ **DONE** (2026-08-03)
- [x] `reportlab` renderer in `src/reports/pdf_report.py` — verdict banner, summary,
      drawn three-lane timeline, per-category tables, provenance footer
- [x] Enabled and defaulted on the Reports screen; PDF export on the video detail page
- [x] Demo-generated reports say so in bold, so they cannot pass as an audit result
- [x] 11 tests, including pagination and tolerance of missing optional fields

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
| ~~—~~ | ~~M1 audio · M2 vision · M3a ad-spots · M3b fine-tune~~ | ✅ done | every engine is real |
| **1** | **Label 20 benchmark clips** | ~1–2 weeks elapsed | 🔴 **the only real blocker** |
| 2 | M5 — PDF export | ~half a day | `reportlab`, render the `_gather()` dict |
| 3 | Run the benchmark, record the figure | ~1 hour | needs step 1 |
| 4 | SRS amendments (§6) | ~1 hour | keeps the documents honest |
| 5 | GPU quality run for the fine-tune | ~30 min | optional; 0.566 → likely better |
| 6 | M6 — polish and viva prep | 2–3 days | last |

**Roughly 2–3 weeks of remaining work**, and almost all of it is step 1 — which is
manual labelling, not engineering.

**Immediate next action:** label clips. Nothing else is blocked, and nothing else
changes the fact that the accuracy claim currently has no evidence behind it.

The engines established a repeatable pattern worth keeping if anything else is added:
implement behind the existing contract, select per stage in the orchestrator, keep the
demo twin working, and report which engine produced each result.

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
