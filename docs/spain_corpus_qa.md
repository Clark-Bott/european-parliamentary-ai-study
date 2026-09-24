# Spain local corpus build and integrity QA — 2026-09-24

The Congreso Diario adapter produced **101,069 speaker-attributed turns / 28,091,299 words** from **583 parsed journals** for 2018–2026. The two journals that lacked usable `textoCompleto` HTML were recovered from their official PDF editions with the separate `pypdf==6.1.1` coordinate-aware parser: `DSCD-12-PL-162` produced **252 turns**, and `DSCD-14-PL-59` produced **148 turns**. The disk-backed full-file audit found zero duplicate speech IDs or integrity errors and 15,462 repeated normalized-text hashes. Fourteen records exceed 10,000 words and remain flagged for manual review. The [tracked manifest](../data/manifests/spain_current_manifest.json) records the local file hash and size. Raw pages, PDFs, and corpus text are excluded from Git.

The 40-word-eligible subset has **50,197 records / 27,276,966 words**, or **296,769 started 100-word units / $14,838.45** at the current list rate. The historical control contains 1,000 records / 373,350 words and has a $210.85 list-price estimate. No Pangram inference was performed.

## PDF fallback evidence

The fallback files were retrieved from the official Congreso PDF paths and match these SHA-256 hashes:

- `DSCD-12-PL-162.PDF`: `1dc99c22aeb70cbade915c4b0e86d988d1af3e5d3ab20a365f754a99fa7d3374`
- `DSCD-14-PL-59.PDF`: `b69d7d39c79cf15463d662ce49a8d835fcd576b2060a25ba26f86a72572aa4b3`

The parser uses embedded-font coordinates and bold speaker labels, removes page furniture and agenda blocks, preserves stage directions in `raw_text`, and fails rather than silently accepting a PDF without two opening markers. Repeated parsing of each PDF produced identical records. This resolves the two source gaps; `data/manifests/spain_unavailable_journals.json` is now an empty list.

The raw-file inventory is in [`spain_coverage_audit.json`](../data/manifests/spain_coverage_audit.json): 581 HTML files have full text, with one additional official PDF fallback in term XII and one in term XIV. The audit does not replace independent session-index reconciliation or random source-boundary review. Stable speaker and party IDs remain unavailable for this source. Rights and third-party processing review remains separate; see [`rights_and_processing_review.md`](rights_and_processing_review.md).
