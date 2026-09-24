import hashlib
import tempfile
import unittest
from pathlib import Path
from http.client import IncompleteRead

from parliament_ai_study.sources.download import download_file, file_manifest_entry
from parliament_ai_study.sources.france import parse_france_xml
from parliament_ai_study.sources.germany import parse_bundestag_xml, _Links
from parliament_ai_study.sources.italy import parse_camera_html, parse_camera_xml
from parliament_ai_study.sources.netherlands import parse_tweede_kamer_xml
from parliament_ai_study.sources.sejm import parse_sejm_statement


class ManifestTests(unittest.TestCase):
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
