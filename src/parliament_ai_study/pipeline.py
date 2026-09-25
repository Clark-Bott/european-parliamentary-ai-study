"""End-to-end smoke, cost-control, inference, and research-output pipeline."""
from __future__ import annotations

from collections.abc import Callable, Iterable
import csv
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import html
import json
import math
import os
from pathlib import Path
from typing import Any

from .analysis import aggregate_results, response_shares
from .budget_sample import file_sha256, plan_sample, write_sample
from .cost import estimate_cost
from .io import iter_jsonl, write_jsonl
from .models import Speech
from .pangram import PangramClient, ResponseCache, request_fingerprint
from .positive_controls import evaluate_positive_controls, load_controls
from .qa import COUNTRIES, audit_corpus_file
from .secondary import descriptive_breakdowns


def _mock_corpus() -> list[dict[str, Any]]:
    rows = []
    for country in COUNTRIES:
        for year in (2019, 2024):
            for month in (2, 6, 10):
                sid = f"mock-{country.lower()}-{year}-{month:02d}"
                text = (f"Synthetic test record for {country}, {year}. This is not a real parliamentary intervention. "
                        "The fixture contains enough words to exercise the length-eligibility path for the mock workflow. "
                        "No detector call is made and every result generated from this fixture is explicitly marked mocked. "
                        "It exists only to demonstrate the tables, figures, report, cache-independent analysis, and quality checks.")
                record = Speech(
                    country=country, parliament={"Germany":"Bundestag", "France":"Assemblée nationale",
                    "Netherlands":"Tweede Kamer", "Italy":"Camera dei deputati",
                    "Spain":"Congreso de los Diputados", "Poland":"Sejm"}[country],
                    chamber="lower house", date=f"{year}-{month:02d}-15", session_id=f"mock-session-{year}-{month}",
                    speech_id=sid, speaker_id="synthetic-test", speaker_name="Synthetic fixture",
                    speech_text=text, source_url=f"https://example.invalid/mock/{sid}",
                    source_identifier=sid, source_type="synthetic_smoke_fixture",
                    cleaning_notes="Synthetic data generated solely for pipeline testing.",
                    text_language="und", speaker_role="ordinary member")
                rows.append(record.to_dict())
    return rows


def _write_csv(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not records:
        path.write_text("\n", encoding="utf-8")
        return
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(records[0]), extrasaction="ignore")
        writer.writeheader()
        writer.writerows(records)


def _country_summaries(speeches: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, dict[str, int]] = {}
    for speech in speeches:
        row = grouped.setdefault(str(speech["country"]), {
            "speeches": 0, "words": 0, "eligible_speeches": 0, "eligible_words": 0})
        words = int(speech["word_count"])
        row["speeches"] += 1
        row["words"] += words
        if words >= 40:
            row["eligible_speeches"] += 1
            row["eligible_words"] += words
    empty = {"speeches": 0, "words": 0, "eligible_speeches": 0, "eligible_words": 0}
    return [{"country": country, **grouped.get(country, empty)} for country in COUNTRIES]


def _mock_response(speech: dict[str, Any]) -> dict[str, Any]:
    digest = hashlib.sha256(str(speech["speech_id"]).encode()).digest()
    ai = (digest[0] % 16) / 100
    mixed = (digest[1] % 11) / 100
    return {
        "stage": "STAGE_SUCCESS", "version": "MOCK", "fraction_ai": ai,
        "fraction_ai_assisted": mixed, "fraction_human": 1 - ai - mixed,
        "prediction_short": "MOCK", "mock": True,
    }


def _write_svg(path: Path, groups: list[dict[str, Any]], *, title: str,
               share_key: str = "ai_word_share") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    width, height, left, right, top, bottom = 920, 440, 70, 25, 45, 70
    countries = list(dict.fromkeys(row["country"] for row in groups))
    periods = sorted({row["period"] for row in groups})
    if not periods:
        periods = ["no data"]
    palette = ["#3569a8", "#d45e36", "#32876b", "#8b62a9", "#d09b27", "#4b8e9d"]
    plot_width, plot_height = width - left - right, height - top - bottom
    points = {country: {} for country in countries}
    for row in groups:
        points[row["country"]][row["period"]] = float(row[share_key])
    maximum = max((float(row[share_key]) for row in groups), default=0.0)
    ceiling = max(0.05, min(1.0, maximum * 1.15))
    elements = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
                '<rect width="100%" height="100%" fill="white"/>',
                f'<text x="{left}" y="25" font-family="sans-serif" font-size="18" font-weight="bold">{html.escape(title)}</text>']
    for tick in range(0, 6):
        y = top + plot_height * tick / 5
        label = f"{ceiling * (1 - tick / 5):.1%}"
        elements.append(f'<line x1="{left}" y1="{y:.1f}" x2="{width-right}" y2="{y:.1f}" stroke="#ddd"/>')
        elements.append(f'<text x="{left-10}" y="{y+4:.1f}" text-anchor="end" font-size="11" font-family="sans-serif">{label}</text>')
    for pi, period_value in enumerate(periods):
        x = left if len(periods) == 1 else left + plot_width * pi / (len(periods) - 1)
        if pi % max(1, len(periods) // 10) == 0 or pi == len(periods)-1:
            elements.append(f'<text x="{x:.1f}" y="{height-40}" text-anchor="middle" font-size="10" font-family="sans-serif">{html.escape(period_value)}</text>')
    for ci, country in enumerate(countries):
        pts = []
        for pi, period_value in enumerate(periods):
            if period_value not in points[country]:
                continue
            x = left if len(periods) == 1 else left + plot_width * pi / (len(periods) - 1)
            value = max(0.0, min(ceiling, points[country][period_value]))
            y = top + plot_height * (1 - value / ceiling)
            pts.append((x, y))
        if pts:
            coords = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
            elements.append(f'<polyline points="{coords}" fill="none" stroke="{palette[ci % len(palette)]}" stroke-width="2"/>')
            for x, y in pts:
                elements.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3" fill="{palette[ci % len(palette)]}"/>')
        lx = left + ci * 135
        elements.append(f'<line x1="{lx}" y1="{height-15}" x2="{lx+18}" y2="{height-15}" stroke="{palette[ci % len(palette)]}" stroke-width="3"/>')
        elements.append(f'<text x="{lx+24}" y="{height-11}" font-size="11" font-family="sans-serif">{html.escape(country)}</text>')
    elements.append("</svg>")
    path.write_text("\n".join(elements) + "\n", encoding="utf-8")


def _write_outputs(corpus_path: str | Path,
                   response_for_speech: Callable[[dict[str, Any]], dict[str, Any]],
                   results_dir: Path, *, model: str, synthetic: bool, mocked: bool,
                    qa: dict[str, Any], estimate: dict[str, Any],
                    response_min_words: int,
                    sampling_plan: dict[str, Any] | None = None,
                    positive_controls_path: str | Path | None = None) -> dict[str, Any]:
    tables = results_dir / "tables"
    figures = results_dir / "figures"
    reports = results_dir / "reports"
    processed = results_dir / "processed"
    for directory in (tables, figures, reports, processed):
        directory.mkdir(parents=True, exist_ok=True)
    sizes = _country_summaries(iter_jsonl(corpus_path))
    _write_csv(tables / "corpus_size.csv", sizes)
    _write_csv(tables / "cost_estimate.csv", estimate["rows"] + [{
        "country": "TOTAL", "speeches": estimate["speeches"], "words": estimate["words"],
        "estimated_api_units": estimate["estimated_api_units"], "estimated_cost": estimate["estimated_cost"]}])
    periods = {}
    for granularity in ("month", "quarter", "year"):
        print(f"Aggregating detector output by {granularity}…", flush=True)
        aggregated = aggregate_results(iter_jsonl(corpus_path), response_for_speech,
                                      period=granularity)
        periods[granularity] = aggregated
        filename = {"month": "monthly", "quarter": "quarterly", "year": "annual"}[granularity]
        _write_csv(tables / f"{filename}_results.csv", aggregated)
    annual = periods["year"]
    baseline = [row for row in annual if 2018 <= int(row["period"]) <= 2021]
    _write_csv(tables / "historical_baseline.csv", baseline)
    pre_post_groups: dict[tuple[str, str], dict[str, float]] = {}
    for row in annual:
        year = int(row["period"])
        group_name = "pre-LLM control" if year <= 2021 else "transition" if year == 2022 else "post-ChatGPT"
        group = pre_post_groups.setdefault((row["country"], group_name),
                                           {"speeches": 0, "words": 0, "ai_words_estimate": 0.0,
                                            "mixed_words_estimate": 0.0})
        for field in group:
            group[field] += row[field]
    pre_post = [{"country": country, "period_group": label, **values,
                 "ai_word_share": values["ai_words_estimate"] / values["words"],
                 "ai_plus_mixed_word_share": (values["ai_words_estimate"] + values["mixed_words_estimate"]) / values["words"]}
                for (country, label), values in sorted(pre_post_groups.items()) if values["words"]]
    _write_csv(tables / "pre_post_comparison.csv", pre_post)
    control_rates = {row["country"]: row["ai_word_share"] for row in pre_post
                     if row["period_group"] == "pre-LLM control"}
    sensitivity = []
    for minimum in (40, 100, 250):
        for exclusion in ("none", "ministers", "chairs"):
            print(f"Sensitivity: min_words={minimum}, excluded_role={exclusion}", flush=True)
            for row in aggregate_results(iter_jsonl(corpus_path), response_for_speech,
                                         period="year", min_words=minimum,
                                         exclude_ministers=exclusion == "ministers",
                                         exclude_chairs=exclusion == "chairs"):
                baseline_rate = control_rates.get(row["country"])
                sensitivity.append({**row, "min_words": minimum, "excluded_role": exclusion,
                                    "historical_baseline_ai_share": baseline_rate,
                                    "baseline_adjusted_ai_share_sensitivity":
                                    max(0.0, row["ai_word_share"] - baseline_rate)
                                    if baseline_rate is not None else None})
    _write_csv(tables / "sensitivity.csv", sensitivity)
    print("Aggregating descriptive party, term, length and speaker splits…", flush=True)
    descriptive = descriptive_breakdowns(iter_jsonl(corpus_path), response_for_speech)
    for dimension, rows in descriptive.items():
        _write_csv(tables / f"{dimension}_breakdown.csv", rows)
    # Optional Phase 8 calibration: synthetic LLM passages are scored only if
    # the researcher has prepared them; their absence is not an error.
    positive_controls: dict[str, Any] = {"prepared": False}
    if positive_controls_path is not None and Path(positive_controls_path).is_file():
        controls = load_controls(positive_controls_path)
        passage_rows, language_rows = evaluate_positive_controls(
            controls, lambda record: response_for_speech(record))
        _write_csv(tables / "positive_controls.csv", language_rows)
        positive_controls = {"prepared": True, "file": str(positive_controls_path),
                             "records": len(controls), "by_language": language_rows}
        (reports / "positive_controls.json").write_text(
            json.dumps(positive_controls, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8")
    suffix = (" (SAMPLED ESTIMATE)" if sampling_plan else "") + (" (MOCKED)" if mocked else "")
    _write_svg(figures / "all_countries.svg", periods["month"],
                title="Pangram-classified AI-generated word share by month" + suffix)
    for key, label in (("mixed_word_share", "AI-assisted"),
                       ("ai_plus_mixed_word_share", "AI-generated plus AI-assisted")):
        _write_svg(figures / f"all_countries_{key}.svg", periods["month"],
                   title=f"Pangram-classified {label} word share by month" + suffix,
                   share_key=key)
    for country in COUNTRIES:
        safe = country.lower().replace(" ", "_")
        country_rows = [row for row in periods["month"] if row["country"] == country]
        _write_svg(figures / f"{safe}.svg", country_rows,
                   title=f"{country}: AI-generated word share" + suffix)
        for key, label in (("mixed_word_share", "AI-assisted"),
                           ("ai_plus_mixed_word_share", "AI-generated plus AI-assisted")):
            _write_svg(figures / f"{safe}_{key}.svg", country_rows,
                       title=f"{country}: {label} word share" + suffix, share_key=key)
    def response_records():
        for speech in iter_jsonl(corpus_path):
            if int(speech.get("word_count", 0)) < response_min_words:
                continue
            yield {"speech_id": str(speech["speech_id"]),
                   "response": response_for_speech(speech)}
    write_jsonl(processed / ("mock_results.jsonl" if mocked else "speech_results.jsonl"),
                response_records())
    (reports / "corpus_qa.json").write_text(json.dumps(qa, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if sampling_plan:
        (reports / "sampling_plan.json").write_text(
            json.dumps(sampling_plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    status = "MOCKED PIPELINE DRY RUN — NOT RESEARCH RESULTS" if mocked else "Pangram inference outputs"
    report = [f"# Experiment run: {status}", "", f"Model selector: `{model}`", f"Speeches: {qa['records']:,}",
              f"Words: {estimate['words']:,}", f"Estimated cost at configured rate: ${estimate['estimated_cost']:.4f}",
              f"Countries present: {', '.join(qa['countries_present']) or 'none'}", "",
              ("This report contains deterministic mocked detector fractions. "
               "Mock values are not Pangram findings and must not be cited as empirical results. "
               + ("The corpus is also a synthetic fixture. " if synthetic else "The supplied corpus may be real data. ")) if mocked else
               "This report summarizes Pangram detector output. Classification is not proof of authorship or personal AI use.", "",
               ("Country-month simple random samples were drawn from the complete eligible corpus. "
                "Monthly/annual shares, sensitivity, and party/term/length breakdowns use inverse-inclusion "
                "weights; speech-level outputs and cost tables describe the selected sample only. "
                "Speaker breakdowns are suppressed. Sampling uncertainty is not quantified: "
                "small monthly samples are exploratory, not precise population rates. "
                "See sampling_plan.json for selected/population counts, weights, and hashes."
                if sampling_plan else "Full-corpus inference; no sampling weights."), "",
                "Outputs: annual/monthly/quarterly tables, historical baseline and pooled pre/post tables, length/role sensitivity, descriptive party/term/length/pseudonymous-speaker splits, SVG figures, corpus QA JSON, and machine-readable result JSONL."]
    (reports / ("dry_run_report.md" if mocked else "results_report.md")).write_text("\n".join(report) + "\n", encoding="utf-8")
    return {"synthetic_smoke_test": synthetic, "mocked": mocked, "speeches": qa["records"], "words": estimate["words"],
             "estimated_cost": estimate["estimated_cost"], "countries": qa["countries_present"],
             "sampled": sampling_plan is not None,
            "positive_controls": positive_controls,
            "errors": qa["errors"], "warnings": qa["warnings"], "results_dir": str(results_dir)}


def validate_processing_approval(path: str | Path) -> dict[str, Any]:
    """Require a recorded human approval for source and processor terms."""
    approval_path = Path(path)
    if not approval_path.is_file():
        raise PermissionError(f"paid processing requires an approval record: {approval_path}")
    try:
        approval = json.loads(approval_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        raise PermissionError(f"cannot read processing approval: {approval_path}") from exc
    required = {
        "approved": True,
        "source_terms_reviewed": True,
        "processor_terms_reviewed": True,
        "international_transfer_reviewed": True,
    }
    missing = [key for key, value in required.items() if approval.get(key) is not value]
    for key in ("approved_by", "approved_at_utc", "scope"):
        if not str(approval.get(key, "")).strip():
            missing.append(key)
    if missing:
        raise PermissionError(
            f"processing approval {approval_path} is incomplete: " + ", ".join(missing))
    return approval


def _qa_for_path(path: str | Path) -> dict[str, Any]:
    """Adapt the disk-backed audit to the pipeline's QA result shape."""
    audit = audit_corpus_file(path)
    errors = list(audit["errors"])
    if audit["duplicate_speech_id_count"]:
        errors.append(
            f"{audit['duplicate_speech_id_count']} duplicate speech IDs; "
            "the first are " + ", ".join(audit["duplicate_speech_ids"])
        )
    country_year_counts = dict(audit["country_year_counts"])
    years_present = sorted({
        int(key.rsplit(":", 1)[1]) for key in country_year_counts
        if ":" in key
    })
    countries_present = sorted(audit["countries"])
    return {
        "records": audit["records"],
        "words": audit["words"],
        "countries_present": countries_present,
        "countries": countries_present,
        "years_present": years_present,
        "missing_countries": [country for country in COUNTRIES if country not in countries_present],
        "country_year_counts": country_year_counts,
        "duplicate_speech_ids": audit["duplicate_speech_ids"],
        "duplicate_speech_id_count": audit["duplicate_speech_id_count"],
        "duplicate_text_count": audit["duplicate_text_count"],
        "empty_speeches": audit["empty_speeches"],
        "implausible_lengths": audit["implausible_lengths"],
        "errors": errors,
        "warnings": audit["warnings"],
        "valid": audit["valid"] and not audit["duplicate_speech_id_count"],
    }


def _cached_response(cache: ResponseCache, model: str,
                     speech: dict[str, Any]) -> dict[str, Any]:
    """Read a completed response without submitting another paid request."""
    configuration = {"model": model, "public_dashboard_link": False}
    fingerprint = request_fingerprint(str(speech["speech_text"]), configuration)
    state = cache.state(fingerprint)
    if state is None or state.get("status") != "complete":
        raise RuntimeError(
            f"missing completed cached Pangram response for {speech.get('speech_id')}"
        )
    return state["response"]


def _validate_paid_corpus(corpus_path: Path, qa: dict[str, Any],
                          gap_reports: str | Path | Iterable[str | Path] | None,
                          processing_approval: str | Path | None) -> None:
    """Apply the same full-source checks before *any* parliamentary submission."""
    missing = [f"{country}:{year}" for country in COUNTRIES for year in range(2018, 2026)
               if not qa["country_year_counts"].get(f"{country}:{year}")]
    if missing:
        raise ValueError("paid six-country run requires country/year coverage; missing " + ", ".join(missing))
    if isinstance(gap_reports, (str, Path)):
        report_paths = (Path(gap_reports),)
    elif gap_reports is None:
        report_paths = (Path("data/manifests/spain_unavailable_journals.json"),
                        Path("data/manifests/germany_unavailable_protocols.json"),
                        Path("data/manifests/poland_unavailable_statements.json"))
    else:
        report_paths = tuple(Path(path) for path in gap_reports)
    if not report_paths:
        raise ValueError("paid inference requires source-gap reports")
    for gaps_path in report_paths:
        if not gaps_path.is_file():
            raise ValueError(f"required source-gap report is missing: {gaps_path}")
        gaps = json.loads(gaps_path.read_text(encoding="utf-8"))
        if not isinstance(gaps, list):
            raise ValueError(f"source-gap report must be a JSON list: {gaps_path}")
        if gaps:
            raise ValueError(f"unresolved official source gaps recorded in {gaps_path}; no paid submission")
    validate_processing_approval(
        processing_approval or "data/manifests/paid_processing_approval.json")


def run_pipeline(*, corpus: str | Path | None, results_dir: str | Path,
                 dry_run: bool, price_per_1000_words: float, model: str,
                 confirm_paid_run: bool = False, api_key: str | None = None,
                 gap_reports: str | Path | Iterable[str | Path] | None = None,
                 processing_approval: str | Path | None = None,
                 positive_controls: str | Path | None = Path(
                     "data/controls/positive_controls.jsonl"),
                  max_cost: float | None = None, sample_budget: float | None = None,
                  sample_seed: int = 2026) -> dict[str, Any]:
    """Run the deterministic mock workflow or authorized Pangram inference."""
    target = Path(results_dir)
    opposite = target / "reports" / ("results_report.md" if dry_run else "dry_run_report.md")
    if opposite.exists():
        raise ValueError(f"{target} already contains {'paid' if dry_run else 'mock'} outputs; "
                         "use a separate results directory")
    synthetic = False
    if corpus is None:
        if not dry_run:
            raise FileNotFoundError("a normalized corpus path is required for paid inference")
        corpus_path = target / "processed" / "mock_corpus.jsonl"
        write_jsonl(corpus_path, _mock_corpus())
        synthetic = True
    else:
        corpus_path = Path(corpus)
        if not corpus_path.is_file():
            if dry_run:
                corpus_path = target / "processed" / "mock_corpus.jsonl"
                write_jsonl(corpus_path, _mock_corpus())
                synthetic = True
            else:
                raise FileNotFoundError(corpus_path)

    qa = _qa_for_path(corpus_path)
    if qa["errors"]:
        raise ValueError("corpus failed QA: " + "; ".join(qa["errors"][:10]))
    if not dry_run:
        _validate_paid_corpus(corpus_path, qa, gap_reports, processing_approval)

    control_records = (load_controls(positive_controls) if positive_controls is not None
                       and Path(positive_controls).is_file() else [])
    control_estimate = estimate_cost(control_records, price_per_1000_words=price_per_1000_words,
                                     min_words=1)
    if control_records:
        print(f"Optional positive controls: {len(control_records)} texts; estimated extra cost "
              f"${control_estimate['estimated_cost']:.4f}.")
    if max_cost is not None and (not math.isfinite(max_cost) or max_cost < 0):
        raise ValueError("--max-cost must be finite and non-negative")
    sampling_plan = None
    if sample_budget is not None:
        if not math.isfinite(sample_budget) or sample_budget <= 0:
            raise ValueError("--sample-budget must be finite and positive")
        if max_cost is not None and sample_budget > max_cost:
            raise ValueError("--sample-budget cannot exceed --max-cost")
        available = sample_budget - control_estimate["estimated_cost"]
        if available < 0:
            raise ValueError("positive controls alone exceed the sample budget")
        sampling_plan = plan_sample(corpus_path, budget=available,
                                    price_per_1000_words=price_per_1000_words, seed=sample_seed)
        if not dry_run:
            missing_eligible = [f"{country}:{year}" for country in COUNTRIES for year in range(2018, 2026)
                                if not any(key.startswith(f"{country}:{year}-")
                                           for key in sampling_plan["strata"])]
            if missing_eligible:
                raise ValueError("sample requires eligible country/year coverage; missing " + ", ".join(missing_eligible))
        sampling_plan["total_budget_usd"] = sample_budget
        sampling_plan["control_estimated_usd"] = control_estimate["estimated_cost"]
        sampling_plan["control_sha256"] = (file_sha256(Path(positive_controls))
                                           if control_records and positive_controls is not None else None)
        sample_path = target / "processed" / "budget_sample.jsonl"
        manifest_path = target / "reports" / "sampling_plan.json"
        if manifest_path.exists():
            previous = json.loads(manifest_path.read_text(encoding="utf-8"))
            for key in ("source_sha256", "seed", "budget_usd", "total_budget_usd",
                        "control_sha256", "price_per_1000_words", "strata"):
                if previous[key] != sampling_plan[key]:
                    raise ValueError("existing sampling plan differs; use a new results directory")
        write_sample(corpus_path, sample_path, sampling_plan)
        if manifest_path.exists() and previous.get("sample_sha256") != sampling_plan["sample_sha256"]:
            raise ValueError("sample does not match existing plan; use a new results directory")
        corpus_path = sample_path
        qa = _qa_for_path(corpus_path)
        if qa["errors"]:
            raise ValueError("sample failed QA: " + "; ".join(qa["errors"][:10]))
    estimate = estimate_cost(iter_jsonl(corpus_path), price_per_1000_words=price_per_1000_words)
    print(f"Corpus: {qa['records']} speeches, {estimate['words']:,} words; estimated Pangram cost ${estimate['estimated_cost']:.4f} at ${price_per_1000_words}/1,000 words.")
    total_cost = estimate["estimated_cost"] + control_estimate["estimated_cost"]
    exact_cost = (Decimal(estimate["estimated_api_units"] + control_estimate["estimated_api_units"])
                  * Decimal(str(price_per_1000_words)) / 10)
    if sample_budget is not None and exact_cost > Decimal(str(sample_budget)):
        raise PermissionError("sample and controls exceed the requested budget; no API calls made")
    if max_cost is not None and exact_cost > Decimal(str(max_cost)):
        raise PermissionError(
            f"estimated cost ${total_cost:.2f} including positive controls exceeds the --max-cost "
            f"cap of ${max_cost:.2f}; raise the cap deliberately to continue")
    if sampling_plan:
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        pending_manifest = manifest_path.with_suffix(".json.tmp")
        pending_manifest.write_text(json.dumps(sampling_plan, ensure_ascii=False, indent=2) + "\n",
                                    encoding="utf-8")
        os.replace(pending_manifest, manifest_path)
    if dry_run:
        response_for_speech = _mock_response
        response_min_words = 0
    else:
        if not confirm_paid_run:
            raise PermissionError("refusing paid inference without --confirm-paid-run")
        secret = api_key or os.environ.get("PANGRAM_API_KEY", "")
        if not secret:
            raise EnvironmentError("PANGRAM_API_KEY is required")
        client = PangramClient(secret, model=model)
        if model not in client.available_models():
            raise ValueError(f"Pangram model {model!r} is not available to this API key")
        cache = ResponseCache(target / "raw_pangram")
        total = estimate["speeches"]
        eligible_index = 0
        for speech in iter_jsonl(corpus_path):
            if int(speech.get("word_count", 0)) < 40:
                continue
            eligible_index += 1
            sid = str(speech["speech_id"])
            text = str(speech["speech_text"])
            print(f"Pangram {eligible_index}/{total}: {sid}")
            try:
                client.analyze(text, cache, allow_paid=True)
            except Exception as exc:
                log = target / "reports" / "pangram_errors.jsonl"
                log.parent.mkdir(parents=True, exist_ok=True)
                with log.open("a", encoding="utf-8") as stream:
                    stream.write(json.dumps({"at_utc": datetime.now(timezone.utc).isoformat(),
                                             "speech_id": sid, "error_type": type(exc).__name__,
                                             "message": str(exc)}, ensure_ascii=False) + "\n")
                raise
        response_for_speech = lambda speech: _cached_response(cache, model, speech)
        response_min_words = 40
        # Synthetic positive controls are billed like any other text and are
        # submitted through the same fingerprint cache, so a restart never
        # pays for one twice.
        if control_records:
            for index, control in enumerate(control_records, 1):
                print(f"Pangram positive control {index}: {control['speech_id']}")
                try:
                    client.analyze(str(control["speech_text"]), cache, allow_paid=True)
                except Exception as exc:
                    log = target / "reports" / "pangram_errors.jsonl"
                    log.parent.mkdir(parents=True, exist_ok=True)
                    with log.open("a", encoding="utf-8") as stream:
                        stream.write(json.dumps({
                            "at_utc": datetime.now(timezone.utc).isoformat(),
                            "speech_id": control["speech_id"],
                            "error_type": type(exc).__name__, "message": str(exc)},
                            ensure_ascii=False) + "\n")
                    raise

    return _write_outputs(corpus_path, response_for_speech, target, model=model,
                          synthetic=synthetic, mocked=dry_run, qa=qa, estimate=estimate,
                           response_min_words=response_min_words,
                           sampling_plan=sampling_plan,
                           positive_controls_path=positive_controls)


def _select_test_speeches(corpus_path: Path, *, count: int,
                          country: str | None) -> list[dict[str, Any]]:
    """Keep the lowest hash priorities for distinct short contemporary texts."""
    top: list[tuple[bytes, bytes, dict[str, Any]]] = []
    for speech in iter_jsonl(corpus_path):
        words = int(speech["word_count"])
        if not 40 <= words <= 100 or str(speech["date"]) < "2023-01-01":
            continue
        if country is not None and speech["country"] != country:
            continue
        identity = f"2026|{speech['country']}|{speech['date']}|{speech['speech_id']}"
        rank = hashlib.sha256(identity.encode("utf-8")).digest()
        text_hash = hashlib.sha256(str(speech["speech_text"]).encode("utf-8")).digest()
        match = next((index for index, (_, digest, _) in enumerate(top)
                      if digest == text_hash), None)
        if match is not None:
            if rank < top[match][0]:
                top[match] = (rank, text_hash, speech)
                top.sort(key=lambda item: item[0])
        elif len(top) < count or rank < top[-1][0]:
            top.append((rank, text_hash, speech))
            top.sort(key=lambda item: item[0])
            del top[count:]
    if len(top) != count:
        raise ValueError(f"only {len(top)} distinct eligible 40–100 word speeches since 2023 "
                         f"found in {country or 'the corpus'}; requested {count}")
    return [speech for _, _, speech in top]


def run_api_test(*, corpus: str | Path, results_dir: str | Path, model: str,
                 api_key: str | None, confirm_paid_run: bool,
                 price_per_1000_words: float, max_cost: float = 0.05,
                 test_count: int = 1, test_country: str | None = None,
                 gap_reports: str | Path | Iterable[str | Path] | None = None,
                 processing_approval: str | Path | None = None) -> dict[str, Any]:
    """Classify at most three real corpus speeches, with full paid-run guards."""
    if not confirm_paid_run:
        raise PermissionError("parliamentary paid test requires --confirm-paid-run")
    if not 1 <= test_count <= 3:
        raise ValueError("--test-count must be between 1 and 3")
    if test_country is not None and test_country not in COUNTRIES:
        raise ValueError(f"--test-country must be one of: {', '.join(COUNTRIES)}")
    if not math.isfinite(price_per_1000_words) or price_per_1000_words < 0:
        raise ValueError("price must be finite and non-negative")
    if not math.isfinite(max_cost) or max_cost < 0:
        raise ValueError("--max-cost must be finite and non-negative")
    corpus_path = Path(corpus)
    if not corpus_path.is_file():
        raise FileNotFoundError(f"test corpus not found: {corpus_path}; --test-api never downloads or builds it")
    corpus_sha256 = file_sha256(corpus_path)
    qa = _qa_for_path(corpus_path)
    if qa["errors"]:
        raise ValueError("corpus failed QA: " + "; ".join(qa["errors"][:10]))
    _validate_paid_corpus(corpus_path, qa, gap_reports, processing_approval)
    selected = _select_test_speeches(corpus_path, count=test_count, country=test_country)
    if file_sha256(corpus_path) != corpus_sha256:
        raise ValueError("corpus changed during API test preflight; no request submitted")
    estimate = estimate_cost(selected, price_per_1000_words=price_per_1000_words)
    exact_cost = Decimal(estimate["estimated_api_units"]) * Decimal(str(price_per_1000_words)) / 10
    if exact_cost > Decimal(str(max_cost)):
        raise PermissionError(f"{test_count} corpus task(s) estimated at ${estimate['estimated_cost']:.4f} "
                              f"exceed the test cap of ${max_cost:.4f}")
    configuration = {"model": model, "public_dashboard_link": False}
    selection = {"status": "real corpus API diagnostic — NOT STUDY RESULTS",
                 "corpus_sha256": corpus_sha256, "model": model,
                 "price_per_1000_words": price_per_1000_words,
                 "estimated_max_cost_usd": estimate["estimated_cost"],
                 "billing_units": estimate["estimated_api_units"],
                 "speeches": [{"speech_id": str(speech["speech_id"]),
                               "country": speech["country"], "date": speech["date"],
                               "source_url": speech["source_url"],
                               "word_count": speech["word_count"],
                               "cache_fingerprint": request_fingerprint(str(speech["speech_text"]), configuration)}
                              for speech in selected]}
    target = Path(results_dir) / "api_test"
    selection_path = target / "selection.json"
    result_path = target / "test_result.json"
    if selection_path.exists():
        if json.loads(selection_path.read_text(encoding="utf-8")) != selection:
            raise ValueError("existing API test selection differs; use a new results directory")
    elif result_path.exists():
        raise ValueError("existing API test output has no selection record; use a new results directory")
    secret = api_key or os.environ.get("PANGRAM_API_KEY", "")
    if not secret:
        raise EnvironmentError("PANGRAM_API_KEY is required")
    client = PangramClient(secret, model=model)
    if model not in client.available_models():
        raise ValueError(f"Pangram model {model!r} is not available to this API key")
    target.mkdir(parents=True, exist_ok=True)
    pending = selection_path.with_suffix(".json.tmp")
    pending.write_text(json.dumps(selection, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(pending, selection_path)
    cache = ResponseCache(target / "raw_pangram")
    results = []
    for speech, metadata in zip(selected, selection["speeches"], strict=True):
        response = client.analyze(str(speech["speech_text"]), cache, allow_paid=True)
        ai, assisted = response_shares(response, str(speech["speech_id"]))
        results.append({**metadata, "stage": response["stage"],
                        "ai_only_share": ai, "ai_assisted_share": assisted,
                        "ai_plus_assisted_share": ai + assisted})
        summary = {**{key: value for key, value in selection.items() if key != "speeches"},
                   "completed_speeches": results,
                   "note": "Detector classification of short speeches is not proof of authorship or study prevalence."}
        pending = result_path.with_suffix(".json.tmp")
        pending.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        os.replace(pending, result_path)
    return summary
