# Testing

> Doc version: 1.3 | Updated: 2026-10-29 | Verified against: `c83dfd5`

## Unit suite (required before every commit)

```powershell
python -m pytest tests/ -q --cov=app --cov-fail-under=70
```

Current state: 171 tests, ~89% coverage, gate is 70%. Relevant test file or package must pass
for any area you touch; never narrow a failing run (`-k 'not ...'`, `--deselect`, skips) to
make it green.

## Lint

```powershell
ruff check app/ eval/ tests/
```

Must report `All checks passed!`. (`make lint` covers `app/ tests/`; CI matches the fuller
three-tree invocation above.)

## Meta-only compliance

The stack is Meta-only: no `openai`/`anthropic`/`cohere` imports, no Streamlit/RAG libraries.
Enforced three ways:

1. `tests/test_no_openai.py` (runs in the suite),
2. `make verify-meta-only`,
3. `.github/workflows/secret-scan.yml` in CI.

## Pre-commit and secret scanning

`pre-commit install` (from Getting Started) enables the hooks in `.pre-commit-config.yaml`.
Secret baselines live in `.secrets.baseline`. Never commit `.env` or key material — the hooks
and CI scan are backstops, not permission to be careless.

## Mocked eval as a test

```powershell
python -m eval.run --mode mocked --out eval/report.json
```

50/50 with all gates green is the expected steady state. A red mocked gate means the harness
or pipeline contract broke -- fix it before any live run. (Mocked validates wiring only; it says
nothing about model quality.)

## Pre-merge regression (run tags + compare)

```powershell
python -m eval.run --mode live --run-tag base --out live_reports/base.json
# ... make your change ...
python -m eval.run --mode live --run-tag head --out live_reports/head.json
python -m eval.compare --base live_reports/base.json --head live_reports/head.json
```

Review metric deltas, gate flips, and new fabrication cases before merging.
Use `--record`/`--replay` (see `eval/stage_3_replay_harnesses/README.md`) to
separate code regressions from live API variance. `--judge` adds a
non-gating narrative-clarity score when prose changed.

## CI

Two workflows run on push/PR (`.github/workflows/`):

| Workflow | Checks |
|----------|--------|
| `ci.yml` | pytest + coverage, ruff, Meta-only, SBOM, UI, compose, live slice (needs `META_API_KEY` secret) |
| `secret-scan.yml` | Gitleaks + TruffleHog scans, Meta-only grep, `.env` + boundary checks |

Keep both green. If CI fails on code you did not touch, report it -- do not "fix" it by
weakening the gate.
