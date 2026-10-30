# Runbook

> Doc version: 1.4 | Updated: 2026-10-29 | Verified against: `bc663e4`

Day-to-day commands. All assume the venv is activated from the repo root.

## API server (local, no Docker)

```powershell
python -m uvicorn --factory app.api.main:create_app --host 127.0.0.1 --port 8000
```

Routes (`v1` = API version):

| Method & path | Purpose |
|---------------|---------|
| `GET /healthz` | Liveness (no auth) |
| `GET /metrics` | Prometheus metrics (no auth) |
| `POST /v1/auth/token` | Issue JWT access + refresh pair (username + password) |
| `POST /v1/auth/refresh` | Rotate refresh token (single-use) for a fresh pair |
| `POST /v1/inspections` | Run SAM → Vision → Spark → Wonder → Validate on images + note |
| `GET /v1/inspections/{request_id}` | Fetch a stored result |
| `GET /v1/inspections/{request_id}/overlay` | Segmentation overlay image |
| `GET /v1/inspections/{request_id}/image` | Normalized working image (no masks) |
| `POST /v1/inspections/{request_id}/review` | Human review decision |
| `GET /v1/inspections` | History list (`limit`, `review_status`, `asset_id` filters) |
| `GET /v1/stats` | Summary counts, review rate, cost totals, latency p50/p95 |

Authenticated routes need the `X-API-Key` header or `Authorization: Bearer <access>` (see [Configuration](CONFIGURATION.md)).
Single worker per container by design. Local runs default to in-memory limits; compose sets `RATE_LIMIT_STORAGE_URI=redis://valkey:6379` for shared limits across replicas.

Example inspection (dev key only, local):

```powershell
$headers = @{ "X-API-Key" = "<your API_KEY or dev key>" }
Invoke-RestMethod http://127.0.0.1:8000/healthz
```

## CLI (no server)

```powershell
python -m app.cli inspect --image culvert.jpg --note "Crack near top edge" --asset-id F-1 --overlay-dir previews/
```

Runs the pipeline in-process (needs `META_API_KEY`), prints result JSON, optionally writes
per-image overlay PNGs. Exit 0 = ok, 1 = upstream/model failure, 2 = caller/input failure.

## Full stack (Docker Compose)

```powershell
docker compose up --build
```

Starts API (:8000), review UI (:3000), OTEL collector (:4317/:4318), Prometheus (:9090), Valkey (:6379, shared rate limits).
Requires `.env` with `META_API_KEY` for live model calls. **Run from a local drive, not a
UNC path** — Docker fails on UNC checkouts.

## Evaluations

Mocked (no key, seconds, validates the harness — 50/50 expected green):

```powershell
python -m eval.run --mode mocked --out eval/report.json
```

Live slice (needs key + cases; ~35–50 s per case):

```powershell
$env:META_API_TIMEOUT_S = "180"
python -m eval.run --mode live --cases-dir eval/cases/synthetic --suites clear --limit 3 --out live_reports/slice.json
```

Full live 50 (needs key + cases; takes ~1.5 h, rough unpriced cost $2–3):

```powershell
$env:META_API_TIMEOUT_S = "180"
python -m eval.run --mode live --cases-dir eval/cases/synthetic --out live_reports/live-YYYY-MM-DD.json
```

CLI flags: `--mode {mocked,live}`, `--cases-dir`, `--out`, `--limit N`, `--suites ...`, `--skip-gates ...`. `--skip-gates` measures but exempts named gates (CI exempts `latency_p95_ms`, red by architecture).
Suites: `clear` (15), `incomplete` (10), `contradictory` (10), `ambiguous` (10), `adversarial` (5).
Exit code is nonzero when any gate fails — read the gate table in the report JSON.

`live_reports/` is gitignored: timestamped live reports stay local by design.

## Synthetic case generation

Case PNGs (~205 MB) ship with the repo, so evals run with no regeneration step. Refresh them with
(needs `META_API_KEY`; image generation needs the 180 s timeout):

```powershell
$env:META_API_TIMEOUT_S = "180"
python -m app.synthetic --out eval/cases/synthetic
```

Useful flags: `--suites`, `--limit`, `--overwrite`, `--image-size 1024x1024`.
See `eval/cases/synthetic/README.md` for the artifact contract.

## Review UI

Dev server (from `app/ui`, needs `node_modules` installed locally — not on UNC):

```powershell
cd app/ui
npm install
npm run dev      # vite on :3000
```

Other scripts: `npm run build`, `npm run preview`, `npm run test` (`vitest run`).
Production serves the built UI through nginx in the compose stack.

## Pipeline stages (what runs per inspection)

```
images + note → SAM segment → Vision fuse → Spark draft → Wonder plan → Validate
```

Per-stage wall-clock timings are recorded in `durations_ms` on every result and aggregated
as `stage_p95_ms` in eval reports. The chain is serial by design (each stage consumes the
previous stage's output); see `ARCHITECTURE.md` before attempting to parallelize it.

## Data handling and retention (operators)

- Ingress re-encodes every upload, dropping EXIF/GPS (`app/api/adapter.py`).
  The Meta API receives pixels + note text, never device metadata.
- The store keeps validated results, rendered overlays, normalized working
  images (EXIF-stripped, as the model saw them), and review state
  only — never raw uploads. Raw notes are not stored either, but evidence
  spans quote note text, so field notes with reporter PII survive inside
  stored observations. No redaction pass exists by design (redaction would
  corrupt span offsets); treat stored results as potentially PII-bearing.
- SQLite lives at `data/inspections.db` (or `:memory:`); records expire
  after 24 h via opportunistic TTL prune on access (`app/api/store.py`).
- `cost_cents` on results and eval reports are rate-card estimates for
  budgeting. Reconcile against the Meta console invoice before quoting.
