"""Canonical speech record for the multilingual parliamentary corpus."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date
import re
from typing import Any

_WORD = re.compile(r"[^\W_]+(?:['’][^\W_]+)*", re.UNICODE)


def word_count(text: str) -> int:
    """Count Unicode letter/digit tokens without translating or rewriting text."""
    return len(_WORD.findall(text or ""))


@dataclass(frozen=True)
class Speech:
    country: str
    parliament: str
    chamber: str
    date: str
    session_id: str
    speech_id: str
    speaker_id: str
    speaker_name: str
    speech_text: str
    source_url: str
    party: str = ""
    speaker_role: str = ""
    legislative_term: str = ""
    source_type: str = "official_transcript"
    source_identifier: str = ""
    raw_text: str = ""
    cleaning_notes: str = ""
    text_language: str = ""
    record_status: str = ""
    word_count: int = 0

    def __post_init__(self) -> None:
        date.fromisoformat(self.date)
        for name in ("country", "parliament", "chamber", "session_id", "speech_id", "speaker_name", "speech_text", "source_url"):
            if not getattr(self, name):
                raise ValueError(f"{name} must not be empty")
        calculated = word_count(self.speech_text)
        if self.word_count not in (0, calculated):
            raise ValueError(f"word_count mismatch for {self.speech_id}: {self.word_count} != {calculated}")
        object.__setattr__(self, "word_count", calculated)
        if not self.source_identifier:
            object.__setattr__(self, "source_identifier", self.speech_id)
        if not self.raw_text:
            object.__setattr__(self, "raw_text", self.speech_text)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, record: dict[str, Any]) -> "Speech":
        fields = cls.__dataclass_fields__
        return cls(**{key: value for key, value in record.items() if key in fields})
