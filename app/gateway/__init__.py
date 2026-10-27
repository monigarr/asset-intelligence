"""Meta Model API gateway: transport, config, pricing."""

from app.gateway.config import Settings
from app.gateway.errors import (
    MetaAPIError,
    MetaAuthError,
    MetaClientError,
    MetaRateLimitError,
    MetaResponseError,
    MetaServerError,
    MetaTimeoutError,
)
from app.gateway.meta_client import ChatResult, GeneratedImage, MetaClient, Segmentation
from app.gateway.pricing import estimate_chat_cost_cents, estimate_per_image_cost_cents

__all__ = [
    "ChatResult",
    "GeneratedImage",
    "MetaAPIError",
    "MetaAuthError",
    "MetaClient",
    "MetaClientError",
    "MetaRateLimitError",
    "MetaResponseError",
    "MetaServerError",
    "MetaTimeoutError",
    "Segmentation",
    "Settings",
    "estimate_chat_cost_cents",
    "estimate_per_image_cost_cents",
]
