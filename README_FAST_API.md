# Asset Intelligence FastAPI - Team Onboarding

The backend is a FastAPI service (`app/api/main.py`, factory `create_app`) that runs the five-stage inspection pipeline and serves the review UI. This guide gets a new teammate from zero to first inspection in minutes.

Base URLs: local API http://127.0.0.1:8000 (compose also serves the UI at http://localhost:3000). Interactive docs: http://127.0.0.1:8000/docs (Swagger) and /redoc. `/healthz` and `/metrics` answer without auth but are hidden from the schema.

## 1. Start it

Option A - full stack (recommended, from a local drive, not a UNC path):

```powershell
Copy-Item .env.example .env   # add META_API_KEY for live calls
docker compose up --build
```

Option B - API only, no Docker (from repo root, venv active):

```powershell
python -m uvicorn --factory app.api.main:create_app --host 127.0.0.1 --port 8000
```

Sanity check (no auth):

```powershell
Invoke-RestMethod http://127.0.0.1:8000/healthz   # {"status": "ok", "version": "..."}
```

## 2. Authenticate

Every `/v1/*` route needs ONE of: `X-API-Key` header, or JWT `Authorization: Bearer [REDACTED]

- Local demos: if `API_KEY` is unset, the server uses the documented dev key `local-dev-key-123` and logs a loud warning. Convenient for `compose up`, never for anything shared.
- Shared or hosted use: set `API_KEY` in `.env` and send `-H "X-API-Key: <value>"`. A missing or wrong key returns `401 invalid or missing X-API-Key`.

JWT flow (needs `JWT_SECRET` + `UI_USERNAME` + `UI_PASSWORD_HASH`, else `503 JWT auth not configured`):

```powershell
# 1. trade UI login for a token pair (10/minute limit)
Invoke-RestMethod http://127.0.0.1:8000/v1/auth/token -Method POST -ContentType "application/json" -Body "{`"username`":`"reviewer`",`"password`":`"..."}"
# 2. call the API with the access token
$h = @{ Authorization = "Bearer <access_token>" }
Invoke-RestMethod http://127.0.0.1:8000/v1/stats -Headers $h
# 3. rotate before expiry
Invoke-RestMethod http://127.0.0.1:8000/v1/auth/refresh -Method POST -ContentType "application/json" -Body "{`"refresh_token`":`"..."}"
```

## 3. Run your first inspection

`POST /v1/inspections` takes multipart form fields (exact names):

| Field | Type | Rules |
|---|---|---|
| `images` | file, repeatable | 1-5 images, JPEG/PNG/WebP only, max 15 MB each |
| `note` | text | crew note, max 10,000 chars (default empty) |
| `asset_meta` | text | JSON object as string (default `{}`), e.g. `{"asset_id":"DEMO-001"}` |

Privacy note: every image is orientation-normalized and re-encoded with EXIF (GPS included) stripped before anything downstream sees it.

```powershell
curl.exe -X POST http://127.0.0.1:8000/v1/inspections -H "X-API-Key: <your-key>" -F "images=@culvert.jpg" -F "note=crack near top edge with seepage" -F "asset_meta={`"asset_id`":`"DEMO-001"}"
```

The response is the stored record JSON, including `request_id`, `segmentations` (RLE masks), `observations` with evidence pointers, `discrepancies`, `missing_information`, `recommended_next_step`, `human_review_required: true`, `model_trace`, `cost_cents` / `cost_priced`, and per-stage `durations_ms`. Expect tens of seconds on live mode (four serial model calls).

## 4. Read results

| Call | Returns |
|---|---|
| `GET /v1/inspections?limit=50&review_status=pending&asset_id=...` | `{inspections, count}`; limit 1-200 default 50; review_status in pending, accept, edit, reject |
| `GET /v1/inspections/{request_id}` | full record, or 404 `unknown or expired inspection` |
| `GET /v1/inspections/{request_id}/overlay?image=0` | PNG photo WITH SAM masks |
| `GET /v1/inspections/{request_id}/image?image=0` | original working photo (EXIF-stripped) |
| `GET /v1/stats` | usage + cost totals |

History keeps 24 h (TTL) and the list caps at 200 rows with no pagination yet: fetch what you need the same day.

## 5. Review (human gate)

`POST /v1/inspections/{request_id}/review` with JSON body `{"decision": "accept"|"edit"|"reject", "note": "optional, max 2000 chars"}` returns `{request_id, review_status, reviewed_at}`, or 404 for unknown/expired ids. Nothing is ever auto-accepted: `human_review_required` is always true.

## 6. Limits and errors (exact map)

| Code | Meaning | Typical cause |
|---|---|---|
| 400 | caller mistake | 0 or 6+ images, empty file, bad image bytes, wrong format, note over 10k chars, asset_meta not a JSON object |
| 401 | unauthorized | missing/wrong X-API-Key, expired Bearer, bad UI login |
| 404 | gone | unknown request_id, bad image index, or record past 24 h TTL |
| 413 | too large | image over 15 MB (also possible from the nginx proxy on huge uploads) |
| 422 | unusable | validator rejection with field errors, or model returned unusable output |
| 429 | slow down | rate limit (60/min default, 10/min on auth routes); upstream model limit adds `Retry-After` |
| 500 | server config | `META_API_KEY` missing on server, or Meta auth failure (no secrets leak in the message) |
| 502 / 504 | upstream | model service error / timeout |
| 503 | overloaded or off | model circuit open, or JWT routes called without JWT configured |

Rate limiting keys by API key (or token digest, or IP), via slowapi: `memory://` solo, Valkey in compose (`RATE_LIMIT_STORAGE_URI`). Run ONE worker on memory mode (see Dockerfile); Valkey allows replicas.

## 7. Observability

- `GET /metrics` (no auth): Prometheus scrape; includes per-inspection cost observer and validation-failure counter.
- OTEL traces per stage when `OTEL_EXPORTER_OTLP_ENDPOINT` is set; compose wires the collector + Prometheus.
- Every record carries `durations_ms` per stage and a `model_trace` of model IDs used.

## 8. Troubleshooting

- 401 on everything: start with `/healthz` (no auth). If that works, your key is wrong or the server `API_KEY` differs from what you send.
- 422 with field errors: the pipeline ran but the validator rejected the output. Read the error list; do not retry blindly.
- 429: back off for the `Retry-After` seconds; check whether `RATE_LIMIT_STORAGE_URI` points where you think.
- 502/503/504: Meta-side trouble or circuit open. Check server logs for `model service` lines; retry after a pause.
- 500 mentioning META_API_KEY: server-side `.env` problem, not your request. Never paste keys into chat or tickets.
- 404 right after creating: clocks or TTL confusion, or you are talking to a different container (Space vs local have separate stores).

## 9. Go deeper

- Limits and error map: section 6 above; operations: `docs/RUNBOOK.md`.
- All settings: `.env.example` + `docs/CONFIGURATION.md`.
- Auth and threat model: `SECURITY.md`.
- Test and eval workflow: `docs/TESTING.md` (`python -m pytest tests/ -q`, `python -m eval.run --mode mocked`).
- No-server CLI alternative: `python -m app.cli inspect --image culvert.jpg --note "..."` (exit 0/1/2).
