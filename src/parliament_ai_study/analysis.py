"""Analysis functions for Pangram word fractions and parliamentary aggregates."""
from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable, Mapping
from datetime import date
import re
from typing import Any, Iterable

# Role vocabulary measured on the six normalized corpora. Filtering has to
# work in every source language: adapters emit free-text roles (Germany,
# Netherlands, Poland), normalized tokens (Italy, Spain, France), or both.
#
# Ministers: the stem "minist" covers German Minister(in), French
# ministre/ministère, Dutch minister(-president), Italian minister/ministro,
# Spanish minister/ministro, and Polish Prezes Rady Ministrów. The remaining
# markers catch cabinet roles that lack that stem (chancellor, premier,
# secretaries of state, keeper of the seals).
MINISTER_MARKERS = (
    "minist", "kanzler", "premier", "secrétaire d'état", "secretaire d'etat",
    "staatssecretaris", "garde des sceaux", "presidente del consiglio",
    "sottosegretari",
)

# Presiding officers: "presiding_officer" is the token emitted by the French,
# Italian, and Spanish adapters. German uses free-text Präsident(in)/
# Vizepräsident(in) titles and Poland uses Marszałek/Wicemarszałek (observed
# in the role or the name field). The German state title Ministerpräsident(in)
# is a head of government, not a chamber chair, so it is handled by the
# minister filter instead. Committee chairs are not chamber chairs and are
# deliberately not excluded: the Dutch voorzitter roles are all committee or
# Presidium chairs, and French président de la commission roles are likewise
# committee offices. The Dutch plenary chair is not identifiable from the
# role metadata, so Dutch rows are never excluded by this filter.
CHAIR_ROLE_MARKERS = ("präsident", "praeses", "marszał", "presiding")
CHAIR_NAME_PREFIXES = ("marszałek", "wicemarszałek")
CHAIR_NAME_MARKERS = (
    "le président", "la présidente", "président de la séance",
    "presidente de la mesa", "presidente de la cámara",
)

# Pangram window labels, normalized to lowercase ASCII alphanumerics.
AI_WINDOW_LABELS = {"ai-generated", "ai-written", "ai", "generated-by-ai",
                    "machine-generated", "ai-text", "ai-generated-text"}
MIXED_WINDOW_LABELS = {"ai-assisted", "mixed", "ai-assisted-mixed",
                       "ai-assisted-and-mixed", "mixed-ai-human"}
HUMAN_WINDOW_LABELS = {"human-written", "human", "human-text", "human-generated",
                       "non-ai", "not-ai", "not-ai-written"}


def _normalize_role(value: Any) -> str:
    return str(value or "").casefold().replace("’", "'").strip()


def is_minister_role(role: Any) -> bool:
    """True for cabinet/ministerial roles in any of the six source languages."""
    normalized = _normalize_role(role)
    return any(marker in normalized for marker in MINISTER_MARKERS)


def is_chair_role(role: Any, speaker_name: Any = "") -> bool:
    """True for presiding-officer/chair roles across the six chambers.

    French, Italian, and Spanish adapters already mark the plenary chair as
    ``presiding_officer``. For free-text roles the match is on the plenary
    chair vocabulary; generic French ``président de la commission …`` roles
    are committee chairs and are deliberately not excluded.
    """
    normalized = _normalize_role(role)
    if normalized == "presiding_officer":
        return True
    if "ministerpräsident" in normalized:
        return False
    if any(marker in normalized for marker in CHAIR_ROLE_MARKERS):
        return True
    normalized_name = _normalize_role(speaker_name)
    if any(normalized_name.startswith(prefix) for prefix in CHAIR_NAME_PREFIXES):
        return True
    return any(marker in normalized_name for marker in CHAIR_NAME_MARKERS)


def _normalize_window_label(label: Any) -> str:
    """Fold ``AI Generated``/``ai_generated``/``AI-Assisted / Mixed`` to one key."""
    return re.sub(r"[^a-z0-9]+", "-", str(label or "").casefold()).strip("-")


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


ResponseSource = Mapping[str, dict[str, Any]] | Callable[[Any], dict[str, Any]]


def response_shares(response: dict[str, Any], speech_id: str) -> tuple[float, float]:
    """AI-only and assisted fractions on the common source-word denominator."""
    ai = _fraction(response, "fraction_ai")
    mixed = _fraction(response, "fraction_ai_assisted")
    if ai + mixed > 1.000001:
        raise ValueError(f"AI and assisted fractions exceed 1 for {speech_id}")
    windows = response.get("windows")
    if isinstance(windows, list) and windows:
        window_ai = window_mixed = 0
        classified_words = 0
        unknown_labels: set[str] = set()
        for window in windows:
            label = _normalize_window_label(window.get("label", ""))
            count = int(window.get("word_count", 0))
            if count < 0:
                raise ValueError(f"negative window word count for {speech_id}")
            classified_words += count
            if label in AI_WINDOW_LABELS:
                window_ai += count
            elif label in MIXED_WINDOW_LABELS:
                window_mixed += count
            elif label not in HUMAN_WINDOW_LABELS:
                unknown_labels.add(label)
        if classified_words and not unknown_labels:
            # Pangram may normalize text; its window words need not equal our
            # Unicode tokenizer's count. Use its proportions, not raw offsets.
            ai = window_ai / classified_words
            mixed = window_mixed / classified_words
        # Unknown labels fall back to validated response-level fractions.
    return ai, mixed


def aggregate_results(
    speeches: Iterable[Any],
    responses: ResponseSource,
    *, period: str = "month", min_words: int = 40,
    exclude_ministers: bool = False, exclude_chairs: bool = False,
) -> list[dict[str, Any]]:
    """Return word- and speech-weighted AI/mixed shares grouped by country and time."""
    groups: dict[tuple[str, str], dict[str, float]] = defaultdict(
        lambda: {"speeches": 0, "sampled_speeches": 0, "words": 0, "ai_words": 0.0, "mixed_words": 0.0,
                "ai_speech_sum": 0.0, "mixed_speech_sum": 0.0})
    for speech in speeches:
        get = speech.get if isinstance(speech, dict) else lambda key, default=None: getattr(speech, key, default)
        words = int(get("word_count", 0))
        if words < min_words:
            continue
        role = str(get("speaker_role", ""))
        name = str(get("speaker_name", ""))
        if exclude_ministers and is_minister_role(role):
            continue
        if exclude_chairs and is_chair_role(role, name):
            continue
        speech_id = str(get("speech_id", ""))
        response = responses(speech) if callable(responses) else responses[speech_id]
        ai, mixed = response_shares(response, speech_id)
        weight = float(get("sampling_weight", 1))
        if not 0 < weight < float("inf"):
            raise ValueError(f"invalid sampling weight for {speech_id}")
        ai_words = words * weight * ai
        mixed_words = words * weight * mixed
        day = date.fromisoformat(str(get("date")))
        key = (str(get("country")), _period(day, period))
        group = groups[key]
        group["speeches"] += weight
        group["sampled_speeches"] += 1
        group["words"] += words * weight
        group["ai_words"] += ai_words
        group["mixed_words"] += mixed_words
        group["ai_speech_sum"] += ai * weight
        group["mixed_speech_sum"] += mixed * weight
    result = []
    for (country, period_value), group in sorted(groups.items()):
        words, n = group["words"], group["speeches"]
        result.append({
            "country": country, "period": period_value,
            "speeches": n, "sampled_speeches": int(group["sampled_speeches"]), "words": words,
            "ai_words_estimate": group["ai_words"], "mixed_words_estimate": group["mixed_words"],
            "ai_word_share": group["ai_words"] / words if words else 0.0,
            "mixed_word_share": group["mixed_words"] / words if words else 0.0,
            "ai_plus_mixed_word_share": (group["ai_words"] + group["mixed_words"]) / words if words else 0.0,
            "ai_speech_weighted_share": group["ai_speech_sum"] / n if n else 0.0,
            "mixed_speech_weighted_share": group["mixed_speech_sum"] / n if n else 0.0,
        })
    return result
