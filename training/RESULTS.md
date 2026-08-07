# Fine-tune results

Two runs. **Run 1 is the shipped model**; run 2 scored better on every headline
metric and was rejected on evidence. Read the per-class tables rather than the
averages — and read the video results rather than either.

> ## Outcome: run 2 rejected, run 1 restored
>
> Run 2 improved mAP@50 (0.566 → 0.591), precision, recall, and `Handgun`
> specifically (0.487 → 0.546). It was then tested on the clip that prompted the
> retrain — an ATF firing-range video, pistol at arm's length in 720p — and
> **detected the weapon zero times** where run 1 found it 13 times.
>
> | conf | run 1 | run 2 |
> |---|---:|---:|
> | 0.20 | 43 (Knife) | 5 — as **Beer** |
> | 0.35 | 20 (Knife) | 1 — as Beer |
> | **0.50** | **13 (Knife)** | **0** |
>
> Running the risk model alone with no threshold, its strongest response anywhere
> on those frames was `Beer` at 0.464; every weapon class collapsed — `Handgun`
> 0.112, `Knife` 0.086. The weapon had become invisible to it.
>
> **A validation set drawn from the training distribution cannot tell you whether
> a model works.** Run 2 is better at Open Images photographs and worse at the job.
> Files: `risk_yolov8.pt` is run 1; run 2 is kept as `risk_yolov8.run2.pt`.
>
> **The likely cause is a change made to help.** `scale=0.75` was set well above the
> 0.5 default specifically to teach scale invariance, because the run 1 failure
> looked like a scale problem. Aggressive scale jitter plus 40 epochs appears to
> have specialised the model onto Open Images' photographic domain rather than
> generalising it. A third run should revert `scale` to the default and change one
> thing at a time.

---

## Run 2 — rejected, kept as `models/risk_yolov8.run2.pt`

**2026-08-07** · `yolov8n` fine-tuned for **40 epochs @ 640 px**, batch 32,
**Colab T4 GPU** · ~20 minutes · 11 classes

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

On its own that would have been an acceptable trade — the verdict turns on whether a
weapon is present, not on pixel-accurate geometry. Read next to what follows, it is
better understood as the first sign that the scale jitter had done something other
than what it was meant to.

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

**On the case that drove the work it failed outright** — see the outcome box at the
top of this file. The ATF firing-range clip, a pistol at arm's length in 720p, went
from 13 detections under run 1 to **zero**. That is why run 1 is the shipped model.

Artifacts: `training/runs/risk2/` (PR curves, confusion matrix, per-epoch CSV).

---

## Run 1 — **shipped**, `models/risk_yolov8.pt`

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
`Bow and arrow` added. It held up in the sense that mattered — `Handgun` improved
again in run 2 without being merged into anything — even though run 2 was rejected
for unrelated reasons.

---

## Caveats that apply to both runs

**These numbers are not the project's accuracy claim.** They are measured on Open
Images photographs, not on video frames from creator content. The SRS figure must
come from the labelled benchmark clips — see [`benchmark/README.md`](../benchmark/README.md).

**The gap between the two is the point, and it has now bitten twice.** Run 1 scored
0.487 on `Handgun` in photographs and then failed completely on a pistol in 720p news
footage — a failure that turned out to be inference resolution, not the model (see
`context.md` §12). Run 2 then scored *better* on every headline metric and failed the
same clip outright. A validation table cannot tell you whether the tool works on
video. Only video can.
