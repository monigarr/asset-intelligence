# PRIVATE_DEV_GUIDE — Startup Track Private Development Playbook

- **Project:** Asset Intelligence — Meta Global AI Hackathon
- **Mode:** Private Development → Public Submission
- **Track:** Startup / Push the Frontier
- **Goal:** Build privately without disqualifying, leaking secrets, or mixing proprietary Manage Assets code

## 1. Why Private Dev is Allowed & Recommended

- Official rules as of Oct 17: No public repo requirement stated — only requirement is original work you own + working demo + video. You can develop private.
- Startup track judged on production readiness, not early public commits.
- You have a private core (Manage Assets) that MUST stay out of public repo per your ADR-001.
- **Rule:** Nothing you share during the event is treated as confidential, and you grant organizers royalty-free license. So keep secrets out of git entirely.

**Workflow:**

```text
Private Repo (this one): monigarr/asset-intelligence-private
  → active dev, all experiments, may contain local paths
  → NEVER push Manage Assets code, real customer data, or .env
Public Submission Repo (on Nov 4): monigarr/asset-intelligence
  → clean copy of only OSS core + synthetic data + optimized docs
  → what judges see, what demo video shows
  → Apache 2.0
```

## 2. Exact .gitignore — Copy This to Root

Save as .gitignore in private repo. This is hardened for Meta hackathon.

```gitignore
# === SECRETS - NEVER COMMIT ===
.env
.env.*
!.env.example
*.env
*.pem
*.key
*.crt
*.p12
*.pfx
secrets/
.secrets/
credentials.json
service-account*.json
api_keys.txt
# Meta API keys, Baseten, Modal
baseten_key.txt
modal_token.txt
fireworks_key.txt
# === PYTHON ===
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
venv/
.venv/
env/
ENV/
.env_venv/
pip-log.txt
pip-delete-this-directory.txt
.pytest_cache/
.coverage
htmlcov/
*.egg-info/
dist/
build/
.mypy_cache/
.ruff_cache/
# === NODE / UI ===
node_modules/
npm-debug.log*
yarn-debug.log*
yarn-error.log*
.pnp/
.pnp.js
dist-ui/
build/
.next/
out/
.parcel-cache/
.vite/
*.tsbuildinfo
# === DATA - REAL vs SYNTHETIC ===
# Keep synthetic samples, ignore real inspection data
samples/raw/
samples/private/
samples/customer/
data/
datasets/
*.jpg
*.jpeg
*.png
*.webp
*.mp4
*.mov
# BUT allow synthetic demo images (override)
!samples/demo/
!samples/demo/**
!samples/synthetic/
!eval/cases/synthetic/
!eval/cases/demo/
# Large masks, embeddings, model weights
*.npy
*.npz
*.bin
*.pt
*.pth
*.onnx
*.safetensors
models/
checkpoints/
weights/
embeddings/
# === LOGS, OS, IDE ===
logs/
*.log
.DS_Store
Thumbs.db
.idea/
.vscode/
*.swp
*.swo
*~
.jupyter/
.ipynb_checkpoints/
# === DOCKER & TEMP ===
.docker/
docker-compose.override.yml
tmp/
temp/
.cache/
# === MANAGE ASSETS PRIVATE CORE - CRITICAL ===
# Never commit proprietary platform
manage-assets/
manage_assets/
private_core/
proprietary/
customer_data/
real_customer_records/
**/private_api/
**/internal_api/
# === EVAL ARTIFACTS (keep report, ignore raw) ===
eval/raw/
eval/tmp/
# Keep final report
!eval/report.json
!eval/report.html
# === SBOM & SECURITY ===
# Keep sbom.txt but ignore local scans
security-scan-results/
gitleaks-report.json
```

**Create .env.example (committed):**

```text
# Copy to .env and fill — NEVER commit .env
META_API_KEY=sk-meta-...-REPLACE_ME
META_API_BASE_URL=https://api.meta.ai/v1
VISION_MODEL_ID=llama-4-maverick-17b-128e-vision
FALLBACK_VISION_MODEL_ID=llama-4-scout-17b-16e-vision
SAM_MODEL_ID=sam-3.1
REASONING_MODEL_ID=muse-spark-1.3
PLANNING_MODEL_ID=muse-wonder
IMAGE_MODEL_ID=muse-image
BASETEN_API_KEY= # optional
MODAL_TOKEN= # optional
API_KEY=local-dev-key-123 # for FastAPI auth
```

## 3. Secret Scanning — Pre-Commit + CI

### A. Pre-commit (local, blocks commit if secret found)

**.pre-commit-config.yaml:**

```yaml
repos:
  - repo: https://github.com/gitleaks/gitleaks
    rev: v8.18.0
    hooks:
      - id: gitleaks
  - repo: https://github.com/Yelp/detect-secrets
    rev: v1.5.0
    hooks:
      - id: detect-secrets
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.6.0
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format
```

**Install:**

```bash
pip install pre-commit
pre-commit install
pre-commit run --all-files
```

### B. GitHub Actions — Secret Scan + Meta-Only Enforcement

**Create .github/workflows/secret-scan.yml:**

```yaml
name: Secret Scan & Compliance (Private Dev)
on:
  push:
    branches: [main, develop]
  pull_request:
  workflow_dispatch:
jobs:
  security:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - name: Gitleaks — Secret Detection
        uses: gitleaks/gitleaks-action@v2
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          GITLEAKS_ENABLE_COMMENTS: true
      - name: TruffleHog — Verify No Secrets
        uses: trufflesecurity/trufflehog@main
        with:
          path: ./
          base: main
          head: HEAD
          extra_args: --debug --only-verified
      - name: Enforce Meta-Only Stack (No OpenAI)
        run: |
          echo "Checking for banned imports..."
          if grep -r "import openai" --include="*.py" app/ 2>/dev/null; then
            echo "::error::Found 'import openai' — violates Meta-only requirement"
            exit 1
          fi
          if grep -r "from openai" --include="*.py" app/ 2>/dev/null; then
            echo "::error::Found 'from openai' — violates Meta-only requirement"
            exit 1
          fi
          if grep -r "anthropic" --include="*.py" app/ requirements*.txt 2>/dev/null; then
            echo "::error::Found anthropic — use Meta models only"
            exit 1
          fi
          echo "✅ Meta-only check passed"
      - name: Check .env Not Committed
        run: |
          if [ -f .env ]; then
            echo "::error::.env file exists in repo — should be gitignored"
            exit 1
          fi
          if git ls-files | grep -E "^\.env$|private_core|manage-assets|*.pem|*.key"; then
            echo "::error::Sensitive files tracked by git"
            exit 1
          fi
          echo "✅ No secrets tracked"
      - name: Validate .env.example Placeholders Only
        run: |
          if grep -E "sk-|api_key.*[a-zA-Z0-9]{20,}" .env.example 2>/dev/null | grep -v REPLACE_ME; then
            echo "::warning::.env.example may contain real-looking keys — use REPLACE_ME placeholders"
          fi
  compliance:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Check Private Core Boundary (ADR-001)
        run: |
          if [ -d "manage-assets" ] || [ -d "manage_assets" ] || [ -d "private_core" ]; then
            echo "::error::Private core folder found in repo — must stay outside public submission"
            exit 1
          fi
          echo "✅ Private boundary clean"
      - name: Check Synthetic Data Only
        run: |
          # Ensure no real images accidentally committed (size check)
          if find samples/ -type f \( -name "*.jpg" -o -name "*.png" \) -size +5M 2>/dev/null | grep -q .; then
            echo "::warning::Large images in samples/ — ensure they are synthetic"
          fi
```

### C. Full CI (add to same or separate workflow)

**.github/workflows/ci.yml:**

```yaml
name: CI — Production Readiness (Startup Track)
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - run: pip install -r requirements.txt && pip install -r requirements-dev.txt
      - run: ruff check app/
      - run: pytest tests/ -v --cov=app --cov-fail-under=70
      - run: make verify-meta-only
  docker:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: docker compose config --quiet
      - run: docker compose build --no-cache api
```

## 4. How to Transition: Private → Public Submission on Nov 4

Step-by-step for Nov 4, 6pm ET (3 hours before deadline):

```bash
# 1. In private repo, ensure clean
make test
make eval
make verify-meta-only
./scripts/scan-secrets.sh  # runs gitleaks locally
# 2. Create clean public repo
mkdir /tmp/public-release
cd /tmp/public-release
git clone --no-checkout https://github.com/monigarr/asset-intelligence-private temp-private
cd temp-private
git archive --format=tar main app/ samples/demo/ samples/synthetic/ eval/cases/synthetic/ eval/report.json README_OPTIMIZED.md PRD_OPTIMIZED.md ARCHITECTURE_OPTIMIZED.md Makefile requirements.txt docker-compose.yml Dockerfile .env.example .github/ | tar -x -C /tmp/public-release
# 3. In public repo
cd /tmp/public-release
cp README_OPTIMIZED.md README.md
cp PRD_OPTIMIZED.md PRD.md
cp ARCHITECTURE_OPTIMIZED.md ARCHITECTURE.md
rm -rf .git
git init
git add .
git commit -m "feat: initial public submission - Meta Global AI Hackathon - 5-model pipeline - production ready"
# 4. Push to public
gh repo create monigarr/asset-intelligence --public --source=. --push
# OR manually: git remote add origin ... && git push -u origin main
# 5. Verify public repo is clean
gitleaks detect --source . --verbose
grep -r "sk-" . --include="*.md" --include="*.py" || echo "clean"
docker compose up --build # must work for judges
```

**Checklist before making public:**

- [ ] No .env, no *.pem, no manage-assets/ folder
- [ ] samples/ only contains synthetic/demo images (5-10 images max)
- [ ] requirements.txt has meta-ai, baseten, modal, fastapi, pydantic — NO openai
- [ ] docker compose up works in <60s for stranger
- [ ] eval/report.json exists with 50 cases
- [ ] README has demo video YouTube link (unlisted is OK), architecture mermaid, quickstart
- [ ] SBOM: pip freeze > sbom.txt committed
- [ ] License: Apache 2.0
- [ ] Model IDs logged: sam-3.1, llama-4-maverick, muse-spark-1.3, muse-wonder, muse-image

## 5. If Judges Need Access to Private Repo (Fallback)

If final rules require private sharing instead of public:

- Go to GitHub repo Settings → Collaborators → Invite cerebral-valley-judges (email will be in Discord)
- Add note in Cerebral Valley submission: "Private repo — invite sent to [email], public demo at [URL], video at [YouTube]"
- Keep private repo's main branch = submission snapshot, create tag v1.0-submission
- Better to have public submission repo — easier for judges, better for Impact score.

## 6. Daily Private Dev Habits (Startup Track)

```bash
# Morning
git pull
cp .env.example .env  # ensure not overwritten
make dev
# Before every commit
pre-commit run --all-files
make verify-meta-only
# Before push
gitleaks detect --source . --no-git -v
pytest tests/test_no_openai.py -v
```

**Never:**

- git add .env
- Commit photos from real job sites (use synthetic from Muse Image)
- Copy code from Manage Assets private repo
- Commit API keys even in comments

**Always:**

- Log model_trace with model IDs + cost_cents per request
- Keep human_review_required=true enforced
- Write test for every validator rule

## 7. Scripts — Add These

**scripts/scan-secrets.sh:**

```bash
#!/bin/bash
set -e
echo "🔍 Scanning for secrets..."
docker run --rm -v $(pwd):/path zricethezav/gitleaks:latest detect --source="/path" --verbose
echo "✅ No secrets found"
```

**scripts/prepare-public.sh:** (automates step 4 above)

**Final Note:** Private dev is your competitive advantage for Startup track. Keep experiments private, ship polished public artifact. Judges score Impact 30% + Creative Meta Use 25% + Demo 25% + Tech Depth 20% — not commit history.

Built for $1M prize pool, Startup $550k, first prize $250k.

Good luck — now build.
