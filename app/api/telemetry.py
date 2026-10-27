"""OTEL tracing + Prometheus metrics (Day 7, ARCH §10).

Tracing: OTLP/HTTP export to the collector when `OTEL_EXPORTER_OTLP_ENDPOINT`
is set, silent local NoOp-ish provider otherwise (export failures are SDK
background noise, never fatal). Metrics: request counts/latency,
validation failures, cost histogram, served at /metrics.
"""

from __future__ import annotations

from fastapi import FastAPI, Request, Response
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

REQUEST_COUNT = Counter(
    "inspection_requests_total", "API requests", ["method", "route", "status"]
)
REQUEST_LATENCY = Histogram(
    "inspection_request_latency_seconds", "API latency", ["route"]
)
VALIDATION_FAILURES = Counter(
    "inspection_validation_failures_total", "Validator rejections"
)
COST_CENTS = Histogram(
    "inspection_cost_cents",
    "Pipeline cost per inspection",
    buckets=(1, 5, 10, 15, 25, 50, 100, float("inf")),
)

_configured = False


def setup_telemetry(app: FastAPI, endpoint: str | None) -> None:
    """Install tracer provider + FastAPI instrumentation exactly once."""
    global _configured
    if _configured:
        return
    provider = TracerProvider(
        resource=Resource({"service.name": "asset-intelligence-api"})
    )
    if endpoint:
        provider.add_span_processor(
            BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint))
        )
    trace.set_tracer_provider(provider)
    FastAPIInstrumentor.instrument_app(app)
    _configured = True


async def metrics_middleware(request: Request, call_next):
    """Record per-route counts + latency (route templates, not raw paths)."""
    import time

    started = time.perf_counter()
    response = await call_next(request)
    route = request.scope.get("route")
    template = getattr(route, "path", request.url.path) if route else request.url.path
    REQUEST_COUNT.labels(request.method, template, str(response.status_code)).inc()
    REQUEST_LATENCY.labels(template).observe(time.perf_counter() - started)
    return response


def metrics_response() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
