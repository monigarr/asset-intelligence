"""Gateway tests with mocked Meta Model API transport (no network, no key)."""

from __future__ import annotations

import base64
import json
import logging
from io import BytesIO
from pathlib import Path

import httpx
import pytest
from PIL import Image

from app.gateway.config import Settings
from app.gateway.errors import (
    MetaAPIError,
    MetaAuthError,
    MetaClientError,
    MetaResponseError,
    MetaServerError,
    MetaTimeoutError,
)
from app.gateway.meta_client import MetaClient, parse_retry_after

LOGGER = "asset_intel.gateway"
JPEG = b"\xff\xd8\xff" + b"\x00" * 100  # minimal JPEG magic
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100


def _settings(**overrides: object) -> Settings:
    kwargs: dict[str, object] = {
        "api_key": "test-key",
        "base_url": "https://api.test/v1",
        "timeout_s": 5.0,
        "max_retries": 2,
    }
    kwargs.update(overrides)
    return Settings(**kwargs)  # type: ignore[arg-type]


def _client(handler: object, **overrides: object) -> MetaClient:
    return MetaClient(
        settings=_settings(),
        transport=httpx.MockTransport(handler),  # type: ignore[arg-type]
        retry_wait=lambda _state: 0,  # never sleep in tests
        **overrides,  # type: ignore[arg-type]
    )


def _call_record(caplog: pytest.LogCaptureFixture, status: str = "ok"):
    records = [
        r
        for r in caplog.records
        if r.name == LOGGER and getattr(r, "status", None) == status
    ]
    assert len(records) == 1, f"expected one {status} record, got {len(records)}"
    return records[0]


@pytest.fixture(autouse=True)
def _capture_gateway_logs(caplog: pytest.LogCaptureFixture):
    caplog.set_level(logging.INFO, logger=LOGGER)


# -- chat ---------------------------------------------------------------


def test_chat_success_logs_structured_fields(caplog: pytest.LogCaptureFixture) -> None:
    seen: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["auth"] = request.headers["Authorization"]
        seen["path"] = request.url.path
        seen["request_id"] = request.headers["X-Request-ID"]
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": "crack observed"}}],
                "usage": {
                    "prompt_tokens": 100,
                    "completion_tokens": 20,
                    "total_tokens": 120,
                },
            },
        )

    result = _client(handler).chat(
        "muse-spark-1.3", [{"role": "user", "content": "hi"}], request_id="req_test1"
    )
    assert result.text == "crack observed"
    assert result.usage.total_tokens == 120
    assert seen["auth"] == "Bearer test-key"
    assert seen["path"] == "/v1/chat/completions"
    assert seen["request_id"] == "req_test1"

    rec = _call_record(caplog)
    assert rec.request_id == "req_test1"
    assert rec.model_id == "muse-spark-1.3"
    assert rec.operation == "chat"
    assert rec.attempts == 1
    assert rec.latency_ms >= 0
    assert rec.total_tokens == 120
    assert rec.cost_priced is False  # placeholder pricing (pricing.py)


def test_chat_with_images_json_format_and_extra() -> None:
    seen: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["body"] = json.loads(request.content.decode())
        return httpx.Response(
            200, json={"choices": [{"message": {"content": '{"ok": true}'}}]}
        )

    result = _client(handler).chat(
        "muse-spark-1.3",
        [{"role": "user", "content": "describe"}],
        images=[JPEG],
        response_format={"type": "json_schema", "json_schema": {"name": "s"}},
        extra={"sam_masks": [{"mask_id": "mask_1"}]},
    )
    assert result.data == {"ok": True}

    body = seen["body"]
    assert isinstance(body, dict)
    assert body["response_format"]["type"] == "json_schema"
    assert body["sam_masks"] == [{"mask_id": "mask_1"}]
    content = body["messages"][0]["content"]
    assert content[0] == {"type": "text", "text": "describe"}
    assert content[1]["image_url"]["url"].startswith("data:image/jpeg;base64,")


def test_chat_invalid_json_content_fails_closed_single_attempt() -> None:
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(200, json={"choices": [{"message": {"content": "nope"}}]})

    with pytest.raises(MetaResponseError):
        _client(handler).chat(
            "muse-spark-1.3",
            [{"role": "user", "content": "hi"}],
            response_format={"type": "json_object"},
        )
    assert len(calls) == 1  # deterministic failure: no retry


def test_chat_non_dict_json_fails_closed() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"choices": [{"message": {"content": "[1]"}}]})

    with pytest.raises(MetaResponseError):
        _client(handler).chat(
            "muse-spark-1.3",
            [{"role": "user", "content": "hi"}],
            response_format={"type": "json_object"},
        )


# -- retry behavior -----------------------------------------------------


def test_rate_limit_then_success(caplog: pytest.LogCaptureFixture) -> None:
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        if len(calls) == 1:
            return httpx.Response(429, headers={"Retry-After": "0"}, text="slow down")
        return httpx.Response(200, json={"choices": [{"message": {"content": "ok"}}]})

    result = _client(handler).chat("muse-spark-1.3", [{"role": "user", "content": "hi"}])
    assert result.text == "ok"
    assert len(calls) == 2
    assert _call_record(caplog).attempts == 2


def test_persistent_500_retries_twice_then_raises(
    caplog: pytest.LogCaptureFixture,
) -> None:
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(500, text="boom")

    with pytest.raises(MetaServerError):
        _client(handler).chat("muse-spark-1.3", [{"role": "user", "content": "hi"}])
    assert len(calls) == 3  # initial + 2 retries (ARCHITECTURE.md max 2 retries)
    rec = _call_record(caplog, status="error")
    assert rec.error_type == "MetaServerError"
    assert rec.attempts == 3


def test_unauthorized_not_retried() -> None:
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(401, text="bad key")

    with pytest.raises(MetaAuthError):
        _client(handler).chat("muse-spark-1.3", [{"role": "user", "content": "hi"}])
    assert len(calls) == 1


def test_bad_request_not_retried() -> None:
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(400, text="bad model")

    with pytest.raises(MetaClientError):
        _client(handler).chat("nope", [{"role": "user", "content": "hi"}])
    assert len(calls) == 1


def test_timeout_retried_then_raises() -> None:
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        raise httpx.ConnectTimeout("connect timed out")

    with pytest.raises(MetaTimeoutError):
        _client(handler).chat("muse-spark-1.3", [{"role": "user", "content": "hi"}])
    assert len(calls) == 3


# -- segment / generate_image -------------------------------------------


def _grammar() -> str:
    return (Path(__file__).parent / "fixtures" / "sam_crack.txt").read_text(
        encoding="utf-8"
    )


def _tiny_png(w: int = 64, h: int = 48) -> bytes:
    img = Image.new("RGB", (w, h), (200, 200, 200))
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def test_segment_success(caplog: pytest.LogCaptureFixture) -> None:
    seen: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["body"] = json.loads(request.content.decode())
        seen["path"] = request.url.path
        return httpx.Response(
            200,
            json={
                "status": "completed",
                "output": [
                    {
                        "type": "message",
                        "content": [{"type": "output_text", "text": _grammar()}],
                    }
                ],
            },
        )

    masks = _client(handler).segment("sam-3.1", _tiny_png(), "crack")
    assert len(masks) == 1
    mask = masks[0]
    assert (mask.mask_id, mask.label, mask.source_image) == ("mask-1", "crack", "image_0")
    assert mask.confidence == 0.5  # live grammar omits c (unscored default)
    assert mask.bbox == [27, 4, 42, 20]
    assert isinstance(mask.rle, dict)
    assert mask.rle["size"] == [48, 64]
    assert sum(mask.rle["counts"]) == 64 * 48
    body = seen["body"]
    assert isinstance(body, dict)
    assert seen["path"] == "/v1/responses"
    assert body["model"] == "sam-3.1"
    content = body["input"][0]["content"]
    assert content[0] == {"type": "input_text", "text": "crack"}
    assert content[1]["image_url"].startswith("data:image/png;base64,")
    assert _call_record(caplog).mask_count == 1


def test_segment_rejects_bad_payload_single_attempt() -> None:
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(200, json={"status": "completed", "output": []})

    with pytest.raises(MetaResponseError):
        _client(handler).segment("sam-3.1", _tiny_png(), "crack")
    assert len(calls) == 1


def test_segment_empty_output_text_is_no_match() -> None:
    # Live shape for "prompt found nothing": completed + output_text "".
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "status": "completed",
                "output": [
                    {
                        "type": "message",
                        "content": [{"type": "output_text", "text": ""}],
                    }
                ],
            },
        )

    assert _client(handler).segment("sam-3.1", _tiny_png(), "water seepage") == []


def test_generate_image_success() -> None:
    payload = base64.b64encode(PNG).decode("ascii")

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/images/generations"
        return httpx.Response(200, json={"data": [{"b64_json": payload}]})

    result = _client(handler).generate_image("muse-image", "culvert crack")
    assert result.image_bytes == PNG
    assert result.mime_type == "image/png"


# -- config / helpers ---------------------------------------------------


def test_missing_api_key_fails_fast() -> None:
    with pytest.raises(MetaAuthError, match="META_API_KEY not configured"):
        Settings.from_env({})
    with pytest.raises(MetaAuthError, match="META_API_KEY not configured"):
        Settings.from_env({"META_API_KEY": "sk-meta-REPLACE_ME"})
    assert isinstance(MetaAuthError("x"), MetaAPIError)


def test_parse_retry_after() -> None:
    assert parse_retry_after(None) is None
    assert parse_retry_after("  ") is None
    assert parse_retry_after("3") == 3.0
    assert parse_retry_after("garbage") is None
    assert parse_retry_after("Sun, 06 Nov 1994 08:49:37 GMT") == 0.0  # past
    future = parse_retry_after("Sun, 06 Nov 2034 08:49:37 GMT")
    assert future is not None and future > 0


def test_no_secret_leak_in_logs(caplog: pytest.LogCaptureFixture) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"choices": [{"message": {"content": "ok"}}]})

    _client(handler).chat("muse-spark-1.3", [{"role": "user", "content": "hi"}])
    assert "test-key" not in caplog.text


def test_placeholder_tables_cover_live_model_ids() -> None:
    from app.gateway.pricing import (
        _PLACEHOLDER_PER_1K_TOKENS_CENTS,
        _PLACEHOLDER_PER_IMAGE_CENTS,
    )

    assert "muse-wonder-1.0" in _PLACEHOLDER_PER_1K_TOKENS_CENTS
    assert "muse-image-1.0" in _PLACEHOLDER_PER_IMAGE_CENTS
    assert "muse-wonder" not in _PLACEHOLDER_PER_1K_TOKENS_CENTS
    assert "muse-image" not in _PLACEHOLDER_PER_IMAGE_CENTS


def test_breaker_opens_after_consecutive_server_errors() -> None:
    import httpx

    from app.gateway import Settings
    from app.gateway.errors import MetaCircuitOpenError, MetaServerError
    from app.gateway.meta_client import MetaClient

    def _boom(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"error": "down"})

    client = MetaClient(
        settings=Settings(api_key="t"),
        transport=httpx.MockTransport(_boom),
        retry_wait=lambda _state: 0.0,
    )
    for _ in range(5):
        with pytest.raises(MetaServerError):
            client.chat("muse-spark-1.3", [{"role": "user", "content": "hi"}])
    with pytest.raises(MetaCircuitOpenError):
        client.chat("muse-spark-1.3", [{"role": "user", "content": "hi"}])


def test_breaker_resets_on_success_and_half_opens() -> None:
    from app.gateway.meta_client import _CircuitBreaker

    breaker = _CircuitBreaker(threshold=2, cooldown_s=100.0)
    breaker.record_failure()
    breaker.record_success()  # consecutive chain broken
    breaker.record_failure()
    breaker.check()  # only 1 consecutive: still closed
    breaker.record_failure()
    with pytest.raises(Exception, match="circuit open"):
        breaker.check()
    breaker._opened_at -= 200.0  # simulate cooldown elapse
    breaker.check()  # half-open: trial allowed
    breaker.record_success()
    breaker.check()  # closed again


def test_split_pricing_input_output_math() -> None:
    from app.gateway.pricing import estimate_chat_cost_cents

    env = {
        "META_PRICE_PER_1K_CENTS_MUSE_SPARK_1_3_INPUT": "0.125",
        "META_PRICE_PER_1K_CENTS_MUSE_SPARK_1_3_OUTPUT": "0.425",
    }
    cents, priced = estimate_chat_cost_cents("muse-spark-1.3", 1000, 1000, env)
    assert priced is True
    assert cents == pytest.approx(0.55)


def test_split_pricing_cached_tokens_use_cached_rate() -> None:
    from app.gateway.pricing import estimate_chat_cost_cents

    env = {
        "META_PRICE_PER_1K_CENTS_MUSE_SPARK_1_3_INPUT": "0.125",
        "META_PRICE_PER_1K_CENTS_MUSE_SPARK_1_3_CACHED_INPUT": "0.015",
        "META_PRICE_PER_1K_CENTS_MUSE_SPARK_1_3_OUTPUT": "0.425",
    }
    cents, priced = estimate_chat_cost_cents(
        "muse-spark-1.3", 1000, 0, env, cached_tokens=1000
    )
    assert priced is True
    assert cents == pytest.approx(0.015)


def test_blended_fallback_when_split_unset() -> None:
    from app.gateway.pricing import estimate_chat_cost_cents

    env = {"META_PRICE_PER_1K_CENTS_MUSE_SPARK_1_3": "0.2"}
    cents, priced = estimate_chat_cost_cents("muse-spark-1.3", 1000, 1000, env)
    assert priced is True
    assert cents == pytest.approx(0.4)


def test_price_override_rejects_non_numeric() -> None:
    from app.gateway.pricing import estimate_chat_cost_cents

    with pytest.raises(ValueError, match="must be a number"):
        estimate_chat_cost_cents(
            "muse-spark-1.3",
            1,
            1,
            {"META_PRICE_PER_1K_CENTS_MUSE_SPARK_1_3": "$1.25"},
        )


def test_tier_schedule_wins_when_complete() -> None:
    from app.gateway.pricing import estimate_chat_cost_cents

    env = {
        "META_PRICE_TIER": "contributor",
        "META_PRICE_PER_1K_CENTS_MUSE_SPARK_1_3_INPUT": "0.125",
        "META_PRICE_PER_1K_CENTS_MUSE_SPARK_1_3_OUTPUT": "0.425",
        "META_PRICE_PER_1K_CENTS_MUSE_SPARK_1_3_CONTRIBUTOR_INPUT": "0.01",
        "META_PRICE_PER_1K_CENTS_MUSE_SPARK_1_3_CONTRIBUTOR_OUTPUT": "0.02",
    }
    cents, priced = estimate_chat_cost_cents("muse-spark-1.3", 1000, 1000, env)
    assert priced is True
    assert cents == pytest.approx(0.03)


def test_tier_falls_back_to_base_schedule() -> None:
    from app.gateway.pricing import estimate_chat_cost_cents

    env = {
        "META_PRICE_TIER": "contributor",
        "META_PRICE_PER_1K_CENTS_MUSE_SPARK_1_3_INPUT": "0.125",
        "META_PRICE_PER_1K_CENTS_MUSE_SPARK_1_3_OUTPUT": "0.425",
    }
    cents, priced = estimate_chat_cost_cents("muse-spark-1.3", 1000, 1000, env)
    assert priced is True
    assert cents == pytest.approx(0.55)


def test_hourly_estimate_math_and_unpriced() -> None:
    from app.gateway.pricing import estimate_hourly_cost_cents

    cents, priced = estimate_hourly_cost_cents(
        "muse-image-1.0", 1800.0, {"META_PRICE_PER_1_HOUR_MUSE_IMAGE_1_0_OUTPUT": "1.0"}
    )
    assert priced is True
    assert cents == pytest.approx(0.5)
    assert estimate_hourly_cost_cents("muse-image-1.0", 1800.0, {}) == (0.0, False)
