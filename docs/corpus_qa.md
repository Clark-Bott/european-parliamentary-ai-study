# Corpus QA report — France only

Last acquisition and parse: 2026-09-24. This is an execution log for the French adapter, not a six-country corpus QA sign-off.

**Rebuild note (2026-09-24):** An updated full rebuild of the same three archived ZIP checksums emitted 1,243,606 records / 75,392,623 words (393,565 records / 66,401,901 words at 40 words or more). This differs from the earlier four-output run tabulated below by 218 records and 28,133 words, entirely within the previously reported legislature-16 total. The cause remains under investigation; treat the table below as a historical run, **not** the latest corpus. The current French Pangram 4 per-item list-price estimate is 847,941 rounded 100-word units × $0.05 = **$42,397.05** before cache hits or discounts.

A new disk-backed full-file audit (`python -m parliament_ai_study.qa data/processed/france_speeches.jsonl`) passed for the rebuild: **0 duplicate IDs, 0 empty/mismatched text records, 0 missing provenance fields, 0 invalid dates, and coverage in each year 2018–2026**. It found **389,687 repeated normalized text hashes** across all records, largely short formulaic turns. A separate exact-text check of the 393,565 length-eligible records found **175 repeats** (360 rounded units / $18 potential cache savings); leading repeated examples are chair announcements (“La parole est à…”, “L’ordre du jour appelle…”). These data indicate procedural contamination still requires manual review, not that the words are AI-written. The audit is programmatically reproducible; no country-wide random manual source-boundary review has been completed.

## Source acquisition

Three official Assemblée nationale Syceron XML archives for legislatures 15, 16, and 17 were downloaded from the parliamentary open-data portal. The portal links its Open Licence; review the exact terms and attribution obligations before redistribution.[6][7][8]

| Legislature | Raw ZIP bytes | SHA-256 | ZIP members | Parse coverage in this project |
|---|---:|---|---:|---|
| 15 | 148,954,869 | `9c6b38cb0e63fd17b1e1754f87e77bdf593769e4b7dd2e356d5b9af977efe7f4` | 1,562 | 2018–2022 |
| 16 | 57,553,703 | `52519bf690fd31720f568a311a60dcda79c57adea5ee9c6de16c1b171127a424` | 605 | 2022–2024 |
| 17 | 55,772,428 | `286d23a57d30e056f8603eb1c6f4b5e3eae22e3338da551298097deeff5f2700` | 601 | 2024–2026 |

The ZIP integrity check reported no bad member in any archive. Retrieval URLs, UTC timestamps, local relative paths, media types, and SHA-256 values are recorded in `data/manifests/source_manifest.jsonl`. Raw archives and normalized JSONL outputs are intentionally excluded from Git due to size; the code can download and rebuild them with `PYTHONPATH=src python -m parliament_ai_study.sources.cli France ...`.

## Parsed material

The French adapter uses official `<paragraphe>` elements with an `<orateurs>` speaker record and a sibling `<texte>` body. It preserves original French, speaker ID/name/role, source session and paragraph IDs, the official archive URL, and both `raw_text` and cleaned `speech_text`. Cleaning collapses whitespace and removes selected explicit parenthetical audience/noise annotations (e.g. applause); it does not translate the text. Very short turns remain in the archived normalized corpus and are excluded from the default detector run by a 40-word eligibility threshold; alternative thresholds can be passed to analysis functions.

| Output JSONL | Records | Source words | First year | Last year | SHA-256 |
|---|---:|---:|---:|---:|---|
| `france_leg15_2018_2021.jsonl` | 619,447 | 40,362,142 | 2018 | 2021 | `ba100b4b3abedfe45b256b225cbbea62de151c1760c299b23096e920f6855caa` |
| `france_leg15_2022.jsonl` | 20,273 | 1,858,204 | 2022 | 2022 | `b640e73ccb6f6959e8f178ec19d43b29221a716aefee1b972ac38ce30070326b` |
| `france_legislature16_2022_2024.jsonl` | 311,250 | 16,676,553 | 2022 | 2024 | `90970de1330eefda73d87f30435ceca16f63718ec601a416246fccb48099d4cc` |
| `france_leg17_2024_2026.jsonl` | 292,418 | 16,467,591 | 2024 | 2026 | `6af4119d09e0084b87a3df48c0ea74bd7a2043d5e89e2f94ed211d1dab09d3c0` |
| **Total (before eligibility filtering)** | **1,243,388** | **75,364,490** | **2018-01-16** | **2026-07-21** | — |

Counts intentionally include short interruptions and procedural turns; do not interpret them as eligible “speeches” without the planned role/text audit. In the **earlier** run the 40-word rule left 393,480 records / 66,375,086 words. Its $33,187.54 estimate did **not** round each speech separately and therefore understated the projected list price. Use the current estimate in the rebuild note above. These are France-only transcript counts, not a cross-country comparison or detector result.

## Integrity checks executed

A streaming check across all four normalized outputs found:

- 1,243,388 rows and 1,243,388 distinct `speech_id` values (no duplicate IDs).
- No empty `speech_text` fields.
- No missing `source_identifier` or `source_url` fields.
- Every parsed date fell between 2018-01-16 and 2026-07-21.
- 849,908 interventions were shorter than 40 words and will not be sent to Pangram under the default run threshold.
- One record exceeds 10,000 words: `CRSJOCGR5L15S2018E1N001:1360145`, dated 2018-07-09, attributed to President Emmanuel Macron, 10,181 words. It has not been declared erroneous or excluded; verify against the official record before inference.

The earlier run had not audited exact duplicate-text hashes; the new full-file audit above did. Country/year anomaly thresholds, party metadata completeness, and representative random manual source-boundary samples have not yet been audited.

## Manual source comparison

For one 16th-legislature example, the normalized record `CRSANR5L16S2024O1N109:3355792` is dated 2024-01-30, attributes the passage to Gabriel Attal, and begins “Le propre de toute société humaine, c’est de regarder en face l’avenir qui se dessine devant elle…”. The official Assembly record for the second sitting that day displays the same speaker and opening text.[21] This single check confirms one speaker/date/text boundary; it does not validate the entire French corpus or any other country.

## Not yet complete

- A reproducible random sample review with multiple sessions and speakers.
- A systematic check of cleaning boundaries, presidencies, ministerial remarks, short interruptions, and duplicate text.
- Manual review of the 10,181-word record.
- A final exact source-license/attribution review for downstream redistribution or Pangram processing.
- Any comparable corpus for Germany, Netherlands, Italy, Spain, or Poland.

No Pangram calls were made. No empirical AI-use result is claimed.
