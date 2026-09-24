"""Transparent Pangram cost estimates; rates remain configurable and mutable."""
from __future__ import annotations

from collections import defaultdict
from datetime import date
import math
from typing import Any, Iterable


def _get(record: Any, key: str, default: Any = None) -> Any:
    return record.get(key, default) if isinstance(record, dict) else getattr(record, key, default)


def estimate_cost(
    speeches: Iterable[Any],
    *,
    price_per_1000_words: float,
    billing_unit_words: int = 100,
    country: str | None = None,
    years: set[int] | None = None,
    period: str | None = None,
    min_words: int = 40,
) -> dict[str, Any]:
    """Estimate cost for records, optionally restricted to a country/year period."""
    if price_per_1000_words < 0 or billing_unit_words < 1:
        raise ValueError("price must be non-negative and billing_unit_words positive")
    counts: dict[str, dict[str, Any]] = defaultdict(lambda: {"speeches": 0, "words": 0, "estimated_api_units": 0})
    total_speeches = total_words = 0
    total_units = 0
    for item in speeches:
        item_country = str(_get(item, "country", ""))
        item_date = str(_get(item, "date", ""))
        if country and item_country != country:
            continue
        try:
            year = date.fromisoformat(item_date).year if item_date else None
        except ValueError:
            # A malformed date must not crash a whole-corpus estimate; the
            # disk-backed QA reports bad dates separately.
            year = None
        if years is not None and (year is None or year not in years):
            continue
        if period == "historical" and (year is None or year > 2021):
            continue
        if period == "post_chatgpt" and (year is None or year < 2023):
            continue
        words = int(_get(item, "word_count", 0))
        if words < 0:
            raise ValueError("word_count must be non-negative")
        if words < min_words:
            continue
        counts[item_country]["speeches"] += 1
        counts[item_country]["words"] += words
        # Pangram bills one *started* word block per item, not fractional
        # blocks across the combined corpus. Each intervention is one task.
        units = math.ceil(words / billing_unit_words)
        counts[item_country]["estimated_api_units"] += units
        total_speeches += 1
        total_words += words
        total_units += units
    rows = []
    for name, values in sorted(counts.items()):
        rows.append({"country": name, **values,
                      "estimated_cost": values["estimated_api_units"] * billing_unit_words * price_per_1000_words / 1000})
    return {"rows": rows, "speeches": total_speeches, "words": total_words,
            "estimated_api_units": total_units,
            "estimated_cost": total_units * billing_unit_words * price_per_1000_words / 1000,
            "price_per_1000_words": price_per_1000_words,
            "billing_unit_words": billing_unit_words}
