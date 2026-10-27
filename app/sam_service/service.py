"""SAM 3.1 defect segmentation service (Day 3).

Wraps `MetaClient.segment` with input validation, COCO RLE decoding, an
in-memory LRU mask cache (ARCHITECTURE.md §12), and low-confidence flagging.

GAP defaults applied (ARCHITECTURE.md is silent on wire details):
  - RLE payloads are COCO-style ``{"size": [height, width], "counts": [...]}``
    with uncompressed integer runs in column-major order. Compressed-string
    counts are rejected with a named error until the live API shape is seen.
  - `bbox` is corners ``[x1, y1, x2, y2]`` in pixels (PRD.md §6's example is
    consistent with this). Bounds-checked against the image; violations fail
    closed. Revisit on the Day-3 live-key check.
  - Low-confidence masks (< 0.4) are KEPT and flagged, never dropped
    (ARCHITECTURE.md §4.2, §11).
"""

from __future__ import annotations

import hashlib
import logging
from collections import OrderedDict
from collections.abc import Sequence
from dataclasses import dataclass
from io import BytesIO
from typing import Any
from uuid import uuid4

import numpy as np
from PIL import Image, UnidentifiedImageError

from app.gateway import MetaClient, Segmentation, Settings
from app.sam_service.errors import SamDecodeError, SamInputError

logger = logging.getLogger("asset_intel.sam")

DEFAULT_TEXT_PROMPTS = ("crack", "corrosion", "water seepage")  # ARCHITECTURE.md §4.2
LOW_CONFIDENCE_THRESHOLD = 0.4
MAX_IMAGE_BYTES = 15 * 1024 * 1024  # PRD FR-01 / ARCHITECTURE.md §4.1
SUPPORTED_FORMATS = frozenset({"JPEG", "PNG", "WEBP"})
DEFAULT_CACHE_SIZE = 32


@dataclass(frozen=True, eq=False)
class DecodedMask:
    """A validated mask plus its decoded bitmap (None when bbox-only)."""

    mask: Segmentation
    low_confidence: bool
    bitmap: np.ndarray | None  # bool array, shape (height, width)


def decode_coco_rle(counts: Sequence[int], height: int, width: int) -> np.ndarray:
    """Decode uncompressed COCO RLE runs (column-major) to a bool bitmap."""
    if height <= 0 or width <= 0:
        raise SamDecodeError(f"invalid RLE size [{height}, {width}]")
    try:
        runs = list(counts)
    except TypeError as exc:
        raise SamDecodeError(f"RLE counts must be a list of ints: {exc}") from exc
    total = height * width
    flat = np.zeros(total, dtype=bool)
    pos = 0
    foreground = False
    for run in runs:
        if not isinstance(run, int) or isinstance(run, bool) or run < 0:
            raise SamDecodeError(f"invalid RLE run {run!r}")
        flat[pos : pos + run] = foreground
        pos += run
        foreground = not foreground
    if pos != total:
        raise SamDecodeError(f"RLE counts sum to {pos}, expected {total}")
    return flat.reshape((height, width), order="F")


def decode_mask_rle(
    rle: str | dict[str, Any] | None, image_size: tuple[int, int]
) -> np.ndarray | None:
    """Decode a gateway RLE payload to a bool bitmap, or None when bbox-only.

    `image_size` is (width, height) per PIL convention. Masks whose size does
    not match the image fail closed — a size mismatch means the wire contract
    changed and must be investigated, not silently tolerated.
    """
    if rle is None:
        return None
    if isinstance(rle, str):
        raise SamDecodeError(
            "unsupported RLE string encoding (GAP: Day-3 decodes COCO dicts only)"
        )
    if not isinstance(rle, dict):
        raise SamDecodeError(f"unsupported RLE payload type {type(rle).__name__}")
    size = rle.get("size")
    counts = rle.get("counts")
    if (
        not isinstance(size, (list, tuple))
        or len(size) != 2
        or not all(isinstance(v, int) and not isinstance(v, bool) for v in size)
    ):
        raise SamDecodeError(f"invalid RLE size {size!r} (want [height, width] ints)")
    height, width = size
    img_width, img_height = image_size
    if (width, height) != (img_width, img_height):
        raise SamDecodeError(
            f"RLE size [{height}, {width}] does not match image {img_width}x{img_height}"
        )
    if isinstance(counts, str):
        raise SamDecodeError(
            "compressed COCO RLE strings not supported yet "
            "(GAP: Day-3 decodes uncompressed counts lists only)"
        )
    return decode_coco_rle(counts, height, width)


class SamService:
    """Defect segmentation over `MetaClient` with validation, decode, cache."""

    def __init__(
        self,
        client: MetaClient | None = None,
        settings: Settings | None = None,
        cache_size: int = DEFAULT_CACHE_SIZE,
    ) -> None:
        if cache_size < 1:
            raise ValueError("cache_size must be >= 1")
        self._settings = settings or Settings.from_env()
        self._client = client or MetaClient(settings=self._settings)
        self._cache: OrderedDict[str, list[DecodedMask]] = OrderedDict()
        self._cache_size = cache_size

    def clear_cache(self) -> None:
        self._cache.clear()

    def segment_image(
        self,
        image_bytes: bytes,
        text_prompts: Sequence[str] | None = None,
        *,
        source_image: str = "image_0",
        request_id: str | None = None,
    ) -> list[DecodedMask]:
        """Segment defects. Returns decoded masks; low-confidence kept + flagged."""
        rid = request_id or f"req_{uuid4().hex[:24]}"  # same interim format as gateway
        width, height = self._validate_image(image_bytes)
        prompts = self._validate_prompts(text_prompts)
        key = self._cache_key(image_bytes, prompts)

        cached = self._cache.get(key)
        if cached is not None:
            self._cache.move_to_end(key)
            logger.debug(
                "sam_cache_hit", extra={"request_id": rid, "mask_count": len(cached)}
            )
            return cached

        model_id = self._settings.sam_model_id
        masks = self._client.segment(
            model_id, image_bytes, prompts, source_image=source_image, request_id=rid
        )
        decoded = [self._decode_one(m, width, height) for m in masks]
        self._cache[key] = decoded
        while len(self._cache) > self._cache_size:
            self._cache.popitem(last=False)

        low = sum(1 for d in decoded if d.low_confidence)
        logger.info(
            "sam_segment",
            extra={
                "request_id": rid,
                "model_id": model_id,
                "mask_count": len(decoded),
                "low_confidence_count": low,
                "image_bytes": len(image_bytes),
                "cached": False,
            },
        )
        return decoded

    def _decode_one(self, mask: Segmentation, width: int, height: int) -> DecodedMask:
        bitmap = decode_mask_rle(mask.rle, (width, height))
        x1, y1, x2, y2 = mask.bbox
        if not (0 <= x1 < x2 <= width and 0 <= y1 < y2 <= height):
            raise SamDecodeError(
                f"mask {mask.mask_id} bbox {mask.bbox} outside {width}x{height} "
                "(GAP default: corners [x1, y1, x2, y2])"
            )
        return DecodedMask(
            mask=mask,
            low_confidence=mask.confidence < LOW_CONFIDENCE_THRESHOLD,
            bitmap=bitmap,
        )

    @staticmethod
    def _validate_image(image_bytes: bytes) -> tuple[int, int]:
        if not image_bytes:
            raise SamInputError("empty image bytes")
        if len(image_bytes) > MAX_IMAGE_BYTES:
            raise SamInputError(
                f"image is {len(image_bytes)} bytes, max is {MAX_IMAGE_BYTES}"
            )
        try:
            with Image.open(BytesIO(image_bytes)) as img:
                img.load()
                fmt, size = img.format, img.size
        except (UnidentifiedImageError, OSError) as exc:
            raise SamInputError(f"unrecognized image bytes: {exc}") from exc
        if fmt not in SUPPORTED_FORMATS:
            raise SamInputError(
                f"unsupported image format {fmt!r} (need JPEG, PNG, or WebP)"
            )
        return size

    @staticmethod
    def _validate_prompts(text_prompts: Sequence[str] | None) -> tuple[str, ...]:
        prompts = tuple(text_prompts) if text_prompts is not None else DEFAULT_TEXT_PROMPTS
        if not prompts:
            raise SamInputError("at least one text prompt is required")
        if any(not isinstance(p, str) or not p.strip() for p in prompts):
            raise SamInputError("text prompts must be non-empty strings")
        return prompts

    def _cache_key(self, image_bytes: bytes, prompts: tuple[str, ...]) -> str:
        digest = hashlib.sha256()
        digest.update(self._settings.sam_model_id.encode())
        digest.update(b"\x00")
        digest.update("\x00".join(prompts).encode())
        digest.update(b"\x00")
        digest.update(image_bytes)
        return digest.hexdigest()
