# PRD_MODAL - Optional Modal Compute Path
Status: DRAFT for owner review. NOT approved for implementation. No code changes ship from this document.
Date: 2026-11-02. Related: PRD.md v1.1, ARCHITECTURE.md v1.2, private BaseTen/Modal status doc 2026-11-02.
Save location: repo root (public when committed; commit only on owner request). No secrets in this file.

## Goal
Add an OPTIONAL, flag-gated Modal path for offline batch work. Slice 1 (recommended): parallel live-eval runner for the 50-case harness. Slice 2 (possibility for review): GPU-hosted open-SAM fallback for SAM-degraded cases. The synchronous inspection request path never touches Modal.

## Success Criteria
- Slice 1: one command runs the same 50 cases on Modal and returns a report.json identical in schema to the local run, with estimated GPU cost attached.
- Default behavior unchanged: API server never imports modal; all existing tests and gates untouched.
- Rollback is not running the command; nothing in the default path references Modal.
- Slice 2 only proceeds if the owner explicitly approves after Slice 1; it is NOT part of the recommended go.

## Approach
New top-level modal_app/ directory holding a Modal batch app that fans out eval cases across containers and collects results; eval/run.py gains an additive --backend modal flag (default local). Slice 1 is CLI-driven only, never called from the API. Pricing activates the inert MODAL_PRICE_GPU_* notebook vars for post-run GPU-second attribution (estimates only). Modal packaging details to be confirmed against Modal docs at build time (no API version asserted here).

## Steps (Slice 1)
1. modal_app/eval_runner.py (NEW): fan-out/collect app; mounts repo eval modules; writes report.json back locally.
2. eval/run.py (ADDITIVE): --backend modal submits the case list and collects; local backend byte-identical.
3. Pricing (ADDITIVE): eval report includes estimated GPU cost from MODAL_PRICE_GPU_* x measured GPU-seconds; unset stays unpriced.
4. tests/test_modal_backend.py (NEW): mocked submit/collect tests; live runs stay manual (owner token), never CI.
5. Docs: RUNBOOK entry (install CLI, modal token new locally, run command, spending-limit warning); VERSIONS entry; .env.example placeholders stay empty.

## Validation Plan
- pytest + ruff + vitest green; confirm no app/ module imports modal (grep gate in the new test).
- Manual 5-case Modal run diffed against local: same schema, same gate math.
- Full 50-case run with cost attribution attached; runtime and estimate recorded in the report.
- Rollback check: default local backend run, unchanged output.

## Pros
- Eval scale: serial 50-case live runs take tens of minutes; parallel Modal fan-out cuts that to minutes.
- Zero request-path risk: offline only, cannot affect p95, UI, or demos.
- Reproducible cloud runs for the planned calibration study; frees the local machine.
- Makes the Modal partner story true with minimal surface.

## Cons / Risks
- New toolchain (Modal CLI + token) serving one batch job; real learning curve.
- GPU spend is real and easy to leave running; a stuck fan-out burns GPU-hours. Mitigation: account spending limit before first run plus per-run attribution.
- First packaging and mount setup takes about an hour, not minutes.
- Slice 2 adds cold-start latency, weight-licensing questions, and a runtime GPU dependency; that is why it is deferred by default.

## Slice 2 possibility (for review, not recommended now)
app/sam_service/modal_fallback.py would route SAM-degraded cases to a Modal GPU function hosting open SAM weights. Pros: better masks when Meta SAM degrades; cost control. Cons: cold starts, hosting and licensing review, second failure mode in a user-visible path. Proceed only if mask quality becomes a blocking issue AND the owner approves.

## Alternatives rejected
- Modal inside the live request path: rejected; cold starts worsen p95 and add a hard runtime dependency.
- Scheduled nightly evals on Modal: deferred; needs secrets handling and alerting first (post-launch).

## Open Questions
None from repo discovery. Owner runs all live Modal commands with a personal token; nothing token-like is committed.
