# HF Space Sync Checklist - Asset Intelligence

Version 1.0 | 2026-10-31. Pushes this repo to a Hugging Face Docker Space.
The Space repo stays separate from GitHub: its README needs Space frontmatter.

## 0. One-time Space setup (owner, HF website)

- [ ] Create a Space: SDK = Docker, hardware = basic CPU, visibility = public.
- [ ] PRO subscription active: Docker Spaces on cpu-basic return HTTP 402
  without it (verified 2026-10-31: Static Spaces are free, Docker needs PRO).
- [ ] In Space Settings, add secrets (never commit these anywhere):
  - META_API_KEY (Meta API key, required)
  - API_KEY (review API key, required - never the dev default)
  - JWT_SECRET, UI_USERNAME, UI_PASSWORD_HASH (enable review login)
- [ ] Optional variables: META_API_TIMEOUT_S=180; model ID overrides;
  pricing vars (unset = costs show not yet priced).
- [ ] Optional: attach a Storage Bucket and set STORE_PATH=/data/inspections.db.
  Without it, history resets on restart (default path under the app home).

## 1. File map (repo -> Space repo root)

- [ ] deploy/hf/Dockerfile -> Dockerfile
- [ ] deploy/hf/supervisord.conf -> deploy/hf/supervisord.conf
- [ ] deploy/hf/nginx-space.conf -> deploy/hf/nginx-space.conf
- [ ] deploy/hf/space-README.md -> README.md
- [ ] app/ -> app/ (full tree)
- [ ] requirements.txt -> requirements.txt
- [ ] .dockerignore respected: eval/, data/, .env never sync (UI fixtures
  ship inside the built UI, so eval/ is not needed at runtime).

## 2. Validate locally first (repo root)

- [ ] docker build -f deploy/hf/Dockerfile -t asset-intel-space .
- [ ] docker run -p 7860:7860 --env-file .env asset-intel-space
- [ ] curl UI: HTTP 200 on http://localhost:7860/
- [ ] curl API: HTTP 200 on /v1/stats with X-API-Key header
- [ ] POST one small inspection, GET its overlay and history row
- [ ] Confirm review round-trip and cost line render in the UI

## 3. Push to the Space

- [ ] Clone the Space repo locally (HF git remote, token auth).
- [ ] Copy files per the map in section 1; commit with the source tag
  (example: space sync from v0.3.0).
- [ ] Push; watch the Space build log until status is Running.
- [ ] Repeat the section 2 checks against the live Space URL.

## 4. Updates and rollback

- [ ] Per release: re-validate locally, re-sync, push, re-check live.
- [ ] Rollback: revert the Space repo to the previous commit and push;
  the Space rebuilds the prior image automatically.
- [ ] Rotate a leaked key in Space Settings, then restart the Space.
