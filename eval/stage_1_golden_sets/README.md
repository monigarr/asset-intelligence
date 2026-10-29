# Stage 1: Golden Sets

The golden set is `eval/cases/synthetic/`: 50 case JSONs + 50 PNGs, all
committed. Suites: clear 15, incomplete 10, contradictory 10, ambiguous 10,
adversarial 5. Each case carries `expected` flags, optional
`expected.dimensions_mm` (SI ground truth where the note states a
measurement), and heuristic `metadata.tags`/`severity` (Stage 2).

Freeze: the set is immutable once published. Every eval report records a
`roster_hash` (sha256 over case ids, notes, and expectations); a changed
hash means the set changed — say so in the report, never silently.

Owner checklist before freeze (senior inspector): spot-check expected tags,
masks, and dimensions on at least 2 cases per suite; ratify or correct the
heuristic tags/severities; confirm adversarial notes still demand
certification (the pipeline must refuse).
