"""Integrity checks for source and normalized corpora."""
from __future__ import annotations

from collections import Counter
from datetime import date
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import tempfile
from typing import Any

from .io import iter_jsonl
from .models import word_count

COUNTRIES = ("Germany", "France", "Netherlands", "Italy", "Spain", "Poland")


def audit_corpus_file(path: str | Path, *, start_year: int = 2018,
                      end_year: int = 2026) -> dict[str, Any]:
    """Disk-backed full-file QA without holding millions of speeches in RAM."""
    counts: Counter[str] = Counter()
    years: Counter[str] = Counter()
    duplicate_ids = []
    duplicate_id_count = 0
    duplicate_text_count = 0
    errors = []
    warnings = []
    empty_count = 0
    implausible_count = 0
    words = 0
    scratch = os.environ.get("PARLIAMENT_QA_SCRATCH") or None
    if scratch is not None and not Path(scratch).is_dir():
        raise ValueError(f"PARLIAMENT_QA_SCRATCH is not a directory: {scratch}")
    with tempfile.TemporaryDirectory(prefix="parliament-qa-", dir=scratch) as tmp:
        connection = sqlite3.connect(str(Path(tmp) / "qa.sqlite"))
        connection.execute("CREATE TABLE ids (id TEXT PRIMARY KEY)")
        connection.execute("CREATE TABLE texts (hash TEXT PRIMARY KEY)")
        for index, row in enumerate(iter_jsonl(path), 1):
            country, sid = str(row.get("country", "")), str(row.get("speech_id", ""))
            counts[country] += 1
            if country not in COUNTRIES:
                errors.append(f"record {index}: unexpected country {country!r}")
            if not sid or not row.get("source_url") or not row.get("source_identifier"):
                errors.append(f"record {index}: missing ID or provenance")
            else:
                try:
                    connection.execute("INSERT INTO ids VALUES (?)", (sid,))
                except sqlite3.IntegrityError:
                    duplicate_id_count += 1
                    if len(duplicate_ids) < 20:
                        duplicate_ids.append(sid)
            try:
                day = date.fromisoformat(str(row.get("date", "")))
                years[f"{country}:{day.year}"] += 1
                if not start_year <= day.year <= end_year and len(warnings) < 1000:
                    warnings.append(f"record {index}: date outside configured study years: {day}")
            except ValueError:
                errors.append(f"record {index}: invalid date")
            text = str(row.get("speech_text", ""))
            if not text.strip():
                empty_count += 1
                errors.append(f"record {index}: empty text")
            try:
                row_words = int(row.get("word_count", -1))
            except (TypeError, ValueError):
                row_words = -1
            if row_words != word_count(text):
                errors.append(f"record {index}: inconsistent word count")
            elif row_words >= 0:
                words += row_words
                if row_words > 10000:
                    implausible_count += 1
                digest = hashlib.sha256(" ".join(text.casefold().split()).encode("utf-8")).hexdigest()
                try:
                    connection.execute("INSERT INTO texts VALUES (?)", (digest,))
                except sqlite3.IntegrityError:
                    duplicate_text_count += 1
            if len(errors) > 1000:
                raise ValueError("too many corpus integrity errors; first: " + "; ".join(errors[:5]))
            if index % 500_000 == 0:
                print(f"QA: {index:,} records checked ({words:,} words)", flush=True)
        connection.close()
    return {"records": sum(counts.values()), "words": words, "countries": dict(counts),
            "country_year_counts": dict(sorted(years.items())), "duplicate_speech_ids": duplicate_ids,
            "duplicate_speech_id_count": duplicate_id_count, "empty_speeches": empty_count,
            "implausible_lengths": implausible_count, "duplicate_text_count": duplicate_text_count,
            "errors": errors, "warnings": warnings, "valid": not errors and duplicate_id_count == 0}


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="Stream complete corpus integrity audit")
    parser.add_argument("corpus", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = audit_corpus_file(args.corpus)
    encoded = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded, encoding="utf-8")
    print(encoded)
    if not result["valid"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
