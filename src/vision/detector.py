"""Visual risk detection (Module 2, stage 2).

Contract: a detector takes sampled frames and returns VisualFlags-shaped dicts.

Label normalisation (PLAN.md §5.5): community/custom model class names are mapped to
our DDD risk_category vocabulary (Weapon | Substance | Graphic) HERE, at the detector
boundary — so swapping models later never ripples into the database or UI.
"""
import random

# Raw model label -> DDD risk_category. Extend as community weights are integrated (D1).
RISK_CATEGORY_MAP = {
    "knife": "Weapon", "gun": "Weapon", "pistol": "Weapon", "rifle": "Weapon",
    "handgun": "Weapon", "scissors": "Weapon", "baseball bat": "Weapon",
    "cigarette": "Substance", "smoking": "Substance", "vape": "Substance",
    "bottle": "Substance", "wine glass": "Substance", "alcohol": "Substance",
    "syringe": "Substance", "pills": "Substance",
    "blood": "Graphic", "corpse": "Graphic",
}


def normalise_label(raw_label: str) -> str | None:
    """Map a model's class name to a risk_category; None means 'not a risk class'."""
    return RISK_CATEGORY_MAP.get(raw_label.strip().lower())


class YoloRiskDetector:
    """Real engine — lands in M2 with community weights (decision D1), fine-tune later.

    Implementation sketch:
        from ultralytics import YOLO
        model = YOLO(weights_path)                    # models/risk_yolov8.pt
        results = model(frame, conf=confidence_threshold, verbose=False)
        for box in results[0].boxes:
            label = model.names[int(box.cls)]
            category = normalise_label(label)         # skip None (non-risk classes)
            ...
    """

    def __init__(self, weights_path: str, confidence_threshold: float = 0.5):
        self.weights_path = weights_path
        self.confidence_threshold = confidence_threshold

    def detect(self, frames) -> list[dict]:
        raise NotImplementedError(
            "YoloRiskDetector lands in M2 — source community weights (Roboflow Universe / "
            "HuggingFace), `pip install ultralytics`, implement per the class docstring. "
            "Until then run the pipeline in demo mode."
        )


class DemoDetector:
    """Emits plausible risk detections, deterministic per seed.

    Emits RAW labels and runs them through normalise_label(), exercising the same
    boundary contract the real detector will use.
    """

    _EVENTS = [  # (fraction of duration, raw_label, confidence)
        (0.18, "knife", 0.87),
        (0.31, "bottle", 0.64),
        (0.55, "cigarette", 0.72),
        (0.78, "knife", 0.91),
    ]

    def __init__(self, seed: int = 0):
        self.seed = seed

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
            })
        return flags
