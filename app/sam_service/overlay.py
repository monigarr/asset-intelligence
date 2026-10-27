"""SAM mask overlay rendering for the review UI (Day 3).

Draws decoded mask bitmaps (translucent fill), bboxes, and confidence labels
onto a copy of the inspection image. Always returns PNG bytes. Presentation
only — never mutates evidence or invents geometry.
"""

from __future__ import annotations

from collections.abc import Sequence
from io import BytesIO

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from app.gateway import Segmentation
from app.sam_service.errors import SamInputError
from app.sam_service.service import LOW_CONFIDENCE_THRESHOLD, DecodedMask

LABEL_COLORS: dict[str, tuple[int, int, int]] = {
    "crack": (239, 68, 68),
    "corrosion": (249, 115, 22),
    "spall": (234, 179, 8),
    "vegetation": (34, 197, 94),
    "water seepage": (59, 130, 246),
    "water intrusion": (59, 130, 246),
}
DEFAULT_COLOR = (148, 163, 184)
MASK_ALPHA = 90
LOW_CONF_ALPHA = 45
LOW_CONF_SUFFIX = " (low-conf)"


def render_overlay(
    image_bytes: bytes,
    masks: Sequence[DecodedMask | Segmentation],
    *,
    show_labels: bool = True,
    show_bboxes: bool = True,
) -> bytes:
    """Render masks over the image. Returns PNG bytes at the original size."""
    try:
        base = Image.open(BytesIO(image_bytes)).convert("RGBA")
    except Exception as exc:
        raise SamInputError(f"overlay needs decodable image bytes: {exc}") from exc
    width, height = base.size
    draw = ImageDraw.Draw(base, "RGBA")
    font = ImageFont.load_default()

    for item in masks:
        mask, low_conf, bitmap = _normalize(item)
        color = LABEL_COLORS.get(mask.label.lower(), DEFAULT_COLOR)
        if bitmap is not None:
            _check_bitmap(item, bitmap, width, height)
            tint = Image.new(
                "RGBA", (width, height), (*color, LOW_CONF_ALPHA if low_conf else MASK_ALPHA)
            )
            base.paste(tint, (0, 0), Image.fromarray(bitmap))
        if show_bboxes:
            x1, y1, x2, y2 = mask.bbox
            draw.rectangle([x1, y1, x2, y2], outline=(*color, 255), width=3)
        if show_labels:
            x1, y1, _, _ = mask.bbox
            text = f"{mask.label} {mask.confidence:.2f}"
            if low_conf:
                text += LOW_CONF_SUFFIX
            draw.text(
                (x1, max(0, y1 - 12)),
                text,
                font=font,
                fill=(255, 255, 255, 255),
                stroke_width=2,
                stroke_fill=(0, 0, 0, 255),
            )

    out = BytesIO()
    base.convert("RGB").save(out, format="PNG")
    return out.getvalue()


def _normalize(
    item: DecodedMask | Segmentation,
) -> tuple[Segmentation, bool, np.ndarray | None]:
    if isinstance(item, DecodedMask):
        return item.mask, item.low_confidence, item.bitmap
    if isinstance(item, Segmentation):
        return item, item.confidence < LOW_CONFIDENCE_THRESHOLD, None
    raise SamInputError(
        "overlay expects DecodedMask or Segmentation, "
        f"got {type(item).__name__}"
    )


def _check_bitmap(
    item: DecodedMask | Segmentation, bitmap: np.ndarray, width: int, height: int
) -> None:
    mask_id = item.mask.mask_id if isinstance(item, DecodedMask) else item.mask_id
    if bitmap.dtype != bool or bitmap.shape != (height, width):
        raise SamInputError(
            f"mask {mask_id} bitmap shape {bitmap.shape}/{bitmap.dtype} "
            f"does not match image {width}x{height} bool"
        )
