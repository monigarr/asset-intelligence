# Configuration

> Doc version: 1.3 | Updated: 2026-10-29 | Verified against: `c83dfd5`

All runtime configuration is environment variables, loaded from `.env` (see `.env.example`).
**Never commit `.env`.** The template `.env.example` is safe to commit and is the canonical list.

## Required for live calls

| Variable | Purpose | Example |
|----------|---------|---------|
| `META_API_KEY` | Meta Model API key ([console](https://dev.meta.ai/api-keys)) | *(secret)* |
| `META_API_BASE_URL` | API base | `https://api.meta.ai/v1` |
| `META_API_TIMEOUT_S` | HTTP timeout. Image generation exceeds the 15 s default — set `180` for synthetic case generation or live eval | `180` |

## Model IDs (live-verified 2026-10-27)

| Variable | Default | Role |
|----------|---------|------|
| `VISION_MODEL_ID` | `muse-spark-1.3` | Primary vision fusion |
| `FALLBACK_VISION_MODEL_ID` | `muse-spark-1.3` | Vision fallback (same model; no Llama model exists on the live API, verified 2026-10-27) |
| `REASONING_MODEL_ID` | `muse-spark-1.3` | Spark structured reasoning |
| `PLANNING_MODEL_ID` | `muse-wonder-1.0` | Wonder planning review |
| `IMAGE_MODEL_ID` | `muse-image-1.0` | Synthetic image generation |
| `SAM_MODEL_ID` | `sam-3.1` | Segmentation via `POST /v1/responses` |

There is no `POST /v1/segment` endpoint; segmentation goes through `/v1/responses` with the
official `meta_sam_parser` (`app/gateway/sam_responses.py`).

The compose stack pins `VISION/FALLBACK_VISION/REASONING/PLANNING_MODEL_ID` in `docker-compose.yml` so demos ignore stale `.env` IDs; local runs use `.env` (or code defaults).

## API server

Protected routes accept `X-API-Key` or a JWT Bearer token (`/v1/auth/*` issue/refresh).

| Variable | Purpose | Default |
|----------|---------|---------|
| `API_KEY` | `X-API-Key` auth for the FastAPI service. Unset = documented dev key, local demos only — set this for anything shared (see `SECURITY.md` §2) | dev key |
| `JWT_SECRET` | HS256 secret enabling `/v1/auth/*` (long random string; unset = 503) | unset |
| `UI_USERNAME` / `UI_PASSWORD_HASH` | Review-UI credential (Argon2 hash; mint command in `.env.example`) | reviewer / unset |
| `RATE_LIMIT_STORAGE_URI` | slowapi storage: `memory://` solo, `redis://valkey:6379` shared | memory:// |
| `STORE_PATH` | SQLite inspection store path | compose sets `/data/inspections.db` |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | OTLP/HTTP trace export (full path; a bare host 404s) | compose sets `http://otel-collector:4318/v1/traces` |

## Cost metering (optional, fail-closed)

Built-in prices are `0.0` placeholders and every estimate reports `priced=False` until you
supply overrides. Never quote `cost_cents` to judges while `priced` is `False`.

| Variable pattern | Purpose |
|------------------|---------|
| `META_PRICE_PER_1K_CENTS_<MODEL>_{INPUT,OUTPUT,CACHED_INPUT}` | Split chat/vision USD cents per 1k tokens (preferred) |
| `META_PRICE_PER_1K_CENTS_<MODEL>` | Blended fallback when split rates are absent |
| `META_PRICE_PER_1K_CENTS_<MODEL>_<TIER>_{...}` | Tier schedule selected by `META_PRICE_TIER` (e.g. `contributor`) |
| `META_PRICE_PER_IMAGE_CENTS_<MODEL>` | Per-image USD cents, e.g. `META_PRICE_PER_IMAGE_CENTS_SAM_3_1` |
| `META_PRICE_PER_1_HOUR_<MODEL>_OUTPUT` | USD cents/hour for time-metered models (image generation) |

`<MODEL>` is the model id uppercased with non-alphanumerics as `_`. All values are plain
numbers (USD cents; token rates convert as cents/1k = $/1M / 10) -- no `$` signs or suffixes.
`.env.example` carries Meta-console figures (observed 2026-10-28, Standard mode) as commented
examples; set `META_PRICE_TIER=contributor` only if your usage is billed at contributor rates.
Re-confirm against your Meta console invoice before quoting costs.

## Ports (compose stack)

| Service | Port |
|---------|------|
| API | 8000 |
| Review UI | 3000 |
| Prometheus | 9090 |
| OTLP gRPC / HTTP | 4317 / 4318 |
| Valkey (rate limits) | 6379 |

MinIO is intentionally absent: Docker Hub gates `minio/minio` pulls and Day-7 storage is
SQLite by design. It returns with M3 production persistence.
