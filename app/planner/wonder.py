"""Muse Wonder planning review (Day 5).

Reviews the Spark draft + fused vision evidence and produces discrepancies,
finalized missing information, and a non-certifying recommended next step.
Text reasoning only — no raw images (ARCHITECTURE.md §5: draft + vision in).

Defense in depth: the prompt forbids certification, and the Day-5 validator
independently rejects certifying language, so a prompt-injection or model
slip still fails closed.
"""

from __future__ import annotations

import json
import logging
import re
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field, ValidationError, field_validator

from app.gateway import MetaClient, Settings
from app.gateway.errors import MetaResponseError
from app.gateway.meta_client import ChatUsage

if TYPE_CHECKING:  # breaks the planner <-> orchestrator import cycle
    from app.orchestrator.pipeline import DraftResult
    from app.vision import VisionObservation

logger = logging.getLogger("asset_intel.planner")

WONDER_SYSTEM_PROMPT = (
    "You are a maintenance planning reviewer. Given observations and evidence, "
    "decide what contradicts, what is missing for a qualified decision, and the "
    "safest next step. "
    "Rules: NEVER certify safe or unsafe. NEVER declare compliance. NEVER invent "
    "measurements, dimensions, or dates. Flag contradictions between the note and "
    "the images. List missing information as short snake_case keys "
    "(e.g. crack_dimensions, inspection_date). Recommend only non-certifying next "
    "steps such as requesting a qualified inspection or re-photographing with a "
    "scale reference. Return ONLY JSON matching the schema."
)

WONDER_JSON_SCHEMA: dict[str, Any] = {
    "name": "wonder_plan",
    "schema": {
        "type": "object",
        "required": ["discrepancies", "missing_information", "recommended_next_step"],
        "properties": {
            "discrepancies": {"type": "array", "items": {"type": "string"}},
            "missing_information": {
                "type": "array",
                "items": {"type": "string", "pattern": "^[a-z0-9_]+$"},
            },
            "recommended_next_step": {"type": "string", "minLength": 1},
        },
        "additionalProperties": False,
    },
}

_MISSING_KEY_RE = re.compile(r"^[a-z0-9_]+$")


class WonderPlan(BaseModel):
    discrepancies: list[str]
    missing_information: list[str]
    recommended_next_step: str = Field(min_length=1)
    usage: ChatUsage = ChatUsage()
    model_id: str

    @field_validator("discrepancies")
    @classmethod
    def _no_blank_discrepancies(cls, items: list[str]) -> list[str]:
        if any(not s.strip() for s in items):
            raise ValueError("discrepancies must be non-empty strings")
        return items

    @field_validator("missing_information")
    @classmethod
    def _keys_snake_case(cls, items: list[str]) -> list[str]:
        bad = [s for s in items if not _MISSING_KEY_RE.match(s)]
        if bad:
            raise ValueError(f"missing_information keys must be snake_case: {bad}")
        return items

    @field_validator("recommended_next_step")
    @classmethod
    def _next_step_nonblank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("recommended_next_step must be non-blank")
        return value


class WonderPlanner:
    """Discrepancy + missing-info + next-step review over the planning model."""

    def __init__(
        self,
        client: MetaClient | None = None,
        settings: Settings | None = None,
    ) -> None:
        self._settings = settings or Settings.from_env()
        self._client = client or MetaClient(settings=self._settings)

    def plan(
        self,
        draft: DraftResult,
        vision: VisionObservation,
        note: str,
        asset_meta: dict[str, Any],
        request_id: str | None = None,
    ) -> WonderPlan:
        """Review the draft and produce the planning verdict."""
        # Re-group segmentations per image for the shared mask summarizer.
        per_image: dict[int, list[Any]] = {}
        for seg in draft.segmentations:
            try:
                idx = int(seg.source_image.split("_", 1)[1]) if seg.source_image else 0
            except (ValueError, IndexError):
                idx = 0
            per_image.setdefault(idx, []).append(seg)
        mask_lines = []
        for i in sorted(per_image):
            mask_lines.append(f"image_{i} ({len(per_image[i])} masks):")
            for m in per_image[i]:
                mask_lines.append(
                    f"- {m.mask_id}: {m.label}, conf {m.confidence:.2f}, "
                    f"bbox {m.bbox} ({m.source_image})"
                )
        masks_text = "\n".join(mask_lines) if mask_lines else "(no segmentations)"

        result = self._client.chat(
            self._settings.planning_model_id,
            [
                {"role": "system", "content": WONDER_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": (
                        "OBSERVATIONS:\n"
                        f"{json.dumps([o.model_dump() for o in draft.observations])}\n"
                        f"VISION: {vision.model_dump_json(exclude={'usage'})}\n"
                        f"SEGMENTATIONS:\n{masks_text}\n"
                        f"NOTE: {note}\n"
                        f"ASSET_META: {json.dumps(asset_meta)}\n"
                        "TASK: Given observations + evidence, what contradicts? "
                        "What is missing for a qualified decision? What is the "
                        "safest next step that is NOT a certification?"
                    ),
                },
            ],
            response_format={
                "type": "json_schema",
                "json_schema": WONDER_JSON_SCHEMA,
            },
            request_id=request_id,
        )
        data = result.data
        if data is None:
            raise MetaResponseError("planning model returned no JSON data")
        try:
            plan = WonderPlan(
                discrepancies=data["discrepancies"],
                missing_information=data["missing_information"],
                recommended_next_step=data["recommended_next_step"],
                usage=result.usage,
                model_id=self._settings.planning_model_id,
            )
        except (KeyError, ValidationError) as exc:
            raise MetaResponseError(
                f"planning model returned invalid plan: {exc}"
            ) from exc
        logger.debug(
            "wonder_plan",
            extra={
                "request_id": request_id,
                "model_id": plan.model_id,
                "discrepancy_count": len(plan.discrepancies),
            },
        )
        return plan
