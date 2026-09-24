"""Reconcile cached raw-source files with the append-only provenance manifest."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
from typing import Any
from urllib.parse import urlparse

from .sources.download import file_manifest_entry
from .sources.italy import camera_xml_url
from .sources.netherlands import ODATA
from .sources.sejm import API as SEJM_API
from .sources.spain import journal_url, pdf_journal_url

_MANIFEST_VERSION = 1
_SPAN = re.compile(r"term-(\d+)/DSCD-(\d+)-PL-(\d+)\.html$")
_PDF = re.compile(r"pdf-fallback/DSCD-(\d+)-PL-(\d+)\.PDF$")
_ITALY = re.compile(r"italy/leg(\d+)/sitting-(\d+)\.xml$")
_ITALY_HTML = re.compile(r"italy/leg(\d+)/sitting-(\d+)\.html$")
_NETHERLANDS = re.compile(r"netherlands/verslag/([^/]+)\.xml$")
_POLAND_TERM = re.compile(r"poland/term-(\d+)/proceedings\.json$")
_POLAND_DAY = re.compile(
    r"poland/term-(\d+)/proceeding-(\d+)/(\d{4}-\d{2}-\d{2})/statements\.json$"
)
_POLAND_STATEMENT = re.compile(
    r"poland/term-(\d+)/proceeding-(\d+)/(\d{4}-\d{2}-\d{2})/statement-(\d+)\.html$"
)


def _content_type(path: Path) -> str:
    return {
        ".zip": "application/zip",
        ".json": "application/json",
        ".html": "text/html",
        ".xml": "text/xml",
        ".pdf": "application/pdf",
    }.get(path.suffix.casefold(), "application/octet-stream")


def _source_url(relative: str) -> str | None:
    """Infer an official URL from the adapter's deterministic raw path."""
    path = Path(relative)
    name = path.name
    if relative.startswith("spain/"):
        match = _SPAN.search(relative)
        if match:
            return journal_url(int(match.group(2)), int(match.group(3)))
        match = _PDF.search(relative)
        if match:
            return pdf_journal_url(int(match.group(1)), int(match.group(2)))
    if relative.startswith("italy/"):
        match = _ITALY.search(relative)
        if match:
            return camera_xml_url(int(match.group(1)), int(match.group(2)))
        match = _ITALY_HTML.search(relative)
        if match:
            return (f"https://www.camera.it/leg{match.group(1)}/410?"
                    f"idSeduta={match.group(2)}&tipo=stenografico")
    if relative.startswith("netherlands/"):
        match = _NETHERLANDS.search(relative)
        if match:
            return f"{ODATA}/Verslag({match.group(1)})/resource"
    if relative.startswith("poland/"):
        match = _POLAND_TERM.search(relative)
        if match:
            return f"{SEJM_API}/term{match.group(1)}/proceedings"
        match = _POLAND_DAY.search(relative)
        if match:
            return (f"{SEJM_API}/term{match.group(1)}/proceedings/{match.group(2)}/"
                    f"{match.group(3)}/transcripts")
        match = _POLAND_STATEMENT.search(relative)
        if match:
            return (f"{SEJM_API}/term{match.group(1)}/proceedings/{match.group(2)}/"
                    f"{match.group(3)}/transcripts/{match.group(4)}")
    if relative.startswith("france/"):
        match = re.search(r"legislature-(\d+)-syceron\.zip$", relative)
        if match:
            return (f"https://data.assemblee-nationale.fr/static/openData/repository/"
                    f"{match.group(1)}/vp/syceronbrut/syseron.xml.zip")
    if relative.startswith("germany/cpp-bt/"):
        archives = {
            "CPP-BT_2026-09-19_DE_CSV_Reden_Gesamt.zip":
                "https://zenodo.org/api/records/22844952/files/CPP-BT_2026-09-19_DE_CSV_Reden_Gesamt.zip/content",
            "CPP-BT_2026-01-17_DE_CSV_Reden_Gesamt.zip":
                "https://zenodo.org/api/records/18177196/files/CPP-BT_2026-01-17_DE_CSV_Reden_Gesamt.zip/content",
            "CPP-BT_2026-09-19_DE_CSV_Plenarprotokolle_Metadaten.zip":
                "https://zenodo.org/api/records/22844952/files/CPP-BT_2026-09-19_DE_CSV_Plenarprotokolle_Metadaten.zip/content",
        }
        if name in archives:
            return archives[name]
    return None


def _read_existing(path: Path) -> tuple[dict[str, dict[str, Any]], list[str]]:
    entries: dict[str, dict[str, Any]] = {}
    malformed: list[str] = []
    if not path.is_file():
        return entries, malformed
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            malformed.append(f"line {line_number}: invalid JSON")
            continue
        if not isinstance(value, dict) or not isinstance(value.get("local_path"), str):
            malformed.append(f"line {line_number}: missing local_path")
            continue
        entries[value["local_path"]] = value
    return entries, malformed


def _resolve_germany_urls() -> dict[str, str]:
    from .sources.germany import list_protocols

    resolved: dict[str, str] = {}
    for term in (19, 20, 21):
        for url in list_protocols(term):
            filename = Path(urlparse(url).path).name
            resolved[f"germany/term-{term}/{filename}"] = url
    return resolved


def reconcile_source_manifest(raw_dir: str | Path = "data/raw",
                              manifest_path: str | Path = "data/manifests/source_manifest.jsonl",
                              report_path: str | Path = "data/manifests/source_manifest_reconciliation.json",
                              *, resolve_germany: bool = False) -> dict[str, Any]:
    """Hash current raw files and write one deterministic entry per current path."""
    raw = Path(raw_dir)
    manifest = Path(manifest_path)
    existing, malformed = _read_existing(manifest)
    overrides = _resolve_germany_urls() if resolve_germany else {}
    current: dict[str, dict[str, Any]] = {}
    unresolved: list[dict[str, str]] = []
    files = sorted(path for path in raw.rglob("*")
                   if path.is_file() and path.name != ".gitkeep"
                   and not path.name.endswith(".tmp"))
    for path in files:
        relative = path.relative_to(raw).as_posix()
        local_path = path.as_posix()
        url = overrides.get(relative) or _source_url(relative)
        if url is None:
            unresolved.append({"local_path": local_path, "reason": "source URL could not be inferred"})
            url = ""
        entry = file_manifest_entry(
            path, url, content_type=_content_type(path),
            retrieved_at_utc=datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat())
        if not url:
            entry["provenance_status"] = "unresolved_source_url"
        current[local_path] = entry

    historical_missing = sorted(set(existing) - set(current))
    combined = dict(existing)
    combined.update(current)
    ordered = [combined[path] for path in sorted(combined)]
    manifest.parent.mkdir(parents=True, exist_ok=True)
    temporary = manifest.with_suffix(manifest.suffix + ".tmp")
    temporary.write_text("".join(json.dumps(entry, ensure_ascii=False, sort_keys=True) + "\n"
                                  for entry in ordered), encoding="utf-8")
    temporary.replace(manifest)
    report = {
        "manifest_version": _MANIFEST_VERSION,
        "reconciled_at_utc": datetime.now(timezone.utc).isoformat(),
        "current_raw_files": len(current),
        "entries_written": len(ordered),
        "new_or_changed_entries": sum(existing.get(path) != entry for path, entry in current.items()),
        "historical_missing_files": historical_missing,
        "unresolved_source_urls": unresolved,
        "malformed_existing_lines": malformed,
        "germany_urls_resolved": len(overrides),
    }
    report_file = Path(report_path)
    report_file.parent.mkdir(parents=True, exist_ok=True)
    report_file.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Reconcile raw source checksums and URLs")
    parser.add_argument("--raw-dir", type=Path, default=Path("data/raw"))
    parser.add_argument("--manifest", type=Path, default=Path("data/manifests/source_manifest.jsonl"))
    parser.add_argument("--report", type=Path, default=Path("data/manifests/source_manifest_reconciliation.json"))
    parser.add_argument("--resolve-germany", action="store_true",
                        help="query the official XML lists to resolve cached German protocol URLs")
    args = parser.parse_args()
    print(json.dumps(reconcile_source_manifest(args.raw_dir, args.manifest, args.report,
                                               resolve_germany=args.resolve_germany),
                     ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
