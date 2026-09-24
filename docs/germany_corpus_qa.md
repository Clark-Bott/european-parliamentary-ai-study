# Germany local corpus build and integrity QA — 2026-09-24

The German baseline uses **CPP-BT version 2026-01-17**, DOI `10.5281/zenodo.18177196`. CPP-BT is a private, CC0-licensed research compilation derived from official Bundestag Open Data XML and DIP records. Its published speech archive was downloaded from Zenodo. The archive matched the published MD5 `9b03325c65c6930bc5e44d4206ce3d42`, passed ZIP integrity testing, and has local SHA-256 `4e8ed7550b447be2ca798f23bbb381491f5fd7e31e2c7f97efb38d0b8259a9e0`.

Normalization emitted **59,225 non-empty attributed speeches / 30,146,735 words**. Forty-three empty archive rows were excluded. Coverage is 6,369 records in 2018, 7,503 in 2019, 7,492 in 2020, 5,573 in 2021, 8,188 in 2022, 9,254 in 2023, 8,111 in 2024, 6,406 in 2025, and 329 from 1–15 January 2026. The disk-backed full-file audit found zero duplicate speech IDs or integrity errors and 84 repeated normalized-text hashes. The [tracked manifest](../data/manifests/germany_current_manifest.json) records the local corpus hash and size. Raw archives and corpus text are excluded from Git.

The 40-word-eligible subset has **58,352 records / 30,125,701 words**, or **329,769 started 100-word units / $16,488.45** at the current list rate. This is a baseline estimate, not an account quote.

## Unresolved 2026 interval

CPP-BT has a 17 January 2026 cutoff. The official XML list endpoint can enumerate protocols, but Bundestag resource requests are redirected to an Enodia verification page and return HTTP 400 to the non-interactive downloader. No attempt is made to bypass that verification. Therefore the corpus does **not** cover the interval from 18 January through the end of 2026. `data/manifests/germany_unavailable_protocols.json` records this gap, and the paid-run guard rejects any non-empty gap report.

The CPP-BT baseline is derived from official protocols, but this project has not yet completed a random speech-boundary comparison against official XML, review of duplicate texts, or independent session-count reconciliation. CC0 covers the compilation, and the dataset states that plenary protocols are official works, but downstream processing and attribution decisions still require project review. No Pangram call was made.
