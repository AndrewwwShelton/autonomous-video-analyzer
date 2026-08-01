"""Tests for benchmark scoring — the matching rules are where scoring goes wrong."""
import pytest

from src.benchmark.evaluator import (Metrics, interval_iou, match_events,
                                     match_intervals, per_category)
from src.benchmark.runner import validate_label


def ev(key, time):
    return {"key": key, "time": time}


# ------------------------------------------------------------------ metrics

def test_metrics_rates():
    m = Metrics(tp=8, fp=2, fn=5)
    assert m.precision == pytest.approx(0.8)
    assert m.recall == pytest.approx(8 / 13)
    assert m.support == 13


def test_metrics_do_not_divide_by_zero():
    m = Metrics()
    assert (m.precision, m.recall, m.f1) == (0.0, 0.0, 0.0)


def test_metrics_sum_across_clips():
    total = sum([Metrics(1, 2, 3), Metrics(4, 5, 6)], Metrics())
    assert (total.tp, total.fp, total.fn) == (5, 7, 9)


# ------------------------------------------------------------------ matching

def test_exact_match_within_tolerance():
    r = match_events([ev("damn", 10.0)], [ev("damn", 10.6)], tolerance_sec=2.0)
    assert (r.metrics.tp, r.metrics.fp, r.metrics.fn) == (1, 0, 0)


def test_match_rejected_outside_tolerance():
    r = match_events([ev("damn", 10.0)], [ev("damn", 44.0)], tolerance_sec=2.0)
    assert (r.metrics.tp, r.metrics.fp, r.metrics.fn) == (0, 1, 1)


def test_wrong_word_is_not_a_match():
    r = match_events([ev("damn", 10.0)], [ev("hell", 10.0)], tolerance_sec=2.0)
    assert (r.metrics.tp, r.metrics.fp, r.metrics.fn) == (0, 1, 1)


def test_matching_is_case_insensitive():
    r = match_events([ev("Damn", 10.0)], [ev("damn", 10.0)])
    assert r.metrics.tp == 1


def test_one_truth_cannot_be_claimed_twice():
    """A model repeating the same flag must not earn several true positives."""
    r = match_events([ev("gun", 10.0)],
                     [ev("gun", 10.1), ev("gun", 10.2), ev("gun", 10.3)])
    assert (r.metrics.tp, r.metrics.fp, r.metrics.fn) == (1, 2, 0)


def test_closest_prediction_wins():
    r = match_events([ev("gun", 10.0)], [ev("gun", 11.5), ev("gun", 10.1)])
    matched_truth, matched_pred, delta = r.matched[0]
    assert matched_pred["time"] == 10.1
    assert delta == pytest.approx(0.1)


def test_repeated_word_at_distinct_times_matches_pairwise():
    r = match_events([ev("damn", 5.0), ev("damn", 30.0)],
                     [ev("damn", 5.2), ev("damn", 30.4)])
    assert (r.metrics.tp, r.metrics.fp, r.metrics.fn) == (2, 0, 0)


def test_empty_prediction_is_all_false_negatives():
    r = match_events([ev("a", 1.0), ev("b", 2.0)], [])
    assert (r.metrics.tp, r.metrics.fn) == (0, 2)


def test_empty_truth_is_all_false_positives():
    r = match_events([], [ev("a", 1.0)])
    assert (r.metrics.tp, r.metrics.fp) == (0, 1)


def test_per_category_isolates_weak_classes():
    truth = [ev("Weapon", 5.0), ev("Substance", 10.0)]
    pred = [ev("Weapon", 5.2)]           # substance missed entirely
    cats = per_category(truth, pred, tolerance_sec=2.0)
    assert cats["weapon"].precision == 1.0
    assert cats["substance"].recall == 0.0


# ------------------------------------------------------------------ intervals

def test_interval_iou():
    assert interval_iou((0, 10), (0, 10)) == pytest.approx(1.0)
    assert interval_iou((0, 10), (20, 30)) == 0.0
    assert interval_iou((0, 10), (5, 15)) == pytest.approx(5 / 15)


def test_ad_spot_overlap_match():
    r = match_intervals([{"start": 10.0, "end": 20.0}],
                        [{"start": 11.0, "end": 19.0}], iou_threshold=0.3)
    assert r.metrics.tp == 1


def test_ad_spot_insufficient_overlap_is_a_miss():
    r = match_intervals([{"start": 10.0, "end": 20.0}],
                        [{"start": 19.5, "end": 40.0}], iou_threshold=0.3)
    assert (r.metrics.tp, r.metrics.fp, r.metrics.fn) == (0, 1, 1)


# ------------------------------------------------------------------ labels

def test_valid_label_passes():
    assert validate_label({
        "clip": "a.mp4",
        "audio": [{"word": "damn", "at": 3.0}],
        "visual": [{"category": "Weapon", "at": 8.0}],
        "ad_spots": [{"start": 1.0, "end": 9.0}],
    }) == []


def test_label_problems_are_reported():
    problems = validate_label({
        "audio": [{"word": "damn"}],                       # missing 'at'
        "visual": [{"category": "Banana", "at": 2.0}],     # unknown category
        "ad_spots": [{"start": 9.0, "end": 1.0}],          # ends before it starts
    })
    assert len(problems) == 4       # missing clip + the three above
    assert any("missing 'clip'" in p for p in problems)
    assert any("Banana" in p for p in problems)
