"""Validator tests: structural, evidence, measurement, certification rules."""

from __future__ import annotations

from typing import Any

import pytest
from pydantic import ValidationError

from app.validator import InspectionResult, validate_inspection

NOTE = "Crack near top edge, seepage observed"
NOTE_WITH_MEASURE = "Crack near top edge, about 2ft long, seepage observed"


def _payload(**over: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "request_id": "req_1",
        "asset_id": "A-1",
        "asset_type": "drainage_structure",
        "model_trace": {
            "sam": "sam-3.1",
            "vision": "muse-spark-1.3",
            "reasoning": "muse-spark-1.3",
            "planning": "muse-wonder-1.0",
            "timestamp": "2026-10-26T00:00:00+00:00",
        },
        "segmentations": [
            {
                "mask_id": "mask_1",
                "label": "crack",
                "bbox": [1, 1, 5, 5],
                "confidence": 0.9,
                "source_image": "image_0",
            }
        ],
        "observations": [
            {
                "text": "crack visible",
                "evidence": [
                    {"source": "image_0", "mask_id": "mask_1"},
                    {"source": "maintenance_note", "span": [0, 5]},
                ],
                "uncertainty": 0.3,
            }
        ],
        "discrepancies": [],
        "missing_information": ["crack_dimensions"],
        "recommended_next_step": "Request qualified inspection with measurement.",
        "human_review_required": True,
        "cost_cents": 11.0,
        "cost_priced": False,
    }
    base.update(over)
    return base


def _obs(text: str, evidence: list[dict[str, Any]]) -> dict[str, Any]:
    return {"text": text, "evidence": evidence, "uncertainty": 0.3}


# -- happy path + structural --------------------------------------------


def test_valid_payload_passes() -> None:
    out = validate_inspection(_payload(), note=NOTE, image_count=1)
    assert out.asset_id == "A-1"
    assert out.human_review_required is True


def test_structural_failures() -> None:
    cases = [
        ({"asset_id": None}, "asset_id"),  # required (None rejected)
        ({"human_review_required": False}, "human_review_required"),
        ({"observations": [_obs("x", [])]}, "evidence"),  # min 1
    ]
    for over, match in cases:
        with pytest.raises(ValidationError, match=match):
            validate_inspection(_payload(**over), note=NOTE, image_count=1)
    bad_uncertainty = _obs("x", [{"source": "image_0", "mask_id": "mask_1"}])
    bad_uncertainty["uncertainty"] = 2.0
    with pytest.raises(ValidationError, match="uncertainty"):
        validate_inspection(_payload(observations=[bad_uncertainty]), note=NOTE, image_count=1)
    with pytest.raises(ValidationError, match="validator context"):
        InspectionResult.model_validate(_payload())  # no context at all
    with pytest.raises(ValidationError):
        validate_inspection("not-a-dict", note=NOTE, image_count=1)  # type: ignore[arg-type]


# -- evidence integrity -------------------------------------------------


def test_evidence_source_rules() -> None:
    def check(evidence: list[dict[str, Any]], match: str) -> None:
        with pytest.raises(ValidationError, match=match):
            validate_inspection(
                _payload(observations=[_obs("x", evidence)]), note=NOTE, image_count=1
            )

    check([{"source": "image_5", "mask_id": "mask_1"}], "unknown source")
    check([{"source": "photo_0", "mask_id": "mask_1"}], "image_<i> or maintenance_note")
    check([{"source": "image_0"}], "needs mask_id")
    check([{"source": "image_0", "mask_id": "mask_1", "span": [0, 1]}], "must not carry span")
    check([{"source": "image_0", "mask_id": "mask_9"}], "unknown mask_id")
    check([{"source": "maintenance_note"}], "needs span")
    check(
        [{"source": "maintenance_note", "mask_id": "mask_1", "span": [0, 1]}],
        "must not carry mask_id",
    )
    check([{"source": "maintenance_note", "span": [0, 9999]}], "out of bounds")
    check([{"source": "maintenance_note", "span": [5, 5]}], "out of bounds")


def test_mask_must_come_from_cited_image() -> None:
    payload = _payload(
        segmentations=[
            {
                "mask_id": "mask_1",
                "label": "crack",
                "bbox": [1, 1, 5, 5],
                "confidence": 0.9,
                "source_image": "image_1",
            }
        ],
        observations=[
            _obs("x", [{"source": "image_0", "mask_id": "mask_1"}]),
        ],
    )
    with pytest.raises(ValidationError, match="is not from image_0"):
        validate_inspection(payload, note=NOTE, image_count=2)


# -- measurement honesty ------------------------------------------------


def test_measurement_rule() -> None:
    dim_obs = _obs("crack about 2ft long", [{"source": "image_0", "mask_id": "mask_1"}])
    # image-only evidence: rejected even when the note has numbers
    with pytest.raises(ValidationError, match="no maintenance_note evidence"):
        validate_inspection(
            _payload(observations=[dim_obs]), note=NOTE_WITH_MEASURE, image_count=1
        )
    # note evidence but numberless note: rejected
    dim_obs_noted = _obs(
        "crack about 2ft long",
        [
            {"source": "image_0", "mask_id": "mask_1"},
            {"source": "maintenance_note", "span": [0, 5]},
        ],
    )
    with pytest.raises(ValidationError, match="no measurement reference"):
        validate_inspection(_payload(observations=[dim_obs_noted]), note=NOTE, image_count=1)
    # note evidence + numbered note: accepted
    out = validate_inspection(
        _payload(observations=[dim_obs_noted]), note=NOTE_WITH_MEASURE, image_count=1
    )
    assert out.observations[0].text.startswith("crack about 2ft")
    # discrepancies / next step follow the same note-number rule
    with pytest.raises(ValidationError, match="no measurement reference"):
        validate_inspection(
            _payload(discrepancies=["note says 2ft but no scale visible"]),
            note=NOTE,
            image_count=1,
        )
    ok = validate_inspection(
        _payload(discrepancies=["note says 2ft but no scale visible"]),
        note=NOTE_WITH_MEASURE,
        image_count=1,
    )
    assert ok.discrepancies[0].startswith("note says 2ft")
    with pytest.raises(ValidationError, match="no measurement reference"):
        validate_inspection(
            _payload(recommended_next_step="Measure the 3 cm crack."),
            note=NOTE,
            image_count=1,
        )
    # control: ids and unitless numbers are not dimensions
    control = validate_inspection(
        _payload(
            observations=[
                _obs(
                    "mask_1 shows 2 regions of distress",
                    [{"source": "image_0", "mask_id": "mask_1"}],
                )
            ]
        ),
        note=NOTE,
        image_count=1,
    )
    assert control.observations[0].text.startswith("mask_1")


# -- certification guard ------------------------------------------------


@pytest.mark.parametrize(
    "text",
    [
        "I certify this culvert as safe.",
        "The structure is certified for continued use.",
        "The asset is compliant with code.",
        "It is safe to operate the culvert.",
        "We declare the bridge safe for traffic.",
        "The wall is structurally sound.",
        "No further action needed.",
        "No action required at this time.",
    ],
)
def test_certifying_language_rejected(text: str) -> None:
    with pytest.raises(ValidationError, match="certifying language"):
        validate_inspection(
            _payload(recommended_next_step=text), note=NOTE, image_count=1
        )
    with pytest.raises(ValidationError, match="certifying language"):
        validate_inspection(
            _payload(observations=[_obs(text, [{"source": "image_0", "mask_id": "mask_1"}])]),
            note=NOTE,
            image_count=1,
        )


@pytest.mark.parametrize(
    "text",
    [
        "Request qualified inspection with measurement tape.",
        "Schedule a follow-up safety inspection after rain.",
        "Re-photograph with a scale reference; do not certify anything yet.",
    ],
)
def test_non_certifying_language_passes(text: str) -> None:
    # NOTE: the third case mentions "certify" inside a refusal instruction —
    # the guard is intentionally literal and rejects any certif* mention.
    if "certify" in text:
        with pytest.raises(ValidationError, match="certifying language"):
            validate_inspection(
                _payload(recommended_next_step=text), note=NOTE, image_count=1
            )
    else:
        out = validate_inspection(
            _payload(recommended_next_step=text), note=NOTE, image_count=1
        )
        assert out.recommended_next_step == text


# -- shape details ------------------------------------------------------


def test_shape_details() -> None:
    with pytest.raises(ValidationError, match="snake_case"):
        validate_inspection(
            _payload(missing_information=["Crack Size"]), note=NOTE, image_count=1
        )
    with pytest.raises(ValidationError, match="non-empty strings"):
        validate_inspection(
            _payload(discrepancies=["  "]), note=NOTE, image_count=1
        )
    with pytest.raises(ValidationError, match="non-blank"):
        validate_inspection(
            _payload(recommended_next_step="  "), note=NOTE, image_count=1
        )
    with pytest.raises(ValidationError, match="non-blank"):
        validate_inspection(
            _payload(
                observations=[
                    _obs("  ", [{"source": "image_0", "mask_id": "mask_1"}])
                ]
            ),
            note=NOTE,
            image_count=1,
        )
