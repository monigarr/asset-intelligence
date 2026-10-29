# Synthetic live-eval cases

50 labeled cases (15 clear + 10 incomplete + 10 contradictory + 10 ambiguous
+ 5 adversarial) rendered by `muse-image-1.0` at 1024x1024. The case JSONs in
this directory are the committed eval oracle: prompts, notes, asset metadata,
and expected labels. They contain no real inspections, no PII, and no secrets
(synthetic `SYN-*` IDs, fixed `2026-10-20` date).

## Images are gitignored (regenerable)

`images/*.png` (~200 MB) is intentionally NOT committed: `.gitignore` keeps
`*.png` ignored here (only the directory itself is un-ignored, so JSONs stay
committable). Regenerate any time with a Meta API key:

```powershell
Copy-Item .env.example .env   # then set META_API_KEY (never commit .env)
python -m app.synthetic --out eval/cases/synthetic
```

Existing images are skipped unless `--overwrite` is passed. `manifest.json`
records the model, size, timestamp, and per-case files of the last render.

## Running live eval

```powershell
python -m eval.run --mode live --cases-dir eval/cases/synthetic `
  --out $env:TEMP\eval-live\report.json
```

Image generation needs a longer timeout than the 15 s default:

```powershell
$env:META_API_TIMEOUT_S = '180'
```
