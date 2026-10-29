"""asset-intel CLI (ARCH §4.8): inspect without the server.

Usage:
    python -m app.cli inspect --image crack.jpg [--image seam.jpg] --note "..."         [--asset-id X] [--out result.json] [--overlay-dir previews/]

Runs the full pipeline in-process (needs META_API_KEY), prints the validated
result JSON to stdout (or --out), and optionally writes per-image SAM overlay
PNGs. Exit 0 = ok, 1 = upstream/model failure, 2 = caller/input failure.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from app.gateway import Settings
from app.gateway.errors import MetaAPIError
from app.orchestrator import InspectionPipeline
from app.orchestrator.errors import PipelineInputError
from app.sam_service.errors import SamInputError
from app.sam_service.overlay import render_overlay

logger = logging.getLogger("asset_intel.cli")


def _load_images(paths: Sequence[str]) -> list[bytes]:
    images = []
    for raw in paths:
        path = Path(raw)
        if not path.is_file():
            raise PipelineInputError(f"image not found: {raw}")
        images.append(path.read_bytes())
    return images


def _write_overlays(
    images: Sequence[bytes], segmentations: Sequence[Any], overlay_dir: str
) -> list[str]:
    out_dir = Path(overlay_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    written = []
    for i, image_bytes in enumerate(images):
        segs = [s for s in segmentations if s.source_image == f"image_{i}"]
        if not segs:
            continue
        dest = out_dir / f"overlay_{i}.png"
        dest.write_bytes(render_overlay(image_bytes, segs))
        written.append(str(dest))
    return written


def inspect_command(
    images: Sequence[str],
    note: str,
    asset_id: str | None,
    out: str | None,
    overlay_dir: str | None,
    pipeline: InspectionPipeline | None = None,
) -> int:
    """Run one inspection. Returns the process exit code."""
    try:
        image_bytes = _load_images(images)
        pipe = pipeline or InspectionPipeline(settings=Settings.from_env())
        result = pipe.run_full(
            image_bytes,
            note=note,
            asset_meta={"asset_id": asset_id} if asset_id else {},
        )
    except (PipelineInputError, SamInputError, ValidationError, ValueError) as exc:
        print(json.dumps({"error": f"{type(exc).__name__}: {exc}"}), file=sys.stderr)
        return 2
    except MetaAPIError as exc:
        print(json.dumps({"error": f"{type(exc).__name__}: {exc}"}), file=sys.stderr)
        return 1
    dumped = result.model_dump(mode="json")
    text = json.dumps(dumped, indent=2)
    if out:
        Path(out).write_text(text, encoding="utf-8")
    else:
        print(text)
    if overlay_dir:
        written = _write_overlays(image_bytes, result.segmentations, overlay_dir)
        print(json.dumps({"overlays": written}), file=sys.stderr)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="asset-intel", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    cmd = sub.add_parser("inspect", help="inspect images + note, print result JSON")
    cmd.add_argument("--image", action="append", required=True, help="image path (repeat 1-5x)")
    cmd.add_argument("--note", default="", help="maintenance note text")
    cmd.add_argument("--asset-id", default=None, help="asset id for asset_meta")
    cmd.add_argument("--out", default=None, help="write result JSON to file instead of stdout")
    cmd.add_argument("--overlay-dir", default=None, help="write per-image overlay PNGs here")
    return parser


def main(argv: Sequence[str] | None = None, pipeline: InspectionPipeline | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "inspect":
        return inspect_command(
            args.image, args.note, args.asset_id, args.out, args.overlay_dir,
            pipeline=pipeline,
        )
    raise AssertionError("unreachable")  # pragma: no cover


if __name__ == "__main__":
    raise SystemExit(main())
