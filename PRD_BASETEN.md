# PRD_BASETEN - Optional BaseTen Inference Path
Status: DRAFT for owner review. NOT approved for implementation. No code changes ship from this document.
Date: 2026-11-02. Related: PRD.md v1.1, ARCHITECTURE.md v1.2, private BaseTen/Modal status doc 2026-11-02.
Save location: repo root (public when committed; commit only on owner request). No secrets in this file.

## Goal
Add an OPTIONAL, flag-gated BaseTen path for open-weights Llama vision as an alternate to the default Meta Model API vision stage. Default behavior stays Meta-only with zero changes when the flag is unset.

## Success Criteria
- Flag unset: behavior identical to today (all existing tests, routes, UI, exports unchanged).
- Flag set with key: one live inspection completes end to end through BaseTen vision with cost attributed to the BaseTen schedule.
- A short A/B eval note (Meta vs BaseTen vision) exists before any quality claim is made.
- Rollback is one env var (unset flag) with no code deploy.

## Approach
New thin gateway client beside meta_client.py, branched only inside app/vision/extractor.py behind BASETEN_ENABLED (default false). Reuse the existing timeout/retry/logging contract, token metering shape, and provider-error shape. Pricing activates the currently inert BASETEN_PRICE_* notebook vars under the same unset-means-unpriced rule. SDK import is lazy so installs without BaseTen deps keep working; endpoint shape to be confirmed against BaseTen docs at build time (no API version asserted here).

## Steps
1. app/gateway/baseten_client.py (NEW): request/response wrapper; lazy SDK import with a clear error if the flag is on but the package is missing.
2. app/gateway/config.py (ADDITIVE): read BASETEN_ENABLED (default false), BASETEN_API_KEY (default empty), BASETEN_MODEL_ID (default empty, owner supplies the verified deployment id).
3. app/vision/extractor.py (BRANCH): route through baseten_client only when enabled and configured; else the existing Meta path untouched.
4. app/gateway/pricing.py (ADDITIVE): BaseTen schedule from BASETEN_PRICE_* vars; unset stays unpriced fail-soft.
5. app/orchestrator/pipeline.py (PASS-THROUGH): record provider baseten in model_usage for cost and telemetry attribution.
6. tests/test_baseten.py (NEW): mocked client tests plus a skip-gated live test (runs only with key and flag, mirroring existing live gates).
7. eval/run.py (FLAG): optional --provider baseten arm for parity runs; default arm and all gates unchanged.
8. Docs: CONFIGURATION + VERSIONS entries; .env.example block with empty values; runbook troubleshooting lines.

## Validation Plan
- pytest (full suite incl. new mocked tests) + ruff + vitest 66/66: all green, no existing test modified.
- Manual live inspection with flag on: 200, provider baseten in usage, cost line present and labeled estimate.
- A/B note: same 5 cases through Meta and BaseTen vision, diff recorded; no claim beyond what the diff shows.
- Rollback check: unset flag, rerun one inspection, confirm Meta-only behavior and zero BaseTen import.

## Pros
- Small diff on a proven seam (gateway client + one branch).
- Possible price leverage at volume (notebook rates in owner .env; every figure invoice-verified before quoting).
- Outage and rate-limit redundancy for the vision stage.
- Turns the aspirational partner claim into a true, verified statement.

## Cons / Risks
- Dilutes the Meta-only judging story; must ship and be framed as optional alternate, default Meta.
- Second provider means a second failure mode, invoice, and CI live gate.
- Quality parity unknown until the A/B note exists; no claim before then.
- Support surface grows for a path most users never enable.

## Alternatives rejected
- Dedicated autoscaled BaseTen deployment for prod traffic: premature with no paid traffic; revisit with the async queue.
- Fine-tuned defect classifier on BaseTen: needs labeled data plus training pipeline; post-hackathon at earliest.

## Open Questions
None from repo discovery. Owner supplies the verified deployment id at build time.
