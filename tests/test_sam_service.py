"""SAM service tests: RLE decode, validation, cache, overlay.

All fixtures are synthetic and in-memory (PIL-generated); no network, no key.
Also covers the gateway contract this service depends on: `Segmentation.rle`
must accept COCO dicts (see `test_segmentation_accepts_coco_rle_dict`).
"""

from __future__ import annotations

from io import BytesIO
from typing import Any

import numpy as np
import pytest
from PIL import Image

from app.gateway import Segmentation, Settings
from app.sam_service import (
    DecodedMask,
    SamDecodeError,
    SamInputError,
    SamService,
    decode_coco_rle,
    decode_mask_rle,
    render_overlay,
)

W, H = 64, 48


def _image_bytes(fmt: str = "JPEG", size: tuple[int, int] = (W, H)) -> bytes:
    img = Image.new("RGB", size, (200, 200, 200))
    buf = BytesIO()
    img.save(buf, format=fmt)
    return buf.getvalue()


def _rle_dict(width: int = W, height: int = H, **over: Any) -> dict[str, Any]:
    total = width * height
    d: dict[str, Any] = {"size": [height, width], "counts": [100, 50, total - 150]}
    d.update(over)
    return d


def _mask(**over: Any) -> Segmentation:
    base: dict[str, Any] = {
        "mask_id": "mask_1",
        "label": "crack",
        "bbox": [4, 4, 40, 30],
        "confidence": 0.87,
        "rle": _rle_dict(),
        "source_image": "image_0",
    }
    base.update(over)
    return Segmentation(**base)


class _StubClient:
    """Fake MetaClient: records calls, returns canned masks."""

    def __init__(self, masks: list[Segmentation]) -> None:
        self.masks = masks
        self.calls: list[dict[str, Any]] = []

    def segment(self, model_id: str, image_bytes: bytes, text_prompts: Any, **kw: Any):
        self.calls.append({"model_id": model_id, "prompts": list(text_prompts), **kw})
        return self.masks


def _service(masks: list[Segmentation], **kw: Any) -> tuple[SamService, _StubClient]:
    stub = _StubClient(masks)
    svc = SamService(client=stub, settings=Settings(api_key="test"), **kw)  # type: ignore[arg-type]
    return svc, stub


# -- gateway contract ---------------------------------------------------


def test_segmentation_accepts_coco_rle_dict() -> None:
    m = _mask()
    assert isinstance(m.rle, dict)
    assert m.rle["counts"][:2] == [100, 50]


# -- COCO RLE decode ----------------------------------------------------


def test_decode_coco_rle_column_major() -> None:
    # h=2, w=3: runs bg×2, fg×1, bg×3 over 6 column-major pixels.
    got = decode_coco_rle([2, 1, 3], 2, 3)
    want = np.array([[False, True, False], [False, False, False]])
    assert got.shape == (2, 3)
    assert got.dtype == bool
    assert np.array_equal(got, want)


def test_decode_coco_rle_rejects_bad_runs() -> None:
    with pytest.raises(SamDecodeError):
        decode_coco_rle([2, 1], 2, 3)  # sum 3 != 6
    with pytest.raises(SamDecodeError):
        decode_coco_rle([2, -1, 4], 2, 3)  # negative run
    with pytest.raises(SamDecodeError):
        decode_coco_rle([2, True, 3], 2, 3)  # bool is not an int run
    with pytest.raises(SamDecodeError):
        decode_coco_rle([6], 0, 3)  # bad size


def test_decode_mask_rle_variants() -> None:
    assert decode_mask_rle(None, (W, H)) is None  # bbox-only
    ok = decode_mask_rle(_rle_dict(), (W, H))
    assert ok is not None and ok.shape == (H, W)
    with pytest.raises(SamDecodeError):
        decode_mask_rle(_rle_dict(width=8, height=8), (W, H))  # size mismatch
    with pytest.raises(SamDecodeError):
        decode_mask_rle(_rle_dict(counts="eN00compressed"), (W, H))  # compressed str
    with pytest.raises(SamDecodeError):
        decode_mask_rle("some-string-encoding", (W, H))  # unknown string
    with pytest.raises(SamDecodeError):
        decode_mask_rle({"size": [H, W]}, (W, H))  # counts missing


# -- service ------------------------------------------------------------


def test_segment_happy_path_flags_low_confidence() -> None:
    svc, stub = _service([_mask(), _mask(mask_id="mask_2", confidence=0.2, rle=None)])
    out = svc.segment_image(_image_bytes(), ["crack"])
    assert len(out) == 2
    assert out[0].low_confidence is False
    assert out[0].bitmap is not None and out[0].bitmap.shape == (H, W)
    assert out[1].low_confidence is True
    assert out[1].bitmap is None  # bbox-only passes through
    assert stub.calls[0]["model_id"] == "sam-3.1"
    assert stub.calls[0]["prompts"] == ["crack"]


def test_segment_uses_default_prompts() -> None:
    svc, stub = _service([_mask()])
    svc.segment_image(_image_bytes())
    assert stub.calls[0]["prompts"] == ["crack", "corrosion", "water seepage"]


def test_segment_caches_by_image_and_prompts() -> None:
    svc, stub = _service([_mask()])
    img = _image_bytes()
    first = svc.segment_image(img, ["crack"])
    second = svc.segment_image(img, ["crack"])
    assert first is second  # cache hit returns the same list
    assert len(stub.calls) == 1
    svc.segment_image(img, ["corrosion"])  # different prompts -> miss
    assert len(stub.calls) == 2
    svc.clear_cache()
    svc.segment_image(img, ["crack"])
    assert len(stub.calls) == 3


def test_low_confidence_boundary() -> None:
    svc, _ = _service(
        [_mask(mask_id="a", confidence=0.4), _mask(mask_id="b", confidence=0.3999)]
    )
    out = svc.segment_image(_image_bytes())
    assert out[0].low_confidence is False  # 0.4 is not low
    assert out[1].low_confidence is True


def test_segment_rejects_bad_inputs() -> None:
    svc, _ = _service([_mask()])
    with pytest.raises(SamInputError):
        svc.segment_image(b"")
    with pytest.raises(SamInputError):
        svc.segment_image(b"not-an-image")
    with pytest.raises(SamInputError):
        svc.segment_image(bytes(15 * 1024 * 1024 + 1))  # over 15 MB
    with pytest.raises(SamInputError):
        svc.segment_image(_image_bytes(fmt="GIF"))  # unsupported format
    with pytest.raises(SamInputError):
        svc.segment_image(_image_bytes(), [])
    with pytest.raises(SamInputError):
        svc.segment_image(_image_bytes(), ["  "])


def test_segment_rejects_out_of_bounds_bbox() -> None:
    svc, _ = _service([_mask(bbox=[0, 0, 9999, 9999])])
    with pytest.raises(SamDecodeError):
        svc.segment_image(_image_bytes())


def test_service_logs_summary(caplog: pytest.LogCaptureFixture) -> None:
    import logging

    caplog.set_level(logging.INFO, logger="asset_intel.sam")
    svc, _ = _service([_mask(), _mask(mask_id="m2", confidence=0.1)])
    svc.segment_image(_image_bytes(), request_id="req_sam1")
    recs = [r for r in caplog.records if r.name == "asset_intel.sam"]
    assert len(recs) == 1
    assert recs[0].mask_count == 2
    assert recs[0].low_confidence_count == 1
    assert recs[0].request_id == "req_sam1"


# -- overlay ------------------------------------------------------------


def test_overlay_renders_png_deterministically() -> None:
    svc, _ = _service([_mask(), _mask(mask_id="m2", confidence=0.1, rle=None)])
    decoded = svc.segment_image(_image_bytes())
    first = render_overlay(_image_bytes(), decoded)
    second = render_overlay(_image_bytes(), decoded)
    assert first[:8] == b"\x89PNG\r\n\x1a\n"
    assert first == second
    with Image.open(BytesIO(first)) as img:
        assert img.size == (W, H)


def test_overlay_accepts_bare_segmentations_and_empty() -> None:
    out = render_overlay(_image_bytes(), [_mask()])
    assert out[:8] == b"\x89PNG\r\n\x1a\n"
    empty = render_overlay(_image_bytes(), [])
    with Image.open(BytesIO(empty)) as img:
        assert img.size == (W, H)


def test_overlay_rejects_bad_items() -> None:
    with pytest.raises(SamInputError):
        render_overlay(_image_bytes(), ["not-a-mask"])  # type: ignore[list-item]
    bad_bitmap = DecodedMask(
        mask=_mask(), low_confidence=False, bitmap=np.zeros((4, 4), dtype=bool)
    )
    with pytest.raises(SamInputError):
        render_overlay(_image_bytes(), [bad_bitmap])
    with pytest.raises(SamInputError):
        render_overlay(b"junk", [_mask()])
