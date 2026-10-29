"""Wave 5: judge pilot + run comparison."""
from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest
from PIL import Image

from eval.compare import compare_reports
from eval.compare import main as compare_main
from eval.judge import score_clarity, score_from_data
from eval.run import run_eval


def test_score_from_data_validates() -> None:
    assert score_from_data({"score": 4, "rationale": "  clear  "}) == {
        "score": 4,
        "rationale": "clear",
    }
    with pytest.raises(ValueError, match="int 1-5"):
        score_from_data({"score": 7, "rationale": "x"})
    with pytest.raises(ValueError, match="int 1-5"):
        score_from_data({"score": True, "rationale": "x"})
    with pytest.raises(ValueError, match="non-blank"):
        score_from_data({"score": 3, "rationale": "   "})
    with pytest.raises(TypeError, match="must be an object"):
        score_from_data([4])


def test_score_clarity_prompts_and_normalizes() -> None:
    seen: list = []

    def fake_chat(messages: list) -> dict:
        seen.extend(messages)
        return {"score": 5, "rationale": "  crystal  "}

    out = score_clarity(["crack observed"], fake_chat)
    assert out == {"score": 5, "rationale": "crystal"}
    blob = "\n".join(m["content"] for m in seen)
    assert "narrative clarity" in blob and "crack observed" in blob


def _live_case_dir(root: Path) -> Path:
    cases_dir = root / "cases"
    (cases_dir / "images").mkdir(parents=True)
    Image.new("RGB", (16, 12), (200, 200, 200)).save(cases_dir / "images" / "j-01.png")
    (cases_dir / "j-01.json").write_text(
        json.dumps({
            "case_id": "j-01", "suite": "clear", "image_file": "images/j-01.png",
            "image_prompt": "x", "note": "Crack near top edge.",
            "asset_meta": {"asset_id": "J-1", "asset_type": "drainage_structure"},
            "expected": {"missing_any": False, "expect_discrepancy": False,
                         "expect_uncertain": False, "adversarial": False},
        }),
        encoding="utf-8",
    )
    return cases_dir


def test_judge_scores_live_records_without_gating(tmp_path: Path) -> None:
    from app.gateway import MetaClient, Settings
    from eval.run import MockedModelServer

    server = MockedModelServer([])

    def route(request: httpx.Request) -> httpx.Response:
        if b"narrative clarity" in request.content:
            content = '{"score": 4, "rationale": "clear and direct"}'
            payload = {"choices": [{"message": {"content": content}}]}
            return httpx.Response(200, json=payload)
        return server(request)

    settings = Settings(api_key="t", base_url="https://mock.eval/v1")
    client = MetaClient(
        settings=settings, transport=httpx.MockTransport(route),
        retry_wait=lambda _s: 0,
    )
    report = run_eval(
        mode="live", cases_dir=_live_case_dir(tmp_path),
        out_path=tmp_path / "j.json", client=client, judge=True,
    )
    rec = report["cases"][0]
    assert rec["outcome"] == "ok"
    assert rec["judge"] == {"score": 4, "rationale": "clear and direct"}
    assert report["metrics"]["judge_mean"] == 4.0
    assert report["metrics"]["judge_n_scored"] == 1
    assert "judge" not in report["gates"]


def test_judge_records_errors_without_crashing(tmp_path: Path) -> None:
    from app.gateway import MetaClient, Settings
    from eval.run import MockedModelServer

    server = MockedModelServer([])

    def route(request: httpx.Request) -> httpx.Response:
        if b"narrative clarity" in request.content:
            content = '{"score": 9}'
            payload = {"choices": [{"message": {"content": content}}]}
            return httpx.Response(200, json=payload)
        return server(request)

    settings = Settings(api_key="t", base_url="https://mock.eval/v1")
    client = MetaClient(
        settings=settings, transport=httpx.MockTransport(route),
        retry_wait=lambda _s: 0,
    )
    report = run_eval(
        mode="live", cases_dir=_live_case_dir(tmp_path),
        out_path=tmp_path / "j.json", client=client, judge=True,
    )
    judge = report["cases"][0]["judge"]
    assert judge["score"] is None and "error" in judge
    assert report["metrics"]["judge_mean"] is None


def test_judge_needs_live(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="judge needs live mode"):
        run_eval(mode="mocked", out_path=tmp_path / "r.json", limit=1, judge=True)


def _mini_report(tag: str, success: float, fab_cases: list, outcome: str) -> dict:
    return {
        "run_tag": tag, "roster_hash": "abc",
        "metrics": {
            "success_rate": success, "fabrication_rate": 0.0,
            "fabrication_cases": fab_cases, "cost_total_cents": 1.0,
        },
        "gates": {"success_rate": {"pass": success == 1.0}},
        "cases": [{"case_id": "c-1", "outcome": outcome}],
    }


def test_compare_reports_deltas_and_flips() -> None:
    base = _mini_report("a", 1.0, [], "ok")
    head = _mini_report("b", 0.5, ["c-1"], "validator_rejected")
    comp = compare_reports(base, head)
    assert comp["same_roster"] is True
    assert comp["metric_deltas"]["success_rate"] == {
        "base": 1.0, "head": 0.5, "delta": -0.5}
    assert comp["gate_flips"] == [{"gate": "success_rate", "base": True, "head": False}]
    assert comp["new_fab_cases"] == ["c-1"] and comp["fixed_fab_cases"] == []
    assert comp["outcome_changes"] == [
        {"case_id": "c-1", "base": "ok", "head": "validator_rejected"}]


def test_compare_cli(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    base_p, head_p = tmp_path / "a.json", tmp_path / "b.json"
    base_p.write_text(json.dumps(_mini_report("a", 1.0, [], "ok")), encoding="utf-8")
    head_p.write_text(json.dumps(_mini_report("b", 1.0, [], "ok")), encoding="utf-8")
    assert compare_main(["--base", str(base_p), "--head", str(head_p)]) == 0
    out = capsys.readouterr().out
    assert "| success_rate | 1.0 | 1.0 | 0.0 |" in out
    assert compare_main(["--base", str(tmp_path / "nope"), "--head", str(head_p)]) == 2
