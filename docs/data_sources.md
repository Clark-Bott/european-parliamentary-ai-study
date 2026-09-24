# Parliamentary data sources: reconnaissance

This inventory distinguishes a source's existence from a verified, complete speech corpus. A linked official archive is not evidence that this project has downloaded or validated its full historical coverage. Data/reuse terms must be reviewed for each source before redistribution.

| Country / chamber | Official source and observed format | Initial coverage / access findings | Status / unresolved work |
|---|---|---|---|
| Germany — Bundestag | DIP read-only REST API for parliamentary materials including plenary protocols and their texts. An API key is required; the official help page publishes a time-limited public key, so no key is embedded in this repository.[4][5] | API documentation exposes `plenarprotokoll` and `plenarprotokoll-text`; protocol metadata is date-filterable and results are cursor-paginated. | Need implement and test key retrieval/configuration, paginate full 2018–latest corpus, inspect transcript format, segment interventions, and review DIP reuse terms. |
| France — Assemblée nationale | Official open-data portal exposes plenary records and a zipped `syseron.xml` debate corpus for the current legislature; the plenary page exposes session CSVs. Archived legislature paths are linked from the portal.[6][7] | Portal links an Open Licence / Licence Ouverte.[8] | Need test 15th–17th legislature archives, parse speaker IDs and boundaries, confirm full temporal coverage and exact licence text. |
| Netherlands — Tweede Kamer | Official VLOS-derived `Verslag` entity has downloadable XML; documentation says records are available from 25 June 2013. The official OData API returns machine-readable JSON metadata.[9][10][11] | Live API reconnaissance confirmed the meeting entity has date/type fields and the verslag entity links to its meeting; individual XML is available through a resource endpoint.[9][11] | Need choose corrected versus interim transcript policy, paginate plenary meetings, download/parse resources, preserve speaker and interruption labels, and inspect reuse terms. |
| Italy — Camera dei deputati | Official Dati Camera portal provides open datasets and RDF linked data.[12] | Portal is live, but this reconnaissance did not validate a speech-level `Interventi` or stenographic transcript download suitable for the target period. | **Major unresolved source adapter.** Identify exact primary transcript endpoints, formats, dates, and reuse terms; do not substitute unverified scraped text. |
| Spain — Congreso de los Diputados | Official open-data portal offers XML, JSON, and CSV. The interventions page publishes timestamped `IntervencionesCronologicamente` and `IntervencionesIniciativa` files in those formats.[13][14] | The daily path was live during reconnaissance; availability of a historical bulk archive and stable speech text schema remains to be confirmed. | Need retrieve full relevant files, determine text completeness and historical archive behavior, normalize interventions, verify against official session pages, and review terms. |
| Poland — Sejm | Official Sejm API documentation and OpenAPI portal cover chamber activity and related information.[15][16] | Live `proceedings` endpoint returned sitting agenda metadata; this is not itself speech-level transcript data. | Need verify and implement the authoritative stenographic transcript endpoint (including historical 2018–2026 coverage), parse `SPEECH` events/MP attribution, and review reuse terms. |

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
