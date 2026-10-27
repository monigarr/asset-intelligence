"""Orchestrator tests: Spark prompt contract, pipeline assembly, full flow."""

from __future__ import annotations

import json
from datetime import datetime
from io import BytesIO
from typing import Any

import httpx
import pytest
from PIL import Image

from app.gateway import MetaClient, Segmentation, Settings
from app.gateway.errors import MetaResponseError
from app.gateway.meta_client import ChatUsage
from app.orchestrator import InspectionPipeline, PipelineInputError, SparkReasoner
from app.sam_service import DecodedMask, SamService
from app.vision import VisionExtractor, VisionObservation

JPEG = b"\xff\xd8\xff" + b"\x00" * 64

SPARK_JSON = {
    "asset_type": "drainage_structure",
    "observations": [
        {
            "text": "Visible linear crack near top edge with active seepage",
            "evidence": [
                {"source": "image_0", "mask_id": "mask_1"},
                {"source": "maintenance_note", "span": [0, 20]},
            ],
            "uncertainty": 0.35,
        }
    ],
    "missing_information": ["crack_dimensions", "inspection_date"],
}


def _settings() -> Settings:
    return Settings(api_key="test", base_url="https://api.test/v1")


def _decoded(mask_id: str = "mask_1", source: str = "image_0") -> DecodedMask:
    return DecodedMask(
        mask=Segmentation(
            mask_id=mask_id,
            label="crack",
            bbox=[4, 4, 20, 20],
            confidence=0.87,
            source_image=source,
        ),
        low_confidence=False,
        bitmap=None,
    )


def _vision_obs() -> VisionObservation:
    return VisionObservation(
        asset_type="drainage_structure",
        condition_tags=["crack"],
        symptoms=[],
        model_id="muse-spark-1.3",
        usage=ChatUsage(prompt_tokens=1000, completion_tokens=500, total_tokens=1500),
    )


class _FakeSam:
    def __init__(self, by_source: dict[str, list[DecodedMask]]) -> None:
        self.by_source = by_source
        self.calls: list[str] = []

    def segment_image(self, image: bytes, prompts: Any, *, source_image: str, **kw: Any):
        self.calls.append(source_image)
        return self.by_source[source_image]


class _FakeVision:
    def __init__(self, obs: VisionObservation) -> None:
        self.obs = obs

    def extract(self, *a: Any, **kw: Any) -> VisionObservation:
        return self.obs


def _spark_reasoner(handler: Any) -> SparkReasoner:
    settings = _settings()
    client = MetaClient(
        settings=settings, transport=httpx.MockTransport(handler), retry_wait=lambda _s: 0
    )
    return SparkReasoner(client=client, settings=settings)


# -- Spark prompt contract ----------------------------------------------


def test_spark_prompt_and_schema() -> None:
    seen: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["body"] = json.loads(request.content.decode())
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": json.dumps(SPARK_JSON)}}],
                "usage": {"prompt_tokens": 800, "completion_tokens": 120},
            },
        )

    draft = _spark_reasoner(handler).reason(
        _vision_obs().model_dump_json(),
        [[_decoded()]],
        "Crack near top",
        {"asset_id": "A-1"},
        request_id="req_s1",
    )
    assert draft.observations[0].uncertainty == 0.35
    assert draft.missing_information == ["crack_dimensions", "inspection_date"]
    assert draft.usage.completion_tokens == 120

    body = seen["body"]
    assert body["model"] == "muse-spark-1.3"
    assert body["response_format"]["json_schema"]["name"] == "inspection_draft"
    assert all(
        "image_url" not in json.dumps(m) for m in body["messages"]
    ), "Spark reasons over fused text, not raw images"
    user_text = body["messages"][1]["content"]
    for needle in ("IMAGES: image_0", "mask_1", "Crack near top", "A-1", "VISION:"):
        assert needle in user_text
    assert "Return ONLY valid JSON" in body["messages"][0]["content"]


def test_spark_rejects_missing_observations() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200, json={"choices": [{"message": {"content": '{"asset_type": "x"}'}}]}
        )

    with pytest.raises(MetaResponseError, match="invalid draft"):
        _spark_reasoner(handler).reason("{}", [[_decoded()]], "n", {})


# -- pipeline assembly --------------------------------------------------


def _pipeline(handler: Any, by_source: dict[str, list[DecodedMask]]) -> InspectionPipeline:
    return InspectionPipeline(
        sam=_FakeSam(by_source),  # type: ignore[arg-type]
        vision=_FakeVision(_vision_obs()),  # type: ignore[arg-type]
        spark=_spark_reasoner(handler),
        settings=_settings(),
    )


def _spark_ok(request: httpx.Request) -> httpx.Response:
    return httpx.Response(
        200,
        json={
            "choices": [{"message": {"content": json.dumps(SPARK_JSON)}}],
            "usage": {"prompt_tokens": 800, "completion_tokens": 120},
        },
    )


def test_pipeline_assembles_draft() -> None:
    pipe = _pipeline(_spark_ok, {"image_0": [_decoded()], "image_1": [_decoded("m2", "image_1")]})
    out = pipe.run([JPEG, JPEG], note="Crack near top", asset_meta={"asset_id": "A-1"})
    assert out.asset_id == "A-1"
    assert out.asset_type == "drainage_structure"
    assert [m.mask_id for m in out.segmentations] == ["mask_1", "m2"]
    assert [m.source_image for m in out.segmentations] == ["image_0", "image_1"]
    assert len(out.observations) == 1
    assert out.missing_information == ["crack_dimensions", "inspection_date"]
    assert out.human_review_required is True
    assert out.model_trace.sam == "sam-3.1"
    assert out.model_trace.vision == "muse-spark-1.3"
    assert out.model_trace.reasoning == "muse-spark-1.3"
    datetime.fromisoformat(out.model_trace.timestamp)  # parses
    assert out.cost_priced is False  # placeholder pricing
    assert out.cost_cents == 0.0


def test_pipeline_cost_math_with_priced_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("META_PRICE_PER_IMAGE_CENTS_SAM_3_1", "2.0")
    monkeypatch.setenv("META_PRICE_PER_1K_CENTS_MUSE_SPARK_1_3", "4.0")
    pipe = _pipeline(_spark_ok, {"image_0": [_decoded()]})
    out = pipe.run([JPEG])
    # sam 2.0 + vision-as-spark (1500/1000*4.0)=6.0 + spark (920/1000*4.0)=3.68
    assert out.cost_cents == pytest.approx(2.0 + 6.0 + 3.68)
    assert out.cost_priced is True


def test_pipeline_defaults_and_request_id() -> None:
    pipe = _pipeline(_spark_ok, {"image_0": [_decoded()]})
    out = pipe.run([JPEG], request_id="req_p1")
    assert out.request_id == "req_p1"
    assert out.asset_id == "ASSET-req_p1"
    auto = pipe.run([JPEG])
    assert auto.request_id.startswith("req_") and auto.asset_id.startswith("ASSET-req_")


def test_pipeline_validates_inputs() -> None:
    pipe = _pipeline(_spark_ok, {"image_0": [_decoded()]})
    with pytest.raises(PipelineInputError, match="1-5 images"):
        pipe.run([])
    with pytest.raises(PipelineInputError, match="1-5 images"):
        pipe.run([JPEG] * 6)
    with pytest.raises(PipelineInputError, match="non-empty bytes"):
        pipe.run([b""])
    with pytest.raises(PipelineInputError, match="max is 10000"):
        pipe.run([JPEG], note="x" * 10001)
    with pytest.raises(PipelineInputError, match="asset_meta must be a dict"):
        pipe.run([JPEG], asset_meta="x")  # type: ignore[arg-type]


def test_pipeline_propagates_spark_failure() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"choices": [{"message": {"content": "nope"}}]})

    pipe = _pipeline(handler, {"image_0": [_decoded()]})
    with pytest.raises(MetaResponseError):
        pipe.run([JPEG])


# -- full flow: real SAM + Vision + Spark over one mock -----------------


def _real_jpeg(w: int = 32, h: int = 24) -> bytes:
    img = Image.new("RGB", (w, h), (200, 200, 200))
    buf = BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


def _has_image_parts(body: dict[str, Any]) -> bool:
    for message in body.get("messages", []):
        content = message.get("content", [])
        if isinstance(content, list):
            for part in content:
                if isinstance(part, dict) and part.get("type") == "image_url":
                    return True
    return False


def test_full_flow_sam_vision_spark() -> None:
    img = _real_jpeg()
    vision_json = {
        "asset_type": "drainage_structure",
        "condition_tags": ["crack"],
        "symptoms": [
            {
                "text": "crack",
                "evidence": [{"source": "image_0", "mask_id": "mask_1"}],
                "uncertainty": 0.3,
            }
        ],
    }

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/v1/responses":
            from pathlib import Path

            grammar = (Path(__file__).parent / "fixtures" / "sam_crack.txt").read_text()
            return httpx.Response(
                200,
                json={
                    "status": "completed",
                    "output": [
                        {
                            "type": "message",
                            "content": [{"type": "output_text", "text": grammar}],
                        }
                    ],
                },
            )
        body = json.loads(request.content.decode())
        if body["model"] == "muse-spark-1.3" and _has_image_parts(body):
            return httpx.Response(
                200, json={"choices": [{"message": {"content": json.dumps(vision_json)}}]}
            )
        assert body["model"] == "muse-spark-1.3"
        assert "mask_1" in body["messages"][1]["content"]  # SAM evidence reaches Spark
        return httpx.Response(
            200, json={"choices": [{"message": {"content": json.dumps(SPARK_JSON)}}]}
        )

    settings = _settings()
    client = MetaClient(
        settings=settings, transport=httpx.MockTransport(handler), retry_wait=lambda _s: 0
    )
    pipe = InspectionPipeline(
        sam=SamService(client=client, settings=settings),
        vision=VisionExtractor(client=client, settings=settings),
        spark=SparkReasoner(client=client, settings=settings),
        settings=settings,
    )
    out = pipe.run([img], note="crack", asset_meta={"asset_id": "E2E-1"})
    assert out.asset_id == "E2E-1"
    assert len(out.segmentations) == 3  # one mask per default prompt
    assert out.segmentations[0].rle["size"] == [24, 32]
    assert sum(out.segmentations[0].rle["counts"]) == 32 * 24
    assert out.observations[0].evidence[0].mask_id == "mask_1"
