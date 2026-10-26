# Asset Intelligence — PRD (Hackathon Winner Edition)

- **Project:** Asset Intelligence — Production Multimodal Infrastructure Intelligence Platform
- **Hackathon:** Meta Global AI Developer Hackathon — Oct 26-Nov 4, 2026
- **Track:** Startup / Push the Frontier
- **Version:** 1.0 — Optimized for Judging
- **Owner:** MoniGarr
- **Stack Mandate:** Meta-Only (No OpenAI / Direct Competitors)

## 0. Executive Summary — Why This Wins

**One-liner:** The first open-core platform that gives machines the ability to see, segment, reason, and plan over real-world infrastructure — turning field photos + notes into auditable, evidence-linked maintenance intelligence using Meta's full model stack.

### Hackathon Alignment (Official Scoring):

Finished projects are scored on impact (30%), how creatively they use Meta's AI tools (25%), the demo including its video (25%), and technical depth and execution (20%).

| Judging Criterion | How We Ace It | Weight |
| --- | --- | --- |
| Impact 30% | Addresses $2.3T US deferred infrastructure maintenance backlog. Directly enables municipal crews, utilities, public works. Push the Frontier: "Give a machine a new capability... unlock a better way to understand and control a physical system." | 30% |
| Creative Meta Use 25% | Orchestrates 5 Meta models: SAM 3.1 for defect segmentation, Llama 4 Maverick Vision for multimodal extraction, Muse Spark 1.3 for structured reasoning, Muse Wonder for multi-step maintenance planning, Muse Image for synthetic training data + counterfactual visualization. All via Meta Model API + open-weights on Baseten/Modal. | 25% |
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
- **Pipeline:** SAM 3.1 → Llama 4 Maverick Vision → Muse Spark → Muse Wonder → Validator → Human Review
- **Output:** Evidence-linked JSON with SAM masks, uncertainty, missing info, and draft next steps — never an auto-executed work order.

### Why Only Meta Can Do This (No OpenAI Needed)

| Capability | Meta Model | Why Meta, Not Competitor |
| --- | --- | --- |
| Zero-shot defect segmentation | SAM 3.1 via Meta Model API | State-of-art instance segmentation, no training needed for cracks/corrosion/vegetation |
| Long-context multimodal fusion (10M tokens Scout, 1M Maverick) | Llama 4 Maverick 17B-128E Vision | Handles 20 photos + 10 years maintenance history in one context |
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
- Llama 4 Maverick Vision compares note vs image: extracts "crack, seepage, top edge"
- Muse Spark produces structured observation with evidence pointers: evidence: [{source: "image_0", mask_id: "mask_1"}, {source: "maintenance_note", span: [0,32]}]
- Muse Wonder flags: missing dimensions, no inspection date, discrepancy (note says 2ft but no scale reference)
- Validator enforces schema + human_review_required=true
- Review UI shows image with SAM overlay, side-by-side JSON, missing info checklist
- Coordinator approves → optional adapter posts to Manage Assets via mTLS

**Time:** < 8 sec p95, cost: <$0.12 per inspection.

## 5. Functional Requirements — Production Grade

| ID | Requirement | Priority | Meta Model |
| --- | --- | --- | --- |
| FR-01 | Accept 1-5 images (JPEG/PNG, <15MB) + text note + asset metadata | Must | SAM 3.1, Llama 4 Vision |
| FR-02 | SAM 3.1 segmentation of defects with masks, bboxes, confidence | Must | SAM 3.1 |
| FR-03 | Multimodal extraction: observations, asset_type, condition | Must | Llama 4 Maverick Vision |
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
    "sam_model": "sam-3.1",
    "vision_model": "llama-4-maverick-vision",
    "reasoning_model": "claude-like? NO - use Muse Spark 1.3",
    "reasoning_model_id": "muse-spark-1.3",
    "planning_model_id": "muse-wonder",
    "timestamp": "2026-10-26T..."
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
  "cost_cents": 11
}
```

**Rules:**

- Every observation MUST have >=1 evidence pointer
- No invented measurements
- human_review_required always true for MVP
- Include cost, model IDs for reproducibility

## 7. Non-Functional — Startup Track Production Checklist

**Reliability:**

- Bounded retries (max 2), circuit breaker, idempotent request_id
- p95 < 8s, p99 < 15s

**Security (No OpenAI proxy):**

- Secrets via env, never committed. SBOM generated.
- Images validated, stripped EXIF GPS before logging
- Hosted inference disclosure: inputs sent to Meta Model API — no sensitive PII in demo

**Scalability:**

- Stateless FastAPI, horizontal via Modal + Baseten endpoints for Llama 4 open-weights fallback
- Queue for batch mode

**Observability:**

- OpenTelemetry traces per model call, Prometheus metrics: latency, validation_fail_rate, sam_mask_count
- Structured logs with request_id, no raw images in logs

**Cost Control:**

- Token + segmentation metering, synthetic fixtures for tests, Llama 4 Scout for low-cost path

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
- 50/50 synthetic cases schema-valid, 0 fabricated measurements
- Missing info detection precision >85%
- Demo video <2min shows full flow with SAM overlay
- No OpenAI SDK imported (grep check in CI)
- Cost per inspection logged, avg <$0.15

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
- **30-55s:** SAM masks appear, Llama extracts, Spark JSON streams, Wonder flags missing tape measure
- **55-80s:** Reviewer UI: click mask, see evidence, approve
- **80-90s:** Architecture: 5 Meta models, open-core, production-ready

## 12. Milestones — 10-Day Sprint

- **Day 1-2:** API connectivity (SAM 3.1 + Llama 4 Maverick via Meta Model API), env config
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

**Agent Instruction:** Build exactly this PRD. Use only Meta Model API (muse-spark-1.3, muse-wonder, llama-4-maverick, llama-4-scout, sam-3.1, muse-image). No openai package. Provide make verify-meta-only that fails if openai import found. Log model IDs and cost per request.
