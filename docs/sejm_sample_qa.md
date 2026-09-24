# Sejm sample QA — one sitting day only

The official Sejm REST API was used to retrieve term 10, proceeding 1, dated 2023-11-13: the transcript statement list plus each statement's individual HTML body.[19][20][22] The source statements list provides speaker name, member ID, official function, statement number, and whether an item was spoken. The parser retains the source URL and IDs, extracts paragraph text, removes only standalone recognized Polish stage/audience annotations from cleaned text, and keeps those annotations in `raw_text`.

## Observed sample

| Item | Result |
|---|---:|
| Sitting date | 2023-11-13 |
| Sejm term / proceeding | 10 / 1 |
| Normalized interventions | 43 |
| Unique normalized IDs | 43 |
| Words before the default 40-word threshold | 19,291 |
| Interventions under 40 words | 2 |
| Empty cleaned text | 0 |

One mapped record is statement 1: Andrzej Duda, `Prezydent Rzeczypospolitej Polskiej`, 2,610 words. The normalized sample is stored locally at `data/processed/poland_sample_2023-11-13.jsonl`; the official list and individual HTML responses are under ignored `data/raw/poland/term-10/proceeding-1/2023-11-13/`. The raw response URLs and content hashes are in `data/manifests/source_manifest.jsonl`.

This verifies that one official API day's list and body endpoints can be retrieved and normalized. It is not a random sample audit against an independently rendered Sejm site, does not establish historical completeness, and is not a full Polish corpus. The complete 2018–2026 downloader has been implemented but not executed. Party affiliation is not currently enriched from the Sejm membership endpoint.

No Pangram inference was run.
