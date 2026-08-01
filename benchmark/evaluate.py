"""Run the accuracy benchmark and print a readable report.

    python benchmark/evaluate.py              # real engines (default)
    python benchmark/evaluate.py --mode demo  # sanity-check the harness itself
    python benchmark/evaluate.py --validate   # check label files, run nothing

Only stages backed by a real engine count toward the SRS precision claim; stages
still using stand-ins are reported but explicitly marked, so a demo number can
never be mistaken for a result.
"""
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.benchmark import runner  # noqa: E402

# Windows consoles default to cp1252, which cannot encode box-drawing characters
# or em-dashes. Output stays ASCII, and stdout is widened as a belt-and-braces
# guard so a stray character can never crash a benchmark run.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BAR = "=" * 74


def _pct(x) -> str:
    return f"{x * 100:5.1f}%"


def print_report(report: dict) -> None:
    print()
    print(BAR)
    print(f" ACCURACY BENCHMARK | mode={report['mode']} | {report['generated']}")
    print(BAR)
    print(f" clips evaluated : {report['clips_evaluated']} / {report['clips_total']}")
    if report["clips_failed"]:
        print(f" clips failed    : {len(report['clips_failed'])}")
        for f in report["clips_failed"]:
            print(f"     ! {f['clip']}: {f['error']}")

    print()
    print(f" {'stage':<10} {'engine':<9} {'prec':>7} {'recall':>8} {'f1':>7} "
          f"{'TP':>4} {'FP':>4} {'FN':>4}  claim")
    print(" " + "-" * 71)
    for stage, s in report["stages"].items():
        if not s["support"] and not s["fp"]:
            print(f" {stage:<10} {s['engine']:<9} {'--':>7} {'--':>8} {'--':>7} "
                  f"{'--':>4} {'--':>4} {'--':>4}  no labels")
            continue
        claim = "counts" if s["counts_toward_claim"] else "EXCLUDED (stub)"
        print(f" {stage:<10} {s['engine']:<9} {_pct(s['precision']):>7} "
              f"{_pct(s['recall']):>8} {_pct(s['f1']):>7} "
              f"{s['tp']:>4} {s['fp']:>4} {s['fn']:>4}  {claim}")

    # Headline: only real engines may contribute.
    valid = [s for s in report["stages"].values()
             if s["counts_toward_claim"] and s["support"]]
    print()
    if valid:
        tp = sum(s["tp"] for s in valid)
        fp = sum(s["fp"] for s in valid)
        overall = tp / (tp + fp) if (tp + fp) else 0.0
        target = report["precision_target"]
        verdict = "MEETS" if overall >= target else "BELOW"
        print(f" Overall precision (real engines only): {_pct(overall)}  "
              f"-- {verdict} the {_pct(target)} target")
    else:
        print(" No stage is backed by a real engine yet -- no claim can be made.")

    ev = report.get("evidence", {})
    print(f" Evidence base: {ev.get('labelled_events_on_real_engines', 0)} labelled "
          f"events across {ev.get('real_clips', 0)} real clip(s)"
          + (f" + {ev['synthetic_clips']} synthetic" if ev.get("synthetic_clips") else ""))
    if not ev.get("sufficient", False):
        print()
        print(" *** NOT YET PUBLISHABLE ***")
        for s in ev.get("shortfalls", []):
            print(f"   - {s}")
        print("   The figure above is indicative only. Do not quote it in the report")
        print("   or the viva until the evidence base is large enough.")

    # Category breakdowns are only meaningful for engines that are actually real.
    for stage in ("audio", "visual"):
        if report["stages"].get(stage, {}).get("engine") != "valid":
            continue
        cats = report["by_category"].get(stage) or {}
        if cats:
            print(f"\n {stage} by category:")
            for name, m in cats.items():
                print(f"    {name:<14} prec {_pct(m['precision'])}  "
                      f"recall {_pct(m['recall'])}  (n={m['support']})")

    misses = [(c["clip"], c["missed_audio"], c["spurious_audio"])
              for c in report["per_clip"]
              if c.get("missed_audio") or c.get("spurious_audio")]
    if misses:
        print("\n audio errors worth inspecting:")
        for clip, missed, spurious in misses:
            if missed:
                print(f"    {clip}: missed {missed}")
            if spurious:
                print(f"    {clip}: spurious {spurious}")

    print()
    print(f" full report written to {report['_written_to']}")
    print(BAR)
    print()


def main() -> int:
    ap = argparse.ArgumentParser(description="Run the AdSafe accuracy benchmark.")
    ap.add_argument("--mode", choices=["real", "demo"], default="real",
                    help="which engines to run (default: real)")
    ap.add_argument("--validate", action="store_true",
                    help="validate label files and exit without running the pipeline")
    ap.add_argument("--keep-scratch", action="store_true",
                    help="keep the temporary benchmark database for debugging")
    args = ap.parse_args()

    if args.validate:
        try:
            labels = runner.load_labels()
        except ValueError as e:
            print(f"INVALID: {e}")
            return 1
        if not labels:
            print(f"No label files found in {runner.LABELS_DIR}")
            return 1
        total_a = sum(len(l.get("audio", [])) for l in labels)
        total_v = sum(len(l.get("visual", [])) for l in labels)
        total_s = sum(len(l.get("ad_spots", [])) for l in labels)
        print(f"OK -- {len(labels)} label file(s): "
              f"{total_a} audio, {total_v} visual, {total_s} ad-spot events")
        for l in labels:
            missing = "" if (runner.CLIPS_DIR / l["clip"]).exists() else "   [CLIP MISSING]"
            print(f"   {l['_label_file']:<28} -> {l['clip']}{missing}")
        return 0

    try:
        report = runner.run(mode=args.mode, keep_scratch=args.keep_scratch)
    except ValueError as e:
        print(f"Cannot run: {e}")
        return 1
    print_report(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
