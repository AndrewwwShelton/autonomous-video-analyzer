# Fine-tune results

Two runs. Read the per-class table rather than the headline in both cases — the
averages hide the thing that actually matters each time.

---

## Run 2 — current, shipped as `models/risk_yolov8.pt`

**2026-08-07** · `yolov8n` fine-tuned for **40 epochs @ 640 px**, batch 32,
**Colab T4 GPU** · ~20 minutes · 11 classes · run 1 kept as `risk_yolov8.prev.pt`

Evaluated on the held-out validation set: 488 images, 884 instances, sourced from
the Open Images `validation` split (training came from `test` — they do not overlap).

### Overall

| Metric | Run 1 | **Run 2** | |
|---|---|---|---|
| Precision | 0.569 | **0.615** | +0.046 |
| Recall | 0.548 | **0.566** | +0.018 |
| mAP@50 | 0.566 | **0.591** | +0.025 |
| mAP@50-95 | 0.432 | **0.396** | **−0.036** |
| Inference | 88.8 ms/img | 87.5 ms/img | unchanged |

### Per class (AP@50)

| Class | Run 1 | Run 2 | Change |
|---|---:|---:|---:|
| Knife | 0.766 | **0.849** | +0.083 |
| Cocktail | 0.856 | 0.829 | −0.027 |
| Beer | 0.723 | 0.729 | +0.006 |
| Rifle | 0.749 | 0.681 | −0.068 |
| Wine glass | 0.586 | 0.589 | +0.003 |
| **Handgun** | 0.487 | **0.546** | +0.059 |
| Sword | 0.420 | **0.521** | +0.101 |
| Dagger | 0.484 | 0.494 | +0.010 |
| Kitchen knife | — | 0.478 | new |
| Bow and arrow | — | 0.445 | new |
| Shotgun | 0.339 | 0.340 | +0.001 |
| ~~Wine~~ | 0.250 | *dropped* | — |

`Handgun` — the weakest and most consequential class — improved most among the
carried-over weapons, and `Sword` gained the most overall. Two new classes landed
usable. Nothing regressed badly.

### What did NOT improve, and why it matters

**Localisation got looser: mAP@50-95 fell from 0.432 to 0.396.** Classification and
detection improved while box tightness declined. The likely cause is the training
choice made deliberately here — `scale=0.75`, well above the 0.5 default — which
teaches scale invariance at the cost of precise box regression.

For this application that is an acceptable trade. The compliance verdict turns on
*whether* a weapon is present, not on pixel-accurate geometry, and the ad-spot
occupancy mask dilates boxes anyway. It would matter for a system that cropped or
measured what it found.

**Detections on real video went down, not up.** On the one real clip available for
an A/B (Counter-Strike gameplay, 38 sampled frames):

| Confidence | Run 1 | Run 2 |
|---|---:|---:|
| 0.25 | 54 | 19 |
| 0.35 | 23 | 13 |
| 0.50 | 12 | 6 |
| 0.65 | 7 | 5 |

Run 2 is markedly more conservative here, at every threshold, despite scoring
*higher* recall on Open Images photographs. Peak confidence rose (0.77 → 0.81), so
it is more certain about fewer things. The end-to-end verdict was unchanged —
`Review`, 6 weapon detections against overlay evidence — so nothing about the
outcome regressed, but the recall drop is real and is not visible in the
validation table.

**This remains unverified on the case that drove the work**: a small, distant,
motion-blurred weapon in filmed video (the ATF firing-range clip). That video was
deleted before the A/B could run. Until it is re-tested, run 2 is *better on
photographs and more conservative on rendered game footage*, which is not the same
as better at the job.

**If it proves worse there, keep run 1** — `models/risk_yolov8.prev.pt`.

Artifacts: `training/runs/risk2/` (PR curves, confusion matrix, per-epoch CSV).

---

## Run 1 — superseded, kept as `models/risk_yolov8.prev.pt`

**2026-08-03** · `yolov8n` fine-tuned for 12 epochs @ 512 px, batch 16, CPU
(i5-1235U) · **10.8 hours** · 10 classes

| Metric | Value |
|---|---|
| Precision | 0.569 |
| Recall | 0.548 |
| mAP@50 | **0.566** |
| mAP@50-95 | 0.432 |
| Inference | 88.8 ms/image (CPU) |

| Class | Instances (train) | mAP@50 |
|---|---:|---:|
| Cocktail | 616 | 0.856 |
| Knife | 233 | 0.766 |
| Rifle | 404 | 0.749 |
| Beer | 365 | 0.723 |
| Wine glass | 421 | 0.586 |
| Handgun | 84 | 0.487 |
| Dagger | 160 | 0.484 |
| Sword | 123 | 0.420 |
| Shotgun | 169 | 0.339 |
| Wine | 1175 | **0.250** |

### The result worth reading twice

**More data did not mean better performance, and at the extremes the relationship
was inverted.** `Wine` had the *most* training data of any class — 1,175 instances —
and scored the *worst*, 0.250. `Handgun` had the *least* — 84, fourteen times fewer —
and scored 0.487.

Before training, the worry was that `Handgun` would be unlearnable and might need
merging into a generic "Firearm" class. The measurement said the opposite: **class
definition mattered more than class volume.** "Wine" in Open Images is applied to
bottles, to filled glasses and to the liquid itself, overlapping the separate
`Wine glass` and `Cocktail` classes — the model cannot draw a boundary the labels do
not contain.

That finding set the run 2 class list: `Wine` dropped, `Kitchen knife` and
`Bow and arrow` added. It also holds up — `Handgun` improved again in run 2 without
being merged into anything.

---

## Caveats that apply to both runs

**These numbers are not the project's accuracy claim.** They are measured on Open
Images photographs, not on video frames from creator content. The SRS figure must
come from the labelled benchmark clips — see [`benchmark/README.md`](../benchmark/README.md).

**The gap between the two is the point.** Run 1 scored 0.487 on `Handgun` in
photographs and then failed completely on a pistol in 720p news footage — a failure
that turned out to be inference resolution, not the model (see `context.md` §12).
A validation table cannot tell you whether the tool works on video. Only video can.
