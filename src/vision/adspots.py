"""Ad-spot detection (Module 2, stage 3) — the project's novel contribution.

Finding an advertisement surface is **not** an object-detection problem. A blank
wall is the *absence* of objects, and no detector can be trained to find nothing.
This module therefore inverts the question: instead of asking "what is here?", it
asks "where is nothing, for long enough to matter?".

Per sampled frame (PLAN.md §2.2):

  1. **Occupancy mask** — union the COCO detection boxes. Anything a detector
     recognised is, by definition, not empty space.
  2. **Busy mask** — Canny edge density plus local intensity variance. A patterned
     rug is unoccupied but useless to advertise on; texture ruins legibility.
  3. **Free space** = NOT occupied AND NOT busy.
  4. **Largest inscribed rectangles** — maximal-rectangle-in-binary-matrix, solved
     with the histogram/stack method in O(w·h). Advertisements are rectangular, so
     the largest axis-aligned rectangle that fits inside the free region is exactly
     the quantity of interest.
  5. **Classify** the surface from what surrounds it — a screen, a wall, a desk.
  6. **Score** on area, uniformity and centrality.

The temporal pass lives in `tracker.py` and is already real: a surface must persist
for at least five seconds before it becomes a Premium Ad Spot, which filters out
rectangles that only appear because a single frame happened to be uncluttered.

Everything here operates on a downscaled copy. Advertisement placement needs
approximate geometry, not pixel precision, and the DP is linear in pixel count, so
working at ~320 px wide makes the whole pass roughly thirty times cheaper with no
practical loss.
"""
import random
from dataclasses import dataclass

import cv2
import numpy as np

# Detector classes that indicate what a nearby free region probably is.
SCREEN_CLASSES = {"tv", "laptop", "monitor", "television"}
DESK_CLASSES = {"dining table", "desk", "table", "keyboard", "mouse", "book"}


@dataclass
class AdSpotParams:
    """Tunable knobs. Defaults chosen against 720p indoor footage."""
    work_width: int = 320          # analysis resolution
    box_dilate_frac: float = 0.01  # grow detections slightly; objects have shadows
    canny_low: int = 50
    canny_high: int = 150
    edge_density_max: float = 0.02  # fraction of edge pixels tolerated in a window
    variance_max: float = 90.0      # local intensity variance tolerated
    texture_window: int = 9
    min_area_frac: float = 0.02     # ignore rectangles under 2% of the frame
    min_side_frac: float = 0.08     # and slivers, whatever their area
    max_candidates: int = 3


# --------------------------------------------------------------------- masks

def occupancy_mask(shape: tuple[int, int], boxes: list[list[int]],
                   scale: float, dilate_px: int) -> np.ndarray:
    """True where a detector found something. Boxes arrive in original coordinates."""
    h, w = shape
    mask = np.zeros((h, w), dtype=bool)
    for x1, y1, x2, y2 in boxes:
        sx1 = max(0, int(x1 * scale) - dilate_px)
        sy1 = max(0, int(y1 * scale) - dilate_px)
        sx2 = min(w, int(x2 * scale) + dilate_px)
        sy2 = min(h, int(y2 * scale) + dilate_px)
        if sx2 > sx1 and sy2 > sy1:
            mask[sy1:sy2, sx1:sx2] = True
    return mask


def busy_mask(gray: np.ndarray, p: AdSpotParams) -> np.ndarray:
    """True where the surface is too textured to carry an overlay.

    Two independent signals, because each misses cases the other catches: edge
    density finds hard structure (bookshelves, window frames), local variance finds
    soft clutter and gradients that produce few edges but still read as noisy.
    """
    edges = cv2.Canny(gray, p.canny_low, p.canny_high) > 0
    k = p.texture_window
    density = cv2.boxFilter(edges.astype(np.float32), -1, (k, k), normalize=True)

    f = gray.astype(np.float32)
    mean = cv2.boxFilter(f, -1, (k, k), normalize=True)
    mean_sq = cv2.boxFilter(f * f, -1, (k, k), normalize=True)
    variance = np.maximum(mean_sq - mean * mean, 0.0)

    return (density > p.edge_density_max) | (variance > p.variance_max)


# ------------------------------------------------------- maximal rectangle

def _largest_rect_in_histogram(heights: np.ndarray) -> tuple[int, int, int, int]:
    """Largest rectangle under a histogram: (area, left, right_exclusive, height).

    Classic monotonic-stack solution, linear in the number of bars.
    """
    stack: list[tuple[int, int]] = []          # (start index, height)
    best = (0, 0, 0, 0)
    for i, h in enumerate(np.append(heights, 0)):
        h = int(h)
        start = i
        while stack and stack[-1][1] > h:
            idx, height = stack.pop()
            area = height * (i - idx)
            if area > best[0]:
                best = (area, idx, i, height)
            start = idx
        stack.append((start, h))
    return best


def largest_free_rectangle(free: np.ndarray) -> tuple[int, int, int, int, int]:
    """Largest all-True axis-aligned rectangle: (area, x1, y1, x2, y2).

    Builds, for each row, the height of the free column above it, then solves the
    histogram problem per row. O(rows × cols) overall.
    """
    h, w = free.shape
    heights = np.zeros(w, dtype=np.int32)
    best = (0, 0, 0, 0, 0)
    for y in range(h):
        heights = np.where(free[y], heights + 1, 0)
        area, left, right, height = _largest_rect_in_histogram(heights)
        if area > best[0]:
            best = (area, left, y - height + 1, right, y + 1)
    return best


def top_free_rectangles(free: np.ndarray, count: int,
                        min_area: int, min_side: int) -> list[tuple[int, int, int, int]]:
    """The `count` largest disjoint free rectangles, largest first.

    Greedy: take the biggest, erase it, repeat. Not globally optimal — that problem
    is NP-hard — but the second-best rectangle is rarely worth more than the cost of
    finding it, and erasing guarantees the results do not overlap.
    """
    working = free.copy()
    out = []
    for _ in range(count):
        area, x1, y1, x2, y2 = largest_free_rectangle(working)
        if area < min_area or (x2 - x1) < min_side or (y2 - y1) < min_side:
            break
        out.append((x1, y1, x2, y2))
        working[y1:y2, x1:x2] = False
    return out


# ------------------------------------------------------- classify and score

def classify_spot(rect: tuple[int, int, int, int], labelled_boxes: list[tuple[str, list[int]]],
                  scale: float, frame_shape: tuple[int, int]) -> str:
    """Name the surface from its neighbours.

    A free rectangle sitting on a television is a screen; one resting above a table
    is a desk; anything else large and clear is treated as wall.
    """
    x1, y1, x2, y2 = rect
    h, w = frame_shape

    def scaled(box):
        return [box[0] * scale, box[1] * scale, box[2] * scale, box[3] * scale]

    def overlaps(box) -> bool:
        bx1, by1, bx2, by2 = scaled(box)
        return not (bx2 <= x1 or bx1 >= x2 or by2 <= y1 or by1 >= y2)

    def sits_above(box) -> bool:
        """Rectangle bottom is near the box top, and they share horizontal extent."""
        bx1, by1, bx2, by2 = scaled(box)
        vertical = 0 <= (by1 - y2) <= h * 0.12
        horizontal = min(x2, bx2) - max(x1, bx1) > 0
        return vertical and horizontal

    for label, box in labelled_boxes:
        if label in SCREEN_CLASSES and overlaps(box):
            return "screen"
    for label, box in labelled_boxes:
        if label in DESK_CLASSES and (sits_above(box) or overlaps(box)):
            return "empty_desk"
    return "blank_wall"


def score_spot(rect: tuple[int, int, int, int], gray: np.ndarray) -> float:
    """Combine area, uniformity and centrality into 0..1.

    Multiplicative, as PLAN.md §2.2 specifies, so a rectangle must be reasonable on
    every axis: a huge but noisy region, or a pristine but tiny one, both score low.
    """
    h, w = gray.shape
    x1, y1, x2, y2 = rect
    patch = gray[y1:y2, x1:x2]
    if patch.size == 0:
        return 0.0

    area = min(1.0, (x2 - x1) * (y2 - y1) / float(w * h) / 0.25)   # 25% of frame saturates

    # Uniformity from standard deviation: a flat wall approaches 1, noise approaches 0.
    uniformity = float(np.clip(1.0 - patch.std() / 64.0, 0.0, 1.0))

    # Centrality: distance of the rectangle centre from the frame centre.
    cx, cy = (x1 + x2) / 2.0, (y1 + y2) / 2.0
    dx, dy = abs(cx - w / 2.0) / (w / 2.0), abs(cy - h / 2.0) / (h / 2.0)
    centrality = float(np.clip(1.0 - (dx * dx + dy * dy) ** 0.5 / 1.4142, 0.0, 1.0))

    return round(area * uniformity * centrality, 4)


# --------------------------------------------------------------- entry point

def find_ad_spot_candidates(frame: np.ndarray, coco_detections,
                            params: AdSpotParams | None = None) -> list[dict]:
    """Per-frame ad-spot candidates, ready for the temporal tracker.

    `coco_detections` is any iterable of objects exposing `.label` and `.box`
    (`src.vision.detector.Detection`), or (label, box) pairs.

    Returns dicts shaped for `tracker.merge_candidates`, with boxes mapped back to
    the frame's own coordinates.
    """
    p = params or AdSpotParams()
    if frame is None or frame.size == 0:
        return []

    full_h, full_w = frame.shape[:2]
    scale = min(1.0, p.work_width / float(full_w))
    small = cv2.resize(frame, (max(1, int(full_w * scale)), max(1, int(full_h * scale))),
                       interpolation=cv2.INTER_AREA)
    gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
    sh, sw = gray.shape

    labelled = []
    for d in coco_detections or []:
        if hasattr(d, "label"):
            labelled.append((str(d.label).strip().lower(), list(d.box)))
        else:
            label, box = d
            labelled.append((str(label).strip().lower(), list(box)))

    occupied = occupancy_mask((sh, sw), [b for _, b in labelled], scale,
                              int(p.box_dilate_frac * sw))
    busy = busy_mask(gray, p)
    free = ~(occupied | busy)

    rects = top_free_rectangles(
        free, p.max_candidates,
        min_area=int(p.min_area_frac * sh * sw),
        min_side=int(p.min_side_frac * min(sh, sw)),
    )

    inv = 1.0 / scale if scale else 1.0
    candidates = []
    for rect in rects:
        x1, y1, x2, y2 = rect
        full_box = [int(x1 * inv), int(y1 * inv), int(x2 * inv), int(y2 * inv)]
        candidates.append({
            "bounding_box": full_box,
            "spot_type": classify_spot(rect, labelled, scale, (sh, sw)),
            "area_pixels": int((full_box[2] - full_box[0]) * (full_box[3] - full_box[1])),
            "score": score_spot(rect, gray),
        })
    return candidates


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

    @property
    def name(self) -> str:
        return "demo-adspots"

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
