"""CLI for cost estimation and the one-command study pipeline."""
from __future__ import annotations

import argparse
import math
import os
from pathlib import Path
import sys

from .cost import estimate_cost
from .io import iter_jsonl
from .pipeline import run_api_test, run_pipeline
from .sources.build import build_six_country_corpus


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
    parser.add_argument("--test-api", action="store_true", help="one short synthetic paid API task only; no parliamentary data or plots")
    parser.add_argument("--corpus", type=Path, default=Path("data/processed/speeches.jsonl"))
    parser.add_argument("--results-dir", type=Path, default=Path("results"))
    parser.add_argument("--model", default=None, help="explicit Pangram model selector; defaults to PANGRAM_MODEL or pangram-4")
    parser.add_argument("--price-per-1000-words", type=float, default=None)
    parser.add_argument("--confirm-paid-run", action="store_true", help="required explicit authorization for paid inference")
    parser.add_argument("--max-cost", type=float, default=None,
                         help="refuse any run whose estimate exceeds this USD amount")
    parser.add_argument("--sample-budget", type=float, default=None,
                        help="USD ceiling including optional controls; draw a weighted country-month sample (full paid-run guards still apply)")
    parser.add_argument("--sample-seed", type=int, default=2026,
                        help="reproducible country-month sample seed (default: 2026)")
    parser.add_argument("--estimate-only", action="store_true", help="print cost table and exit without inference or analysis")
    parser.add_argument("--build-corpus", action="store_true", help="acquire/rebuild missing country corpora before a dry run or estimate")
    parser.add_argument("--country", help="optional country filter for --estimate-only")
    parser.add_argument("--year", type=int, action="append", help="optional year filter (repeatable) for --estimate-only")
    parser.add_argument("--period", choices=("historical", "post_chatgpt"), help="optional period filter for --estimate-only")
    parser.add_argument("--processing-approval", type=Path,
                        default=Path("data/manifests/paid_processing_approval.json"),
                        help="recorded human approval for source, processor, and transfer terms")
    parser.add_argument("--gap-report", type=Path, action="append",
                        default=[Path("data/manifests/spain_unavailable_journals.json"),
                                 Path("data/manifests/germany_unavailable_protocols.json"),
                                 Path("data/manifests/poland_unavailable_statements.json")],
                        help="recorded official source gaps that must be empty before paid inference; repeatable")
    return parser


def main(argv: list[str] | None = None) -> int:
    arguments = sys.argv[1:] if argv is None else argv
    args = _parser().parse_args(arguments)
    load_dotenv()
    model = args.model or os.environ.get("PANGRAM_MODEL", "pangram-4")
    price = args.price_per_1000_words
    if price is None:
        price = float(os.environ.get("PANGRAM_PRICE_PER_1000_WORDS", "0.50"))
    if not math.isfinite(price) or price < 0:
        raise SystemExit("price must be finite and non-negative")
    if args.test_api:
        if args.dry_run or args.estimate_only or args.build_corpus or args.sample_budget is not None:
            raise SystemExit("--test-api cannot be combined with dry-run, estimate-only, build-corpus or sampling")
        summary = run_api_test(results_dir=args.results_dir, model=model,
                               api_key=os.environ.get("PANGRAM_API_KEY"),
                               confirm_paid_run=args.confirm_paid_run,
                               price_per_1000_words=price,
                               max_cost=0.05 if args.max_cost is None else args.max_cost)
        print(f"Synthetic API check completed: {summary['stage']}; not research data. "
              f"Estimated ceiling ${summary['estimated_max_cost_usd']:.4f}; "
              f"record at {args.results_dir / 'api_test' / 'test_result.json'}")
        return 0
    if args.dry_run and args.confirm_paid_run:
        raise SystemExit("--dry-run and --confirm-paid-run cannot be combined")
    if args.estimate_only and args.sample_budget is not None:
        raise SystemExit("--sample-budget requires a pipeline run; --estimate-only reports the full-corpus estimate")
    if not args.dry_run and not args.estimate_only and not args.confirm_paid_run:
        raise SystemExit("refusing paid inference without --confirm-paid-run")
    if args.build_corpus or (not args.dry_run and not args.corpus.is_file()):
        build_six_country_corpus(args.corpus)
    if args.dry_run and not args.corpus.is_file() and any(
        argument == "--corpus" or argument.startswith("--corpus=") for argument in arguments
    ):
        raise FileNotFoundError(
            f"explicit corpus not found: {args.corpus}; omit --corpus for a synthetic smoke test "
            "or use --build-corpus to acquire official transcripts"
        )
    if args.estimate_only:
        if not args.corpus.is_file():
            raise SystemExit(f"corpus not found: {args.corpus}")
        report = estimate_cost(iter_jsonl(args.corpus), price_per_1000_words=price,
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
                           api_key=os.environ.get("PANGRAM_API_KEY"),
                           gap_reports=args.gap_report,
                           processing_approval=args.processing_approval,
                            max_cost=args.max_cost, sample_budget=args.sample_budget,
                            sample_seed=args.sample_seed)
    print(f"Pipeline complete: {summary['results_dir']}")
    mode = "synthetic smoke test" if summary["synthetic_smoke_test"] else (
        "real corpus / MOCKED detector responses" if summary["mocked"] else "Pangram inference")
    print(f"Mode: {mode}")
    print(f"Outputs: 3 time aggregations; six country figures; tables; QA and report")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValueError, RuntimeError, PermissionError, FileNotFoundError, EnvironmentError, TimeoutError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2)
