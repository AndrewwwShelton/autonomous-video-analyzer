"""Persistent-overlay detection (Module 2, stage 4).

Object detection answers "is there a gun on screen?" but not "is this real?". A
rifle rendered in Call of Duty and a rifle on a table produce the same detection,
so a compliance rule built on detections alone restricts gameplay footage — the
precise context-blind over-flagging this project was written to criticise.

The distinguishing signal is not the weapon. It is the **interface drawn on top of
it**. Gameplay carries a heads-up display: crosshair, health bar, minimap, ammo
counter. These share a property nothing in filmed footage has — they occupy fixed
pixels, frame after frame, while the world behind them moves.

Two measurements separate that from everything else:

  1. **Per-pixel temporal variance.** Overlay pixels barely change. Accumulated in
     one streaming pass (running sum and sum-of-squares), so memory is independent
     of video length — a 1-hour video costs the same ~1 MB as a 30-second one.

  2. **Edges surviving in the temporal mean.** This is the discriminating step. In
     the mean image a static overlay stays *sharp*, because it lands on the same
     pixels every frame; moving content averages into a blur. So an edge that is
     still crisp in the mean, at a pixel that barely varies, is a drawn overlay
     rather than a coincidentally still object.

Neither measurement alone is sufficient, and the failure each one prevents is
worth stating:

  * Variance alone flags letterbox bars, faded-to-black passages and any tripod
    shot. The edge test rejects them: flat regions have no structure in the mean.
  * Edges alone flag every static object in a still scene. The variance test only
    means something when the rest of the frame is moving, which `motion_ratio`
    checks before any verdict is issued.

**What this module honestly detects is a persistent graphical overlay, not a
video game.** A channel watermark, a news lower-third and a livestream donation
bar are all overlays and all trigger it. Gameplay is an *inference* the evidence
supports, which is why the report carries region count and coverage rather than a
bare boolean: a lone small corner region is a watermark, several regions covering
a few percent of the frame is an interface. Callers are expected to weigh the
evidence, and `compliance_verdict` never suppresses a flag on this basis — it
annotates it, so a real weapon is never silently discarded because a game-like
overlay was present.
"""
from dataclasses import dataclass, field

import cv2
import numpy as np


@dataclass
class OverlayParams:
    """Tunable knobs. Defaults chosen against 720p gameplay and filmed footage."""
    work_width: int = 320           # analysis resolution, as in adspots.py
    stable_std_max: float = 4.0     # per-pixel temporal std at or below this is static
    motion_std_min: float = 10.0    # and above this the pixel is genuinely moving
    # The scene must genuinely move before any overlay claim is made. Measured:
    # dynamic footage (gameplay, handheld, moving subject) sits at 98-100%, while
    # a locked-off camera on a mostly still scene sits near 13%. Below this gate a
    # stationary physical object -- a television on a stand, a poster -- is
    # indistinguishable from a drawn overlay, because neither moves and both hold
    # sharp edges in the temporal mean. 0.35 sits in the empty space between the
    # two populations rather than close to either.
    min_motion_ratio: float = 0.35
    canny_low: int = 60
    canny_high: int = 160
    edge_dilate_px: int = 2         # overlay glyphs are thin; thicken before masking
    min_region_area_frac: float = 0.0004   # ignore specks
    min_coverage_frac: float = 0.010       # overlay must cover 1% of frame to count
    strong_coverage_frac: float = 0.030    # and 3% reads as a full interface
    min_frames: int = 8             # fewer than this cannot establish persistence
    bar_flatness_max: float = 6.0   # intensity spread within a letterbox bar row
    bar_margin_px: int = 3          # extra rows trimmed to swallow the bar's edge


@dataclass
class OverlayReport:
    """Evidence, not a verdict on the video. See module docstring."""
    frames_analysed: int = 0
    motion_ratio: float = 0.0        # fraction of frame that genuinely moves
    overlay_coverage: float = 0.0    # fraction that is persistent structured overlay
    regions: list[dict] = field(default_factory=list)   # original-frame coordinates
    verdict: str = "inconclusive"    # "overlay" | "none" | "inconclusive"
    confidence: float = 0.0          # 0..1, how strongly the evidence reads
    reason: str = ""                 # plain English, shown in the interface

    def as_dict(self) -> dict:
        return {
            "frames_analysed": self.frames_analysed,
            "motion_ratio": round(self.motion_ratio, 4),
            "overlay_coverage": round(self.overlay_coverage, 4),
            "region_count": len(self.regions),
            "regions": self.regions,
            "verdict": self.verdict,
            "confidence": round(self.confidence, 3),
            "reason": self.reason,
        }


class OverlayAccumulator:
    """Streams frames and reports on persistent overlays.

    Deliberately incremental: the vision stage already decodes every sampled frame
    for detection, so this rides along on that single pass rather than forcing a
    second decode of the whole file.
    """

    def __init__(self, params: OverlayParams | None = None):
        self.p = params or OverlayParams()
        self._n = 0
        self._sum: np.ndarray | None = None
        self._sumsq: np.ndarray | None = None
        self._shape: tuple[int, int] | None = None      # working (h, w)
        self._source_shape: tuple[int, int] | None = None  # original (h, w)

    # ------------------------------------------------------------- accumulate

    def _prepare(self, frame: np.ndarray) -> np.ndarray:
        """Downscale to the working width and convert to float grayscale."""
        h, w = frame.shape[:2]
        if self._source_shape is None:
            self._source_shape = (h, w)
        scale = self.p.work_width / float(w) if w > self.p.work_width else 1.0
        if scale < 1.0:
            frame = cv2.resize(frame, (self.p.work_width, max(1, round(h * scale))),
                               interpolation=cv2.INTER_AREA)
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) if frame.ndim == 3 else frame
        return gray.astype(np.float64)

    def add(self, frame: np.ndarray) -> None:
        """Fold one sampled frame into the running statistics."""
        gray = self._prepare(frame)
        if self._sum is None:
            self._shape = gray.shape
            self._sum = np.zeros_like(gray)
            self._sumsq = np.zeros_like(gray)
        elif gray.shape != self._shape:
            # Resolution changes mid-video are rare but not impossible; conform to
            # the first frame rather than abandoning the measurement.
            gray = cv2.resize(gray, (self._shape[1], self._shape[0]),
                              interpolation=cv2.INTER_AREA)
        self._sum += gray
        self._sumsq += gray * gray
        self._n += 1

    # ----------------------------------------------------------------- report

    def _statistics(self) -> tuple[np.ndarray, np.ndarray]:
        """Temporal mean and per-pixel standard deviation."""
        mean = self._sum / self._n
        # var = E[x^2] - E[x]^2, clamped: floating-point error can make it -1e-12.
        var = np.maximum(self._sumsq / self._n - mean * mean, 0.0)
        return mean, np.sqrt(var)

    def report(self) -> OverlayReport:
        if self._n < self.p.min_frames or self._sum is None:
            return OverlayReport(
                frames_analysed=self._n, verdict="inconclusive",
                reason=(f"only {self._n} frames analysed; at least "
                        f"{self.p.min_frames} are needed to establish persistence"),
            )

        mean, std = self._statistics()
        total = float(std.size)

        # Does anything actually move? Without motion, "static" is meaningless --
        # a slideshow or a locked-off tripod shot is stable everywhere.
        motion_ratio = float(np.count_nonzero(std > self.p.motion_std_min) / total)
        if motion_ratio < self.p.min_motion_ratio:
            return OverlayReport(
                frames_analysed=self._n, motion_ratio=motion_ratio,
                verdict="inconclusive",
                reason=(f"only {motion_ratio:.0%} of the picture changes over time. "
                        f"With a near-static camera a fixed physical object holds "
                        f"the same sharp, unchanging edges as a drawn overlay, so "
                        f"the two cannot be told apart here."),
            )

        overlay_mask = self._overlay_mask(mean, std)
        regions, coverage = self._regions(overlay_mask)
        return self._judge(motion_ratio, coverage, regions)

    def _overlay_mask(self, mean: np.ndarray, std: np.ndarray) -> np.ndarray:
        """Pixels that are both temporally static and structured in the mean."""
        stable = std <= self.p.stable_std_max

        # Edges in the MEAN image, not in any single frame. A static overlay stays
        # sharp under averaging; moving content blurs away. This is what stops a
        # faded-to-black passage or a still object from reading as overlay.
        mean_u8 = np.clip(mean, 0, 255).astype(np.uint8)
        edges = cv2.Canny(mean_u8, self.p.canny_low, self.p.canny_high)
        if self.p.edge_dilate_px > 0:
            k = 2 * self.p.edge_dilate_px + 1
            edges = cv2.dilate(edges, np.ones((k, k), np.uint8))

        mask = stable & (edges > 0)
        mask[self._letterbox_bands(mean_u8, std)] = False
        return mask

    def _letterbox_bands(self, mean_u8: np.ndarray, std: np.ndarray) -> np.ndarray:
        """Uniform bars at the frame edges, which are not overlays.

        The bar interior is featureless and correctly ignored, but the *boundary*
        where it meets the picture is a sharp, perfectly stationary edge — the
        strongest overlay signal in the frame if left alone. Measured: 2.22% of
        frame across two regions, reported as a heads-up display.

        Scanning inward from each edge while rows stay flat locates the bars
        without assuming their thickness. A bar carrying HUD glyphs is not flat,
        so the scan stops before it and genuine overlay is preserved.

        A row must be flat in the mean AND temporally frozen. Uniformity alone is
        not enough: busy content often averages to flat grey, so a mean-only test
        chews inward from every edge and deletes exactly the corner and border
        regions where a HUD lives. Measured on a moving scene, that cost the HUD
        case its detection outright.
        """
        h, w = mean_u8.shape
        band = np.zeros((h, w), dtype=bool)
        m = self.p.bar_margin_px

        def is_bar(mean_line: np.ndarray, std_line: np.ndarray) -> bool:
            return (float(mean_line.std()) <= self.p.bar_flatness_max
                    and float(std_line.max()) <= self.p.stable_std_max)

        top = 0
        while top < h // 3 and is_bar(mean_u8[top], std[top]):
            top += 1
        bottom = h - 1
        while bottom > 2 * h // 3 and is_bar(mean_u8[bottom], std[bottom]):
            bottom -= 1
        left = 0
        while left < w // 3 and is_bar(mean_u8[:, left], std[:, left]):
            left += 1
        right = w - 1
        while right > 2 * w // 3 and is_bar(mean_u8[:, right], std[:, right]):
            right -= 1

        if top > 0:
            band[:min(h, top + m), :] = True
        if bottom < h - 1:
            band[max(0, bottom - m):, :] = True
        if left > 0:
            band[:, :min(w, left + m)] = True
        if right < w - 1:
            band[:, max(0, right - m):] = True
        return band

    def _regions(self, mask: np.ndarray) -> tuple[list[dict], float]:
        """Connected overlay areas in ORIGINAL coordinates, plus total extent.

        Coverage is the union of region *bounding boxes*, not the count of lit
        mask pixels. The mask holds edges, so a minimap outline is a thin ring and
        a filled panel is only its border; counting ink measures how much was
        drawn, when the question is how much of the frame the interface occupies.
        Measured on the same footage, ink read 1.1% where extent reads about 6%.
        Union rather than sum, so overlapping boxes are not counted twice.
        """
        h, w = mask.shape
        total = float(h * w)
        min_area = self.p.min_region_area_frac * total
        count, _, stats, _ = cv2.connectedComponentsWithStats(
            mask.astype(np.uint8), connectivity=8)

        sh, sw = self._source_shape or (h, w)
        fx, fy = sw / float(w), sh / float(h)

        extent = np.zeros((h, w), dtype=bool)
        regions = []
        for i in range(1, count):                    # 0 is the background
            x, y, bw, bh, area = stats[i]
            if area < min_area:
                continue
            extent[y:y + bh, x:x + bw] = True
            regions.append({
                "box": [round(x * fx), round(y * fy),
                        round((x + bw) * fx), round((y + bh) * fy)],
                "area_frac": round(bw * bh / total, 5),
                "ink_frac": round(area / total, 5),
                "position": _position_of(x + bw / 2, y + bh / 2, w, h),
            })
        regions.sort(key=lambda r: r["area_frac"], reverse=True)
        return regions, float(np.count_nonzero(extent) / total)

    def _judge(self, motion_ratio: float, coverage: float,
               regions: list[dict]) -> OverlayReport:
        """Turn the measurements into a graded, explainable verdict."""
        report = OverlayReport(
            frames_analysed=self._n, motion_ratio=motion_ratio,
            overlay_coverage=coverage, regions=regions,
        )

        if coverage < self.p.min_coverage_frac or not regions:
            report.verdict = "none"
            report.confidence = 0.0
            report.reason = (
                f"no persistent overlay found: {coverage:.2%} of the frame is "
                f"fixed structure, against a {self.p.min_coverage_frac:.0%} "
                f"threshold. Consistent with filmed footage."
            )
            return report

        report.verdict = "overlay"
        # Confidence rises with coverage and with the number of distinct regions.
        # One small corner region is a watermark; several spread around the frame
        # is an interface. Both are overlays -- they differ in what they imply.
        spread = min(1.0, len(regions) / 4.0)
        extent = min(1.0, coverage / self.p.strong_coverage_frac)
        report.confidence = round(0.35 * spread + 0.65 * extent, 3)

        where = ", ".join(sorted({r["position"] for r in regions[:4]}))
        if len(regions) == 1 and coverage < self.p.strong_coverage_frac:
            report.reason = (
                f"one fixed graphical region ({coverage:.2%} of frame, {where}) "
                f"persists while {motion_ratio:.0%} of the picture moves. A single "
                f"small region is more consistent with a channel watermark than "
                f"with a game interface."
            )
        else:
            report.reason = (
                f"{len(regions)} fixed graphical regions ({coverage:.2%} of frame; "
                f"{where}) persist while {motion_ratio:.0%} of the picture moves. "
                f"That pattern is characteristic of a heads-up display, as found in "
                f"gameplay footage."
            )
        return report


def _position_of(cx: float, cy: float, w: int, h: int) -> str:
    """Coarse placement label, for explaining findings in the interface."""
    col = "left" if cx < w / 3 else "right" if cx > 2 * w / 3 else "centre"
    row = "top" if cy < h / 3 else "bottom" if cy > 2 * h / 3 else "middle"
    if row == "middle" and col == "centre":
        return "centre"
    return f"{row}-{col}"


def analyse_frames(frames) -> OverlayReport:
    """Convenience wrapper for a finite iterable of frames (used by tests)."""
    acc = OverlayAccumulator()
    for f in frames:
        acc.add(f)
    return acc.report()


class DemoOverlayFinder:
    """Deterministic stand-in, matching the other Demo* engines.

    Demo mode has a twin for every model-backed engine so the interface can be
    shown without weights. Overlay detection needs one for the same reason: the
    'Review' verdict only appears when weapon findings meet overlay evidence, and
    without this it could never be demonstrated in the mode the tool is presented
    in.

    Its output is clearly labelled as demo in `reason`, and the pipeline names it
    as the producing engine, so a synthetic finding cannot be mistaken for a
    measured one. Alternating on the seed keeps a library varied rather than
    every video reporting the same thing.
    """

    name = "demo-overlay"

    def __init__(self, seed: int = 0):
        self.seed = seed

    def report(self, frames_analysed: int = 40) -> OverlayReport:
        if self.seed % 2 == 0:
            return OverlayReport(
                frames_analysed=frames_analysed, motion_ratio=0.18,
                overlay_coverage=0.0, verdict="none", confidence=0.0,
                reason="DEMO OUTPUT — no persistent overlay found. Consistent "
                       "with filmed footage.",
            )
        return OverlayReport(
            frames_analysed=frames_analysed, motion_ratio=0.94,
            overlay_coverage=0.078, confidence=0.91, verdict="overlay",
            regions=[
                {"box": [24, 456, 285, 513], "area_frac": 0.0287,
                 "ink_frac": 0.004, "position": "bottom-left"},
                {"box": [765, 15, 936, 153], "area_frac": 0.0455,
                 "ink_frac": 0.006, "position": "top-right"},
                {"box": [735, 468, 876, 516], "area_frac": 0.0119,
                 "ink_frac": 0.003, "position": "bottom-right"},
            ],
            reason="DEMO OUTPUT — 3 fixed graphical regions (7.80% of frame; "
                   "bottom-left, bottom-right, top-right) persist while 94% of "
                   "the picture moves. That pattern is characteristic of a "
                   "heads-up display, as found in gameplay footage.",
        )
