"""Decode SAM 3.1 Responses-API output into gateway Segmentations.

Live wire format (verified 2026-10-27 against api.meta.ai/v1 and
dev.meta.ai/docs/sam/*): the client POSTs /responses with an input_text
noun-phrase prompt plus an input_image data URL; the completed response's
output_text carries the SAM record grammar, e.g.
``<0f>0<|box;x1=..;y1=..;x2=..;y2=..;w=..;h=..|><|mask;x=0;y=0;data=H,W,~..|>``.

Decoding uses the official zero-dependency ``meta_sam_parser`` package for
records, then this module rescales boxes from SAM source-media coordinates
to image pixels, pastes each box-local raster into a full-image bitmap, and
encodes uncompressed COCO RLE (the pipeline's standing flavor).

GAP decisions (the API omits these):
  - confidence: the box/mask ``c`` fields are optional and absent live, so
    unscored detections get UNSCORED_CONFIDENCE (0.5). 1.0 would fake
    calibration and 0.0 would force low-confidence display on every live
    mask; 0.5 keeps the validator's uncertainty requirement engaged.
  - frame size: parsed records do not retain the box token's w/h, so it is
    recovered with a targeted regex over the same raw grammar the parser
    accepted. Missing/unparseable sizes fail closed.
"""

from __future__ import annotations

import logging
import math
import re
from functools import lru_cache
from typing import TYPE_CHECKING

import numpy as np
from meta_sam_parser import (
    CompletedOutcome,
    SegmentationBoxRecord,
    SegmentationMaskRecord,
    decode_mask_to_raster,
    image_segmentation_format,
)

from app.gateway.errors import MetaResponseError

if TYPE_CHECKING:
    from app.gateway.meta_client import Segmentation

logger = logging.getLogger("asset_intel.sam_responses")

UNSCORED_CONFIDENCE = 0.5

_BOX_TOKEN_RE = re.compile(r"(\d+)<\|box;([^|]*)\|>")
_FRAME_W_RE = re.compile(r"(?:^|;)w=(\d+)")
_FRAME_H_RE = re.compile(r"(?:^|;)h=(\d+)")


def encode_coco_rle(bitmap: np.ndarray) -> list[int]:
    """Encode a bool (H, W) bitmap as uncompressed column-major COCO runs."""
    flat = bitmap.reshape(-1, order="F")
    counts: list[int] = []
    run = 0
    value = False
    for pixel in flat:
        is_fg = bool(pixel)
        if is_fg != value:
            counts.append(run)
            run = 0
            value = is_fg
        run += 1
    counts.append(run)
    return counts


def _frame_sizes(raw_output: str) -> dict[str, tuple[int, int]]:
    """Map grammar object id -> source frame (width, height)."""
    sizes: dict[str, tuple[int, int]] = {}
    for match in _BOX_TOKEN_RE.finditer(raw_output):
        object_id, fields = match.group(1), match.group(2)
        w = _FRAME_W_RE.search(fields)
        h = _FRAME_H_RE.search(fields)
        if w is None or h is None:
            raise MetaResponseError(
                f"SAM box token for object {object_id} omits frame w/h"
            )
        width, height = int(w.group(1)), int(h.group(1))
        if width <= 0 or height <= 0:
            raise MetaResponseError(f"SAM frame size {width}x{height} is invalid")
        sizes[object_id] = (width, height)
    return sizes


def _rescale_box(
    box: SegmentationBoxRecord,
    frame: tuple[int, int],
    image_size: tuple[int, int],
) -> tuple[int, int, int, int] | None:
    """Rescale a half-open source-media box to image pixels (clamped).

    Returns None when the box degenerates below one pixel (caller skips it
    with a warning rather than failing the whole inspection).
    """
    frame_w, frame_h = frame
    img_w, img_h = image_size
    x1 = max(math.floor(box.left * img_w / frame_w), 0)
    y1 = max(math.floor(box.top * img_h / frame_h), 0)
    x2 = min(math.ceil(box.right * img_w / frame_w), img_w)
    y2 = min(math.ceil(box.bottom * img_h / frame_h), img_h)
    if x1 >= x2 or y1 >= y2:
        return None
    return (x1, y1, x2, y2)


def _mask_bitmap(
    mask: SegmentationMaskRecord,
    corners: tuple[int, int, int, int],
    image_size: tuple[int, int],
) -> np.ndarray:
    """Paste a box-local raster into a full-image bool bitmap (nearest)."""
    x1, y1, x2, y2 = corners
    img_w, img_h = image_size
    raster = np.frombuffer(
        decode_mask_to_raster(mask.mask), dtype=np.uint8
    ).reshape(mask.mask.height, mask.mask.width)
    box_w, box_h = x2 - x1, y2 - y1
    rows = (np.arange(box_h) * raster.shape[0] // box_h).clip(0, raster.shape[0] - 1)
    cols = (np.arange(box_w) * raster.shape[1] // box_w).clip(0, raster.shape[1] - 1)
    full = np.zeros((img_h, img_w), dtype=bool)
    full[y1:y2, x1:x2] = raster[rows[:, None], cols].astype(bool)
    return full


@lru_cache(maxsize=64)
def _decode_grammar(
    output_text: str, image_size: tuple[int, int]
) -> tuple[tuple[tuple[int, int, int, int], float, list[int], list[int]], ...]:
    """Decode one grammar payload to ((bbox, confidence, counts, size), ...).

    Pure in / pure out (callers copy the counts): shared across prompts,
    cases, and threads. The slow step is the mask-codec raster decode, so
    repeated identical payloads parse once. Mirrors the service-level image
    cache (ARCHITECTURE.md §12). Malformed payloads raise every call —
    lru_cache never caches exceptions.
    """
    img_width, img_height = image_size
    parser = image_segmentation_format().create_parser()
    parser.push(output_text)
    result = parser.finish(CompletedOutcome()).result

    boxes: dict[str, SegmentationBoxRecord] = {}
    masks: dict[str, SegmentationMaskRecord] = {}
    for record in result.records:
        if isinstance(record, SegmentationBoxRecord):
            boxes.setdefault(record.object_id, record)
        elif isinstance(record, SegmentationMaskRecord):
            masks.setdefault(record.object_id, record)
    paired = sorted(
        (oid for oid in boxes if oid in masks), key=lambda oid: boxes[oid].order
    )
    if not paired:
        errors = [d for d in result.diagnostics if d.severity == "error"]
        if errors:
            raise MetaResponseError(f"SAM output rejected: {errors[0].message}")
        return ()

    frames = _frame_sizes(result.raw_output)
    decoded: list[tuple[tuple[int, int, int, int], float, list[int], list[int]]] = []
    for object_id in paired:
        box, mask = boxes[object_id], masks[object_id]
        frame = frames.get(object_id)
        if frame is None:
            raise MetaResponseError(
                f"SAM output omits frame size for object {object_id}"
            )
        corners = _rescale_box(box, frame, image_size)
        if corners is None:
            logger.warning("sam_degenerate_box", extra={"object_id": object_id})
            continue
        confidence: float | None = box.confidence
        if confidence is None:
            confidence = mask.confidence
        bitmap = _mask_bitmap(mask, corners, image_size)
        decoded.append(
            (
                corners,
                UNSCORED_CONFIDENCE if confidence is None else confidence,
                encode_coco_rle(bitmap),
                [img_height, img_width],
            )
        )
    return tuple(decoded)


def parse_segmentation_output(
    output_text: str,
    *,
    image_size: tuple[int, int],
    label: str,
    source_image: str = "image_0",
    id_prefix: str = "mask",
) -> list[Segmentation]:
    """Parse one SAM grammar payload into image-pixel Segmentations.

    `image_size` is (width, height) per PIL convention. Genuine no-match
    output yields []; malformed output raises MetaResponseError.
    """
    # Deferred: meta_client imports this module, so a top-level import
    # would cycle at load time. Function-level imports dodge E402.
    from app.gateway.meta_client import Segmentation

    out: list[Segmentation] = []
    for index, (bbox, confidence, counts, size) in enumerate(
        _decode_grammar(output_text, image_size), 1
    ):
        out.append(
            Segmentation(
                mask_id=f"{id_prefix}-{index}",
                label=label,
                bbox=list(bbox),
                confidence=confidence,
                rle={"size": list(size), "counts": list(counts)},
                source_image=source_image,
            )
        )
    return out
