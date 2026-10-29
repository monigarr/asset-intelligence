"""Pure eval metric functions (Stage 1 architecture).

Extracted verbatim from eval/run.py so orchestration changes cannot silently
alter scoring math. Unit-tested in isolation in tests/test_eval_metrics.py;
eval/run.py re-exports these names for backward compatibility.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from typing import Any

from app.sam_service import decode_coco_rle


def percentile_ms(values: Sequence[float], pct: float = 95.0) -> float:
    """Nearest-rank percentile. Raises ValueError when empty."""
    if not values:
        raise ValueError("percentile of empty sequence")
    if not 0 <= pct <= 100:
        raise ValueError(f"percentile {pct} out of range")
    ordered = sorted(values)
    rank = max(0, min(len(ordered) - 1, math.ceil(pct / 100 * len(ordered)) - 1))
    return float(ordered[rank])


def prf_missing(
    predicted: Sequence[str], expected: Sequence[str]
) -> tuple[float, float, float]:
    """Precision/recall/F1 over missing-information key sets."""
    pred, exp = set(predicted), set(expected)
    hit = len(pred & exp)
    precision = 1.0 if not pred else hit / len(pred)
    recall = 1.0 if not exp else hit / len(exp)
    f1 = 0.0 if precision + recall == 0 else 2 * precision * recall / (precision + recall)
    return precision, recall, f1


# Missing-key families: live models emit specific keys (crack_length,
# photo_scale_reference) where the oracle seeds generic ones. Normalizing
# both sides through families scores recovery of the underlying gap instead
# of exact-vocab match. Derived from the seeded-gap intent (ARCH §13), not
# fitted to any single run's outputs.
_DIMENSION_WORDS = frozenset(
    {
        "dimension",
        "dimensions",
        "length",
        "width",
        "depth",
        "extent",
        "extents",
        "size",
        "sizes",
        "area",
        "measurement",
        "measurements",
    }
)


def normalize_missing_keys(keys: Sequence[str]) -> list[str]:
    """Map missing-information keys to canonical families."""
    out: list[str] = []
    for key in keys:
        parts = set(key.split("_"))
        if "date" in parts:
            out.append("inspection_date")
        elif "scale" in parts:
            out.append("scale_reference")
        elif parts & _DIMENSION_WORDS:
            out.append("defect_dimensions")
        else:
            out.append(key)
    return out


def binary_f1(
    y_true: Sequence[bool], y_pred: Sequence[bool]
) -> tuple[float, float, float]:
    """Precision/recall/F1 for binary flags (e.g. has-discrepancy)."""
    if len(y_true) != len(y_pred):
        raise ValueError("length mismatch")
    tp = sum(1 for t, p in zip(y_true, y_pred) if t and p)
    fp = sum(1 for t, p in zip(y_true, y_pred) if not t and p)
    fn = sum(1 for t, p in zip(y_true, y_pred) if t and not p)
    precision = 1.0 if tp + fp == 0 else tp / (tp + fp)
    recall = 1.0 if tp + fn == 0 else tp / (tp + fn)
    f1 = 0.0 if precision + recall == 0 else 2 * precision * recall / (precision + recall)
    return precision, recall, f1


def mask_iou(rle_a: Mapping[str, Any], rle_b: Mapping[str, Any]) -> float:
    """IoU between two COCO RLE dicts (must share size)."""
    if list(rle_a["size"]) != list(rle_b["size"]):
        raise ValueError(f"RLE size mismatch {rle_a['size']} vs {rle_b['size']}")
    height, width = rle_a["size"]
    a = decode_coco_rle(rle_a["counts"], height, width)
    b = decode_coco_rle(rle_b["counts"], height, width)
    union = int((a | b).sum())
    return 1.0 if union == 0 else int((a & b).sum()) / union


def ece(
    uncertainties: Sequence[float], correct: Sequence[bool], bins: int = 10
) -> float:
    """Expected Calibration Error over (uncertainty, correctness) pairs."""
    if len(uncertainties) != len(correct):
        raise ValueError("length mismatch")
    if not uncertainties:
        raise ValueError("ece of empty sequence")
    if bins < 1:
        raise ValueError("bins must be >= 1")
    total, n = 0.0, len(uncertainties)
    for b in range(bins):
        lo, hi = b / bins, (b + 1) / bins
        idx = [
            i
            for i, u in enumerate(uncertainties)
            if (lo <= u < hi) or (u == 1.0 and hi == 1.0)
        ]
        if not idx:
            continue
        confidence = sum(1 - uncertainties[i] for i in idx) / len(idx)
        accuracy = sum(1 for i in idx if correct[i]) / len(idx)
        total += len(idx) / n * abs(accuracy - confidence)
    return total


DIMENSION_UNITS_TO_MM = {
    "mm": 1.0,
    "cm": 10.0,
    "m": 1000.0,
    "meter": 1000.0,
    "meters": 1000.0,
    "feet": 304.8,
    "foot": 304.8,
    "ft": 304.8,
    "in": 25.4,
    "inch": 25.4,
    "inches": 25.4,
}


def normalize_dimension_to_mm(value: float, unit: str) -> float:
    """Convert a dimension to millimeters. Raises ValueError on unknown unit."""
    try:
        factor = DIMENSION_UNITS_TO_MM[unit.strip().lower()]
    except KeyError:
        raise ValueError(f"unknown dimension unit: {unit!r}") from None
    return value * factor


def unfounded_dimensions_mm(
    predicted_mm: Sequence[float],
    expected_mm: Sequence[float],
    *,
    rel_tol: float = 0.05,
    abs_tol_mm: float = 1.0,
) -> list[float]:
    """Predicted dimensions (mm) with no ground-truth match within tolerance."""
    unfounded = []
    for pred in predicted_mm:
        ok = any(
            abs(pred - exp) <= max(abs_tol_mm, rel_tol * abs(exp))
            for exp in expected_mm
        )
        if not ok:
            unfounded.append(pred)
    return unfounded
