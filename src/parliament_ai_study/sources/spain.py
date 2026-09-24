"""Official Congreso Diario de Sesiones HTML, plenary speech turns only.

The open-data intervention CSV/JSON is an index of recordings, not speech text.
The official full-text Diario is the source of the spoken content.
"""
from __future__ import annotations

from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path
import json
import re

from ..io import write_jsonl
from ..models import Speech
from .download import download_file, fetch_bytes
from .spain_pdf import parse_congreso_pdf

BASE = "https://www.congreso.es"
_TURN = re.compile(r"^[ \t]*(?:La señora|El señor)\s+([A-ZÁÉÍÓÚÜÑÀÈÌÒÙÇ][^:\n]{1,105}):\s*", re.M)
_STAGE = re.compile(r"\((?:(?:Continúan|Se producen) los? )?(?:Aplausos|Rumores|Risas|Protestas|Pausa)[^()]*\)", re.I)


def journal_url(term: int, number: int) -> str:
    roman = {12: "XII", 13: "XIII", 14: "XIV", 15: "XV"}[term]
    return (f"{BASE}/busqueda-de-intervenciones?p_p_id=intervenciones&p_p_lifecycle=0&"
            "p_p_state=normal&p_p_mode=view&_intervenciones_mode=mostrarTextoIntegro&"
            f"_intervenciones_legislatura={roman}&_intervenciones_id_texto=(DSCD-{term}-PL-{number}.CODI.)")


def pdf_journal_url(term: int, number: int) -> str:
    return f"{BASE}/public_oficiales/L{term}/CONG/DS/PL/DSCD-{term}-PL-{number}.PDF"


class _Journal(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.active = False
        self.parts: list[str] = []
        self.date_parts: list[str] = []
        self.in_date = False

    def handle_starttag(self, tag, attrs):
        classes = dict(attrs).get("class", "").split()
        if tag == "p" and "textoCompleto" in classes:
            self.active = True
        if tag == "div" and "datos1" in classes:
            self.in_date = True
        if self.active and tag in ("br", "p"):
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag == "div":
            if self.in_date:
                self.in_date = False
            elif self.active:
                self.active = False
        if self.active and tag == "p":
            self.parts.append("\n")

    def handle_data(self, data):
        if self.in_date:
            self.date_parts.append(data)
        if self.active:
            self.parts.append(data)


def parse_congreso_html(data: bytes | str, *, source_url: str, term: int, number: int) -> list[Speech]:
    if isinstance(data, bytes):
        data = data.decode("utf-8", errors="replace")
    parser = _Journal()
    parser.feed(data)
    date_match = re.search(r"\b(\d{2}/\d{2}/\d{4})\b", " ".join(parser.date_parts))
    if not date_match or not parser.parts:
        raise ValueError(f"official journal DSCD-{term}-PL-{number} has no full text/date")
    day = datetime.strptime(date_match.group(1), "%d/%m/%Y").date().isoformat()
    text = "".join(parser.parts)
    # Some journals repeat their opening in the synopsis; others mention only
    # the adjournment there, leaving a single opening in verbatim proceedings.
    # Do not classify the synopsis itself as spoken text.
    openings = list(re.finditer(r"Se (?:abre|reanuda) la sesión\b", text, re.I))
    if not openings:
        raise ValueError(f"cannot locate verbatim debate after synopsis in DSCD-{term}-PL-{number}")
    before_opening = text[:openings[0].start()]
    if "SUMARIO" not in before_opening and ("ORDEN DEL DÍA" not in before_opening or len(openings) < 2):
        raise ValueError(f"cannot locate verbatim debate after synopsis in DSCD-{term}-PL-{number}")
    text = text[openings[1 if len(openings) > 1 else 0].start():]
    turns = list(_TURN.finditer(text))
    if not turns:
        raise ValueError(f"no speaker boundaries in DSCD-{term}-PL-{number}")
    session = f"congreso-{term}-PL-{number}"
    output = []
    for index, match in enumerate(turns):
        label = " ".join(match.group(1).split())
        if re.search(r"\bSECRETARI[OA]\s+DE\s+LA\s+MESA", label):
            continue  # roll-call and formal reading, not a substantive intervention
        raw = " ".join(text[match.end():turns[index + 1].start() if index + 1 < len(turns) else len(text)].split())
        # Remove page markers and parenthesized audience cues, not substantive
        # prose. Agenda headings between turns remain a manual QA concern.
        cleaned = re.sub(r"\bPágina\s+\d+\b", " ", raw)
        cleaned = " ".join(_STAGE.sub(" ", cleaned).split())
        if not cleaned:
            continue
        speech_id = f"{session}:turn-{index + 1:04d}"
        output.append(Speech(country="Spain", parliament="Congreso de los Diputados",
                             chamber="Congreso de los Diputados", date=day, session_id=session,
                             speech_id=speech_id, speaker_id="", speaker_name=label,
                             speaker_role="presiding_officer" if "PRESIDENT" in label else
                             "minister" if "MINISTR" in label else "",
                             legislative_term=str(term), speech_text=cleaned, raw_text=raw,
                             source_url=source_url, source_identifier=speech_id,
                             source_type="official_congreso_diario_html", text_language="es",
                             cleaning_notes="Synopsis and page markers removed; speech boundaries follow Diario speaker labels."))
    return output


def _has_journal(term: int, number: int) -> bool:
    body, _ = fetch_bytes(journal_url(term, number))
    return 'class="textoCompleto"' in body.decode("utf-8", errors="replace")


def _last_journal(term: int) -> int:
    low, high = 1, 2
    while _has_journal(term, high):
        low, high = high, high * 2
        if high > 4096:
            raise ValueError(f"Congress term {term} journal upper bound exceeded")
    while low + 1 < high:
        mid = (low + high) // 2
        if _has_journal(term, mid):
            low = mid
        else:
            high = mid
    return low


def audit_congreso_raw_coverage(raw_dir: str | Path = "data/raw") -> dict:
    """Summarize downloaded Diario HTML/PDF files and remaining unresolved journals."""
    terms = []
    for term in (12, 13, 14, 15):
        directory = Path(raw_dir) / "spain" / f"term-{term}"
        numbers = sorted(int(path.stem.rsplit("-", 1)[1]) for path in directory.glob("DSCD-*-PL-*.html"))
        if not numbers:
            terms.append({"term": term, "html_files": 0, "first": None, "last": None,
                          "expected_range": 0, "missing_html_numbers": []})
            continue
        expected = set(range(min(numbers), max(numbers) + 1))
        terms.append({
            "term": term, "html_files": len(numbers), "first": min(numbers), "last": max(numbers),
            "expected_range": len(expected), "missing_html_numbers": sorted(expected - set(numbers)),
            "html_full_text_files": sum(b'class="textoCompleto"' in path.read_bytes()
                                        for path in directory.glob("DSCD-*-PL-*.html")),
        })
    pdf_dir = Path(raw_dir) / "spain" / "pdf-fallback"
    pdfs = sorted(path.name for path in pdf_dir.glob("DSCD-*-PL-*.PDF"))
    return {"terms": terms, "pdf_fallback_files": pdfs,
            "note": "Raw-file audit only; it does not replace official index reconciliation or random boundary review."}


def build_congreso_corpus(output_path: str | Path, *, start_year: int = 2018, end_year: int = 2026,
                          raw_dir: str | Path = "data/raw",
                          manifest_path: str | Path = "data/manifests/source_manifest.jsonl") -> dict[str, int]:
    counts = {"records": 0, "words": 0, "journals": 0, "pdf_fallback_journals": 0}
    gaps: list[dict[str, str | int]] = []

    def rows():
        for term in (12, 13, 14, 15):
            last = _last_journal(term)
            first = 1
            if term == 12 and start_year > 2016:
                low, high = 1, last + 1
                while low < high:
                    mid = (low + high) // 2
                    probe, _ = fetch_bytes(journal_url(term, mid))
                    probe_parser = _Journal()
                    probe_parser.feed(probe.decode("utf-8", errors="replace"))
                    match = re.search(r"\b\d{2}/\d{2}/(\d{4})\b", " ".join(probe_parser.date_parts))
                    if not match:
                        raise ValueError(f"date missing in Congreso journal {term}-{mid}")
                    if int(match.group(1)) < start_year:
                        low = mid + 1
                    else:
                        high = mid
                first = low
            for number in range(first, last + 1):
                url = journal_url(term, number)
                path = Path(raw_dir) / "spain" / f"term-{term}" / f"DSCD-{term}-PL-{number}.html"
                if not path.exists():
                    download_file(url, path, manifest_path=manifest_path)
                contents = path.read_bytes()
                source_url = url
                if b'class="textoCompleto"' in contents:
                    speeches = parse_congreso_html(contents, source_url=source_url,
                                                   term=term, number=number)
                else:
                    pdf_path = Path(raw_dir) / "spain" / "pdf-fallback" / f"DSCD-{term}-PL-{number}.PDF"
                    if not pdf_path.exists():
                        download_file(pdf_journal_url(term, number), pdf_path,
                                      manifest_path=manifest_path,
                                      headers={"User-Agent": "Mozilla/5.0", "Referer": f"{BASE}/"})
                    try:
                        source_url = pdf_journal_url(term, number)
                        speeches = parse_congreso_pdf(pdf_path.read_bytes(), source_url=source_url,
                                                      term=term, number=number)
                        counts["pdf_fallback_journals"] += 1
                    except Exception as exc:
                        gaps.append({"term": term, "number": number, "url": source_url,
                                     "reason": "official PDF fallback could not be parsed",
                                     "error": f"{type(exc).__name__}: {exc}"})
                        continue
                if not speeches or not start_year <= int(speeches[0].date[:4]) <= end_year:
                    continue
                counts["journals"] += 1
                for speech in speeches:
                    counts["records"] += 1
                    counts["words"] += speech.word_count
                    yield speech.to_dict()

    write_jsonl(output_path, rows())
    report = Path(manifest_path).parent / "spain_unavailable_journals.json"
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(gaps, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    coverage_path = report.parent / "spain_coverage_audit.json"
    coverage_path.write_text(json.dumps(audit_congreso_raw_coverage(raw_dir), ensure_ascii=False, indent=2) + "\n",
                             encoding="utf-8")
    counts["unavailable_journal_numbers"] = len(gaps)
    counts["coverage_audit"] = str(coverage_path)
    return counts
