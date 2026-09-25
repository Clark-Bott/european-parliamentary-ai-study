"""Optional positive controls: labelled synthetic LLM passages, kept apart.

Phase 8 of the design. Positive controls test whether the detector flags
clearly machine-written parliamentary prose in each source language. They
are synthetic by construction, are never mixed with real parliamentary
records, and no paid execution is required to design or validate them.

Text generation is deliberately not automated here: the researcher produces
the passages with any contemporary LLM (the ``--brief`` command prints a
per-language specification), stores them with provenance metadata, and this
module validates, stores, submits through the same cached Pangram client,
and scores them.
"""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
import argparse
import json
from pathlib import Path
from typing import Any, Iterable

from .io import iter_jsonl, write_jsonl
from .models import word_count

# Synthetic records must be recognisable by every downstream stage without
# inspecting the file path.
SYNTHETIC_SOURCE_TYPE = "synthetic_positive_control"
ID_PREFIX = "positive-control-"
REQUIRED_FIELDS = ("country", "text_language", "generator", "prompt_id", "text")

COUNTRIES = ("Germany", "France", "Netherlands", "Italy", "Spain", "Poland")
LANGUAGE = {"Germany": "de", "France": "fr", "Netherlands": "nl",
            "Italy": "it", "Spain": "es", "Poland": "pl"}
PARLIAMENT = {"Germany": "Bundestag", "France": "Assemblée nationale",
              "Netherlands": "Tweede Kamer", "Italy": "Camera dei deputati",
              "Spain": "Congreso de los Diputados", "Poland": "Sejm"}


def brief(country: str) -> dict[str, Any]:
    """Return the generation specification for one target language."""
    if country not in COUNTRIES:
        raise ValueError(f"unknown country {country!r}; expected one of {', '.join(COUNTRIES)}")
    return {
        "country": country,
        "text_language": LANGUAGE[country],
        "parliament": PARLIAMENT[country],
        "task": (
            f"Write three fictional plenary intervention drafts for the "
            f"{PARLIAMENT[country]} in {LANGUAGE[country].upper()}: one "
            f"government statement, one opposition reply, and one committee "
            f"report speech."
        ),
        "requirements": [
            "150-400 words each, written entirely by a contemporary LLM.",
            "Realistic parliamentary register, addressing the chair and the house.",
            "Invent names, dates, and legislative references; do not copy real speeches.",
            "No stage directions, applause notes, or speaker labels in the text body.",
            "Record the generating model, model version, prompt id, and UTC date.",
        ],
        "separation_rule": (
            "Store the passages as JSONL rows with source_type="
            f"'{SYNTHETIC_SOURCE_TYPE}' and speech_id starting with '{ID_PREFIX}'. "
            "Never append them to a real corpus file."
        ),
    }


def normalize_record(record: dict[str, Any], index: int) -> dict[str, Any]:
    """Validate one synthetic passage and return it in the speech schema.

    Accepts both the researcher's raw field ``text`` and the normalized field
    ``speech_text``, so an already-normalized file can be re-validated.
    """
    record = dict(record)
    if not str(record.get("text", "")).strip() and str(record.get("speech_text", "")).strip():
        record["text"] = record["speech_text"]
    missing = [field for field in REQUIRED_FIELDS if not str(record.get(field, "")).strip()]
    if missing:
        raise ValueError(f"positive control {index}: missing " + ", ".join(missing))
    country = str(record["country"])
    if country not in COUNTRIES:
        raise ValueError(f"positive control {index}: unknown country {country!r}")
    language = str(record["text_language"])
    if language != LANGUAGE[country]:
        raise ValueError(
            f"positive control {index}: language {language!r} does not match {country}")
    for forbidden in ("source_url", "speaker_id", "party", "source_identifier"):
        if record.get(forbidden):
            raise ValueError(
                f"positive control {index}: {forbidden} must stay empty; synthetic "
                "passages must not impersonate an official source record")
    text = str(record["text"])
    if word_count(text) < 1:
        raise ValueError(f"positive control {index}: text contains no words")
    prompt_id = str(record["prompt_id"])
    return {
        "country": country,
        "parliament": PARLIAMENT[country],
        "chamber": PARLIAMENT[country],
        "date": str(record.get("date") or datetime.now(timezone.utc).date().isoformat()),
        "session_id": "positive-control-session",
        "speech_id": f"{ID_PREFIX}{LANGUAGE[country]}-{prompt_id}",
        "speaker_id": "",
        "speaker_name": "Synthetic LLM passage",
        "party": "",
        "speaker_role": "synthetic control",
        "legislative_term": "",
        "speech_text": text,
        "raw_text": text,
        "word_count": word_count(text),
        "source_url": "",
        "source_identifier": "",
        "source_type": SYNTHETIC_SOURCE_TYPE,
        "text_language": language,
        "record_status": "synthetic",
        "generator": str(record["generator"]),
        "prompt_id": prompt_id,
        "synthetic_control": True,
        "cleaning_notes": "Synthetic positive control; not parliamentary data.",
    }


def load_controls(path: str | Path) -> list[dict[str, Any]]:
    """Read and re-validate a positive-control file at any time."""
    return [normalize_record(record, index)
            for index, record in enumerate(iter_jsonl(path), 1)]


def import_controls(source: str | Path, output: str | Path) -> list[dict[str, Any]]:
    """Validate researcher-generated passages and write the control file."""
    records = load_controls(source)
    if not records:
        raise ValueError(f"no positive controls found in {source}")
    counts = Counter(record["country"] for record in records)
    missing = sorted(set(COUNTRIES) - set(counts))
    if missing:
        print(f"WARNING: no synthetic passage yet for {', '.join(missing)}", flush=True)
    write_jsonl(output, records)
    return records


def evaluate_positive_controls(
    controls: Iterable[dict[str, Any]],
    response_for_speech: Any,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Score detector output on the synthetic passages, per language.

    Returns ``(per_passage_rows, per_language_summary)``. ``response_for_speech``
    maps a control record to its cached Pangram response. A working detector
    should report a high AI fraction here; a low value warns that the
    subsequent historical baselines may also be understated. This is
    calibration evidence, not a research finding.
    """
    rows: list[dict[str, Any]] = []
    for control in controls:
        response = response_for_speech(control)
        ai = float(response.get("fraction_ai", 0.0))
        mixed = float(response.get("fraction_ai_assisted", 0.0))
        words = int(control.get("word_count", 0))
        rows.append({
            "country": str(control["country"]),
            "text_language": str(control["text_language"]),
            "speech_id": str(control["speech_id"]),
            "generator": str(control.get("generator", "")),
            "words": words,
            "ai_fraction": ai,
            "mixed_fraction": mixed,
            "detected_ai": ai + mixed >= 0.5,
        })
    summary: dict[tuple[str, str], dict[str, Any]] = {}
    for row in rows:
        key = (row["country"], row["text_language"])
        group = summary.setdefault(key, {"country": row["country"],
                                         "text_language": row["text_language"],
                                         "passages": 0, "detected": 0,
                                         "ai_fraction_sum": 0.0})
        group["passages"] += 1
        group["detected"] += int(row["detected_ai"])
        group["ai_fraction_sum"] += row["ai_fraction"]
    totals = [dict(group, detection_rate=group["detected"] / group["passages"],
                   mean_ai_fraction=group["ai_fraction_sum"] / group["passages"])
              for group in summary.values()]
    for group in totals:
        group.pop("ai_fraction_sum", None)
    return sorted(rows, key=lambda row: (row["country"], row["speech_id"])), sorted(
        totals, key=lambda group: group["country"])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Design, import, and score synthetic positive controls")
    parser.add_argument("--brief", metavar="COUNTRY",
                        help="print the generation brief for one country and exit")
    parser.add_argument("--import-from", type=Path,
                        help="JSONL of researcher-generated passages to validate")
    parser.add_argument("--output", type=Path,
                        default=Path("data/controls/positive_controls.jsonl"))
    parser.add_argument("--validate", type=Path,
                        help="re-validate an existing positive-control file")
    args = parser.parse_args(argv)
    if args.brief:
        print(json.dumps(brief(args.brief), ensure_ascii=False, indent=2))
        return 0
    if args.validate:
        records = load_controls(args.validate)
        print(json.dumps({"file": str(args.validate), "records": len(records),
                          "countries": dict(sorted(Counter(r["country"] for r in records).items()))},
                         ensure_ascii=False, indent=2))
        return 0
    if args.import_from:
        records = import_controls(args.import_from, args.output)
        print(json.dumps({"output": str(args.output), "records": len(records),
                          "countries": dict(sorted(Counter(r["country"] for r in records).items())),
                          "words": sum(r["word_count"] for r in records)},
                         ensure_ascii=False, indent=2))
        return 0
    parser.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
