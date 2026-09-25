"""Conservative, reproducible country-month simple random sampling.

Allocation uses only corpus metadata. Reserving the most expensive speech in
each stratum ensures the realized selection cannot exceed the stated cap.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import date
from decimal import Decimal
import hashlib
import heapq
import math
from pathlib import Path
from typing import Any

from .io import iter_jsonl, write_jsonl


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def plan_sample(corpus: str | Path, *, budget: float, price_per_1000_words: float,
                seed: int = 2026) -> dict[str, Any]:
    """Plan fixed n per nonempty country-month; never condition n on selected texts."""
    if not math.isfinite(budget) or budget < 0 or not math.isfinite(price_per_1000_words) or price_per_1000_words <= 0:
        raise ValueError("sampling requires a finite non-negative budget and positive price")
    path = Path(corpus)
    populations: dict[str, dict[str, int]] = defaultdict(
        lambda: {"eligible": 0, "max_units": 0, "total_units": 0})
    for row in iter_jsonl(path):
        words = int(row["word_count"])
        if words < 40:
            continue
        stratum = f"{row['country']}:{str(row['date'])[:7]}"
        # Strict date parsing prevents treating malformed labels as valid months.
        date.fromisoformat(str(row["date"]))
        units = math.ceil(words / 100)
        group = populations[stratum]
        group["eligible"] += 1
        group["total_units"] += units
        group["max_units"] = max(group["max_units"], units)
    unit_price = price_per_1000_words / 10
    # Floor in units, never round a dollar cap up. Small floating-point
    # representation errors must not permit a submission above the cap.
    available = int(Decimal(str(budget)) / (Decimal(str(price_per_1000_words)) / 10))
    minimum = sum(group["max_units"] for group in populations.values())
    if minimum > available:
        raise ValueError(
            f"budget cannot cover one possible speech in each of {len(populations)} "
            f"populated country-months: conservative minimum ${minimum * unit_price:.2f}; "
            "increase the budget or explicitly change the study scope")
    full_units = sum(g["total_units"] for g in populations.values())
    n = {key: 1 for key in populations}
    reserved = minimum
    # Allocate the next slot to the least-sampled month. Fixed allocations are
    # determined by N and maximum possible cost, NOT by detector output or the
    # actual cost of the random winners. This keeps within-month probabilities n/N.
    if full_units <= available:
        n = {key: group["eligible"] for key, group in populations.items()}
        reserved = full_units
    queue = [(1 / group["eligible"], key) for key, group in populations.items()
             if group["eligible"] > 1 and n[key] < group["eligible"]]
    heapq.heapify(queue)
    while queue:
        fraction, key = heapq.heappop(queue)
        group = populations[key]
        cost = group["max_units"]
        if cost > available - reserved:
            # No later allocation can use this slot; another month may fit.
            continue
        n[key] += 1
        reserved += cost
        if n[key] < group["eligible"]:
            heapq.heappush(queue, (n[key] / group["eligible"], key))
    return {"method": "country-month SRS without replacement", "seed": seed,
            "source_sha256": file_sha256(path), "budget_usd": budget,
            "price_per_1000_words": price_per_1000_words,
            "reserved_units": reserved, "reserved_usd": reserved * unit_price,
            "full_units": full_units,
            "strata": {key: {**group, "selected": n[key],
                             "inclusion_probability": n[key] / group["eligible"]}
                       for key, group in sorted(populations.items())}}


def write_sample(corpus: str | Path, output: str | Path, plan: dict[str, Any]) -> dict[str, Any]:
    """Use bottom-n pseudorandom hashes per month; write only selected text."""
    path = Path(corpus)
    if file_sha256(path) != plan["source_sha256"]:
        raise ValueError("corpus changed since the sample plan was created")
    heaps: dict[str, list[tuple[int, str]]] = defaultdict(list)
    for row in iter_jsonl(path):
        if int(row["word_count"]) < 40:
            continue
        key = f"{row['country']}:{str(row['date'])[:7]}"
        size = plan["strata"][key]["selected"]
        sid = str(row["speech_id"])
        priority = int.from_bytes(hashlib.sha256(
            f"{plan['seed']}|{key}|{sid}".encode("utf-8")).digest(), "big")
        heap = heaps[key]
        candidate = (-priority, sid)
        if len(heap) < size:
            heapq.heappush(heap, candidate)
        elif candidate > heap[0]:
            heapq.heapreplace(heap, candidate)
    chosen = {sid: key for key, heap in heaps.items() for _, sid in heap}
    if len(chosen) != sum(g["selected"] for g in plan["strata"].values()):
        raise ValueError("sample contains duplicate speech IDs or missing strata")

    def rows():
        for row in iter_jsonl(path):
            key = chosen.get(str(row["speech_id"]))
            if key is not None:
                yield {**row, "sampling_weight": 1 / plan["strata"][key]["inclusion_probability"]}

    output = Path(output)
    if output.resolve() == path.resolve():
        raise ValueError("sample path cannot overwrite the source corpus")
    write_jsonl(output, rows())
    if file_sha256(path) != plan["source_sha256"]:
        output.unlink()
        raise ValueError("corpus changed while the sample was written")
    plan["sample_sha256"] = file_sha256(output)
    plan["sampled_speeches"] = len(chosen)
    return plan
