"""Cost metering for Meta Model API calls.

GAP (default applied): no pricing table exists in PRD.md / ARCHITECTURE.md.
All built-in prices are 0.0 placeholders and every estimate reports
`priced=False` until real prices are supplied via environment overrides:

    META_PRICE_PER_1K_CENTS_<MODEL>      chat/vision, USD cents per 1k tokens
    META_PRICE_PER_IMAGE_CENTS_<MODEL>   SAM segmentation / image generation

`<MODEL>` is the model id uppercased with non-alphanumerics as `_`, e.g.
`META_PRICE_PER_1K_CENTS_MUSE_SPARK_1_3`. Override the placeholders with real
hackathon-credit pricing before quoting cost_cents to judges.
"""

from __future__ import annotations

import os
import re
from collections.abc import Mapping

# Placeholder table — every entry is intentionally 0.0 (see module docstring).
_PLACEHOLDER_PER_1K_TOKENS_CENTS: dict[str, float] = {
    "llama-4-maverick-17b-128e-vision": 0.0,
    "llama-4-scout-17b-16e-vision": 0.0,
    "muse-spark-1.3": 0.0,
    "muse-wonder": 0.0,
}
_PLACEHOLDER_PER_IMAGE_CENTS: dict[str, float] = {
    "sam-3.1": 0.0,
    "muse-image": 0.0,
}


def _model_env_token(model_id: str) -> str:
    return re.sub(r"[^A-Z0-9]+", "_", model_id.upper()).strip("_")


def _env_price(var: str, environ: Mapping[str, str]) -> float | None:
    raw = (environ.get(var) or "").strip()
    if not raw:
        return None
    try:
        return float(raw)
    except ValueError as exc:
        raise ValueError(f"{var} must be a number, got {raw!r}") from exc


def price_per_1k_tokens_cents(
    model_id: str, environ: Mapping[str, str] | None = None
) -> tuple[float, bool]:
    """Return (cents per 1k tokens, priced). `priced` is False on placeholder."""
    env = os.environ if environ is None else environ
    override = _env_price(f"META_PRICE_PER_1K_CENTS_{_model_env_token(model_id)}", env)
    if override is not None:
        return override, True
    return _PLACEHOLDER_PER_1K_TOKENS_CENTS.get(model_id, 0.0), False


def price_per_image_cents(
    model_id: str, environ: Mapping[str, str] | None = None
) -> tuple[float, bool]:
    """Return (cents per image, priced). `priced` is False on placeholder."""
    env = os.environ if environ is None else environ
    override = _env_price(f"META_PRICE_PER_IMAGE_CENTS_{_model_env_token(model_id)}", env)
    if override is not None:
        return override, True
    return _PLACEHOLDER_PER_IMAGE_CENTS.get(model_id, 0.0), False


def estimate_chat_cost_cents(
    model_id: str,
    prompt_tokens: int,
    completion_tokens: int,
    environ: Mapping[str, str] | None = None,
) -> tuple[float, bool]:
    """Estimate chat/vision call cost. Returns (cents, priced)."""
    per_1k, priced = price_per_1k_tokens_cents(model_id, environ)
    total_tokens = max(prompt_tokens, 0) + max(completion_tokens, 0)
    return round(total_tokens / 1000 * per_1k, 4), priced


def estimate_per_image_cost_cents(
    model_id: str, environ: Mapping[str, str] | None = None
) -> tuple[float, bool]:
    """Estimate one segmentation/generation call cost. Returns (cents, priced)."""
    return price_per_image_cents(model_id, environ)
