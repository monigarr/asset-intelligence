"""Gateway configuration loaded from the environment (12-factor).

Keys mirror `.env.example`. Local development populates `os.environ` from
`.env` via `load_dotenv()`; production sets real environment variables.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass

from dotenv import load_dotenv

from app.gateway.errors import MetaAuthError

DEFAULT_BASE_URL = "https://api.meta.ai/v1"


def _as_float(raw: str, var: str) -> float:
    try:
        return float(raw)
    except ValueError as exc:
        raise ValueError(f"{var} must be a number, got {raw!r}") from exc


def _as_int(raw: str, var: str) -> int:
    try:
        return int(raw)
    except ValueError as exc:
        raise ValueError(f"{var} must be an integer, got {raw!r}") from exc


@dataclass(frozen=True)
class Settings:
    """Immutable gateway settings. Use `Settings.from_env()` in production."""

    api_key: str
    base_url: str = DEFAULT_BASE_URL
    timeout_s: float = 15.0
    max_retries: int = 2
    sam_model_id: str = "sam-3.1"
    # Live-verified 2026-10-27: the Meta Model API serves no Llama vision
    # models (GET /v1/models: 9 entries, none Llama). Vision uses the
    # API-native multimodal reader instead — a deliberate deviation from
    # ARCHITECTURE.md §4.3. Fallback intentionally (open-weights deferred, ARCH v1.1)
    # equals primary: no cheaper multimodal model exists on this API.
    vision_model_id: str = "muse-spark-1.3"
    fallback_vision_model_id: str = "muse-spark-1.3"
    reasoning_model_id: str = "muse-spark-1.3"
    planning_model_id: str = "muse-wonder-1.0"
    image_model_id: str = "muse-image-1.0"

    @classmethod
    def from_env(cls, environ: Mapping[str, str] | None = None) -> Settings:
        """Build settings from the environment. `environ` override is for tests."""
        load_dotenv()  # no-op when no .env file exists
        env: Mapping[str, str] = os.environ if environ is None else environ

        key = (env.get("META_API_KEY") or "").strip()
        if not key or "REPLACE_ME" in key:
            raise MetaAuthError(
                "META_API_KEY not configured — copy .env.example to .env "
                "and add your key (see README.md)."
            )

        timeout_s = _as_float(env.get("META_API_TIMEOUT_S", "15"), "META_API_TIMEOUT_S")
        if timeout_s <= 0:
            raise ValueError("META_API_TIMEOUT_S must be positive")
        max_retries = _as_int(env.get("META_API_MAX_RETRIES", "2"), "META_API_MAX_RETRIES")
        if max_retries < 0:
            raise ValueError("META_API_MAX_RETRIES must be >= 0")

        return cls(
            api_key=key,
            base_url=(env.get("META_API_BASE_URL") or DEFAULT_BASE_URL).rstrip("/"),
            timeout_s=timeout_s,
            max_retries=max_retries,
            sam_model_id=env.get("SAM_MODEL_ID", cls.sam_model_id),
            vision_model_id=env.get("VISION_MODEL_ID", cls.vision_model_id),
            fallback_vision_model_id=env.get(
                "FALLBACK_VISION_MODEL_ID", cls.fallback_vision_model_id
            ),
            reasoning_model_id=env.get("REASONING_MODEL_ID", cls.reasoning_model_id),
            planning_model_id=env.get("PLANNING_MODEL_ID", cls.planning_model_id),
            image_model_id=env.get("IMAGE_MODEL_ID", cls.image_model_id),
        )
