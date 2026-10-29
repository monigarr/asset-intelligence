# Stage 5: Experiments

Tag runs and compare them before merging:

- `python -m eval.run --mode live --run-tag prompt-v1 ...`
- `python -m eval.run --mode live --run-tag prompt-v2 ...`
- `python -m eval.compare --base live_reports/prompt-v1.json --head live_reports/prompt-v2.json`

Comparison covers metric deltas, gate flips, new/fixed fabrication cases,
and per-case outcome changes, plus a roster-hash check. Prompt A/B runs on
Meta models only: non-Meta comparison arms are out of scope for this repo
(Meta-only stack, PRD 14 agent instruction). For determinism, record once
and replay per arm (Stage 3).
