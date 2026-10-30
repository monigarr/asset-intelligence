"""Cost metering for Meta Model API calls.

GAP (default applied): no pricing table exists in PRD.md / ARCHITECTURE.md.
All built-in prices are 0.0 placeholders and every estimate reports
`priced=False` until real prices are supplied via environment overrides:

    META_PRICE_PER_1K_CENTS_<MODEL>              blended USD cents per 1k tokens
    META_PRICE_PER_1K_CENTS_<MODEL>_INPUT        split: input (non-cached) rate
    META_PRICE_PER_1K_CENTS_<MODEL>_OUTPUT       split: output rate
    META_PRICE_PER_1K_CENTS_<MODEL>_CACHED_INPUT split: cached-input rate
    META_PRICE_PER_IMAGE_CENTS_<MODEL>           USD cents per image
    META_PRICE_PER_IMAGE_CENTS_<MODEL>_IMAGE     alias (same meaning, explicit unit)
    META_PRICE_PER_1_HOUR_<MODEL>_OUTPUT         USD cents per hour (time-metered)

`<MODEL>` is the model id uppercased with non-alphanumerics as `_`, e.g.
`META_PRICE_PER_1K_CENTS_MUSE_SPARK_1_3_INPUT`. Split rates win when both
_INPUT and _OUTPUT are set; otherwise the blended var applies. When
 META_PRICE_TIER is set (e.g. `contributor`), tier-suffixed schedules
 (`<PREFIX>_<TIER>_INPUT`, ...) win when complete, else the base schedule. All overrides
are PLAIN NUMBERS (USD cents) -- no `$` signs or `/1000 ...` suffixes;
anything else raises ValueError.

Meta-published figures (developer console pricing page, observed 2026-10-28,
Standard API mode; re-confirm against the Meta console invoice before quoting
costs). Token units convert as cents/1k = $/1M / 10:

    muse-spark-1.3:  $1.25/M in, $0.15/M cached in, $4.25/M out
    muse-wonder-1.0: $4/M in, $0.20/M cached in, $20/M out
    sam-3.1: $2.50/1000 images ($0.0025/image); video $0.20/1000 frames
        (reserved: this app has no video path yet)
    muse-image-1.0: $0.01/hour -- set the per-image override from measured
        images/hour; muse-voice transcribe $0.18/hour is reserved (unused).
    Contributor-tier Spark: $0.10/M in, $0.002/M cached in, $0.20/M out --
        set META_PRICE_TIER=contributor and put them in
        META_PRICE_PER_1K_CENTS_<MODEL>_CONTRIBUTOR_{INPUT,OUTPUT,CACHED_INPUT}.
    Hourly rates (USD cents/hour, for time-metered models):
        META_PRICE_PER_1_HOUR_<MODEL>_OUTPUT (muse-image-1.0 at $0.01/h
        = 1.0; muse-voice-transcribe at $0.18/h = 18.0, reserved).

See .env.example for the override template.
"""

from __future__ import annotations

import os
import re
from collections.abc import Mapping

# Placeholder table -- every entry is intentionally 0.0 (see module docstring).
_PLACEHOLDER_PER_1K_TOKENS_CENTS: dict[str, float] = {
    "muse-spark-1.3": 0.0,
    "muse-wonder-1.0": 0.0,
}
_PLACEHOLDER_PER_IMAGE_CENTS: dict[str, float] = {
    "sam-3.1": 0.0,
    "muse-image-1.0": 0.0,
}


def _model_env_token(model_id: str) -> str:
    return re.sub(r"[^A-Z0-9]+", "_", model_id.upper()).strip("_")


def _tier_suffix(environ: Mapping[str, str]) -> str:
    """Normalized META_PRICE_TIER suffix ('' when unset)."""
    tier = (environ.get("META_PRICE_TIER") or "").strip()
    return _model_env_token(tier) if tier else ""


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
    prefix = f"META_PRICE_PER_1K_CENTS_{_model_env_token(model_id)}"
    tier = _tier_suffix(env)
    if tier:
        override = _env_price(f"{prefix}_{tier}", env)
        if override is not None:
            return override, True
    override = _env_price(prefix, env)
    if override is not None:
        return override, True
    return _PLACEHOLDER_PER_1K_TOKENS_CENTS.get(model_id, 0.0), False


def price_split_1k_cents(
    model_id: str, environ: Mapping[str, str] | None = None
) -> tuple[float | None, float | None, float | None]:
    """Return (input, output, cached-input) cents per 1k; None when unset.

    A complete META_PRICE_TIER schedule wins; otherwise the base schedule.
    """
    env = os.environ if environ is None else environ
    prefix = f"META_PRICE_PER_1K_CENTS_{_model_env_token(model_id)}"
    tier = _tier_suffix(env)
    if tier:
        tiered = (
            _env_price(f"{prefix}_{tier}_INPUT", env),
            _env_price(f"{prefix}_{tier}_OUTPUT", env),
            _env_price(f"{prefix}_{tier}_CACHED_INPUT", env),
        )
        if tiered[0] is not None and tiered[1] is not None:
            return tiered
    return (
        _env_price(f"{prefix}_INPUT", env),
        _env_price(f"{prefix}_OUTPUT", env),
        _env_price(f"{prefix}_CACHED_INPUT", env),
    )


def price_per_image_cents(
    model_id: str, environ: Mapping[str, str] | None = None
) -> tuple[float, bool]:
    """Return (cents per image, priced). `priced` is False on placeholder.

    Accepts the canonical ``META_PRICE_PER_IMAGE_CENTS_<MODEL>`` var and the
    ``..._<MODEL>_IMAGE`` alias (same value, explicit unit)."""
    env = os.environ if environ is None else environ
    base = f"META_PRICE_PER_IMAGE_CENTS_{_model_env_token(model_id)}"
    override = _env_price(base, env)
    if override is None:
        override = _env_price(f"{base}_IMAGE", env)
    if override is not None:
        return override, True
    return _PLACEHOLDER_PER_IMAGE_CENTS.get(model_id, 0.0), False


def estimate_chat_cost_cents(
    model_id: str,
    prompt_tokens: int,
    completion_tokens: int,
    environ: Mapping[str, str] | None = None,
    *,
    cached_tokens: int = 0,
) -> tuple[float, bool]:
    """Estimate chat/vision call cost. Returns (cents, priced).

    Split input/output rates win when both are set; otherwise falls back to
    the blended per-model rate. `cached_tokens` (a subset of prompt_tokens)
    is priced at the cached-input rate when set, else the input rate.
    """
    env = os.environ if environ is None else environ
    per_in, per_out, per_cached = price_split_1k_cents(model_id, env)
    if per_in is not None and per_out is not None:
        prompt = max(prompt_tokens, 0)
        cached = min(max(cached_tokens, 0), prompt)
        completion = max(completion_tokens, 0)
        cached_rate = per_cached if per_cached is not None else per_in
        cents = (prompt - cached) / 1000 * per_in
        cents += cached / 1000 * cached_rate + completion / 1000 * per_out
        return round(cents, 4), True
    per_1k, priced = price_per_1k_tokens_cents(model_id, env)
    total_tokens = max(prompt_tokens, 0) + max(completion_tokens, 0)
    return round(total_tokens / 1000 * per_1k, 4), priced


def estimate_per_image_cost_cents(
    model_id: str, environ: Mapping[str, str] | None = None
) -> tuple[float, bool]:
    """Estimate one segmentation/generation call cost. Returns (cents, priced)."""
    return price_per_image_cents(model_id, environ)


def price_per_hour_cents(
    model_id: str, environ: Mapping[str, str] | None = None
) -> tuple[float, bool]:
    """Return (USD cents per hour, priced) for time-metered models."""
    env = os.environ if environ is None else environ
    var = f"META_PRICE_PER_1_HOUR_{_model_env_token(model_id)}_OUTPUT"
    override = _env_price(var, env)
    if override is not None:
        return override, True
    return 0.0, False


def estimate_hourly_cost_cents(
    model_id: str,
    seconds: float,
    environ: Mapping[str, str] | None = None,
) -> tuple[float, bool]:
    """Estimate a time-metered call cost. Returns (cents, priced)."""
    per_hour, priced = price_per_hour_cents(model_id, environ)
    if not priced:
        return 0.0, False
    return round(max(seconds, 0.0) / 3600 * per_hour, 4), True
