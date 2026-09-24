"""Tweede Kamer OData acquisition and VLOS XML intervention parsing."""
from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path
from typing import Any, Iterator
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
import xml.etree.ElementTree as ET

from ..io import write_jsonl
from ..models import Speech
from .download import download_file, fetch_bytes

ODATA = "https://gegevensmagazijn.tweedekamer.nl/OData/v4/2.0"


def _name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _child_text(element: ET.Element, local: str) -> str:
    child = next((c for c in list(element) if _name(c.tag) == local), None)
    return "" if child is None else " ".join("".join(child.itertext()).split())


def _speaker_header(item: str, speaker: ET.Element) -> bool:
    if not item.rstrip().endswith(":"):
        return False
    candidates = (_child_text(speaker, "verslagnaam"), _child_text(speaker, "weergavenaam"),
                  _child_text(speaker, "achternaam"), _child_text(speaker, "voornaam"))
    lowered = item.casefold()
    return any(candidate and candidate.casefold() in lowered for candidate in candidates)


def parse_tweede_kamer_xml(xml_data: str | bytes | ET.Element, *, source_url: str,
                           record_status: str = "") -> list[Speech]:
    """Parse attributed speaker turns from one official VLOS `Verslag` XML document."""
    root = xml_data if isinstance(xml_data, ET.Element) else ET.fromstring(xml_data)
    meeting = next((e for e in root.iter() if _name(e.tag) == "vergadering"), None)
    if meeting is None:
        raise ValueError("VLOS document has no vergadering element")
    raw_date = _child_text(meeting, "datum")
    date_value = datetime.fromisoformat(raw_date[:10]).date().isoformat()
    session_id = meeting.attrib.get("objectid", "")
    term = _child_text(meeting, "vergaderjaar")
    document_id = root.attrib.get("MessageID", "")
    output: list[Speech] = []
    for turn in root.iter():
        if _name(turn.tag) != "woordvoerder":
            continue
        speaker = next((child for child in list(turn) if _name(child.tag) == "spreker"), None)
        text = next((child for child in list(turn) if _name(child.tag) == "tekst"), None)
        if speaker is None or text is None:
            continue
        items = [" ".join("".join(item.itertext()).split()) for item in text.iter()
                 if _name(item.tag) == "alineaitem"]
        items = [item for item in items if item]
        raw_text = " ".join(items)
        cleaned_items = list(items)
        if cleaned_items and _speaker_header(cleaned_items[0], speaker):
            cleaned_items.pop(0)
        speech_text = " ".join(cleaned_items).strip()
        if not speech_text:
            continue
        first, last = _child_text(speaker, "voornaam"), _child_text(speaker, "achternaam")
        speaker_name = " ".join(part for part in (first, last) if part).strip()
        if not speaker_name:
            speaker_name = _child_text(speaker, "weergavenaam") or _child_text(speaker, "verslagnaam")
        if not speaker_name:
            continue
        turn_id = turn.attrib.get("objectid", "")
        speech_id = f"{session_id}:{turn_id or document_id}"
        role = _child_text(speaker, "functie") or speaker.attrib.get("soort", "")
        output.append(Speech(
            country="Netherlands", parliament="Tweede Kamer", chamber="Tweede Kamer",
            date=date_value, session_id=session_id or document_id, speech_id=speech_id,
            speaker_id=speaker.attrib.get("objectid", ""), speaker_name=speaker_name,
            party=_child_text(speaker, "fractie"), speaker_role=role, legislative_term=term,
            speech_text=speech_text, raw_text=raw_text, source_url=source_url,
            source_identifier=speech_id, source_type="official_vlos_xml", text_language="nl",
            record_status=record_status,
            cleaning_notes="Removed the source XML speaker-label prefix from speech_text; raw_text retains it."
            if raw_text != speech_text else ""))
    return output


def _odata_pages(url: str) -> Iterator[dict[str, Any]]:
    """OData server may omit nextLink even when $top truncated the result."""
    next_url: str | None = url
    seen_urls = set()
    while next_url:
        if next_url in seen_urls or len(seen_urls) > 10000:
            raise ValueError("repeated or excessive OData pagination URL")
        seen_urls.add(next_url)
        body, _ = fetch_bytes(next_url)
        page = json.loads(body)
        values = page.get("value")
        if not isinstance(values, list):
            raise ValueError("OData response has no value array")
        yield from values
        explicit = page.get("@odata.nextLink")
        if explicit:
            next_url = explicit
            continue
        parts = urlsplit(next_url)
        params = dict(parse_qsl(parts.query))
        limit = int(params.get("$top", "250"))
        if len(values) < limit:
            return
        params["$skip"] = str(int(params.get("$skip", "0")) + len(values))
        next_url = urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(params), ""))


def _corrected_final_report(meeting_id: str) -> dict[str, Any] | None:
    expression = (f"Vergadering_Id eq {meeting_id} and Verwijderd eq false and "
                  "Soort eq 'Eindpublicatie'")
    url = ODATA + "/Verslag?" + urlencode({"$filter": expression, "$orderby": "GewijzigdOp desc", "$top": "20"})
    versions = list(_odata_pages(url))
    if not versions:
        return None
    versions.sort(key=lambda row: (row.get("Status") in ("Gecorrigeerd", "Gerectificeerd"),
                                   row.get("GewijzigdOp", "")), reverse=True)
    return versions[0]


def _download_report(report_id: str, raw_dir: str | Path,
                     manifest_path: str | Path) -> tuple[Path, str]:
    url = f"{ODATA}/Verslag({report_id})/resource"
    path = Path(raw_dir) / "netherlands" / "verslag" / f"{report_id}.xml"
    if not path.is_file():
        download_file(url, path, manifest_path=manifest_path)
    return path, url


def iter_tweede_kamer_speeches(*, start_year: int = 2018, end_year: int = 2026,
                               raw_dir: str | Path = "data/raw",
                               manifest_path: str | Path = "data/manifests/source_manifest.jsonl") -> Iterator[Speech]:
    """Iterate plenary turns with a corrected final report when available."""
    meeting_filter = (
        "Verwijderd eq false and Soort eq 'Plenair' and Kamer eq 'Tweede Kamer' and "
        f"Datum ge {start_year - 1}-12-31T00:00:00Z and Datum lt {end_year + 1}-01-02T00:00:00Z"
    )
    # The server rejects $top > 250. OData dates carry a +01:00/+02:00
    # offset, so use a padded range and filter parsed local dates below.
    meeting_url = ODATA + "/Vergadering?" + urlencode({"$filter": meeting_filter,
                                                        "$orderby": "Datum asc,Id asc", "$top": "250"})
    for meeting in _odata_pages(meeting_url):
        if not start_year <= int(str(meeting["Datum"])[:4]) <= end_year:
            continue
        meeting_id = str(meeting["Id"])
        report = _corrected_final_report(meeting_id)
        if report is None:
            continue
        report_path, source_url = _download_report(str(report["Id"]), raw_dir, manifest_path)
        try:
            yield from parse_tweede_kamer_xml(report_path.read_bytes(), source_url=source_url,
                                              record_status=str(report.get("Status", "")))
        except (ET.ParseError, ValueError) as exc:
            raise ValueError(f"cannot parse Tweede Kamer report {source_url}") from exc


def build_tweede_kamer_corpus(output_path: str | Path, *, start_year: int = 2018,
                              end_year: int = 2026, raw_dir: str | Path = "data/raw",
                              manifest_path: str | Path = "data/manifests/source_manifest.jsonl") -> dict[str, int]:
    records = words = 0

    def serialized():
        nonlocal records, words
        for speech in iter_tweede_kamer_speeches(start_year=start_year, end_year=end_year,
                                                 raw_dir=raw_dir, manifest_path=manifest_path):
            records += 1
            words += speech.word_count
            yield speech.to_dict()

    write_jsonl(output_path, serialized())
    return {"records": records, "words": words}
