"""Bundestag official Open Data XML (19th through 21st electoral terms)."""
from __future__ import annotations

from collections.abc import Iterator
import csv
from datetime import datetime
import hashlib
from html.parser import HTMLParser
import io
from pathlib import Path
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET
from zipfile import ZipFile

from ..io import write_jsonl
from ..models import Speech
from .download import download_file, fetch_bytes

BASE = "https://www.bundestag.de"
# IDs are the XML-only document lists on the Bundestag's Open Data page.
LIST_IDS = {19: "543410-543410", 20: "866354-866354", 21: "1058442-1058442"}
CPP_BT_ARCHIVE = "CPP-BT_2026-01-17_DE_CSV_Reden_Gesamt.zip"
CPP_BT_URL = ("https://zenodo.org/api/records/18177196/files/"
              "CPP-BT_2026-01-17_DE_CSV_Reden_Gesamt.zip/content")
CPP_BT_MEMBER = "CPP-BT_2026-01-17_DE_CSV_Reden_Gesamt.csv"
CPP_BT_MD5 = "9b03325c65c6930bc5e44d4206ce3d42"
CPP_BT_DOI = "10.5281/zenodo.18177196"
CPP_BT_CUTOFF = "2026-01-17"
LIST_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Referer": f"{BASE}/services/opendata",
}


def _fetch_list_page(url: str) -> bytes:
    """Use the open-data page's normal referer and HTML request contract."""
    request = Request(url, headers=LIST_HEADERS, method="GET")
    with urlopen(request, timeout=60) as response:
        return response.read()


class _Links(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            href = dict(attrs).get("href", "")
            if urlparse(href).path.lower().endswith(".xml"):
                self.links.append(urljoin(BASE, href))


def list_protocols(term: int) -> list[str]:
    """Page the Bundestag's official XML-only list; reject repeated pages."""
    if term not in LIST_IDS:
        raise ValueError(f"unsupported Bundestag electoral term: {term}")
    found: dict[str, str] = {}
    for offset in range(0, 10000, 10):
        url = (f"{BASE}/ajax/filterlist/de/services/opendata/{LIST_IDS[term]}"
               f"?noFilterSet=true&limit=10&offset={offset}")
        page = _fetch_list_page(url)
        parser = _Links()
        parser.feed(page.decode("utf-8"))
        if not parser.links:
            return list(found.values())
        for link in parser.links:
            name = Path(urlparse(link).path).name
            if name in found and found[name] != link:
                raise ValueError(f"conflicting protocol URL for {name}")
            found[name] = link
        if len(parser.links) < 10:
            return list(found.values())
    raise ValueError(f"protocol list for term {term} exceeded pagination limit")


def _none_or_value(value: object) -> str:
    return "" if value in (None, "NA", "") else str(value)


def _ensure_cpp_bt_archive(raw_dir: str | Path, manifest_path: str | Path) -> Path:
    """Download and verify the versioned CC0 CPP-BT speech archive when absent."""
    archive = Path(raw_dir) / "germany" / "cpp-bt" / CPP_BT_ARCHIVE
    if not archive.is_file():
        download_file(CPP_BT_URL, archive, manifest_path=manifest_path, retries=3)
    digest = hashlib.md5()
    with archive.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    if digest.hexdigest() != CPP_BT_MD5:
        raise ValueError(f"CPP-BT archive MD5 mismatch: {archive}")
    return archive


def iter_cpp_bt_speeches(archive: str | Path, *, start_year: int = 2018,
                         end_year: int = 2026) -> Iterator[Speech]:
    """Normalize the verified CC0 CPP-BT speech-level CSV archive."""
    with ZipFile(archive) as bundle:
        names = bundle.namelist()
        member = CPP_BT_MEMBER if CPP_BT_MEMBER in names else next(
            name for name in names if name.endswith(".csv"))
        with bundle.open(member) as raw:
            for row in csv.DictReader(io.TextIOWrapper(raw, encoding="utf-8", newline="")):
                try:
                    year = int(row["sitzung_jahr"])
                    term = int(row["wahlperiode"])
                    sitting = int(row["sitzung_nr"])
                except (KeyError, TypeError, ValueError) as exc:
                    raise ValueError(f"invalid CPP-BT speech metadata in {member}") from exc
                if not start_year <= year <= end_year:
                    continue
                text = _none_or_value(row.get("rede_text")).strip()
                speech_id = _none_or_value(row.get("rede_id"))
                if not text or not speech_id:
                    continue
                title = _none_or_value(row.get("redner_titel"))
                first = _none_or_value(row.get("redner_vorname"))
                last = _none_or_value(row.get("redner_nachname"))
                suffix = _none_or_value(row.get("redner_namenszusatz"))
                place = _none_or_value(row.get("redner_ortszusatz"))
                name = " ".join(part for part in (title, first, last, suffix, place) if part)
                day = datetime.strptime(row["sitzung_datum"], "%Y-%m-%d").date().isoformat()
                source_url = f"https://doi.org/{CPP_BT_DOI}#{speech_id}"
                yield Speech(
                    country="Germany", parliament="Bundestag", chamber="Bundestag",
                    date=day, session_id=f"bundestag-{term}-{sitting}",
                    speech_id=speech_id,
                    speaker_id=_none_or_value(row.get("redner_id")),
                    speaker_name=name or "Unknown speaker",
                    party=_none_or_value(row.get("redner_fraktion")),
                    speaker_role=(_none_or_value(row.get("redner_rolle_lang"))
                                 or _none_or_value(row.get("redner_rolle_kurz"))),
                    legislative_term=str(term), speech_text=text, raw_text=text,
                    source_url=source_url, source_identifier=speech_id,
                    source_type="cpp_bt_cc0_speech_csv", text_language="de",
                    cleaning_notes=("CPP-BT already removes official speaker headers and audience comments; "
                                    f"raw_text and speech_text preserve its cleaned text. DOI {CPP_BT_DOI}."))


def _text_without_annotations(node: ET.Element) -> str:
    parts = [node.text or ""]
    for child in node:
        if child.tag not in {"kommentar", "redner"}:
            parts.append(_text_without_annotations(child))
        parts.append(child.tail or "")
    return "".join(parts)


def parse_bundestag_xml(data: bytes | str, *, source_url: str) -> list[Speech]:
    root = ET.fromstring(data)
    if root.tag != "dbtplenarprotokoll":
        raise ValueError("not a Bundestag plenary protocol XML document")
    term, sitting = root.attrib["wahlperiode"], root.attrib["sitzung-nr"]
    date_value = datetime.strptime(root.attrib["sitzung-datum"], "%d.%m.%Y").date().isoformat()
    session = f"bundestag-{term}-{sitting}"
    output: list[Speech] = []
    for rede in root.iter("rede"):
        header = next((p for p in rede.findall("p") if p.attrib.get("klasse") == "redner"), None)
        speaker = header.find("redner") if header is not None else None
        name = speaker.find("name") if speaker is not None else None
        if name is None:
            continue
        full_name = " ".join(filter(None, (name.findtext("titel", ""), name.findtext("vorname", ""),
                                           name.findtext("namenszusatz", ""), name.findtext("nachname", ""))))
        raw = " ".join(" ".join("".join(child.itertext()).split()) for child in rede
                       if child.tag in {"p", "kommentar"} and child is not header).strip()
        clean = " ".join(" ".join(_text_without_annotations(p).split()) for p in rede.findall("p")
                         if p is not header).strip()
        if not full_name or not clean:
            continue
        speech_id = f"{session}:{rede.attrib['id']}"
        output.append(Speech(country="Germany", parliament="Bundestag", chamber="Bundestag",
                             date=date_value, session_id=session, speech_id=speech_id,
                             speaker_id=speaker.attrib.get("id", ""), speaker_name=full_name,
                             party=name.findtext("fraktion", ""), speaker_role=name.findtext("rolle/rolle_lang", ""),
                             legislative_term=term, speech_text=clean, raw_text=raw,
                             source_url=source_url + "#" + rede.attrib["id"], source_identifier=rede.attrib["id"],
                             source_type="official_bundestag_xml", text_language="de",
                             cleaning_notes="Removed speaker header and XML commentary; raw_text retains annotations."))
    return output


def build_bundestag_corpus(output_path: str | Path, *, start_year: int = 2018, end_year: int = 2026,
                           raw_dir: str | Path = "data/raw",
                           manifest_path: str | Path = "data/manifests/source_manifest.jsonl") -> dict[str, int | str]:
    counts: dict[str, int | str] = {
        "records": 0, "words": 0, "protocols": 0, "cpp_bt_records": 0,
        "official_xml_records": 0, "official_xml_status": "not_requested",
        "official_xml_error": "", "cpp_bt_cutoff": CPP_BT_CUTOFF,
    }

    def rows():
        archive = _ensure_cpp_bt_archive(raw_dir, manifest_path)
        for speech in iter_cpp_bt_speeches(archive, start_year=start_year, end_year=end_year):
            counts["records"] += 1
            counts["words"] += speech.word_count
            counts["cpp_bt_records"] += 1
            yield speech.to_dict()
        # The CC0 baseline is required. Official XML is an optional supplement
        # for the period after the archive cutoff; resource verification must
        # not invalidate the verified historical baseline.
        try:
            for term in LIST_IDS:
                for url in list_protocols(term):
                    filename = Path(urlparse(url).path).name
                    path = Path(raw_dir) / "germany" / f"term-{term}" / filename
                    if not path.exists():
                        download_file(url, path, manifest_path=manifest_path)
                    root = ET.fromstring(path.read_bytes())
                    day = datetime.strptime(root.attrib["sitzung-datum"], "%d.%m.%Y").date().isoformat()
                    if not (CPP_BT_CUTOFF < day <= f"{end_year}-12-31"):
                        continue
                    speeches = parse_bundestag_xml(ET.tostring(root), source_url=url)
                    counts["protocols"] += 1
                    for speech in speeches:
                        counts["records"] += 1
                        counts["words"] += speech.word_count
                        counts["official_xml_records"] += 1
                        yield speech.to_dict()
            counts["official_xml_status"] = "complete"
        except Exception as exc:
            counts["official_xml_status"] = "unavailable"
            counts["official_xml_error"] = f"{type(exc).__name__}: {exc}"
            print(f"WARNING: CPP-BT baseline retained; official XML supplement unavailable: {exc}", flush=True)

    write_jsonl(output_path, rows())
    return counts
