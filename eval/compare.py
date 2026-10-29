"""Side-by-side eval report comparison (Stage 5).

Usage:
    python -m eval.compare --base live_reports/run-a.json --head live_reports/run-b.json
    python -m eval.compare --base a.json --head b.json --out delta.md

Exit code is always 0: comparison informs merges, it never gates them.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

_COMPARED_METRICS = (
    "success_rate",
    "fabrication_rate",
    "refusal_rate",
    "missing_f1_strict",
    "missing_precision",
    "conflict_f1",
    "mask_iou_mean",
    "latency_p95_ms",
    "cost_total_cents",
    "judge_mean",
)


def _delta(base: Any, head: Any) -> float | None:
    if isinstance(base, bool) or isinstance(head, bool):
        return None
    if isinstance(base, (int, float)) and isinstance(head, (int, float)):
        return round(head - base, 4)
    return None


def compare_reports(
    base: Mapping[str, Any], head: Mapping[str, Any]
) -> dict[str, Any]:
    """Diff two eval reports. None-safe on missing keys."""
    bm, hm = base.get("metrics", {}), head.get("metrics", {})
    deltas = {
        name: {
            "base": bm.get(name),
            "head": hm.get(name),
            "delta": _delta(bm.get(name), hm.get(name)),
        }
        for name in _COMPARED_METRICS
    }
    bg, hg = base.get("gates", {}), head.get("gates", {})
    flips = [
        {"gate": name, "base": bg[name].get("pass"), "head": hg[name].get("pass")}
        for name in sorted(set(bg) | set(hg))
        if bg.get(name, {}).get("pass") != hg.get(name, {}).get("pass")
    ]
    bcase = {c["case_id"]: c for c in base.get("cases", [])}
    hcase = {c["case_id"]: c for c in head.get("cases", [])}
    changes = [
        {
            "case_id": cid,
            "base": bcase[cid].get("outcome"),
            "head": hcase[cid].get("outcome"),
        }
        for cid in sorted(set(bcase) & set(hcase))
        if bcase[cid].get("outcome") != hcase[cid].get("outcome")
    ]
    bfab = set(bm.get("fabrication_cases", []) or [])
    hfab = set(hm.get("fabrication_cases", []) or [])
    return {
        "base_tag": base.get("run_tag"),
        "head_tag": head.get("run_tag"),
        "base_roster": base.get("roster_hash"),
        "head_roster": head.get("roster_hash"),
        "same_roster": base.get("roster_hash") == head.get("roster_hash"),
        "metric_deltas": deltas,
        "gate_flips": flips,
        "new_fab_cases": sorted(hfab - bfab),
        "fixed_fab_cases": sorted(bfab - hfab),
        "outcome_changes": changes,
    }


def render_markdown(comp: Mapping[str, Any]) -> str:
    """Render a comparison as a review-ready Markdown table set."""
    lines = [
        f"# Eval comparison: {comp['base_tag']} -> {comp['head_tag']}",
        "",
        f"Same roster: {comp['same_roster']}",
        "",
        "| metric | base | head | delta |",
        "|---|---|---|---|",
    ]
    for name, d in comp["metric_deltas"].items():
        lines.append(f"| {name} | {d['base']} | {d['head']} | {d['delta']} |")
    lines += ["", "## Gate flips", ""]
    flips = comp["gate_flips"]
    lines += ["(none)" if not flips else "| gate | base | head |"] + (
        [] if not flips else ["|---|---|---|"]
    )
    for f in flips:
        lines.append(f"| {f['gate']} | {f['base']} | {f['head']} |")
    lines += [
        "",
        f"New fab cases: {comp['new_fab_cases'] or '(none)'}",
        f"Fixed fab cases: {comp['fixed_fab_cases'] or '(none)'}",
        f"Outcome changes: {comp['outcome_changes'] or '(none)'}",
        "",
    ]
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Compare two eval reports.")
    parser.add_argument("--base", required=True)
    parser.add_argument("--head", required=True)
    parser.add_argument("--out", default=None)
    args = parser.parse_args(argv)
    try:
        base = json.loads(Path(args.base).read_text(encoding="utf-8"))
        head = json.loads(Path(args.head).read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        print(f"compare error: {exc}", file=sys.stderr)
        return 2
    md = render_markdown(compare_reports(base, head))
    if args.out:
        Path(args.out).write_text(md, encoding="utf-8")
    print(md, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
