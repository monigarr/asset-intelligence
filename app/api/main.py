"""FastAPI review API (Day 7).

Routes: POST /v1/inspections (multipart upload → validated result),
GET /v1/inspections/{id}, GET .../overlay?image=N, POST .../review,
plus /healthz and /metrics (no auth).

Notes:
  - Import side-effect free; serve with `uvicorn --factory app.api.main:create_app`.
  - Auth is API key only; JWT/SSO is a post-hackathon item (ARCH §6).
  - Rate limiting is in-memory (slowapi) — run ONE worker (see Dockerfile);
    Redis-backed limits are the production move.
  - Error mapping (ARCH §11): caller mistakes → 400/413/422, validator
    rejection → 422 with field errors, upstream rate limit → 429 with
    Retry-After, upstream failure → 502/504, missing server key → 500
    without leaking anything.
"""

from __future__ import annotations

import logging
import os
import secrets
from typing import Annotated, Any, Literal

from fastapi import (
    Depends,
    FastAPI,
    File,
    Form,
    Header,
    HTTPException,
    Request,
    Response,
    UploadFile,
)
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, ValidationError
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app import __version__
from app.api.adapter import normalize_inspection
from app.api.security import resolve_api_key
from app.api.store import InspectionStore
from app.api.telemetry import (
    COST_CENTS,
    VALIDATION_FAILURES,
    metrics_middleware,
    metrics_response,
    setup_telemetry,
)
from app.gateway import Settings
from app.gateway.errors import (
    MetaAuthError,
    MetaClientError,
    MetaRateLimitError,
    MetaResponseError,
    MetaServerError,
    MetaTimeoutError,
)
from app.orchestrator import InspectionPipeline
from app.sam_service import DecodedMask
from app.sam_service.overlay import render_overlay
from app.sam_service.service import LOW_CONFIDENCE_THRESHOLD, decode_mask_rle
from app.validator import InspectionResult

logger = logging.getLogger("asset_intel.api")


class ReviewRequest(BaseModel):
    decision: Literal["accept", "edit", "reject"]
    note: str | None = Field(default=None, max_length=2000)


def _rate_key(request: Request) -> str:
    key = request.headers.get("X-API-Key")
    if key:
        return f"key:{key}"
    host = request.client.host if request.client else "unknown"
    return f"ip:{host}"


def _serializable_errors(exc: ValidationError) -> list[dict[str, Any]]:
    return exc.errors(include_url=False)


def _decoded_for(
    result: InspectionResult, image_index: int, width: int, height: int
) -> list[DecodedMask]:
    out = []
    for mask in result.segmentations:
        if mask.source_image != f"image_{image_index}":
            continue
        out.append(
            DecodedMask(
                mask=mask,
                low_confidence=mask.confidence < LOW_CONFIDENCE_THRESHOLD,
                bitmap=decode_mask_rle(mask.rle, (width, height)),
            )
        )
    return out


def create_app(
    *,
    settings: Settings | None = None,
    pipeline: InspectionPipeline | None = None,
    store: InspectionStore | None = None,
    store_path: str | None = None,
    api_key: str | None = None,
    rate_limit: str = "60/minute",
    enable_otel: bool = True,
) -> FastAPI:
    expected_key = api_key or resolve_api_key()
    active_store = store or InspectionStore(
        store_path or os.environ.get("STORE_PATH", "data/inspections.db")
    )
    app = FastAPI(title="Asset Intelligence API", version=__version__)

    limiter = Limiter(key_func=_rate_key, default_limits=[rate_limit])
    app.state.limiter = limiter
    app.add_middleware(SlowAPIMiddleware)
    app.middleware("http")(metrics_middleware)

    @app.exception_handler(RateLimitExceeded)
    async def _ratelimited(request: Request, exc: RateLimitExceeded) -> JSONResponse:
        return JSONResponse({"detail": "rate limit exceeded"}, status_code=429)

    if enable_otel:
        setup_telemetry(app, os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT"))

    holder: dict[str, Any] = {"settings": settings, "pipeline": pipeline}

    def get_pipeline() -> InspectionPipeline:
        if holder["pipeline"] is None:
            try:
                active_settings = holder["settings"] or Settings.from_env()
            except MetaAuthError:
                raise HTTPException(500, "META_API_KEY not configured on server")
            holder["settings"] = active_settings
            holder["pipeline"] = InspectionPipeline(settings=active_settings)
        return holder["pipeline"]

    async def require_key(
        x_api_key: Annotated[str | None, Header()] = None,
    ) -> str:
        if not x_api_key or not secrets.compare_digest(x_api_key, expected_key):
            raise HTTPException(401, "invalid or missing X-API-Key")
        return x_api_key

    @app.get("/healthz", include_in_schema=False)
    async def healthz() -> dict[str, str]:
        return {"status": "ok", "version": __version__}

    @app.get("/metrics", include_in_schema=False)
    async def metrics() -> Response:
        return metrics_response()

    @app.post("/v1/inspections")
    async def create_inspection(
        request: Request,
        # B008 note: canonical FastAPI form; FastAPI copy_field_info's
        # the default per-route, so no mutable-default hazard exists.
        images: list[UploadFile] = File(...),  # noqa: B008
        note: str = Form(""),
        asset_meta: str = Form("{}"),
        key: str = Depends(require_key),
    ) -> dict[str, Any]:
        normalized, text, meta = await normalize_inspection(images, note, asset_meta)
        pipe = get_pipeline()
        try:
            result = pipe.run_full([n.data for n in normalized], text, meta)
        except ValidationError as exc:
            VALIDATION_FAILURES.inc()
            raise HTTPException(422, detail=_serializable_errors(exc))
        except MetaRateLimitError as exc:
            raise HTTPException(
                429,
                detail="model rate limit exceeded",
                headers={"Retry-After": str(int(exc.retry_after_s or 1))},
            )
        except MetaTimeoutError:
            raise HTTPException(504, "model request timed out")
        except MetaServerError:
            raise HTTPException(502, "model service error")
        except MetaAuthError:
            raise HTTPException(
                500, "Meta API authentication failed — check server META_API_KEY"
            )
        except MetaClientError as exc:
            raise HTTPException(502, f"model request rejected: {exc}")
        except MetaResponseError as exc:
            raise HTTPException(422, f"model returned unusable output: {exc}")
        overlays = {
            i: render_overlay(n.data, _decoded_for(result, i, n.width, n.height))
            for i, n in enumerate(normalized)
        }
        record = active_store.save(result, overlays)
        COST_CENTS.observe(result.cost_cents)
        logger.info(
            "inspection_complete",
            extra={
                "request_id": record.request_id,
                "mask_count": len(result.segmentations),
                "observation_count": len(result.observations),
                "cost_cents": result.cost_cents,
            },
        )
        return record.model_dump(mode="json")

    @app.get("/v1/inspections/{request_id}")
    async def get_inspection(
        request_id: str, key: str = Depends(require_key)
    ) -> dict[str, Any]:
        record = active_store.get(request_id)
        if record is None:
            raise HTTPException(404, "unknown or expired inspection")
        return record.model_dump(mode="json")

    @app.get("/v1/inspections/{request_id}/overlay")
    async def get_overlay(
        request_id: str, image: int = 0, key: str = Depends(require_key)
    ) -> Response:
        png = active_store.get_overlay(request_id, image)
        if png is None:
            raise HTTPException(404, "unknown inspection or image index")
        return Response(png, media_type="image/png")

    @app.post("/v1/inspections/{request_id}/review")
    async def review_inspection(
        request_id: str, body: ReviewRequest, key: str = Depends(require_key)
    ) -> dict[str, Any]:
        record = active_store.review(request_id, body.decision, body.note)
        if record is None:
            raise HTTPException(404, "unknown or expired inspection")
        return {
            "request_id": request_id,
            "review_status": record.review_status,
            "reviewed_at": record.reviewed_at,
        }

    return app
