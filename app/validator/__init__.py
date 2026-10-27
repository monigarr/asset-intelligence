"""Fail-closed inspection validation."""

from app.validator.schema import (
    EvidenceRef,
    InspectionResult,
    ModelTrace,
    Observation,
    validate_inspection,
)

__all__ = [
    "EvidenceRef",
    "InspectionResult",
    "ModelTrace",
    "Observation",
    "validate_inspection",
]
