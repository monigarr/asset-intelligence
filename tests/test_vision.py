"""Vision extractor tests (mocked transport, synthetic images)."""

from __future__ import annotations

import json
from io import BytesIO
from typing import Any

import httpx
import pytest
from PIL import Image

from app.gateway import MetaClient, Segmentation, Settings
from app.gateway.errors import MetaAuthError, MetaResponseError
from app.sam_service import DecodedMask
from app.vision import VisionExtractor, summarize_masks_for_prompt

JPEG = b"\xff\xd8\xff" + b"\x00" * 64

VISION_JSON = {
    "asset_type": "drainage_structure",
    "condition_tags": ["crack", "seepage"],
    "symptoms": [
        {
            "text": "linear crack with seepage",
            "evidence": [
                {"source": "image_0", "mask_id": "mask_1"},
                {"source": "maintenance_note", "span": [0, 20]},
            ],
            "uncertainty": 0.3,
        }
    ],
}


def _decoded(mask_id: str = "mask_1", conf: float = 0.87) -> DecodedMask:
    return DecodedMask(
        mask=Segmentation(
            mask_id=mask_id,
            label="crack",
            bbox=[4, 4, 20, 20],
            confidence=conf,
            source_image="image_0",
        ),
        low_confidence=conf < 0.4,
        bitmap=None,
    )


def _extractor(handler: Any, **overrides: Any) -> VisionExtractor:
    params: dict[str, Any] = {"api_key": "test", "base_url": "https://api.test/v1"}
    params.update(overrides)
    settings = Settings(**params)  # type: ignore[arg-type]
    client = MetaClient(
        settings=settings,
        transport=httpx.MockTransport(handler),
        retry_wait=lambda _s: 0,
    )
    return VisionExtractor(client=client, settings=settings)


def test_summarize_masks_for_prompt() -> None:
    text = summarize_masks_for_prompt([[_decoded(), _decoded("m2", 0.2)], []])
    assert "image_0 (2 masks)" in text
    assert "mask_1: crack, conf 0.87" in text
    assert "m2" in text and "LOW-CONFIDENCE" in text
    assert "image_1 (0 masks): none" in text


def test_extract_happy_path() -> None:
    seen: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["body"] = json.loads(request.content.decode())
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": json.dumps(VISION_JSON)}}],
                "usage": {"prompt_tokens": 500, "completion_tokens": 60},
            },
        )

    obs = _extractor(handler).extract(
        [JPEG, JPEG],
        [[_decoded()], [_decoded("m9")]],
        note="Crack near top edge",
        asset_meta={"asset_id": "A-1"},
        request_id="req_v1",
    )
    assert obs.asset_type == "drainage_structure"
    assert obs.symptoms[0].evidence[1].span == [0, 20]
    assert obs.model_id == "muse-spark-1.3"
    assert obs.fallback_used is False
    assert obs.usage.prompt_tokens == 500

    body = seen["body"]
    assert body["model"] == "muse-spark-1.3"
    assert body["response_format"]["type"] == "json_schema"
    user_content = body["messages"][1]["content"]
    # gateway packs text + images as content parts; text is always first
    user_text = user_content[0]["text"]
    assert "Crack near top edge" in user_text
    assert "mask_1" in user_text and "m9" in user_text
    assert "A-1" in user_text
    parts = body["messages"][-1]["content"]
    assert sum(1 for p in parts if p.get("type") == "image_url") == 2


def test_extract_falls_back_once() -> None:
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content.decode())
        calls.append(body["model"])
        if body["model"] == "vis-primary":
            return httpx.Response(500, text="down")
        return httpx.Response(
            200, json={"choices": [{"message": {"content": json.dumps(VISION_JSON)}}]}
        )

    obs = _extractor(
        handler, vision_model_id="vis-primary", fallback_vision_model_id="vis-fallback"
    ).extract([JPEG], [[_decoded()]])
    assert obs.model_id == "vis-fallback"
    assert obs.fallback_used is True
    assert calls.count("vis-primary") == 3  # gateway retries
    assert calls.count("vis-fallback") == 1


def test_extract_no_fallback_on_auth_error() -> None:
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(json.loads(request.content.decode())["model"])
        return httpx.Response(401, text="bad key")

    with pytest.raises(MetaAuthError):
        _extractor(handler).extract([JPEG], [[_decoded()]])
    assert calls == ["muse-spark-1.3"]  # deterministic: no fallback


def test_extract_rejects_invalid_observation() -> None:
    bad = {"symptoms": [{"text": "x", "evidence": [], "uncertainty": 0.1}]}

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200, json={"choices": [{"message": {"content": json.dumps(bad)}}]}
        )

    with pytest.raises(MetaResponseError, match="invalid observation"):
        _extractor(handler).extract([JPEG], [[_decoded()]])


def test_extract_validates_arguments() -> None:
    ext = _extractor(lambda r: httpx.Response(200, json={}))
    with pytest.raises(ValueError, match="1-5 images"):
        ext.extract([], [])
    with pytest.raises(ValueError, match="1-5 images"):
        ext.extract([JPEG] * 6, [[]] * 6)
    with pytest.raises(ValueError, match="parallel"):
        ext.extract([JPEG], [[], []])
    with pytest.raises(TypeError, match="note must be a string"):
        ext.extract([JPEG], [[]], note=123)  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="asset_meta must be a dict"):
        ext.extract([JPEG], [[]], asset_meta="x")  # type: ignore[arg-type]


def test_extract_empty_note_allowed() -> None:
    seen: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["body"] = json.loads(request.content.decode())
        return httpx.Response(
            200, json={"choices": [{"message": {"content": json.dumps(VISION_JSON)}}]}
        )

    _extractor(handler).extract([JPEG], [[_decoded()]], note="")
    content = seen["body"]["messages"][1]["content"]
    assert "(no note provided)" in content[0]["text"]


def test_extract_real_jpeg_bytes() -> None:
    """Extractor accepts genuine PIL-produced bytes (not just magic stubs)."""
    img = Image.new("RGB", (16, 12), (10, 20, 30))
    buf = BytesIO()
    img.save(buf, format="JPEG")
    seen: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["body"] = json.loads(request.content.decode())
        return httpx.Response(
            200, json={"choices": [{"message": {"content": json.dumps(VISION_JSON)}}]}
        )

    obs = _extractor(handler).extract([buf.getvalue()], [[_decoded()]])
    assert obs.symptoms[0].text == "linear crack with seepage"
