# Source-boundary verification

Screening check that parsed records really occur in their official source.
Tool: `python -m parliament_ai_study.review --verify`. Method: take a
deterministic full-file SHA-256 sample (seed 2026, balanced across years), retrieve each
record's own source, and test whether the normalized `speech_text` occurs in
it.

| Country | Sample | verified | normalized | partial | mismatch | skipped |
|---|---|---|---|---|---|---|
| Germany | 10 | 10 | 0 | 0 | 0 | 0 |
| France | 10 | 6 | 4 | 0 | 0 | 0 |
| Netherlands | 10 | 10 | 0 | 0 | 0 | 0 |
| Italy | 10 | 8 | 2 | 0 | 0 | 0 |
| Spain | 10 | 4 | 2 | 3 | 1 | 0 |
| Poland | — | not run; acquisition still running | | | | |

Status meanings are recorded in
`data/manifests/source_boundary_verification.json`:

- **verified** — record text found verbatim after whitespace and case folding.
- **normalized** — found after ignoring punctuation spacing, decorative
  characters, and apostrophe style (for example `n’ai` against `n'ai`).
- **partial** — every substantial segment found; inline material that the
  parser correctly removes (audience cues such as `(rumores y protestas)`,
  page markers such as `Página 4`) accounts for the difference.
- **mismatch** — not located; must be investigated before the corpus is used.
- **skipped** — source not retrievable by this tool.

**Sampler correction, 2026-09-25:** The first screening implementation
selected only from the first 64 records of each year. That is not a random
sample of a year's corpus. The sampler now ranks all records in each year by
SHA-256 while retaining only the best candidates in memory. All five
country checks in the table above were rerun with the corrected method;
the earlier counts are superseded.

**Spanish follow-up:** The one automatic mismatch is
`congreso-14-PL-251:turn-0112` (2023-03-09, 26 words). Inspection of the
official Diario page located the chair's intervention and the exact voting
totals (346 votes, 202 for, 122 against, 22 abstentions). The parser removes
the inline `(Pausa)` cue, leaving a double full stop; the automated substring
check cannot join the two sides of the deletion. This procedural turn is below
the 40-word inference threshold. The result remains a mismatch in the
machine-readable report; a full human speaker/date and boundary review has
not been signed off.

Transport per country: Germany and France are checked against the local
official bulk archives (the CC0 CPP-BT CSV and the Syceron ZIPs) because
their `source_url` values are a DOI and a bulk ZIP rather than a per-record
page. Italy, the Netherlands, and Spain are checked against the live official
URL stored on each record.

## What this does and does not establish

It provides screening evidence that most sampled records' text occurs in
their stated official source. The Spanish automatic mismatch was located
manually and is still visible in the report. This check is not evidence that
every record has the right speaker or date or that the corpus is complete.

It does **not** complete Phase 4 validation. Ten records per country is a
screening sample. Still outstanding for every country: a human reading of a
larger random sample (packets are generated under
`data/interim/review_packets/`, Git-ignored because they contain transcript
text), speaker-attribution and date confirmation against the official page,
duplicate-review of the repeated French text hashes, and review of the
>10,000-word French record. Poland has not been checked at all yet.

## Reproduce

```bash
uv run --python 3.12 python -m parliament_ai_study.review \
  --corpus data/processed/spain_speeches.jsonl --country Spain \
  --count 10 --verify --report results/reports/spain_source_boundary.json
```

Exit status is 1 when any sampled record is a mismatch or is skipped, so the
command fails loudly on an unresolved record.
