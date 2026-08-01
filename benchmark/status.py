"""Coverage report -- how far the benchmark set is from being usable.

    python benchmark/status.py

Answers the question the evaluator cannot: not "how accurate is the tool" but
"do I have enough labelled data to make any claim at all, and what is missing".
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from src.benchmark import runner  # noqa: E402

TARGET_CLIPS = 20
BAR = "=" * 74


def bar(done: int, target: int, width: int = 28) -> str:
    filled = min(width, int(width * done / target)) if target else 0
    return "[" + "#" * filled + "." * (width - filled) + "]"


def main() -> int:
    try:
        labels = runner.load_labels()
    except ValueError as e:
        print(f"A label file is invalid: {e}")
        print("Fix it, then run:  python benchmark/evaluate.py --validate")
        return 1

    real = [l for l in labels if not l.get("synthetic")]
    synthetic = [l for l in labels if l.get("synthetic")]
    missing_clip = [l for l in labels if not (runner.CLIPS_DIR / l["clip"]).exists()]

    n_audio = sum(len(l.get("audio", [])) for l in real)
    n_visual = sum(len(l.get("visual", [])) for l in real)
    n_spots = sum(len(l.get("ad_spots", [])) for l in real)
    total_events = n_audio + n_visual + n_spots

    clean = [l for l in real
             if not (l.get("audio") or l.get("visual"))
             and "clean clip" in (l.get("notes", "") or "").lower()]
    unattributed = [l for l in real if not (l.get("source") or "").strip()]

    print()
    print(BAR)
    print(" BENCHMARK COVERAGE")
    print(BAR)
    print(f" real clips       {bar(len(real), TARGET_CLIPS)}  {len(real):>3} / {TARGET_CLIPS}")
    print(f" labelled events  {bar(total_events, runner.MIN_EVENTS_FOR_CLAIM)}  "
          f"{total_events:>3} / {runner.MIN_EVENTS_FOR_CLAIM} minimum")
    print()
    print(f"   audio {n_audio}   visual {n_visual}   ad spots {n_spots}")
    if synthetic:
        print(f"   plus {len(synthetic)} synthetic clip(s), excluded from the evidence base")

    print("\n Checks")
    def line(ok, text):
        print(f"   [{'ok' if ok else '  '}] {text}")

    line(len(real) >= runner.MIN_REAL_CLIPS_FOR_CLAIM,
         f"at least {runner.MIN_REAL_CLIPS_FOR_CLAIM} real clips "
         f"(have {len(real)})")
    line(total_events >= runner.MIN_EVENTS_FOR_CLAIM,
         f"at least {runner.MIN_EVENTS_FOR_CLAIM} labelled events (have {total_events})")
    line(bool(clean),
         f"some clean clips with no violations, to catch false positives "
         f"(have {len(clean)})")
    line(n_visual > 0, f"visual events labelled, ready for M2 (have {n_visual})")
    line(not missing_clip, "every label has its clip present")
    line(not unattributed, "every clip records where it came from")

    if missing_clip:
        print("\n Labels whose clip is missing from benchmark/clips/:")
        for l in missing_clip:
            print(f"   - {l['_label_file']} -> {l['clip']}")
    if unattributed:
        print("\n Clips with no source recorded:")
        for l in unattributed:
            print(f"   - {l['_label_file']}")

    print("\n Next")
    if len(real) < TARGET_CLIPS:
        print(f"   Add {TARGET_CLIPS - len(real)} more clip(s):")
        print("     python benchmark/intake.py <video> --start 1:10 --end 2:00 \\")
        print('         --source \"where it came from\"')
        print("   Then label with benchmark/labeller.html")
    elif total_events < runner.MIN_EVENTS_FOR_CLAIM:
        print("   Enough clips, but more labelled events needed -- check for missed ones.")
    else:
        print("   Coverage looks adequate. Run:  python benchmark/evaluate.py")
    print(BAR)
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
