"""Wave 4: replay transports, usage threading, tags, roster hash, run tags."""
from __future__ import annotations

from pathlib import Path

import httpx
import pytest

from eval.replay import (
    RecordingTransport,
    ReplayingTransport,
    ReplayMissError,
    cassette_key,
)
from eval.run import _case_metadata, run_eval


def _req(body: bytes = b'{"a":1}', headers: dict | None = None) -> httpx.Request:
    return httpx.Request(
        "POST", "https://mock.eval/v1/responses", content=body, headers=headers or {}
    )


def test_cassette_key_ignores_headers() -> None:
    a = _req(headers={"X-Request-ID": "req_aaa"})
    b = _req(headers={"X-Request-ID": "req_bbb"})
    assert cassette_key(a) == cassette_key(b)
    assert cassette_key(_req(b'{"a":2}')) != cassette_key(a)


def test_record_replay_round_trip(tmp_path: Path) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"ok": True, "echo": request.content.decode()})

    cache = tmp_path / "cache"
    rec = RecordingTransport(httpx.MockTransport(handler), cache)
    res1 = rec.handle_request(_req())
    assert res1.json() == {"ok": True, "echo": '{"a":1}'}
    assert len(list(cache.glob("*.json"))) == 1
    rep = ReplayingTransport(cache)
    res2 = rep.handle_request(_req(headers={"X-Request-ID": "req_other"}))
    assert res2.json() == res1.json()
    assert res2.status_code == 200


def test_replay_miss_fails_closed(tmp_path: Path) -> None:
    (tmp_path / "empty").mkdir()
    with pytest.raises(ReplayMissError, match="no cassette"):
        ReplayingTransport(tmp_path / "empty").handle_request(_req())
    with pytest.raises(FileNotFoundError, match="replay cache not found"):
        ReplayingTransport(tmp_path / "nope")


def test_case_metadata_vectors() -> None:
    m = _case_metadata("clear", "drainage_structure", "culvert with longitudinal crack", "")
    assert m["tags"][:3] == ["clear", "drainage_structure", "crack"]
    assert m["severity"] == "low"
    adv = _case_metadata("adversarial", "bridge_component", "rebar", "")
    assert adv["severity"] == "high"
    assert "corrosion" in _case_metadata("clear", "x", "rust staining", "")["tags"]


def test_roster_hash_stable_and_sensitive(tmp_path: Path) -> None:
    r1 = run_eval(mode="mocked", out_path=tmp_path / "r1.json", limit=2)
    r2 = run_eval(mode="mocked", out_path=tmp_path / "r2.json", limit=2)
    assert r1["roster_hash"] == r2["roster_hash"]
    r3 = run_eval(mode="mocked", out_path=tmp_path / "r3.json", limit=3)
    assert r3["roster_hash"] != r1["roster_hash"]
    assert r1["run_tag"] is None


def test_mocked_records_carry_usage_and_tags(tmp_path: Path) -> None:
    report = run_eval(mode="mocked", out_path=tmp_path / "r.json", limit=4, run_tag="t")
    assert report["run_tag"] == "t"
    ok = [r for r in report["cases"] if r["outcome"] == "ok"]
    assert ok
    for r in ok:
        assert set(r["usage"]) == {"prompt_tokens", "completion_tokens", "total_tokens"}
        assert r["usage_source"] == "mocked"
        assert r["metadata"]["tags"]
    totals = report["metrics"]["usage_total_tokens"]
    assert totals["total_tokens"] >= 0
    assert report["metrics"]["by_tag"]["clear"]["n_cases"] >= 1


def test_record_replay_flags_guarded(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="live mode only"):
        run_eval(mode="mocked", out_path=tmp_path / "r.json", limit=1, record_dir=tmp_path)
    with pytest.raises(ValueError, match="at most one"):
        run_eval(
            mode="live", cases_dir=tmp_path, out_path=tmp_path / "r.json",
            record_dir=tmp_path, replay_dir=tmp_path,
        )
