"""Package the prepared dataset into a single archive for a cloud GPU run.

    python training/package_for_colab.py

Produces `training/risk_dataset_colab.zip`, ready to upload to Colab.

Two things this does that a plain `zip` of the folder would not:

**Images are resized so the long side is at most the training resolution.** The
Open Images exports are around 1024 px, training runs at 640, so every pixel above
that is decoded and thrown away on every epoch -- and, more to the point here,
uploaded first. YOLO label files store *normalised* coordinates, so resizing the
image leaves them correct without touching them. Measured: 513 MB -> roughly a
third of that, with no effect on the trained model.

**dataset.yaml is rewritten with a relative path.** The local file carries an
absolute Windows path (`C:\\Users\\...`), which means nothing on a Linux VM;
ultralytics would report zero images found and train on nothing, which looks like
a broken dataset rather than a broken path.
"""
import argparse
import shutil
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

DATASET_DIR = ROOT / "datasets" / "risk"
STAGE_DIR = ROOT / "training" / "_colab_stage"
ARCHIVE = ROOT / "training" / "risk_dataset_colab.zip"

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def main() -> int:
    ap = argparse.ArgumentParser(description="Bundle the risk dataset for Colab.")
    ap.add_argument("--imgsz", type=int, default=640,
                    help="longest side to keep; match the training resolution")
    args = ap.parse_args()

    data_yaml = DATASET_DIR / "dataset.yaml"
    if not data_yaml.exists():
        print(f"No dataset at {data_yaml.relative_to(ROOT)}.")
        print("Fetch it first:")
        print(r"   .venv-data\Scripts\python.exe training/download_dataset.py")
        return 1

    try:
        import yaml
        from PIL import Image
    except ImportError as e:
        print(f"Missing dependency: {e}")
        return 1

    from training.download_dataset import CLASSES

    spec = yaml.safe_load(data_yaml.read_text(encoding="utf-8"))
    names = [spec["names"][i] for i in sorted(spec["names"])]
    if names != CLASSES:
        print("dataset.yaml and CLASSES disagree -- refusing to package.")
        print(f"  dataset.yaml: {names}")
        print(f"  CLASSES     : {CLASSES}")
        print("YOLO addresses classes by index, so this would mislabel everything.")
        return 1

    if STAGE_DIR.exists():
        shutil.rmtree(STAGE_DIR)

    print(f"staging {len(names)} classes, resizing to {args.imgsz} px ...")
    kept = shrunk = 0
    for split in ("train", "val"):
        (STAGE_DIR / "images" / split).mkdir(parents=True, exist_ok=True)
        (STAGE_DIR / "labels" / split).mkdir(parents=True, exist_ok=True)

        for img in sorted((DATASET_DIR / "images" / split).glob("*.jpg")):
            label = DATASET_DIR / "labels" / split / f"{img.stem}.txt"
            # An image with no label file contributes nothing but upload weight.
            if not label.exists():
                continue
            dest = STAGE_DIR / "images" / split / img.name
            with Image.open(img) as im:
                im = im.convert("RGB")
                if max(im.size) > args.imgsz:
                    ratio = args.imgsz / max(im.size)
                    im = im.resize((max(1, round(im.width * ratio)),
                                    max(1, round(im.height * ratio))),
                                   Image.LANCZOS)
                    shrunk += 1
                im.save(dest, "JPEG", quality=88, optimize=True)
            # Labels are normalised coordinates, so they survive the resize as-is.
            shutil.copy2(label, STAGE_DIR / "labels" / split / label.name)
            kept += 1
        print(f"   {split}: {len(list((STAGE_DIR / 'images' / split).glob('*.jpg')))} images")

    # Relative path: resolved against wherever the archive is unpacked.
    (STAGE_DIR / "dataset.yaml").write_text(
        yaml.safe_dump({"path": ".", "train": "images/train", "val": "images/val",
                        "names": {i: n for i, n in enumerate(names)}},
                       sort_keys=False),
        encoding="utf-8")

    print("\ncompressing ...")
    ARCHIVE.unlink(missing_ok=True)
    with zipfile.ZipFile(ARCHIVE, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for f in sorted(STAGE_DIR.rglob("*")):
            if f.is_file():
                z.write(f, f.relative_to(STAGE_DIR))
    shutil.rmtree(STAGE_DIR)

    before = sum(f.stat().st_size for f in DATASET_DIR.rglob("*") if f.is_file())
    after = ARCHIVE.stat().st_size
    print(f"\n{kept} images ({shrunk} resized)")
    print(f"source {before / 1e6:.0f} MB  ->  archive {after / 1e6:.0f} MB")
    print(f"\nwrote {ARCHIVE.relative_to(ROOT)}")
    print("Upload it with training/colab_train.ipynb")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
