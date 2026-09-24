# Parliamentary data sources: reconnaissance

This inventory distinguishes a source's existence from a verified, complete speech corpus. A linked official archive is not evidence that this project has downloaded or validated its full historical coverage. Data/reuse terms must be reviewed for each source before redistribution.

| Country / chamber | Official source and observed format | Initial coverage / access findings | Status / unresolved work |
|---|---|---|---|
| Germany — Bundestag | Official Bundestag Open Data XML protocol lists for terms 19–21 (no DIP key required); DIP REST is an alternative.[4][5] | Official XML listing paginates; the 2026-09-23 XML sample contains 190 speaker turns / 43,805 words. [Sample QA](germany_sample_qa.md). | Full archive download, random source review, and rights review remain. |
| France — Assemblée nationale | Official Syceron XML bulk archives for legislatures 15–17; the source portal identifies the Open Licence.[6][7][8] | An earlier run downloaded and ZIP-tested three archives and measured 1,243,388 paragraph-level records / 75,364,490 words through 2026-07-21. Counts/checksums are in [French QA](corpus_qa.md); files are Git-ignored and must be downloaded in a fresh clone. | One manual record comparison, no random audit; 40-word threshold excludes many short turns. Review the >10,000-word intervention and role conventions. |
| Netherlands — Tweede Kamer | Official VLOS-derived `Verslag` entity has downloadable XML; documentation says records are available from 25 June 2013. The official OData API returns machine-readable JSON metadata.[9][10][11] | The adapter enumerates plenary meetings, selects the latest corrected final report where available (`Eindpublicatie`, `Gecorrigeerd`/`Gerectificeerd`), and parses speaker-attributed `woordvoerder` turns. One official corrected report for 2025-03-19 produced 308 interventions and 55,561 words.[23] | Adapter and one-day sample are complete; full 2018–2026 download, correction-status coverage audit, randomized boundary/source review, data-license review, and corpus QA remain outstanding. |
| Italy — Camera dei deputati | Official `formato_xml` sitting record and official term-specific index, terms 17–19.[12][18] | The original HTML sample omitted continuation text. Replacement XML parser recovered 47 interventions / 15,203 words for 2026-09-18. [Sample QA](italy_sample_qa.md). | Full archive run, random boundary validation, and reuse/third-party processing terms remain. |
| Spain — Congreso de los Diputados | Open-data intervention index has metadata only; official `mostrarTextoIntegro` Diario provides full speech text.[13][14] | Official `DSCD-15-PL-204` sample parsed 134 turns / 53,459 words; journal enumeration covers terms XII–XV. [Sample QA](spain_sample_qa.md). | Full archive download, party/speaker enrichment, random boundary checks, and reuse review remain. |
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
