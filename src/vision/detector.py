"""Visual risk detection (Module 2, stage 2).

Architecture follows decision D4 — **two models, one pass over each frame**:

  * **COCO YOLOv8** knows people, furniture, screens and tables. That is what makes
    it useful for scene occupancy, which the M3a ad-spot algorithm consumes. It also
    happens to cover five risk-adjacent classes (knife, scissors, baseball bat,
    bottle, wine glass).
  * **A specialist risk model** is required for the rest of our taxonomy. Verified
    against the shipped weights: COCO's 80 classes contain **no gun, cigarette, or
    drugs**, so those cannot be detected without one. See PLAN.md §0.1 and the
    weights slot below.

Detection therefore returns *raw* detections, and risk classification is a separate
step. One inference pass, two consumers: risk flags now, occupancy masks at M3a.

Class-name normalisation happens at this boundary (PLAN.md §5.5) so swapping in
different weights later never ripples into the database or the UI.
"""
import random
from dataclasses import dataclass
from pathlib import Path

from src import config

# Raw model label -> our DDD risk_category. Community weights arrive with someone
# else's vocabulary, so extend this map rather than touching anything downstream.
RISK_CATEGORY_MAP = {
    # --- present in stock COCO ---
    "knife": "Weapon", "scissors": "Weapon", "baseball bat": "Weapon",
    "bottle": "Substance", "wine glass": "Substance",
    # --- require a specialist model (absent from COCO) ---
    # Firearms and blades: the classes our Open Images fine-tune is trained on
    # (training/download_dataset.py) plus common synonyms other weights may use.
    "gun": "Weapon", "pistol": "Weapon", "rifle": "Weapon", "handgun": "Weapon",
    "shotgun": "Weapon", "firearm": "Weapon", "weapon": "Weapon",
    "dagger": "Weapon", "sword": "Weapon", "axe": "Weapon",
    "kitchen knife": "Weapon", "bow and arrow": "Weapon",
    # Alcohol and other substances.
    "cigarette": "Substance", "smoking": "Substance", "vape": "Substance",
    "alcohol": "Substance", "beer": "Substance", "wine": "Substance",
    "cocktail": "Substance", "syringe": "Substance",
    "pills": "Substance", "drugs": "Substance",
    "blood": "Graphic", "corpse": "Graphic", "gore": "Graphic",
}

# This map is deliberately a SUPERSET of what any loaded model can emit. An entry
# only becomes a detectable label once some model is trained on it, so roughly half
# of these are inert -- forward-compatible synonyms kept so that swapping in
# different weights does not silently drop a whole class. `coverage_report()` is
# the honest view: it intersects this map with the vocabularies actually loaded.
#
# Never covered by the current data source: cigarette, smoking, vape, drugs, pills,
# blood, gore, corpse. Open Images V7 has no such classes (verified against all 601
# boxable names), so those entries cannot go live without a different dataset.

# Classes COCO provides that are useful for ad-spot occupancy at M3a.
SURFACE_CLASSES = {"tv", "laptop", "dining table", "desk", "couch", "chair", "bed"}


def normalise_label(raw_label: str) -> str | None:
    """Map a model's class name to a risk_category. None means 'not a risk class'."""
    return RISK_CATEGORY_MAP.get(raw_label.strip().lower())


@dataclass
class Detection:
    """One raw model output, before any risk interpretation."""
    label: str
    confidence: float
    box: list[int]          # [x1, y1, x2, y2]
    timestamp: float


class DetectorError(RuntimeError):
    """Raised when detection cannot run, with a message fit for the UI."""


# Upper bound on inference resolution. Ultralytics defaults to 640, which silently
# halves 720p and quarters 4K -- and a weapon is a *small* object in real footage.
# Measured on an ATF firing-range clip (1280x720, pistol in an outstretched hand):
#
#     imgsz=640   nothing above 0.07          <- the whole weapon module looked broken
#     imgsz=1280  Knife at 0.657              <- comfortably above the 0.5 threshold
#     imgsz=1920  Knife at 0.562
#
# The model was never blind; the pistol was simply resized below what YOLOv8n can
# resolve. 1280 caps the cost while covering the 720p/1080p footage this tool is
# aimed at. Raising it further mainly buys detections on 4K sources.
DEFAULT_MAX_IMGSZ = 1280
MIN_IMGSZ = 640


def inference_imgsz(frame_width: int, max_imgsz: int = DEFAULT_MAX_IMGSZ) -> int:
    """Inference resolution for a frame of this width, as a multiple of 32.

    Never downscales below the source unnecessarily, because downscaling is what
    made small weapons undetectable; never upscales past it, because that spends
    time without adding information. Clamped so a thumbnail-sized video still gets
    a sane window and a 4K one does not become unusably slow.
    """
    target = max(MIN_IMGSZ, min(int(frame_width), int(max_imgsz)))
    return int(round(target / 32) * 32)


def inference_scales(frame_width: int,
                     max_imgsz: int = DEFAULT_MAX_IMGSZ) -> tuple[int, ...]:
    """The resolutions a frame is run at. Usually two, and that is the point.

    Detection count against resolution, measured on two real clips -- a firing
    range with a pistol at arm's length, and a review with one filling the frame:

        imgsz    distant pistol    close-up pistol
          640          0 flags          10 flags
          960          1                 4
         1280         13                 1
         1600         15                 0

    The relationship is inverted, so **no single resolution serves both**. The
    fine-tune was trained at 512 px: shrink the frame and a distant weapon falls
    below what the network can resolve, enlarge it and a near one grows past the
    scales the model ever saw. Running both ends and merging is what makes the
    module work on real footage rather than only on the framing it was tuned for.

    The cost is roughly double, which is the honest price of the recall.
    """
    low = MIN_IMGSZ
    high = inference_imgsz(frame_width, max_imgsz)
    return (low,) if high == low else (low, high)


def _iou(a: list[int], b: list[int]) -> float:
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    ix1, iy1 = max(ax1, bx1), max(ay1, by1)
    ix2, iy2 = min(ax2, bx2), min(ay2, by2)
    inter = max(0, ix2 - ix1) * max(0, iy2 - iy1)
    if inter == 0:
        return 0.0
    union = ((ax2 - ax1) * (ay2 - ay1)) + ((bx2 - bx1) * (by2 - by1)) - inter
    return inter / union if union else 0.0


def merge_scale_detections(detections: list["Detection"],
                           iou_threshold: float = 0.55) -> list["Detection"]:
    """Collapse the same object found at more than one scale into one detection.

    Without this every object visible at both resolutions is flagged twice, which
    would inflate the counts the compliance report is built on. Highest confidence
    wins; only same-label boxes are compared, so a genuine overlap between, say, a
    person and the weapon they hold is preserved.
    """
    kept: list[Detection] = []
    for d in sorted(detections, key=lambda x: -x.confidence):
        if not any(k.label == d.label and _iou(k.box, d.box) >= iou_threshold
                   for k in kept):
            kept.append(d)
    return kept


def resolve_weights(name_or_path: str) -> str:
    """Prefer a copy under models/; otherwise let ultralytics fetch it by name.

    Keeps downloaded weights with the project's other model assets rather than
    scattering them through whatever directory the process happened to start in.
    """
    config.MODELS_DIR.mkdir(parents=True, exist_ok=True)
    candidate = config.MODELS_DIR / Path(name_or_path).name
    if candidate.exists():
        return str(candidate)
    direct = Path(name_or_path)
    if direct.exists():
        return str(direct)
    return name_or_path  # ultralytics resolves/downloads by name


class YoloDetector:
    """Runs one or more YOLO models over frames and returns raw detections.

    Multiple weight files are supported so the COCO model and a specialist risk
    model can run together; their outputs are merged into one detection list.
    """

    def __init__(self, weights: tuple[str, ...] = ("yolov8n.pt",),
                 confidence_threshold: float = 0.5, device: str | None = None,
                 max_imgsz: int = DEFAULT_MAX_IMGSZ):
        self.weights = tuple(weights)
        self.confidence_threshold = confidence_threshold
        self.device = device
        self.max_imgsz = max_imgsz
        self._models: list = []

    def _load(self) -> list:
        if not self._models:
            try:
                from ultralytics import YOLO
            except ImportError as e:
                raise DetectorError(
                    "ultralytics is not installed. Run: pip install ultralytics"
                ) from e
            for w in self.weights:
                path = resolve_weights(w)
                try:
                    self._models.append(YOLO(path))
                except Exception as e:
                    raise DetectorError(
                        f"Could not load detection weights '{w}'. If this is the first "
                        f"run the file must be downloaded once, which needs a network "
                        f"connection. Underlying error: {e}"
                    ) from e
        return self._models

    def _predict_at(self, model, frame, imgsz: int, timestamp: float) -> list[Detection]:
        """One model, one scale."""
        try:
            results = model.predict(
                frame, conf=self.confidence_threshold, imgsz=imgsz,
                verbose=False, device=self.device,
            )
        except Exception as e:
            raise DetectorError(f"Detection failed: {e}") from e

        found: list[Detection] = []
        for r in results:
            for box in (r.boxes or []):
                x1, y1, x2, y2 = (round(float(v)) for v in box.xyxy[0].tolist())
                found.append(Detection(
                    label=r.names[int(box.cls)],
                    confidence=round(float(box.conf), 3),
                    box=[x1, y1, x2, y2],
                    timestamp=round(timestamp, 3),
                ))
        return found

    def detect_frame(self, frame, timestamp: float = 0.0) -> list[Detection]:
        """All detections above threshold for a single frame (BGR numpy array).

        Every model is run at every scale in `inference_scales`, and the results
        are merged. One resolution cannot cover both a distant weapon and one
        filling the frame -- see the measurements in `inference_scales`.
        """
        out: list[Detection] = []
        for model in self._load():
            for imgsz in inference_scales(frame.shape[1], self.max_imgsz):
                out += self._predict_at(model, frame, imgsz, timestamp)
        return merge_scale_detections(out)

    @property
    def name(self) -> str:
        return "yolo:" + "+".join(Path(w).stem for w in self.weights)


def to_risk_flags(detections: list[Detection],
                  detection_model: str | None = None) -> list[dict]:
    """Keep only detections that map to a risk category; shape them for VisualFlags.

    `detection_model` is recorded per flag, as AudioFlags has always done. Without
    it a demo detection -- invented at a fixed fraction of the duration, touching
    no pixels -- was indistinguishable from a measured one in the interface.
    """
    flags = []
    for d in detections:
        category = normalise_label(d.label)
        if category is None:
            continue                      # scenery, not a compliance risk
        flags.append({
            "frame_timestamp": d.timestamp,
            "object_detected": d.label,
            "bounding_box": d.box,
            "confidence_score": d.confidence,
            "risk_category": category,
            "detection_model": detection_model,
        })
    return flags


def detectable_risk_labels(detector: "YoloDetector") -> set[str]:
    """Which risk labels the loaded weights can actually produce.

    Used to report coverage honestly: a category absent from every loaded model
    will never be flagged, and that is a property of the weights, not the footage.
    """
    labels: set[str] = set()
    for model in detector._load():
        labels |= {str(n).strip().lower() for n in model.names.values()}
    return {lbl for lbl in labels if lbl in RISK_CATEGORY_MAP}


_coverage_cache: dict[tuple, dict] = {}


def coverage_report(weights: tuple[str, ...]) -> dict:
    """What the configured weights can and cannot detect, per risk category.

    Exists so the interface never implies a capability the loaded models lack.
    Silently failing to flag firearms because the weights do not know what one is
    would be the most damaging kind of false negative this tool could produce.
    """
    key = tuple(weights)
    if key in _coverage_cache:
        return _coverage_cache[key]

    report: dict = {"weights": list(weights), "loaded": False, "by_category": {}}
    try:
        detectable = detectable_risk_labels(YoloDetector(key))
        report["loaded"] = True
    except DetectorError as e:
        report["error"] = str(e)
        detectable = set()

    for category in ("Weapon", "Substance", "Graphic"):
        known = {lbl for lbl, cat in RISK_CATEGORY_MAP.items() if cat == category}
        covered = sorted(known & detectable)
        report["by_category"][category] = {
            "covered": covered,
            "missing": sorted(known - detectable),
            "status": ("none" if not covered
                       else "partial" if known - detectable
                       else "full"),
        }
    report["detectable_labels"] = sorted(detectable)
    if report["loaded"]:
        _coverage_cache[key] = report
    return report


class DemoDetector:
    """Emits plausible risk detections, deterministic per seed.

    Emits RAW labels and runs them through normalise_label(), exercising the same
    boundary contract the real detector uses.
    """

    _EVENTS = [  # (fraction of duration, raw_label, confidence)
        (0.18, "knife", 0.87),
        (0.31, "bottle", 0.64),
        (0.55, "cigarette", 0.72),
        (0.78, "knife", 0.91),
    ]

    def __init__(self, seed: int = 0):
        self.seed = seed

    @property
    def name(self) -> str:
        return "demo-detector"

    def detect(self, duration_sec: float, width: int, height: int) -> list[dict]:
        rng = random.Random(self.seed)
        flags = []
        for frac, label, conf in self._EVENTS:
            t = round(frac * duration_sec, 1)
            if t >= duration_sec:
                continue
            x1 = rng.randint(0, int(width * 0.6))
            y1 = rng.randint(0, int(height * 0.6))
            w = rng.randint(int(width * 0.08), int(width * 0.25))
            h = rng.randint(int(height * 0.08), int(height * 0.25))
            flags.append({
                "frame_timestamp": t,
                "object_detected": label,
                "bounding_box": [x1, y1, min(x1 + w, width), min(y1 + h, height)],
                "confidence_score": round(conf + rng.uniform(-0.05, 0.05), 3),
                "risk_category": normalise_label(label),
                # Stamped so the interface can say plainly that nothing was
                # looked at. These events are placed at fixed fractions of the
                # duration and have no relationship to the footage.
                "detection_model": self.name,
            })
        return flags
