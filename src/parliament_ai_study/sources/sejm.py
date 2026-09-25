"""Polish Sejm API transcript acquisition and normalization."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import date
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import re
from typing import Any, Iterator

from ..io import iter_jsonl, write_jsonl
from ..models import Speech
from .download import download_file

API = "https://api.sejm.gov.pl/sejm"
TERMS = (8, 9, 10)
_STAGE_PARAGRAPH = re.compile(
    r"^\(?\s*(?:głos z sali|oklaski|protesty|protest|wesołość|poruszenie|brawa)(?:\s*:.*?)?\s*[.!]?\)?$",
    re.IGNORECASE,
)


def _cutoff(through_date: str | None) -> date:
    cutoff = date.fromisoformat(through_date) if through_date else date.today()
    if cutoff > date.today():
        raise ValueError(f"Sejm acquisition cutoff is in the future: {cutoff}")
    return cutoff


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
        # Proceedings indexes, day metadata and individual statements are
        # small. A ranged probe plus the full range otherwise costs two HTTP
        # round trips for each statement; the plain GET still streams to an
        # atomic file and records the same hash/URL provenance.
        download_file(url, destination, manifest_path=manifest_path, use_range=False)
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
                        workers: int = 4, through_date: str | None = None) -> Iterator[Speech]:
    """Fetch all plenary statement bodies in the requested years; resumable via raw-file cache."""
    cutoff = _cutoff(through_date)
    for term in terms:
        list_url = f"{API}/term{term}/proceedings"
        list_path = Path(raw_dir) / "poland" / f"term-{term}" / "proceedings.json"
        proceedings = json.loads(_cached_download(list_url, list_path, manifest_path))
        for sitting in proceedings:
            proceeding = int(sitting["number"])
            if proceeding <= 0:  # provisional schedule placeholders have no transcript
                continue
            for date_value in sitting.get("dates", []):
                day = date.fromisoformat(date_value)
                if start_year <= day.year <= end_year and day <= cutoff:
                    yield from download_sejm_date(term, proceeding, date_value,
                                                  raw_dir=raw_dir, manifest_path=manifest_path,
                                                  workers=workers)


def audit_sejm_raw_coverage(raw_dir: str | Path = "data/raw", *,
                            through_date: str | None = None) -> dict[str, Any]:
    """Reconcile every 2018–2026 indexed sitting date with its spoken bodies."""
    cutoff = _cutoff(through_date)
    terms = []
    missing: list[dict[str, Any]] = []
    for term in TERMS:
        root = Path(raw_dir) / "poland" / f"term-{term}"
        proceedings_path = root / "proceedings.json"
        if not proceedings_path.is_file():
            missing.append({"term": term, "reason": "proceedings index missing"})
        proceedings = json.loads(proceedings_path.read_text(encoding="utf-8")) if proceedings_path.is_file() else []
        dates = [date_value for sitting in proceedings for date_value in sitting.get("dates", [])]
        target_days = [(int(sitting["number"]), date_value)
                       for sitting in proceedings for date_value in sitting.get("dates", [])
                       if int(sitting["number"]) > 0
                       and 2018 <= date.fromisoformat(date_value).year <= 2026
                       and date.fromisoformat(date_value) <= cutoff]
        expected_bodies = 0
        for proceeding, date_value in target_days:
            day = root / f"proceeding-{proceeding}" / date_value
            metadata_path = day / "statements.json"
            if not metadata_path.is_file():
                missing.append({"term": term, "proceeding": proceeding,
                                "date": date_value, "reason": "statement metadata missing"})
                continue
            try:
                statements = json.loads(metadata_path.read_text(encoding="utf-8"))["statements"]
            except (json.JSONDecodeError, KeyError, TypeError) as exc:
                missing.append({"term": term, "proceeding": proceeding,
                                "date": date_value, "reason": f"invalid statement metadata: {exc}"})
                continue
            if not isinstance(statements, list):
                missing.append({"term": term, "proceeding": proceeding,
                                "date": date_value, "reason": "statement list is not an array"})
                continue
            for statement in statements:
                if not isinstance(statement, dict):
                    missing.append({"term": term, "proceeding": proceeding,
                                    "date": date_value, "reason": "statement metadata is not an object"})
                    continue
                if statement.get("unspoken"):
                    continue
                expected_bodies += 1
                try:
                    number = int(statement["num"])
                except (KeyError, ValueError, TypeError):
                    missing.append({"term": term, "proceeding": proceeding,
                                    "date": date_value, "reason": "invalid statement number"})
                    continue
                if not (day / f"statement-{number}.html").is_file():
                    missing.append({"term": term, "proceeding": proceeding,
                                    "date": date_value, "statement": number,
                                    "reason": "spoken statement body missing"})
        body_files = list(root.glob("proceeding-*/**/statement-*.html"))
        metadata_files = list(root.glob("proceeding-*/**/statements.json"))
        terms.append({
            "term": term, "proceedings": len(proceedings), "dates": len(dates),
            "target_dates": len(target_days), "expected_spoken_bodies": expected_bodies,
            "first_date": min(dates) if dates else None, "last_date": max(dates) if dates else None,
            "statement_metadata_files": len(metadata_files), "statement_body_files": len(body_files),
        })
    return {"terms": terms, "through_date": cutoff.isoformat(),
            "missing": missing, "complete": not missing,
            "note": "Raw-file reconciliation against cached official proceedings indexes; "
                    "independent live-index and manual boundary review remain separate."}


def build_sejm_corpus(output_path: str | Path, *, start_year: int = 2018, end_year: int = 2026,
                      terms: tuple[int, ...] = TERMS, raw_dir: str | Path = "data/raw",
                      manifest_path: str | Path = "data/manifests/source_manifest.jsonl",
                      workers: int = 4, resume_partial: bool = False,
                      through_date: str | None = None) -> dict[str, int | str]:
    records = words = 0
    cutoff = _cutoff(through_date).isoformat()

    if resume_partial:
        target = Path(output_path)
        partial = target.with_suffix(target.suffix + ".tmp")
        if target.exists():
            raise FileExistsError(f"complete Polish corpus already exists: {target}")
        if not partial.is_file():
            raise FileNotFoundError(f"no partial Polish corpus to resume: {partial}")
        with partial.open("rb") as stream:
            stream.seek(0, os.SEEK_END)
            if stream.tell() == 0:
                raise ValueError(f"partial corpus is empty: {partial}")
            stream.seek(-1, os.SEEK_END)
            if stream.read(1) != b"\n":
                raise ValueError(f"partial corpus has an incomplete final line: {partial}")

        def resumed():
            nonlocal records, words
            iterator = iter_sejm_speeches(start_year=start_year, end_year=end_year, terms=terms,
                                         raw_dir=raw_dir, manifest_path=manifest_path,
                                         workers=workers, through_date=cutoff)
            # Do not mutate the partial file unless every saved record matches
            # the source-derived prefix in the same order and with the same text.
            for saved in iter_jsonl(partial):
                try:
                    speech = next(iterator).to_dict()
                except StopIteration as exc:
                    raise ValueError("partial corpus exceeds the current source index") from exc
                if speech != saved:
                    raise ValueError(f"partial corpus diverges at {saved.get('speech_id')}")
                records += 1
                words += speech["word_count"]
            # A validated prefix can now be extended in the existing file.
            print(f"Resuming Poland after {records:,} verified records", flush=True)
            with partial.open("a", encoding="utf-8", newline="\n") as stream:
                for speech in iterator:
                    record = speech.to_dict()
                    stream.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
                    records += 1
                    words += speech.word_count
                    if records % 10000 == 0:
                        print(f"Poland: {records:,} records", flush=True)
            os.replace(partial, target)

        resumed()
    else:

        def serialized():
            nonlocal records, words
            for speech in iter_sejm_speeches(start_year=start_year, end_year=end_year, terms=terms,
                                             raw_dir=raw_dir, manifest_path=manifest_path,
                                             workers=workers, through_date=cutoff):
                records += 1
                words += speech.word_count
                yield speech.to_dict()

        write_jsonl(output_path, serialized())
    coverage_path = Path(manifest_path).parent / "poland_coverage_audit.json"
    coverage_path.parent.mkdir(parents=True, exist_ok=True)
    coverage = audit_sejm_raw_coverage(raw_dir, through_date=cutoff)
    coverage_path.write_text(json.dumps(coverage, ensure_ascii=False, indent=2) + "\n",
                             encoding="utf-8")
    gap_path = coverage_path.parent / "poland_unavailable_statements.json"
    gap_path.write_text(json.dumps(coverage["missing"], ensure_ascii=False, indent=2) + "\n",
                        encoding="utf-8")
    return {"records": records, "words": words, "through_date": cutoff,
            "coverage_audit": str(coverage_path)}


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
    parser.add_argument("--resume-partial", action="store_true",
                        help="validate and append to an existing .jsonl.tmp corpus")
    parser.add_argument("--through-date", type=str,
                        help="latest sitting date to include (ISO); defaults to today's date")
    args = parser.parse_args(argv)
    if args.workers < 1:
        parser.error("--workers must be positive")
    stats = build_sejm_corpus(args.output, start_year=args.start_year, end_year=args.end_year,
                              raw_dir=args.raw_dir, manifest_path=args.manifest,
                              workers=args.workers, resume_partial=args.resume_partial,
                              through_date=args.through_date)
    print(json.dumps({"country": "Poland", "output": str(args.output), **stats}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
