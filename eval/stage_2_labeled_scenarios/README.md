# Stage 2: Labeled Scenarios

Cases carry `metadata: {"tags": [...], "severity": "low|medium|high"}`.
Tags derive from suite + asset type + defect keywords
(`eval/run.py::_case_metadata`, heuristic v0 — ratify in the Stage 1
inspector audit). Every report includes a `by_tag` table (n_cases, n_fab,
cost) so failures can be pinned to infrastructure slices
(e.g. `corrosion` vs `crack`) instead of treated uniformly.
