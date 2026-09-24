# Parliamentary data sources: reconnaissance

This inventory distinguishes a source's existence from a verified, complete speech corpus. A linked official archive is not evidence that this project has downloaded or validated its full historical coverage. Data/reuse terms must be reviewed for each source before redistribution.

| Country / chamber | Official source and observed format | Initial coverage / access findings | Status / unresolved work |
|---|---|---|---|
| Germany — Bundestag | Official Bundestag Open Data XML protocol lists for terms 19–21; DIP REST is an alternative.[4][5] The verified fallback baseline is CPP-BT 2026-01-17, a CC0 research compilation derived from official XML/DIP records.[24] | CPP-BT speech archive: 59,225 non-empty records / 30,146,735 words through 2026-01-15; full-file integrity QA passed. [Build QA](germany_corpus_qa.md); [sample QA](germany_sample_qa.md). Official resource requests after the archive cutoff still redirect to Enodia verification. | Resolve and document 2026-01-18 onward through a permitted official route; then reconcile session counts and perform random speech-boundary review. The paid guard blocks the current gap. |
| France — Assemblée nationale | Official Syceron XML bulk archives for legislatures 15–17; the source portal identifies the Open Licence.[6][7][8] | An earlier run downloaded and ZIP-tested three archives and measured 1,243,388 paragraph-level records / 75,364,490 words through 2026-07-21. Counts/checksums are in [French QA](corpus_qa.md); files are Git-ignored and must be downloaded in a fresh clone. | One manual record comparison, no random audit; 40-word threshold excludes many short turns. Review the >10,000-word intervention and role conventions. |
| Netherlands — Tweede Kamer | Official VLOS-derived `Verslag` downloadable XML; OData JSON metadata. The [portal disclaimer](https://opendata.tweedekamer.nl/disclaimer) states CC0 1.0 applies to its API data unless otherwise indicated, and notes IP-level bandwidth limits.[9][10][11] | Corrected-pagination build: 344,220 records / 46,237,076 words from 903 reports; file integrity QA passed. Coverage audit: 919 meeting rows, exactly 903 active corrected/rectified finals locally matched; 15 later meetings remain provisional-only and one 2020 OData row is a verified duplicate. [Build QA](netherlands_corpus_qa.md); [sample QA](netherlands_sample_qa.md).[23] | Keep the fixed corpus corrected-final only; audit random XML boundaries and verify no record-specific CC0 exception. |
| Italy — Camera dei deputati | Official `formato_xml` sitting record and term-specific index, terms 17–19.[12][18] The [RDF open-data dataset](https://dati.camera.it/dataset/sedute-e-resoconti-stenografici-delle-legislature-precedenti) lists CC BY-SA; this does **not** establish that the separate rendered XML endpoint has identical terms. | The local full-builder run emitted 262,716 interventions / 49,946,554 words across 1,457 sittings; full-file integrity QA passed. [Build QA](italy_corpus_qa.md) and [sample QA](italy_sample_qa.md). | Official sitting-enumeration reconciliation, random boundary validation, role/short-turn review, and applicable XML endpoint/third-party processing terms remain. |
| Spain — Congreso de los Diputados | Open-data intervention index has metadata only; official `mostrarTextoIntegro` Diario provides full speech text.[13][14] Official PDF fallback exists for journals without the HTML text response. | Full local build: 100,669 turns / 28,046,062 words from 581 journals; integrity QA passed. `DSCD-12-PL-162` and `DSCD-14-PL-59` have official PDFs but no usable numbered HTML. [Build QA](spain_corpus_qa.md); [sample QA](spain_sample_qa.md). | Resolve both journals, reconcile all journal numbers, enrich speaker/party IDs, run random boundary checks, and complete reuse review. |
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
[24] https://doi.org/10.5281/zenodo.18177196 — CPP-BT 2026-01-17, CC0 compilation of Bundestag plenary protocols
