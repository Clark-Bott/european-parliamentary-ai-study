"""PDF fallback parser for Congreso Diario journals without usable HTML text."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import hashlib
from io import BytesIO
import re
from typing import Any

from ..models import Speech

PDF_PARSER_VERSION = "pypdf-6.1.1-coordinate-v1"
_PREFIX = re.compile(r"^\s*(La\s*señora|El\s*señor)\b", re.IGNORECASE)
_OPENING = re.compile(r"\bSe\s+(?:abre|reanuda)\s+la\s+sesi[oó]n\b", re.IGNORECASE)
_PAGE_MARK = re.compile(r"^\s*(?:Página|Pag\.)\s*\d*\s*$", re.IGNORECASE)
_FURNITURE = re.compile(
    r"DIARIO DE SESIONES|PLENO Y DIPUTACIÓN PERMANENTE|^NÚM\.|^PÁG\.|^CVE:",
    re.IGNORECASE,
)
_STAGE_START = re.compile(
    r"^\s*(?:(?:Continúan|Se producen) los? )?"
    r"(?:Aplausos|Rumores|Risas|Protestas|Pausa)",
    re.IGNORECASE,
)
_DATE_TEXT = re.compile(
    r"\b(\d{1,2})\s+de\s+(enero|febrero|marzo|abril|mayo|junio|julio|agosto|"
    r"septiembre|setiembre|octubre|noviembre|diciembre)\s+de\s+(\d{4})\b",
    re.IGNORECASE,
)
_MONTHS = {"enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5,
           "junio": 6, "julio": 7, "agosto": 8, "septiembre": 9, "setiembre": 9,
           "octubre": 10, "noviembre": 11, "diciembre": 12}


@dataclass(frozen=True)
class _Chunk:
    order: int
    x: float
    y: float
    text: str
    font: str
    bold: bool


@dataclass(frozen=True)
class _Line:
    page: int
    y: float
    x: float
    text: str
    bold: bool
    chunks: tuple[_Chunk, ...]


def _font_info(font_dict: Any) -> tuple[str, bool]:
    if not isinstance(font_dict, dict):
        return "", False
    font = str(font_dict.get("/BaseFont", ""))
    return font, "bold" in font.casefold()


def _matrix_multiply(left: list[float], right: list[float]) -> list[float]:
    """Multiply pypdf's row-vector text and current transformation matrices."""
    return [
        left[0] * right[0] + left[1] * right[2],
        left[0] * right[1] + left[1] * right[3],
        left[2] * right[0] + left[3] * right[2],
        left[2] * right[1] + left[3] * right[3],
        left[4] * right[0] + left[5] * right[2] + right[4],
        left[4] * right[1] + left[5] * right[3] + right[5],
    ]


def _join_chunks(chunks: list[_Chunk]) -> str:
    """Join pypdf font runs without losing word boundaries."""
    pieces: list[str] = []
    for chunk in sorted(chunks, key=lambda item: (item.x, item.order)):
        if not chunk.text:
            continue
        if pieces and not pieces[-1].endswith((" ", "\n")) and not chunk.text.startswith((" ", "\n")):
            pieces.append(" ")
        pieces.append(chunk.text)
    return " ".join("".join(pieces).replace("\u00ad", "").split())


def extract_pdf_lines(data: bytes) -> list[list[_Line]]:
    """Extract positioned text lines from a text-layer PDF using pypdf."""
    try:
        from pypdf import PdfReader
    except ImportError as exc:  # pragma: no cover - exercised by runtime setup
        raise RuntimeError("pypdf==6.1.1 is required for the Spanish PDF fallback") from exc

    reader = PdfReader(BytesIO(data), strict=False)
    pages: list[list[_Line]] = []
    order = 0
    for page_number, page in enumerate(reader.pages, 1):
        chunks: list[_Chunk] = []
        tracked_text_matrix = [1.0, 0.0, 0.0, 1.0, 0.0, 0.0]
        tracked_current_matrix = [1.0, 0.0, 0.0, 1.0, 0.0, 0.0]

        def before(_operator: str, _operands: list[Any], cm: Any, tm: Any) -> None:
            nonlocal tracked_current_matrix, tracked_text_matrix
            tracked_current_matrix = [float(value) for value in (cm or tracked_current_matrix)]
            tracked_text_matrix = [float(value) for value in (tm or tracked_text_matrix)]

        def visitor(text: str, _cm: Any, _tm: Any, font_dict: Any, _font_size: Any) -> None:
            nonlocal order
            if not text or not text.strip():
                return
            font, bold = _font_info(font_dict)
            matrix = _matrix_multiply(tracked_text_matrix, tracked_current_matrix)
            chunks.append(_Chunk(order, float(matrix[4]), float(matrix[5]), text, font, bold))
            order += 1

        page.extract_text(visitor_text=visitor, visitor_operand_before=before)
        buckets: list[tuple[float, list[_Chunk]]] = []
        for chunk in sorted(chunks, key=lambda item: (-item.y, item.order)):
            if not buckets or abs(chunk.y - buckets[-1][0]) > 0.75:
                buckets.append((chunk.y, [chunk]))
            else:
                buckets[-1][1].append(chunk)
        lines = []
        for y, group in buckets:
            ordered = tuple(sorted(group, key=lambda item: (item.x, item.order)))
            lines.append(_Line(page_number, y, min(item.x for item in ordered),
                               _join_chunks(list(ordered)), any(item.bold for item in ordered), ordered))
        pages.append(lines)
    return pages


def _is_heading(line: _Line) -> bool:
    if not line.bold:
        return False
    letters = "".join(character for character in line.text if character.isalpha())
    if not letters:
        return False
    uppercase_ratio = sum(character.isupper() for character in letters) / len(letters)
    # The PDF uses bold uppercase lines for agenda text. Speaker labels are
    # removed before body collection and therefore do not reach this test.
    return uppercase_ratio >= 0.82


def _remove_stage_directions(text: str) -> str:
    """Remove balanced Spanish audience-cue parentheses, retaining other text."""
    output: list[str] = []
    index = 0
    while index < len(text):
        if text[index] != "(":
            output.append(text[index])
            index += 1
            continue
        depth = 1
        end = index + 1
        while end < len(text) and depth:
            if text[end] == "(":
                depth += 1
            elif text[end] == ")":
                depth -= 1
            end += 1
        if depth == 0 and _STAGE_START.match(text[index + 1:end - 1]):
            output.append(" ")
        else:
            output.append(text[index:end])
        index = end
    return "".join(output)


def _normalise_body(text: str) -> str:
    text = _remove_stage_directions(text.replace("\u00ad", ""))
    text = " ".join(text.split())
    text = re.sub(r"\s+([,.;:!?])", r"\1", text)
    text = re.sub(r"([¿¡])\s+", r"\1", text)
    return text.strip()


def _label_role(label: str) -> str:
    upper = label.upper()
    if "MINISTR" in upper:
        return "minister"
    if re.match(r"^(?:PRESIDENTE|PRESIDENTA|VICEPRESIDENTE|VICEPRESIDENTA)\b", upper):
        return "presiding_officer"
    return ""


def parse_congreso_pdf(data: bytes, *, source_url: str, term: int, number: int,
                       date_value: str | None = None) -> list[Speech]:
    """Parse speaker-labelled turns from an official Congreso Diario PDF."""
    if not data.startswith(b"%PDF"):
        raise ValueError("Spain PDF fallback is not a PDF document")
    pages = extract_pdf_lines(data)
    lines = [line for page in pages for line in page]
    openings = [index for index, line in enumerate(lines) if _OPENING.search(line.text)]
    if len(openings) < 2:
        raise ValueError(f"expected two opening markers in DSCD-{term}-PL-{number}")
    candidates: list[tuple[int, str, _Line]] = []
    for index in range(openings[1], len(lines)):
        line = lines[index]
        match = _PREFIX.match(line.text)
        if match and line.bold and 70 <= line.x <= 150:
            candidates.append((index, match.group(1), line))
    if not candidates:
        raise ValueError(f"no PDF speaker boundaries in DSCD-{term}-PL-{number}")

    if date_value is None:
        date_value = None
        for line in lines:
            numeric = re.search(r"\b\d{2}/\d{2}/\d{4}\b", line.text)
            if numeric:
                date_value = datetime.strptime(numeric.group(0), "%d/%m/%Y").date().isoformat()
                break
            textual = _DATE_TEXT.search(line.text)
            if textual:
                day, month_name, year = textual.groups()
                date_value = datetime(int(year), _MONTHS[month_name.casefold()], int(day)).date().isoformat()
                break
        if date_value is None:
            raise ValueError(f"no date in DSCD-{term}-PL-{number} PDF")

    heading_indices = {index for index, line in enumerate(lines) if _is_heading(line)}
    session = f"congreso-{term}-PL-{number}"
    source_hash = hashlib.sha256(data).hexdigest()
    output: list[Speech] = []
    for turn_index, (line_index, _prefix, label_line) in enumerate(candidates):
        match = _PREFIX.match(label_line.text)
        assert match is not None
        label_text = label_line.text[match.end():]
        end_line = line_index
        while ":" not in label_text and end_line + 1 < len(lines) and end_line - line_index < 8:
            end_line += 1
            label_text += " " + lines[end_line].text
        if ":" not in label_text:
            raise ValueError(f"unterminated PDF speaker label at line {line_index}")
        label, body_on_label = label_text.split(":", 1)
        label = " ".join(label.split())
        next_index = candidates[turn_index + 1][0] if turn_index + 1 < len(candidates) else len(lines)
        body_lines: list[str] = []
        heading = next((index for index in sorted(heading_indices)
                        if end_line < index < next_index), None)
        body_end = heading if heading is not None else next_index
        if body_on_label.strip():
            body_lines.append(body_on_label.strip())
        for index in range(end_line + 1, body_end):
            line = lines[index]
            if not line.text.strip() or line.y > 735 or line.y < 55:
                continue
            if _PAGE_MARK.match(line.text) or _FURNITURE.search(line.text):
                continue
            body_lines.append(line.text)
        raw_text = " ".join(body_lines)
        speech_text = _normalise_body(raw_text)
        if not label or not speech_text:
            raise ValueError(f"empty PDF turn {turn_index + 1} in DSCD-{term}-PL-{number}")
        speech_id = f"{session}:turn-{turn_index + 1:04d}"
        output.append(Speech(
            country="Spain", parliament="Congreso de los Diputados",
            chamber="Congreso de los Diputados", date=date_value, session_id=session,
            speech_id=speech_id, speaker_id="", speaker_name=label,
            speaker_role=_label_role(label), legislative_term=str(term),
            speech_text=speech_text, raw_text=raw_text, source_url=source_url,
            source_identifier=speech_id, source_type="official_congreso_diario_pdf",
            text_language="es",
            cleaning_notes=(f"{PDF_PARSER_VERSION}; removed PDF page furniture, all-caps agenda blocks, "
                            f"and stage cues; source PDF SHA-256 {source_hash}."),
        ))
    return output
