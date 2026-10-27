"""SAM-degraded fallback: vision-only pipeline, high uncertainty, flagged."""

from __future__ import annotations

from typing import Any

import pytest

from app.gateway.errors import (
    MetaAuthError,
    MetaClientError,
    MetaRateLimitError,
    MetaServerError,
    MetaTimeoutError,
)
from app.gateway.meta_client import ChatUsage
from app.orchestrator.pipeline import DraftResult, InspectionPipeline
from app.orchestrator.spark import DraftObservation, EvidenceRef, SparkDraft
from app.planner import WonderPlan
from app.vision import VisionObservation

NOTE = "Crack seen"
JPEG = b"\xff\xd8\xff" + b"\x00" * 64


class _FailingSam:
    def __init__(self, error: Exception) -> None:
        self.error = error

    def segment_image(self, *a: Any, **k: Any):
        raise self.error


class _FakeVision:
    def extract(self, *a: Any, **k: Any) -> VisionObservation:
        return VisionObservation(
            model_id="muse-spark-1.3",
            usage=ChatUsage(prompt_tokens=10, completion_tokens=5, total_tokens=15),
        )


def _draft() -> SparkDraft:
    return SparkDraft(
        asset_type="drainage_structure",
        observations=[
            DraftObservation(
                text="possible crack",
                evidence=[EvidenceRef(source="maintenance_note", span=[0, 5])],
                uncertainty=0.2,
            )
        ],
        missing_information=[],
        usage=ChatUsage(prompt_tokens=10, completion_tokens=5, total_tokens=15),
        model_id="muse-spark-1.3",
    )


class _FakeSpark:
    def reason(self, *a: Any, **k: Any) -> SparkDraft:
        return _draft()


class _FakeWonder:
    def plan(self, *a: Any, **k: Any) -> WonderPlan:
        return WonderPlan(
            discrepancies=[],
            missing_information=[],
            recommended_next_step="Request qualified inspection.",
            model_id="muse-wonder-1.0",
        )


def _pipe(error: Exception) -> InspectionPipeline:
    from app.gateway import Settings

    return InspectionPipeline(
        sam=_FailingSam(error),  # type: ignore[arg-type]
        vision=_FakeVision(),  # type: ignore[arg-type]
        spark=_FakeSpark(),  # type: ignore[arg-type]
        wonder=_FakeWonder(),  # type: ignore[arg-type]
        settings=Settings(api_key="t"),
    )


@pytest.mark.parametrize(
    "error",
    [MetaServerError("down"), MetaTimeoutError("t"), MetaRateLimitError("slow")],
)
def test_sam_degraded_run_full(error: Exception) -> None:
    out = _pipe(error).run_full([JPEG], note=NOTE)
    assert out.segmentations == []
    assert out.observations[0].uncertainty == 0.9
    assert "requires_human_measurement" in out.missing_information


def test_sam_degraded_run() -> None:
    draft: DraftResult = _pipe(MetaServerError("down")).run([JPEG], note=NOTE)
    assert draft.segmentations == []
    assert draft.observations[0].uncertainty == 0.9


@pytest.mark.parametrize(
    "error", [MetaAuthError("bad"), MetaClientError("rejected")],
)
def test_deterministic_sam_errors_propagate(error: Exception) -> None:
    with pytest.raises(type(error)):
        _pipe(error).run_full([JPEG], note=NOTE)
