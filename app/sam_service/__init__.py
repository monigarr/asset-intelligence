"""SAM 3.1 defect segmentation service: validation, RLE decode, overlay."""

from app.sam_service.errors import SamDecodeError, SamInputError, SamServiceError
from app.sam_service.overlay import render_overlay
from app.sam_service.service import (
    DEFAULT_TEXT_PROMPTS,
    LOW_CONFIDENCE_THRESHOLD,
    DecodedMask,
    SamService,
    decode_coco_rle,
    decode_mask_rle,
)

__all__ = [
    "DEFAULT_TEXT_PROMPTS",
    "LOW_CONFIDENCE_THRESHOLD",
    "DecodedMask",
    "SamDecodeError",
    "SamInputError",
    "SamService",
    "SamServiceError",
    "decode_coco_rle",
    "decode_mask_rle",
    "render_overlay",
]
