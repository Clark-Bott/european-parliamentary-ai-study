# Spain local corpus build and integrity QA — 2026-09-24

The Congreso Diario adapter produced **100,669 speaker-attributed turns / 28,046,062 words** from **581 parsed journals** for 2018–2026. The disk-backed full-file audit found zero duplicate speech IDs or integrity errors and 15,385 repeated normalized-text hashes. Every year has records; 2019 is lower than adjacent years and must be reviewed during source-coverage checks. The 40-word-eligible subset has **50,021 records / 27,234,410 words**, or **296,262 started 100-word units / $14,813.10** at the current list rate. The [tracked manifest](../data/manifests/spain_current_manifest.json) records the local file hash and size. Raw pages and corpus text are excluded from Git.

## Unresolved journals

The numbered HTML lookup does not return `textoCompleto` for two existing official journals:

- `DSCD-12-PL-162`, dated 2018-10-31
- `DSCD-14-PL-59`, dated 2020-10-29

Both official PDF files were retrieved and read locally. The first contains 155 plenary session material; the second contains 56th-session material. Their HTML is absent, so the current parser does not include their speech text. They are **not** empty journals. `data/manifests/spain_unavailable_journals.json` records the gap and the paid-run guard rejects inference while it is non-empty. Resolve these journals through a reproducible, reviewed text format before inference.

The build also does not reconcile all 581 journal numbers to an independent official session index, enrich stable speaker or party IDs, or review procedural and role boundaries against a random source sample. No Pangram call was made.
