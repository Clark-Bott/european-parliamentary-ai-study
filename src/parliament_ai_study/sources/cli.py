"""CLI for official parliamentary source acquisition."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from .france import build_france_corpus, download_france_archives
from .germany import build_bundestag_corpus
from .italy import build_camera_corpus
from .netherlands import build_tweede_kamer_corpus
from .sejm import build_sejm_corpus
from .spain import build_congreso_corpus


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Acquire and normalize official parliamentary sources")
    parser.add_argument("country", choices=("France", "Germany", "Netherlands", "Italy", "Spain", "Poland"), help="country adapter to execute")
    parser.add_argument("--start-year", type=int, default=2018)
    parser.add_argument("--end-year", type=int, default=2026)
    parser.add_argument("--terms", type=int, nargs="+", default=[15, 16, 17], help="Assemblée législature archives to use")
    parser.add_argument("--raw-dir", type=Path, default=Path("data/raw"))
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--manifest", type=Path, default=Path("data/manifests/source_manifest.jsonl"))
    args = parser.parse_args(argv)
    output = args.output or Path("data/processed") / f"{args.country.lower()}_speeches.jsonl"
    opts = {"start_year": args.start_year, "end_year": args.end_year,
            "raw_dir": args.raw_dir, "manifest_path": args.manifest}
    if args.country == "France":
        archives = download_france_archives(terms=tuple(args.terms), raw_dir=args.raw_dir, manifest_path=args.manifest)
        stats = build_france_corpus(archives, output, start_year=args.start_year, end_year=args.end_year)
    else:
        builder = {"Germany": build_bundestag_corpus, "Italy": build_camera_corpus,
                   "Spain": build_congreso_corpus,
                   "Netherlands": build_tweede_kamer_corpus,
                   "Poland": build_sejm_corpus}[args.country]
        stats = builder(output, **opts)
    print(json.dumps({"country": args.country, "output": str(output), **stats}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
