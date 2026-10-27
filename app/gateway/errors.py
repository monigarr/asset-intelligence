"""Typed gateway errors.

Split into its own module so config, client, and (later) pipeline layers can
share them without import cycles. Only rate-limit, server, and timeout errors
are retried; everything else fails fast.
"""

from __future__ import annotations


class MetaAPIError(Exception):
    """Base class for all Meta Model API gateway failures."""


class MetaAuthError(MetaAPIError):
    """Missing/invalid API key (startup) or 401/403 from the API. Never retried."""


class MetaRateLimitError(MetaAPIError):
    """HTTP 429. Retried; honors the Retry-After hint when present."""

    def __init__(self, message: str, retry_after_s: float | None = None) -> None:
        super().__init__(message)
        self.retry_after_s = retry_after_s


class MetaServerError(MetaAPIError):
    """HTTP 5xx or transport failure. Retried with backoff."""


class MetaTimeoutError(MetaAPIError):
    """Request exceeded the configured timeout. Retried with backoff."""


class MetaClientError(MetaAPIError):
    """Non-retriable 4xx (bad request, unknown model, etc.)."""


class MetaResponseError(MetaAPIError):
    """API answered but the payload is not usable JSON of the expected shape."""
