"""Descriptive, non-causal splits of already-classified parliamentary speech."""
from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable, Iterable
import hashlib
from typing import Any

from .analysis import response_shares


def descriptive_breakdowns(
    speeches: Iterable[dict[str, Any]],
    response_for_speech: Callable[[dict[str, Any]], dict[str, Any]],
    *, min_words: int = 40, min_speaker_speeches: int = 10,
) -> dict[str, list[dict[str, Any]]]:
    """Stream party/term/length/speaker summaries without alleging personal AI use.

    Speaker groups are stable local pseudonyms, not member names or a claim
    about the member's own writing. No individual row is emitted below the
    specified minimum number of eligible interventions. Unknown party/term
    metadata is explicit. Government status and debate topic are not inferred
    from weak metadata.
    """
    splits = ("party", "legislative_term", "length_band", "speaker")
    groups: dict[tuple[str, str, str, str], dict[str, float]] = defaultdict(
        lambda: {"speeches": 0, "words": 0, "ai_words": 0.0,
                 "mixed_words": 0.0, "ai_speech_sum": 0.0, "mixed_speech_sum": 0.0})
    for speech in speeches:
        words = int(speech.get("word_count", 0))
        if words < min_words:
            continue
        country = str(speech["country"])
        year = str(speech["date"])[:4]
        response = response_for_speech(speech)
        ai, mixed = response_shares(response, str(speech.get("speech_id", "")))
        band = "40–99" if words < 100 else "100–249" if words < 250 else "250+"
        categories = [
            ("party", year, str(speech.get("party") or "__UNKNOWN__").strip() or "__UNKNOWN__"),
            ("legislative_term", year, str(speech.get("legislative_term") or "__UNKNOWN__")),
            ("length_band", year, band),
        ]
        speaker_id = str(speech.get("speaker_id") or "").strip()
        if speaker_id and speaker_id.casefold() not in {"0", "none", "null", "unknown"}:
            pseudonym = hashlib.sha256(f"{country}|{speaker_id}".encode("utf-8")).hexdigest()[:16]
            categories.append(("speaker", "all", pseudonym))
        for dimension, period, category in categories:
            group = groups[dimension, country, period, category]
            group["speeches"] += 1
            group["words"] += words
            group["ai_words"] += words * ai
            group["mixed_words"] += words * mixed
            group["ai_speech_sum"] += ai
            group["mixed_speech_sum"] += mixed

    results: dict[str, list[dict[str, Any]]] = {dimension: [] for dimension in splits}
    for (dimension, country, period, category), group in sorted(groups.items()):
        count = int(group["speeches"])
        if dimension == "speaker" and count < min_speaker_speeches:
            continue
        words = int(group["words"])
        results[dimension].append({
            "country": country, "period": period, "group": category,
            "speeches": count, "words": words,
            "ai_word_share": group["ai_words"] / words,
            "mixed_word_share": group["mixed_words"] / words,
            "ai_plus_mixed_word_share": (group["ai_words"] + group["mixed_words"]) / words,
            "ai_speech_weighted_share": group["ai_speech_sum"] / count,
        })
    return results
