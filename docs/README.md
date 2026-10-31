# Asset Intelligence — Documentation

> Doc version: 1.4 | Updated: 2026-10-31 | Verified against: `2b6e515`

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

## Source-of-truth documents (repo root, read after onboarding)

- `PRD.md` v1.1 — product requirements.
- `ARCHITECTURE.md` v1.2 — system design and module contracts.
- `DESIGN.md` v1.1 — UI/UX design law + polish plan.
- `BRAND_KIT.md` v2.1 — logos, tokens, usage law.
- `SECURITY.md` — threat model, auth, secret handling.
- `AUDIT.md` — known gaps and risks.
- `AGENT_BUILD_GUIDE.md` / `PRIVATE_DEV_GUIDE.md` — maintainer-owned build notes.

## Conventions

- Commands are **PowerShell-first** (the team's primary shell); `python` means the repo venv Python.
- `v1` in routes (e.g. `/v1/inspections`) is the **API version**, independent of doc versions.
- Each guide carries a `Doc version` header. Bump MINOR on content changes, MAJOR on
  restructuring; record the change in [Versions](VERSIONS.md#doc-changelog).
