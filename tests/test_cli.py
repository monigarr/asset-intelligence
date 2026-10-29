"""CLI tests (stubbed pipeline, tiny real PNGs, no network)."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from PIL import Image

from app.cli import main


def _png(path: Path) -> str:
    img = Image.new("RGB", (16, 12), (90, 90, 90))
    img.save(path, format="PNG")
    return str(path)


def _stub_pipeline(payload: dict[str, Any], segments: list | None = None):  # type: ignore[no-untyped-def]
    result = SimpleNamespace(
        segmentations=segments or [],
        model_dump=lambda mode=None: payload,
    )
    return SimpleNamespace(run_full=lambda *a, **k: result)


def test_inspect_prints_json_and_returns_zero(
    tmp_path: Path, capsys: Any
) -> None:
    img = _png(tmp_path / "a.png")
    payload = {"request_id": "r1", "segmentations": [], "human_review_required": True}
    code = main(["inspect", "--image", img, "--note", "crack"], pipeline=_stub_pipeline(payload))
    assert code == 0
    out, _ = capsys.readouterr()
    assert json.loads(out)["request_id"] == "r1"


def test_inspect_writes_out_and_overlays(
    tmp_path: Path, monkeypatch: object, capsys: Any
) -> None:
    import app.cli as cli_mod

    img = _png(tmp_path / "a.png")
    seg = SimpleNamespace(source_image="image_0", mask_id="mask_1")
    payload = {"request_id": "r2", "segmentations": [{"mask_id": "mask_1"}]}
    calls: list[tuple[bytes, list]] = []

    def _fake_render(image_bytes: bytes, masks):  # type: ignore[no-untyped-def]
        calls.append((image_bytes, list(masks)))
        return b"PNG"

    monkeypatch.setattr(cli_mod, "render_overlay", _fake_render)  # type: ignore[attr-defined]
    out_file = tmp_path / "result.json"
    code = main(
        ["inspect", "--image", img, "--out", str(out_file),
         "--overlay-dir", str(tmp_path / "ov")],
        pipeline=_stub_pipeline(payload, segments=[seg]),
    )
    assert code == 0
    assert json.loads(out_file.read_text(encoding="utf-8"))["request_id"] == "r2"
    assert (tmp_path / "ov" / "overlay_0.png").read_bytes() == b"PNG"
    assert len(calls) == 1


def test_inspect_missing_image_returns_two(tmp_path: Path) -> None:
    code = main(
        ["inspect", "--image", str(tmp_path / "nope.png")],
        pipeline=_stub_pipeline({}),
    )
    assert code == 2
