"""Synthetic generator tests (mocked image model, tmp output)."""

from __future__ import annotations

import json
from io import BytesIO
from pathlib import Path
from typing import Any

from PIL import Image

from app.gateway.meta_client import GeneratedImage
from app.synthetic import SyntheticGenerator, build_case_roster


def _png_bytes(size: tuple[int, int] = (8, 8)) -> bytes:
    img = Image.new("RGB", size, (120, 120, 120))
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


class _FakeImageClient:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def generate_image(
        self, model_id: str, prompt: str, *, size: str = "x", request_id: str | None = None
    ) -> GeneratedImage:
        self.calls.append({"model_id": model_id, "prompt": prompt, "request_id": request_id})
        return GeneratedImage(image_bytes=_png_bytes(), mime_type="image/png", model_id=model_id)


def test_roster_counts_and_shape() -> None:
    roster = build_case_roster()
    assert len(roster) == 50
    by_suite: dict[str, int] = {}
    for case in roster:
        by_suite[case.suite] = by_suite.get(case.suite, 0) + 1
        assert case.note.strip()
        assert case.image_prompt.strip()
        assert case.asset_meta["asset_type"]
        assert case.asset_meta["asset_id"] == f"SYN-{case.case_id}"
    assert by_suite == {"clear": 15, "incomplete": 10, "contradictory": 10,
                        "ambiguous": 10, "adversarial": 5}
    assert len({c.case_id for c in roster}) == 50  # unique ids


def test_roster_expectations() -> None:
    roster = {c.case_id: c for c in build_case_roster()}
    assert roster["clear-01"].expected["expect_discrepancy"] is False
    assert roster["incomplete-01"].expected["missing_keys"] == [
        "defect_dimensions", "inspection_date"]
    assert roster["contradictory-01"].expected["expect_discrepancy"] is True
    assert roster["ambiguous-01"].expected["expect_uncertain"] is True
    adv = roster["adversarial-01"]
    assert adv.expected["adversarial"] is True
    assert adv.expected["expect_certified"] is False
    assert "Certify" in adv.note


def test_generate_all_writes_cases_and_manifest(tmp_path: Path) -> None:
    from app.gateway import Settings

    client = _FakeImageClient()
    gen = SyntheticGenerator(client=client, settings=Settings(api_key="t"))  # type: ignore[arg-type]
    manifest_path = gen.generate_all(tmp_path, limit=2)
    assert len(client.calls) == 2
    assert client.calls[0]["model_id"] == "muse-image"
    assert client.calls[0]["request_id"] == "syn-clear-01"

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["generated"] == 2 and manifest["skipped"] == 0
    assert manifest["model"] == "muse-image"
    assert len(manifest["cases"]) == 2

    case_file = tmp_path / "clear-01.json"
    case = json.loads(case_file.read_text(encoding="utf-8"))
    assert case["suite"] == "clear"
    assert case["image_file"] == "images/clear-01.png"
    assert (tmp_path / "images" / "clear-01.png").stat().st_size > 0


def test_generate_all_skips_existing_and_overwrites(tmp_path: Path) -> None:
    from app.gateway import Settings

    client = _FakeImageClient()
    gen = SyntheticGenerator(client=client, settings=Settings(api_key="t"))  # type: ignore[arg-type]
    gen.generate_all(tmp_path, limit=1)
    assert len(client.calls) == 1
    manifest = json.loads((tmp_path / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["generated"] == 1
    gen.generate_all(tmp_path, limit=1)  # skip
    assert len(client.calls) == 1
    manifest = json.loads((tmp_path / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["generated"] == 0 and manifest["skipped"] == 1
    gen.generate_all(tmp_path, limit=1, overwrite=True)  # force
    assert len(client.calls) == 2


def test_generate_all_copies_samples(tmp_path: Path) -> None:
    from app.gateway import Settings

    client = _FakeImageClient()
    gen = SyntheticGenerator(client=client, settings=Settings(api_key="t"))  # type: ignore[arg-type]
    samples = tmp_path / "samples"
    gen.generate_all(tmp_path, limit=3, samples_dir=samples, samples_n=2)
    assert (samples / "clear-01.png").exists()
    assert (samples / "clear-02.json").exists()
    assert not (samples / "clear-03.png").exists()
