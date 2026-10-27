"""CLI entry: python -m app.synthetic --out eval/cases/synthetic [--limit N]."""

from __future__ import annotations

import argparse
import logging

from app.synthetic import SyntheticGenerator

SUITES = ("clear", "incomplete", "contradictory", "ambiguous", "adversarial")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate synthetic eval cases.")
    parser.add_argument("--out", default="eval/cases/synthetic", help="Output directory")
    parser.add_argument("--suites", nargs="*", choices=SUITES, default=None)
    parser.add_argument("--limit", type=int, default=None, help="Max cases to render")
    parser.add_argument("--overwrite", action="store_true", help="Regenerate existing cases")
    parser.add_argument("--image-size", default="1024x1024")
    parser.add_argument("--samples-dir", default=None, help="Copy first N cases here too")
    parser.add_argument("--samples", type=int, default=0)
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )
    gen = SyntheticGenerator(image_size=args.image_size)
    manifest = gen.generate_all(
        args.out,
        suites=args.suites,
        limit=args.limit,
        overwrite=args.overwrite,
        samples_dir=args.samples_dir,
        samples_n=args.samples,
    )
    print(f"manifest: {manifest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
