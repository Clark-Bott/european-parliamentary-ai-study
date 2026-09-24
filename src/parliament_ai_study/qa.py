"""Integrity checks for source and normalized corpora."""
from __future__ import annotations

from collections import Counter
from datetime import date
import hashlib
import json
from pathlib import Path
import re
import sqlite3
import tempfile
from typing import Any, Iterable

from .io import iter_jsonl
from .models import word_count

COUNTRIES = ("Germany", "France", "Netherlands", "Italy", "Spain", "Poland")


def validate_corpus(records: Iterable[dict[str, Any]], *, start_year: int = 2018, end_year: int = 2026) -> dict[str, Any]:
    rows = list(records)
    ids: Counter[str] = Counter()
    text_hashes: Counter[str] = Counter()
    country_year: Counter[tuple[str, int]] = Counter()
    errors: list[str] = []
    warnings: list[str] = []
    total_words = 0
    empty_count = 0
    implausible_count = 0
    for position, row in enumerate(rows, 1):
        sid = str(row.get("speech_id", ""))
        if not sid:
            errors.append(f"record {position}: missing speech_id")
        ids[sid] += 1
        country = str(row.get("country", ""))
        if country not in COUNTRIES:
            errors.append(f"record {position}: unexpected country {country!r}")
        try:
            day = date.fromisoformat(str(row.get("date", "")))
            if day.year < start_year or day.year > end_year:
                warnings.append(f"record {position}: date outside configured study years: {day}")
            country_year[(country, day.year)] += 1
        except ValueError:
            errors.append(f"record {position}: invalid ISO date {row.get('date')!r}")
        text = str(row.get("speech_text", ""))
        if not text.strip():
            empty_count += 1
            errors.append(f"record {position}: empty speech text")
        normalized = re.sub(r"\s+", " ", text).strip().casefold()
        if normalized:
            text_hashes[hashlib.sha256(normalized.encode("utf-8")).hexdigest()] += 1
        words = row.get("word_count")
        if not isinstance(words, int) or words < 0:
            errors.append(f"record {position}: invalid word_count")
            words = 0
        if words > 10000:
            implausible_count += 1
            warnings.append(f"record {position}: unusually long intervention ({words} words)")
        total_words += words
        if not row.get("source_identifier") or not row.get("source_url"):
            warnings.append(f"record {position}: incomplete source provenance")
    duplicate_ids = sorted(key for key, count in ids.items() if key and count > 1)
    duplicate_text_hashes = sum(count - 1 for count in text_hashes.values() if count > 1)
    if duplicate_ids:
        errors.append(f"duplicate speech IDs: {len(duplicate_ids)}")
    countries_present = sorted(set(str(row.get("country", "")) for row in rows))
    years_present = sorted({date.fromisoformat(str(row["date"])).year for row in rows if _valid_date(row.get("date"))})
    missing_countries = sorted(set(COUNTRIES) - set(countries_present))
    if missing_countries:
        warnings.append("countries without records: " + ", ".join(missing_countries))
    present_by_country_year = {
        f"{country}:{year}": count for (country, year), count in sorted(country_year.items())
    }
    return {
        "records": len(rows), "words": total_words, "countries_present": countries_present,
        "years_present": years_present, "missing_countries": missing_countries,
        "country_year_counts": present_by_country_year, "duplicate_speech_ids": duplicate_ids,
        "duplicate_text_count": duplicate_text_hashes, "empty_speeches": empty_count,
        "implausible_lengths": implausible_count, "errors": errors, "warnings": warnings,
        "valid": not errors,
    }


def _valid_date(value: Any) -> bool:
    try:
        date.fromisoformat(str(value))
        return True
    except ValueError:
        return False


def audit_corpus_file(path: str | Path) -> dict[str, Any]:
    """Disk-backed full-file QA without holding millions of speeches in RAM."""
    counts: Counter[str] = Counter()
    years: Counter[str] = Counter()
    duplicate_ids = []
    duplicate_text_count = 0
    errors = []
    words = 0
    scratch = "/tmp/opencode" if Path("/tmp/opencode").is_dir() else None
    with tempfile.TemporaryDirectory(prefix="parliament-qa-", dir=scratch) as tmp:
        connection = sqlite3.connect(str(Path(tmp) / "qa.sqlite"))
        connection.execute("CREATE TABLE ids (id TEXT PRIMARY KEY)")
        connection.execute("CREATE TABLE texts (hash TEXT PRIMARY KEY)")
        for index, row in enumerate(iter_jsonl(path), 1):
            country, sid = str(row.get("country", "")), str(row.get("speech_id", ""))
            counts[country] += 1
            if not sid or not row.get("source_url") or not row.get("source_identifier"):
                errors.append(f"record {index}: missing ID or provenance")
            else:
                try:
                    connection.execute("INSERT INTO ids VALUES (?)", (sid,))
                except sqlite3.IntegrityError:
                    duplicate_ids.append(sid)
            try:
                day = date.fromisoformat(str(row.get("date", "")))
                years[f"{country}:{day.year}"] += 1
            except ValueError:
                errors.append(f"record {index}: invalid date")
            text = str(row.get("speech_text", ""))
            if not text.strip() or int(row.get("word_count", -1)) != word_count(text):
                errors.append(f"record {index}: empty text or inconsistent word count")
            else:
                words += int(row["word_count"])
                digest = hashlib.sha256(" ".join(text.casefold().split()).encode("utf-8")).hexdigest()
                try:
                    connection.execute("INSERT INTO texts VALUES (?)", (digest,))
                except sqlite3.IntegrityError:
                    duplicate_text_count += 1
            if len(errors) > 1000:
                raise ValueError("too many corpus integrity errors; first: " + "; ".join(errors[:5]))
        connection.close()
    return {"records": sum(counts.values()), "words": words, "countries": dict(counts),
            "country_year_counts": dict(sorted(years.items())), "duplicate_speech_ids": duplicate_ids[:20],
            "duplicate_speech_id_count": len(duplicate_ids),
            "duplicate_text_count": duplicate_text_count, "errors": errors, "valid": not errors and not duplicate_ids}


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
