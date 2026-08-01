"""Benchmark scoring — pure functions, no I/O, no database.

Substantiates the SRS accuracy claim ("precision greater than 85% on benchmark
testing sets"). Kept free of side effects so the matching rules can be tested
directly, which matters because the matching rules are where scoring goes wrong.

Design notes that are easy to get wrong:

- **Timestamps never align exactly.** ASR word boundaries drift by a few hundred
  milliseconds, and vision runs at 1 FPS so a detection can only ever land on a
  whole second. Matching is therefore tolerance-based, not exact.
- **One truth item may be claimed by at most one prediction**, and vice versa.
  Without that rule a model that emits the same flag ten times would score ten
  true positives off a single labelled event.
- **Severity is not a prediction.** It is looked up from our own dictionary once a
  word is detected, so scoring it would measure the config file, not the engine.
  Audio matching therefore keys on the word; severity is reported separately as a
  consistency check.
"""
from dataclasses import dataclass, field


@dataclass
class Metrics:
    """Counts for one category, with the derived rates."""
    tp: int = 0
    fp: int = 0
    fn: int = 0

    @property
    def precision(self) -> float:
        denom = self.tp + self.fp
        return self.tp / denom if denom else 0.0

    @property
    def recall(self) -> float:
        denom = self.tp + self.fn
        return self.tp / denom if denom else 0.0

    @property
    def f1(self) -> float:
        p, r = self.precision, self.recall
        return 2 * p * r / (p + r) if (p + r) else 0.0

    @property
    def support(self) -> int:
        """Number of labelled events — precision on a tiny support means little."""
        return self.tp + self.fn

    def __add__(self, other: "Metrics") -> "Metrics":
        return Metrics(self.tp + other.tp, self.fp + other.fp, self.fn + other.fn)

    def as_dict(self) -> dict:
        return {"tp": self.tp, "fp": self.fp, "fn": self.fn, "support": self.support,
                "precision": round(self.precision, 4), "recall": round(self.recall, 4),
                "f1": round(self.f1, 4)}


@dataclass
class MatchResult:
    metrics: Metrics = field(default_factory=Metrics)
    matched: list = field(default_factory=list)      # (truth, prediction, delta_sec)
    false_positives: list = field(default_factory=list)
    false_negatives: list = field(default_factory=list)


def match_events(truth: list[dict], predicted: list[dict],
                 tolerance_sec: float = 2.0) -> MatchResult:
    """Greedy one-to-one matching of timestamped events sharing a `key`.

    Each event is {"key": str, "time": float, ...}. A prediction matches a truth
    item when the keys are equal (case-insensitive) and the times fall within
    `tolerance_sec`. Closest-in-time wins, and each side is consumed once.
    """
    result = MatchResult()
    unclaimed = list(predicted)

    for t in truth:
        t_key = str(t["key"]).strip().lower()
        candidates = [
            (abs(p["time"] - t["time"]), i, p)
            for i, p in enumerate(unclaimed)
            if str(p["key"]).strip().lower() == t_key
            and abs(p["time"] - t["time"]) <= tolerance_sec
        ]
        if candidates:
            delta, idx, pred = min(candidates, key=lambda c: c[0])
            result.matched.append((t, pred, round(delta, 3)))
            result.metrics.tp += 1
            unclaimed.pop(idx)
        else:
            result.false_negatives.append(t)
            result.metrics.fn += 1

    result.false_positives = unclaimed
    result.metrics.fp = len(unclaimed)
    return result


def interval_iou(a: tuple[float, float], b: tuple[float, float]) -> float:
    """Temporal intersection-over-union of two [start, end] intervals."""
    lo = max(a[0], b[0])
    hi = min(a[1], b[1])
    if hi <= lo:
        return 0.0
    inter = hi - lo
    union = (a[1] - a[0]) + (b[1] - b[0]) - inter
    return inter / union if union else 0.0


def match_intervals(truth: list[dict], predicted: list[dict],
                    iou_threshold: float = 0.3) -> MatchResult:
    """Match ad-spot intervals by temporal overlap rather than a single instant.

    Ad spots are stretches of time, so a point tolerance makes no sense. Spot type
    is deliberately *not* required to match: whether a blank wall is called a wall
    or a desk is far less important than whether the interval is genuinely usable.
    """
    result = MatchResult()
    unclaimed = list(predicted)

    for t in truth:
        t_iv = (t["start"], t["end"])
        candidates = [
            (interval_iou(t_iv, (p["start"], p["end"])), i, p)
            for i, p in enumerate(unclaimed)
        ]
        candidates = [c for c in candidates if c[0] >= iou_threshold]
        if candidates:
            iou, idx, pred = max(candidates, key=lambda c: c[0])
            result.matched.append((t, pred, round(iou, 3)))
            result.metrics.tp += 1
            unclaimed.pop(idx)
        else:
            result.false_negatives.append(t)
            result.metrics.fn += 1

    result.false_positives = unclaimed
    result.metrics.fp = len(unclaimed)
    return result


def per_category(truth: list[dict], predicted: list[dict],
                 tolerance_sec: float = 2.0) -> dict[str, Metrics]:
    """Break scoring down by key, so a strong overall figure cannot hide a weak class."""
    keys = {str(e["key"]).strip().lower() for e in truth} | \
           {str(e["key"]).strip().lower() for e in predicted}
    out: dict[str, Metrics] = {}
    for k in sorted(keys):
        t = [e for e in truth if str(e["key"]).strip().lower() == k]
        p = [e for e in predicted if str(e["key"]).strip().lower() == k]
        out[k] = match_events(t, p, tolerance_sec).metrics
    return out
