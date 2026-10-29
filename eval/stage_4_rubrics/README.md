# Stage 4: Rubrics (judge pilot, non-gating)

`eval/judge.py` scores narrative clarity 1-5 on a fixed rubric via a Meta
model (`--judge`, live only, default off). Scores land in
`record["judge"]` and `metrics.judge_mean`; no gate reads them — this is
structural (nothing in `_build_report` gates on judge output), not policy.
Judge errors are recorded per case, never raised. Judge token spend is NOT
included in usage totals (pilot limitation). Factual gates (IoU, F1,
fabrication, refusal) stay purely programmatic per PRD.
