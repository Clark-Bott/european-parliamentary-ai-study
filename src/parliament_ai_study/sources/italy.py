"""Camera dei deputati stenographic HTML acquisition and parsing."""
from __future__ import annotations

from datetime import date
from html.parser import HTMLParser
from pathlib import Path
import re
from urllib.parse import parse_qs, urljoin, urlparse
from typing import Any
import xml.etree.ElementTree as ET

from ..io import write_jsonl
from ..models import Speech
from .download import download_file, fetch_bytes

_BASE = "https://www.camera.it"
_MONTHS = {"gennaio": 1, "febbraio": 2, "marzo": 3, "aprile": 4, "maggio": 5,
           "giugno": 6, "luglio": 7, "agosto": 8, "settembre": 9, "ottobre": 10,
           "novembre": 11, "dicembre": 12}
_DATE = re.compile(r"\bdi\s+\w+\s+(\d{1,2})\s+([a-zà]+)\s+(\d{4})\b", re.I)
_PARTY = re.compile(r"\s*\(([^()]*)\)\s*$")


class _CameraHtml(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.paragraphs: list[dict[str, Any]] = []
        self._active: dict[str, Any] | None = None
        self._anchor: dict[str, Any] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if tag.lower() == "p":
            self._active = {"class": values.get("class", ""), "id": values.get("id", ""), "text": [], "anchors": []}
        elif tag.lower() == "a" and self._active is not None:
            self._anchor = {"href": values.get("href", ""), "title": values.get("title", ""), "text": []}

    def handle_data(self, data: str) -> None:
        if self._active is not None:
            self._active["text"].append(data)
        if self._anchor is not None:
            self._anchor["text"].append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "a" and self._anchor is not None:
            if self._active is not None:
                self._active["anchors"].append(self._anchor)
            self._anchor = None
        elif tag.lower() == "p" and self._active is not None:
            self._active["text"] = " ".join("".join(self._active["text"]).split())
            self.paragraphs.append(self._active)
            self._active = None


def _date_from_page(paragraphs: list[dict[str, Any]]) -> str:
    for paragraph in paragraphs:
        match = _DATE.search(paragraph["text"])
        if not match:
            continue
        day, month_name, year = match.groups()
        month = _MONTHS.get(month_name.casefold())
        if month is None:
            raise ValueError(f"unrecognized Italian month: {month_name}")
        return date(int(year), month, int(day)).isoformat()
    raise ValueError("official Camera page has no parseable sitting date")


def parse_camera_html(html_data: str | bytes, *, legislature: int, sitting_id: str,
                      source_url: str) -> list[Speech]:
    if isinstance(html_data, bytes):
        html_data = html_data.decode("utf-8", errors="replace")
    parser = _CameraHtml()
    parser.feed(html_data)
    date_value = _date_from_page(parser.paragraphs)
    output = []
    session_id = f"camera-leg{legislature}-sed{sitting_id}"
    for paragraph in parser.paragraphs:
        if "intervento" not in paragraph["class"].split():
            continue
        text = paragraph["text"]
        if not text:
            continue
        anchor = paragraph["anchors"][0] if paragraph["anchors"] else {}
        label = " ".join("".join(anchor.get("text", [])).split())
        title = str(anchor.get("title", ""))
        name_match = re.search(r"scheda personale:\s*(.+)$", title, re.I)
        speaker_name = name_match.group(1).strip() if name_match else label
        party_match = _PARTY.search(label)
        party = party_match.group(1) if party_match else ""
        if not speaker_name:
            continue
        speaker_id = parse_qs(urlparse(urljoin(source_url, str(anchor.get("href", "")))).query).get("idPersona", [""])[0]
        role = "presiding_officer" if label.casefold().startswith("presidente") else "floor_speaker"
        clean = text
        if label and clean.casefold().startswith(label.casefold()):
            clean = clean[len(label):].lstrip(" .:–-\t")
        if not clean:
            continue
        element_id = paragraph["id"] or f"intervento-{len(output) + 1}"
        speech_id = f"{session_id}:{element_id}"
        output.append(Speech(
            country="Italy", parliament="Camera dei deputati", chamber="Camera dei deputati",
            date=date_value, session_id=session_id, speech_id=speech_id,
            speaker_id=speaker_id, speaker_name=speaker_name, party=party,
            speaker_role=role, legislative_term=str(legislature), speech_text=clean,
            raw_text=text, source_url=source_url, source_identifier=speech_id,
            source_type="official_camera_stenographic_html", text_language="it",
            cleaning_notes="Removed linked speaker-label prefix from speech_text; raw_text retains it."
            if clean != text else ""))
    return output


def download_camera_sitting(legislature: int, sitting_id: str, *,
                            raw_dir: str | Path = "data/raw",
                            manifest_path: str | Path = "data/manifests/source_manifest.jsonl") -> tuple[Path, str]:
    source_url = f"{_BASE}/leg{legislature}/410?idSeduta={sitting_id}&tipo=stenografico"
    target = Path(raw_dir) / "italy" / f"leg{legislature}" / f"sitting-{sitting_id}.html"
    if not target.is_file():
        download_file(source_url, target, manifest_path=manifest_path)
    return target, source_url


def parse_camera_file(path: str | Path, *, legislature: int, sitting_id: str,
                       source_url: str) -> list[Speech]:
    return parse_camera_html(Path(path).read_bytes(), legislature=legislature,
                             sitting_id=sitting_id, source_url=source_url)


def camera_xml_url(legislature: int, sitting_id: int) -> str:
    return ("https://documenti.camera.it/apps/commonServices/getDocumento.ashx?"
            f"sezione=assemblea&tipoDoc=formato_xml&tipologia=stenografico&"
            f"idNumero={sitting_id:04d}&idLegislatura={legislature}")


def parse_camera_xml(data: bytes | str, *, source_url: str) -> list[Speech]:
    """Use the complete official XML intervention, including virtual continuation nodes."""
    root = ET.fromstring(data)
    if root.tag != "seduta" or root.attrib.get("ramo") != "camera":
        raise ValueError("not a Camera dei deputati plenary XML sitting")
    term, sitting = root.attrib["legislatura"], root.attrib["numero"]
    date_value = date(int(root.attrib["anno"]), int(root.attrib["mese"]), int(root.attrib["giorno"])).isoformat()
    session = f"camera-leg{term}-sed{sitting:0>4}"
    output: list[Speech] = []
    for turn in root.findall(".//resoconto//intervento"):
        node = turn.find("testoXHTML")
        name = node.find("nominativo") if node is not None else None
        if name is None:
            continue
        label = " ".join("".join(name.itertext()).split())
        speaker_name = name.attrib.get("cognomeNome", "").strip() or label
        raw = " ".join(" ".join("".join(part.itertext()).split()) for part in turn
                       if part.tag in ("testoXHTML", "interventoVirtuale"))
        # The XML nominativo is the speaker label, not spoken content. Preserve
        # the tail after that label and all virtual continuation paragraphs.
        first = "".join((name.tail or "", *("".join(child.itertext()) + (child.tail or "")
                                                for child in list(node) if child is not name)))
        if not list(node) or list(node)[0] is not name:
            raise ValueError(f"unexpected nominativo layout in {source_url}: {turn.attrib.get('id')}")
        first = first.lstrip(" .,:;–-\t\n")
        rest = ["".join(part.itertext()) for part in turn.findall("interventoVirtuale")]
        clean = " ".join(" ".join(part.split()) for part in [first, *rest] if part.strip()).strip()
        # Parenthesized audience reactions are marked as italic in the official XML.
        clean = re.sub(r"\s*\((?:Applausi|Commenti|Proteste|Risate)[^()]*\)", " ", clean, flags=re.I)
        clean = " ".join(clean.split())
        if not speaker_name or not clean:
            continue
        element_id = turn.attrib["id"]
        party_match = re.match(r"^\s*\(([^()]+)\)", first)
        if party_match:
            clean = clean[len(party_match.group(0)):].lstrip(" .,:;–-")
        if not clean:
            continue
        output.append(Speech(country="Italy", parliament="Camera dei deputati", chamber="Camera dei deputati",
                             date=date_value, session_id=session, speech_id=f"{session}:{element_id}",
                             speaker_id=name.attrib.get("id", ""), speaker_name=speaker_name,
                             party=party_match.group(1) if party_match else "",
                             speaker_role="presiding_officer" if label.casefold().startswith("presidente") else "floor_speaker",
                             legislative_term=term, speech_text=clean, raw_text=raw,
                             source_url=source_url + "#" + element_id, source_identifier=element_id,
                             source_type="official_camera_stenographic_xml", text_language="it",
                             cleaning_notes="XML nominativo label and selected audience reactions removed; virtual continuation included."))
    return output


def _last_sitting(term: int) -> int:
    """Get the highest numbered sitting from the official term index."""
    body, _ = fetch_bytes(f"https://www.camera.it/leg{term}/207")
    numbers = [int(value) for value in re.findall(rb"idSeduta=(\d+)", body)]
    if not numbers:
        raise ValueError(f"no sittings on Camera term {term} official index")
    return max(numbers)


def build_camera_corpus(output_path: str | Path, *, start_year: int = 2018, end_year: int = 2026,
                        raw_dir: str | Path = "data/raw",
                        manifest_path: str | Path = "data/manifests/source_manifest.jsonl") -> dict[str, int]:
    counts = {"records": 0, "words": 0, "sittings": 0}

    def get_sitting(term: int, sitting: int) -> tuple[ET.Element, str]:
        url = camera_xml_url(term, sitting)
        path = Path(raw_dir) / "italy" / f"leg{term}" / f"sitting-{sitting:04d}.xml"
        if not path.exists():
            download_file(url, path, manifest_path=manifest_path)
        return ET.fromstring(path.read_bytes()), url

    def rows():
        for term in (17, 18, 19):
            last = _last_sitting(term)
            # Electoral term 17 begins in 2013. Locate the first requested
            # year by sitting number rather than downloading five extra years.
            low, high = 1, last + 1
            if term == 17:
                while low < high:
                    mid = (low + high) // 2
                    root, _ = get_sitting(term, mid)
                    if int(root.attrib["anno"]) < start_year:
                        low = mid + 1
                    else:
                        high = mid
            for sitting in range(low, last + 1):
                root, url = get_sitting(term, sitting)
                year = int(root.attrib["anno"])
                if not start_year <= year <= end_year:
                    continue
                speeches = parse_camera_xml(ET.tostring(root), source_url=url)
                counts["sittings"] += 1
                for speech in speeches:
                    counts["records"] += 1
                    counts["words"] += speech.word_count
                    yield speech.to_dict()

    write_jsonl(output_path, rows())
    return counts
