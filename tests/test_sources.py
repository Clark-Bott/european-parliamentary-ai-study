import hashlib
import json
import os
import tempfile
import unittest
from pathlib import Path
from http.client import IncompleteRead
from zipfile import ZipFile

from parliament_ai_study.sources.download import download_file, file_manifest_entry
from parliament_ai_study.sources.france import parse_france_xml
from parliament_ai_study.sources.germany import (CPP_BT_MEMBER, build_bundestag_corpus,
                                               iter_cpp_bt_speeches, list_protocols,
                                               parse_bundestag_xml, _Links)
from parliament_ai_study.sources.italy import build_camera_corpus, parse_camera_html, parse_camera_xml
from parliament_ai_study.sources.netherlands import (audit_tweede_kamer_coverage,
    iter_tweede_kamer_speeches, parse_tweede_kamer_xml, _odata_pages,
    _select_final_report)
from unittest.mock import patch
from parliament_ai_study.sources.sejm import (audit_sejm_raw_coverage, build_sejm_corpus,
                                                download_sejm_date, parse_sejm_statement)
from parliament_ai_study.sources.spain import (_has_journal, _html_full_text_available,
                                             parse_congreso_html, journal_url)
from parliament_ai_study.sources.spain_pdf import _Chunk, _Line, parse_congreso_pdf


def _spain_pdf_fixture(term: int, number: int) -> Path | None:
    """Locate an official PDF fixture, which is not part of a fresh clone.

    Search order: PARLIAMENT_SPAIN_PDF_DIR, then the local raw archive. The
    golden test skips when no fixture is present on this machine.
    """
    name = f"DSCD-{term}-PL-{number}.PDF"
    candidates = []
    override = os.environ.get("PARLIAMENT_SPAIN_PDF_DIR")
    if override:
        candidates.append(Path(override) / name)
    candidates.append(Path("/tmp/opencode") / name)
    for directory in (Path("data/raw/spain"), Path("data/raw")):
        if directory.is_dir():
            candidates.extend(sorted(directory.rglob(name)))
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return None


def _both_spain_fixtures_present() -> bool:
    return all(_spain_pdf_fixture(term, number)
               for term, number in ((12, 162), (14, 59)))


class CongresoParserTests(unittest.TestCase):
    def test_order_of_day_synopsis_precedes_verbatim_opening(self):
        html = '''<div class="datos1">DS. Pleno, de 07/06/2023</div>
        <p class="textoCompleto">ORDEN DEL DÍA: Decreto ...<br>Se abre la sesión a las once.<br>
        La señora PRESIDENTA: Resumen no pronunciado.<br>Se abre la sesión a las once.<br>
        La señora PRESIDENTA: Empieza la sesión de hoy.<br>El señor PÉREZ: Texto pronunciado.</p></div>'''
        rows = parse_congreso_html(html, source_url=journal_url(14, 273), term=14, number=273)
        self.assertEqual(len(rows), 2)
        self.assertNotIn("Resumen", rows[0].speech_text)

    def test_one_opening_after_synopsis_is_enough_for_reconvened_sitting(self):
        html = '''<div class="datos1">DS. Pleno, de 12/04/2018</div>
        <p class="textoCompleto">SUMARIO<br>Se levanta la sesión a la una.<br>
        Se reanuda la sesión a las nueve.<br>
        El señor MONTORO ROMERO: Muchas gracias. Esta ley es fundamental.<br>
        La señora ORAMAS: Gracias. La propuesta plantea muchas dudas.</p></div>'''
        rows = parse_congreso_html(html, source_url=journal_url(12, 115), term=12, number=115)
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0].date, "2018-04-12")
        self.assertNotIn("Se levanta", rows[0].speech_text)

    def test_ignores_synopsis_and_segments_verbatim_remarks(self):
        html = '''<div class="datos1">DS. Pleno, núm. 1, de 17/08/2023</div>
        <p class="textoCompleto">SUMARIO<br>Se abre la sesión a las diez.<br>
        La señora PRESIDENTA: Summary text only.<br>
        Se abre la sesión a las diez.<br>
        La señora PRESIDENTA: Comienza el debate.<br>
        El señor RODRÍGUEZ DE MILLÁN: Señorías, esta propuesta es importante. (Aplausos).<br>
        La señora PRESIDENTA: Gracias, señor diputado.</p></div>'''
        rows = parse_congreso_html(html, source_url=journal_url(15, 1), term=15, number=1)
        self.assertEqual(len(rows), 3)
        self.assertEqual(rows[1].date, "2023-08-17")
        self.assertEqual(rows[1].speaker_name, "RODRÍGUEZ DE MILLÁN")
        self.assertNotIn("Summary", rows[0].speech_text)
        self.assertNotIn("Aplausos", rows[1].speech_text)
        self.assertIn("Aplausos", rows[1].raw_text)

    def test_pdf_fallback_handles_wrapped_labels_and_stage_cues(self):
        def line(text, *, bold=False, x=82.2, y=500.0):
            return _Line(1, y, x, text, bold, (_Chunk(0, x, y, text, "Bold" if bold else "Regular", bold),))
        pages = [[
            line("Se reanuda la sesión a las nueve.", y=730),
            line("Se reanuda la sesión a las nueve.", y=720),
            line("La señora VICEPRESIDENTA", bold=True, y=700),
            line("DEL GOBIERNO: Buenos días.", bold=True, y=680),
            line("La respuesta continúa.", y=660),
            line("DIARIO DE SESIONES DEL CONGRESO DE LOS DIPUTADOS", bold=True, y=800),
            line("La continuación no se pierde.", y=650),
            line("El señor MINISTRO DE SANIDAD: Gracias. (Aplausos).", bold=True, y=640),
            line("DIARIO DE SESIONES DEL CONGRESO", bold=True, y=800),
        ]]
        with patch("parliament_ai_study.sources.spain_pdf.extract_pdf_lines", return_value=pages):
            rows = parse_congreso_pdf(b"%PDF-1.4\n", source_url="https://example.test/journal.pdf",
                                       term=14, number=59, date_value="2020-10-29")
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0].speaker_name, "VICEPRESIDENTA DEL GOBIERNO")
        self.assertEqual(rows[0].speaker_role, "presiding_officer")
        self.assertIn("La continuación no se pierde", rows[0].speech_text)
        self.assertNotIn("Aplausos", rows[1].speech_text)
        self.assertIn("Aplausos", rows[1].raw_text)

    def test_pdf_only_journal_is_detected_when_html_has_no_full_text(self):
        self.assertFalse(_html_full_text_available(b"<html><body>sin texto</body></html>"))
        with patch("parliament_ai_study.sources.spain.fetch_bytes", return_value=(b"<html></html>", {})), \
             patch("parliament_ai_study.sources.spain._pdf_journal_available", return_value=True):
            self.assertTrue(_has_journal(12, 162))

    def test_pdf_fallback_accepts_one_opening_marker(self):
        def line(text, *, bold=False, x=82.2, y=500.0):
            return _Line(1, y, x, text, bold, (_Chunk(0, x, y, text, "Bold" if bold else "Regular", bold),))
        pages = [[
            line("Se reanuda la sesión a las nueve.", y=720),
            line("La señora PRESIDENTA: Hola", bold=True, y=700),
        ]]
        with patch("parliament_ai_study.sources.spain_pdf.extract_pdf_lines", return_value=pages):
            rows = parse_congreso_pdf(b"%PDF-1.4\n", source_url="https://example.test/journal.pdf",
                                       term=14, number=59, date_value="2020-10-29")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].speaker_name, "PRESIDENTA")

    def test_pdf_fallback_raises_without_an_opening_marker(self):
        line = _Line(1, 500, 82.2, "La señora PRESIDENTA: Hola", True,
                     (_Chunk(0, 82.2, 500, "La señora PRESIDENTA: Hola", "Bold", True),))
        with patch("parliament_ai_study.sources.spain_pdf.extract_pdf_lines", return_value=[[line]]):
            with self.assertRaisesRegex(ValueError, "opening marker"):
                parse_congreso_pdf(b"%PDF-1.4\n", source_url="https://example.test/journal.pdf",
                                   term=14, number=59, date_value="2020-10-29")

    @unittest.skipUnless(_both_spain_fixtures_present(),
                         "official PDF validation fixtures are not in a fresh clone")
    def test_official_pdf_fallback_golden_counts_and_determinism(self):
        try:
            import pypdf  # noqa: F401
        except ImportError:
            self.skipTest("pypdf is not installed in the no-project test environment")
        expected = {(12, 162): (252, 39537, "rompa con los partidos independentistas"),
                    (14, 59): (148, 53545, "la vacuna o un tratamiento eficaz")}
        for (term, number), (count, words, excerpt) in expected.items():
            path = _spain_pdf_fixture(term, number)
            self.assertIsNotNone(path, f"fixture missing for DSCD-{term}-PL-{number}")
            url = f"https://www.congreso.es/public_oficiales/L{term}/CONG/DS/PL/DSCD-{term}-PL-{number}.PDF"
            first = parse_congreso_pdf(path.read_bytes(), source_url=url, term=term, number=number)
            second = parse_congreso_pdf(path.read_bytes(), source_url=url, term=term, number=number)
            self.assertEqual(len(first), count)
            self.assertEqual(sum(row.word_count for row in first), words)
            self.assertTrue(any(excerpt in row.speech_text for row in first))
            self.assertEqual([row.to_dict() for row in first], [row.to_dict() for row in second])


class ManifestTests(unittest.TestCase):
    def test_unknown_range_total_falls_back_to_verified_plain_get(self):
        with tempfile.TemporaryDirectory() as directory:
            calls = []

            class Response:
                def __init__(self, status):
                    self.status = status
                    self.headers = {"Content-Type": "application/xml", **(
                        {"Content-Range": "bytes 0-0/*"} if status == 206 else {"Content-Length": "4"})}
                    self.data = b"<x/>" if status == 200 else b"<"
                    self.position = 0
                def __enter__(self): return self
                def __exit__(self, *args): return False
                def read(self, size=-1):
                    data = self.data[self.position:self.position + size]
                    self.position += len(data)
                    return data

            def opener(request, timeout):
                calls.append(request.get_header("Range"))
                return Response(206 if request.get_header("Range") else 200)

            path = Path(directory) / "archive.xml"
            download_file("https://example.test/archive.xml", path, manifest_path=Path(directory) / "manifest.jsonl",
                          opener=opener, sleep=lambda _: None)
            self.assertEqual(calls, ["bytes=0-0", None])
            self.assertEqual(path.read_bytes(), b"<x/>")

    def test_download_retries_malformed_partial_content_metadata(self):
        with tempfile.TemporaryDirectory() as directory:
            calls = []

            class Response:
                status = 206
                def __init__(self, attempt):
                    self.sent = False
                    self.headers = {"Content-Range": "invalid" if attempt == 1 else "bytes 0-0/1",
                                    "Content-Type": "application/xml"}
                def __enter__(self): return self
                def __exit__(self, *args): return False
                def read(self, size=-1):
                    if self.sent: return b""
                    self.sent = True
                    return b"x"

            def opener(request, timeout):
                calls.append(request.get_header("Range"))
                return Response(len(calls))

            path = Path(directory) / "source.xml"
            download_file("https://example.test/source.xml", path, manifest_path=Path(directory) / "manifest.jsonl",
                          opener=opener, retries=2, sleep=lambda _: None)
            self.assertEqual(path.read_bytes(), b"x")
            self.assertEqual(len(calls), 3)

    def test_manifest_records_hash_size_type_and_source_without_query_credentials(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "source.xml"
            path.write_bytes("données".encode("utf-8"))
            entry = file_manifest_entry(path, "https://data.example/record?apikey=secret", content_type="text/xml")
            self.assertEqual(entry["bytes"], path.stat().st_size)
            self.assertEqual(entry["sha256"], hashlib.sha256(path.read_bytes()).hexdigest())
            self.assertEqual(entry["content_type"], "text/xml")
            self.assertEqual(entry["source_url"], "https://data.example/record")

    def test_download_streams_to_disk_and_retries_an_incomplete_response(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "archive.zip"
            manifest = Path(directory) / "manifest.jsonl"
            payload = b"0123456789abcdef"
            attempts = []

            class FakeResponse:
                status = 200
                headers = {"Content-Type": "application/zip", "Content-Length": str(len(payload))}
                def __init__(self, fail_after=None):
                    self.position = 0
                    self.fail_after = fail_after
                    self.failed = False
                def __enter__(self): return self
                def __exit__(self, *args): return False
                def read(self, size=-1):
                    if size < 0:
                        raise AssertionError("download must stream in bounded chunks")
                    if self.fail_after is not None and self.position >= self.fail_after and not self.failed:
                        self.failed = True
                        raise IncompleteRead(b"", len(payload) - self.position)
                    if self.position >= len(payload): return b""
                    end = min(self.position + size, len(payload), self.fail_after or len(payload))
                    chunk = payload[self.position:end]
                    self.position = end
                    return chunk

            def opener(request, timeout):
                attempts.append(request.full_url)
                return FakeResponse(fail_after=2) if len(attempts) == 1 else FakeResponse()

            entry = download_file("https://data.example/archive.zip", target,
                                  manifest_path=manifest, opener=opener, retries=2,
                                  sleep=lambda _: None, chunk_size=4)
            self.assertEqual(target.read_bytes(), payload)
            self.assertEqual(entry["bytes"], len(payload))
            self.assertEqual(len(attempts), 2)
            self.assertEqual(len(manifest.read_text(encoding="utf-8").splitlines()), 1)
    def test_ranged_download_assembles_exact_byte_ranges(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "ranged.bin"
            manifest = Path(directory) / "manifest.jsonl"
            payload = b"0123456789"
            requested = []

            class RangeResponse:
                def __init__(self, start, end):
                    self.body = payload[start:end + 1]
                    self.position = 0
                    self.status = 206
                    self.headers = {"Content-Type": "application/octet-stream",
                                    "Content-Range": f"bytes {start}-{end}/{len(payload)}",
                                    "Content-Length": str(len(self.body))}
                def __enter__(self): return self
                def __exit__(self, *args): return False
                def read(self, size=-1):
                    part = self.body[self.position:self.position + size]
                    self.position += len(part)
                    return part

            def opener(request, timeout):
                value = request.get_header("Range")
                requested.append(value)
                start, end = map(int, value.removeprefix("bytes=").split("-"))
                return RangeResponse(start, end)

            download_file("https://data.example/ranged", target, manifest_path=manifest,
                          opener=opener, range_chunk_size=4, chunk_size=2,
                          sleep=lambda _: None)
            self.assertEqual(target.read_bytes(), payload)
            self.assertEqual(requested, ["bytes=0-0", "bytes=0-3", "bytes=4-7", "bytes=8-9"])


class BundestagParserTests(unittest.TestCase):
    def test_cpp_bt_baseline_survives_official_xml_source_failure(self):
        fixture = Path(__file__).parent / "fixtures" / CPP_BT_MEMBER
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive = root / "raw" / "germany" / "cpp-bt" / "speeches.zip"
            archive.parent.mkdir(parents=True)
            with ZipFile(archive, "w") as bundle:
                bundle.write(fixture, CPP_BT_MEMBER)
            with patch("parliament_ai_study.sources.germany._ensure_cpp_bt_archive", return_value=archive), \
                 patch("parliament_ai_study.sources.germany.list_protocols", side_effect=OSError("blocked")):
                stats = build_bundestag_corpus(root / "germany.jsonl", raw_dir=root / "raw",
                                               manifest_path=root / "manifest.jsonl")
            self.assertEqual(stats["cpp_bt_records"], 1)
            self.assertEqual(stats["official_xml_status"], "unavailable")
            self.assertEqual(stats["records"], 1)
            self.assertIn("blocked", stats["official_xml_error"])
            self.assertIn("blocked", (root / "germany_unavailable_protocols.json").read_text())

    def test_cpp_bt_archive_normalizes_speech_metadata_and_skips_empty_text(self):
        fixture = Path(__file__).parent / "fixtures" / CPP_BT_MEMBER
        with tempfile.TemporaryDirectory() as directory:
            archive = Path(directory) / "speeches.zip"
            with ZipFile(archive, "w") as bundle:
                bundle.write(fixture, CPP_BT_MEMBER)
            rows = list(iter_cpp_bt_speeches(archive))
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row.speech_id, "ID1900100100")
        self.assertEqual(row.date, "2018-01-10")
        self.assertEqual(row.speaker_id, "11001001")
        self.assertEqual(row.speaker_name, "Dr. Erika Example")
        self.assertEqual(row.party, "CDU/CSU")
        self.assertEqual(row.speech_text, "Vielen Dank, Herr Präsident. (Beifall)")
        self.assertIn("zenodo.22844952", row.source_url)

    def test_protocol_list_uses_official_limit_and_html_headers(self):
        requests = []
        def fake_page(url):
            requests.append(url)
            offset = int(url.rsplit("offset=", 1)[1])
            links = (f'<a href="/resource/blob/1/{19000 + offset + index}.xml">x</a>'
                     for index in range(10 if offset == 0 else 1))
            return ("".join(links)).encode()
        with patch("parliament_ai_study.sources.germany._fetch_list_page", side_effect=fake_page):
            links = list_protocols(19)
        self.assertEqual(len(links), 11)
        self.assertIn("limit=10&offset=0", requests[0])
        self.assertIn("limit=10&offset=10", requests[1])

    def test_list_request_uses_official_referer_header(self):
        with patch("parliament_ai_study.sources.germany.urlopen") as opener:
            opener.return_value.__enter__.return_value.read.return_value = b""
            list_protocols(19)
        request = opener.call_args.args[0]
        self.assertEqual(request.get_header("Referer"), "https://www.bundestag.de/services/opendata")
        self.assertIn("text/html", request.get_header("Accept"))

    def test_minister_role_comes_from_nested_official_role_label(self):
        xml = '''<dbtplenarprotokoll wahlperiode="21" sitzung-nr="95" sitzung-datum="23.09.2026">
          <rede id="ID1"><p klasse="redner"><redner id="1"><name><vorname>Boris</vorname>
          <nachname>Pistorius</nachname><rolle><rolle_lang>Bundesminister der Verteidigung</rolle_lang>
          </rolle></name></redner>Minister:</p><p>Vielen Dank für diese wichtige Frage.</p></rede>
          </dbtplenarprotokoll>'''
        self.assertEqual(parse_bundestag_xml(xml, source_url="https://example.org/protocol.xml")[0].speaker_role,
                         "Bundesminister der Verteidigung")

    def test_official_xml_excludes_commentary_and_preserves_speaker(self):
        xml = '''<dbtplenarprotokoll wahlperiode="21" sitzung-nr="95" sitzung-datum="23.09.2026">
        <rede id="ID219500100"><p klasse="redner"><redner id="123"><name><vorname>Irene</vorname>
        <nachname>Mihalic</nachname><fraktion>GRÜNE</fraktion></name></redner>Irene Mihalic:</p>
        <p klasse="J">Sehr geehrte Frau Präsidentin!</p><kommentar>(Beifall)</kommentar>
        <p klasse="O">Das ist wichtig für alle Bürgerinnen und Bürger.</p></rede></dbtplenarprotokoll>'''
        rows = parse_bundestag_xml(xml, source_url="https://www.bundestag.de/resource/blob/1/21095.xml")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].date, "2026-09-23")
        self.assertEqual(rows[0].speaker_name, "Irene Mihalic")
        self.assertEqual(rows[0].party, "GRÜNE")
        self.assertIn("Bürgerinnen", rows[0].speech_text)
        self.assertNotIn("Beifall", rows[0].speech_text)
        self.assertIn("Beifall", rows[0].raw_text)
        self.assertTrue(rows[0].source_url.endswith("#ID219500100"))

    def test_listing_links_only_xml(self):
        links = _Links()
        links.feed('<a href="/resource/blob/1/21095.xml">XML</a><a href="/other.pdf">PDF</a>')
        self.assertEqual(links.links, ["https://www.bundestag.de/resource/blob/1/21095.xml"])


class ItalyParserTests(unittest.TestCase):
    def test_each_legislature_starts_at_its_own_first_sitting(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            years = {(17, 1): 2017, (17, 2): 2017, (17, 3): 2018,
                     (18, 1): 2018, (18, 2): 2019, (19, 1): 2022}
            for (term, sitting), year in years.items():
                path = root / "raw" / "italy" / f"leg{term}" / f"sitting-{sitting:04d}.xml"
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(
                    f'<seduta ramo="camera" legislatura="{term}" numero="{sitting}" '
                    f'anno="{year}" mese="1" giorno="1"><resoconto><intervento id="i1">'
                    '<testoXHTML><nominativo id="1" cognomeNome="Test Member">TEST MEMBER</nominativo>'
                    'This is the spoken text.</testoXHTML></intervento></resoconto></seduta>',
                    encoding="utf-8")
            with patch("parliament_ai_study.sources.italy._last_sitting",
                       side_effect=lambda term: {17: 3, 18: 2, 19: 1}[term]):
                stats = build_camera_corpus(root / "italy.jsonl", raw_dir=root / "raw",
                                            manifest_path=root / "sources.jsonl")
            self.assertEqual(stats["sittings"], 4)
            self.assertEqual(stats["records"], 4)
            self.assertIn('"session_id": "camera-leg18-sed0001"',
                          (root / "italy.jsonl").read_text(encoding="utf-8"))

    def test_xml_continuations_are_part_of_same_speech(self):
        xml = '''<seduta legislatura="19" numero="711" anno="2026" mese="09" giorno="18" ramo="camera">
          <resoconto tipo="stenografico"><intervento id="tit00020.int00020"><testoXHTML>
          <nominativo id="302794" cognomeNome="MORASSUT Roberto">ROBERTO MORASSUT</nominativo>
          (PD-IDP). Grazie Presidente. Parliamo della Costituzione.</testoXHTML>
          <interventoVirtuale id="iv.4">La legge è importante per i cittadini.</interventoVirtuale>
          <interventoVirtuale id="iv.5">(Applausi dei deputati.)</interventoVirtuale>
          </intervento></resoconto></seduta>'''
        rows = parse_camera_xml(xml, source_url="https://documenti.camera.it/sitting")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].party, "PD-IDP")
        self.assertIn("La legge è importante", rows[0].speech_text)
        self.assertNotIn("Applausi", rows[0].speech_text)
        self.assertIn("Applausi", rows[0].raw_text)
        self.assertEqual(rows[0].speaker_id, "302794")

    def test_extracts_official_italian_intervention_and_speaker_metadata(self):
        html = """<html><body><div id='divWrapper' class='stenografico'>
          <p class='centerBold'>Seduta n. 711 di venerdì 18 settembre 2026</p>
          <p class='intervento' id='sed0711.stenografico.tit00000.int00010'>
            <a href='?idPersona=305704' title='Vai alla scheda personale: ASCANI Anna'>PRESIDENTE</a>. La seduta è aperta.</p>
          <p class='intervento' id='sed0711.stenografico.tit00020.int00010'>
            <a href='?idPersona=100' title='Vai alla scheda personale: ROSSI Mario'>ROSSI Mario</a>. Grazie, colleghi, per il lavoro svolto.</p>
        </div></body></html>"""
        speeches = parse_camera_html(html, legislature=19, sitting_id="0711",
                                    source_url="https://www.camera.it/leg19/410?idSeduta=0711&tipo=stenografico")
        self.assertEqual(len(speeches), 2)
        self.assertEqual(speeches[0].date, "2026-09-18")
        self.assertEqual(speeches[0].speaker_id, "305704")
        self.assertEqual(speeches[0].speaker_name, "ASCANI Anna")
        self.assertEqual(speeches[0].speaker_role, "presiding_officer")
        self.assertEqual(speeches[0].speech_text, "La seduta è aperta.")
        self.assertIn("PRESIDENTE", speeches[0].raw_text)
        self.assertEqual(speeches[1].speech_text, "Grazie, colleghi, per il lavoro svolto.")


class NetherlandsParserTests(unittest.TestCase):
    def test_only_corrected_final_report_is_selectable(self):
        versions = [
            {"Id": "uncorrected", "Status": "Ongecorrigeerd", "GewijzigdOp": "2026-09-24"},
            {"Id": "corrected", "Status": "Gecorrigeerd", "GewijzigdOp": "2026-09-23"},
        ]
        self.assertEqual(_select_final_report(versions)["Id"], "corrected")
        self.assertIsNone(_select_final_report([versions[0]]))

    def test_coverage_audit_distinguishes_finals_from_provisional_reports(self):
        meetings = [
            {"Id": "m1", "Datum": "2024-01-01T00:00:00+01:00", "VergaderingNummer": 1,
             "Titel": "One", "Verslag": [
                 {"Id": "r1", "Soort": "Eindpublicatie", "Status": "Gecorrigeerd",
                  "GewijzigdOp": "2024-01-02", "Verwijderd": False}]},
            {"Id": "m2", "Datum": "2026-09-24T00:00:00+02:00", "VergaderingNummer": 2,
             "Titel": "Two", "Verslag": [
                 {"Id": "r2", "Soort": "Tussenpublicatie", "Status": "Ongecorrigeerd",
                  "GewijzigdOp": "2026-09-24", "Verwijderd": False}]},
            {"Id": "m3", "Datum": "2020-12-08T00:00:00+01:00", "VergaderingNummer": 3,
             "Titel": "Duplicate", "Verslag": []},
        ]
        with patch("parliament_ai_study.sources.netherlands._odata_pages", return_value=meetings):
            audit = audit_tweede_kamer_coverage()
        self.assertEqual(audit["listed_meetings"], 3)
        self.assertEqual(audit["selected_final_reports"], 1)
        self.assertEqual(audit["provisional_only_meetings"], 1)
        self.assertEqual(audit["meetings_without_any_report"], 1)

    def test_odata_manual_skip_when_server_omits_nextlink(self):
        import json
        pages = []
        def fake_fetch(url):
            pages.append(url)
            value = [{"Id": len(pages)}] if len(pages) < 3 else []
            return json.dumps({"value": value}).encode(), {}
        with patch("parliament_ai_study.sources.netherlands.fetch_bytes", side_effect=fake_fetch):
            rows = list(_odata_pages("https://example.test/Vergadering?%24top=1"))
        self.assertEqual([row["Id"] for row in rows], [1, 2])
        self.assertIn("%24skip=2", pages[-1])

    def test_odata_request_respects_official_maximum_page_size(self):
        requests = []
        def empty(url):
            requests.append(url)
            return iter(())
        with patch("parliament_ai_study.sources.netherlands._odata_pages", side_effect=empty):
            self.assertEqual(list(iter_tweede_kamer_speeches(start_year=2025, end_year=2025)), [])
        self.assertIn("%24top=250", requests[0])

    def test_extracts_speaker_attributed_dutch_intervention_and_preserves_source(self):
        xml = """<?xml version='1.0' encoding='UTF-8'?>
        <vlosCoreDocument xmlns='http://www.tweedekamer.nl/ggm/vergaderverslag/v1.0'>
          <vergadering soort='Plenair' objectid='meeting-1' kamer='Tweede Kamer'>
            <titel>65e vergadering</titel><vergaderjaar>2024-2025</vergaderjaar>
            <vergaderingnummer>65</vergaderingnummer><datum>2025-03-19T00:00:00</datum>
            <activiteit soort='Plenair debat' objectid='debate-1'>
              <activiteithoofd soort='Termijn' objectid='term-1'>
                <activiteititem soort='Woordvoerder' objectid='item-1'>
                  <activiteitdeel soort='Spreekbeurt' objectid='turn-1'>
                    <woordvoerder objectid='turn-1'>
                      <spreker soort='Tweede Kamerlid' objectid='member-1'>
                        <fractie>GroenLinks-PvdA</fractie><aanhef>Mevrouw</aanhef>
                        <verslagnaam>Kathmann</verslagnaam><weergavenaam>Kathmann</weergavenaam>
                        <voornaam>Barbara</voornaam><achternaam>Kathmann</achternaam>
                        <functie>lid Tweede Kamer</functie>
                      </spreker>
                      <tekst><alinea><alineaitem>Mevrouw Kathmann (GroenLinks-PvdA):</alineaitem>
                        <alineaitem>Voorzitter, ik spreek de Kamer toe.</alineaitem></alinea></tekst>
                    </woordvoerder>
                  </activiteitdeel>
                </activiteititem>
              </activiteithoofd>
            </activiteit>
          </vergadering>
        </vlosCoreDocument>"""
        speeches = parse_tweede_kamer_xml(xml, source_url="https://example.test/verslag.xml")
        self.assertEqual(len(speeches), 1)
        speech = speeches[0]
        self.assertEqual(speech.country, "Netherlands")
        self.assertEqual(speech.date, "2025-03-19")
        self.assertEqual(speech.speaker_id, "member-1")
        self.assertEqual(speech.speaker_name, "Barbara Kathmann")
        self.assertEqual(speech.party, "GroenLinks-PvdA")
        self.assertEqual(speech.speech_text, "Voorzitter, ik spreek de Kamer toe.")
        self.assertIn("Mevrouw Kathmann", speech.raw_text)


class SejmParserTests(unittest.TestCase):
    def test_resume_partial_validates_prefix_and_promotes_only_after_completion(self):
        from parliament_ai_study.models import Speech

        speeches = [Speech(country="Poland", parliament="Sejm", chamber="Sejm", date="2024-01-01",
                           session_id="s", speech_id=f"s-{number}", speaker_id="",
                           speaker_name="Member", speech_text=f"Words for record {number}.",
                           source_url="https://example.test/source") for number in (1, 2, 3)]
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "poland.jsonl"
            partial = target.with_suffix(".jsonl.tmp")
            partial.write_text(json.dumps(speeches[0].to_dict(), sort_keys=True) + "\n",
                               encoding="utf-8")
            with patch("parliament_ai_study.sources.sejm.iter_sejm_speeches",
                       side_effect=lambda **kwargs: iter(speeches)):
                result = build_sejm_corpus(target, raw_dir=directory,
                                           manifest_path=Path(directory) / "manifest.jsonl",
                                           resume_partial=True)
            self.assertEqual(result["records"], 3)
            self.assertEqual([json.loads(line)["speech_id"] for line in target.read_text().splitlines()],
                             ["s-1", "s-2", "s-3"])
            self.assertFalse(partial.exists())

    def test_resume_partial_rejects_divergent_prefix_without_modifying_file(self):
        from parliament_ai_study.models import Speech

        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "poland.jsonl"
            partial = target.with_suffix(".jsonl.tmp")
            content = '{"speech_id":"wrong","word_count":1}\n'
            partial.write_text(content, encoding="utf-8")
            speech = Speech(country="Poland", parliament="Sejm", chamber="Sejm", date="2024-01-01",
                            session_id="s", speech_id="s-1", speaker_id="", speaker_name="Member",
                            speech_text="Words for record one.", source_url="https://example.test/source")
            with patch("parliament_ai_study.sources.sejm.iter_sejm_speeches",
                       side_effect=lambda **kwargs: iter([speech])):
                with self.assertRaisesRegex(ValueError, "diverges"):
                    build_sejm_corpus(target, raw_dir=directory,
                                      manifest_path=Path(directory) / "manifest.jsonl",
                                      resume_partial=True)
            self.assertEqual(partial.read_text(encoding="utf-8"), content)

    def test_extracts_polish_statement_and_keeps_raw_interruption_annotation(self):
        body = """<html lang='pl'><body><blockquote>
          <h1>10. kadencja, 1. posiedzenie, 1. dzień (13-11-2023)</h1>
          <p class='punkt-tytul'>Punkt obrad</p>
          <h2 class='mowca'>Prezes Rady Ministrów Mateusz Morawiecki:</h2>
          <p>Wielce Szanowny Panie Prezydencie! Dziękuję państwu.</p>
          <p>(Oklaski.)</p>
        </blockquote></body></html>"""
        statement = {"num": 27, "name": "Mateusz Morawiecki", "memberID": 246,
                     "function": "Prezes Rady Ministrów", "unspoken": False}
        speech = parse_sejm_statement(body, statement, term=10, proceeding=1,
                                      date_value="2023-11-13",
                                      source_url="https://api.sejm.gov.pl/sejm/term10/proceedings/1/2023-11-13/transcripts/27")
        self.assertEqual(speech.country, "Poland")
        self.assertEqual(speech.date, "2023-11-13")
        self.assertEqual(speech.speaker_id, "246")
        self.assertEqual(speech.speaker_role, "Prezes Rady Ministrów")
        self.assertEqual(speech.word_count, 6)
        self.assertNotIn("Oklaski", speech.speech_text)
        self.assertIn("Oklaski", speech.raw_text)
        self.assertEqual(speech.source_identifier, speech.speech_id)

    def test_parallel_date_download_preserves_statement_order_and_skips_unspoken(self):
        metadata = {"statements": [
            {"num": 2, "name": "Second", "memberID": 2, "function": "", "unspoken": False},
            {"num": 1, "name": "First", "memberID": 1, "function": "", "unspoken": False},
            {"num": 3, "name": "Skipped", "memberID": 3, "function": "", "unspoken": True},
        ]}
        def fake_download(url, destination, manifest_path):
            if destination.name == "statements.json":
                return json.dumps(metadata).encode()
            number = int(destination.stem.split("-")[-1])
            return f"<p>Statement number {number} has enough words for a test.</p>".encode()
        with tempfile.TemporaryDirectory() as directory:
            with patch("parliament_ai_study.sources.sejm._cached_download", side_effect=fake_download):
                rows = download_sejm_date(8, 1, "2018-01-10", raw_dir=directory,
                                          manifest_path=Path(directory) / "manifest.jsonl",
                                          workers=2)
        self.assertEqual([row.speech_id.rsplit("statement", 1)[-1] for row in rows], ["1", "2"])
        self.assertTrue(all(row.speech_id.startswith("sejm-term8-proceeding1-2018-01-10-")
                            for row in rows))

    def test_raw_coverage_audit_counts_proceedings_and_statement_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "poland/term-8"
            (root).mkdir(parents=True)
            (root / "proceedings.json").write_text(json.dumps([
                {"number": 1, "dates": ["2018-01-10", "2018-01-11"]},
            ]), encoding="utf-8")
            day = root / "proceeding-1/2018-01-10"
            day.mkdir(parents=True)
            (day / "statements.json").write_text("{}", encoding="utf-8")
            (day / "statement-1.html").write_text("<p>text</p>", encoding="utf-8")
            report = audit_sejm_raw_coverage(Path(directory))
        term = next(row for row in report["terms"] if row["term"] == 8)
        self.assertEqual(term["proceedings"], 1)
        self.assertEqual(term["dates"], 2)
        self.assertEqual(term["statement_body_files"], 1)


class FranceParserTests(unittest.TestCase):
    def test_extracts_attributed_french_intervention_and_keeps_raw_text(self):
        xml = """<?xml version='1.0' encoding='UTF-8'?>
        <compteRendu xmlns='http://schemas.assemblee-nationale.fr/referentiel'>
          <uid>CRTEST</uid><seanceRef>SESSION-1</seanceRef>
          <metadonnees><dateSeance>20240201150000000</dateSeance><legislature>16</legislature></metadonnees>
          <contenu><paragraphe id_syceron='123'>
            <orateurs><orateur><nom>M. Jean Dupont (SOC)</nom><id>456</id><qualite>Député</qualite></orateur></orateurs>
            <texte stime='10'>Bonjour, collègues. Notre texte est important.
              <italique>(Applaudissements sur les bancs.)</italique></texte>
          </paragraphe></contenu>
        </compteRendu>"""
        speeches = parse_france_xml(xml, source_url="https://data.example/archive.zip")
        self.assertEqual(len(speeches), 1)
        speech = speeches[0]
        self.assertEqual(speech.country, "France")
        self.assertEqual(speech.date, "2024-02-01")
        self.assertEqual(speech.speaker_id, "456")
        self.assertEqual(speech.speaker_name, "M. Jean Dupont")
        self.assertEqual(speech.party, "SOC")
        self.assertIn("Bonjour", speech.speech_text)
        self.assertNotIn("Applaudissements", speech.speech_text)
        self.assertIn("Applaudissements", speech.raw_text)
        self.assertEqual(speech.source_identifier, "CRTEST:123")


if __name__ == "__main__":
    unittest.main()
