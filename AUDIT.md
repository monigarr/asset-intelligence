# AUDIT.md — Asset Intelligence Repo Health Check

- **Date:** 2026-10-26
- **Auditor:** Muse Code (agentic session)
- **Project root:** `\\Pc2\e\Meta_Global_AI_Hackathon\asset-intelligence`
- **Scope:** File inventory, git state, test evidence, secret-scan posture, CI/config review vs `PRIVATE_DEV_GUIDE.md` and `AGENT_BUILD_GUIDE.md`

**Verdict:** Docs and private-dev scaffolding complete. Zero application code. Ready for Day 1–2 gateway build.

---

## 1. Files present

**Tracked by git (15 files, `git ls-files`):**

```text
.env.example
.github/workflows/ci.yml
.github/workflows/secret-scan.yml
.gitignore
.pre-commit-config.yaml
.secrets.baseline
AGENT_BUILD_GUIDE.md
ANTI_PROJECT_COMPLIANCE.md
ARCHITECTURE.md
LICENSE
NOTICE
PRD.md
PRIVATE_DEV_GUIDE.md
README.md
setup-private.ps1
```

**On disk, untracked but expected (gitignored):** `.env` (786 bytes, not read — secrets), `.venv/`, `.agents/skills/modal/` (vendored skill refs).

**On disk, untracked and NOT ignored:** `secret_scan.yaml` (2,656 bytes) — see Finding F-01.

**Missing (expected by `AGENT_BUILD_GUIDE.md` / `PRIVATE_DEV_GUIDE.md`):** `app/`, `tests/`, `eval/`, `samples/`, `demo/`, `Makefile`, `docker-compose.yml`, `Dockerfile`, `requirements.txt`, `requirements-dev.txt`, `sbom.txt`.

## 2. Git state

- Branch: `master`, tracking `origin/master`. Remote configured: `origin` (names only checked; URL not printed to avoid token leak).
- Working tree: clean except untracked `secret_scan.yaml`.
- HEAD: `14fda0d chore(repo): harden ignore rules and add secret-scanning CI` (8 commits total).
- Minor: git prints `warning: unable to find all commit-graph files` on status/log — harmless housekeeping; fix with `git commit-graph write` if it annoys you.
- `.env`, `.venv/`, `.agents/` confirmed NOT tracked. No `manage-assets/`, `manage_assets/`, or `private_core/` directories exist.

## 3. Test evidence

- `GAP: tests/ not found at PROJECT_ROOT` — no test evidence. First test per `AGENT_BUILD_GUIDE.md` Day 1–2 should be `tests/test_no_openai.py`.
- `python --version` → 3.12.3 (system and `.venv` agree; matches CI `python-version: '3.12'`).
- `pytest` NOT installed in `.venv` (`No module named pytest`). Nothing to run yet.
- Finding F-02: `.github/workflows/ci.yml` has **no pytest step** — diverges from `PRIVATE_DEV_GUIDE.md` L304 (`pytest tests/ -v --cov=app --cov-fail-under=70`). Add the step when `tests/` exists.

## 4. Secret-scan posture

- `.env` untracked and gitignored (`.gitignore` L2–4). `.env` contents never read this session.
- `.env.example` verified placeholders-only (12 lines, `META_API_KEY=[REDACTED]`, empty partner keys).
- `.gitignore` hardened per `PRIVATE_DEV_GUIDE.md` §2 plus `.agents/` exclusion (L130). Matches `setup-private.ps1` template exactly — setup script was executed.
- `.secrets.baseline` clean (`"results": {}`, generated 2026-10-26).
- `.pre-commit-config.yaml` = gitleaks v8.18.0 + detect-secrets v1.5.0 + ruff. `pre-commit 4.3.0` installed on system; whether hooks are installed in this clone (`pre-commit install`) was not verified.
- `GAP: gitleaks NOT INSTALLED locally` — full local secret scan not run. Server-side cover exists via `secret-scan.yml` (Gitleaks + TruffleHog) on next push.

## 5. CI / config review

- `secret-scan.yml` (committed): Gitleaks + TruffleHog + meta-only grep + `.env`-not-tracked check + private-core boundary check. Branch list `[main, master, develop]` matches actual `master` branch.
- Finding F-01: root `secret_scan.yaml` (untracked) is a stale draft of the same workflow — it never runs from repo root. Differences vs committed copy: missing `master` in branch list; has an extra `Verify .env.example Has Placeholders Only` step (L72–78) the committed copy lacks. Recommend: fold that step into `.github/workflows/secret-scan.yml`, then delete the root copy.
- `ci.yml` (committed): install + ruff + meta-only grep + compose validate, all tolerant of missing `app/` (echo fallbacks). Appropriate for Day 0; must be hardened (remove fallbacks, add pytest per F-02) once code lands.
- `setup-private.ps1` reviewed (348 lines): generates `.gitignore`, `.pre-commit-config.yaml`, `.env.example`, both workflows, `.secrets.baseline`. All on-disk files match its templates.

## 6. GAP list

| ID | GAP | Blocks |
| --- | --- | --- |
| GAP-01 | `app/` not found — zero application code | Day 1–2 gateway build is next |
| GAP-02 | `tests/` not found — no test evidence | Any "verified" claim |
| GAP-03 | `requirements.txt` / `requirements-dev.txt` not found | Reproducible env, CI install step is a no-op guard |
| GAP-04 | `Makefile` not found — no `make dev/test/eval/verify-meta-only` targets | `AGENT_BUILD_GUIDE.md` §2 contract |
| GAP-05 | `docker-compose.yml` / `Dockerfile` not found | `docker compose up` demo (PRD §9) |
| GAP-06 | `eval/` harness + `eval/report.json` not found | Any eval-metrics claim |
| GAP-07 | gitleaks not installed locally — full secret scan not run | Local pre-push confidence (CI covers server-side) |

## 7. AGENTS.md §9 validation checklist status

All 12 boxes unchecked — expected at Day 0–1. No box can pass until GAP-01–GAP-06 close.

## 8. Next actions (highest leverage first)

1. Day 1–2: `requirements.txt` + `requirements-dev.txt` (Meta-only: no `openai`), `app/gateway/meta_client.py` per `ARCHITECTURE.md` §4.4, `tests/test_no_openai.py`.
2. Add `Makefile` with `verify-meta-only` + `test` targets so CI and humans share one contract.
3. Resolve F-01 (fold `.env.example` check into workflow, delete root `secret_scan.yaml`) and F-02 (pytest step in `ci.yml`).
4. Install gitleaks locally or run `pre-commit run --all-files` before first push carrying code.
