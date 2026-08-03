"""M3a tests — the free-space algorithm.

The maximal-rectangle search is the part most likely to be subtly wrong, so it is
tested against hand-constructed masks whose answer can be verified by eye.
"""
import numpy as np
import pytest

from src.vision.adspots import (AdSpotParams, busy_mask, classify_spot,
                                find_ad_spot_candidates, largest_free_rectangle,
                                occupancy_mask, score_spot, top_free_rectangles)


def free_grid(rows: list[str]) -> np.ndarray:
    """Build a mask from art: '.' is free, '#' is blocked."""
    return np.array([[c == "." for c in row] for row in rows], dtype=bool)


# ------------------------------------------------------- maximal rectangle

def test_entirely_free_frame_returns_everything():
    area, x1, y1, x2, y2 = largest_free_rectangle(np.ones((10, 20), dtype=bool))
    assert area == 200
    assert (x1, y1, x2, y2) == (0, 0, 20, 10)


def test_entirely_blocked_frame_returns_nothing():
    assert largest_free_rectangle(np.zeros((10, 20), dtype=bool))[0] == 0


def test_finds_a_block_rather_than_the_longest_row():
    """The best answer is two-dimensional, not the widest single row.

    Columns free in every row are {5,6,7} -> 3 wide x 4 tall = 12; rows 1-3 give
    {4,5,6,7} -> 4 wide x 3 tall = 12. Either is valid and both beat the 5-wide
    top row, which is the trap a row-wise scan would fall into.
    """
    mask = free_grid([
        "#####.....",
        "####....##",
        "####....##",
        "####....##",
    ])
    area, x1, y1, x2, y2 = largest_free_rectangle(mask)
    assert area == 12
    assert area == (x2 - x1) * (y2 - y1)       # the reported box matches the area
    assert mask[y1:y2, x1:x2].all()            # and every pixel in it really is free


def test_prefers_wide_over_tall_when_larger():
    mask = free_grid([
        "..........",
        "..........",
        "###..#####",
        "###..#####",
    ])
    area, _x1, y1, _x2, y2 = largest_free_rectangle(mask)
    assert area == 20          # the full 10x2 band
    assert (y1, y2) == (0, 2)


def test_rectangle_around_a_central_obstacle():
    mask = free_grid([
        "........",
        "..####..",
        "..####..",
        "........",
    ])
    area, _, _, _, _ = largest_free_rectangle(mask)
    assert area == 8           # a full 8-wide row band of height 1


def test_top_rectangles_do_not_overlap():
    mask = free_grid([
        "....##....",
        "....##....",
        "....##....",
        "....##....",
    ])
    rects = top_free_rectangles(mask, count=2, min_area=1, min_side=1)
    assert len(rects) == 2
    (ax1, ay1, ax2, ay2), (bx1, by1, bx2, by2) = rects
    assert ax2 <= bx1 or bx2 <= ax1 or ay2 <= by1 or by2 <= ay1


def test_small_rectangles_are_rejected():
    mask = free_grid([
        "#########.",
        "##########",
    ])
    assert top_free_rectangles(mask, count=3, min_area=5, min_side=2) == []


def test_slivers_are_rejected_despite_large_area():
    """A 1-pixel-tall strip has area but is useless as an advertisement surface."""
    mask = np.zeros((10, 40), dtype=bool)
    mask[5, :] = True                       # area 40, height 1
    assert top_free_rectangles(mask, count=1, min_area=10, min_side=3) == []


# ------------------------------------------------------------------ masks

def test_occupancy_marks_detection_boxes():
    mask = occupancy_mask((100, 100), [[10, 10, 30, 30]], scale=1.0, dilate_px=0)
    assert mask[20, 20]
    assert not mask[50, 50]
    assert mask.sum() == 400


def test_occupancy_applies_scale():
    """Boxes arrive in full-resolution coordinates and must be scaled down."""
    mask = occupancy_mask((50, 50), [[20, 20, 60, 60]], scale=0.5, dilate_px=0)
    assert mask[15, 15]        # 30,30 in working space
    assert not mask[5, 5]


def test_occupancy_dilation_grows_the_box():
    plain = occupancy_mask((100, 100), [[40, 40, 60, 60]], 1.0, 0).sum()
    grown = occupancy_mask((100, 100), [[40, 40, 60, 60]], 1.0, 5).sum()
    assert grown > plain


def test_occupancy_clips_to_frame():
    mask = occupancy_mask((50, 50), [[-20, -20, 500, 500]], 1.0, 10)
    assert mask.all()


def test_busy_mask_flags_texture_and_spares_flat_regions():
    p = AdSpotParams()
    flat = np.full((80, 80), 128, dtype=np.uint8)
    assert not busy_mask(flat, p).any()

    noisy = np.random.default_rng(0).integers(0, 255, (80, 80), dtype=np.uint8)
    assert busy_mask(noisy, p).mean() > 0.5


# --------------------------------------------------------------- scoring

def test_score_rewards_large_flat_central_regions():
    gray = np.full((200, 200), 120, dtype=np.uint8)
    central_big = score_spot((50, 50, 150, 150), gray)
    corner_small = score_spot((0, 0, 20, 20), gray)
    assert central_big > corner_small


def test_score_penalises_noise():
    flat = np.full((200, 200), 120, dtype=np.uint8)
    noisy = flat.copy()
    noisy[50:150, 50:150] = np.random.default_rng(1).integers(0, 255, (100, 100))
    assert score_spot((50, 50, 150, 150), flat) > score_spot((50, 50, 150, 150), noisy)


def test_score_is_bounded():
    gray = np.full((100, 100), 128, dtype=np.uint8)
    assert 0.0 <= score_spot((0, 0, 100, 100), gray) <= 1.0


def test_empty_rect_scores_zero():
    assert score_spot((10, 10, 10, 10), np.zeros((50, 50), np.uint8)) == 0.0


# ------------------------------------------------------------ classification

def test_rectangle_over_a_television_is_a_screen():
    spot = classify_spot((10, 10, 50, 50), [("tv", [10, 10, 50, 50])], 1.0, (100, 100))
    assert spot == "screen"


def test_rectangle_above_a_table_is_a_desk():
    spot = classify_spot((10, 10, 50, 40), [("dining table", [10, 45, 50, 80])],
                         1.0, (100, 100))
    assert spot == "empty_desk"


def test_rectangle_with_nothing_nearby_is_a_wall():
    assert classify_spot((10, 10, 50, 50), [], 1.0, (100, 100)) == "blank_wall"


def test_screen_takes_precedence_over_desk():
    """A monitor standing on a desk should be reported as a screen."""
    boxes = [("dining table", [10, 45, 50, 80]), ("tv", [10, 10, 50, 40])]
    assert classify_spot((10, 10, 50, 40), boxes, 1.0, (100, 100)) == "screen"


# ------------------------------------------------------------ end to end

def test_blank_frame_yields_one_large_candidate():
    frame = np.full((360, 640, 3), 200, dtype=np.uint8)
    spots = find_ad_spot_candidates(frame, [])
    assert spots
    x1, y1, x2, y2 = spots[0]["bounding_box"]
    assert (x2 - x1) > 640 * 0.5 and (y2 - y1) > 360 * 0.5
    assert spots[0]["spot_type"] == "blank_wall"


def test_detection_carves_space_out_of_the_candidate():
    frame = np.full((360, 640, 3), 200, dtype=np.uint8)
    from src.vision.detector import Detection
    blocked = find_ad_spot_candidates(
        frame, [Detection("person", 0.9, [0, 0, 320, 360], 0.0)])
    assert blocked
    # Every candidate should now sit clear of the occupied left half.
    for s in blocked:
        assert s["bounding_box"][0] >= 300


def test_noisy_frame_yields_no_usable_surface():
    """Static is unoccupied but unusable — the busy mask must reject it."""
    noisy = np.random.default_rng(3).integers(0, 255, (360, 640, 3), dtype=np.uint8)
    assert find_ad_spot_candidates(noisy, []) == []


def test_candidates_match_the_tracker_contract():
    """Output must slot straight into tracker.merge_candidates."""
    frame = np.full((360, 640, 3), 180, dtype=np.uint8)
    for s in find_ad_spot_candidates(frame, []):
        assert set(s) == {"bounding_box", "spot_type", "area_pixels", "score"}
        assert len(s["bounding_box"]) == 4
        assert 0.0 <= s["score"] <= 1.0


def test_empty_frame_is_handled():
    assert find_ad_spot_candidates(None, []) == []


def test_candidates_are_ordered_largest_first():
    frame = np.full((360, 640, 3), 200, dtype=np.uint8)
    spots = find_ad_spot_candidates(frame, [])
    areas = [s["area_pixels"] for s in spots]
    assert areas == sorted(areas, reverse=True)
