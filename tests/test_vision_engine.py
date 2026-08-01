"""M2 tests — the detection contract and the label-normalisation boundary.

Model inference itself is verified separately against real photographs; these cover
the surrounding logic, which is where swapping weights later is most likely to break
something silently.
"""
import pytest

from src.vision.detector import (RISK_CATEGORY_MAP, SURFACE_CLASSES, Detection,
                                 DemoDetector, YoloDetector, normalise_label,
                                 resolve_weights, to_risk_flags)


def det(label, conf=0.9, box=None, ts=1.0):
    return Detection(label=label, confidence=conf, box=box or [1, 2, 3, 4], timestamp=ts)


# ------------------------------------------------------- label normalisation

def test_coco_risk_classes_map_to_categories():
    assert normalise_label("knife") == "Weapon"
    assert normalise_label("bottle") == "Substance"
    assert normalise_label("wine glass") == "Substance"


def test_specialist_classes_map_even_though_coco_lacks_them():
    """The map is ready for a risk model; COCO simply never emits these labels."""
    assert normalise_label("gun") == "Weapon"
    assert normalise_label("cigarette") == "Substance"
    assert normalise_label("blood") == "Graphic"


def test_normalisation_is_case_and_whitespace_insensitive():
    assert normalise_label("  KNIFE ") == "Weapon"


def test_scenery_is_not_a_risk():
    for label in ("person", "bus", "chair", "laptop", "dog"):
        assert normalise_label(label) is None


def test_every_mapped_category_is_a_valid_ddd_value():
    """VisualFlags has a CHECK constraint; an unknown category would fail insertion."""
    assert set(RISK_CATEGORY_MAP.values()) <= {"Weapon", "Substance", "Graphic"}


def test_surface_classes_do_not_overlap_risk_classes():
    """Occupancy classes feed M3a ad-spots and must never be flagged as risks."""
    assert not (SURFACE_CLASSES & set(RISK_CATEGORY_MAP))


# ------------------------------------------------------- detection -> flags

def test_only_risk_detections_become_flags():
    flags = to_risk_flags([det("person"), det("knife"), det("bus"), det("bottle")])
    assert [f["object_detected"] for f in flags] == ["knife", "bottle"]


def test_flag_shape_matches_the_repository_contract():
    flags = to_risk_flags([det("knife", conf=0.77, box=[10, 20, 30, 40], ts=12.5)])
    f = flags[0]
    assert f == {
        "frame_timestamp": 12.5,
        "object_detected": "knife",
        "bounding_box": [10, 20, 30, 40],
        "confidence_score": 0.77,
        "risk_category": "Weapon",
    }


def test_no_detections_yields_no_flags():
    assert to_risk_flags([]) == []


# ------------------------------------------------------- detector plumbing

def test_models_are_loaded_lazily():
    """Constructing must not pull weights; analysis of a demo run would stall."""
    d = YoloDetector(("yolov8n.pt",))
    assert d._models == []


def test_detector_name_records_every_weight_file():
    assert YoloDetector(("yolov8n.pt",)).name == "yolo:yolov8n"
    assert YoloDetector(("yolov8n.pt", "risk_yolov8.pt")).name == "yolo:yolov8n+risk_yolov8"


def test_weights_resolve_to_models_dir_when_present(tmp_path, monkeypatch):
    from src import config
    monkeypatch.setattr(config, "MODELS_DIR", tmp_path)
    (tmp_path / "yolov8n.pt").write_bytes(b"stub")
    assert resolve_weights("yolov8n.pt") == str(tmp_path / "yolov8n.pt")


def test_unknown_weights_pass_through_for_ultralytics_to_fetch(tmp_path, monkeypatch):
    from src import config
    monkeypatch.setattr(config, "MODELS_DIR", tmp_path)
    assert resolve_weights("yolov8s.pt") == "yolov8s.pt"


# ------------------------------------------------------- demo twin parity

def test_demo_detector_emits_the_same_flag_shape():
    flags = DemoDetector(seed=3).detect(40.0, 1280, 720)
    assert flags
    for f in flags:
        assert set(f) == {"frame_timestamp", "object_detected", "bounding_box",
                          "confidence_score", "risk_category"}
        assert f["risk_category"] in ("Weapon", "Substance", "Graphic")


def test_demo_detector_is_deterministic():
    assert DemoDetector(seed=7).detect(30.0, 640, 480) == \
           DemoDetector(seed=7).detect(30.0, 640, 480)


def test_demo_boxes_stay_inside_the_frame():
    for f in DemoDetector(seed=1).detect(30.0, 640, 480):
        x1, y1, x2, y2 = f["bounding_box"]
        assert 0 <= x1 < x2 <= 640
        assert 0 <= y1 < y2 <= 480
