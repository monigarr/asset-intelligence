"""Meta Model API gateway client.

Transport contract (ASSUMPTION — GAP: PRD.md / ARCHITECTURE.md do not pin the
HTTP wire format):
  - OpenAI-compatible REST rooted at ``META_API_BASE_URL`` (default
    ``https://api.meta.ai/v1``): ``POST /chat/completions``,
    ``POST /images/generations``, ``POST /segment``.
  - Auth via ``Authorization: Bearer <META_API_KEY>``.
  - Usage reported as ``{"prompt_tokens", "completion_tokens",
    "total_tokens"}``.
Day-2 live-key check MUST verify: auth scheme, endpoint paths, usage field
names. Only this module's paths/payload builders should need to change.

Retry policy: max_retries=2 (3 attempts). CONFLICT resolved per AGENTS.md §2
priority — ARCHITECTURE.md §4.4 ("bounded retry (2)") and §11 ("max 2
retries") win over AGENT_BUILD_GUIDE.md's `stop_after_attempt(2)` snippet
(which would allow only 1 retry).

Every logical call emits exactly one ``meta_api_call`` log record with
request_id, model_id, latency, token usage, and metered cost. Key material
is never logged.
"""

from __future__ import annotations

import base64
import binascii
import json
import logging
import time
from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from typing import Any, Self
from uuid import uuid4

import httpx
from pydantic import BaseModel, Field, ValidationError
from tenacity import RetryCallState, Retrying, retry_if_exception, stop_after_attempt
from tenacity import wait_exponential as _wait_exponential

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
from app.gateway.pricing import estimate_chat_cost_cents, estimate_per_image_cost_cents

logger = logging.getLogger("asset_intel.gateway")

WaitPolicy = Callable[[RetryCallState], float]

_RETRIABLE_ERRORS = (MetaRateLimitError, MetaServerError, MetaTimeoutError)
_RETRY_AFTER_CAP_S = 60.0


# ---------------------------------------------------------------------------
# Response models — fail-fast boundary validation of API payloads
# ---------------------------------------------------------------------------


class Segmentation(BaseModel):
    """One SAM defect mask. RLE is a COCO dict or (future) string encoding."""

    mask_id: str
    label: str
    bbox: list[int] = Field(min_length=4, max_length=4)
    confidence: float = Field(ge=0.0, le=1.0)
    rle: str | dict[str, Any] | None = None
    source_image: str | None = None


class ChatUsage(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class ChatResult(BaseModel):
    text: str
    data: dict[str, Any] | None = None  # parsed JSON when response_format given
    usage: ChatUsage = ChatUsage()
    model_id: str
    raw: dict[str, Any]  # full payload, kept for traceability


class GeneratedImage(BaseModel):
    image_bytes: bytes
    mime_type: str
    model_id: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def parse_retry_after(value: str | None) -> float | None:
    """Parse a Retry-After header (delay seconds or HTTP date) to seconds.

    Returns None when absent/unparseable; clamps past dates to 0.0.
    """
    if not value or not value.strip():
        return None
    text = value.strip()
    try:
        return max(float(text), 0.0)
    except ValueError:
        pass
    try:
        moment = parsedate_to_datetime(text)
    except (ValueError, TypeError):
        return None
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=UTC)
    return max((moment - datetime.now(UTC)).total_seconds(), 0.0)


def _mime_for_bytes(data: bytes) -> str:
    if data[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    # Gateway is transport only; the Day-7 InputAdapter validates/sanitizes.
    return "application/octet-stream"


def _new_request_id() -> str:
    # Interim format; the Day-4 orchestrator owns canonical request ids.
    return f"req_{uuid4().hex[:24]}"


def _ms_since(started: float) -> float:
    return round((time.monotonic() - started) * 1000, 1)


def _is_retriable(exc: BaseException) -> bool:
    return isinstance(exc, _RETRIABLE_ERRORS)


def _default_wait(retry_state: RetryCallState) -> float:
    outcome = retry_state.outcome
    exc = outcome.exception() if outcome is not None and outcome.failed else None
    if isinstance(exc, MetaRateLimitError) and exc.retry_after_s is not None:
        return min(max(exc.retry_after_s, 0.0), _RETRY_AFTER_CAP_S)
    return _wait_exponential(multiplier=1, min=1, max=4)(retry_state)


def _with_images(
    messages: Sequence[dict[str, Any]], images: Sequence[bytes]
) -> list[dict[str, Any]]:
    """Attach images as data-URL parts to the last user message (OpenAI style)."""
    if not images:
        return list(messages)
    out = [dict(m) for m in messages]
    parts: list[dict[str, Any]] = [
        {
            "type": "image_url",
            "image_url": {
                "url": f"data:{_mime_for_bytes(b)};base64,"
                f"{base64.b64encode(b).decode('ascii')}"
            },
        }
        for b in images
    ]
    for message in reversed(out):
        if message.get("role") == "user":
            content = message.get("content", "")
            text = content if isinstance(content, str) else ""
            message["content"] = [{"type": "text", "text": text}, *parts]
            return out
    out.append({"role": "user", "content": parts})
    return out


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------


class MetaClient:
    """Thin typed wrapper over the Meta Model API.

    Args:
        settings: Gateway settings; defaults to `Settings.from_env()`.
        transport: Optional httpx transport (tests inject `MockTransport`).
        retry_wait: Optional tenacity wait policy override (tests inject
            zero-sleep). Defaults to Retry-After-aware exponential backoff.
    """

    def __init__(
        self,
        settings: Settings | None = None,
        transport: httpx.BaseTransport | None = None,
        retry_wait: WaitPolicy | None = None,
    ) -> None:
        self._settings = settings or Settings.from_env()
        self._wait = retry_wait or _default_wait
        self._http = httpx.Client(
            base_url=self._settings.base_url,
            timeout=self._settings.timeout_s,
            transport=transport,
            headers={"Authorization": f"Bearer {self._settings.api_key}"},
        )

    def close(self) -> None:
        self._http.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()

    # -- public API ------------------------------------------------------

    def segment(
        self,
        model_id: str,
        image_bytes: bytes,
        text_prompts: Sequence[str],
        *,
        source_image: str = "image_0",
        request_id: str | None = None,
    ) -> list[Segmentation]:
        """Zero-shot defect segmentation (SAM). Returns validated masks."""
        rid = request_id or _new_request_id()
        payload = {
            "model": model_id,
            "image": base64.b64encode(image_bytes).decode("ascii"),
            "image_mime": _mime_for_bytes(image_bytes),
            "text_prompts": list(text_prompts),
            "source_image": source_image,
        }

        def parse(response: httpx.Response) -> tuple[list[Segmentation], dict[str, Any]]:
            data = _as_json("segment", response)
            try:
                masks = [Segmentation(**m) for m in data["masks"]]
            except (KeyError, TypeError, ValidationError) as exc:
                raise MetaResponseError(f"segment returned invalid masks: {exc}") from exc
            cost_cents, priced = estimate_per_image_cost_cents(model_id)
            return masks, {
                "mask_count": len(masks),
                "cost_cents": cost_cents,
                "cost_priced": priced,
            }

        return self._post(
            operation="segment",
            model_id=model_id,
            path="/segment",
            payload=payload,
            request_id=rid,
            parse=parse,
        )

    def chat(
        self,
        model_id: str,
        messages: Sequence[dict[str, Any]],
        *,
        images: Sequence[bytes] | None = None,
        response_format: dict[str, Any] | None = None,
        extra: dict[str, Any] | None = None,
        request_id: str | None = None,
    ) -> ChatResult:
        """Chat/vision completion. With `response_format`, content must be a JSON object."""
        rid = request_id or _new_request_id()
        payload: dict[str, Any] = {
            "model": model_id,
            "messages": _with_images(messages, images or []),
        }
        if response_format is not None:
            payload["response_format"] = response_format
        if extra:
            payload.update(extra)

        def parse(response: httpx.Response) -> tuple[ChatResult, dict[str, Any]]:
            data = _as_json("chat", response)
            try:
                content = data["choices"][0]["message"].get("content") or ""
                text = content if isinstance(content, str) else ""
                parsed: dict[str, Any] | None = None
                if response_format is not None:
                    decoded = json.loads(text)
                    if not isinstance(decoded, dict):
                        raise MetaResponseError(
                            "chat response_format requested a JSON object but "
                            f"got {type(decoded).__name__}"
                        )
                    parsed = decoded
                usage = ChatUsage(**data.get("usage", {}))
            except (KeyError, IndexError, TypeError, ValidationError) as exc:
                raise MetaResponseError(f"chat returned invalid payload: {exc}") from exc
            except json.JSONDecodeError as exc:
                raise MetaResponseError(f"chat content is not valid JSON: {exc}") from exc
            cost_cents, priced = estimate_chat_cost_cents(
                model_id, usage.prompt_tokens, usage.completion_tokens
            )
            fields = {
                "prompt_tokens": usage.prompt_tokens,
                "completion_tokens": usage.completion_tokens,
                "total_tokens": usage.total_tokens,
                "cost_cents": cost_cents,
                "cost_priced": priced,
            }
            return (
                ChatResult(
                    text=text, data=parsed, usage=usage, model_id=model_id, raw=data
                ),
                fields,
            )

        return self._post(
            operation="chat",
            model_id=model_id,
            path="/chat/completions",
            payload=payload,
            request_id=rid,
            parse=parse,
        )

    def generate_image(
        self,
        model_id: str,
        prompt: str,
        *,
        size: str = "1024x1024",
        request_id: str | None = None,
    ) -> GeneratedImage:
        """Synthetic image generation (eval data). Returns decoded bytes."""
        rid = request_id or _new_request_id()
        payload = {
            "model": model_id,
            "prompt": prompt,
            "size": size,
            "response_format": "b64_json",
        }

        def parse(response: httpx.Response) -> tuple[GeneratedImage, dict[str, Any]]:
            data = _as_json("generate_image", response)
            try:
                raw_b64 = data["data"][0]["b64_json"]
                image_bytes = base64.b64decode(raw_b64)
            except (KeyError, IndexError, TypeError, binascii.Error) as exc:
                raise MetaResponseError(
                    f"generate_image returned invalid image data: {exc}"
                ) from exc
            cost_cents, priced = estimate_per_image_cost_cents(model_id)
            result = GeneratedImage(
                image_bytes=image_bytes,
                mime_type=_mime_for_bytes(image_bytes),
                model_id=model_id,
            )
            return result, {"cost_cents": cost_cents, "cost_priced": priced}

        return self._post(
            operation="generate_image",
            model_id=model_id,
            path="/images/generations",
            payload=payload,
            request_id=rid,
            parse=parse,
        )

    # -- transport -------------------------------------------------------

    def _retrying(self) -> Retrying:
        return Retrying(
            stop=stop_after_attempt(self._settings.max_retries + 1),
            wait=self._wait,
            retry=retry_if_exception(_is_retriable),
            reraise=True,
        )

    def _post(
        self,
        *,
        operation: str,
        model_id: str,
        path: str,
        payload: dict[str, Any],
        request_id: str,
        parse: Callable[[httpx.Response], tuple[Any, dict[str, Any]]],
    ) -> Any:
        started = time.monotonic()
        attempts = 0
        try:
            for attempt in self._retrying():
                with attempt:
                    # Count locally: AttemptManager exposes no attempt number,
                    # and one loop pass equals exactly one HTTP attempt.
                    attempts += 1
                    response = self._send(path, payload, request_id, operation)
                    self._check_status(operation, model_id, response)
                    result, fields = parse(response)
                    self._log(
                        operation=operation,
                        model_id=model_id,
                        request_id=request_id,
                        status="ok",
                        latency_ms=_ms_since(started),
                        attempts=attempts,
                        **fields,
                    )
                    return result
        except MetaAPIError as exc:
            # A success record can never precede this: _log(ok) runs only
            # immediately before the return above, and parse failures raise
            # non-retriable MetaResponseError before any success log.
            self._log(
                operation=operation,
                model_id=model_id,
                request_id=request_id,
                status="error",
                latency_ms=_ms_since(started),
                attempts=attempts,
                error_type=type(exc).__name__,
            )
            raise
        raise AssertionError("unreachable")  # pragma: no cover

    def _send(
        self, path: str, payload: dict[str, Any], request_id: str, operation: str
    ) -> httpx.Response:
        try:
            return self._http.post(path, json=payload, headers={"X-Request-ID": request_id})
        except httpx.TimeoutException as exc:
            raise MetaTimeoutError(
                f"{operation} timed out after {self._settings.timeout_s:g}s"
            ) from exc
        except httpx.TransportError as exc:
            raise MetaServerError(f"{operation} transport error: {exc}") from exc

    def _check_status(
        self, operation: str, model_id: str, response: httpx.Response
    ) -> None:
        status = response.status_code
        if 200 <= status < 300:
            return
        detail = response.text[:500]
        if status in (401, 403):
            raise MetaAuthError(
                f"{operation} rejected ({status}) for model {model_id}: {detail}"
            )
        if status == 429:
            raise MetaRateLimitError(
                f"{operation} rate-limited for model {model_id}",
                retry_after_s=parse_retry_after(response.headers.get("retry-after")),
            )
        if status >= 500:
            raise MetaServerError(f"{operation} server error ({status}): {detail}")
        raise MetaClientError(f"{operation} rejected ({status}): {detail}")

    def _log(self, **fields: Any) -> None:
        logger.info("meta_api_call", extra=fields)


def _as_json(operation: str, response: httpx.Response) -> dict[str, Any]:
    try:
        data = response.json()
    except ValueError as exc:
        raise MetaResponseError(
            f"{operation} returned invalid JSON (status {response.status_code})"
        ) from exc
    if not isinstance(data, dict):
        raise MetaResponseError(f"{operation} returned a non-object JSON payload")
    return data
