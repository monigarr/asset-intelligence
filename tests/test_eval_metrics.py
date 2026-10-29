"""Isolated math-vector tests for eval/metrics.py (Stage 1 architecture)."""

from __future__ import annotations

import pytest

from eval import metrics


def test_percentile_vectors() -> None:
    assert metrics.percentile_ms([10, 20, 30, 40, 50]) == 50.0
    assert metrics.percentile_ms([10, 20, 30, 40, 50], 50) == 30.0
    assert metrics.percentile_ms([7.5]) == 7.5
    with pytest.raises(ValueError, match="empty"):
        metrics.percentile_ms([])
    with pytest.raises(ValueError, match="out of range"):
        metrics.percentile_ms([1.0], 101.0)


def test_prf_missing_vectors() -> None:
    assert metrics.prf_missing(["a", "b"], ["b", "c"]) == pytest.approx((0.5, 0.5, 0.5))
    assert metrics.prf_missing([], []) == (1.0, 1.0, 1.0)
    assert metrics.prf_missing(["a"], [])[0] == 0.0


def test_normalize_missing_keys_families() -> None:
    assert metrics.normalize_missing_keys(["crack_length"]) == ["defect_dimensions"]
    assert metrics.normalize_missing_keys(["photo_scale_reference"]) == ["scale_reference"]
    assert metrics.normalize_missing_keys(["inspection_date"]) == ["inspection_date"]
    assert metrics.normalize_missing_keys(["other_key"]) == ["other_key"]


def test_binary_f1_vectors() -> None:
    p, r, f1 = metrics.binary_f1([True, True, False], [True, False, False])
    assert (p, r, f1) == pytest.approx((1.0, 0.5, 2 / 3))
    assert metrics.binary_f1([], []) == (1.0, 1.0, 1.0)
    with pytest.raises(ValueError, match="length mismatch"):
        metrics.binary_f1([True], [])


def test_mask_iou_vectors() -> None:
    same = {"size": [2, 2], "counts": [4]}
    assert metrics.mask_iou(same, same) == 1.0
    left = {"size": [2, 2], "counts": [1, 1, 2]}
    right = {"size": [2, 2], "counts": [3, 1]}
    assert metrics.mask_iou(left, right) == 0.0
    with pytest.raises(ValueError, match="size mismatch"):
        metrics.mask_iou(same, {"size": [3, 3], "counts": [9]})


def test_ece_vectors() -> None:
    assert metrics.ece([0.0, 0.0], [True, True]) == 0.0
    assert metrics.ece([1.0, 1.0], [True, True]) == pytest.approx(1.0)
    with pytest.raises(ValueError, match="length mismatch"):
        metrics.ece([0.5], [])
    with pytest.raises(ValueError, match="empty"):
        metrics.ece([], [])


def test_normalize_dimension_to_mm() -> None:
    assert metrics.normalize_dimension_to_mm(2, "ft") == pytest.approx(609.6)
    assert metrics.normalize_dimension_to_mm(8, "in") == pytest.approx(203.2)
    assert metrics.normalize_dimension_to_mm(450, "mm") == 450.0
    assert metrics.normalize_dimension_to_mm(1.5, "meters") == pytest.approx(1500.0)
    with pytest.raises(ValueError, match="unknown dimension unit"):
        metrics.normalize_dimension_to_mm(1, "furlongs")


def test_unfounded_dimensions_mm() -> None:
    assert metrics.unfounded_dimensions_mm([609.6], [609.6]) == []
    assert metrics.unfounded_dimensions_mm([610.0], [609.6]) == []  # abs tol
    assert metrics.unfounded_dimensions_mm([100.0], [609.6]) == [100.0]
    assert metrics.unfounded_dimensions_mm([], [609.6]) == []


def test_run_reexports_metrics() -> None:
    from eval import run

    for name in (
        "binary_f1", "ece", "mask_iou", "normalize_dimension_to_mm",
        "normalize_missing_keys", "percentile_ms", "prf_missing",
        "unfounded_dimensions_mm",
    ):
        assert getattr(run, name) is getattr(metrics, name), name
