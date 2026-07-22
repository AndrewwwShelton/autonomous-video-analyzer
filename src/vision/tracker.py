"""Temporal ad-spot tracking (Module 2, stage 4) — REAL code, model-free.

Takes per-frame ad-spot candidates and merges them across time: a surface that
persists (same place, same type) for at least `min_duration_sec` becomes one
Premium Ad Spot (the Synopsis's "continuous 5-second" rule).

Greedy association: a candidate extends an open track when IoU with the track's last
box >= iou_threshold, same spot_type, and the time gap <= max_gap_sec; otherwise it
opens a new track.
"""
from dataclasses import dataclass, field


def iou(a: list[float], b: list[float]) -> float:
    """Intersection-over-union of two [x1, y1, x2, y2] boxes."""
    ix1, iy1 = max(a[0], b[0]), max(a[1], b[1])
    ix2, iy2 = min(a[2], b[2]), min(a[3], b[3])
    if ix2 <= ix1 or iy2 <= iy1:
        return 0.0
    inter = (ix2 - ix1) * (iy2 - iy1)
    area_a = (a[2] - a[0]) * (a[3] - a[1])
    area_b = (b[2] - b[0]) * (b[3] - b[1])
    return inter / (area_a + area_b - inter)


@dataclass
class _Track:
    spot_type: str
    start: float
    end: float
    boxes: list = field(default_factory=list)
    areas: list = field(default_factory=list)
    scores: list = field(default_factory=list)

    def add(self, t: float, cand: dict) -> None:
        self.end = t
        self.boxes.append(cand["bounding_box"])
        self.areas.append(cand.get("area_pixels", 0))
        self.scores.append(cand.get("score", 0.0))


def merge_candidates(frames: list[tuple[float, list[dict]]],
                     min_duration_sec: float = 5.0,
                     iou_threshold: float = 0.5,
                     max_gap_sec: float = 1.5) -> list[dict]:
    """frames: [(timestamp, [candidate, ...]), ...] in time order.
    Returns AdSpots-shaped dicts for surfaces persisting >= min_duration_sec.
    """
    open_tracks: list[_Track] = []
    closed: list[_Track] = []

    for t, cands in sorted(frames, key=lambda f: f[0]):
        # Retire tracks that have gone stale before matching.
        still_open = []
        for tr in open_tracks:
            (closed if t - tr.end > max_gap_sec else still_open).append(tr)
        open_tracks = still_open

        for cand in cands:
            best, best_iou = None, iou_threshold
            for tr in open_tracks:
                if tr.spot_type != cand.get("spot_type"):
                    continue
                score = iou(tr.boxes[-1], cand["bounding_box"])
                if score >= best_iou:
                    best, best_iou = tr, score
            if best is not None:
                best.add(t, cand)
            else:
                tr = _Track(spot_type=cand.get("spot_type", "unknown"), start=t, end=t)
                tr.add(t, cand)
                open_tracks.append(tr)

    closed.extend(open_tracks)

    spots = []
    for tr in closed:
        if tr.end - tr.start < min_duration_sec:
            continue
        n = len(tr.boxes)
        avg_box = [round(sum(b[i] for b in tr.boxes) / n) for i in range(4)]
        spots.append({
            "timestamp_start": tr.start,
            "timestamp_end": tr.end,
            "spot_type": tr.spot_type,
            "bounding_box": avg_box,
            "area_pixels": round(sum(tr.areas) / n),
            "suitability_score": round(sum(tr.scores) / n, 3),
        })
    spots.sort(key=lambda s: s["timestamp_start"])
    return spots
