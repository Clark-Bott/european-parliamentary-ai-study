# Parliamentary data sources: reconnaissance

This inventory distinguishes a source's existence from a verified, complete speech corpus. A linked official archive is not evidence that this project has downloaded or validated its full historical coverage. Data/reuse terms must be reviewed for each source before redistribution.

| Country / chamber | Official source and observed format | Initial coverage / access findings | Status / unresolved work |
|---|---|---|---|
| Germany — Bundestag | DIP read-only REST API for parliamentary materials including plenary protocols and their texts. An API key is required; the official help page publishes a time-limited public key, so no key is embedded in this repository.[4][5] | API documentation exposes `plenarprotokoll` and `plenarprotokoll-text`; protocol metadata is date-filterable and results are cursor-paginated. | Need implement and test key retrieval/configuration, paginate full 2018–latest corpus, inspect transcript format, segment interventions, and review DIP reuse terms. |
| France — Assemblée nationale | Official Syceron XML bulk archives for legislatures 15, 16, and 17, linked from the official plenary debates pages; the source portal identifies the Open Licence.[6][7][8] | All three archives were downloaded and ZIP-tested. The parser emits an intervention record per official `<paragraphe>` with speaker metadata, source IDs, raw text, and cleaned text. Outputs cover 2018-01-16 through 2026-07-21: 1,243,388 interventions and 75,364,490 source words across four local JSONL files. The counts, checksums, and QA caveats are in `docs/corpus_qa.md`; raw source checksums are in `data/manifests/source_manifest.jsonl`. | France is the only country with a collected/normalized corpus so far. A single 2024 official webpage sample has been manually compared; no country-wide random boundary audit has been completed. The 40-word inference threshold excludes short records by default but does not remove them from the archived normalized corpus. Review the one >10,000-word intervention and source-specific text/role conventions before inference. |
| Netherlands — Tweede Kamer | Official VLOS-derived `Verslag` entity has downloadable XML; documentation says records are available from 25 June 2013. The official OData API returns machine-readable JSON metadata.[9][10][11] | The adapter enumerates plenary meetings, selects the latest corrected final report where available (`Eindpublicatie`, `Gecorrigeerd`/`Gerectificeerd`), and parses speaker-attributed `woordvoerder` turns. One official corrected report for 2025-03-19 produced 308 interventions and 55,561 words.[23] | Adapter and one-day sample are complete; full 2018–2026 download, correction-status coverage audit, randomized boundary/source review, data-license review, and corpus QA remain outstanding. |
| Italy — Camera dei deputati | Official open-data portal provides RDF data.[12] For speech-level transcripts, the Camera publishes a directly accessible HTML stenographic record at `camera.it/leg{term}/410?idSeduta={id}&tipo=stenografico`; indexed official pages also expose PDFs under `documenti.camera.it/leg{term}/resoconti/assemblea/html/sed{session}/stenografico.pdf`.[18] | A live 2026 sitting page and a 2019 official stenographic PDF were retrieved for endpoint inspection. This confirms a source architecture, not a collected or parsed corpus. | **Adapter and complete index discovery still outstanding.** Need enumerate the 2018–2026 sitting IDs, parse interventions with reliable speaker boundaries, preserve official HTML/PDF provenance, and review reuse terms. Do not use OCR text without validation. |
| Spain — Congreso de los Diputados | Official open-data portal publishes chronological/intervention datasets in CSV, JSON, and XML.[13][14] | The official interventions page and dynamic current-legislature file links were observed; historical bulk coverage for 2018–2023 is not established.[14] | Need actually retrieve files, verify date coverage and text fields, find prior-legislature archives, parse/normalize, validate against official records, and review terms. |
| Poland — Sejm | Official API documents proceedings, transcript statement lists, individual statement bodies, and PDF transcripts.[15][16][19] | The downloader enumerates terms 8–10 and fetches per-day metadata plus per-statement HTML bodies. A live 2023-11-13 sitting sample yielded 43 normalized interventions and 19,291 words; raw responses are in ignored `data/raw/poland/` with provenance manifest entries.[19][20][22] | Adapter code exists but the full 2018–2026 acquisition was not run. Remaining work: execute full download, validate counts/coverage, inspect reuse terms, run manual official-page checks, review role/short-turn cleaning, and build cross-country analyses. |

## Data acquisition policy

- Keep raw source files out of Git unless small and their reuse terms clearly permit it. Store URL, retrieval time, byte count, media type, SHA-256, and parser version in a manifest.
- Preserve source-language Unicode; never translate the text sent for detection.
- Store source identifiers and a direct source URL on every normalized intervention.
- Record correction status (e.g. interim/corrected transcript) and source version when exposed.
- For each chamber, compare a random sample of parsed records against the official record before describing parsing as validated.

## Sources

[4] https://dip.bundestag.de/%C3%BCber-dip/hilfe/api — Bundestag DIP API help
[5] https://search.dip.bundestag.de/api/v1/openapi.yaml — Bundestag DIP OpenAPI
[6] https://data.assemblee-nationale.fr/travaux-parlementaires/debats — French Assembly debates data
[7] https://data.assemblee-nationale.fr/travaux-parlementaires/seance-publique — French Assembly plenary data
[8] https://data.assemblee-nationale.fr/licence-ouverte-open-licence — French Assembly open licence
[9] https://opendata.tweedekamer.nl/documentatie/verslag — Tweede Kamer Verslag documentation
[10] https://opendata.tweedekamer.nl/documentatie/odata-api — Tweede Kamer OData documentation
[11] https://gegevensmagazijn.tweedekamer.nl/OData/v4/2.0/$metadata — Tweede Kamer OData metadata
[12] https://dati.camera.it — Camera open-data portal
[13] https://www.congreso.es/datos-abiertos — Spanish Congress open data
[14] https://www.congreso.es/es/opendata/intervenciones — Spanish Congress interventions
[15] https://api.sejm.gov.pl — Sejm API documentation
[16] https://api.sejm.gov.pl/sejm.html — Sejm API reference
