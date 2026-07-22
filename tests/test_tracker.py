from src.vision.tracker import iou, merge_candidates


def _cand(box, spot_type="blank_wall", score=0.8):
    return {"bounding_box": box, "spot_type": spot_type,
            "area_pixels": (box[2] - box[0]) * (box[3] - box[1]), "score": score}


def test_iou_disjoint_and_identical():
    assert iou([0, 0, 10, 10], [20, 20, 30, 30]) == 0.0
    assert iou([0, 0, 10, 10], [0, 0, 10, 10]) == 1.0


def test_persistent_surface_becomes_one_spot():
    frames = [(float(t), [_cand([100, 100, 300, 300])]) for t in range(0, 9)]
    spots = merge_candidates(frames, min_duration_sec=5.0)
    assert len(spots) == 1
    assert spots[0]["timestamp_start"] == 0.0
    assert spots[0]["timestamp_end"] == 8.0
    assert spots[0]["spot_type"] == "blank_wall"


def test_short_lived_surface_is_dropped():
    frames = [(float(t), [_cand([100, 100, 300, 300])]) for t in range(0, 3)]
    assert merge_candidates(frames, min_duration_sec=5.0) == []


def test_gap_splits_track():
    # 0-3s then a 4s gap then 8-11s: two sub-5s tracks -> nothing survives.
    frames = [(float(t), [_cand([100, 100, 300, 300])]) for t in [0, 1, 2, 3, 8, 9, 10, 11]]
    assert merge_candidates(frames, min_duration_sec=5.0, max_gap_sec=1.5) == []


def test_different_types_never_merge():
    frames = []
    for t in range(0, 9):
        frames.append((float(t), [_cand([100, 100, 300, 300], "blank_wall"),
                                  _cand([100, 100, 300, 300], "screen")]))
    spots = merge_candidates(frames, min_duration_sec=5.0)
    assert sorted(s["spot_type"] for s in spots) == ["blank_wall", "screen"]
