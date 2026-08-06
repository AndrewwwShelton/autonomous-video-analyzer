"""Download an Open Images V7 subset for fine-tuning the risk detector.

Run with the ISOLATED environment, not the project one:

    .venv-data/Scripts/python.exe training/download_dataset.py
    .venv-data/Scripts/python.exe training/download_dataset.py --train 4000 --val 800

Why Open Images rather than the community weights surveyed in PLAN.md 6a:

  * It contains exactly the classes stock COCO lacks -- Handgun, Shotgun and Rifle --
    which are the most consequential gap in our taxonomy.
  * Roughly 90% of its boxes were drawn by professional annotators, and it is
    maintained by Google, so provenance is defensible in a viva.
  * No account or API key is needed, unlike Roboflow, whose trained weights sit
    behind a paid plan and whose free tier is a hosted API that would break the
    project's offline requirement.

fiftyone is kept out of the main environment on purpose: it pulls numpy 2.x,
MongoDB and a large dependency tree that conflicts with the project's stack.
This script only writes image and label files to disk; training runs separately
in the project environment.

**Which Open Images splits we use, and why.** Selecting from the `train` split
forces a ~7 GB metadata download (a 4.8 GB image index plus ~2.5 GB of box
annotations) before a single image arrives. The `test` (125,436 images) and
`validation` (41,620 images) splits carry far smaller indexes and are annotated to
the same standard, so we source from those and re-partition them ourselves:

    Open Images `test`        ->  our training set   (the larger split)
    Open Images `validation`  ->  our validation set (the smaller split)

The mapping follows the sizes, not the names: `test` holds three times as many
images as `validation`, so it supplies the training data. Getting this backwards
produces a validation set larger than the training set, which is exactly what a
first run did. The two never overlap, so the split is clean -- just not the one
the dataset authors originally intended. Worth stating plainly in the report.
"""
import argparse
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATASET_DIR = ROOT / "datasets" / "risk"

# Open Images class names, kept fine-grained. The application maps these to the
# coarse DDD categories via RISK_CATEGORY_MAP, so "Handgun" stays more informative
# in the interface than a flattened "Weapon" would be.
#
# Run 2 revision (see training/RESULTS.md). Run 1 measured that class *definition*
# mattered far more than class volume, so this set is chosen on that basis:
#
#   + Kitchen knife, Bow and arrow, Syringe -- visually distinctive classes that
#     widen coverage without overlapping anything already here. Syringe is the only
#     drug-paraphernalia class this source offers.
#   + Axe -- listed in run 1 but only 2 instances survived the download, so
#     prune_classes.py correctly dropped it. It needs its own quota to be learnable.
#   - Wine -- REMOVED. It scored worst of all ten classes (mAP@50 0.250, recall
#     0.250) because Open Images applies the label to bottles, to filled glasses and
#     to the liquid itself, overlapping both `Wine glass` and `Cocktail`. The model
#     cannot draw a boundary the labels do not contain. Alcohol stays covered by
#     Beer, Cocktail and Wine glass.
WEAPON_CLASSES = ["Handgun", "Shotgun", "Rifle", "Knife", "Kitchen knife",
                  "Dagger", "Sword", "Axe", "Bow and arrow"]
SUBSTANCE_CLASSES = ["Beer", "Cocktail", "Wine glass", "Syringe"]
CLASSES = WEAPON_CLASSES + SUBSTANCE_CLASSES

# Verified against the full 601-class Open Images V7 boxable vocabulary, not
# assumed: there is no cigarette, tobacco, smoking, drug, pill, blood or gore
# class. No amount of retraining covers those from this source -- they need a
# different dataset. Recorded here so the gap stays visible at the point it matters.
UNCOVERED = ["cigarette", "tobacco", "smoking", "drugs", "pills", "blood", "gore"]


def main() -> int:
    ap = argparse.ArgumentParser(description="Fetch an Open Images V7 risk subset.")
    ap.add_argument("--train", type=int, default=600,
                    help="images PER CLASS for our training set (from OI 'test')")
    ap.add_argument("--val", type=int, default=120,
                    help="images PER CLASS for our validation set (from OI 'validation')")
    ap.add_argument("--seed", type=int, default=51, help="shuffle seed, for reproducibility")
    ap.add_argument("--clean", action="store_true", help="delete any previous export first")
    args = ap.parse_args()

    try:
        import fiftyone as fo
        import fiftyone.zoo as foz
    except ImportError:
        print("fiftyone is not available. Run this with the isolated environment:")
        print(r"   .venv-data\Scripts\python.exe training/download_dataset.py")
        return 1

    if args.clean and DATASET_DIR.exists():
        shutil.rmtree(DATASET_DIR)
    DATASET_DIR.mkdir(parents=True, exist_ok=True)

    print(f"classes ({len(CLASSES)}): {', '.join(CLASSES)}")
    print(f"not available from this source: {', '.join(UNCOVERED)}")
    print()

    counts = {}
    # Sample PER CLASS, not across the class set as a whole. Asking for N images
    # containing "any of these classes" returns whatever is commonest -- a trial run
    # came back 393 Wine instances and zero Handgun, which would train a wine
    # detector. Requesting a quota per class keeps the rarer, higher-priority
    # weapon classes represented.
    #
    # (Open Images split, per-class quota, the YOLO split we map it to).
    # 'test' is the larger split, so it feeds training -- see module docstring.
    for split, per_class, yolo_split in (("test", args.train, "train"),
                                         ("validation", args.val, "val")):
        print(f"--- Open Images '{split}' -> our '{yolo_split}': "
              f"up to {per_class} images per class ---")
        total = 0
        for cls in CLASSES:
            try:
                dataset = foz.load_zoo_dataset(
                    "open-images-v7",
                    split=split,
                    label_types=["detections"],
                    classes=[cls],
                    max_samples=per_class,
                    shuffle=True,
                    seed=args.seed,
                    dataset_name=f"risk-{split}-{cls}".replace(" ", "-"),
                )
            except Exception as e:
                print(f"    {cls:<12} skipped ({type(e).__name__}: {e})")
                continue

            # An image pulled in for Handgun may also contain a Knife; keep every
            # label from our class set, not just the one we searched on.
            dataset.filter_labels("ground_truth",
                                  fo.ViewField("label").is_in(CLASSES)).save()
            dataset.export(
                export_dir=str(DATASET_DIR),
                dataset_type=fo.types.YOLOv5Dataset,
                label_field="ground_truth",
                split=yolo_split,
                classes=CLASSES,
            )
            print(f"    {cls:<12} {len(dataset):>4} images")
            total += len(dataset)
            dataset.delete()      # drop from the fiftyone database; files remain

        counts[yolo_split] = total
        print(f"    -> {total} images for '{yolo_split}' "
              f"(before de-duplication of shared images)\n")

    manifest = {
        "source": "Open Images V7 (Google) via fiftyone zoo",
        "url": "https://storage.googleapis.com/openimages/web/index.html",
        "annotations_license": "CC BY 4.0",
        "images_license": "CC BY 2.0 (per-image; verify before redistribution)",
        "split_mapping": {
            "our train": "Open Images 'test' split (125,436 images -- the larger)",
            "our val": "Open Images 'validation' split (41,620 images)",
            "why": ("the Open Images 'train' split requires a ~7 GB metadata download "
                    "before any image is selected; validation and test are annotated "
                    "to the same standard and do not overlap"),
        },
        "classes": CLASSES,
        "weapon_classes": WEAPON_CLASSES,
        "substance_classes": SUBSTANCE_CLASSES,
        "not_covered_by_this_source": UNCOVERED,
        "counts": counts,
        "seed": args.seed,
        "sampling": ("per-class quota rather than a global cap, so rare weapon "
                     "classes are not swamped by common ones such as Wine"),
    }
    (DATASET_DIR / "SOURCE.json").write_text(json.dumps(manifest, indent=2),
                                             encoding="utf-8")

    print("dataset ready at", DATASET_DIR.relative_to(ROOT))
    print("provenance recorded in datasets/risk/SOURCE.json")
    print("\nNext (project environment, not this one):")
    print("   python training/train.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
