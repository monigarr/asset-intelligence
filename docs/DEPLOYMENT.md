# Deployment

> Doc version: 1.1 | Updated: 2026-10-31 | Verified against: `379af51`

Three ways to run this repo, pick one row and follow it. New engineers start
with [Getting Started](GETTING_STARTED.md) for clone, venv, and install.

| # | Option | Use it when | Guide |
|---|--------|-------------|-------|
| A | Local Docker stack | Day-to-day dev, full observability, evals | This file, section A |
| B | Hugging Face Space demo | Public one-link demo for judges and reviewers | This file, section B |
| C | Hosted production | Paying or regulated traffic | Owner-only plan (section C) |

All three serve the same Meta-only pipeline (no OpenAI, Anthropic, or other
providers - CI enforces this). Built for the
[Meta Global AI Developer Hackathon](https://dev.meta.ai/events/global-hackathon).

## A. Local Docker stack (default)

Full system on your machine: API, review UI, Valkey, OTEL collector, Prometheus.

```powershell
cp .env.example .env
# Edit .env: set META_API_KEY (https://dev.meta.ai/api-keys).
# Set API_KEY for anything shared (SECURITY.md section 2).
docker compose up --build
```

| Service | URL |
|---------|-----|
| Review UI | http://localhost:3000/ |
| API | http://localhost:8000/ (`/healthz`, `/v1/...`) |
| Prometheus | http://localhost:9090/ |
| OTLP | localhost:4317/:4318 |
| Valkey | localhost:6379 |

Validate it:

```powershell
curl.exe -s -o NUL -w "ui=%{http_code}\n" http://localhost:3000/
curl.exe -s http://localhost:8000/healthz
```

Then open the UI, pick a demo fixture, and run one inspection end to end.
Data lives in `./data` (SQLite, 24h TTL). Stop with `docker compose down`.

> UNC checkouts: Docker and some Node tooling fail on network paths. Copy the
> repo to a local drive (or map the drive) before any Docker or npm command.
> Details: [Getting Started](GETTING_STARTED.md), [Troubleshooting](TROUBLESHOOTING.md).

## B. Hugging Face Space demo (public one-link demo)

One Docker container (API plus UI behind nginx on port 7860), built from
`deploy/hf/`. Same pipeline and review UI, demo-grade persistence: history
resets when the Space restarts unless a Storage Bucket is attached.

Live: https://huggingface.co/spaces/monigarr/asset-intelligence (app: https://monigarr-asset-intelligence.hf.space).

Prerequisites (owner, one time):

- HF account with PRO: Docker Spaces on cpu-basic return HTTP 402 without it
  (verified 2026-10-31; Static Spaces are free, Docker Spaces need PRO).
- Space secrets in Settings: META_API_KEY (required), API_KEY (required -
  never the dev default on a public Space), JWT/UI login secrets to enable
  review login. Optional: META_API_TIMEOUT_S=180, model ID and pricing vars.

Push and validate:

1. Validate the image locally (repo root):
   `docker build -f deploy/hf/Dockerfile -t asset-intel-space .`
   `docker run -p 7860:7860 --env-file .env asset-intel-space`
2. Follow `deploy/hf/SYNC_CHECKLIST.md` to sync files to the Space repo and push.
3. Watch the Space build log to Running; repeat the UI plus API checks on the
   live Space URL (UI 200, one inspection, overlay, history row, review).

Know the limits: single uvicorn worker (about a minute per inspection, poor
concurrency), in-memory rate limits, no in-Space Valkey or Prometheus, sleep
behavior follows your Space tier. Keep API_KEY set - an open inference
endpoint behind your Meta key attracts abuse.

## C. Hosted production (owner-led)

Production (managed Postgres, object storage, CD, SSO, SLOs) follows the
owner-only plan `DEPLOYMENT_PRODUCTION_PLAN.md`, which is gitignored and
never committed. Direction matches ARCHITECTURE.md section 8: gateway on
Fly.io or Render, SAM work on serverless GPUs, R2 storage, managed Postgres.
Team members: do not improvise a production deploy - ask the owner for the
current phase and the staging URL.

## Further reading

- [Configuration](CONFIGURATION.md) - every variable, safe defaults.
- [Runbook](RUNBOOK.md) - API, stack, evals, case generation.
- [Troubleshooting](TROUBLESHOOTING.md) - ports, keys, compose, 413s.
- Repo root: PRD.md v1.1 (requirements), ARCHITECTURE.md v1.2 (design),
  SECURITY.md (auth and secrets), DESIGN.md (UI law).
