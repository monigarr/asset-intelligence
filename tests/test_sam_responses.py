"""SAM Responses-adapter tests: grammar -> image-pixel Segmentations.

Uses a captured live SAM 3.1 grammar (tests/fixtures/sam_crack.txt):
box x1=690 y1=151 x2=1048 y2=660 in a 1600x1600 source frame, one mask.
No network, no key.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from app.gateway.errors import MetaResponseError
from app.gateway.sam_responses import (
    UNSCORED_CONFIDENCE,
    encode_coco_rle,
    parse_segmentation_output,
)
from app.sam_service import decode_coco_rle

FIXTURE = Path(__file__).parent / "fixtures" / "sam_crack.txt"


def _grammar() -> str:
    return FIXTURE.read_text(encoding="utf-8")


def test_parse_fixture_exact_pixels() -> None:
    masks = parse_segmentation_output(_grammar(), image_size=(1024, 1024), label="crack")
    assert len(masks) == 1
    mask = masks[0]
    assert mask.mask_id == "mask-1"
    assert mask.label == "crack" and mask.source_image == "image_0"
    assert mask.confidence == UNSCORED_CONFIDENCE == 0.5  # live grammar omits c
    assert mask.bbox == [441, 96, 672, 424]
    assert isinstance(mask.rle, dict)
    assert mask.rle["size"] == [1024, 1024]
    assert sum(mask.rle["counts"]) == 1024 * 1024
    bitmap = decode_coco_rle(mask.rle["counts"], 1024, 1024)
    assert bitmap.sum() > 0
    x1, y1, x2, y2 = mask.bbox
    assert bitmap[:y1, :].sum() == 0 and bitmap[y2:, :].sum() == 0
    assert bitmap[:, :x1].sum() == 0 and bitmap[:, x2:].sum() == 0


def test_parse_rescales_to_small_images() -> None:
    masks = parse_segmentation_output(
        _grammar(), image_size=(64, 48), label="crack", id_prefix="mp0"
    )
    assert [m.mask_id for m in masks] == ["mp0-1"]
    assert masks[0].bbox == [27, 4, 42, 20]


def test_parse_empty_text_is_no_match() -> None:
    assert parse_segmentation_output("", image_size=(64, 48), label="x") == []


def test_parse_malformed_record_fails_closed() -> None:
    with pytest.raises(MetaResponseError, match="rejected"):
        parse_segmentation_output("<0f>999", image_size=(64, 48), label="x")


def test_encode_roundtrip_random() -> None:
    rng = np.random.default_rng(7)
    bitmap = rng.random((9, 13)) < 0.3
    assert np.array_equal(decode_coco_rle(encode_coco_rle(bitmap), 9, 13), bitmap)


def test_encode_hand_vector() -> None:
    bitmap = np.array([[True, False], [False, True]])
    # column-major flat: T,F,F,T -> bgx0, fgx1, bgx2, fgx1
    assert encode_coco_rle(bitmap) == [0, 1, 2, 1]
    assert np.array_equal(decode_coco_rle([0, 1, 2, 1], 2, 2), bitmap)
