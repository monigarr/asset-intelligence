# ANTI-PROJECT COMPLIANCE VERIFICATION

- **Project:** Asset Intelligence — Production Multimodal Infrastructure Intelligence
- **Hackathon:** Meta Global AI Developer Hackathon — Startup / Push the Frontier
- **Verification Date:** 2026-10-26
- **Status:** ✅ PASS — Not considered overdone / anti-project

This document verifies that Asset Intelligence does NOT fall into any of the commonly penalized "overdone project" categories that judges deprioritize.

## Official Anti-Project List (from Cerebral Valley / Meta judging guidance)

AI generated medical advice, basic RAG apps, simple image analyzers, streamlit apps, dashboards as the main feature, AI for education chatbots, AI job application screeners, AI nutrition coaches, personality analyzers, sports analyzers or coaches

## Compliance Matrix — Asset Intelligence

| Anti-Project Category | Definition / Why Judges Penalize | Asset Intelligence — Why We Are NOT That | Evidence in Architecture |
| --- | --- | --- | --- |
| AI Generated Medical Advice | Autonomous diagnosis, prescribing, medical Q&A without clinical validation — high safety risk | Infrastructure, not medical. Zero medical content, no diagnosis. Domain is municipal drainage, roads, culverts. Explicit safety rule: MUST NOT declare safe/unsafe, certify compliance, invent measurements. Always human_review_required: true | PRD §10 Safety, ARCH §4.7 Validator fail-closed, Output contract |
| Basic RAG Apps | Simple vector DB + LLM chat over PDFs — no novel model use, 90% of hackathon submissions | No RAG. No vector DB, no document retrieval. Pipeline is multimodal segmentation → vision-language fusion → structured reasoning → planning. Uses 5 Meta models orchestrated, not one LLM over docs. | ARCH §4.2-4.6: SAM 3.1 → Llama 4 Maverick Vision → Muse Spark 1.3 → Muse Wonder → Muse Image. No embedding DB. |
| Simple Image Analyzers | Single image → caption / label, no evidence, no validation, no actionability | Verifiable multimodal intelligence, not captioning. Requires SAM 3.1 instance masks (RLE + bbox + confidence), evidence pointers linking every observation to mask_id + note span, uncertainty calibration, discrepancy detection (note vs image contradiction), missing info checklist. Simple analyzer returns "crack detected" — we return observations[] with evidence[{source: image_0, mask_id: mask_1}], uncertainties[], missing_information[] | ARCH §4.2 SAM Service (masks mandatory), §4.4 Evidence traceability, PRD §6 Output Contract |
| Streamlit Apps | Streamlit as entire product — no API, no production architecture, not scalable | No Streamlit. Stack is FastAPI + Pydantic v2 + OTEL + Prometheus + Docker Compose + React Vite Canvas overlay for SAM masks. Streamlit explicitly banned in build guide. Production-ready API with auth, rate limiting, cost metering. UI is review layer, not product. | ARCH §6 Tech Stack: FastAPI, React, Docker. Makefile targets. Startup track judged on production readiness |
| Dashboards as Main Feature | CRUD dashboard with charts as value prop — no AI depth | Dashboard is NOT main feature. Main feature is 5-model verifiable pipeline. Review UI is <15% of codebase — minimal React + Canvas to visualize SAM masks + evidence. Value is in segmentations[], evidence[], discrepancies[] JSON, not charts. No KPI dashboards. | ARCH §4.8 Review Layer: "CLI can serve as first review surface. Dedicated UI not required for initial proof." PRD FR-08: API + CLI + minimal UI |
| AI for Education Chatbots | Tutor chatbot, homework helper — overdone, no technical depth | No education, no chatbot. Domain is municipal infrastructure maintenance. Interaction is inspection submission → structured JSON, not conversational tutoring. No chat loop. | PRD §4 Target Users: inspectors, coordinators, municipal directors |
| AI Job Application Screeners | Resume parser / screener — ethical risk, overdone | No HR, no resumes. Zero PII, synthetic data only, EXIF GPS stripped. Domain is physical assets (drainage structure DEMO-DRAIN-001). | PRD §9 Security: synthetic data only, no PII logging |
| AI Nutrition Coaches | Meal plan generator, calorie tracker chatbot | No nutrition, no coaching. Output is maintenance intelligence: crack dimensions missing, seepage evidence, qualified inspection recommendation — not meal plans. | Output Contract: asset_type, segmentations, missing_information: ["crack_dimensions"] |
| Personality Analyzers | MBTI from text / social media — low utility, high bias risk | No personality, no psychometrics. Observations are physical: "Visible linear crack near top edge with active seepage" linked to SAM mask, not personality traits. | PRD Output Example: physical defect, not personality |
| Sports Analyzers or Coaches | Game analysis, fitness coach — overdone | No sports. Asset types: drainage structure, culvert, pavement, bridge component. Use case is public works inspection, not athletic performance. | PRD §4 Primary Use Case: field worker records condition affecting infrastructure asset |

## Why This Project is Push the Frontier (Opposite of Overdone)

Judging guidance for Push the Frontier: "Give a machine a new capability, accelerate a scientific experiment, or unlock a better way to understand and control a physical system. Show us what becomes possible when these models meet the real world."

Asset Intelligence does exactly that:

- **New Capability:** Zero-shot physical defect segmentation + evidence-grounded reasoning without training data — impossible before SAM 3.1 + Muse Spark. Simple image analyzers cannot do instance masks + evidence pointers + uncertainty.
- **Physical System Control:** Turns field photos + notes into auditable work order intelligence for real infrastructure (19k US municipalities, $2.3T deferred maintenance). Not a chatbot wrapper.
- **Technical Depth (20% of score):** 5 Meta models orchestrated via Meta Model API: SAM 3.1, Llama 4 Maverick Vision, Muse Spark 1.3, Muse Wonder, Muse Image. Plus Baseten/Modal for Llama 4 open-weights — partner credits used creatively. Simple RAG / simple image analyzer uses 1 model.
- **Production Ready (Startup track lens: technical execution and whether it holds up in production):** FastAPI, Pydantic v2 fail-closed validator, JWT + API key, OTEL tracing, cost metering, 50-case eval harness via Muse Image synthetic data, CI with meta-only enforcement, Docker Compose. Streamlit/dashboard projects fail this.
- **Impact (30% of score — largest weight):** Addresses municipal public works burden — 2.5 hrs/day inspector data entry, 40% missed defects on transcription. No overdone project has this quantified physical-world impact.

## Risk Mitigation — How to Ensure Judges Never Misclassify

Even though you pass, add these explicit signals to submission to avoid snap judgment:

### In README (first 100 words):

- Add badge: ![Not Overdone](https://img.shields.io/badge/Not-Overdone-5--Model_Verifiable_Pipeline-blue)
- Add sentence: "This is NOT a simple image analyzer or RAG app — it's a 5-model verifiable pipeline: SAM 3.1 segmentation masks (RLE) + Llama 4 Maverick multimodal fusion + Muse Spark evidence-linked JSON + Muse Wonder discrepancy detection + Muse Image synthetic eval, with fail-closed Pydantic validator and human review gate."

### In Demo Video (0-10s):

Say: "Most inspection tools are simple captioning — 'crack detected'. We do verifiable intelligence: SAM 3.1 segments the crack with mask_id, Llama fuses note vs image, Spark produces evidence-linked JSON where every observation cites mask_id + note span, Wonder flags missing tape measure — and validator enforces human review."

### In Submission Description:

Use keywords judges scan for:

- "Evidence traceability with SAM 3.1 instance masks"
- "Fail-closed validation"
- "Human review required"
- "Production-ready FastAPI + OTEL + cost metering"
- "Meta-only: 5 models via Meta Model API"
- "Push the Frontier: physical system understanding"

**Avoid These Phrases (trigger overdone filter):**

- ❌ "AI assistant that analyzes images"
- ❌ "RAG over inspection reports"
- ❌ "Streamlit dashboard"
- ❌ "Chatbot for inspectors"
- ✅ Use instead: "Verifiable multimodal intelligence platform", "Evidence-linked structured output", "SAM 3.1 segmentation service", "Production API"

## Final Verification Statement for Submission Portal

Copy-paste this into your Cerebral Valley submission "Additional Notes":

Asset Intelligence is NOT an overdone project: it is not medical advice, RAG, simple image analyzer, Streamlit app, dashboard, education chatbot, job screener, nutrition coach, personality analyzer, or sports analyzer. It is a production-ready, 5-model Meta-native platform for physical infrastructure intelligence: SAM 3.1 for zero-shot defect segmentation (masks + bboxes), Llama 4 Maverick Vision for multimodal fusion, Muse Spark 1.3 for evidence-linked structured JSON, Muse Wonder for discrepancy + missing info detection, and Muse Image for synthetic eval generation. Every observation requires evidence pointers (mask_id + note span), validator is fail-closed with human_review_required=true, and stack is FastAPI + Docker + OTEL — built for Startup track production readiness, not a demo dashboard.

## Checklist for Coding Agents

- [ ] No Streamlit import anywhere (grep -r streamlit app/ must be empty)
- [ ] No vector DB / RAG library (chromadb, faiss, pinecone not in requirements.txt)
- [ ] SAM masks are mandatory in output, not optional visualization
- [ ] Every observation.evidence must reference mask_id or note span — validator enforces
- [ ] UI is React + Canvas overlay, not Streamlit
- [ ] README first paragraph mentions 5 Meta models + evidence traceability
- [ ] Demo shows mask overlay click → evidence highlight

Result: ✅ PASS — Project is classified as novel Push the Frontier infrastructure intelligence, not overdone.
