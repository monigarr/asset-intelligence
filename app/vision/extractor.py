"""Llama 4 Maverick Vision evidence fusion (Day 4).

Fuses inspection images + SAM mask summaries + field note + asset context into
a grounded intermediate observation. Falls back to Llama 4 Scout once when the
primary model is unavailable (GAP default: ARCHITECTURE.md §4.3 names Scout as
the cost-efficient fallback but pins no trigger; retriable-exhaustion is the
trigger — deterministic failures like 401/invalid JSON never fall back).

Note spans are [start, end] character offsets into the NOTE text as sent.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Sequence
from typing import Any

from pydantic import BaseModel, Field, ValidationError

from app.gateway import MetaClient, Settings
from app.gateway.errors import (
    MetaRateLimitError,
    MetaResponseError,
    MetaServerError,
    MetaTimeoutError,
)
from app.gateway.meta_client import ChatUsage
from app.sam_service import DecodedMask

logger = logging.getLogger("asset_intel.vision")

VISION_SYSTEM_PROMPT = (
    "You fuse inspection evidence into grounded symptoms. "
    "Ground every symptom in the attached images, the SAM masks, or the note, "
    "and cite evidence for each. Never invent measurements, dimensions, or dates. "
    "Prefer explicit uncertainty over false precision. "
    "Return ONLY JSON matching the schema."
)

VISION_JSON_SCHEMA: dict[str, Any] = {
    "name": "vision_observation",
    "schema": {
        "type": "object",
        "required": ["symptoms"],
        "properties": {
            "asset_type": {"type": ["string", "null"]},
            "condition_tags": {"type": "array", "items": {"type": "string"}},
            "symptoms": {
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
        },
        "additionalProperties": False,
    },
}

_FALLBACK_ERRORS = (MetaRateLimitError, MetaServerError, MetaTimeoutError)


class VisionEvidence(BaseModel):
    source: str  # image_<i> or maintenance_note
    mask_id: str | None = None
    span: list[int] | None = Field(default=None, min_length=2, max_length=2)


class VisionSymptom(BaseModel):
    text: str
    evidence: list[VisionEvidence] = Field(min_length=1)
    uncertainty: float = Field(ge=0.0, le=1.0)


class VisionObservation(BaseModel):
    asset_type: str | None = None
    condition_tags: list[str] = []
    symptoms: list[VisionSymptom] = []
    model_id: str
    fallback_used: bool = False
    usage: ChatUsage = ChatUsage()


def summarize_masks_for_prompt(
    masks_by_image: Sequence[Sequence[DecodedMask]],
) -> str:
    """Render decoded masks as compact text the vision/reasoning models can cite."""
    lines = []
    for i, masks in enumerate(masks_by_image):
        if not masks:
            lines.append(f"image_{i} (0 masks): none")
            continue
        lines.append(f"image_{i} ({len(masks)} masks):")
        for d in masks:
            flag = " LOW-CONFIDENCE" if d.low_confidence else ""
            lines.append(
                f"- {d.mask.mask_id}: {d.mask.label}, "
                f"conf {d.mask.confidence:.2f}{flag}, bbox {d.mask.bbox}"
            )
    return "\n".join(lines)


class VisionExtractor:
    """Multimodal fusion over the vision model (+ one Scout fallback)."""

    def __init__(
        self,
        client: MetaClient | None = None,
        settings: Settings | None = None,
    ) -> None:
        self._settings = settings or Settings.from_env()
        self._client = client or MetaClient(settings=self._settings)

    def extract(
        self,
        images: Sequence[bytes],
        masks_by_image: Sequence[Sequence[DecodedMask]],
        note: str = "",
        asset_meta: dict[str, Any] | None = None,
        request_id: str | None = None,
    ) -> VisionObservation:
        """Fuse images + masks + note into a validated VisionObservation."""
        imgs = list(images)
        masks = list(masks_by_image)
        if not 1 <= len(imgs) <= 5:
            raise ValueError(f"need 1-5 images, got {len(imgs)}")
        if len(masks) != len(imgs):
            raise ValueError("masks_by_image must parallel images")
        if not isinstance(note, str):
            raise TypeError("note must be a string")
        if asset_meta is not None and not isinstance(asset_meta, dict):
            raise TypeError("asset_meta must be a dict")

        messages = [
            {"role": "system", "content": VISION_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f"NOTE:\n{note or '(no note provided)'}\n"
                    f"ASSET_META:\n{json.dumps(asset_meta or {})}\n"
                    f"SAM_MASKS:\n{summarize_masks_for_prompt(masks)}\n"
                    "TASK: Fuse the attached images with the SAM masks and note. "
                    "Emit symptoms with evidence pointers (source image_<i> with "
                    "mask_id, or maintenance_note with span [start, end])."
                ),
            },
        ]
        attempts = (
            (self._settings.vision_model_id, False),
            (self._settings.fallback_vision_model_id, True),
        )
        for model_id, fallback_used in attempts:
            try:
                result = self._client.chat(
                    model_id,
                    messages,
                    images=imgs,
                    response_format={
                        "type": "json_schema",
                        "json_schema": VISION_JSON_SCHEMA,
                    },
                    request_id=request_id,
                )
            except _FALLBACK_ERRORS as exc:
                if fallback_used:
                    raise
                logger.warning(
                    "vision_fallback",
                    extra={
                        "request_id": request_id,
                        "primary_model": model_id,
                        "fallback_model": self._settings.fallback_vision_model_id,
                        "error_type": type(exc).__name__,
                    },
                )
                continue
            data = result.data
            if data is None:
                raise MetaResponseError("vision model returned no JSON data")
            try:
                return VisionObservation(
                    asset_type=data.get("asset_type"),
                    condition_tags=data.get("condition_tags", []),
                    symptoms=data.get("symptoms", []),
                    model_id=model_id,
                    fallback_used=fallback_used,
                    usage=result.usage,
                )
            except ValidationError as exc:
                raise MetaResponseError(
                    f"vision model returned invalid observation: {exc}"
                ) from exc
        raise AssertionError("unreachable")  # pragma: no cover
