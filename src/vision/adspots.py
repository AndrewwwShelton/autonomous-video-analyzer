"""Ad-spot candidate detection per frame (Module 2, stage 3).

This is the novel algorithm of the project (PLAN.md §2.2). Per sampled frame:

  1. OCCUPANCY MASK — run COCO YOLOv8, union all detection boxes into a binary mask.
     (COCO is used for what it is good at: people, furniture, tv, laptop — see D4.)
  2. BUSY MASK — Canny edge density + local colour variance; textured regions make
     bad ad surfaces.
  3. FREE SPACE = NOT occupied AND NOT busy.
  4. LARGEST INSCRIBED RECTANGLES in the free space — maximal-rectangle-in-binary-
     matrix DP, O(w·h).
  5. CLASSIFY spot_type: overlaps a tv/laptop box -> "screen"; large uniform region
     with no detections -> "blank_wall"; adjacent to a dining table box -> "empty_desk".
  6. SCORE = area x uniformity x centrality -> suitability_score (0..1).

The temporal pass (tracker.py — real code, already implemented) then merges candidates
across frames into >=5s Premium Ad Spots.
"""
import random


def find_ad_spot_candidates(frame, coco_detections) -> list[dict]:
    """Real algorithm — lands in M3a. Returns candidate dicts:
    {"bounding_box": [x1,y1,x2,y2], "spot_type": str, "area_pixels": float, "score": float}
    """
    raise NotImplementedError(
        "find_ad_spot_candidates lands in M3a — implement the 6-step algorithm in this "
        "module's docstring using OpenCV. Until then run the pipeline in demo mode."
    )


class DemoAdSpotFinder:
    """Generates per-frame candidates for a few stable windows plus one too-short window.

    Output feeds the REAL temporal tracker, so demo mode exercises the actual
    merge/persistence code path end to end. The too-short window (<5s) exists to prove
    the tracker's minimum-duration filter works — it must NOT appear in the final spots.
    """

    _WINDOWS = [  # (start_frac, end_frac, spot_type, box_frac[x1,y1,x2,y2])
        (0.10, 0.42, "blank_wall", (0.62, 0.12, 0.95, 0.55)),
        (0.50, 0.68, "screen",     (0.15, 0.20, 0.42, 0.50)),
        (0.74, 0.96, "empty_desk", (0.30, 0.65, 0.80, 0.92)),
        (0.45, 0.475, "blank_wall", (0.05, 0.05, 0.25, 0.30)),  # ~3% of duration: dropped
    ]

    def __init__(self, seed: int = 0):
        self.seed = seed

    def candidates_by_frame(self, duration_sec: float, width: int, height: int,
                            sample_fps: float = 1.0) -> list[tuple[float, list[dict]]]:
        rng = random.Random(self.seed)
        frames = []
        step = 1.0 / sample_fps
        t = 0.0
        while t <= duration_sec:
            cands = []
            for f0, f1, spot_type, (bx1, by1, bx2, by2) in self._WINDOWS:
                if f0 * duration_sec <= t <= f1 * duration_sec:
                    jitter = lambda: rng.uniform(-0.01, 0.01)  # boxes wobble a little frame to frame
                    x1, y1 = (bx1 + jitter()) * width, (by1 + jitter()) * height
                    x2, y2 = (bx2 + jitter()) * width, (by2 + jitter()) * height
                    area = (x2 - x1) * (y2 - y1)
                    cands.append({
                        "bounding_box": [round(x1), round(y1), round(x2), round(y2)],
                        "spot_type": spot_type,
                        "area_pixels": round(area),
                        "score": round(min(1.0, area / (width * height) * 3) *
                                       rng.uniform(0.85, 1.0), 3),
                    })
            frames.append((round(t, 2), cands))
            t += step
        return frames
