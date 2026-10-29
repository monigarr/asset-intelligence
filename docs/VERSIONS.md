# Versions

> Doc version: 1.5 | Updated: 2026-10-29 | Verified against: `bc663e4`

Single reference for every version that matters in this repo. When you change a pinned
version, update this file in the same commit.

## Doc changelog

| Doc version | Date | Change |
|-------------|------|--------|
| 1.0 | 2026-10-27 | Initial `docs/` (this file + README, Getting Started, Configuration, Runbook, Testing, Troubleshooting), verified against `2b1c7dc` |
| 1.1 | 2026-10-27 | JWT/Valkey/CLI coverage; new dep pins; 139 tests; precision gate; PRD/ARCH v1.1 |
| 1.2 | 2026-10-29 | TESTING 1.2 (regression workflow); CONFIGURATION 1.2 (pricing contract); GETTING_STARTED 1.1; freeze adds starlette 1.10.0; 171 tests |
| 1.3 | 2026-10-29 | Verified against `c83dfd5`: PNG-policy corrections, 171-test sync, git-housekeeping notes, CI fixes; ARCH v1.2 |
| 1.4 | 2026-10-29 | Verified against `42211b5`: CI live/skip-gates, compose `$$` unescape, JWT escaping docs |
| 1.5 | 2026-10-29 | Verified against `bc663e4`: Insights tab (history/stats endpoints, filterable UI); 178 tests |

Guide docs carry their own `Doc version` headers; bump MINOR on content changes, MAJOR on
restructuring, and add a row here.

## Runtime

| Component | Version | Source |
|-----------|---------|--------|
| Python (verified) | 3.12.3 | local venv |
| Python (Docker) | `python:3.12-slim` | `Dockerfile` |
| API version | `v1` (`/v1/inspections`, …) | `app/api/main.py` |
| Review UI | 0.1.0 | `app/ui/package.json` |
| PRD / ARCHITECTURE | PRD v1.1, ARCH v1.2 (2026-10-29) | repo root |

## Live model IDs (verified 2026-10-27 via `GET /v1/models`)

| Role | ID | Variable |
|------|----|----------|
| Vision + fallback | `muse-spark-1.3` | `VISION_MODEL_ID`, `FALLBACK_VISION_MODEL_ID` |
| Reasoning | `muse-spark-1.3` | `REASONING_MODEL_ID` |
| Planning | `muse-wonder-1.0` | `PLANNING_MODEL_ID` |
| Image generation | `muse-image-1.0` | `IMAGE_MODEL_ID` |
| Segmentation | `sam-3.1` (via `POST /v1/responses`) | `SAM_MODEL_ID` |
| API base | `https://api.meta.ai/v1` | `META_API_BASE_URL` |

## Verified dependency freeze

`requirements.txt` uses floor pins; these are the exact versions installed and green in the
verified checkout (`pip freeze`, 2026-10-27). Use this table to sanity-check a fresh install.

```
coverage==7.17.0
fastapi==0.162.0
httpx==0.28.1
numpy==2.5.4
opentelemetry-api==1.45.1
pillow==13.0.0
pydantic==2.14.1
pydantic_core==2.50.1
pytest==9.1.1
pytest-cov==7.1.0
python-dotenv==1.2.4
ruff==0.17.3
uvicorn==0.54.0
PyJWT==2.15.1
argon2-cffi==25.1.0
redis==8.1.0
starlette==1.10.0
```

(Full transitive freeze: run `pip freeze` in your venv. A committed `sbom.txt` is planned
per `PRIVATE_DEV_GUIDE.md`.)

## Compose image pins

| Image | Pin | File |
|-------|-----|------|
| OTEL collector | `otel/opentelemetry-collector:0.110.0` | `docker-compose.yml` |
| Prometheus | `prom/prometheus:v2.52.0` | `docker-compose.yml` |
| API / UI | built from repo (`Dockerfile`, `app/ui/Dockerfile`) | `docker-compose.yml` |

## Eval gates (current contract)

| Gate | Threshold | Last live 50 (2026-10-27) |
|------|-----------|---------------------------|
| success_rate | == 1.0 | 0.90 — red |
| refusal_rate | == 1.0 | 1.0 — green |
| missing_f1 | ≥ 0.7 | 0.822 — green |
| missing_precision | ≥ 0.85 | new gate, mocked 1.0 — green |
| conflict_f1 | ≥ 0.6 | 1.0 — green |
| fabrication_rate | == 0 | 0.0 — green |
| latency p95 | < 8000 ms | 47896 ms — red (architectural, see Runbook) |
| mask IoU | ≥ 0.55 (mocked only) | n/a live |
| ECE | ≤ 0.15 (needs labels) | n/a (unlabeled cases) |

Unit suite: 178 tests, coverage gate 70% (currently ~89%). Report: `live_reports/`.
