"""Inspection pipeline: SAM → Vision → Spark → Wonder → Validate (Day 5).

Day 7: OTEL spans per stage (sam.segment, vision.extract, spark.reason,
wonder.plan, validate) + SAM-degraded fallback: when segmentation is
unavailable, the pipeline continues vision-only with uncertainties clamped
to ≥0.9 and a requires_human_measurement flag (ARCH §11; key normalized to
the snake_case missing-information contract). `run()` stops at the Spark
draft; `run_full()` continues through planning and fail-closed validation.
No stage certifies safety, declares compliance, or creates work orders.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from typing import Any, Literal
from uuid import uuid4

from opentelemetry import trace
from pydantic import BaseModel

from app.gateway import MetaClient, Segmentation, Settings
from app.gateway.errors import MetaRateLimitError, MetaServerError, MetaTimeoutError
from app.gateway.meta_client import ChatUsage
from app.gateway.pricing import estimate_chat_cost_cents, estimate_per_image_cost_cents
from app.orchestrator.errors import PipelineInputError
from app.orchestrator.spark import DraftObservation, SparkReasoner
from app.planner import WonderPlanner
from app.sam_service import DecodedMask, SamService
from app.validator import InspectionResult, validate_inspection
from app.vision import VisionExtractor, VisionObservation

logger = logging.getLogger("asset_intel.pipeline")
tracer = trace.get_tracer("asset_intel.pipeline")

MAX_IMAGES = 5
MAX_NOTE_CHARS = 10_000  # ARCHITECTURE.md §4.1
MAX_WORKERS = 5


class ModelTrace(BaseModel):
    sam: str
    vision: str
    vision_fallback_used: bool = False
    reasoning: str
    timestamp: str


class DraftResult(BaseModel):
    request_id: str
    asset_id: str
    asset_type: str | None = None
    segmentations: list[Segmentation] = []
    observations: list[DraftObservation] = []
    missing_information: list[str] = []
    human_review_required: Literal[True] = True
    model_trace: ModelTrace
    cost_cents: float = 0.0
    cost_priced: bool = False


class InspectionPipeline:
    """Orchestrates SAM (parallel) → Vision → Spark → Wonder → Validate."""

    def __init__(
        self,
        sam: SamService | None = None,
        vision: VisionExtractor | None = None,
        spark: SparkReasoner | None = None,
        wonder: WonderPlanner | None = None,
        settings: Settings | None = None,
        client: MetaClient | None = None,
        max_workers: int = MAX_WORKERS,
    ) -> None:
        self._settings = settings or Settings.from_env()
        self._sam = sam or SamService(client=client, settings=self._settings)
        self._vision = vision or VisionExtractor(client=client, settings=self._settings)
        self._spark = spark or SparkReasoner(client=client, settings=self._settings)
        self._wonder = wonder or WonderPlanner(client=client, settings=self._settings)
        self._max_workers = max(1, max_workers)

    def run(
        self,
        images: Sequence[bytes],
        note: str = "",
        asset_meta: dict[str, Any] | None = None,
        request_id: str | None = None,
    ) -> DraftResult:
        """Run SAM → Vision → Spark and assemble the validated draft."""
        draft, _, _, _, _ = self._execute(images, note, asset_meta, request_id)
        return draft

    def run_full(
        self,
        images: Sequence[bytes],
        note: str = "",
        asset_meta: dict[str, Any] | None = None,
        request_id: str | None = None,
    ) -> InspectionResult:
        """Run the full chain through Wonder planning and fail-closed validation."""
        draft, vision, meta, text, image_count = self._execute(
            images, note, asset_meta, request_id
        )
        with tracer.start_as_current_span("wonder.plan") as span:
            plan = self._wonder.plan(draft, vision, text, meta, draft.request_id)
            span.set_attribute("planning.model_id", plan.model_id)
        wonder_cents, wonder_priced = estimate_chat_cost_cents(
            plan.model_id, plan.usage.prompt_tokens, plan.usage.completion_tokens
        )
        trace = draft.model_trace.model_dump()
        trace["planning"] = plan.model_id
        payload = draft.model_dump()
        payload.update(
            discrepancies=plan.discrepancies,
            missing_information=_merge_missing(
                draft.missing_information, plan.missing_information
            ),
            recommended_next_step=plan.recommended_next_step,
            model_trace=trace,
            cost_cents=round(draft.cost_cents + wonder_cents, 4),
            cost_priced=bool(draft.cost_priced and wonder_priced),
        )
        with tracer.start_as_current_span("validate"):
            return validate_inspection(payload, note=text, image_count=image_count)

    def _execute(
        self,
        images: Sequence[bytes],
        note: str,
        asset_meta: dict[str, Any] | None,
        request_id: str | None,
    ) -> tuple[DraftResult, VisionObservation, dict[str, Any], str, int]:
        imgs = self._validate_images(images)
        text = self._validate_note(note)
        meta = self._validate_asset_meta(asset_meta)
        rid = request_id or f"req_{uuid4().hex[:24]}"  # same interim format as gateway

        with tracer.start_as_current_span("sam.segment") as span:
            span.set_attribute("image_count", len(imgs))
            try:
                masks_by_image = self._segment_all(imgs, rid)
                span.set_attribute("mask_count", sum(map(len, masks_by_image)))
                sam_degraded = False
            except (MetaRateLimitError, MetaServerError, MetaTimeoutError) as exc:
                logger.warning(
                    "sam_degraded",
                    extra={"request_id": rid, "error_type": type(exc).__name__},
                )
                span.set_attribute("degraded", True)
                masks_by_image = [[] for _ in imgs]
                sam_degraded = True

        with tracer.start_as_current_span("vision.extract") as span:
            vision = self._vision.extract(imgs, masks_by_image, text, meta, rid)
            span.set_attribute("vision.model_id", vision.model_id)
            span.set_attribute("vision.fallback_used", vision.fallback_used)
        with tracer.start_as_current_span("spark.reason") as span:
            draft = self._spark.reason(
                vision.model_dump_json(), masks_by_image, text, meta, rid
            )
            span.set_attribute("reasoning.model_id", draft.model_id)

        cost_cents, priced = self._total_cost(vision, draft.usage, len(imgs))
        result = DraftResult(
            request_id=rid,
            asset_id=meta.get("asset_id") or f"ASSET-{rid}",
            asset_type=draft.asset_type or vision.asset_type,
            segmentations=[d.mask for per_image in masks_by_image for d in per_image],
            observations=draft.observations,
            missing_information=draft.missing_information,
            model_trace=ModelTrace(
                sam=self._settings.sam_model_id,
                vision=vision.model_id,
                vision_fallback_used=vision.fallback_used,
                reasoning=draft.model_id,
                timestamp=datetime.now(UTC).isoformat(),
            ),
            cost_cents=cost_cents,
            cost_priced=priced,
        )
        if sam_degraded:
            # ARCH §11 vision-only fallback: masks stay empty, uncertainty is
            # pinned high, and the missing measurement is flagged. The key is
            # the snake_case form of ARCH's "requires human measurement".
            for ob in result.observations:
                ob.uncertainty = max(ob.uncertainty, 0.9)
            if "requires_human_measurement" not in result.missing_information:
                result.missing_information.append("requires_human_measurement")
        logger.info(
            "pipeline_complete",
            extra={
                "request_id": rid,
                "mask_count": len(result.segmentations),
                "observation_count": len(result.observations),
                "cost_cents": cost_cents,
                "cost_priced": priced,
            },
        )
        return result, vision, meta, text, len(imgs)

    def _segment_all(
        self, imgs: list[bytes], request_id: str
    ) -> list[list[DecodedMask]]:
        workers = min(len(imgs), self._max_workers)
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = [
                pool.submit(
                    self._sam.segment_image,
                    img,
                    None,
                    source_image=f"image_{i}",
                    request_id=request_id,
                )
                for i, img in enumerate(imgs)
            ]
            return [f.result() for f in futures]

    def _total_cost(
        self, vision: VisionObservation, spark_usage: ChatUsage, image_count: int
    ) -> tuple[float, bool]:
        sam_each, sam_priced = estimate_per_image_cost_cents(self._settings.sam_model_id)
        vis_cents, vis_priced = estimate_chat_cost_cents(
            vision.model_id, vision.usage.prompt_tokens, vision.usage.completion_tokens
        )
        spark_cents, spark_priced = estimate_chat_cost_cents(
            self._settings.reasoning_model_id,
            spark_usage.prompt_tokens,
            spark_usage.completion_tokens,
        )
        total = round(sam_each * image_count + vis_cents + spark_cents, 4)
        return total, bool(sam_priced and vis_priced and spark_priced)

    @staticmethod
    def _validate_images(images: Sequence[bytes]) -> list[bytes]:
        imgs = list(images)
        if not 1 <= len(imgs) <= MAX_IMAGES:
            raise PipelineInputError(f"need 1-{MAX_IMAGES} images, got {len(imgs)}")
        if any(not isinstance(b, bytes) or not b for b in imgs):
            raise PipelineInputError("images must be non-empty bytes")
        return imgs

    @staticmethod
    def _validate_note(note: str) -> str:
        if not isinstance(note, str):
            raise PipelineInputError("note must be a string")
        if len(note) > MAX_NOTE_CHARS:
            raise PipelineInputError(
                f"note is {len(note)} chars, max is {MAX_NOTE_CHARS}"
            )
        return note

    @staticmethod
    def _validate_asset_meta(asset_meta: dict[str, Any] | None) -> dict[str, Any]:
        if asset_meta is None:
            return {}
        if not isinstance(asset_meta, dict):
            raise PipelineInputError("asset_meta must be a dict")
        return asset_meta


def _merge_missing(first: list[str], second: list[str]) -> list[str]:
    """Ordered union: Spark's keys first, then Wonder's additions."""
    merged = list(first)
    merged.extend(k for k in second if k not in merged)
    return merged
