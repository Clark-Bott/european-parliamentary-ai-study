"""CLI for cost estimation and the one-command study pipeline."""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import sys

from .cost import estimate_cost
from .io import read_jsonl
from .pipeline import run_pipeline


def load_dotenv(path: Path = Path(".env")) -> None:
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        key, value = key.strip(), value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="European parliamentary AI-writing study pipeline")
    parser.add_argument("--dry-run", action="store_true", help="run the full pipeline with deterministic mock results; never call Pangram")
    parser.add_argument("--corpus", type=Path, default=Path("data/processed/speeches.jsonl"))
    parser.add_argument("--results-dir", type=Path, default=Path("results"))
    parser.add_argument("--model", default=None, help="explicit Pangram model selector; defaults to PANGRAM_MODEL or pangram-4")
    parser.add_argument("--price-per-1000-words", type=float, default=None)
    parser.add_argument("--confirm-paid-run", action="store_true", help="required explicit authorization for paid inference")
    parser.add_argument("--estimate-only", action="store_true", help="print cost table and exit without inference or analysis")
    parser.add_argument("--country", help="optional country filter for --estimate-only")
    parser.add_argument("--year", type=int, action="append", help="optional year filter (repeatable) for --estimate-only")
    parser.add_argument("--period", choices=("historical", "post_chatgpt"), help="optional period filter for --estimate-only")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    load_dotenv()
    model = args.model or os.environ.get("PANGRAM_MODEL", "pangram-4")
    price = args.price_per_1000_words
    if price is None:
        price = float(os.environ.get("PANGRAM_PRICE_PER_1000_WORDS", "0.50"))
    if price < 0:
        raise SystemExit("price must be non-negative")
    if args.dry_run and args.confirm_paid_run:
        raise SystemExit("--dry-run and --confirm-paid-run cannot be combined")
    if args.estimate_only:
        if not args.corpus.is_file():
            raise SystemExit(f"corpus not found: {args.corpus}")
        report = estimate_cost(read_jsonl(args.corpus), price_per_1000_words=price,
                               country=args.country, years=set(args.year) if args.year else None,
                               period=args.period)
        print(f"country\tspeeches\twords\tAPI units\testimated cost (USD)")
        for row in report["rows"]:
            print(f"{row['country']}\t{row['speeches']}\t{row['words']}\t{row['estimated_api_units']}\t${row['estimated_cost']:.4f}")
        print(f"TOTAL\t{report['speeches']}\t{report['words']}\t{report['estimated_api_units']}\t${report['estimated_cost']:.4f}")
        print(f"Rate: ${price:.4f} / 1,000 words; verify current contract and billing units before a paid run.")
        return 0
    corpus = None if args.dry_run and not args.corpus.exists() else args.corpus
    summary = run_pipeline(corpus=corpus, results_dir=args.results_dir, dry_run=args.dry_run,
                           price_per_1000_words=price, model=model,
                           confirm_paid_run=args.confirm_paid_run,
                           api_key=os.environ.get("PANGRAM_API_KEY"))
    print(f"Pipeline complete: {summary['results_dir']}")
    print(f"Mode: {'synthetic smoke test' if summary['synthetic_smoke_test'] else 'corpus run'}")
    print(f"Outputs: 3 time aggregations; six country figures; tables; QA and report")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValueError, PermissionError, FileNotFoundError, EnvironmentError, TimeoutError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2)
