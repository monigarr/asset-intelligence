"""Narrative-clarity judge pilot (Stage 4).

Non-gating by construction: scores are recorded for analysis and never feed
any gate. Meta models only; disabled unless --judge is passed.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any

JUDGE_RUBRIC = """Rate the narrative clarity of infrastructure inspection text 1-5:
5: Crystal clear -- a dispatcher could act without rereading.
4: Clear -- minor awkwardness, meaning unambiguous.
3: Understandable -- requires effort; some vague phrasing.
2: Unclear -- key points ambiguous or buried.
1: Incoherent or empty.
Score writing clarity ONLY, never factual correctness."""

JUDGE_JSON_SCHEMA = {
    "name": "clarity_judgment",
    "schema": {
        "type": "object",
        "properties": {
            "score": {"type": "integer", "minimum": 1, "maximum": 5},
            "rationale": {"type": "string"},
        },
        "required": ["score", "rationale"],
        "additionalProperties": False,
    },
}

JUDGE_SYSTEM = (
    "You rate the narrative clarity of infrastructure inspection text "
    "on the rubric below. Respond with JSON only."
)


def build_judge_messages(texts: Sequence[str]) -> list[dict[str, str]]:
    """Fixed rubric prompt; inspection text capped to keep judge spend bounded."""
    body = "\n---\n".join(t for t in texts if t)[:4000]
    return [
        {"role": "system", "content": JUDGE_SYSTEM + "\n" + JUDGE_RUBRIC},
        {"role": "user", "content": f"Rate this inspection text:\n{body}"},
    ]


def score_from_data(data: Any) -> dict[str, Any]:
    """Validate judge JSON into {score, rationale}. Fail closed on bad shape."""
    if not isinstance(data, dict):
        raise TypeError(f"judge output must be an object, got {type(data).__name__}")
    score = data.get("score")
    rationale = data.get("rationale", "")
    if not isinstance(score, int) or isinstance(score, bool) or not 1 <= score <= 5:
        raise ValueError(f"judge score must be int 1-5, got {score!r}")
    if not isinstance(rationale, str) or not rationale.strip():
        raise ValueError("judge rationale must be non-blank")
    return {"score": score, "rationale": rationale.strip()[:500]}


def score_clarity(
    texts: Sequence[str], chat_fn: Callable[[list[dict[str, str]]], Any]
) -> dict[str, Any]:
    """Score texts via chat_fn (messages -> parsed JSON object)."""
    return score_from_data(chat_fn(build_judge_messages(texts)))
