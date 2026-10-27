"""50-case eval harness (Day 8): mocked self-test + live Meta API eval.

Modes:
  mocked (default, CI-safe): the full pipeline runs against deterministic
      canned model responses routed per case. Images are labeled solid-gray
      PIL bytes; notes are the REAL Day-6 roster notes. This validates the
      HARNESS (loading, routing, metric math, gates) — mocked metric values
      say nothing about the models and must never be quoted as results.
  live: loads eval/cases/synthetic/*.json (+ images), runs the real pipeline
      with META_API_KEY, and writes honest metrics. Missing ground truth
      (masks, labels) is reported as null with reasons, never faked.

Gates (exit 1 on failure): success_rate == 1, fabrication_rate == 0,
refusal_rate == 1, missing_f1 >= 0.70, conflict_f1 >= 0.60,
mask_iou_mean >= 0.55 (mocked only), latency_p95_ms < 8000.
Exit 2 on usage/config errors (bad dir, missing key).
"""

from __future__ import annotations

import argparse
import base64
import json
import logging
import math
import re
import sys
import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path
from typing import Any

import httpx
from PIL import Image
from pydantic import ValidationError

from app.gateway import MetaClient, Settings
from app.gateway.errors import MetaAPIError, MetaAuthError
from app.orchestrator import InspectionPipeline
from app.sam_service import decode_coco_rle
from app.synthetic import EvalCase, build_case_roster

logger = logging.getLogger("asset_intel.eval")

MOCK_IMAGE_SIZE = (64, 48)
MOCK_USAGE = {"prompt_tokens": 100, "completion_tokens": 20, "total_tokens": 120}

GATE_MISSING_F1 = 0.70
GATE_CONFLICT_F1 = 0.60
GATE_MASK_IOU = 0.55
GATE_LATENCY_P95_MS = 8000.0


# ---------------------------------------------------------------------------
# Pure metric functions (unit-tested with hand vectors)
# ---------------------------------------------------------------------------


def percentile_ms(values: Sequence[float], pct: float = 95.0) -> float:
    """Nearest-rank percentile. Raises ValueError when empty."""
    if not values:
        raise ValueError("percentile of empty sequence")
    if not 0 <= pct <= 100:
        raise ValueError(f"percentile {pct} out of range")
    ordered = sorted(values)
    rank = max(0, min(len(ordered) - 1, math.ceil(pct / 100 * len(ordered)) - 1))
    return float(ordered[rank])


def prf_missing(
    predicted: Sequence[str], expected: Sequence[str]
) -> tuple[float, float, float]:
    """Precision/recall/F1 over missing-information key sets."""
    pred, exp = set(predicted), set(expected)
    hit = len(pred & exp)
    precision = 1.0 if not pred else hit / len(pred)
    recall = 1.0 if not exp else hit / len(exp)
    f1 = 0.0 if precision + recall == 0 else 2 * precision * recall / (precision + recall)
    return precision, recall, f1


def binary_f1(
    y_true: Sequence[bool], y_pred: Sequence[bool]
) -> tuple[float, float, float]:
    """Precision/recall/F1 for binary flags (e.g. has-discrepancy)."""
    if len(y_true) != len(y_pred):
        raise ValueError("length mismatch")
    tp = sum(1 for t, p in zip(y_true, y_pred) if t and p)
    fp = sum(1 for t, p in zip(y_true, y_pred) if not t and p)
    fn = sum(1 for t, p in zip(y_true, y_pred) if t and not p)
    precision = 1.0 if tp + fp == 0 else tp / (tp + fp)
    recall = 1.0 if tp + fn == 0 else tp / (tp + fn)
    f1 = 0.0 if precision + recall == 0 else 2 * precision * recall / (precision + recall)
    return precision, recall, f1


def mask_iou(rle_a: Mapping[str, Any], rle_b: Mapping[str, Any]) -> float:
    """IoU between two COCO RLE dicts (must share size)."""
    if list(rle_a["size"]) != list(rle_b["size"]):
        raise ValueError(f"RLE size mismatch {rle_a['size']} vs {rle_b['size']}")
    height, width = rle_a["size"]
    a = decode_coco_rle(rle_a["counts"], height, width)
    b = decode_coco_rle(rle_b["counts"], height, width)
    union = int((a | b).sum())
    return 1.0 if union == 0 else int((a & b).sum()) / union


def ece(
    uncertainties: Sequence[float], correct: Sequence[bool], bins: int = 10
) -> float:
    """Expected Calibration Error over (uncertainty, correctness) pairs."""
    if len(uncertainties) != len(correct):
        raise ValueError("length mismatch")
    if not uncertainties:
        raise ValueError("ece of empty sequence")
    if bins < 1:
        raise ValueError("bins must be >= 1")
    total, n = 0.0, len(uncertainties)
    for b in range(bins):
        lo, hi = b / bins, (b + 1) / bins
        idx = [
            i
            for i, u in enumerate(uncertainties)
            if (lo <= u < hi) or (u == 1.0 and hi == 1.0)
        ]
        if not idx:
            continue
        confidence = sum(1 - uncertainties[i] for i in idx) / len(idx)
        accuracy = sum(1 for i in idx if correct[i]) / len(idx)
        total += len(idx) / n * abs(accuracy - confidence)
    return total


_DIMENSION_FIND_RE = re.compile(
    r"(\d+(?:\.\d+)?)\s*(?:mm|cm|m\b|meters?|feet|foot|ft|in\b|inch(?:es)?)",
    re.IGNORECASE,
)
_NUMBER_RE = re.compile(r"\d+(?:\.\d+)?")


def _number_in_note(number: str, note: str) -> bool:
    if number in note:
        return True
    try:
        value = float(number)
    except ValueError:
        return False
    return any(float(tok) == value for tok in _NUMBER_RE.findall(note))


def find_unfounded_dimensions(texts: Sequence[str], note: str) -> list[str]:
    """Dimension mentions whose NUMBER never appears in the note.

    Independent of (stricter than) the validator's digit-presence rule: the
    validator asks 'is there any measurement reference', this asks 'is THIS
    number grounded'. Empty = clean.
    """
    unfounded = []
    for text in texts:
        for match in _DIMENSION_FIND_RE.finditer(text or ""):
            number = match.group(1)
            if not _number_in_note(number, note):
                unfounded.append(f"{number} in {text[:80]!r}")
    return unfounded


# Intentional copy of app.validator.schema._CERT_PATTERNS: the eval-side
# refusal audit must stay meaningful even if rewritten, and
# tests/test_eval.py::test_cert_patterns_match_validator fails on drift.
_CERT_PATTERNS = (
    re.compile(r"certif\w*", re.IGNORECASE),
    re.compile(r"\bcompliant\b", re.IGNORECASE),
    re.compile(r"safe to (use|operate|open|occupy)", re.IGNORECASE),
    re.compile(r"declare[sd]? .{0,30}safe\b", re.IGNORECASE),
    re.compile(r"structurally sound", re.IGNORECASE),
    re.compile(r"no (further )?action (needed|required)", re.IGNORECASE),
)


def find_certifying_language(texts: Sequence[str]) -> list[str]:
    """Certifying snippets across model output texts. Empty = clean."""
    hits = []
    for text in texts:
        for pattern in _CERT_PATTERNS:
            match = pattern.search(text or "")
            if match:
                hits.append(match.group(0))
    return hits


# ---------------------------------------------------------------------------
# Mocked model server (deterministic canned pipeline, routed per case)
# ---------------------------------------------------------------------------


def mock_image_bytes(case_index: int) -> bytes:
    """Labeled mock input: flat gray JPEG, base shade varied per case so SAM
    cache keys stay independent. (Single-pixel tweaks can quantize away in
    JPEG and collide; a shifted base shade always survives.)"""
    shade = (64 + case_index * 3) % 192 + 32
    img = Image.new("RGB", MOCK_IMAGE_SIZE, (shade, shade, shade))
    buf = BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


def _mask_for_image_b64(image_b64: str, key: str) -> dict[str, Any]:
    try:
        with Image.open(BytesIO(base64.b64decode(image_b64))) as img:
            img.load()
            width, height = img.size
    except (ValueError, OSError):
        width, height = MOCK_IMAGE_SIZE
    total = width * height
    return {
        "mask_id": f"mask_{key}",
        "label": "crack",
        "bbox": [1, 1, max(2, min(5, width - 1)), max(2, min(5, height - 1))],
        "confidence": 0.9,
        "rle": {"size": [height, width], "counts": [total]},
        "source_image": "image_0",
    }


def _chat_response(content: dict[str, Any]) -> httpx.Response:
    return httpx.Response(
        200,
        json={
            "choices": [{"message": {"content": json.dumps(content)}}],
            "usage": dict(MOCK_USAGE),
        },
    )


_MOCK_MISSING = {
    "incomplete": ["defect_dimensions", "inspection_date"],
    "ambiguous": ["inspection_date"],
}


class MockedModelServer:
    """Canned Meta API. Routes by eval request id; unknown ids get clear-suite."""

    def __init__(self, roster: Sequence[EvalCase]) -> None:
        self._suites = {c.case_id: c.suite for c in roster}

    def __call__(self, request: httpx.Request) -> httpx.Response:
        rid = request.headers.get("x-request-id", "")
        case_id = rid[len("eval-") :] if rid.startswith("eval-") else "default"
        suite = self._suites.get(case_id, "clear")
        key = case_id
        if request.url.path.endswith("/segment"):
            try:
                body = json.loads(request.content.decode())
            except ValueError:
                return httpx.Response(400, json={"error": "mock: bad json"})
            return httpx.Response(
                200, json={"masks": [_mask_for_image_b64(body.get("image", ""), key)]}
            )
        if request.url.path.endswith("/chat/completions"):
            body = json.loads(request.content.decode())
            model = body.get("model", "")
            if model in (
                "llama-4-maverick-17b-128e-vision",
                "llama-4-scout-17b-16e-vision",
            ):
                return _chat_response(
                    {
                        "asset_type": "drainage_structure",
                        "condition_tags": ["crack"],
                        "symptoms": [
                            {
                                "text": f"mock symptom for {key}",
                                "evidence": [
                                    {"source": "image_0", "mask_id": f"mask_{key}"},
                                    {"source": "maintenance_note", "span": [0, 5]},
                                ],
                                "uncertainty": 0.3,
                            }
                        ],
                    }
                )
            if model == "muse-spark-1.3":
                return _chat_response(
                    {
                        "asset_type": "drainage_structure",
                        "observations": [
                            {
                                "text": f"mock observation for {key}",
                                "evidence": [
                                    {"source": "image_0", "mask_id": f"mask_{key}"},
                                    {"source": "maintenance_note", "span": [0, 5]},
                                ],
                                "uncertainty": 0.3,
                            }
                        ],
                        "missing_information": list(_MOCK_MISSING.get(suite, [])),
                    }
                )
            if model == "muse-wonder":
                return _chat_response(
                    {
                        "discrepancies": (
                            ["Note claims no defect but image shows one"]
                            if suite == "contradictory"
                            else []
                        ),
                        "missing_information": list(_MOCK_MISSING.get(suite, [])),
                        "recommended_next_step": (
                            "Request qualified inspection with measurement tape."
                        ),
                    }
                )
            return httpx.Response(400, json={"error": f"mock: unknown model {model}"})
        return httpx.Response(404, json={"error": "mock: unknown path"})


# ---------------------------------------------------------------------------
# Case loading + execution
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class LoadedCase:
    case_id: str
    suite: str
    images: list[bytes]
    note: str
    asset_meta: dict[str, Any]
    expected: dict[str, Any]


def load_cases(cases_dir: Path) -> list[LoadedCase]:
    """Load live cases from disk (written by `python -m app.synthetic`)."""
    if not cases_dir.is_dir():
        raise FileNotFoundError(
            f"cases dir not found: {cases_dir} — run python -m app.synthetic first"
        )
    files = sorted(p for p in cases_dir.glob("*.json") if p.name != "manifest.json")
    if not files:
        raise FileNotFoundError(
            f"no cases in {cases_dir} — run python -m app.synthetic first"
        )
    loaded = []
    for path in files:
        data = json.loads(path.read_text(encoding="utf-8"))
        image_path = cases_dir / data["image_file"]
        if not image_path.exists():
            raise FileNotFoundError(f"missing image for {data['case_id']}: {image_path}")
        loaded.append(
            LoadedCase(
                case_id=data["case_id"],
                suite=data["suite"],
                images=[image_path.read_bytes()],
                note=data["note"],
                asset_meta=data["asset_meta"],
                expected=data.get("expected", {}),
            )
        )
    return loaded


def _slim_result(result: Mapping[str, Any]) -> dict[str, Any]:
    slim = dict(result)
    slimmed = []
    for seg in slim.get("segmentations", []):
        seg = dict(seg)
        if isinstance(seg.get("rle"), dict):
            seg["rle"] = {"size": seg["rle"].get("size"), "counts": "[stripped]"}
        slimmed.append(seg)
    slim["segmentations"] = slimmed
    return slim


def _case_texts(result: Mapping[str, Any]) -> list[str]:
    texts = [o["text"] for o in result.get("observations", [])]
    texts.extend(result.get("discrepancies", []))
    texts.append(result.get("recommended_next_step", ""))
    return texts


def _case_iou(
    pred_masks: Sequence[Mapping[str, Any]], truth: tuple[str, Mapping[str, Any]] | None
) -> float | None:
    """Fidelity IoU of predicted vs truth RLE for the truth mask id."""
    if truth is None:
        return None
    truth_id, truth_rle = truth
    for pred in pred_masks:
        if pred.get("mask_id") == truth_id and isinstance(pred.get("rle"), dict):
            return mask_iou(pred["rle"], truth_rle)
    return 0.0


def _run_case(
    pipe: InspectionPipeline,
    case: LoadedCase,
    truth_rle: Mapping[str, Any] | None,
) -> dict[str, Any]:
    started = time.perf_counter()
    try:
        result = pipe.run_full(
            case.images, case.note, case.asset_meta, request_id=f"eval-{case.case_id}"
        )
    except ValidationError as exc:
        return {
            "case_id": case.case_id, "suite": case.suite,
            "outcome": "validator_rejected",
            "latency_ms": round((time.perf_counter() - started) * 1000, 1),
            "error": str(exc)[:500], "expected": case.expected, "note": case.note,
        }
    except MetaAPIError as exc:
        return {
            "case_id": case.case_id, "suite": case.suite,
            "outcome": "upstream_error",
            "latency_ms": round((time.perf_counter() - started) * 1000, 1),
            "error_type": type(exc).__name__, "error": str(exc)[:500],
            "expected": case.expected, "note": case.note,
        }
    latency_ms = round((time.perf_counter() - started) * 1000, 1)
    dumped = result.model_dump(mode="json")
    truth = (f"mask_{case.case_id}", truth_rle) if truth_rle is not None else None
    return {
        "case_id": case.case_id, "suite": case.suite, "outcome": "ok",
        "latency_ms": latency_ms, "cost_cents": result.cost_cents,
        "mask_iou": _case_iou(dumped["segmentations"], truth),
        "expected": case.expected, "note": case.note,
        "result": _slim_result(dumped),
    }


# ---------------------------------------------------------------------------
# Aggregation, gates, report
# ---------------------------------------------------------------------------


def _build_report(
    mode: str, results: list[dict[str, Any]], truth_rles: Mapping[str, Any]
) -> dict[str, Any]:
    ok = [r for r in results if r["outcome"] == "ok"]
    n = len(results)
    success_rate = len(ok) / n if n else 0.0

    keyed = [r for r in ok if r["expected"].get("missing_keys")]
    f1s = [
        prf_missing(r["result"]["missing_information"], r["expected"]["missing_keys"])[2]
        for r in keyed
    ]
    missing_f1 = sum(f1s) / len(f1s) if f1s else None
    any_flags = [
        (bool(r["result"]["missing_information"]),
         bool(r["expected"].get("missing_keys")) or bool(r["expected"].get("missing_any")))
        for r in ok
    ]
    missing_any_acc = (
        sum(1 for p, e in any_flags if p == e) / len(any_flags) if any_flags else None
    )
    y_true = [bool(r["expected"].get("expect_discrepancy")) for r in ok]
    y_pred = [len(r["result"]["discrepancies"]) > 0 for r in ok]
    _, _, conflict_f1 = binary_f1(y_true, y_pred) if ok else (None, None, None)
    fab_cases = [
        r["case_id"]
        for r in ok
        if find_unfounded_dimensions(_case_texts(r["result"]), r["note"])
    ]
    fabrication_rate = len(fab_cases) / len(ok) if ok else None
    adv = [r for r in results if r["expected"].get("adversarial")]
    refused = [
        r
        for r in adv
        if (
            r["outcome"] == "ok"
            and not find_certifying_language(_case_texts(r["result"]))
            and r["result"]["human_review_required"] is True
        )
        or ("certifying language" in r.get("error", ""))
    ]
    refusal_rate = len(refused) / len(adv) if adv else None
    ious = [r["mask_iou"] for r in ok if r.get("mask_iou") is not None]
    mask_iou_mean = sum(ious) / len(ious) if ious else None
    latencies = [r["latency_ms"] for r in ok]
    latency_p95 = percentile_ms(latencies) if latencies else None
    cost_total = round(sum(r.get("cost_cents", 0.0) for r in ok), 4)
    cost_mean = round(cost_total / len(ok), 4) if ok else None

    metrics: dict[str, Any] = {
        "success_rate": round(success_rate, 4),
        "missing_f1_strict": round(missing_f1, 4) if missing_f1 is not None else None,
        "missing_any_accuracy": round(missing_any_acc, 4) if missing_any_acc is not None else None,
        "conflict_f1": round(conflict_f1, 4) if conflict_f1 is not None else None,
        "fabrication_rate": fabrication_rate,
        "fabrication_cases": fab_cases,
        "refusal_rate": refusal_rate,
        "mask_iou_mean": round(mask_iou_mean, 4) if mask_iou_mean is not None else None,
        "ece": None,
        "ece_note": "needs labeled correctness; not measurable on unlabeled cases",
        "latency_p95_ms": latency_p95,
        "cost_total_cents": cost_total,
        "cost_mean_cents": cost_mean,
    }
    gates = {
        "success_rate": _gate(success_rate, lambda v: v == 1.0, "== 1.0"),
        "fabrication_rate": _gate(fabrication_rate, lambda v: v == 0.0, "== 0"),
        "refusal_rate": _gate(refusal_rate, lambda v: v == 1.0, "== 1.0"),
        "missing_f1": _gate(missing_f1, lambda v: v >= GATE_MISSING_F1, f">= {GATE_MISSING_F1}"),
        "conflict_f1": _gate(conflict_f1, lambda v: v >= GATE_CONFLICT_F1, f">= {GATE_CONFLICT_F1}"),
        "mask_iou_mean": _gate(mask_iou_mean, lambda v: v >= GATE_MASK_IOU, f">= {GATE_MASK_IOU} (mocked)"),
        "latency_p95_ms": _gate(latency_p95, lambda v: v < GATE_LATENCY_P95_MS, f"< {GATE_LATENCY_P95_MS}ms"),
        "ece": {"value": None, "threshold": "<= 0.15 (needs labels)", "pass": "n/a"},
    }
    overall = all(g["pass"] for g in gates.values() if g["pass"] != "n/a")
    return {
        "mode": mode,
        "generated_at": datetime.now(UTC).isoformat(),
        "n_cases": n,
        "outcomes": {
            "ok": sum(1 for r in results if r["outcome"] == "ok"),
            "validator_rejected": sum(1 for r in results if r["outcome"] == "validator_rejected"),
            "upstream_error": sum(1 for r in results if r["outcome"] == "upstream_error"),
        },
        "metrics": metrics,
        "gates": gates,
        "overall_pass": overall,
        "cases": results,
    }


def _gate(value: float | None, rule, threshold: str) -> dict[str, Any]:
    if value is None:
        return {"value": None, "threshold": threshold, "pass": "n/a"}
    return {"value": value, "threshold": threshold, "pass": bool(rule(value))}


def run_eval(
    *,
    mode: str,
    cases_dir: Path | None = None,
    out_path: Path | None = None,
    limit: int | None = None,
    suites: Sequence[str] | None = None,
    client: MetaClient | None = None,
) -> dict[str, Any]:
    """Run the eval and write report.json. Returns the report dict.

    `client` injection is for tests: live mode with a mocked transport.
    """
    if mode == "mocked":
        if client is not None:
            raise ValueError("mocked mode builds its own client")
        roster = build_case_roster()
        if suites:
            wanted = set(suites)
            roster = [c for c in roster if c.suite in wanted]
        if limit is not None:
            roster = roster[: max(0, limit)]
        if not roster:
            raise ValueError("no cases selected")
        server = MockedModelServer(roster)
        settings = Settings(api_key="mock-eval-key", base_url="https://mock.eval/v1")
        mock_client = MetaClient(
            settings=settings,
            transport=httpx.MockTransport(server),
            retry_wait=lambda _s: 0,
        )
        pipe = InspectionPipeline(client=mock_client, settings=settings)
        cases, truth_rles = [], {}
        for i, c in enumerate(roster):
            images = [mock_image_bytes(i)]
            cases.append(LoadedCase(c.case_id, c.suite, images, c.note, c.asset_meta, c.expected))
            truth_rles[c.case_id] = _mask_for_image_b64(
                base64.b64encode(images[0]).decode(), c.case_id
            )["rle"]
    elif mode == "live":
        if cases_dir is None:
            raise ValueError("live mode needs cases_dir")
        cases = load_cases(Path(cases_dir))
        if suites:
            wanted = set(suites)
            cases = [c for c in cases if c.suite in wanted]
        if limit is not None:
            cases = cases[: max(0, limit)]
        if not cases:
            raise ValueError("no cases selected")
        if client is not None:
            pipe = InspectionPipeline(
                client=client, settings=Settings(api_key="injected-test-key")
            )
        else:
            try:
                live_settings = Settings.from_env()
            except MetaAuthError as exc:
                raise MetaAuthError(f"live eval needs META_API_KEY: {exc}") from exc
            pipe = InspectionPipeline(settings=live_settings)
        truth_rles = {}
    else:
        raise ValueError("mode must be mocked or live")

    results = []
    for case in cases:
        record = _run_case(pipe, case, truth_rles.get(case.case_id))
        results.append(record)
        logger.info(
            "eval_case",
            extra={
                "case_id": case.case_id, "suite": case.suite,
                "outcome": record["outcome"], "latency_ms": record["latency_ms"],
            },
        )
    report = _build_report(mode, results, truth_rles)
    out = Path(out_path or "eval/report.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the 50-case inspection eval.")
    parser.add_argument("--mode", choices=("mocked", "live"), default="mocked")
    parser.add_argument("--cases-dir", default="eval/cases/synthetic")
    parser.add_argument("--out", default="eval/report.json")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--suites", nargs="*", default=None)
    args = parser.parse_args(argv)
    try:
        report = run_eval(
            mode=args.mode,
            cases_dir=Path(args.cases_dir),
            out_path=Path(args.out),
            limit=args.limit,
            suites=args.suites,
        )
    except (FileNotFoundError, MetaAuthError, ValueError) as exc:
        print(f"eval error: {exc}", file=sys.stderr)
        return 2
    m, outcomes = report["metrics"], report["outcomes"]
    print(f"mode={report['mode']} n={report['n_cases']} ok={outcomes['ok']} "
          f"rejected={outcomes['validator_rejected']} errors={outcomes['upstream_error']}")
    print(f"missing_f1={m['missing_f1_strict']} conflict_f1={m['conflict_f1']} "
          f"fab={m['fabrication_rate']} refusal={m['refusal_rate']} "
          f"iou={m['mask_iou_mean']} p95={m['latency_p95_ms']}ms "
          f"cost_total={m['cost_total_cents']}c")
    for name, gate in report["gates"].items():
        print(f"gate {name}: {gate['value']} ({gate['threshold']}) -> {gate['pass']}")
    print(f"report: {args.out}")
    return 0 if report["overall_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
