"""Official Assemblée nationale XML corpus acquisition and parsing."""
from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path
import re
from typing import Any, Iterator, Mapping
from zipfile import ZipFile
import xml.etree.ElementTree as ET

from ..io import write_jsonl
from ..models import Speech
from .download import download_file, file_manifest_entry

ARCHIVE_URLS = {
    15: "https://data.assemblee-nationale.fr/static/openData/repository/15/vp/syceronbrut/syseron.xml.zip",
    16: "https://data.assemblee-nationale.fr/static/openData/repository/16/vp/syceronbrut/syseron.xml.zip",
    17: "https://data.assemblee-nationale.fr/static/openData/repository/17/vp/syceronbrut/syseron.xml.zip",
}
_STAGE = re.compile(r"\((?:[^()]*(?:applaudissements?|exclamations?|rires?|brouhaha|mêmes mouvements|mêmes protestations|mêmes applaudissements)[^()]*)\)", re.I)
_PARTY = re.compile(r"\s+\(([^()]*)\)\s*$")


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _first_text(element: ET.Element, path: str) -> str:
    found = element.find(f".//{{*}}{path}")
    return "" if found is None else "".join(found.itertext()).strip()


def parse_france_xml(xml_data: str | bytes | ET.Element, *, source_url: str) -> list[Speech]:
    """Parse one official Syceron plenary record; retain raw markup text per speech."""
    root = xml_data if isinstance(xml_data, ET.Element) else ET.fromstring(xml_data)
    uid = _first_text(root, "uid")
    session_id = _first_text(root, "seanceRef") or uid
    raw_date = _first_text(root, "dateSeance")
    date_value = datetime.strptime(raw_date[:8], "%Y%m%d").date().isoformat()
    term = _first_text(root, "legislature")
    outputs: list[Speech] = []
    index = 0
    for block in root.iter():
        if _local_name(block.tag) != "paragraphe":
            continue
        orateurs_node = next((child for child in block if _local_name(child.tag) == "orateurs"), None)
        if orateurs_node is None:
            continue
        speaker = next((child for child in orateurs_node if _local_name(child.tag) == "orateur"), None)
        text_element = next((child for child in block if _local_name(child.tag) == "texte"), None)
        if speaker is None or text_element is None:
            continue
        index += 1
        full_name = _first_text(speaker, "nom")
        speaker_id = _first_text(speaker, "id")
        role = _first_text(speaker, "qualite")
        party_match = _PARTY.search(full_name)
        party = party_match.group(1).strip() if party_match else ""
        speaker_name = _PARTY.sub("", full_name).strip()
        raw_text = " ".join("".join(text_element.itertext()).split())
        cleaned = _STAGE.sub(" ", raw_text)
        cleaned = " ".join(cleaned.split())
        if not speaker_name or not cleaned:
            continue
        record_id = block.attrib.get("id_syceron") or str(index)
        speech_id = f"{uid}:{record_id}"
        outputs.append(Speech(
            country="France", parliament="Assemblée nationale", chamber="Assemblée nationale",
            date=date_value, session_id=session_id, speech_id=speech_id,
            speaker_id=speaker_id or "", speaker_name=speaker_name, party=party,
            speaker_role=role, legislative_term=term, speech_text=cleaned,
            raw_text=raw_text, source_url=source_url, source_identifier=speech_id,
            source_type="official_syceron_xml", text_language="fr",
            cleaning_notes="Removed selected parenthetical audience/noise annotations; raw_text retains source text."
            if cleaned != raw_text else ""))
    return outputs


def parse_france_archive(path: str | Path, *, start_year: int = 2018,
                         end_year: int = 2026, source_url: str | None = None) -> Iterator[Speech]:
    archive_path = Path(path)
    provenance = source_url or ARCHIVE_URLS.get(16, "")
    with ZipFile(archive_path) as archive:
        for name in archive.namelist():
            if not name.lower().endswith(".xml") or "/compterendu/" not in name.lower():
                continue
            try:
                root = ET.fromstring(archive.read(name))
                source_date = datetime.strptime(_first_text(root, "dateSeance")[:8], "%Y%m%d").date()
                if source_date.year < start_year or source_date.year > end_year:
                    continue
                parsed = parse_france_xml(root, source_url=provenance)
            except (ET.ParseError, ValueError):
                continue
            yield from parsed


def download_france_archives(*, terms: tuple[int, ...] = (15, 16, 17),
                             raw_dir: str | Path = "data/raw",
                             manifest_path: str | Path = "data/manifests/source_manifest.jsonl") -> dict[int, Path]:
    """Fetch official legislature archives; keep checksums and never store API secrets."""
    manifest = Path(manifest_path)
    manifest.parent.mkdir(parents=True, exist_ok=True)
    known_hashes = set()
    if manifest.exists():
        for line in manifest.read_text(encoding="utf-8").splitlines():
            try:
                known_hashes.add(json.loads(line).get("sha256"))
            except json.JSONDecodeError:
                continue
    output: dict[int, Path] = {}
    for term in terms:
        if term not in ARCHIVE_URLS:
            raise ValueError(f"unsupported Assemblée nationale legislature: {term}")
        url = ARCHIVE_URLS[term]
        target = Path(raw_dir) / "france" / f"legislature-{term}-syceron.zip"
        if target.is_file():
            entry = file_manifest_entry(target, url, content_type="application/zip")
            if entry["sha256"] not in known_hashes:
                with manifest.open("a", encoding="utf-8") as stream:
                    stream.write(json.dumps(entry, ensure_ascii=False, sort_keys=True) + "\n")
                known_hashes.add(entry["sha256"])
        else:
            entry = download_file(url, target, manifest_path=manifest)
            known_hashes.add(entry["sha256"])
        output[term] = target
    return output


def build_france_corpus(archives: Mapping[int, str | Path], output_path: str | Path, *,
                        start_year: int = 2018, end_year: int = 2026) -> dict[str, Any]:
    """Stream downloaded official XML interventions into common JSONL schema."""
    stats: dict[str, Any] = {"speeches": 0, "words": 0, "years": {}, "legs": {}}

    def records():
        years: dict[str, int] = {}
        terms: dict[str, int] = {}
        for term, path in sorted(archives.items()):
            for speech in parse_france_archive(path, start_year=start_year, end_year=end_year,
                                               source_url=ARCHIVE_URLS[term]):
                stats["speeches"] = int(stats["speeches"]) + 1
                stats["words"] = int(stats["words"]) + speech.word_count
                year = speech.date[:4]
                years[year] = years.get(year, 0) + 1
                terms[str(term)] = terms.get(str(term), 0) + 1
                yield speech.to_dict()
        stats["years"] = dict(sorted(years.items()))
        stats["legs"] = dict(sorted(terms.items()))

    write_jsonl(output_path, records())
    return stats
