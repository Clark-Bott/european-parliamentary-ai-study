"""Polish Sejm API transcript acquisition and normalization."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from html.parser import HTMLParser
import json
from pathlib import Path
import re
from typing import Any, Iterator
from urllib.parse import quote

from ..io import write_jsonl
from ..models import Speech
from .download import download_file

API = "https://api.sejm.gov.pl/sejm"
TERMS = (8, 9, 10)
_STAGE_PARAGRAPH = re.compile(
    r"^\(?\s*(?:głos z sali|oklaski|protesty|protest|wesołość|poruszenie|brawa)(?:\s*:.*?)?\s*[.!]?\)?$",
    re.IGNORECASE,
)


class _ParagraphText(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.paragraphs: list[str] = []
        self._inside = False
        self._skip = False
        self._buffer: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() == "p":
            attributes = dict(attrs)
            self._inside = True
            self._skip = "punkt-tytul" in (attributes.get("class") or "").split()
            self._buffer = []
        elif tag.lower() == "br" and self._inside and not self._skip:
            self._buffer.append(" ")

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "p" and self._inside:
            paragraph = " ".join("".join(self._buffer).split())
            if paragraph and not self._skip:
                self.paragraphs.append(paragraph)
            self._inside = False
            self._skip = False
            self._buffer = []

    def handle_data(self, data: str) -> None:
        if self._inside and not self._skip:
            self._buffer.append(data)


def parse_sejm_statement(html_data: str | bytes, statement: dict[str, Any], *,
                         term: int, proceeding: int, date_value: str,
                         source_url: str) -> Speech | None:
    """Parse one official statement body; preserve raw paragraphs and strip audience cues."""
    if statement.get("unspoken"):
        return None
    if isinstance(html_data, bytes):
        html_data = html_data.decode("utf-8", errors="replace")
    parser = _ParagraphText()
    parser.feed(html_data)
    raw_paragraphs = parser.paragraphs
    raw_text = " ".join(raw_paragraphs)
    cleaned_paragraphs = [paragraph for paragraph in raw_paragraphs
                          if not _STAGE_PARAGRAPH.match(paragraph)]
    speech_text = " ".join(cleaned_paragraphs)
    if not speech_text.strip():
        return None
    speech_num = int(statement["num"])
    speech_id = f"sejm-term{term}-proceeding{proceeding}-{date_value}-statement{speech_num}"
    speaker_name = str(statement.get("name", "")).strip()
    if not speaker_name:
        return None
    return Speech(
        country="Poland", parliament="Sejm", chamber="Sejm",
        date=date_value,
        session_id=f"sejm-term{term}-proceeding{proceeding}-{date_value}",
        speech_id=speech_id, speaker_id=str(statement.get("memberID", "")),
        speaker_name=speaker_name, speaker_role=str(statement.get("function", "")),
        legislative_term=str(term), speech_text=speech_text, raw_text=raw_text,
        source_url=source_url, source_identifier=speech_id,
        source_type="official_sejm_html", text_language="pl",
        cleaning_notes="Removed standalone Polish audience/stage-direction paragraphs; raw_text retains them."
        if speech_text != raw_text else "")


def _cached_download(url: str, destination: Path, manifest_path: str | Path) -> bytes:
    if not destination.is_file():
        download_file(url, destination, manifest_path=manifest_path)
    return destination.read_bytes()


def download_sejm_date(term: int, proceeding: int, date_value: str, *,
                       raw_dir: str | Path = "data/raw",
                       manifest_path: str | Path = "data/manifests/source_manifest.jsonl",
                       workers: int = 4) -> list[Speech]:
    """Download statement metadata and text bodies for one sitting day."""
    if workers < 1:
        raise ValueError("workers must be positive")
    day_dir = Path(raw_dir) / "poland" / f"term-{term}" / f"proceeding-{proceeding}" / date_value
    metadata_url = f"{API}/term{term}/proceedings/{proceeding}/{date_value}/transcripts"
    metadata_path = day_dir / "statements.json"
    metadata = json.loads(_cached_download(metadata_url, metadata_path, manifest_path))
    statements = [statement for statement in metadata.get("statements", [])
                  if not statement.get("unspoken")]

    def fetch(statement: dict[str, Any]) -> tuple[int, Speech | None]:
        number = int(statement["num"])
        body_url = f"{metadata_url}/{number}"
        body_path = day_dir / f"statement-{number}.html"
        body = _cached_download(body_url, body_path, manifest_path)
        speech = parse_sejm_statement(body, statement, term=term, proceeding=proceeding,
                                      date_value=date_value, source_url=body_url)
        return number, speech

    if workers == 1:
        fetched = [fetch(statement) for statement in statements]
    else:
        with ThreadPoolExecutor(max_workers=workers) as executor:
            fetched = list(executor.map(fetch, statements))
    return [speech for _, speech in sorted(fetched, key=lambda item: item[0])
            if speech is not None]


def iter_sejm_speeches(*, start_year: int = 2018, end_year: int = 2026,
                       terms: tuple[int, ...] = TERMS,
                       raw_dir: str | Path = "data/raw",
                       manifest_path: str | Path = "data/manifests/source_manifest.jsonl",
                       workers: int = 4) -> Iterator[Speech]:
    """Fetch all plenary statement bodies in the requested years; resumable via raw-file cache."""
    for term in terms:
        list_url = f"{API}/term{term}/proceedings"
        list_path = Path(raw_dir) / "poland" / f"term-{term}" / "proceedings.json"
        proceedings = json.loads(_cached_download(list_url, list_path, manifest_path))
        for sitting in proceedings:
            proceeding = int(sitting["number"])
            for date_value in sitting.get("dates", []):
                year = int(date_value[:4])
                if start_year <= year <= end_year:
                    yield from download_sejm_date(term, proceeding, date_value,
                                                  raw_dir=raw_dir, manifest_path=manifest_path,
                                                  workers=workers)


def build_sejm_corpus(output_path: str | Path, *, start_year: int = 2018, end_year: int = 2026,
                      terms: tuple[int, ...] = TERMS, raw_dir: str | Path = "data/raw",
                      manifest_path: str | Path = "data/manifests/source_manifest.jsonl",
                      workers: int = 4) -> dict[str, int]:
    records = words = 0

    def serialized():
        nonlocal records, words
        for speech in iter_sejm_speeches(start_year=start_year, end_year=end_year, terms=terms,
                                         raw_dir=raw_dir, manifest_path=manifest_path,
                                         workers=workers):
            records += 1
            words += speech.word_count
            yield speech.to_dict()

    write_jsonl(output_path, serialized())
    return {"records": records, "words": words}


def main(argv: list[str] | None = None) -> int:
    import argparse
    parser = argparse.ArgumentParser(description="Acquire Sejm plenary transcript interventions")
    parser.add_argument("--start-year", type=int, default=2018)
    parser.add_argument("--end-year", type=int, default=2026)
    parser.add_argument("--output", type=Path, default=Path("data/processed/poland_speeches.jsonl"))
    parser.add_argument("--raw-dir", type=Path, default=Path("data/raw"))
    parser.add_argument("--manifest", type=Path, default=Path("data/manifests/source_manifest.jsonl"))
    parser.add_argument("--workers", type=int, default=4,
                        help="bounded parallel statement-body downloads per sitting day")
    args = parser.parse_args(argv)
    if args.workers < 1:
        parser.error("--workers must be positive")
    stats = build_sejm_corpus(args.output, start_year=args.start_year, end_year=args.end_year,
                              raw_dir=args.raw_dir, manifest_path=args.manifest,
                              workers=args.workers)
    print(json.dumps({"country": "Poland", "output": str(args.output), **stats}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
