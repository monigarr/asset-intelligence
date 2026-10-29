# AGENT BUILD GUIDE — For AI Coding Agents (Muse Code / etc.)

This is the execution guide for your coding agents. Source of truth: PRD.md + ARCHITECTURE.md + README.md

> Historical build notes (2026-10-26): model IDs and retry/policy details here are stale where they differ from ARCHITECTURE.md — notably, no Llama model exists on the live API (ARCH §4.3), and ARCH retry/Valkey/JWT terms win.

## 0. Golden Rules

- **Meta-Only:** Use only Meta Model API. Allowed models: sam-3.1, llama-4-maverick-17b-128e-vision, llama-4-scout-17b-16e-vision, muse-spark-1.3, muse-wonder, muse-image. Also allowed: Llama 4 open-weights via Baseten/Modal. NEVER import openai, anthropic, cohere. CI will grep and fail.
- **Production First:** Every feature must have: type hints, Pydantic validation, OTEL span, error handling, test, cost logging.
- **Evidence Traceability:** Every observation must cite source: image index + mask_id OR note span. No exceptions.
- **Fail-Closed:** Validator rejects invalid JSON, missing evidence, invented numbers.
- **Human Gate:** human_review_required=true always in MVP.
- **Docker Demo:** docker compose up must work for judges.

## 1. Environment Setup

**.env.example:**

```text
META_API_KEY=
META_API_BASE_URL=https://api.meta.ai/v1
VISION_MODEL_ID=llama-4-maverick-17b-128e-vision
FALLBACK_VISION_MODEL_ID=llama-4-scout-17b-16e-vision
SAM_MODEL_ID=sam-3.1
REASONING_MODEL_ID=muse-spark-1.3
PLANNING_MODEL_ID=muse-wonder
IMAGE_MODEL_ID=muse-image
BASETEN_API_KEY= # optional, from hackathon partner
MODAL_TOKEN= # optional
```

Do NOT commit .env. .env.example has placeholders only.

## 2. Makefile Targets (Must Implement)

```makefile
dev: install pre-commit
run: docker compose up
test: pytest tests/ -v --cov=app
eval: python eval/run.py --cases 50 --report eval/report.json
verify-meta-only: @! grep -r "import openai" --include="*.py" app/ && echo "Meta-only OK"
demo: run # alias
lint: ruff check app/
```

## 3. Implementation Order (10 Days)

### Day 1-2: Gateway

- **File:** `app/gateway/meta_client.py`
- Wrap Meta Model API SDK
- **Methods:** segment(model, image, text_prompts), chat(model, messages, images, response_format), generate_image(model, prompt)
- **Features:** auth header, timeout 15s, retry 2x with backoff, parse 429 Retry-After, log model_id, latency, tokens, cost
- **Test:** tests/test_gateway.py with mocked responses

### Day 3: SAM Service

- `app/sam_service/service.py`
- **Input:** PIL image, text prompts
- Calls gateway.segment
- **Output:** List[Mask {mask_id, rle, bbox, confidence, label}]
- **Also:** overlay.py to draw masks on image for UI
- **Test:** synthetic image

### Day 4: Vision + Reasoning

- `app/vision/extractor.py`: takes images + sam_masks + note → calls Llama 4 Maverick Vision → VisionObservation
- `app/orchestrator/pipeline.py`: orchestrates SAM → Vision → Spark
- Spark prompt: MUST enforce JSON schema, evidence pointers, no invented measurements
- Use response_format={"type":"json_schema", ...} if Meta API supports, else parse and validate

### Day 5: Wonder + Validator

- `app/planner/wonder.py`: takes draft JSON + vision → discrepancies, missing, next_step
- `app/validator/schema.py`: Pydantic v2 models for InspectionResult, with custom validators for evidence refs
- Fail-closed: if any observation.evidence invalid → raise ValidationError

### Day 6: UI + Synthetic Data

- `app/ui/`: Vite React, upload form, canvas overlay for SAM masks, JSON viewer
- `app/synthetic/generator.py`: uses Muse Image to generate 50 defect images for eval (prompts like "concrete culvert longitudinal crack...")
- Save to samples/ + eval/cases/

### Day 7: Production Hardening

- `app/api/main.py`: FastAPI, routes: POST /v1/inspections, GET /v1/inspections/{id}, POST /v1/inspections/{id}/review
- **Auth:** API key middleware (X-API-Key), rate limit (slowapi or redis)
- **OTEL:** instrument every model call
- **Docker:** Dockerfile, docker-compose.yml (api, ui, otel-collector, minio, prometheus)
- **CI:** .github/workflows/ci.yml: lint, test, verify-meta-only, eval (mocked)

### Day 8: Eval Harness

- `eval/run.py`: loads 50 cases, runs pipeline, computes metrics: schema_valid_rate, evidence_coverage, hallucination_rate, missing_recall, cost, latency
- Outputs eval/report.json + eval/report.html with SAM overlays
- Must show 0 hallucinated measurements

### Day 9: Demo + Docs

- Record demo/video.mp4 (90s) — use screen capture of UI
- Polish README.md with badges, quickstart, API example
- Generate SBOM

### Day 10: Submission

- Load test: 10 concurrent requests
- Final checks: docker compose up works, verify-meta-only passes, eval report exists

## 4. Key Code Snippets

### Meta Client (Gateway)

```python
import os, time, httpx
from tenacity import retry, stop_after_attempt, wait_exponential
class MetaClient:
    def __init__(self):
        self.base = os.getenv("META_API_BASE_URL")
        self.key = os.getenv("META_API_KEY")
        assert self.key, "META_API_KEY missing"
    @retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=1, min=1, max=4))
    def segment(self, model_id, image_bytes, text_prompts):
        # call Meta Model API SAM 3.1
        # return masks
        pass
```

### Validator — Evidence Check

```python
from pydantic import BaseModel, field_validator
class EvidenceRef(BaseModel):
    source: str  # image_0, maintenance_note
    mask_id: Optional[str] = None
    span: Optional[Tuple[int,int]] = None
class Observation(BaseModel):
    text: str
    evidence: List[EvidenceRef]
    uncertainty: float
    @field_validator('evidence')
    def must_have_valid_ref(cls, v):
        assert len(v) >=1, "Every observation must have evidence"
        return v
```

### No OpenAI Enforcement

```python
# in tests/test_no_openai.py
def test_no_openai_import():
    import pathlib, re
    for f in pathlib.Path("app").rglob("*.py"):
        text = f.read_text()
        assert "import openai" not in text, f"OpenAI found in {f}"
        assert "from openai" not in text
```

## 5. What Judges Will Check (Startup Track)

- Can they run docker compose up and get UI in <60s? YES
- Do logs show real Meta model IDs (sam-3.1, muse-spark-1.3, etc.)? YES, with cost
- Is there SAM overlay in UI? YES
- Is output evidence-linked, not just caption? YES, validator enforces
- Is there eval report with 50 cases? YES
- Is stack Meta-only? YES, verify-meta-only passes
- Is it production-ready (auth, OTEL, CI, SBOM)? YES

## 6. Submission Checklist

- [ ] Public repo, no secrets, no proprietary Manage Assets code
- [ ] README.md is root README (copy over)
- [ ] docker compose up works
- [ ] Demo video <2min uploaded, link in README
- [ ] Eval report in eval/report.json
- [ ] Makefile targets work
- [ ] No openai dependency in requirements.txt
- [ ] Architecture diagram in README
- [ ] Submission mentions 5 Meta models + Muse Code + Baseten/Modal partners
- [ ] Cost per inspection logged

## 7. Prompts for Muse Code

Use these prompts for Muse Code agent:

> Build app/gateway/meta_client.py per ARCHITECTURE.md section 4.4. Must support SAM 3.1, Llama 4 Maverick Vision, Muse Spark 1.3, Muse Wonder, Muse Image. Use tenacity retry, OTEL spans, cost logging. No openai import.

> Build app/validator/schema.py per section 4.7. Pydantic v2 fail-closed. Every observation must have evidence ref. human_review_required must be true.

> Build FastAPI app/api/main.py with POST /v1/inspections that runs pipeline: SAM -> Vision -> Spark -> Wonder -> Validator. Include API key auth, rate limit, OTEL.

> Build minimal React UI that shows uploaded image with SAM mask overlay (canvas), JSON output, missing info checklist, approve button.

> Build eval/run.py that uses Muse Image to generate 50 synthetic defect cases and runs full pipeline, producing report.json with metrics.

End of guide. Now build.
