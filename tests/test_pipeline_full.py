"""Full-chain tests: pipeline run_full with Wonder + validation."""

from __future__ import annotations

import json
import logging
from io import BytesIO
from typing import Any

import httpx
import pytest
from PIL import Image
from pydantic import ValidationError

from app.gateway import MetaClient, Segmentation, Settings
from app.gateway.meta_client import ChatUsage
from app.orchestrator import InspectionPipeline
from app.planner import WonderPlan
from app.sam_service import DecodedMask, SamService
from app.vision import VisionExtractor, VisionObservation

JPEG = b"\xff\xd8\xff" + b"\x00" * 64

SPARK_JSON = {
    "asset_type": "drainage_structure",
    "observations": [
        {
            "text": "Visible linear crack near top edge",
            "evidence": [
                {"source": "image_0", "mask_id": "mask_1"},
                {"source": "maintenance_note", "span": [0, 5]},
            ],
            "uncertainty": 0.35,
        }
    ],
    "missing_information": ["crack_dimensions"],
}

WONDER_DICT = {
    "discrepancies": [],
    "missing_information": ["inspection_date"],
    "recommended_next_step": "Request qualified inspection with measurement tape.",
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


class _FakeSam:
    def segment_image(self, image: bytes, prompts: Any, *, source_image: str, **kw: Any):
        return [_decoded(source=source_image)]


class _FakeVision:
    def extract(self, *a: Any, **kw: Any) -> VisionObservation:
        return VisionObservation(
            asset_type="drainage_structure",
            model_id="muse-spark-1.3",
            usage=ChatUsage(prompt_tokens=1000, completion_tokens=500, total_tokens=1500),
        )


class _FakeWonder:
    def __init__(self, plan: WonderPlan) -> None:
        self.plan_obj = plan
        self.seen: dict[str, Any] = {}

    def plan(self, draft: Any, vision: Any, note: str, meta: Any, rid: Any) -> WonderPlan:
        self.seen = {"observations": len(draft.observations), "note": note}
        return self.plan_obj


def _spark_client(handler: Any) -> MetaClient:
    settings = _settings()
    return MetaClient(
        settings=settings, transport=httpx.MockTransport(handler), retry_wait=lambda _s: 0
    )


def _spark_ok(request: httpx.Request) -> httpx.Response:
    return httpx.Response(
        200,
        json={
            "choices": [{"message": {"content": json.dumps(SPARK_JSON)}}],
            "usage": {"prompt_tokens": 800, "completion_tokens": 120},
        },
    )


def _plan(**over: Any) -> WonderPlan:
    base: dict[str, Any] = dict(WONDER_DICT)
    base.update(over)
    base.setdefault("usage", ChatUsage(prompt_tokens=700, completion_tokens=80))
    base.setdefault("model_id", "muse-wonder-1.0")
    return WonderPlan(**base)


def _has_image_parts(body: dict[str, Any]) -> bool:
    for message in body.get("messages", []):
        content = message.get("content", [])
        if isinstance(content, list):
            for part in content:
                if isinstance(part, dict) and part.get("type") == "image_url":
                    return True
    return False


def test_run_full_returns_validated_result() -> None:
    from app.orchestrator.spark import SparkReasoner

    pipe = InspectionPipeline(
        sam=_FakeSam(),  # type: ignore[arg-type]
        vision=_FakeVision(),  # type: ignore[arg-type]
        spark=SparkReasoner(client=_spark_client(_spark_ok), settings=_settings()),
        wonder=_FakeWonder(_plan()),  # type: ignore[arg-type]
        settings=_settings(),
    )
    out = pipe.run_full([JPEG], note="Crack seen", asset_meta={"asset_id": "F-1"})
    assert out.asset_id == "F-1"
    assert out.model_trace.planning == "muse-wonder-1.0"
    assert out.missing_information == ["crack_dimensions", "inspection_date"]
    assert out.recommended_next_step.startswith("Request qualified inspection")
    assert out.human_review_required is True


def test_run_full_merges_missing_without_dupes() -> None:
    from app.orchestrator.spark import SparkReasoner

    pipe = InspectionPipeline(
        sam=_FakeSam(),  # type: ignore[arg-type]
        vision=_FakeVision(),  # type: ignore[arg-type]
        spark=SparkReasoner(client=_spark_client(_spark_ok), settings=_settings()),
        wonder=_FakeWonder(_plan(missing_information=["crack_dimensions", "weather"])),
        settings=_settings(),
    )
    out = pipe.run_full([JPEG], note="Crack seen")
    assert out.missing_information == ["crack_dimensions", "weather"]


def test_run_full_rejects_invalid_draft() -> None:
    from app.orchestrator.spark import SparkReasoner

    bad_spark = {
        **SPARK_JSON,
        "observations": [
            {
                **SPARK_JSON["observations"][0],
                "evidence": [{"source": "image_0", "mask_id": "mask_NOPE"}],
            }
        ],
    }

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200, json={"choices": [{"message": {"content": json.dumps(bad_spark)}}]}
        )

    pipe = InspectionPipeline(
        sam=_FakeSam(),  # type: ignore[arg-type]
        vision=_FakeVision(),  # type: ignore[arg-type]
        spark=SparkReasoner(client=_spark_client(handler), settings=_settings()),
        wonder=_FakeWonder(_plan()),
        settings=_settings(),
    )
    with pytest.raises(ValidationError, match="unknown mask_id"):
        pipe.run_full([JPEG], note="Crack seen")


def test_run_full_cost_includes_wonder(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.orchestrator.spark import SparkReasoner

    monkeypatch.setenv("META_PRICE_PER_1K_CENTS_MUSE_WONDER_1_0", "3.0")
    pipe = InspectionPipeline(
        sam=_FakeSam(),  # type: ignore[arg-type]
        vision=_FakeVision(),  # type: ignore[arg-type]
        spark=SparkReasoner(client=_spark_client(_spark_ok), settings=_settings()),
        wonder=_FakeWonder(_plan()),
        settings=_settings(),
    )
    out = pipe.run_full([JPEG], note="Crack seen")
    # only wonder is priced here: (780/1000)*3.0 = 2.34, overall unpriced
    assert out.cost_cents == pytest.approx(2.34)
    assert out.cost_priced is False


def test_full_chain_all_real_components() -> None:
    img = Image.new("RGB", (32, 24), (200, 200, 200))
    buf = BytesIO()
    img.save(buf, format="JPEG")
    image_bytes = buf.getvalue()
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
        if body["model"] == "muse-spark-1.3":
            return httpx.Response(
                200, json={"choices": [{"message": {"content": json.dumps(SPARK_JSON)}}]}
            )
        assert body["model"] == "muse-wonder-1.0"
        return httpx.Response(
            200, json={"choices": [{"message": {"content": json.dumps(WONDER_DICT)}}]}
        )

    settings = _settings()
    client = MetaClient(
        settings=settings, transport=httpx.MockTransport(handler), retry_wait=lambda _s: 0
    )
    from app.orchestrator.spark import SparkReasoner
    from app.planner import WonderPlanner

    pipe = InspectionPipeline(
        sam=SamService(client=client, settings=settings),
        vision=VisionExtractor(client=client, settings=settings),
        spark=SparkReasoner(client=client, settings=settings),
        wonder=WonderPlanner(client=client, settings=settings),
        settings=settings,
    )
    out = pipe.run_full([image_bytes], note="Crack seen", asset_meta={"asset_id": "E2E-5"})
    assert out.asset_id == "E2E-5"
    assert out.model_trace.planning == "muse-wonder-1.0"
    assert out.observations[0].evidence[0].mask_id == "mask_1"
    assert out.missing_information == ["crack_dimensions", "inspection_date"]


def test_run_full_records_stage_durations() -> None:
    from app.orchestrator.spark import SparkReasoner

    pipe = InspectionPipeline(
        sam=_FakeSam(),  # type: ignore[arg-type]
        vision=_FakeVision(),  # type: ignore[arg-type]
        spark=SparkReasoner(client=_spark_client(_spark_ok), settings=_settings()),
        wonder=_FakeWonder(_plan()),  # type: ignore[arg-type]
        settings=_settings(),
    )
    out = pipe.run_full([JPEG], note="Crack seen", asset_meta={"asset_id": "F-1"})
    assert set(out.durations_ms) == {"sam", "vision", "spark", "wonder", "validate"}
    assert all(v >= 0 for v in out.durations_ms.values())


def test_budget_alert_logs_over_50c(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    from app.orchestrator.spark import SparkReasoner

    monkeypatch.setenv("META_PRICE_PER_IMAGE_CENTS_SAM_3_1", "100.0")
    pipe = InspectionPipeline(
        sam=_FakeSam(),  # type: ignore[arg-type]
        vision=_FakeVision(),  # type: ignore[arg-type]
        spark=SparkReasoner(client=_spark_client(_spark_ok), settings=_settings()),
        wonder=_FakeWonder(_plan()),  # type: ignore[arg-type]
        settings=_settings(),
    )
    with caplog.at_level(logging.WARNING, logger="asset_intel.pipeline"):
        pipe.run_full([JPEG], note="Crack seen", asset_meta={"asset_id": "F-1"})
    assert "cost_budget_alert" in caplog.text
