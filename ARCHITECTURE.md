# Architecture — Asset Intelligence (Winner Edition)

- **Status:** Production-Ready Prototype for Meta Global AI Hackathon
- **Track:** Startup / Push the Frontier
- **Version:** 1.2 (2026-10-29: Valkey/request-id errata; see §16)
- **Date:** 2026-10-29
- **Mandate:** Meta-Only Stack — Zero OpenAI Dependency

## 1. Purpose & Hackathon Fit

Asset Intelligence transforms physical infrastructure inspection evidence (photos + notes) into structured, auditable intelligence using an orchestrated Meta supermodel pipeline.

**Judging:** impact 30%, creative use of Meta's tools 25%, demo+video 25%, technical depth 20%. Startup track judged on technical execution and whether it holds up in production.

**Theme:** Push the Frontier — "Give a machine a new capability... unlock a better way to understand and control a physical system". We give vision models physical defect understanding + evidence-grounded reasoning.

## 2. Principles

- **Meta-First:** Every inference via Meta Model API — Muse Spark series, Muse Wonder, Muse Image, SAM 3.1. Llama 4 open-weights via partners: deferred (no live Llama model, verified 2026-10-27).
- **Production-First:** Stateless, 12-factor, observable, secure by default — what Startup track demands.
- **Verifiable:** SAM masks + evidence pointers + uncertainty > pure captioning.
- **Fail-Closed:** Invalid JSON, low SAM confidence, missing evidence → error, not hallucination.
- **Human Gate:** No autonomous work order. human_review_required=true enforced in validator.
- **Private Core Boundary:** Manage Assets proprietary — only via explicit mTLS adapter, optional, not required for demo.

## 3. System Context

```mermaid
flowchart TD
    U[Inspector / Reviewer]
    WEB[Review UI - SAM Overlay]
    API[FastAPI Gateway - Auth, Rate Limit]
    ORCH[Inspection Orchestrator]
    V[Validator - Pydantic v2]
    SAM[SAM 3.1 - Meta Model API - Segmentation]
    VLM[Muse Spark 1.3 Vision - Multimodal Extraction]
    REASON[Muse Spark 1.3 - Structured Reasoning]
    PLAN[Muse Wonder 1.0 - Discrepancy & Planning]
    SYN[Muse Image - Synthetic Data Gen]
    ADAPT[Manage Assets Adapter - Optional mTLS]
    CORE[Proprietary Manage Assets Core - Private]
    U --> WEB --> API --> ORCH
    ORCH --> SAM --> VLM --> REASON --> PLAN --> V
    V --> WEB
    SYN -. eval data .-> ORCH
    ORCH -. optional context .-> ADAPT -.-> CORE
```

**Trust Boundaries:**

- Public Repo: OSS code, schemas, synthetic data only
- Meta Model API: receives only de-identified inspection evidence, disclosure in docs
- Private: never in public repo, adapter disabled by default

## 4. Logical Components — With Meta Model Assignments

### 4.1 Input Adapter

- Accepts: 1-5 images (JPEG/PNG/WebP, 15MB max), note (UTF-8, 10k chars), asset_meta
- Sanitizes: EXIF strip, MIME sniff, NSFW check (via Llama Guard? Future)
- Normalizes to InspectionRequest {request_id, images[], note, asset_meta, timestamp}
- Rejects oversize, unsupported types with 400

### 4.2 SAM 3.1 Segmentation Service — Creative Use #1

**Model:** sam-3.1 via Meta Model API

**Responsibility:**

- Zero-shot segmentation of defects: crack, corrosion, spall, vegetation, water intrusion
- Returns: masks (RLE), bboxes, confidence, label
- Prompting: text prompts ["crack", "corrosion", "water seepage"] + automatic mask generation

**Failure:** if confidence <0.4, flag uncertainty: high, require human

**Why SAM 3.1 wins points:** No training data needed, physical world understanding, instance-level evidence.

### 4.3 Muse Spark 1.3 Vision Extractor — Creative Use #2

**Models:** muse-spark-1.3 (primary and fallback; identical pending a verified replacement -- no Llama model on the live API)

**Responsibility:**

- Fuse images + SAM masks + note + asset context (downscaled to 768 px for the vision call; no coordinates leave vision)
- Extract: asset_type, condition_tags, visible symptoms
- Output intermediate: VisionObservation {observations[], evidence_refs[]}

**Config:**

```text
META_API_BASE_URL=https://api.meta.ai/v1
VISION_MODEL_ID=muse-spark-1.3
FALLBACK_VISION_MODEL_ID=muse-spark-1.3
VISION_MAX_IMAGES=5
VISION_MAX_DIM=768
```

### 4.4 Muse Spark 1.3 Reasoning Gateway — Creative Use #3

**Model:** muse-spark-1.3 (reasoning, coding, agentic)

**Responsibility:**

- System prompt: "You are infrastructure inspection analyst. Return ONLY valid JSON per schema. Every observation must cite evidence: image index + mask_id or note span. Never invent measurements."
- JSON mode (json_schema response format) for schema enforcement
- Handles auth, timeout (15s), bounded retry (2), rate limit parsing
- Logs: model_id, latency, token usage, cost

**Prompt Contract:**

```python
system = """Evidence before inference. Explicit uncertainty over false precision."""
user = f"""
IMAGES: {image_refs} with SAM masks {sam_results}
NOTE: {note}
ASSET_META: {asset_meta}
TASK: Produce JSON matching schema. If dimension missing, list in missing_information.
"""
```

### 4.5 Muse Wonder Planner — Creative Use #4

**Model:** muse-wonder-1.0

**Responsibility:**

- Multi-step reasoning: "Given observations + history, what contradicts? What's missing for a qualified decision? What is safest next step that is NOT a certification?"
- Detects: contradictory text vs image (note says dry, image shows seepage), missing scale, missing date/weather
- Generates: discrepancies[], missing_information[], recommended_next_step (non-certifying)

### 4.6 Muse Image Synthetic Generator — Creative Use #5

**Model:** muse-image-1.0 via Meta Model API

**Responsibility:**

- Generate 50 synthetic defect images for eval: "concrete culvert with 2ft longitudinal crack, overcast, muddy"
- Used ONLY for testing, not training. Ensures no real PII needed.
- Also: counterfactual "what repaired looks like" for review UI (future)

### 4.7 Output Validator — Production Gate

**Tech:** Pydantic v2 + JSON Schema 2020-12

**Rules:**

- Required: asset_id, observations[], evidence[], human_review_required=true
- Every observation.evidence must reference valid image or mask_id
- uncertainty field always required (stricter than the <0.6 trigger)
- No numeric dimensions unless evidence contains measurement reference
- Fail-closed: invalid → 422 with field-level errors, no partial acceptance

### 4.8 Evidence & Review Layer

- **API:** GET /v1/inspections/{request_id}, POST /v1/inspections/{id}/review {decision: accept|edit|reject, note?} (+ /v1/auth/* JWT, /healthz, /metrics)
- **UI:** React minimal + Canvas for SAM mask overlay, evidence click-to-highlight, missing info checklist
- **CLI:** python -m app.cli inspect --image crack.jpg --note "crack near top" (exit 0/1/2; --out, --overlay-dir) → streams JSON + mask preview

### 4.9 Optional Manage Assets Adapter (Disabled by Default)

- mTLS client cert, scoped OAuth2, allowlist endpoints
- Translates public schema → private API contract (documented only when authorized)
- Data minimization: only sends approved fields after human review
- Demo runs WITHOUT this — satisfies hackathon public repo rule.

## 5. Detailed Request Flow — 8 Steps, 5 Meta Models

- **Ingress:** POST /v1/inspections → Auth (API key) → Rate limit (Valkey/memory) → InputAdapter validates → generates request_id (`req_` + 24 hex)
- **SAM:** Images → SAM 3.1 → masks + bboxes (parallel per image; 11 s p95 measured live 2026-10-27, see live_reports/)
- **Vision:** Images + masks + note → Muse Spark 1.3 Vision → vision_observations
- **Reasoning:** vision_observations + masks → Muse Spark 1.3 → draft JSON (JSON mode)
- **Planning:** draft + vision → Muse Wonder → discrepancies + missing + next step
- **Validation:** Pydantic validator → if fail, return 422 with trace; if pass, attach cost + model_trace
- **Persistence (ephemeral for demo):** SQLite + overlay/original BLOBs, 24h TTL, no PII logging (MinIO returns with M3)
- **Review:** UI polls or SSE streams result, shows SAM overlay, human approves
- **Total cost tracked:** cost_cents = sam_tokens + vision_tokens + spark_tokens + wonder_tokens

## 6. Tech Stack — Meta-Native, Production-Ready

| Layer | Choice | Why |
| --- | --- | --- |
| API | FastAPI, Python 3.12, Uvicorn | Async, Pydantic v2, OpenAPI auto |
| Meta Inference | Hand-rolled httpx gateway (tenacity retry, breaker) | No official SDK; supports Spark, Wonder, SAM 3.1, Muse Image |
| Open-weights fallback | Deferred (no live Llama model) | Was: Scout/Maverick via partners; re-add when verified |
| Validation | Pydantic v2, JSON Schema | Fail-closed |
| Auth | X-API-Key + JWT issue/refresh (HS256, Argon2) | Bearer or key; SSO post-hackathon |
| Storage | SQLite + overlay/original BLOBs (demo); Postgres/MinIO M3 | Zero cloud dep for local |
| Queue (future) | Modal Queues or Valkey | Batch inspections |
| Observability | OpenTelemetry, Prometheus, stdlib logging | OTEL traces per model call |
| Packaging | Docker, docker-compose, Makefile | docker compose up wins |
| CI | lint, test+coverage, meta-only, SBOM, UI, compose, live slice (keyed) | Startup track demands CI |
| Code Gen | Muse Code agent | Build faster, required by hackathon |

No OpenAI SDK: requirements.txt has httpx, tenacity, pydantic, fastapi (plus pyjwt, argon2-cffi, and the redis client library, which talks to Valkey, for auth/limits) — NOT openai.

## 7. Data Schemas

### InspectionRequest

```json
{
  "request_id": "ulid",
  "images": ["base64 or url"],
  "note": "string",
  "asset_meta": {"asset_id": "string", "asset_type": "string", "location": "optional"}
}
```

### InspectionResult (see PRD for full)

Includes: segmentations[], observations[]{text, evidence[{source, mask_id, span}], uncertainty}, discrepancies[], missing_information[], recommended_next_step, human_review_required, model_trace, cost_cents

## 8. Deployment Architecture

### Local (Default for Demo):

```text
docker compose up
- api: :8000 (FastAPI)
- ui: :3000 (Vite + React)
- otel-collector: :4317
- valkey: :6379 (rate limits; minio returns with M3)
- prometheus: :9090
```

### Production (Startup Vision):

- API on serverless GPUs (SAM) + Fly.io / Render for gateway
- Dedicated model endpoints if open-weights return (was: Baseten Maverick 2M TPM)
- Cloudflare R2 for mask storage, Postgres managed

## 9. Security & Privacy

- **Secrets:** META_API_KEY, API_KEY, JWT_SECRET, UI_PASSWORD_HASH via env, never committed. .env.example contains placeholders only.
- **Image handling:** EXIF GPS stripped, no raw images in logs, masks stored with TTL
- **Prompt injection:** note is treated as data, not instruction; system prompt immutable
- **Hosted inference disclosure:** README states inputs sent to Meta Model API
- **SBOM:** pip freeze > sbom.txt in CI

## 10. Observability & Auditability

**Per request:**

- request_id, model_ids, latency per model, token counts, cost_cents, validation_result, sam_mask_count, human_review_status
- OTEL span: sam.segment, vision.extract, spark.reason, wonder.plan, validate
- Metrics: inspection_requests_total, inspection_validation_failures_total, inspection_request_latency_seconds, inspection_cost_cents

## 11. Reliability & Failure Handling

| Failure | Behavior |
| --- | --- |
| Missing API key | 500 with "META_API_KEY not configured — see README" (no secret leak) |
| SAM 3.1 unavailable | Degraded Spark-vision-only path, flag uncertainty high |
| Rate limit (429) | Exponential backoff 2x, max 2 retries, then 429 to client with Retry-After |
| Sustained 5xx/timeouts | Circuit opens after 5 consecutive failures; 503 + half-open trial after 30 s |
| Invalid JSON from Spark | Validator rejects, logs raw (truncated), returns 422, triggers retry with stricter prompt once |
| Low SAM confidence (<0.4) | Keep mask but set uncertainty 0.9, add to missing_information: "requires human measurement" |
| Image too large | 413, instruct resize |
| Private adapter down | Demo continues, logs warning — public path unaffected |

## 12. Cost Control

- Cost guard: warn over 50c per request (Scout cheap path deferred with open-weights)
- SAM masks cached by image hash (in-memory LRU)
- Eval uses synthetic images from Muse Image (no repeated real inference)
- Budget alert: if cost_cents >50 per request, log warning

## 13. Testing Strategy

**Unit (no API calls):**

- Schema validation, evidence pointer integrity, human_review flag enforcement, injection rejection

**Integration (mocked Meta API):**

- SAM response parsing (incl. breaker), Spark vision fusion, Spark JSON mode, Wonder discrepancy

**Live (separate job, requires META_API_KEY):**

- End-to-end with 5 synthetic clear cases in CI (keyed job), asserts gates pass

**Evaluation (50 cases):**

- As defined in PRD, generates report eval/report.json with metrics table

## 14. Implementation Sequence — 10 Days

- **Day 1-2:** API Connectivity
  - Verify Meta Model API base, model IDs: sam-3.1, muse-spark-1.3, muse-wonder-1.0, muse-image-1.0
  - Implement Meta Model Gateway with auth, timeout, retry
- **Day 3:** SAM Integration
  - SAM service, mask RLE decode, overlay generation
- **Day 4:** Vision + Reasoning
  - Spark 1.3 vision extractor + Spark structured output
- **Day 5:** Wonder + Validation
  - Wonder planner, Pydantic validator, fail-closed logic
- **Day 6:** UI + Synthetic
  - Minimal UI with SAM overlay, Muse Image synthetic gen
- **Day 7:** Production Hardening
  - Auth, rate limit, OTEL, Docker, Makefile, CI, meta-only check, SBOM
- **Day 8:** Eval
  - 50-case harness, report generation
- **Day 9:** Demo Video + Docs
  - Record 90s video, polish README
- **Day 10:** Submission

## 15. ADRs (Updated for Winning)

### ADR-001: Meta-Only Inference

**Decision:** Use only Meta Model API (+ deferred open-weights path). No OpenAI, Anthropic, etc.

**Reason:** Hackathon requires Meta usage, startup track needs defensible stack, avoids competitor dependency.

**Consequence:** Must handle Meta API quirks directly (no SDK), but gains judging points for creative Meta use.

### ADR-002: SAM 3.1 as First-Class Evidence

**Decision:** SAM masks are mandatory evidence, not optional visualization.

**Reason:** Physical system understanding = segmentation, pushes frontier beyond captioning.

### ADR-003: 5-Stage Orchestration > Single Model

**Decision:** SAM → Vision → Spark → Wonder → Image (eval)

**Reason:** Shows technical depth (20% of score) and creative use (25%). Each model does what it does best.

### ADR-004: Local-First Production

**Decision:** docker compose up works offline except Meta API calls.

**Reason:** Judges can run without cloud, but architecture scales to Modal/Baseten for prod.

### ADR-005: Fail-Closed Validation

**Decision:** Pydantic v2 validator rejects anything not fully evidenced.

**Reason:** Trust > coverage for infrastructure — critical for impact score.

**Agent Build Command:** make dev → make test → make eval → make verify-meta-only (greps for openai import) → make demo

## 16. Changelog

- **v1.2 (2026-10-29):** Valkey queue-store erratum (§6), `redis` client-package clarification, `req_`-prefixed request-id format (§5).
- **v1.1 (2026-10-27, Wave-3 audit):** vision is Muse Spark 1.3 (no live Llama
  model); `-1.0` model IDs; `/v1` routes; httpx gateway (no meta-ai-sdk); stdlib
  logging; Valkey (not Redis) rate-limit storage; SQLite + BLOB persistence
  (MinIO M3); measured SAM p95; breaker + budget-guard + strict-retry behaviors;
  JWT issue/refresh; `python -m app.cli`; CI live slice; exact metric names.
- **v1.0 (2026-10-26):** initial hackathon architecture.
