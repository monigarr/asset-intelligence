# Stage 3: Replay Harnesses

`eval/replay.py` provides record/replay transports around the live API:

- `python -m eval.run --mode live --record eval/.cache --suites clear --limit 5`
- `python -m eval.run --mode live --replay eval/.cache --suites clear --limit 5`

Cassettes are keyed by sha256(method + url + body); headers are excluded
because the gateway's volatile request id travels header-only
(`X-Request-ID`), so identical cases hash identically across runs. A cache
miss raises `ReplayMissError` (fail closed). Records carry
`usage_source`: `measured` (live), `replay` (cached), or `mocked` (canned,
never quotable). Replay is not a latency measurement: durations, p95, and
`overall_pass` are wall-clock-derived and excluded from replay comparison.
`eval/.cache/` is gitignored by design.
