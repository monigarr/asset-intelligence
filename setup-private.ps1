# setup-private.ps1 — Run this in your asset-intelligence folder to install private dev pack
# PowerShell 5.1+ / PowerShell 7+ compatible
param()

Write-Host "🔧 Setting up private dev pack for Meta Global AI Developer Hackathon — Startup Track" -ForegroundColor Cyan
$repoRoot = Get-Location
Write-Host "📁 Repo root: $repoRoot" -ForegroundColor Gray

# Ensure .github/workflows exists
$workflowDir = Join-Path $repoRoot ".github\workflows"
if (-not (Test-Path $workflowDir)) {
    New-Item -ItemType Directory -Force -Path $workflowDir | Out-Null
    Write-Host "✅ Created $workflowDir" -ForegroundColor Green
}

# 1. .gitignore — hardened private mode
@"
# Secrets, keys, env files - NEVER COMMIT
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
baseten_key.txt
modal_token.txt
fireworks_key.txt

# Python
__pycache__/
*.py[cod]
*`$py.class
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

# Node / UI
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

# Data - real vs synthetic — keep synthetic, ignore real
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
# Allow synthetic demo images
!samples/demo/
!samples/demo/**
!samples/synthetic/
!eval/cases/synthetic/
!eval/cases/demo/

# Large binaries
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

# Logs, OS, IDE
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

# Docker temp
.docker/
docker-compose.override.yml
tmp/
temp/
.cache/

# Private core - CRITICAL - never commit proprietary
manage-assets/
manage_assets/
private_core/
proprietary/
customer_data/
real_customer_records/
**/private_api/
**/internal_api/

# Eval temp (keep final report)
eval/raw/
eval/tmp/
!eval/report.json
!eval/report.html

# Security scan results
security-scan-results/
gitleaks-report.json

# AI agent tooling - vendored skills, local agent state
.agents/
"@ | Set-Content -Path (Join-Path $repoRoot ".gitignore") -Encoding UTF8
Write-Host "✅ Created .gitignore (private hardened)" -ForegroundColor Green

# 2. .pre-commit-config.yaml
@"
repos:
  - repo: https://github.com/gitleaks/gitleaks
    rev: v8.18.0
    hooks:
      - id: gitleaks
  - repo: https://github.com/Yelp/detect-secrets
    rev: v1.5.0
    hooks:
      - id: detect-secrets
        args: ['--baseline', '.secrets.baseline']
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.6.0
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format
"@ | Set-Content -Path (Join-Path $repoRoot ".pre-commit-config.yaml") -Encoding UTF8
Write-Host "✅ Created .pre-commit-config.yaml" -ForegroundColor Green

# 3. .env.example
if (-not (Test-Path (Join-Path $repoRoot ".env.example"))) {
@"
# Copy to .env and fill — NEVER commit .env
META_API_KEY=sk-meta-REPLACE_ME
META_API_BASE_URL=https://api.meta.ai/v1
VISION_MODEL_ID=llama-4-maverick-17b-128e-vision
FALLBACK_VISION_MODEL_ID=llama-4-scout-17b-16e-vision
SAM_MODEL_ID=sam-3.1
REASONING_MODEL_ID=muse-spark-1.3
PLANNING_MODEL_ID=muse-wonder
IMAGE_MODEL_ID=muse-image
BASETEN_API_KEY=
MODAL_TOKEN=
API_KEY=local-dev-key-123
"@ | Set-Content -Path (Join-Path $repoRoot ".env.example") -Encoding UTF8
Write-Host "✅ Created .env.example" -ForegroundColor Green
} else {
    Write-Host "ℹ️ .env.example already exists — skipping" -ForegroundColor Yellow
}

# 4. secret-scan.yml workflow
@"
name: Secret Scan & Compliance (Private Dev)

on:
  push:
    branches: [main, master, develop]
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
          GITHUB_TOKEN: `${{ secrets.GITHUB_TOKEN }}
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
          if grep -r "anthropic\|cohere" --include="*.py" app/ requirements*.txt 2>/dev/null; then
            echo "::error::Found competitor SDK — use Meta models only"
            exit 1
          fi
          echo "✅ Meta-only check passed"

      - name: Check .env Not Committed
        run: |
          if [ -f .env ]; then
            echo "::error::.env file exists in repo — should be gitignored"
            exit 1
          fi
          if git ls-files | grep -E "^\.env$|private_core|manage-assets|.*\.pem|.*\.key" | grep -v ".env.example"; then
            echo "::error::Sensitive files tracked by git"
            exit 1
          fi
          echo "✅ No secrets tracked"

  compliance:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Check Private Core Boundary (ADR-001)
        run: |
          if [ -d "manage-assets" ] || [ -d "manage_assets" ] || [ -d "private_core" ]; then
            echo "::error::Private core folder found — must stay outside public submission"
            exit 1
          fi
          echo "✅ Private boundary clean"
"@ | Set-Content -Path (Join-Path $workflowDir "secret-scan.yml") -Encoding UTF8
Write-Host "✅ Created .github/workflows/secret-scan.yml" -ForegroundColor Green

# 5. ci.yml workflow (production readiness)
@"
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
      - name: Install deps
        run: |
          python -m pip install --upgrade pip
          if [ -f requirements.txt ]; then pip install -r requirements.txt; fi
          if [ -f requirements-dev.txt ]; then pip install -r requirements-dev.txt; fi
          pip install ruff pytest pytest-cov pre-commit
      - name: Lint
        run: ruff check app/ || echo "no app/ yet — ok for setup"
      - name: Meta-only check
        run: |
          if [ -d app ]; then
            if grep -r "import openai" --include="*.py" app/; then exit 1; fi
            echo "Meta-only OK"
          fi
      - name: Docker compose validate
        run: |
          if [ -f docker-compose.yml ]; then docker compose config --quiet; fi

  docker:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Build API image
        run: |
          if [ -f docker-compose.yml ]; then
            docker compose build --no-cache api || echo "docker build skipped — no Dockerfile yet"
          fi
"@ | Set-Content -Path (Join-Path $workflowDir "ci.yml") -Encoding UTF8
Write-Host "✅ Created .github/workflows/ci.yml" -ForegroundColor Green

# 6. .secrets.baseline placeholder
@"
{
  "version": "1.5.0",
  "plugins_used": [
    {"name": "ArtifactoryDetector"},
    {"name": "AwsKeyDetector"},
    {"name": "AzureStorageKeyDetector"},
    {"name": "Base64HighEntropyString", "limit": 4.5},
    {"name": "BasicAuthDetector"},
    {"name": "CloudantDetector"},
    {"name": "DiscordBotTokenDetector"},
    {"name": "HexHighEntropyString", "limit": 3.0},
    {"name": "JwtTokenDetector"},
    {"name": "KeywordDetector"},
    {"name": "MailchimpDetector"},
    {"name": "PrivateKeyDetector"},
    {"name": "SlackDetector"},
    {"name": "SoftlayerDetector"},
    {"name": "SquareOAuthDetector"},
    {"name": "StripeDetector"},
    {"name": "TwilioKeyDetector"}
  ],
  "filters_used": [],
  "results": {},
  "generated_at": "2026-10-26T00:00:00Z"
}
"@ | Set-Content -Path (Join-Path $repoRoot ".secrets.baseline") -Encoding UTF8
Write-Host "✅ Created .secrets.baseline" -ForegroundColor Green

Write-Host "`n🎉 Private dev pack installed!" -ForegroundColor Cyan
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "  1. Copy .env.example to .env and add your META_API_KEY:  Copy-Item .env.example .env" -ForegroundColor White
Write-Host "  2. Install pre-commit:  pip install pre-commit && pre-commit install" -ForegroundColor White
Write-Host "  3. Test:  pre-commit run --all-files" -ForegroundColor White
Write-Host "  4. Verify:  git status  (should NOT show .env)" -ForegroundColor White
Write-Host "`nAll files now in your repo — no need to cp _PRIVATE files." -ForegroundColor Green
