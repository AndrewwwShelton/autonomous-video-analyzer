# Roadmap — What's Next

> Tactical, task-level plan for the remaining work. Current state is described in
> [`context.md`](context.md); strategy and decision rationale in [`PLAN.md`](PLAN.md).
>
> Last updated: **2026-08-07** · Status: **every engine built and validated on real
> video; the accuracy claim is still unevidenced**

---

## 1. Status snapshot

Every milestone is built. The pipeline transcribes, detects, finds ad surfaces,
distinguishes rendered overlays from filmed content, and reports — and all of it has
now been exercised against **real footage**, not only synthetic clips.

**The one-line summary is unchanged and is the whole remaining problem: the tool
works, and there is no evidence for how well.** The SRS claims ">85% precision"; the
benchmark that would substantiate it has **zero labelled clips**.

### Done

| Area | Evidence |
|---|---|
| SQLite schema (6 DDD tables + 2 migrations), WAL, FK, config seeding | tested |
| Repository / CRUD layer | tested |
| Keyword compliance matcher (word-boundary + phrases) | tested |
| **M1** Audio — faster-whisper, word timestamps, graceful on silent video | tested |
| **M2** Vision — COCO + fine-tuned risk model, multi-scale inference | tested |
| **M3a** Ad-spot free-space algorithm ★ | tested |
| **M3b** Fine-tune — run 1 shipped, run 2 trained and **rejected** on evidence | measured |
| **M5** CSV / JSON / PDF export + `AuditReports` archive | tested |
| **M6** Persistent-overlay detection ★ + three-state verdict | tested |
| **M7** Real-video hardening — multi-scale, grouped names, provenance, relative stability | tested |
| Temporal ad-spot tracker (IoU merge, ≥5 s rule) | tested |
| Sequential orchestrator, background runs, per-stage engine reporting | working |
| REST API — 15 endpoints incl. `/stats`, `/vision-coverage` | smoke-tested |
| React UI — 7 screens, 4 breakpoints, light+dark, a11y pass | working |
| Benchmark harness with stub-exclusion and small-sample guards | tested |
| Deliverables: Synopsis · SRS · DDD · **UID** · Justification | submitted |

**169 passing tests** across 12 files.

### Not done

| Item | State |
|---|---|
| **Benchmark labelling — 0 of 20 clips** | 🔴 the blocker |
| UID screenshots predate five interface changes | 🟠 deliverable drift |
| SRS amendments (`PLAN.md` §0) | 🟠 pending |
| Fine-tune run 3 | optional, and see §4 |

---

## 2. What changed since the last update

- **M6 and M7 landed**, neither of them planned. M6 came from asking what happens to
  a Call of Duty video; M7 came from running four real clips and finding that *every
  one broke something*.
- **The tool was validated on real footage for the first time.** Until then everything
  had been verified against generated video, which hid several wrong defaults.
- **Run 2 of the fine-tune was trained and rejected.** It beat run 1 on every headline
  metric and then detected a real pistol zero times where run 1 found it thirteen
  times. Run 1 is restored. See `training/RESULTS.md`.
- **The keyword dictionary was rebuilt around a severity contract** after it was
  measured flagging "we were shooting all day" as High — which alone restricts a
  video.
- **The benchmark still has no labelled clips.** Flagged as the top risk in the last
  four revisions of this document.

---

## 3. Remaining work

### 3.1 Label 20 benchmark clips 🔴 **the blocker**

Everything else on this page is polish. This is the only item standing between the
project and a defensible accuracy claim.

The tooling is finished — intake CLI, browser labeller, scoring harness, honesty
guards. What remains is manual and needs a person.

```bash
python benchmark/intake.py <video> --start 1:10 --end 2:00 --source "where it came from"
# then label in benchmark/labeller.html   (browser, no server needed)
python benchmark/status.py                # progress against the gates
python benchmark/evaluate.py              # once the gates pass
```

**Gates before any number may be published** (enforced by the runner, not by
discipline): ≥10 real clips, ≥30 labelled events, and some clean clips carrying no
violations so false positives are measurable.

Rules that keep the result meaningful:

- **Label from the source, never from the tool's output.** Grading a model against
  its own predictions is circular and worthless.
- Include clips that should produce **nothing**. Precision is unmeasurable without
  them, and precision is the claim.
- Prefer real creator footage over clean studio speech. The synthetic clip is a
  best-case floor, and it is excluded from the evidence base for that reason.

**Do this after the dictionary is settled** (§3.2) — measuring precision against a
vocabulary you are about to change wastes the labelling effort.

**Estimate:** 1–2 evenings for 20 clips.

### 3.2 Dictionary is settled — verify before labelling ✅ *done, re-check first*

The vocabulary was rebuilt around a rule: **High severity restricts a video on its
own, so it is reserved for terms that cannot mean anything else.** Ambiguous words sit
at Medium or Low, where they are surfaced without deciding the outcome.

Re-run the false-positive check before labelling starts, and add any new terms *then*
rather than mid-way through:

```bash
python -m pytest tests/test_repository.py -q -k "severity or vocabulary"
```

### 3.3 Re-shoot the UID screenshots 🟠

All 14 captures date from **2026-07-29**. The interface has since gained: the original
logo (2026-08-03), the three-state verdict, the verdict-reasoning banner, grouped
finding names, the detection-model column, and the demo-mode banner.

If the UID is being re-submitted or shown at the viva, the captures no longer match
the product. `docs/SCREENSHOT_CHECKLIST.md` lists the shots; roughly 30 minutes.

### 3.4 SRS amendments 🟠

See §6 — four documented gaps between the design documents and what was built. The
concurrency one is a contradiction *between two of your own submitted documents*.

### 3.5 Fine-tune run 3 — optional, and be careful

Only worth attempting with a specific hypothesis. Run 2's failure (see §4) is the
evidence for what *not* to do.

- Revert `scale` to the default 0.5. It was raised to 0.75 to fix a scale problem and
  is the prime suspect for the collapse.
- **Change one thing at a time**, and evaluate on video before believing the table.
- Gate the result on the ATF clip and the Counter-Strike clip, not on mAP.

---

## 4. Risks

| Risk | Severity | Mitigation |
|---|---|---|
| **No labelled clips, so no defensible accuracy claim** | 🔴 high | §3.1. The benchmark refuses to publish a number below the gates, so the risk is visible rather than silent |
| **Validation metrics do not predict behaviour on video** | 🔴 proven twice | Run 1 scored 0.487 on Handgun and missed a real pistol entirely; run 2 scored *better* and missed it completely. Always gate on video |
| Weapon class labels are unreliable | 🟠 medium | Findings report as "Handheld weapon" with the raw class beneath. The category is reliable; the class is not |
| Overlay detector may fire on watermarks and lower-thirds | 🟠 medium | By design — it detects overlays, not games. Region count and coverage are reported so a lone corner region reads as a watermark |
| Smoking and drugs are uncovered visually | 🟠 medium | Open Images has no such class (verified against all 601). Covered in the audio dictionary instead; stated as out of scope |
| UID/SRS drift from the built system | 🟠 medium | §3.3, §3.4 |
| Demo mode mistaken for real output | 🟢 handled | Seven honesty guards, incl. per-flag engine provenance and a page banner |

---

## 5. Suggested order

1. **Re-check the dictionary** (§3.2) — minutes, and it gates the next step
2. **Label 20 clips** (§3.1) — the only thing that changes what the project can claim
3. **Run the benchmark**, put the real figure in the report, and amend the SRS claim
   if the measurement disagrees with ">85%"
4. **Re-shoot UID screenshots** (§3.3) if that document is still live
5. **SRS amendments** (§3.4)
6. Run 3 of the fine-tune (§3.5) only if there is time and a hypothesis

---

## 6. Pending SRS amendments (from `PLAN.md` §0)

| # | Gap | Amendment |
|---|---|---|
| 0.1 | SRS assumes stock YOLOv8 detects weapons, smoking and drugs | It detects none of them. Describe the fine-tune, its 11 classes, and its measured limits |
| 0.2 | Ad-spot detection described as an object-detection task | A blank wall is the *absence* of objects. Describe the free-space algorithm — it is the project's novel contribution and deserves better than one sentence |
| 0.3 | **Synopsis says "sequentially", SRS says "parallel threads"** | Sequential is correct and is what was built. This is a contradiction between two submitted documents |
| 0.4 | DDD hardcodes `Whisper-base.en` | faster-whisper, for native word-level timestamps that `AudioFlags` requires |
| — | Licensing is not stated anywhere | Ultralytics YOLOv8 is **AGPL-3.0**, and it covers the trained weights, not just the code |
| — | ">85% precision" is unevidenced | Either substantiate it from the benchmark or soften it to a measured figure |

---

## 7. Backlog (unscheduled)

- Ad-spot suppression over detected overlay regions — a HUD is stable and uncluttered,
  so it scores well as an advertisement surface while being the worst possible place
  to put one
- Batch analysis across the whole library
- Export the audit timeline as an image for the report
- Per-video content-type declaration (Gaming / Education / News) to complement the
  overlay heuristic, mirroring how platforms actually self-certify
