"""Source-boundary validation: compare parsed records with the official source.

Two commands support the Phase 4 requirement that parsing be validated
against the official record rather than assumed correct:

``--packet``
    Deterministic per-year sample written as a Markdown review packet, so a
    human can compare each record against the official page.

``--verify``
    Automated containment check. For each sampled record the tool retrieves
    the record's own source (the official URL, or the local official archive
    for bulk-ZIP sources) and checks that the normalized ``speech_text``
    occurs in it. A record whose text is absent is reported as a mismatch for
    manual investigation. This checks boundaries and attribution material; it
    is not a substitute for a human reading a sample.

Every run writes a JSON report so coverage gaps stay visible.
"""
from __future__ import annotations

from datetime import date
from html.parser import HTMLParser
import argparse
import hashlib
import json
import re
import time
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from zipfile import ZipFile

from .io import iter_jsonl, write_jsonl

COUNTRIES = ("Germany", "France", "Netherlands", "Italy", "Spain", "Poland")
USER_AGENT = "european-parliamentary-ai-study-source-check/1.0"


class _TextExtractor(HTMLParser):
    """Collect visible text from HTML or XML, skipping script/style blocks."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self._skip = 0

    def handle_starttag(self, tag: str, attrs: Any) -> None:
        if tag in {"script", "style"}:
            self._skip += 1

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style"} and self._skip:
            self._skip -= 1

    def handle_data(self, data: str) -> None:
        if not self._skip:
            self.parts.append(data)


def visible_text(payload: bytes) -> str:
    parser = _TextExtractor()
    parser.feed(payload.decode("utf-8", "replace"))
    return " ".join(parser.parts)


def normalize(text: str) -> str:
    collapsed = re.sub(r"\s+", " ", text).strip().casefold()
    # Sources and inline markup put spaces before punctuation; records do not.
    return re.sub(r"\s+([.,;:!?)\]»”])", r"\1", collapsed)


def _loose(text: str) -> str:
    """Alphanumeric-only form, tolerant of °/o, hyphenation, and quotes."""
    return re.sub(r"[^0-9a-zà-öø-ÿ]+", "", normalize(text))


def containment_status(record_text: str, source_text: str) -> str:
    """verified, normalized, partial, or mismatch for one record/source pair.

    ``normalized`` means the text is present once punctuation spacing and
    decorative characters are ignored (for example ``n°`` against ``no``).
    """
    needle, haystack = normalize(record_text), normalize(source_text)
    if not needle:
        return "mismatch"
    if needle in haystack:
        return "verified"
    if _loose(needle) and _loose(needle) in _loose(haystack):
        return "normalized"
    head = needle[:160]
    if head and head in haystack:
        return "partial"
    # Sources sometimes decorate the opening (speaker labels, italics).
    tail = needle[-160:]
    if tail and tail in haystack:
        return "partial"
    # Cleaning legitimately removes inline material from the middle of a
    # record (audience cues such as "(rumores y protestas)", page markers).
    # If almost every substantial segment of the record is present, report
    # partial rather than mismatch; a genuine boundary error loses whole
    # segments.
    segments = [part.strip() for part in re.split(r"[.!?;:]\s+", needle)]
    segments = [part for part in segments if len(part) >= 25]
    if segments:
        found = sum(1 for part in segments if part in haystack)
        if found / len(segments) >= 0.9 and (len(segments) > 1 or len(segments[0]) >= 80):
            return "partial"
    return "mismatch"


def sample_records(corpus: Path, country: str, count: int, seed: int) -> list[dict[str, Any]]:
    """Deterministic sample, balanced across the years present for a country."""
    by_year: dict[int, list[dict[str, Any]]] = {}
    total = 0
    for record in iter_jsonl(corpus):
        if record.get("country") != country:
            continue
        total += 1
        try:
            year = date.fromisoformat(str(record.get("date", ""))).year
        except ValueError:
            continue
        bucket = by_year.setdefault(year, [])
        if len(bucket) < 64:
            bucket.append(record)
    if total == 0:
        return []
    years = sorted(by_year)
    quota = max(1, count // max(1, len(years)))
    picked: list[dict[str, Any]] = []
    for year in years:
        bucket = sorted(by_year[year], key=lambda row: str(row.get("speech_id", "")))
        # SHA-256 ordering keeps the sample repeatable across runs and machines.
        bucket.sort(key=lambda row: hashlib.sha256(
            f"{seed}|{row.get('speech_id', '')}".encode("utf-8")).hexdigest())
        picked.extend(bucket[:quota])
    if len(picked) < count:
        chosen_ids = {row.get("speech_id") for row in picked}
        remainder = sorted(
            (row for rows in by_year.values() for row in rows
             if row.get("speech_id") not in chosen_ids),
            key=lambda row: hashlib.sha256(
                f"{seed}|{row.get('speech_id', '')}".encode("utf-8")).hexdigest())
        picked.extend(remainder[:count - len(picked)])
    return picked[:count]


def _fetch(url: str, timeout: float) -> bytes:
    request = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(request, timeout=timeout) as response:  # noqa: S310 (official URLs)
        return response.read()


def _locate(pattern: str, root: Path = Path("data/raw")) -> Path | None:
    matches = sorted(root.rglob(pattern))
    return matches[0] if matches else None


def _source_payload(record: dict[str, Any], *, timeout: float,
                    source_archive: Path | None) -> tuple[str, str | None, str | None]:
    """Return (transport, payload, skip_reason) for one record."""
    source_type = str(record.get("source_type", ""))
    if source_type in {"official_camera_stenographic_xml", "official_vlos_xml",
                       "official_congreso_diario_html", "official_sejm_html",
                       "official_congreso_diario_pdf"}:
        try:
            return "http", _fetch(str(record["source_url"]), timeout).decode("utf-8", "replace"), None
        except (HTTPError, URLError, TimeoutError, OSError) as exc:
            return "http", None, f"fetch failed: {exc}"
    if source_type == "cpp_bt_cc0_speech_csv":
        archive = source_archive or _locate("CPP-BT_*_Reden_Gesamt.zip")
        if archive is None or not archive.is_file():
            return "local-archive", None, "CPP-BT archive not present locally"
        return "local-archive", str(archive), None
    if source_type == "official_syceron_xml":
        archives = sorted(Path("data/raw").rglob("legislature-*-syceron.zip"))
        if source_archive is not None:
            archives = [source_archive]
        if not archives:
            return "local-archive", None, "Syceron archive not present locally"
        return "local-archive", "|".join(str(path) for path in archives), None
    return "unsupported", None, f"no verifier for source_type {source_type!r}"


def _local_payload(record: dict[str, Any], archive: Path) -> str | None:
    """Read one record's text from a bulk official archive."""
    if archive.suffix == ".zip":
        with ZipFile(archive) as bundle:
            identifier = str(record.get("source_identifier", ""))
            # French Syceron IDs are "<session uid>:<record id>"; the uid names
            # the member file, the record id is an attribute inside it. The
            # record's session_id can differ (e.g. RUANR… question-hour IDs),
            # so the member name comes from the source identifier itself.
            if identifier and ":" in identifier:
                member = f"xml/compteRendu/{identifier.split(':', 1)[0]}.xml"
                if member in bundle.namelist():
                    return bundle.read(member).decode("utf-8", "replace")
            names = [name for name in bundle.namelist()
                     if name.lower().endswith((".xml", ".csv"))]
            for name in names:
                payload = bundle.read(name)
                if name.lower().endswith(".xml"):
                    text = payload.decode("utf-8", "replace")
                    if identifier and identifier in text:
                        return text
                    continue
                # CSV fallback: find the row that carries this speech ID.
                if identifier and identifier.encode("utf-8") in payload:
                    return payload.decode("utf-8", "replace")
        return None
    return archive.read_text(encoding="utf-8", errors="replace")


def verify(records: list[dict[str, Any]], *, timeout: float = 30.0,
           sleep: float = 0.5, source_archive: Path | None = None) -> list[dict[str, Any]]:
    results = []
    for record in records:
        transport, payload, skip_reason = _source_payload(
            record, timeout=timeout, source_archive=source_archive)
        status = "skipped"
        detail = skip_reason
        if payload is not None:
            if transport == "local-archive":
                candidates = [Path(item) for item in str(payload).split("|")]
                payload = None
                for candidate in candidates:
                    payload = _local_payload(record, candidate)
                    if payload is not None:
                        break
                if payload is None:
                    detail = "record not located in the local archive"
                else:
                    source_text = (visible_text(payload.encode("utf-8", "replace"))
                                   if "<" in payload[:2000] else payload)
                    status = containment_status(str(record.get("speech_text", "")), source_text)
                    detail = None
            else:
                # Official HTML/XML must be reduced to visible text first, or
                # inline tags break every containment check.
                source_text = visible_text(payload.encode("utf-8", "replace"))
                status = containment_status(str(record.get("speech_text", "")), source_text)
                detail = None
                time.sleep(sleep)
        results.append({
            "country": record.get("country"),
            "date": record.get("date"),
            "speech_id": record.get("speech_id"),
            "speaker_name": record.get("speaker_name"),
            "source_url": record.get("source_url"),
            "transport": transport,
            "status": status,
            "detail": detail,
        })
    return results


def write_packet(records: list[dict[str, Any]], path: Path, *, country: str) -> None:
    lines = [f"# Source-boundary review packet: {country}", "",
             "Compare each record with its official source. Check speaker, date,",
             "text boundaries, and that no procedural text became a speech.",
             "Mark each record verified, corrected, or rejected.", ""]
    for index, record in enumerate(records, 1):
        text = str(record.get("speech_text", ""))
        lines += [
            f"## {index}. {record.get('speech_id')}",
            "",
            f"- date: {record.get('date')}",
            f"- speaker: {record.get('speaker_name')} ({record.get('party') or 'no party'})",
            f"- role: {record.get('speaker_role') or '(empty)'}",
            f"- words: {record.get('word_count')}",
            f"- source: {record.get('source_url')}",
            "",
            text[:1500] + ("…" if len(text) > 1500 else ""),
            "",
            "- [ ] verified  - [ ] corrected  - [ ] rejected",
            "",
        ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--corpus", type=Path, required=True)
    parser.add_argument("--country", required=True, choices=COUNTRIES)
    parser.add_argument("--count", type=int, default=10)
    parser.add_argument("--seed", type=int, default=2026)
    parser.add_argument("--packet", type=Path, help="write a Markdown review packet")
    parser.add_argument("--verify", action="store_true",
                        help="check sampled records against their official source")
    parser.add_argument("--report", type=Path, help="write the JSON verification report")
    parser.add_argument("--output", type=Path, help="write the sampled records as JSONL")
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--sleep", type=float, default=0.5)
    parser.add_argument("--source-archive", type=Path,
                        help="explicit bulk archive for Germany/France checks")
    args = parser.parse_args(argv)
    if not args.packet and not args.verify and not args.output:
        parser.error("choose --packet, --verify, or --output")
    records = sample_records(args.corpus, args.country, args.count, args.seed)
    if not records:
        print(json.dumps({"country": args.country, "records": 0}))
        return 1
    if args.output:
        write_jsonl(args.output, records)
    if args.packet:
        write_packet(records, args.packet, country=args.country)
    summary: dict[str, Any] = {"country": args.country, "sampled": len(records),
                               "seed": args.seed, "corpus": str(args.corpus)}
    if args.verify:
        results = verify(records, timeout=args.timeout, sleep=args.sleep,
                         source_archive=args.source_archive)
        counts: dict[str, int] = {}
        for row in results:
            counts[row["status"]] = counts.get(row["status"], 0) + 1
        summary["status_counts"] = counts
        summary["results"] = results
        if args.report:
            args.report.parent.mkdir(parents=True, exist_ok=True)
            args.report.write_text(
                json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary if not args.verify else
                     {key: value for key, value in summary.items() if key != "results"},
                     ensure_ascii=False, indent=2))
    if args.verify and summary.get("status_counts", {}).get("mismatch"):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
