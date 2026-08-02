# Fine-tuning the risk detector (M3b)

Stock COCO cannot detect the things the SRS promises. It has **no firearm,
cigarette or drug class** — only knife, scissors, baseball bat, bottle and wine
glass. This directory trains a model that covers the gap.

Why train rather than download someone else's: every community candidate surveyed
in [`PLAN.md` §6a](../PLAN.md) was paywalled, unlicensed, trained on the wrong
visual domain, or unverifiable. Training our own gives known provenance, a citable
licence, and a defensible answer to *"where did this model come from?"*

---

## Two environments, on purpose

`fiftyone` (the dataset tool) pulls numpy 2.x, MongoDB and a large dependency tree
that conflicts with the project's stack — installing it into the main environment
broke `scikit-image` and `streamlit`. It therefore lives in its own virtual
environment and only ever writes files to disk.

| Step | Environment | Command |
|---|---|---|
| Download dataset | isolated | `.venv-data\Scripts\python.exe training/download_dataset.py` |
| Train | project | `python training/train.py` |

Create the isolated environment once:

```bash
python -m venv .venv-data
.venv-data\Scripts\python.exe -m pip install fiftyone
```

---

## 1. Download

```bash
.venv-data\Scripts\python.exe training/download_dataset.py --train 300 --val 80
```

Fetches an **Open Images V7** subset. `--train`/`--val` are quotas **per class**,
not totals.

**Classes.** Weapons: Handgun, Shotgun, Rifle, Knife, Dagger, Sword, Axe.
Substances: Beer, Wine, Cocktail, Wine glass.

**Not available from this source: cigarette, tobacco, drugs, blood.** Open Images
has no such class, so smoking and drug detection remain uncovered and must be
described as out of scope rather than implied.

### Two decisions worth knowing

**We source from the `validation` and `test` splits, not `train`.** Selecting from
`train` forces a ~7 GB metadata download (a 4.8 GB image index plus ~2.5 GB of box
annotations) before a single image arrives. Validation and test carry far smaller
indexes, are annotated to the same standard, and do not overlap — so they are
re-partitioned as our train and val sets. Legitimate, just not the split the
dataset authors intended; say so in the report.

**Sampling is per class, not a global cap.** Asking for *N* images containing "any
of these classes" returns whatever is commonest. A trial run came back with 393
Wine instances and **zero Handgun** — that would have trained a wine detector. A
per-class quota keeps the rarer, higher-priority weapon classes represented.

---

## 2. Inspect before training

```bash
python training/train.py --check
```

Prints per-class instance counts and flags any class with under 30 training
instances. A sparse class will train badly and inflate nothing but your
disappointment — either raise the quota or drop the class and narrow the claim.

## 3. Train

```bash
python training/train.py --epochs 40
```

Fine-tunes from `yolov8n.pt` and copies the best checkpoint to
`models/risk_yolov8.pt`. CPU training is slow; if there is no GPU, either reduce
epochs for a first pass or train on a free cloud GPU and copy the weights back.

## 4. Use it

Settings → **Weight files**: `yolov8n.pt, risk_yolov8.pt`

The **Visual detection coverage** panel should then report the new classes. If it
does not, the class names in the trained model differ from
`RISK_CATEGORY_MAP` in `src/vision/detector.py` — extend the map rather than
changing anything downstream.

## 5. Measure it honestly

Training metrics are computed on Open Images photographs, which are not video
frames from creator content. They indicate the model learned something; they are
**not** the project's accuracy claim. That figure comes from the labelled benchmark
clips — see [`benchmark/README.md`](../benchmark/README.md).

---

## Licensing

| Component | Licence |
|---|---|
| Open Images V7 annotations | CC BY 4.0 |
| Open Images V7 images | CC BY 2.0, per image — verify before redistributing |
| Ultralytics YOLOv8 (and models it trains) | **AGPL-3.0** |

AGPL-3.0 is copyleft and, per Ultralytics, covers models produced by the training
code as well as the code itself. Academic use is explicitly endorsed, but if this
repository is ever made public the obligation applies. State the dependency in the
report. Exact provenance for each download is written to `datasets/risk/SOURCE.json`.
