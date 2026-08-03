# Fine-tune results — run 1

**2026-08-03** · `yolov8n` fine-tuned for 12 epochs @ 512 px, batch 16, CPU
(i5-1235U) · **10.8 hours** · weights → `models/risk_yolov8.pt` (6.2 MB)

Evaluated on the held-out validation set: 500 images, 1,087 instances, sourced from
the Open Images `validation` split (training came from `test` — the two do not
overlap).

## Overall

| Metric | Value |
|---|---|
| Precision | 0.569 |
| Recall | 0.548 |
| mAP@50 | **0.566** |
| mAP@50-95 | 0.432 |
| Inference | 88.8 ms/image (CPU) |

## Per class

| Class | Instances (train) | Precision | Recall | mAP@50 | mAP@50-95 |
|---|---:|---:|---:|---:|---:|
| Cocktail | 616 | 0.702 | 0.829 | **0.856** | 0.697 |
| Knife | 233 | 0.671 | 0.750 | 0.766 | 0.593 |
| Rifle | 404 | 0.697 | 0.719 | 0.749 | 0.513 |
| Beer | 365 | 0.698 | 0.748 | 0.723 | 0.606 |
| Wine glass | 421 | 0.635 | 0.560 | 0.586 | 0.471 |
| Handgun | 84 | 0.412 | 0.375 | 0.487 | 0.393 |
| Dagger | 160 | 0.493 | 0.540 | 0.484 | 0.363 |
| Sword | 123 | 0.447 | 0.359 | 0.420 | 0.319 |
| Shotgun | 169 | 0.530 | 0.352 | 0.339 | 0.199 |
| Wine | 1175 | 0.403 | 0.250 | **0.250** | 0.170 |

## The result worth reading twice

**More data did not mean better performance, and the relationship is close to
inverted at the extremes.**

- **Wine** had the *most* training data of any class — 1,175 instances — and scored
  the *worst*, mAP@50 of 0.250.
- **Handgun** had the *least* — 84 instances, 14× fewer — and scored 0.487, nearly
  double.

Before training, the obvious worry was that Handgun would be unlearnable and might
need merging into a generic "Firearm" class to borrow examples from Rifle and
Shotgun. The measurement says the opposite: **class definition mattered more than
class volume.**

"Wine" in Open Images is semantically ambiguous — it is applied to bottles, to
filled glasses, and to the liquid itself, and it overlaps directly with the
separate `Wine glass` and `Cocktail` classes. The model cannot draw a boundary that
does not exist in the labels. `Cocktail`, by contrast, is visually consistent and
scored highest in the whole set despite having half the data.

The practical lesson for any further work: **fix ambiguous classes before adding
images.** Merging `Wine` into `Wine glass`, or dropping it in favour of the
better-defined alcohol classes, would likely raise the overall figure more than
another thousand wine photographs.

## Known weaknesses

- **Shotgun** (0.339) has the weakest localisation of the weapon classes;
  mAP@50-95 of 0.199 says the boxes are loose even when the class is right.
- **Handgun recall is 0.375** — it misses roughly two thirds of handguns. Usable as
  a flag for human review, not as an authority.
- **COCO adds noise.** In an end-to-end check on a held-out image containing a
  rifle and a shotgun, both were correctly detected (0.75 / 0.37) but the COCO
  model also called the same object a `baseball bat` at 0.84. Because that class
  also maps to `Weapon`, the compliance verdict was unaffected — but it inflates
  the flag count.

## Caveats

**12 epochs on CPU is a smoke test, not a competitive model.** It exists to prove
the pipeline end to end. A run of 40+ epochs at 640 px on a GPU should improve
these figures materially and takes roughly twenty minutes on a free Colab T4.

**These numbers are not the project's accuracy claim.** They are measured on Open
Images photographs, not on video frames from creator content. The SRS figure must
come from the labelled benchmark clips — see [`benchmark/README.md`](../benchmark/README.md).

Artifacts (PR curves, confusion matrix, per-epoch CSV) are in `training/runs/risk/`.
