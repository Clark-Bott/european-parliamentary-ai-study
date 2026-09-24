"""Bundestag official Open Data XML (19th through 21st electoral terms)."""
from __future__ import annotations

from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlparse
import xml.etree.ElementTree as ET

from ..io import write_jsonl
from ..models import Speech
from .download import download_file, fetch_bytes

BASE = "https://www.bundestag.de"
# IDs are the XML-only document lists on the Bundestag's Open Data page.
LIST_IDS = {19: "543410-543410", 20: "866354-866354", 21: "1058442-1058442"}


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
        url = f"{BASE}/ajax/filterlist/de/services/opendata/{LIST_IDS[term]}?noFilterSet=true&offset={offset}"
        page, _ = fetch_bytes(url)
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
                           manifest_path: str | Path = "data/manifests/source_manifest.jsonl") -> dict[str, int]:
    counts = {"records": 0, "words": 0, "protocols": 0}

    def rows():
        for term in LIST_IDS:
            for url in list_protocols(term):
                filename = Path(urlparse(url).path).name
                path = Path(raw_dir) / "germany" / f"term-{term}" / filename
                if not path.exists():
                    download_file(url, path, manifest_path=manifest_path)
                # The file date, not the listing order or current term, determines inclusion.
                root = ET.fromstring(path.read_bytes())
                year = datetime.strptime(root.attrib["sitzung-datum"], "%d.%m.%Y").year
                if not start_year <= year <= end_year:
                    continue
                speeches = parse_bundestag_xml(ET.tostring(root), source_url=url)
                counts["protocols"] += 1
                for speech in speeches:
                    counts["records"] += 1
                    counts["words"] += speech.word_count
                    yield speech.to_dict()

    write_jsonl(output_path, rows())
    return counts
