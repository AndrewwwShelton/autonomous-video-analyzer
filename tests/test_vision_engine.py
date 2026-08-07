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


def test_every_fine_tuned_class_is_mapped():
    """Guards the detector.py boundary against a silent whole-class dropout.

    An unmapped class is detected by the model and then discarded here without
    trace. Five of the fine-tune's classes were unmapped when the trained
    vocabulary first landed, so this checks the training class list explicitly.
    """
    from training.download_dataset import CLASSES
    unmapped = [c for c in CLASSES if normalise_label(c) is None]
    assert not unmapped, (
        f"classes trained but not mapped to a risk category: {unmapped}. "
        f"Add them to RISK_CATEGORY_MAP or their detections are silently dropped."
    )


def test_training_classes_are_unique():
    """A duplicate would take a quota slot and corrupt the YOLO index mapping."""
    from training.download_dataset import CLASSES
    duplicates = {c for c in CLASSES if CLASSES.count(c) > 1}
    assert not duplicates, f"duplicated training classes: {duplicates}"


def test_uncovered_classes_are_never_requested_from_open_images():
    """Open Images V7 has no cigarette, drug or blood class.

    RISK_CATEGORY_MAP lists them so other weights would work, which makes it easy
    to assume they can simply be added to the download list. They cannot: the
    downloader would skip them silently and the taxonomy would claim coverage the
    model does not have.
    """
    from training.download_dataset import CLASSES, UNCOVERED
    requested = {c.lower() for c in CLASSES} & {u.lower() for u in UNCOVERED}
    assert not requested, (
        f"{sorted(requested)} cannot be sourced from Open Images V7. "
        f"Covering them needs a different dataset, not a bigger download."
    )


def test_classes_too_sparse_to_learn_are_not_requested():
    """Axe and Syringe exist in Open Images but are near-absent from the splits
    this project sources from -- 2 and 19 training instances, zero validation.

    They were requested in a real run and pruned. Re-adding them looks harmless,
    which is exactly why it needs a guard: a class with no validation instances
    reports a meaningless score while detecting nothing.
    """
    from training.download_dataset import CLASSES, TOO_SPARSE_IN_THESE_SPLITS
    requested = {c.lower() for c in CLASSES} & {
        s.lower() for s in TOO_SPARSE_IN_THESE_SPLITS}
    assert not requested, (
        f"{sorted(requested)} is too sparse in the test/validation splits to "
        f"learn. Raising the quota does not help -- the images are not there."
    )


def test_training_class_list_matches_the_prepared_dataset():
    """CLASSES and dataset.yaml drifting apart silently mislabels everything.

    YOLO label files address classes by integer index, so if prune_classes.py has
    reduced the dataset and CLASSES still lists the original set, every index
    beyond the first divergence points at the wrong class.
    """
    import pytest
    import yaml
    from training.download_dataset import CLASSES, DATASET_DIR
    data_yaml = DATASET_DIR / "dataset.yaml"
    if not data_yaml.exists():
        pytest.skip("no prepared dataset (datasets/ is gitignored)")
    names = yaml.safe_load(data_yaml.read_text(encoding="utf-8"))["names"]
    prepared = [names[i] for i in sorted(names)]
    assert prepared == CLASSES, (
        f"dataset.yaml has {prepared}\nbut CLASSES is {CLASSES}.\n"
        f"Re-run the download, or align CLASSES with what prune_classes.py left."
    )


# ------------------------------------------------------- detection -> flags

def test_only_risk_detections_become_flags():
    flags = to_risk_flags([det("person"), det("knife"), det("bus"), det("bottle")])
    assert [f["object_detected"] for f in flags] == ["knife", "bottle"]


def test_flag_shape_matches_the_repository_contract():
    flags = to_risk_flags([det("knife", conf=0.77, box=[10, 20, 30, 40], ts=12.5)],
                          detection_model="yolo:yolov8n")
    f = flags[0]
    assert f == {
        "frame_timestamp": 12.5,
        "object_detected": "knife",
        "bounding_box": [10, 20, 30, 40],
        "confidence_score": 0.77,
        "risk_category": "Weapon",
        "detection_model": "yolo:yolov8n",
    }


def test_demo_detections_are_labelled_as_demo():
    """Provenance per flag, as AudioFlags has always carried.

    Without it, demo detections -- invented at fixed fractions of the runtime,
    touching no pixels -- were indistinguishable from measured ones in the
    interface. A real news clip analysed in demo mode was reported as a genuine
    misclassification because of exactly this gap.
    """
    for f in DemoDetector(seed=3).detect(40.0, 1280, 720):
        assert "demo" in f["detection_model"].lower(), f


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
                          "confidence_score", "risk_category", "detection_model"}
        assert f["risk_category"] in ("Weapon", "Substance", "Graphic")


def test_demo_detector_is_deterministic():
    assert DemoDetector(seed=7).detect(30.0, 640, 480) == \
           DemoDetector(seed=7).detect(30.0, 640, 480)


def test_demo_boxes_stay_inside_the_frame():
    for f in DemoDetector(seed=1).detect(30.0, 640, 480):
        x1, y1, x2, y2 = f["bounding_box"]
        assert 0 <= x1 < x2 <= 640
        assert 0 <= y1 < y2 <= 480
