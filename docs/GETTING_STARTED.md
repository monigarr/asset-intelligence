# Getting Started

> Doc version: 1.1 | Updated: 2026-10-29 | Verified against: `2b1c7dc`

From zero to a verified working checkout in about 30 minutes. No API key needed until Step 6.

## 1. Prerequisites

| Tool | Version | Check |
|------|---------|-------|
| Python | 3.12 (verified 3.12.3; Docker uses `python:3.12-slim`) | `python --version` |
| Git | any recent | `git --version` |
| Docker Desktop | for the compose stack only (Step 7, optional) | `docker --version` |
| Node.js | for UI dev only (see [Runbook](RUNBOOK.md#review-ui)) | `node --version` |

> Network drives: Docker and some Node tooling fail on UNC paths (`\\server\share`).
> If your checkout is on a UNC path, copy it to a local drive (or map the drive) before
> running Docker or `npm` commands. Python, pytest, and ruff work fine on UNC.

## 2. Clone

```powershell
git clone https://github.com/monigarr/asset-intelligence.git
cd asset-intelligence
```

GitHub is the only remote. There is no GitLab for this repo.

## 3. Create the virtual environment

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
```

## 4. Install dependencies

```powershell
pip install -r requirements.txt -r requirements-dev.txt
pre-commit install
```

Runtime deps are floor-pinned in `requirements.txt` (Meta-only stack: no `openai`/`anthropic`/
`cohere`, enforced by CI). Dev adds `pytest`, `pytest-cov`, `ruff`.

## 5. Configure the environment file

```powershell
Copy-Item .env.example .env
```

`.env` is gitignored — never commit it. For a first local run you can leave `META_API_KEY`
empty; the mocked eval and unit tests do not need it. See [Configuration](CONFIGURATION.md)
for every variable (cost metering: copy the 7 commented price lines from `.env.example`, plus `META_PRICE_TIER` only if contributor-billed). Get a key at <https://dev.meta.ai/api-keys> when you are ready for live calls.

## 6. Verify — mocked eval (no key needed)

```powershell
python -m eval.run --mode mocked --out eval/report.json
```

Expected: `mode=mocked n=50 ok=50 rejected=0 errors=0`, all gates `True`.
This validates the harness and pipeline wiring, not model quality.

## 7. Verify — unit tests and lint

```powershell
python -m pytest tests/ -q --cov=app --cov-fail-under=70
ruff check app/ eval/ tests/
```

Expected: all tests pass, coverage ≥ 70% (currently ~89%), ruff reports `All checks passed!`.

## 8. Verify — API smoke test (optional, still no key)

```powershell
.\.venv\Scripts\python.exe -m uvicorn --factory app.api.main:create_app --host 127.0.0.1 --port 8000
```

In another shell:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/healthz
```

Expected: a healthy status payload. Stop the server with `Ctrl+C`.

## Next steps

- [Configuration](CONFIGURATION.md) — set `META_API_KEY` and model IDs for live work.
- [Runbook](RUNBOOK.md) — run the full stack, live evals, and case generation.
- `SECURITY.md` (repo root) — required reading before handling real keys or data.
