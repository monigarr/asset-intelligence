# Asset Intelligence — Documentation

> Doc version: 1.5 | Updated: 2026-11-02 | Verified against: `ffd16da`

Start here if you just joined the team. These guides get the repo running on your machine
and explain how to work in it day to day.

## Read in this order

| # | Guide | What you get |
|---|-------|--------------|
| 1 | [Getting Started](GETTING_STARTED.md) | Clone → install → first green verification (~30 min) |
| 2 | [Configuration](CONFIGURATION.md) | Every environment variable, with safe defaults |
| 3 | [Runbook](RUNBOOK.md) | Run the API, Docker stack, evals, and case generation |
| 4 | [Testing](TESTING.md) | Test suite, coverage gate, lint, CI |
| 5 | [Troubleshooting](TROUBLESHOOTING.md) | Known gotchas and fixes (read when stuck) |
| 6 | [Versions](VERSIONS.md) | Pinned versions: language, models, packages, ports |
| 7 | [Deployment](DEPLOYMENT.md) | Local stack, HF Space demo, production pointer |

## Key documents (repo root)

- `SECURITY.md` — threat model, auth, secret handling.
- `README_FAST_API.md` - FastAPI team onboarding (repo root).
Internal build specs (PRD, architecture, agent guides) are maintained privately and are not part of the public repo.

## Conventions

- Commands are **PowerShell-first** (the team's primary shell); `python` means the repo venv Python.
- `v1` in routes (e.g. `/v1/inspections`) is the **API version**, independent of doc versions.
- Each guide carries a `Doc version` header. Bump MINOR on content changes, MAJOR on
  restructuring; record the change in [Versions](VERSIONS.md#doc-changelog).
