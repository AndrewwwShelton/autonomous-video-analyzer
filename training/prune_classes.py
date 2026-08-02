"""Drop classes with too few instances to learn, and re-index the labels.

    python training/prune_classes.py --dry-run
    python training/prune_classes.py --min-instances 30

A class with a handful of examples cannot be learned. Left in place it contributes
nothing, reports a meaningless per-class mAP near zero, and drags down the overall
average -- making the model look worse than it is while detecting nothing extra.

Dropping a class is not simply deleting rows: YOLO label files reference classes by
integer index, so every remaining class must be re-indexed and the dataset.yaml
rewritten to match. Getting that wrong silently mislabels the entire dataset, which
is why this is a deliberate step rather than a flag buried in the training script.
"""
import argparse
import shutil
import sys
from collections import Counter
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
DATASET_DIR = ROOT / "datasets" / "risk"
DATA_YAML = DATASET_DIR / "dataset.yaml"

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def count_instances(split: str) -> Counter:
    counts = Counter()
    for f in (DATASET_DIR / "labels" / split).glob("*.txt"):
        for line in f.read_text(encoding="utf-8").splitlines():
            if line.strip():
                counts[int(line.split()[0])] += 1
    return counts


def main() -> int:
    ap = argparse.ArgumentParser(description="Remove unlearnably sparse classes.")
    ap.add_argument("--min-instances", type=int, default=30,
                    help="drop classes with fewer training instances than this")
    ap.add_argument("--dry-run", action="store_true", help="report and change nothing")
    args = ap.parse_args()

    if not DATA_YAML.exists():
        print(f"No dataset at {DATA_YAML.relative_to(ROOT)}.")
        return 1

    spec = yaml.safe_load(DATA_YAML.read_text(encoding="utf-8"))
    names = {int(k): v for k, v in spec["names"].items()}
    train_counts = count_instances("train")

    keep = [i for i in sorted(names) if train_counts[i] >= args.min_instances]
    drop = [i for i in sorted(names) if i not in keep]

    if not drop:
        print(f"Every class has at least {args.min_instances} training instances. "
              f"Nothing to do.")
        return 0

    print(f"threshold: {args.min_instances} training instances\n")
    for i in sorted(names):
        verdict = "keep" if i in keep else "DROP"
        print(f"  [{verdict}] {names[i]:<14} {train_counts[i]:>5} instances")
    print(f"\n{len(keep)} classes kept, {len(drop)} dropped")

    if args.dry_run:
        print("\n(dry run -- nothing written)")
        return 0

    backup = DATASET_DIR / "dataset.yaml.bak"
    if not backup.exists():
        shutil.copy2(DATA_YAML, backup)

    remap = {old: new for new, old in enumerate(keep)}
    rewritten = removed_lines = 0
    for split in ("train", "val"):
        for f in (DATASET_DIR / "labels" / split).glob("*.txt"):
            out = []
            changed = False
            for line in f.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                parts = line.split()
                old = int(parts[0])
                if old not in remap:
                    removed_lines += 1
                    changed = True
                    continue
                if remap[old] != old:
                    parts[0] = str(remap[old])
                    changed = True
                out.append(" ".join(parts))
            if changed:
                f.write_text("\n".join(out) + ("\n" if out else ""), encoding="utf-8")
                rewritten += 1

    spec["names"] = {new: names[old] for old, new in remap.items()}
    DATA_YAML.write_text(yaml.safe_dump(spec, sort_keys=False), encoding="utf-8")

    print(f"\nrewrote {rewritten} label files, removed {removed_lines} annotation lines")
    print(f"dataset.yaml updated ({len(keep)} classes); original kept as "
          f"{backup.name}")
    print("\nRemember to keep RISK_CATEGORY_MAP in src/vision/detector.py in step "
          "with these names.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
