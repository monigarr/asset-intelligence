"""SAM service errors."""

from __future__ import annotations


class SamServiceError(Exception):
    """Base class for SAM segmentation service failures."""


class SamInputError(SamServiceError):
    """Bad caller input: empty/oversize/unreadable image, bad prompts, bad overlay items."""


class SamDecodeError(SamServiceError):
    """Undecodable RLE payload or mask geometry inconsistent with the image."""
