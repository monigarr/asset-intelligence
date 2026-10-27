"""Eval harness tests: metric math, mocked runs, live-shaped wiring."""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest
from PIL import Image

from eval.run import _CERT_PATTERNS as EVAL_CERT_PATTERNS
from eval.run import (
    binary_f1,
    ece,
    find_certifying_language,
    find_unfounded_dimensions,
    main,
    mask_iou,
    percentile_ms,
    prf_missing,
    run_eval,
)


def test_percentile() -> None:
    assert percentile_ms([10, 20, 30, 40, 50]) == 50.0
    assert percentile_ms([10, 20, 30, 40, 50], 50) == 30.0
    assert percentile_ms([7.5]) == 7.5
    with pytest.raises(ValueError, match="empty"):
        percentile_ms([])


def test_prf_missing() -> None:
    assert prf_missing(["a", "b"], ["a", "b"]) == (1.0, 1.0, 1.0)
    assert prf_missing([], []) == (1.0, 1.0, 1.0)
    p, r, f = prf_missing(["a"], ["a", "b"])
    assert (p, r) == (1.0, 0.5)
    assert f == pytest.approx(2 / 3)
    assert prf_missing([], ["a"])[2] == 0.0


def test_binary_f1() -> None:
    # tp=1, fp=0, fn=1 -> P=1.0, R=0.5, F1=2/3
    assert binary_f1([True, True, False], [True, False, False])[2] == pytest.approx(2 / 3)
    assert binary_f1([False, False], [False, False]) == (1.0, 1.0, 1.0)
    with pytest.raises(ValueError, match="length"):
        binary_f1([True], [])


def test_mask_iou() -> None:
    full = {"size": [2, 2], "counts": [0, 4]}
    empty = {"size": [2, 2], "counts": [4]}
    half = {"size": [2, 2], "counts": [2, 2]}
    assert mask_iou(full, full) == 1.0
    assert mask_iou(empty, empty) == 1.0
    assert mask_iou(full, empty) == 0.0
    assert mask_iou(full, half) == 0.5
    with pytest.raises(ValueError, match="size mismatch"):
        mask_iou(full, {"size": [3, 3], "counts": [9]})


def test_ece() -> None:
    assert ece([0.0, 0.0], [True, True]) == 0.0
    assert ece([0.0, 0.0], [False, False]) == 1.0
    assert 0.0 < ece([0.2, 0.8], [True, False]) < 0.5
    with pytest.raises(ValueError, match="length"):
        ece([0.1], [])


def test_fabrication_scan() -> None:
    assert find_unfounded_dimensions(["crack about 2ft long"], "note says 2ft") == []
    assert find_unfounded_dimensions(["crack about 3ft long"], "note says 2ft") != []
    assert find_unfounded_dimensions(["2 regions in mask_1"], "plain note") == []
    assert find_unfounded_dimensions(["width 2.0cm"], "width 2cm here") == []


def test_cert_language_and_drift_guard() -> None:
    assert find_certifying_language(["I certify this as safe"]) != []
    assert find_certifying_language(["Request qualified inspection"]) == []

    from app.validator.schema import _CERT_PATTERNS as VAL_PATTERNS

    assert [p.pattern for p in EVAL_CERT_PATTERNS] == [p.pattern for p in VAL_PATTERNS]


def test_mocked_run_small(tmp_path: Path) -> None:
    out = tmp_path / "report.json"
    report = run_eval(mode="mocked", out_path=out, limit=3)
    assert report["mode"] == "mocked"
    assert report["n_cases"] == 3
    assert report["overall_pass"] is True
    assert report["metrics"]["mask_iou_mean"] == 1.0
    assert out.exists()
    assert json.loads(out.read_text(encoding="utf-8"))["overall_pass"] is True


def test_mocked_first_case_per_suite(tmp_path: Path) -> None:
    for suite in ("clear", "incomplete", "contradictory", "ambiguous", "adversarial"):
        report = run_eval(
            mode="mocked", out_path=tmp_path / f"{suite}.json",
            suites=[suite], limit=1,
        )
        assert report["overall_pass"] is True, suite
        assert report["outcomes"] == {"ok": 1, "validator_rejected": 0, "upstream_error": 0}


def test_live_shaped_with_injected_client(tmp_path: Path) -> None:
    from app.gateway import MetaClient, Settings
    from eval.run import MockedModelServer

    cases_dir = tmp_path / "cases"
    (cases_dir / "images").mkdir(parents=True)
    img = Image.new("RGB", (16, 12), (200, 200, 200))
    img.save(cases_dir / "images" / "live-01.png")
    (cases_dir / "live-01.json").write_text(
        json.dumps({
            "case_id": "live-01", "suite": "clear",
            "image_file": "images/live-01.png",
            "image_prompt": "x", "note": "Crack near top edge.",
            "asset_meta": {"asset_id": "L-1", "asset_type": "drainage_structure"},
            "expected": {"missing_any": False, "expect_discrepancy": False,
                         "expect_uncertain": False, "adversarial": False},
        }),
        encoding="utf-8",
    )
    server = MockedModelServer([])
    settings = Settings(api_key="t", base_url="https://mock.eval/v1")
    client = MetaClient(
        settings=settings, transport=httpx.MockTransport(server),
        retry_wait=lambda _s: 0,
    )
    report = run_eval(mode="live", cases_dir=cases_dir,
                      out_path=tmp_path / "live.json", client=client)
    assert report["mode"] == "live"
    assert report["overall_pass"] is True
    assert report["metrics"]["mask_iou_mean"] is None  # no truth in live mode


def test_live_missing_dir_error(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="run python -m app.synthetic"):
        run_eval(mode="live", cases_dir=tmp_path / "nope", out_path=tmp_path / "r.json")
    assert main(["--mode", "live", "--cases-dir", str(tmp_path / "nope"),
                 "--out", str(tmp_path / "r.json")]) == 2


def test_live_no_key_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from app.gateway.errors import MetaAuthError

    monkeypatch.setattr("app.gateway.config.load_dotenv", lambda *a, **k: None)
    monkeypatch.delenv("META_API_KEY", raising=False)
    cases_dir = tmp_path / "cases"
    (cases_dir / "images").mkdir(parents=True)
    Image.new("RGB", (8, 8)).save(cases_dir / "images" / "a.png")
    (cases_dir / "a.json").write_text(
        json.dumps({"case_id": "a", "suite": "clear", "image_file": "images/a.png",
                    "image_prompt": "x", "note": "n", "asset_meta": {}, "expected": {}}),
        encoding="utf-8",
    )
    with pytest.raises(MetaAuthError, match="META_API_KEY"):
        run_eval(mode="live", cases_dir=cases_dir, out_path=tmp_path / "r.json")


def test_cli_mocked_and_bad_mode(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    out = tmp_path / "cli.json"
    assert main(["--mode", "mocked", "--limit", "2", "--out", str(out)]) == 0
    printed = capsys.readouterr().out
    assert "mode=mocked" in printed
    assert "gate fabrication_rate" in printed
    assert out.exists()
    with pytest.raises(SystemExit) as ei:
        main(["--mode", "bogus"])
    assert ei.value.code == 2
    with pytest.raises(ValueError, match="no cases selected"):
        run_eval(mode="mocked", out_path=tmp_path / "r.json", limit=0)
