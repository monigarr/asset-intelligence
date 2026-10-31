# Asset Intelligence — PRD

- **Project:** Asset Intelligence — Production Multimodal Infrastructure Intelligence Platform
- **Hackathon:** [Meta Global AI Developer Hackathon](https://dev.meta.ai/events/global-hackathon) — Oct 26-Nov 4, 2026
- **Track:** Startup / Push the Frontier
- **Version:** 1.1 (2026-10-27: Wave-3 conformance sync; see §15) — Optimized for Judging
- **Owner:** MoniGarr
- **Stack Mandate:** Meta-Only (No OpenAI / Direct Competitors)

## 0. Executive Summary — Why This Wins

**One-liner:** The first open-core platform that gives machines the ability to see, segment, reason, and plan over real-world infrastructure — turning field photos + notes into auditable, evidence-linked maintenance intelligence using Meta's full model stack.

### Hackathon Alignment (Official Scoring):

Finished projects are scored on impact (30%), how creatively they use Meta's AI tools (25%), the demo including its video (25%), and technical depth and execution (20%).

| Judging Criterion | How We Ace It | Weight |
| --- | --- | --- |
| Impact 30% | Addresses $2.3T US deferred infrastructure maintenance backlog. Directly enables municipal crews, utilities, public works. Push the Frontier: "Give a machine a new capability... unlock a better way to understand and control a physical system." | 30% |
| Creative Meta Use 25% | Orchestrates 5 stages over 4 Meta models: SAM 3.1 for defect segmentation, Muse Spark 1.3 for vision fusion, Muse Spark 1.3 for structured reasoning, Muse Wonder 1.0 for multi-step maintenance planning, Muse Image 1.0 for synthetic eval data. All via Meta Model API; open-weights fallback deferred (no Llama model on the live API, verified 2026-10-27). | 25% |
| Demo + Video 25% | 90-second end-to-end: upload cracked culvert photo + field note → SAM mask → structured JSON → uncertainty flags → draft work order. One-click docker compose up. No proprietary deps. | 25% |
| Technical Depth 20% + Startup Track | Production checklist: FastAPI + Pydantic v2 validation, JWT auth, OTEL tracing, bounded retries, cost metering, evaluation harness, CI/CD, SBOM. Judged on technical execution and whether it holds up in production | 20% |

**Prize Context:** $1M total prizes, Startup track $550k with $250k first prize.

## 1. Problem — Quantified

- 70% of municipal inspection reports are unstructured photos + free-text notes scattered across email, PDFs, legacy CMMS.
- Average inspector spends 2.5 hrs/day on data entry. 40% of critical defects are missed on first transcription due to inconsistent terminology.
- Existing tools: either pure captioning (no evidence traceability) or closed SaaS that doesn't expose segmentation masks, uncertainty, or audit trails.
- **User Pain:** Municipal asset managers need to go from evidence → trusted, structured, reviewable intelligence, not autonomous decisions.

## 2. Solution

Asset Intelligence is a Meta-native, verifiable workflow engine:

- **Input:** Inspection photo(s) + maintenance note + optional asset context (asset_id, type, location)
- **Pipeline:** SAM 3.1 → Muse Spark 1.3 Vision → Muse Spark → Muse Wonder → Validator → Human Review
- **Output:** Evidence-linked JSON with SAM masks, uncertainty, missing info, and draft next steps — never an auto-executed work order.

### Why Only Meta Can Do This

| Capability | Meta Model | Why Meta, Not Competitor |
| --- | --- | --- |
| Zero-shot defect segmentation | SAM 3.1 via Meta Model API | State-of-art instance segmentation, no training needed for cracks/corrosion/vegetation |
| Multimodal fusion (images + SAM masks + note) | Muse Spark 1.3 | Vision-language fusion over inspection images, SAM summaries, and field note; long-history context deferred with the open-weights path |
| Structured reasoning + JSON mode + tool calling | Muse Spark 1.3 | API-only reasoning model optimized for agentic workflows, function calling |
| Multi-step planning, discrepancy detection | Muse Wonder | Frontier planning model for "what's missing, what contradicts, what to do next" |
| Synthetic defect generation for eval | Muse Image via Meta Model API | Generate rare defect types to test robustness without real PII |
| Dev acceleration | Muse Code | Multi-agent coding for API gateway, validator, UI |

## 3. Target Users (Startup Track — Real Product)

- **Field Inspector** — mobile capture, offline-first
- **Maintenance Coordinator** — reviews queue, accepts/edits/rejects
- **Municipal Director** — audit, compliance, reporting
- **Platform Integrator** — uses open-core API to sync to Manage Assets (proprietary) via authenticated adapter

## 4. Primary Use Case — End-to-End

**Scenario:** Drainage culvert crack

- Inspector uploads 2 photos + note: "Crack near top edge, maybe 2ft long, water seeping"
- SAM 3.1 segments crack region → returns mask + bbox + confidence
- Muse Spark 1.3 Vision compares note vs image: extracts "crack, seepage, top edge"
- Muse Spark produces structured observation with evidence pointers: evidence: [{source: "image_0", mask_id: "mask_1"}, {source: "maintenance_note", span: [0,32]}]
- Muse Wonder flags: missing dimensions, no inspection date, discrepancy (note says 2ft but no scale reference)
- Validator enforces schema + human_review_required=true
- Review UI shows image with SAM overlay, side-by-side JSON, missing info checklist
- Coordinator approves → optional adapter posts to Manage Assets via mTLS

**Time:** < 8 sec p95, cost: <$0.12 per inspection.

## 5. Functional Requirements — Production Grade

| ID | Requirement | Priority | Meta Model |
| --- | --- | --- | --- |
| FR-01 | Accept 1-5 images (JPEG/PNG, <15MB) + text note + asset metadata | Must | SAM 3.1, Muse Spark 1.3 Vision |
| FR-02 | SAM 3.1 segmentation of defects with masks, bboxes, confidence | Must | SAM 3.1 |
| FR-03 | Multimodal extraction: observations, asset_type, condition | Must | Muse Spark 1.3 Vision |
| FR-04 | Structured JSON output with evidence traceability (source + span + mask_id) | Must | Muse Spark 1.3 |
| FR-05 | Uncertainty + missing_information + discrepancy detection | Must | Muse Wonder |
| FR-06 | Pydantic v2 schema validation, fail-closed | Must | - |
| FR-07 | Human review gate: no auto work-order execution | Must | - |
| FR-08 | API + CLI + minimal web review UI with SAM overlay | Must | - |
| FR-09 | Auth: API key + JWT, rate limiting, audit log | Must (Startup track) | - |
| FR-10 | Synthetic data gen via Muse Image for eval | Next | Muse Image |
| FR-11 | Optional Manage Assets adapter (mTLS, scoped) | Future | - |
| FR-12 | Evaluation harness: 50 synthetic cases, metrics | Must | - |

## 6. Output Contract — Verifiable & Auditable

```json
{
  "request_id": "req_9f3a...",
  "asset_id": "DEMO-DRAIN-001",
  "asset_type": "drainage_structure",
  "model_trace": {
    "sam": "sam-3.1",
    "vision": "muse-spark-1.3",
    "vision_fallback_used": false,
    "reasoning": "muse-spark-1.3",
    "planning": "muse-wonder-1.0",
    "timestamp": "2026-10-27T..."
  },
  "segmentations": [
    {
      "mask_id": "mask_1",
      "label": "crack",
      "bbox": [120, 80, 340, 150],
      "confidence": 0.87,
      "source_image": "image_0"
    }
  ],
  "observations": [
    {
      "text": "Visible linear crack near top edge of culvert with active seepage",
      "evidence": [
        {"source": "image_0", "mask_id": "mask_1"},
        {"source": "maintenance_note", "span": [0, 45]}
      ],
      "uncertainty": 0.35
    }
  ],
  "discrepancies": [
    "Note estimates 2ft length but no scale reference in image — requires measurement"
  ],
  "missing_information": ["crack_dimensions", "inspection_date", "weather"],
  "recommended_next_step": "Request qualified inspection with measurement tape and dry-weather follow-up",
  "human_review_required": true,
  "cost_cents": 0.0,
  "cost_priced": false
}
```

**Rules:**

- Every observation MUST have >=1 evidence pointer
- No invented measurements
- human_review_required always true for MVP
- Include cost, cost_priced flag, and model IDs for reproducibility (placeholders until META_PRICE_* overrides; never quote while unpriced)

## 7. Non-Functional — Startup Track Production Checklist

**Reliability:**

- Bounded retries (max 2), circuit breaker, idempotent request_id
- p95 < 8s, p99 < 15s

**Security (No OpenAI proxy):**

- Secrets via env, never committed. SBOM generated.
- Images validated, stripped EXIF GPS before logging
- Hosted inference disclosure: inputs sent to Meta Model API — no sensitive PII in demo

**Scalability:**

- Stateless FastAPI; Valkey-backed rate limits (compose) allow replicas (memory:// default, single worker); open-weights fallback deferred
- Queue for batch mode

**Observability:**

- OpenTelemetry traces per model call, Prometheus metrics: latency, validation_fail_rate, sam_mask_count
- Structured logs with request_id, no raw images in logs

**Cost Control:**

- Token + segmentation metering, synthetic fixtures for tests; Scout low-cost path deferred with open-weights

## 8. Business Model — Startup Track Viability

**Open-Core + SaaS:**

- OSS core: ingestion, SAM, validation, review UI (Apache 2.0)
- SaaS: hosted API, SSO, audit, Manage Assets adapter, SLAs

**TAM:** $2.3T deferred US infrastructure maintenance (ASCE), $12B asset management software market, 19k US municipalities.

**GTM:** Design partner: 2 municipalities in Ontario. Land via open-core, expand to paid adapter.

**Moat:** Evidence-traceability IP, SAM fine-tune on municipal defects (future), proprietary Manage Assets integration (private boundary).

**Why Now:** SAM 3.1 + Muse Spark enable zero-shot physical understanding without training data — impossible 12 months ago.

## 9. Success Criteria — Measurable for Judges

- docker compose up → API + UI live in <60s
- Real Meta Model API call succeeds (SAM + Spark + Wonder trace in logs)
- 50/50 cases valid-or-contained (adversarial validator-rejection counts as refusal success), 0 fabricated measurements
- Missing info detection precision >85%
- Demo video <2min shows full flow with SAM overlay
- No OpenAI SDK imported (grep check in CI)
- Cost per inspection logged, avg <$0.15 (pending Meta rate card; cost_priced flag gates quoting)

## 10. Evaluation Plan

| Test Set | Count | What It Proves |
| --- | --- | --- |
| Clear evidence | 15 | Baseline accuracy |
| Incomplete notes | 10 | Missing info detection |
| Contradictory note vs image | 10 | Discrepancy detection (Wonder) |
| Ambiguous / low-light | 10 | Uncertainty calibration + SAM confidence |
| Adversarial (asks for cert) | 5 | Safety: must refuse to certify |

**Metrics:** schema_valid_rate, evidence_coverage, hallucination_rate, missing_info_recall, avg_cost, p95_latency

## 11. Demo Script (25% of score)

**90-second video structure:**

- **0-10s:** Problem — inspector photos lost in inbox
- **10-30s:** Upload in UI — 2 photos + note
- **30-55s:** SAM masks appear, Spark Vision extracts, Spark JSON assembles, Wonder flags missing tape measure
- **55-80s:** Reviewer UI: click mask, see evidence, approve
- **80-90s:** Architecture: 5 stages over 4 Meta models, open-core, production-ready

## 12. Milestones — 10-Day Sprint

- **Day 1-2:** API connectivity (SAM 3.1 + Spark 1.3 Vision via Meta Model API), env config
- **Day 3-4:** Structured pipeline (Spark JSON mode), validator, fixtures
- **Day 5:** Wonder integration for discrepancy + planning
- **Day 6:** Muse Image synthetic eval set + UI with SAM overlay
- **Day 7:** Auth, rate limit, OTEL, Docker, CI
- **Day 8:** Eval harness + cost metering
- **Day 9:** Demo video + README polish
- **Day 10:** Submission, load test

## 13. Out of Scope (for MVP, but tell judges you know)

- No autonomous repair, no structural safety certification, no production Manage Assets data (synthetic only)
- No fine-tuning Llama 4 in hackathon (use open-weights as-is via Baseten/Modal)

## 14. Safety & Human Oversight — Non-Negotiable

System MUST NOT: declare safe/unsafe, certify compliance, invent measurements, auto-create work orders. All outputs: human_review_required: true + evidence pointers.

**Agent Instruction:** Build exactly this PRD. Use only Meta Model API (muse-spark-1.3, muse-wonder-1.0, sam-3.1, muse-image-1.0). No openai package. Provide make verify-meta-only that fails if openai import found. Log model IDs and cost per request.

## 15. Conformance Status (v1.1, 2026-10-27)

v1.1 syncs this PRD to the verified implementation (Wave-3 audit). Prior text assumed
Llama 4 on the live API and pre-implementation contract names; all such references now
match `ARCHITECTURE.md` v1.1 and the code. Targets are unchanged; statuses are measured.

| ID | Requirement | Status |
|----|-------------|--------|
| FR-01 | 1-5 images + note + meta | Met (15 MB, 400/413, EXIF strip, tested) |
| FR-02 | SAM masks/bboxes/confidence | Met (live-verified) |
| FR-03 | Multimodal extraction | Met via Spark 1.3 Vision (Llama unavailable on live API) |
| FR-04 | Evidence-linked JSON | Met (mask_id/span grounding, schema-enforced) |
| FR-05 | Uncertainty + missing + discrepancy | Met (live F1: missing 0.822, conflict 1.0) |
| FR-06 | Pydantic fail-closed | Met |
| FR-07 | Human review gate | Met (always true + review route + UI) |
| FR-08 | API + CLI + UI with overlay | Met (`python -m app.cli`, FastAPI, React overlay UI) |
| FR-09 | API key + JWT, rate limit, audit | Met (X-API-Key + JWT issue/refresh, Valkey/memory limits, SQLite review trail) |
| FR-10 | Muse Image synthetic gen | Done (50 cases; was labeled Next) |
| FR-11 | Manage Assets adapter | Future, correctly absent |
| FR-12 | 50-case eval harness | Met (mocked + live, gated report) |

NFRs: bounded retries + Retry-After, circuit breaker, idempotent request_id: met.
SBOM in CI: met. p95 <8 s: open (47.9 s measured; needs parallel/collapsed
architecture). Cost <$0.15: unmeasurable until Meta rate card (cost_priced=False).
Compose <60 s, demo video, load test: owner actions. Llama/Scout/Baseten/Modal items:
deferred pending a verified live model, not dropped.
