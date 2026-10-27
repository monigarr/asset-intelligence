"""Muse Spark 1.3 structured reasoning (Day 4).

Turns fused vision evidence + SAM masks + note into an evidence-linked draft:
observations with mandatory evidence pointers, uncertainty, and a first pass
at missing information. Structural validation happens here; semantic
fail-closed validation (mask ids exist, spans in bounds, no invented numbers)
is the Day-5 validator's job. Prompt follows ARCHITECTURE.md §4.4 verbatim.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Sequence
from typing import Any

from pydantic import BaseModel, Field, ValidationError

from app.gateway import MetaClient, Settings
from app.gateway.errors import MetaResponseError
from app.gateway.meta_client import ChatUsage
from app.sam_service import DecodedMask
from app.vision.extractor import summarize_masks_for_prompt

logger = logging.getLogger("asset_intel.spark")

SPARK_SYSTEM_PROMPT = (
    "You are an infrastructure inspection analyst. "
    "Return ONLY valid JSON per schema. "
    "Every observation must cite evidence: image index + mask_id or note span. "
    "Never invent measurements. "
    "Evidence before inference. Explicit uncertainty over false precision."
)

OBSERVATION_JSON_SCHEMA: dict[str, Any] = {
    "name": "inspection_draft",
    "schema": {
        "type": "object",
        "required": ["observations", "missing_information"],
        "properties": {
            "asset_type": {"type": ["string", "null"]},
            "observations": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["text", "evidence", "uncertainty"],
                    "properties": {
                        "text": {"type": "string"},
                        "evidence": {
                            "type": "array",
                            "minItems": 1,
                            "items": {
                                "type": "object",
                                "required": ["source"],
                                "properties": {
                                    "source": {"type": "string"},
                                    "mask_id": {"type": ["string", "null"]},
                                    "span": {
                                        "type": ["array"],
                                        "items": {"type": "integer"},
                                        "minItems": 2,
                                        "maxItems": 2,
                                    },
                                },
                            },
                        },
                        "uncertainty": {
                            "type": "number",
                            "minimum": 0,
                            "maximum": 1,
                        },
                    },
                },
            },
            "missing_information": {"type": "array", "items": {"type": "string"}},
        },
        "additionalProperties": False,
    },
}


class EvidenceRef(BaseModel):
    source: str  # image_<i> or maintenance_note
    mask_id: str | None = None
    span: list[int] | None = Field(default=None, min_length=2, max_length=2)


class DraftObservation(BaseModel):
    text: str
    evidence: list[EvidenceRef] = Field(min_length=1)
    uncertainty: float = Field(ge=0.0, le=1.0)


class SparkDraft(BaseModel):
    asset_type: str | None = None
    observations: list[DraftObservation]
    missing_information: list[str] = []
    usage: ChatUsage = ChatUsage()
    model_id: str


class SparkReasoner:
    """Evidence-linked draft generation over the reasoning model."""

    def __init__(
        self,
        client: MetaClient | None = None,
        settings: Settings | None = None,
    ) -> None:
        self._settings = settings or Settings.from_env()
        self._client = client or MetaClient(settings=self._settings)

    def reason(
        self,
        vision_json: str,
        masks_by_image: Sequence[Sequence[DecodedMask]],
        note: str,
        asset_meta: dict[str, Any],
        request_id: str | None = None,
    ) -> SparkDraft:
        """Produce a validated draft from fused evidence."""
        image_refs = ", ".join(f"image_{i}" for i in range(len(masks_by_image)))
        result = self._client.chat(
            self._settings.reasoning_model_id,
            [
                {"role": "system", "content": SPARK_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": (
                        f"IMAGES: {image_refs} with SAM masks\n"
                        f"{summarize_masks_for_prompt(masks_by_image)}\n"
                        f"NOTE: {note}\n"
                        f"ASSET_META: {json.dumps(asset_meta)}\n"
                        f"VISION: {vision_json}\n"
                        "TASK: Produce JSON matching schema. "
                        "If dimension missing, list in missing_information."
                    ),
                },
            ],
            response_format={
                "type": "json_schema",
                "json_schema": OBSERVATION_JSON_SCHEMA,
            },
            request_id=request_id,
        )
        data = result.data
        if data is None:
            raise MetaResponseError("reasoning model returned no JSON data")
        try:
            draft = SparkDraft(
                asset_type=data.get("asset_type"),
                observations=data["observations"],
                missing_information=data.get("missing_information", []),
                usage=result.usage,
                model_id=self._settings.reasoning_model_id,
            )
        except (KeyError, ValidationError) as exc:
            raise MetaResponseError(
                f"reasoning model returned invalid draft: {exc}"
            ) from exc
        logger.debug(
            "spark_draft",
            extra={
                "request_id": request_id,
                "model_id": draft.model_id,
                "observation_count": len(draft.observations),
            },
        )
        return draft
