"""Fine-tune a YOLOv8 risk detector on the Open Images subset.

Run with the PROJECT environment (which already has ultralytics and torch):

    python training/train.py                    # sensible defaults
    python training/train.py --epochs 60 --model yolov8s.pt
    python training/train.py --check            # inspect the dataset, train nothing

Produces models/risk_yolov8.pt, which the application picks up once the file name
is added to the `vision_weights` setting.

This replaces the community-weights route surveyed in PLAN.md 6a, where every
candidate was paywalled, unlicensed, trained on the wrong visual domain, or
unverifiable. Training our own gives known provenance, a citable CC BY 4.0 source,
and a defensible answer to "where did this model come from".

Expect CPU training to be slow. If no GPU is present, prefer a small model and few
epochs, or run this notebook-style on a free cloud GPU and copy the weights back.
"""
import argparse
import shutil
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

DATASET_DIR = ROOT / "datasets" / "risk"
DATA_YAML = DATASET_DIR / "dataset.yaml"
OUT_WEIGHTS = ROOT / "models" / "risk_yolov8.pt"
RUNS_DIR = ROOT / "training" / "runs"


def class_names() -> list[str]:
    import yaml
    d = yaml.safe_load(DATA_YAML.read_text(encoding="utf-8"))
    names = d["names"]
    return [names[i] for i in sorted(names)]


def inspect() -> dict:
    """Per-class instance counts, so imbalance is visible before training."""
    names = class_names()
    report = {}
    for split in ("train", "val"):
        label_dir = DATASET_DIR / "labels" / split
        counts = Counter()
        images = 0
        for f in label_dir.glob("*.txt"):
            images += 1
            for line in f.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    counts[int(line.split()[0])] += 1
        report[split] = {"images": images, "counts": counts}
    return {"names": names, "splits": report}


def print_inspection(info: dict) -> None:
    names = info["names"]
    print(f"{'class':<14} {'train':>8} {'val':>8}")
    print("-" * 32)
    tr = info["splits"]["train"]["counts"]
    va = info["splits"]["val"]["counts"]
    for i, n in enumerate(names):
        flag = "  <-- sparse" if tr[i] < 30 else ""
        print(f"{n:<14} {tr[i]:>8} {va[i]:>8}{flag}")
    print("-" * 32)
    print(f"{'IMAGES':<14} {info['splits']['train']['images']:>8} "
          f"{info['splits']['val']['images']:>8}")
    sparse = [n for i, n in enumerate(names) if tr[i] < 30]
    if sparse:
        print(f"\nSparse classes ({', '.join(sparse)}) will train poorly. Either raise "
              f"--train in\ndownload_dataset.py, or drop them and narrow the claim.")


def main() -> int:
    ap = argparse.ArgumentParser(description="Fine-tune the YOLOv8 risk detector.")
    ap.add_argument("--model", default="yolov8n.pt",
                    help="base weights to fine-tune from (default: yolov8n.pt)")
    ap.add_argument("--epochs", type=int, default=40)
    ap.add_argument("--imgsz", type=int, default=640)
    ap.add_argument("--batch", type=int, default=8)
    ap.add_argument("--device", default=None, help="cuda device index, or cpu")
    ap.add_argument("--check", action="store_true",
                    help="report dataset composition and exit")
    args = ap.parse_args()

    if not DATA_YAML.exists():
        print(f"No dataset at {DATA_YAML.relative_to(ROOT)}.")
        print("Fetch it first with the isolated environment:")
        print(r"   .venv-data\Scripts\python.exe training/download_dataset.py")
        return 1

    info = inspect()
    print_inspection(info)
    if args.check:
        return 0

    try:
        import torch
        from ultralytics import YOLO
    except ImportError as e:
        print(f"Missing dependency: {e}. Run this in the project environment.")
        return 1

    device = args.device
    if device is None:
        device = "0" if torch.cuda.is_available() else "cpu"
    if device == "cpu":
        print("\nNo GPU detected -- training on CPU will be slow. Consider a smaller "
              "--epochs\nvalue for a first pass, or train on a cloud GPU and copy "
              "the weights back.")

    print(f"\nfine-tuning {args.model} for {args.epochs} epochs on {device} ...\n")
    model = YOLO(args.model)
    model.train(
        data=str(DATA_YAML),
        epochs=args.epochs,
        imgsz=args.imgsz,
        batch=args.batch,
        device=device,
        project=str(RUNS_DIR),
        name="risk",
        exist_ok=True,
        patience=10,          # stop early if validation stops improving
    )

    best = RUNS_DIR / "risk" / "weights" / "best.pt"
    if not best.exists():
        print(f"Training finished but {best} is missing.")
        return 1

    OUT_WEIGHTS.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(best, OUT_WEIGHTS)
    print(f"\nbest weights -> {OUT_WEIGHTS.relative_to(ROOT)}")
    print("\nTo use them, add the file to the vision_weights setting:")
    print('   Settings -> Weight files:  yolov8n.pt, risk_yolov8.pt')
    print("Then confirm the Visual detection coverage panel reports the new classes.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
