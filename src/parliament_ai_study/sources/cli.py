"""CLI for official parliamentary source acquisition."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from .france import build_france_corpus, download_france_archives


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Acquire and normalize official parliamentary sources")
    parser.add_argument("country", choices=("France",), help="country adapter to execute")
    parser.add_argument("--start-year", type=int, default=2018)
    parser.add_argument("--end-year", type=int, default=2026)
    parser.add_argument("--terms", type=int, nargs="+", default=[15, 16, 17], help="Assemblée législature archives to use")
    parser.add_argument("--raw-dir", type=Path, default=Path("data/raw"))
    parser.add_argument("--output", type=Path, default=Path("data/processed/france_interventions.jsonl"))
    parser.add_argument("--manifest", type=Path, default=Path("data/manifests/source_manifest.jsonl"))
    args = parser.parse_args(argv)
    archives = download_france_archives(terms=tuple(args.terms), raw_dir=args.raw_dir, manifest_path=args.manifest)
    stats = build_france_corpus(archives, args.output, start_year=args.start_year, end_year=args.end_year)
    print(json.dumps({"country": "France", "output": str(args.output), **stats}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
