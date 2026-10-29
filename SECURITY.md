# Security Policy — Asset Intelligence

- **Status:** Hackathon prototype posture, verified against code on 2026-10-27.
- **Source of truth:** `PRD.md` §7 (Security), §14 (Safety & Human Oversight);
  `ARCHITECTURE.md` §2 (Principles), §3 (Trust Boundaries), §9 (Security &
  Privacy), §11 (Reliability & Failure Handling).
- **Owner:** MoniGarr. Report vulnerabilities via GitHub Issues (no private
  intake process is established yet).

## 1. Trust boundaries (ARCH §3)

| Zone | Contains | Rule |
| --- | --- | --- |
| Public repo | OSS code, schemas, synthetic data | No secrets, no real PII, no private-core code — enforced by CI (see §6) |
| Meta Model API | De-identified inspection evidence per request | Hosted-inference disclosure in `README.md`: inputs leave our servers; no sensitive PII in demos |
| Private core (Manage Assets) | Proprietary systems | Never in this repo; future adapter only, mTLS + scoped, disabled by default |

## 2. Authentication and authorization (FR-09, ARCH §6)

- API routes require `X-API-Key`, compared with `secrets.compare_digest`;
  missing/invalid keys get a bare 401 (`app/api/main.py`, `app/api/security.py`).
- When `API_KEY` is unset the server uses a documented dev key and logs a
  warning. Local-demo convenience only — set `API_KEY` (see `.env.example`)
  for anything shared.
- `/healthz` and `/metrics` are unauthenticated by design; they expose no
  inspection data.
- JWT issue/refresh (HS256 access + rotating refresh, Argon2 password check) is implemented (`POST /v1/auth/*`); SSO stays deferred post-hackathon.
- Rate limiting: 60/minute per key (slowapi; in-memory solo, Valkey-backed in compose) with 429 responses;
  run one worker per container and scale via replicas (`docker-compose.yml`).

## 3. Input handling (ARCH §4.1, `app/api/adapter.py`)

- 1–5 images, JPEG/PNG/WebP only, ≤15 MB each; note ≤10,000 chars;
  `asset_meta` must be a JSON object; review notes ≤2,000 chars.
- Every image is orientation-normalized and **re-encoded without EXIF (GPS
  included)** before anything downstream sees it; oversize uploads get 413,
  other caller mistakes get 400 — never 500s.
- System prompts are code constants; caller notes travel as user-message
  data, never as instructions (`app/orchestrator/spark.py`).

## 4. Data minimization and privacy (PRD §7, ARCH §9)

- Storage keeps only the validated result, rendered PNG overlays, and review
  state -- never raw uploads or notes (`app/api/store.py`).
- SQLite records expire after 24 h (opportunistic TTL prune on access).
- Logs carry `request_id`, counts, and cost -- never image bytes
  (`app/api/main.py` `inspection_complete`). Prometheus labels use route
  templates, not raw paths, so request IDs never become label cardinality
  (`app/api/telemetry.py`).
- Eval data is synthetic only (Muse Image, fixed synthetic IDs/dates);
  nothing in `eval/` may be mistaken for real inspections.
- Uploads are re-encoded at ingress, which drops EXIF (GPS included) before
  anything downstream — logs, store, or Meta API calls — sees it
  (`app/api/adapter.py`).
- Reported `cost_cents` are estimates from console rate cards for budgeting;
  the Meta console invoice is the billed truth (`app/gateway/pricing.py`).

## 5. Model-output safety (PRD §14, ARCH §2)

- Fail-closed Pydantic v2 validator: invalid or un-evidenced output is
  rejected with 422 field errors, never partially accepted.
- `human_review_required` is always true; the review gate
  (accept/edit/reject) is mandatory — no auto-executed work orders.
- Certification language (safe/unsafe declarations, compliance claims) is
  rejected by the validator and probed by 5 adversarial eval cases that must
  refuse (`eval/run.py`, `tests/test_eval.py`).
- No invented measurements: numeric dimensions require a measurement
  reference in evidence; the harness independently audits unfounded numbers.

## 6. Secrets management (ARCH §9)

- Secrets live in `.env` (gitignored) or real environment variables; missing
  `META_API_KEY` fails closed with a 500 that names the variable, never the
  value (ARCH §11).
- `.env.example` holds placeholders only. CI enforces: gitleaks + TruffleHog
  secret scans, a tracked-`.env`/key-file check, a placeholder sanity check,
  and a private-core boundary check (`.github/workflows/secret-scan.yml`).
- Meta-only stack is CI-enforced (grep) and unit-tested
  (`tests/test_no_openai.py`): no `openai`/`anthropic`/`cohere` SDKs.

## 7. Network and upstream calls (`app/gateway/meta_client.py`)

- Bearer key sent in the `Authorization` header only, over HTTPS with the
  HTTP client's default TLS verification; no custom CA or pinning.
- 15 s default timeout (`META_API_TIMEOUT_S` override — required for image
  generation, which exceeds 15 s), max 2 retries with backoff, 429 mapped to
  429 + `Retry-After` for callers.
- Upstream failures map to 502/504; upstream auth failures map to a 500 that
  says to check the server key without leaking anything.

## 8. Supply chain and CI (`.github/workflows/ci.yml`)

- Python: `pip install -r requirements.txt -r requirements-dev.txt`, then
  ruff, pytest with a 70 % coverage gate, and the meta-only check.
- UI: `npm ci` against the committed `package-lock.json`, then build + tests.
- Docker: compose config validation + API image build on every push/PR.
- SBOM: `pip freeze > sbom.txt` uploaded as a CI artifact (ARCH §9).

## 9. Deployment notes (`docker-compose.yml`, ARCH §8)

- `docker compose up` runs API :8000, UI :3000, OTEL collector, Prometheus.
  The `./data` SQLite volume is gitignored.
- Object storage (MinIO per ARCH §8, Postgres/R2 in production) is **not
  yet wired**: MinIO remains out of compose because `minio/minio` pulls are
  still denied by Docker Hub (last checked 2026-10-27); storage stays SQLite
  until access is restored. `docker login` on the operator side is the first
  remediation to try.

## 10. Known gaps (honest list, not roadmap promises)

- SSO and Postgres/MinIO persistence: designed (ARCH §5–§6) but not implemented.
- No `Llama 4 Maverick/Scout` vision models exist on the live Meta Model API
  catalog (verified 2026-10-27: 9 models, none Llama); the vision step uses
  `muse-spark-1.3` per the owner-blessed 2026-10-27 decision (see §11).
- SAM 3.1 is served over `POST /v1/responses` with a special-token
  grammar (see §11); the rewire shipped 2026-10-27 in
  `app/gateway/sam_responses.py` and is verified live end to end.
- Live-verified model IDs differ from early placeholders: `muse-image-1.0`
  (not `muse-image`) and `muse-wonder-1.0` (not `muse-wonder`); `.env.example`
  reflects the verified IDs.
- `python-multipart` file uploads are held in memory during normalization;
  the 15 MB cap bounds this, but disk-spooled uploads are future work.

## 11. Live API notes (verified 2026-10-27, not from memory)

- Base URL `https://api.meta.ai/v1` + Bearer key + OpenAI-compatible error
  shapes confirmed against the live API.
- `GET /v1/models` returned 9 models: `muse-image-1.0`, `muse-spark-1.1`,
  `muse-spark-1.2`, `muse-spark-1.2-contributor`, `muse-spark-1.3`,
  `muse-spark-1.3-contributor`, `muse-voice-transcribe-1.0`,
  `muse-wonder-1.0`, `sam-3.1`.
- `POST /v1/images/generations` works (2/2 eval images rendered).
- `POST /v1/segment` does not exist (bare 404). Per official docs
  (`dev.meta.ai/docs/media-segmentation`, `/docs/sam/*`), SAM 3.1 is called
  via the Responses API with `input_text` + `input_image` parts; masks come
  back base85-encoded in a documented grammar, decodable with the official
  zero-dependency `meta_sam_parser` package. Rewiring `app/sam_service/` to
  that contract shipped 2026-10-27 in `app/gateway/sam_responses.py`.
- Per official docs (`dev.meta.ai/docs/image-understanding`), Muse Spark
  reads images via Responses or chat completions; no Llama vision path is
  documented on this API. The vision step uses `muse-spark-1.3`
  (owner-blessed 2026-10-27 deviation from ARCH §4.3).
- Full live 50-case eval (2026-10-27, synthetic cases): 41 ok, 9
  validator-rejected, 0 transport errors, fabrication rate 0.0. The 5
  adversarial cases all produced certification language that the validator
  caught (defense in depth held; 1 counted non-refused on a different rule).
  Live latency p95 is 66s against the 8s production target — tracked
  optimization work (parallel calls, smaller uploads), not a correctness
  defect. Report: `%TEMP%\eval-live\report.json`.
