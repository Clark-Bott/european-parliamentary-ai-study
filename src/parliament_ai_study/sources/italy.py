"""Camera dei deputati stenographic HTML acquisition and parsing."""
from __future__ import annotations

from datetime import date
from html.parser import HTMLParser
from pathlib import Path
import re
from urllib.parse import parse_qs, urljoin, urlparse
from typing import Any

from ..models import Speech
from .download import download_file

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
