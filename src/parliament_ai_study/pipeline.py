"""End-to-end smoke, cost-control, inference, and research-output pipeline."""
from __future__ import annotations

from collections.abc import Iterable
import csv
from datetime import datetime, timezone
import hashlib
import html
import json
import os
from pathlib import Path
from typing import Any

from .analysis import aggregate_results
from .cost import estimate_cost
from .io import read_jsonl, write_jsonl
from .models import Speech
from .pangram import PangramClient, ResponseCache
from .qa import COUNTRIES, validate_corpus


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


def _country_summaries(speeches: list[dict[str, Any]]) -> list[dict[str, Any]]:
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


def _mock_responses(speeches: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    responses = {}
    for speech in speeches:
        digest = hashlib.sha256(str(speech["speech_id"]).encode()).digest()
        ai = (digest[0] % 16) / 100
        mixed = (digest[1] % 11) / 100
        responses[str(speech["speech_id"])] = {
            "stage": "STAGE_SUCCESS", "version": "MOCK", "fraction_ai": ai,
            "fraction_ai_assisted": mixed, "fraction_human": 1 - ai - mixed,
            "prediction_short": "MOCK", "mock": True,
        }
    return responses


def _write_svg(path: Path, groups: list[dict[str, Any]], *, title: str) -> None:
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
        points[row["country"]][row["period"]] = float(row["ai_word_share"])
    maximum = max((float(row["ai_word_share"]) for row in groups), default=0.0)
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


def _write_outputs(speeches: list[dict[str, Any]], responses: dict[str, dict[str, Any]],
                   results_dir: Path, *, price: float, model: str, synthetic: bool,
                   mocked: bool, qa: dict[str, Any]) -> dict[str, Any]:
    tables = results_dir / "tables"
    figures = results_dir / "figures"
    reports = results_dir / "reports"
    processed = results_dir / "processed"
    for directory in (tables, figures, reports, processed):
        directory.mkdir(parents=True, exist_ok=True)
    sizes = _country_summaries(speeches)
    _write_csv(tables / "corpus_size.csv", sizes)
    estimate = estimate_cost(speeches, price_per_1000_words=price)
    _write_csv(tables / "cost_estimate.csv", estimate["rows"] + [{
        "country": "TOTAL", "speeches": estimate["speeches"], "words": estimate["words"],
        "estimated_api_units": estimate["estimated_api_units"], "estimated_cost": estimate["estimated_cost"]}])
    periods = {}
    for granularity in ("month", "quarter", "year"):
        aggregated = aggregate_results(speeches, responses, period=granularity)
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
            for row in aggregate_results(speeches, responses, period="year", min_words=minimum,
                                         exclude_ministers=exclusion == "ministers",
                                         exclude_chairs=exclusion == "chairs"):
                baseline_rate = control_rates.get(row["country"])
                sensitivity.append({**row, "min_words": minimum, "excluded_role": exclusion,
                                    "historical_baseline_ai_share": baseline_rate,
                                    "baseline_adjusted_ai_share_sensitivity":
                                    max(0.0, row["ai_word_share"] - baseline_rate)
                                    if baseline_rate is not None else None})
    _write_csv(tables / "sensitivity.csv", sensitivity)
    _write_svg(figures / "all_countries.svg", periods["month"],
               title="Pangram-classified AI-generated word share by month" + (" (MOCKED)" if mocked else ""))
    for country in COUNTRIES:
        safe = country.lower().replace(" ", "_")
        country_rows = [row for row in periods["month"] if row["country"] == country]
        _write_svg(figures / f"{safe}.svg", country_rows,
                   title=f"{country}: AI-generated word share" + (" (MOCKED)" if mocked else ""))
    response_records = [{"speech_id": sid, "response": response} for sid, response in sorted(responses.items())]
    write_jsonl(processed / ("mock_results.jsonl" if mocked else "speech_results.jsonl"), response_records)
    (reports / "corpus_qa.json").write_text(json.dumps(qa, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    status = "MOCKED PIPELINE DRY RUN — NOT RESEARCH RESULTS" if mocked else "Pangram inference outputs"
    report = [f"# Experiment run: {status}", "", f"Model selector: `{model}`", f"Speeches: {len(speeches):,}",
              f"Words: {estimate['words']:,}", f"Estimated cost at configured rate: ${estimate['estimated_cost']:.4f}",
              f"Countries present: {', '.join(qa['countries_present']) or 'none'}", "",
              ("This report contains deterministic mocked detector fractions. "
               "Mock values are not Pangram findings and must not be cited as empirical results. "
               + ("The corpus is also a synthetic fixture. " if synthetic else "The supplied corpus may be real data. ")) if mocked else
              "This report summarizes Pangram detector output. Classification is not proof of authorship or personal AI use.", "",
               "Outputs: annual/monthly/quarterly tables, historical baseline and pooled pre/post tables, length/role sensitivity, SVG figures, corpus QA JSON, and machine-readable result JSONL."]
    (reports / ("dry_run_report.md" if mocked else "results_report.md")).write_text("\n".join(report) + "\n", encoding="utf-8")
    return {"synthetic_smoke_test": synthetic, "mocked": mocked, "speeches": len(speeches), "words": estimate["words"],
            "estimated_cost": estimate["estimated_cost"], "countries": qa["countries_present"],
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


def run_pipeline(*, corpus: str | Path | None, results_dir: str | Path,
                 dry_run: bool, price_per_1000_words: float, model: str,
                 confirm_paid_run: bool = False, api_key: str | None = None,
                 gap_reports: str | Path | Iterable[str | Path] | None = None,
                 processing_approval: str | Path | None = None) -> dict[str, Any]:
    """Run the deterministic mock workflow or authorized Pangram inference."""
    target = Path(results_dir)
    synthetic = False
    if corpus is None:
        if not dry_run:
            raise FileNotFoundError("a normalized corpus path is required for paid inference")
        speeches = _mock_corpus()
        synthetic = True
        write_jsonl(target / "processed" / "mock_corpus.jsonl", speeches)
    else:
        source = Path(corpus)
        if not source.is_file():
            if dry_run:
                speeches = _mock_corpus()
                synthetic = True
                write_jsonl(target / "processed" / "mock_corpus.jsonl", speeches)
            else:
                raise FileNotFoundError(source)
        else:
            speeches = read_jsonl(source)
    qa = validate_corpus(speeches)
    if qa["errors"]:
        raise ValueError("corpus failed QA: " + "; ".join(qa["errors"][:10]))
    if not dry_run:
        missing = [f"{country}:{year}" for country in COUNTRIES for year in range(2018, 2027)
                   if year != 2026 and not qa["country_year_counts"].get(f"{country}:{year}")]
        if missing:
            raise ValueError("paid six-country run requires country/year coverage; missing " + ", ".join(missing))
        if isinstance(gap_reports, (str, Path)):
            report_paths = (Path(gap_reports),)
        elif gap_reports is None:
            report_paths = (Path("data/manifests/spain_unavailable_journals.json"),
                            Path("data/manifests/germany_unavailable_protocols.json"))
        else:
            report_paths = tuple(Path(path) for path in gap_reports)
        for gaps_path in report_paths:
            if gaps_path.is_file() and json.loads(gaps_path.read_text(encoding="utf-8")):
                raise ValueError(f"unresolved official source gaps recorded in {gaps_path}; no paid submission")
        validate_processing_approval(
            processing_approval or "data/manifests/paid_processing_approval.json")
    estimate = estimate_cost(speeches, price_per_1000_words=price_per_1000_words)
    print(f"Corpus: {len(speeches)} speeches, {estimate['words']:,} words; estimated Pangram cost ${estimate['estimated_cost']:.4f} at ${price_per_1000_words}/1,000 words.")
    if dry_run:
        responses = _mock_responses(speeches)
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
        responses = {}
        eligible_speeches = [speech for speech in speeches if int(speech.get("word_count", 0)) >= 40]
        total = len(eligible_speeches)
        for index, speech in enumerate(eligible_speeches, 1):
            sid = str(speech["speech_id"])
            text = str(speech["speech_text"])
            print(f"Pangram {index}/{total}: {sid}")
            try:
                responses[sid] = client.analyze(text, cache, allow_paid=True)
            except Exception as exc:
                log = target / "reports" / "pangram_errors.jsonl"
                log.parent.mkdir(parents=True, exist_ok=True)
                with log.open("a", encoding="utf-8") as stream:
                    stream.write(json.dumps({"at_utc": datetime.now(timezone.utc).isoformat(),
                                             "speech_id": sid, "error_type": type(exc).__name__,
                                             "message": str(exc)}, ensure_ascii=False) + "\n")
                raise
    return _write_outputs(speeches, responses, target, price=price_per_1000_words,
                          model=model, synthetic=synthetic, mocked=dry_run, qa=qa)
