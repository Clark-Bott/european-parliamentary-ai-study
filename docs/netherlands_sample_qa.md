# Tweede Kamer sample QA — one plenary sitting only

The OData API was queried for plenary meeting `a1645248-9e62-4297-9cd1-00303a03aa30` (2025-03-19). The downloader selected final report `3c34d93e-6ef7-4cfb-8fbe-adec483d6b60` with `Soort=Eindpublicatie` and `Status=Gecorrigeerd`, fetched its official XML resource, and parsed VLOS `woordvoerder` turns.[9][10][11][23]

| Check | Result |
|---|---:|
| Date | 2025-03-19 |
| Final corrected XML bytes | 1,320,528 |
| Parsed speaker turns | 308 |
| Unique normalized IDs | 308 |
| Words before the default 40-word eligibility rule | 55,561 |
| Distinct speaker IDs | 31 |
| Empty cleaned text | 0 |

The normalized output is local at `data/processed/netherlands_sample_2025-03-19.jsonl`. The original final-report XML is under ignored `data/raw/netherlands/verslag/`; the source URL and SHA-256 are recorded in `data/manifests/source_manifest.jsonl`. For example, a source turn maps speaker name, party, role, session date, and an individual `woordvoerder` ID to the common speech schema.

This is one sitting-day API/parser smoke test, not a random validation sample or a complete Dutch corpus. The full 2018–2026 collection has not been executed; corrected-report availability by meeting, possible rectifications, party-history coverage, text-boundary accuracy, and reuse conditions remain to be audited. No Pangram inference was run.
