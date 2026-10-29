"""Fail-closed inspection validation (Day 5) — the production gate.

`validate_inspection()` enforces the PRD §6 output contract:
  1. Structural: required fields, evidence non-empty, uncertainty range,
     human_review_required=true (pydantic, field-level errors).
  2. Evidence integrity: image evidence cites a mask_id that exists on that
     image; note evidence cites an in-bounds span; no mixed refs.
  3. Measurement honesty (ARCHITECTURE.md §4.7): model text mentioning a
     dimension is accepted only when the field note — the sole source of
     scale — contains a measurement reference (a digit). Observations
     additionally need a maintenance_note evidence ref tying them to it.
  4. Certification guard (PRD §14): certifying/approving language in any
     model text is rejected. The prompt forbids it; this rejects it anyway.
  5. Missing-info keys are snake_case (matches the Wonder/Spark contract).

All failures raise pydantic ValidationError, which FastAPI maps to 422
with field-level errors (Day-7 API). Never coerces, never partial-accepts.

Cross-checks need validation context: `note` (span bounds, measurement
reference) and `image_count` (source validity). Use `validate_inspection()`,
which always supplies both.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any, Literal

from pydantic import BaseModel, Field, ValidationInfo, field_validator, model_validator

from app.gateway import Segmentation

_MISSING_KEY_RE = re.compile(r"^[a-z0-9_]+$")
_DIMENSION_RE = re.compile(
    r"\d+(?:\.\d+)?\s*(?:mm|cm|m\b|meters?|feet|foot|ft|in\b|inch(?:es)?)",
    re.IGNORECASE,
)
_DIGIT_RE = re.compile(r"\d")
# Entries [0:_CERT_ACTION_COUNT] are action-anchored certif* patterns: the bare
# noun ("certification paperwork") never matches, and refusal phrasing
# ("do not certify") is exempt via _REFUSAL_BEFORE_RE. Only performed or
# claimed certification is blocked.
_CERT_ACTION_COUNT = 2
_REFUSAL_BEFORE_RE = re.compile(
    r"\b(do not|don't|cannot|can't|won't|will not|never"
    r"|refus\w*|decline[sd]?|unable to)\b",
    re.IGNORECASE,
)


def _cert_action_hit(text: str, pattern: re.Pattern[str]) -> str | None:
    """Match unless refusal phrasing precedes it within 40 chars."""
    match = pattern.search(text)
    if not match:
        return None
    window = text[max(0, match.start() - 40) : match.start()]
    if _REFUSAL_BEFORE_RE.search(window):
        return None
    return match.group()


_CERT_PATTERNS = (
    re.compile(
        r"\b(issue[sd]?|grant(?:s|ed|ing)?|sign(?:s|ed|ing)?"
        r"|approv(?:e[sd]?|ing|al))\b.{0,40}\bcertificat",
        re.IGNORECASE,
    ),
    re.compile(r"\bcertif(y|ies|ied|ying)\b", re.IGNORECASE),
    re.compile(r"\bcompliant\b", re.IGNORECASE),
    re.compile(r"safe to (use|operate|open|occupy)", re.IGNORECASE),
    re.compile(r"declare[sd]? .{0,30}safe\b", re.IGNORECASE),
    re.compile(r"structurally sound", re.IGNORECASE),
    re.compile(r"no (further )?action (needed|required)", re.IGNORECASE),
)


class EvidenceRef(BaseModel):
    source: str  # image_<i> or maintenance_note
    mask_id: str | None = None
    span: list[int] | None = Field(default=None, min_length=2, max_length=2)


class Observation(BaseModel):
    text: str
    evidence: list[EvidenceRef] = Field(min_length=1)
    uncertainty: float = Field(ge=0.0, le=1.0)  # always required (ARCH §4.7: min when low-conf)

    @field_validator("text")
    @classmethod
    def _text_nonblank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("observation text must be non-blank")
        return value


class ModelTrace(BaseModel):
    sam: str
    vision: str
    vision_fallback_used: bool = False
    reasoning: str
    planning: str
    timestamp: str


class UsageSummary(BaseModel):
    """Aggregate token usage across vision + reasoning + planning calls."""

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class InspectionResult(BaseModel):
    request_id: str
    asset_id: str
    asset_type: str | None = None
    segmentations: list[Segmentation] = []
    observations: list[Observation] = []
    discrepancies: list[str] = []
    missing_information: list[str] = []
    recommended_next_step: str = Field(min_length=1)
    human_review_required: Literal[True] = True
    model_trace: ModelTrace
    cost_cents: float = 0.0
    cost_priced: bool = False
    durations_ms: dict[str, float] = {}
    usage: UsageSummary = Field(default_factory=UsageSummary)

    @field_validator("recommended_next_step")
    @classmethod
    def _next_step_nonblank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("recommended_next_step must be non-blank")
        return value

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

    @model_validator(mode="after")
    def _check_evidence_refs(self, info: ValidationInfo) -> InspectionResult:
        note = _context(info, "note")
        image_count = _context(info, "image_count")
        mask_ids = {m.mask_id for m in self.segmentations}
        mask_sources = {(m.mask_id, m.source_image) for m in self.segmentations}
        errors = []
        for oi, ob in enumerate(self.observations):
            for ei, ev in enumerate(ob.evidence):
                loc = f"observations[{oi}].evidence[{ei}]"
                if ev.source == "maintenance_note":
                    if ev.mask_id is not None:
                        errors.append(f"{loc}: note evidence must not carry mask_id")
                    if ev.span is None:
                        errors.append(f"{loc}: note evidence needs span [start, end]")
                    else:
                        start, end = ev.span
                        if not (0 <= start < end <= len(note)):
                            errors.append(
                                f"{loc}: span {ev.span} out of bounds "
                                f"for note length {len(note)}"
                            )
                elif ev.source.startswith("image_"):
                    idx = ev.source[len("image_") :]
                    if not idx.isdigit() or not 0 <= int(idx) < image_count:
                        errors.append(f"{loc}: unknown source {ev.source!r}")
                        continue
                    if ev.span is not None:
                        errors.append(f"{loc}: image evidence must not carry span")
                    if ev.mask_id is None:
                        errors.append(f"{loc}: image evidence needs mask_id")
                    elif ev.mask_id not in mask_ids:
                        errors.append(f"{loc}: unknown mask_id {ev.mask_id!r}")
                    elif (ev.mask_id, ev.source) not in mask_sources:
                        errors.append(
                            f"{loc}: mask {ev.mask_id!r} is not from {ev.source}"
                        )
                else:
                    errors.append(
                        f"{loc}: source must be image_<i> or maintenance_note, "
                        f"got {ev.source!r}"
                    )
        if errors:
            raise ValueError("; ".join(errors))
        return self

    @model_validator(mode="after")
    def _check_measurements(self, info: ValidationInfo) -> InspectionResult:
        note = _context(info, "note")
        note_has_number = bool(_DIGIT_RE.search(note))
        errors = []
        for oi, ob in enumerate(self.observations):
            if _DIMENSION_RE.search(ob.text):
                has_note_ref = any(
                    ev.source == "maintenance_note" for ev in ob.evidence
                )
                if not has_note_ref:
                    errors.append(
                        f"observations[{oi}]: dimension mentioned but no "
                        "maintenance_note evidence"
                    )
                elif not note_has_number:
                    errors.append(
                        f"observations[{oi}]: dimension mentioned but note has "
                        "no measurement reference"
                    )
        for di, text in enumerate(self.discrepancies):
            if _DIMENSION_RE.search(text) and not note_has_number:
                errors.append(
                    f"discrepancies[{di}]: dimension mentioned but note has "
                    "no measurement reference"
                )
        if _DIMENSION_RE.search(self.recommended_next_step) and not note_has_number:
            errors.append(
                "recommended_next_step: dimension mentioned but note has "
                "no measurement reference"
            )
        if errors:
            raise ValueError("; ".join(errors))
        return self

    @model_validator(mode="after")
    def _check_certification(self) -> InspectionResult:
        texts: list[tuple[str, str]] = [
            (f"observations[{i}]", ob.text) for i, ob in enumerate(self.observations)
        ]
        texts += [(f"discrepancies[{i}]", d) for i, d in enumerate(self.discrepancies)]
        texts.append(("recommended_next_step", self.recommended_next_step))
        errors = []
        for loc, text in texts:
            for i, pattern in enumerate(_CERT_PATTERNS):
                if i < _CERT_ACTION_COUNT:
                    hit = _cert_action_hit(text, pattern)
                else:
                    match = pattern.search(text)
                    hit = match.group() if match else None
                if hit:
                    errors.append(f"{loc}: certifying language {hit!r}")
        if errors:
            raise ValueError("; ".join(errors))
        return self


def _context(info: ValidationInfo, name: str) -> Any:
    ctx = info.context or {}
    if name not in ctx:
        raise ValueError(f"validator context missing {name!r} (use validate_inspection)")
    return ctx[name]


def validate_inspection(
    payload: Mapping[str, Any], *, note: str, image_count: int
) -> InspectionResult:
    """Validate a full inspection payload. Raises ValidationError (→ 422)."""
    return InspectionResult.model_validate(
        payload, context={"note": note, "image_count": image_count}
    )
