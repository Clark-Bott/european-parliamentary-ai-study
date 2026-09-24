# Source-boundary verification

Screening check that parsed records really occur in their official source.
Tool: `python -m parliament_ai_study.review --verify`. Method: take a
deterministic sample (seed 2026, balanced across years), retrieve each
record's own source, and test whether the normalized `speech_text` occurs in
it.

| Country | Sample | verified | normalized | partial | mismatch | skipped |
|---|---|---|---|---|---|---|
| Germany | 10 | 10 | 0 | 0 | 0 | 0 |
| France | 10 | 6 | 4 | 0 | 0 | 0 |
| Netherlands | 10 | 10 | 0 | 0 | 0 | 0 |
| Italy | 10 | 6 | 4 | 0 | 0 | 0 |
| Spain | 10 | 7 | 0 | 3 | 0 | 0 |
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

Transport per country: Germany and France are checked against the local
official bulk archives (the CC0 CPP-BT CSV and the Syceron ZIPs) because
their `source_url` values are a DOI and a bulk ZIP rather than a per-record
page. Italy, the Netherlands, and Spain are checked against the live official
URL stored on each record.

## What this does and does not establish

It establishes that sampled records exist, in the stated form, in the
official source — no invented, merged, or truncated text in this sample.

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
