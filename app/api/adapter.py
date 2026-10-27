"""Input adapter: multipart validation + EXIF sanitize (Day 7, ARCH §4.1).

Accepts 1–5 images (JPEG/PNG/WebP, ≤15MB each), a ≤10k-char note, and a JSON
asset_meta object. Every image is orientation-normalized and re-encoded
without EXIF (GPS included) before anything downstream sees it: logs and
storage only ever touch the normalized bytes. Failures are HTTP 400 (413
for oversize) — never 500s for caller mistakes.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from io import BytesIO

from fastapi import HTTPException, UploadFile
from PIL import Image, ImageOps, UnidentifiedImageError

from app.sam_service.service import MAX_IMAGE_BYTES

MAX_IMAGES = 5
MAX_NOTE_CHARS = 10_000
SUPPORTED_FORMATS = frozenset({"JPEG", "PNG", "WEBP"})


@dataclass(frozen=True)
class NormalizedImage:
    data: bytes
    width: int
    height: int
    mime: str


async def normalize_inspection(
    images: list[UploadFile] | None, note: str, asset_meta_raw: str
) -> tuple[list[NormalizedImage], str, dict]:
    """Validate + sanitize one inspection submission."""
    files = images or []
    if not 1 <= len(files) <= MAX_IMAGES:
        raise HTTPException(400, f"need 1-{MAX_IMAGES} images, got {len(files)}")
    normalized = [await _normalize_image(f) for f in files]
    if len(note) > MAX_NOTE_CHARS:
        raise HTTPException(400, f"note is {len(note)} chars, max is {MAX_NOTE_CHARS}")
    try:
        meta = json.loads(asset_meta_raw or "{}")
    except ValueError as exc:
        raise HTTPException(400, f"asset_meta is not valid JSON: {exc}") from exc
    if not isinstance(meta, dict):
        raise HTTPException(400, "asset_meta must be a JSON object")
    return normalized, note, meta


async def _normalize_image(upload: UploadFile) -> NormalizedImage:
    raw = await upload.read()
    if len(raw) > MAX_IMAGE_BYTES:
        raise HTTPException(413, f"image exceeds {MAX_IMAGE_BYTES} bytes")
    if not raw:
        raise HTTPException(400, "empty image upload")
    try:
        with Image.open(BytesIO(raw)) as img:
            img.load()
            fmt = img.format
    except (UnidentifiedImageError, OSError) as exc:
        raise HTTPException(400, f"unrecognized image bytes: {exc}") from exc
    if fmt not in SUPPORTED_FORMATS:
        raise HTTPException(400, f"unsupported image format {fmt!r} (need JPEG/PNG/WebP)")
    with Image.open(BytesIO(raw)) as img:
        img = ImageOps.exif_transpose(img)
        if fmt == "JPEG" and img.mode != "RGB":
            img = img.convert("RGB")
        buf = BytesIO()
        img.save(buf, format=fmt)  # re-encode drops EXIF (GPS included)
        data = buf.getvalue()
    mime = Image.MIME.get(fmt, "application/octet-stream")
    with Image.open(BytesIO(data)) as final:
        width, height = final.size
    return NormalizedImage(data=data, width=width, height=height, mime=mime)
