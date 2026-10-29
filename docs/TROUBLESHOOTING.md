# Troubleshooting

> Doc version: 1.1 | Updated: 2026-10-27 | Verified against: `2b1c7dc`

## Environment & platform

**Docker or npm fails on my checkout.**
Your checkout is probably on a UNC path (`\\server\share`). Copy the repo to a local drive
(or map the drive) and retry. Python/pytest/ruff work on UNC; Docker and Node tooling do not.

**`pre-commit` / shell quoting acts strangely.**
Use Windows PowerShell (5.1+) or PowerShell 7 with the venv activated. Note PowerShell 5.1
has no `&&` separator and `ConvertFrom-Json` has no `-Depth` flag — use `;` and Python for
deep JSON inspection.

## API keys & auth

**`401` / `MetaAuthError: live eval needs META_API_KEY`.**
`.env` is missing the key or wasn't loaded. Confirm `.env` exists (copied from `.env.example`),
holds a real key from <https://dev.meta.ai/api-keys>, and that you exported it into the shell
running the command. The agent/maintainers will never ask you to paste the key into chat.

**`403` on API routes.**
Authenticated routes need the `X-API-Key` header matching `API_KEY`. Unset `API_KEY` falls back
to a documented dev key for local demos only.

**`401` on `/v1/auth/*`.**
Wrong username/password, or a reused/expired refresh token (single-use by design).

**`503` on `/v1/auth/*`.**
`JWT_SECRET` or `UI_PASSWORD_HASH` is unset. JWT is optional; X-API-Key works without it.

**`503 model service overloaded`.**
The gateway circuit breaker opened after 5 consecutive upstream failures. Wait ~30 s for the
half-open trial; check Meta API status if it persists.

**Rate limiting without Valkey.**
Default `memory://` storage is single-worker. Set `RATE_LIMIT_STORAGE_URI=redis://valkey:6379`
(compose does this) for shared limits; if Valkey is unreachable, requests fail loudly — check
`docker compose ps`.

## Live calls & evals

**`model_not_found` 404s.**
Model IDs must match [Configuration](CONFIGURATION.md) exactly (`muse-spark-1.3`,
`muse-wonder-1.0`, `muse-image-1.0`, `sam-3.1`). There are no Llama models on the live API,
and there is no `POST /v1/segment` endpoint.

**Image generation / live eval times out.**
Image generation exceeds the 15 s default. Set `META_API_TIMEOUT_S=180` (documented in
`.env.example`) before synthetic generation or live runs.

**Live run is slow (~35–60 s/case, ~1.5 h for 50).**
Expected: four serial model calls (SAM → vision → Spark → Wonder). Per-stage timings are in
each report's `stage_p95_ms`. The 8 s p95 gate is currently red by design pending an
architectural decision — see the manual checklist in `live_reports/`.

**Adversarial cases show `validator_rejected` instead of `ok`.**
Containment working as designed: when Wonder quotes a certification demand, the validator
rejects the inspection so nothing certifying is emitted. These count toward `refusal_rate`;
only `refusal_clean_rate` tracks clean refusals. Known follow-up: teach Wonder to refuse
without quoting the demand.

## Evals & cases

**`eval/cases/synthetic` has JSONs but no PNGs.**
By design — PNGs (~200 MB) are gitignored. Regenerate with `python -m app.synthetic --out
eval/cases/synthetic` (needs key + 180 s timeout). See `eval/cases/synthetic/README.md`.

**Mocked eval is red.**
The harness or pipeline contract broke. Fix it before any live run — never "verify" against
live while mocked is red.

## Dependencies

**`pip install` resolves odd versions.**
`requirements.txt` uses floor pins; the versions verified in this checkout are frozen in
[Versions](VERSIONS.md#verified-dependency-freeze). If you suspect a bad resolve, compare with
`pip freeze` and report the diff rather than hand-editing pins.

**`meta_sam_parser` missing.**
It is a runtime dependency (`meta_sam_parser>=0.1.0` in `requirements.txt`) used by
`app/gateway/sam_responses.py`. Re-run the full install command from Getting Started.

## Still stuck?

1. Re-run the [Getting Started](GETTING_STARTED.md) verification steps to isolate the layer.
2. Check `AUDIT.md` (repo root) — your issue may be a documented known gap.
3. Capture the exact command, exit code, and last ~20 lines of output before asking for help.
