"""Analysis functions for Pangram word fractions and parliamentary aggregates."""
from __future__ import annotations

from collections import defaultdict
from datetime import date
from typing import Any, Iterable


def _period(day: date, kind: str) -> str:
    if kind == "year":
        return f"{day.year:04d}"
    if kind == "quarter":
        return f"{day.year:04d}-Q{(day.month - 1) // 3 + 1}"
    if kind == "month":
        return f"{day.year:04d}-{day.month:02d}"
    raise ValueError("period must be month, quarter, or year")


def _fraction(response: dict[str, Any], key: str) -> float:
    value = float(response.get(key, 0.0))
    if not 0.0 <= value <= 1.0:
        raise ValueError(f"{key} must be between 0 and 1")
    return value


def aggregate_results(
    speeches: Iterable[Any],
    responses: dict[str, dict[str, Any]],
    *, period: str = "month", min_words: int = 40,
    exclude_ministers: bool = False, exclude_chairs: bool = False,
) -> list[dict[str, Any]]:
    """Return word- and speech-weighted AI/mixed shares grouped by country and time."""
    groups: dict[tuple[str, str], dict[str, float]] = defaultdict(
        lambda: {"speeches": 0, "words": 0, "ai_words": 0.0, "mixed_words": 0.0,
                "ai_speech_sum": 0.0, "mixed_speech_sum": 0.0})
    for speech in speeches:
        get = speech.get if isinstance(speech, dict) else lambda key, default=None: getattr(speech, key, default)
        words = int(get("word_count", 0))
        if words < min_words:
            continue
        role = str(get("speaker_role", "")).casefold()
        name = str(get("speaker_name", "")).casefold()
        if exclude_ministers and "minister" in role:
            continue
        if exclude_chairs and (any(term in role for term in ("chair", "president", "speaker", "presiding", "voorzitter", "marszał"))
                               or any(term in name for term in ("le président", "la présidente", "presidenta", "presidente de la mesa"))):
            continue
        speech_id = str(get("speech_id", ""))
        if speech_id not in responses:
            raise KeyError(f"missing Pangram response for {speech_id}")
        response = responses[speech_id]
        ai = _fraction(response, "fraction_ai")
        mixed = _fraction(response, "fraction_ai_assisted")
        if ai + mixed > 1.000001:
            raise ValueError(f"AI and assisted fractions exceed 1 for {speech_id}")
        ai_words = words * ai
        mixed_words = words * mixed
        windows = response.get("windows")
        if isinstance(windows, list) and windows:
            window_ai = window_mixed = 0
            classified_words = 0
            for window in windows:
                label = str(window.get("label", "")).casefold().replace("_", "-")
                count = int(window.get("word_count", 0))
                if count < 0:
                    raise ValueError(f"negative window word count for {speech_id}")
                classified_words += count
                if label in {"ai-generated", "ai-written", "ai"}:
                    window_ai += count
                elif label in {"ai-assisted", "mixed", "ai-assisted / mixed"}:
                    window_mixed += count
            if classified_words:
                # Pangram 4 can normalize the submitted text. Its window word
                # count need not equal our Unicode tokenizer's word count.
                # Scale window proportions to the common source denominator.
                ai = window_ai / classified_words
                mixed = window_mixed / classified_words
                ai_words = words * ai
                mixed_words = words * mixed
        day = date.fromisoformat(str(get("date")))
        key = (str(get("country")), _period(day, period))
        group = groups[key]
        group["speeches"] += 1
        group["words"] += words
        group["ai_words"] += ai_words
        group["mixed_words"] += mixed_words
        group["ai_speech_sum"] += ai
        group["mixed_speech_sum"] += mixed
    result = []
    for (country, period_value), group in sorted(groups.items()):
        words, n = group["words"], group["speeches"]
        result.append({
            "country": country, "period": period_value, "speeches": int(n), "words": int(words),
            "ai_words_estimate": group["ai_words"], "mixed_words_estimate": group["mixed_words"],
            "ai_word_share": group["ai_words"] / words if words else 0.0,
            "mixed_word_share": group["mixed_words"] / words if words else 0.0,
            "ai_plus_mixed_word_share": (group["ai_words"] + group["mixed_words"]) / words if words else 0.0,
            "ai_speech_weighted_share": group["ai_speech_sum"] / n if n else 0.0,
            "mixed_speech_weighted_share": group["mixed_speech_sum"] / n if n else 0.0,
        })
    return result
