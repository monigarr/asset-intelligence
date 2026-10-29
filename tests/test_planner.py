"""Wonder planner tests (mocked transport)."""

from __future__ import annotations

import json
from typing import Any

import httpx
import pytest

from app.gateway import MetaClient, Segmentation, Settings
from app.gateway.errors import MetaResponseError
from app.gateway.meta_client import ChatUsage
from app.orchestrator.pipeline import DraftResult, ModelTrace
from app.orchestrator.spark import DraftObservation, EvidenceRef
from app.planner import WonderPlanner
from app.vision import VisionObservation

WONDER_JSON = {
    "discrepancies": ["Note estimates length but no scale reference in image"],
    "missing_information": ["crack_dimensions", "inspection_date"],
    "recommended_next_step": "Request qualified inspection with measurement tape.",
}


def _draft() -> DraftResult:
    return DraftResult(
        request_id="req_d1",
        asset_id="A-1",
        segmentations=[
            Segmentation(
                mask_id="mask_1",
                label="crack",
                bbox=[4, 4, 20, 20],
                confidence=0.87,
                source_image="image_0",
            )
        ],
        observations=[
            DraftObservation(
                text="crack visible",
                evidence=[EvidenceRef(source="image_0", mask_id="mask_1")],
                uncertainty=0.3,
            )
        ],
        missing_information=["weather"],
        model_trace=ModelTrace(
            sam="sam-3.1",
            vision="muse-spark-1.3",
            reasoning="muse-spark-1.3",
            timestamp="2026-10-26T00:00:00+00:00",
        ),
    )


def _vision() -> VisionObservation:
    return VisionObservation(
        asset_type="drainage_structure",
        condition_tags=["crack"],
        symptoms=[],
        model_id="muse-spark-1.3",
        usage=ChatUsage(prompt_tokens=10, completion_tokens=5, total_tokens=15),
    )


def _planner(handler: Any) -> WonderPlanner:
    settings = Settings(api_key="test", base_url="https://api.test/v1")
    client = MetaClient(
        settings=settings, transport=httpx.MockTransport(handler), retry_wait=lambda _s: 0
    )
    return WonderPlanner(client=client, settings=settings)


def test_plan_prompt_contract() -> None:
    seen: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["body"] = json.loads(request.content.decode())
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": json.dumps(WONDER_JSON)}}],
                "usage": {"prompt_tokens": 900, "completion_tokens": 90},
            },
        )

    plan = _planner(handler).plan(
        _draft(), _vision(), "Crack near top", {"asset_id": "A-1"}, request_id="req_w1"
    )
    assert plan.missing_information == ["crack_dimensions", "inspection_date"]
    assert plan.usage.completion_tokens == 90
    assert plan.model_id == "muse-wonder-1.0"

    body = seen["body"]
    assert body["model"] == "muse-wonder-1.0"
    assert body["response_format"]["json_schema"]["name"] == "wonder_plan"
    assert "NEVER certify" in body["messages"][0]["content"]
    user_text = body["messages"][1]["content"]
    for needle in (
        "crack visible",
        "mask_1",
        "drainage_structure",
        "Crack near top",
        "A-1",
        "NOT a certification",
    ):
        assert needle in user_text


def test_plan_rejects_bad_payloads() -> None:
    def handler_for(payload: Any):
        def handler(request: httpx.Request) -> httpx.Response:
            content = payload if isinstance(payload, str) else json.dumps(payload)
            return httpx.Response(200, json={"choices": [{"message": {"content": content}}]})

        return handler

    base = dict(WONDER_JSON)
    bad_cases = [
        ({**base, "missing_information": ["Crack size"]}, "snake_case"),
        ({**base, "discrepancies": ["  "]}, "non-empty strings"),
        ({**base, "recommended_next_step": "  "}, "non-blank"),
        ({"discrepancies": []}, "invalid plan"),  # missing keys entirely
        ("not json", "not valid JSON"),  # gateway-level rejection
    ]
    for payload, match in bad_cases:
        with pytest.raises(MetaResponseError, match=match):
            _planner(handler_for(payload)).plan(_draft(), _vision(), "n", {})


def test_wonder_prompt_has_discrepancy_decision_rule() -> None:
    from app.planner.wonder import WONDER_SYSTEM_PROMPT

    assert "MUST surface" in WONDER_SYSTEM_PROMPT
    assert "empty discrepancies array" in WONDER_SYSTEM_PROMPT
    assert "never placeholder or filler text" in WONDER_SYSTEM_PROMPT


def test_wonder_retries_once_with_stricter_prompt() -> None:
    from types import SimpleNamespace

    from app.gateway import Settings
    from app.gateway.meta_client import ChatUsage
    from app.planner.wonder import WonderPlanner

    calls: list[str] = []

    class _SeqClient:
        def chat(self, model_id: str, messages: list, **kwargs: object):  # type: ignore[no-untyped-def]
            calls.append(messages[1]["content"])
            if len(calls) == 1:
                return SimpleNamespace(data={}, usage=ChatUsage())
            good = {
                "discrepancies": [],
                "missing_information": [],
                "recommended_next_step": "Escalate to qualified inspector.",
            }
            return SimpleNamespace(data=good, usage=ChatUsage())

    planner = WonderPlanner(client=_SeqClient(), settings=Settings(api_key="t"))  # type: ignore[arg-type]
    draft = SimpleNamespace(segmentations=[], observations=[], request_id="r1")
    vision = SimpleNamespace(model_dump_json=lambda **kwargs: "{}")
    plan = planner.plan(draft, vision, "note", {}, request_id="r1")  # type: ignore[arg-type]
    assert plan.recommended_next_step.startswith("Escalate")
    assert len(calls) == 2
    assert "STRICT RETRY" in calls[1]
