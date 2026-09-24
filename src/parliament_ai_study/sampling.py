"""Deterministic, length/year/party-stratified historical control sampling."""
from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import asdict, is_dataclass
from datetime import date
import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable

from .io import iter_jsonl, write_jsonl


def _get(row: Any, key: str, default: Any = None) -> Any:
    if isinstance(row, dict):
        return row.get(key, default)
    return getattr(row, key, default)


def _length_band(words: int) -> str:
    if words < 100:
        return "short"
    if words < 250:
        return "medium"
    return "long"


def sample_historical_controls(
    speeches: Iterable[Any], *, sample_size_per_country: int, seed: int = 2026,
    start_year: int = 2018, end_year: int = 2021, min_words: int = 40,
    max_per_speaker: int = 2,
) -> list[dict[str, Any]]:
    """Select repeatable pre-LLM controls, rotating across year/party/length buckets.

    Buckets are traversed round-robin; within each bucket, order is the SHA-256
    of the seed and immutable speech ID. Python's process-randomized ``hash`` is
    deliberately not used. Missing speaker IDs fall back to speech IDs.
    """
    if sample_size_per_country < 1 or max_per_speaker < 1:
        raise ValueError("sample size and max_per_speaker must be positive")
    if start_year > end_year or min_words < 0:
        raise ValueError("invalid year range or minimum word count")
    buckets: dict[tuple[str, int, str, str], dict[str, tuple[str, dict[str, Any], str]]] = defaultdict(dict)
    for source in speeches:
        day = date.fromisoformat(str(_get(source, "date", "")))
        words = int(_get(source, "word_count", 0))
        if not start_year <= day.year <= end_year or words < min_words:
            continue
        country = str(_get(source, "country", ""))
        speech_id = str(_get(source, "speech_id", ""))
        if not country or not speech_id:
            continue
        if is_dataclass(source):
            record = asdict(source)  # type: ignore[arg-type]
        elif isinstance(source, dict):
            record = dict(source)
        else:
            raise TypeError("speech records must be dictionaries or dataclasses")
        speaker = str(_get(source, "speaker_id", "") or speech_id)
        if speaker.casefold() in {"0", "unknown", "none", "null", "n/a"}:
            speaker = speech_id
        party = str(_get(source, "party", "") or "__UNKNOWN__")
        key = (country, day.year, party, _length_band(words))
        priority = hashlib.sha256(f"{seed}|{speech_id}".encode("utf-8")).hexdigest()
        existing = buckets[key].get(speaker)
        if existing is None or priority < existing[0]:
            buckets[key][speaker] = (priority, record, speaker)
    if not buckets:
        return []
    sorted_buckets = {key: sorted(entries.values(), key=lambda item: item[0])
                      for key, entries in buckets.items()}
    countries = sorted({key[0] for key in buckets})
    selected: list[dict[str, Any]] = []
    for country in countries:
        years = sorted({key[1] for key in buckets if key[0] == country})
        keys_by_year = {
            year: [key for key in buckets if key[0] == country and key[1] == year]
            for year in years
        }
        for year in years:
            keys_by_year[year].sort(
                key=lambda key: hashlib.sha256(f"{seed}|{key}".encode("utf-8")).hexdigest())
        per_speaker: dict[str, int] = defaultdict(int)
        chosen_by_year: dict[int, list[dict[str, Any]]] = {year: [] for year in years}
        exhausted = {key: 0 for key in buckets if key[0] == country}
        bucket_cursor = {year: 0 for year in years}

        def take_one(year: int) -> bool:
            keys = keys_by_year[year]
            if not keys:
                return False
            for offset in range(len(keys)):
                bucket_index = (bucket_cursor[year] + offset) % len(keys)
                key = keys[bucket_index]
                entries = sorted_buckets[key]
                while exhausted[key] < len(entries):
                    _, record, speaker = entries[exhausted[key]]
                    exhausted[key] += 1
                    if per_speaker[speaker] >= max_per_speaker:
                        continue
                    per_speaker[speaker] += 1
                    chosen_by_year[year].append(record)
                    bucket_cursor[year] = (bucket_index + 1) % len(keys)
                    return True
            return False

        base, extra = divmod(sample_size_per_country, len(years))
        quotas = {year: base + (1 if index < extra else 0)
                  for index, year in enumerate(years)}
        while True:
            progress = False
            for year in years:
                if len(chosen_by_year[year]) < quotas[year] and take_one(year):
                    progress = True
            if not progress or all(len(chosen_by_year[y]) >= quotas[y] for y in years):
                break
        # Redistribute any unfillable year quota across the remaining years.
        while sum(len(items) for items in chosen_by_year.values()) < sample_size_per_country:
            progress = False
            for year in years:
                if sum(len(items) for items in chosen_by_year.values()) >= sample_size_per_country:
                    break
                if take_one(year):
                    progress = True
            if not progress:
                break
        for year in years:
            selected.extend(chosen_by_year[year])
    selected.sort(key=lambda row: (str(row.get("country", "")), str(row.get("date", "")),
                                   str(row.get("speech_id", ""))))
    return selected


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Create a deterministic pre-LLM historical control sample")
    parser.add_argument("--corpus", type=Path, required=True, help="normalized speech-level JSONL")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--sample-size-per-country", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=2026)
    parser.add_argument("--max-per-speaker", type=int, default=2)
    parser.add_argument("--min-words", type=int, default=40)
    parser.add_argument("--start-year", type=int, default=2018)
    parser.add_argument("--end-year", type=int, default=2021)
    args = parser.parse_args(argv)
    sample = sample_historical_controls(
        iter_jsonl(args.corpus), sample_size_per_country=args.sample_size_per_country,
        seed=args.seed, max_per_speaker=args.max_per_speaker, min_words=args.min_words,
        start_year=args.start_year, end_year=args.end_year)
    write_jsonl(args.output, sample)
    print(json.dumps({
        "output": str(args.output), "records": len(sample),
        "countries": dict(sorted(Counter(r["country"] for r in sample).items())),
        "years": dict(sorted(Counter(r["date"][:4] for r in sample).items())),
        "words": sum(int(r["word_count"]) for r in sample), "seed": args.seed,
        "min_words": args.min_words, "start_year": args.start_year, "end_year": args.end_year,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
