# Historical control sampling

The reusable sampler is in `src/parliament_ai_study/sampling.py`. It restricts records to the 2018–2021 pre-LLM period and the configured minimum length; deterministically ranks candidates by SHA-256 of `seed|speech_id`; rotates across year, party (or `__UNKNOWN__`), and length buckets; caps reuse of identified speakers; and redistributes unavailable quotas when strata are sparse. It treats missing or sentinel speaker IDs such as `0` as record-specific unknowns instead of one shared person. The selection is reproducible and does not use Python's process-randomized hash.

Example:

```bash
PYTHONPATH=src python -m parliament_ai_study.sampling \
  --corpus data/processed/france_leg15_2018_2021.jsonl \
  --output data/controls/france_historical_control_2018_2021_seed2026.jsonl \
  --sample-size-per-country 1000 --seed 2026 --max-per-speaker 2
```

## Executed French sample

A local control sample was generated from the parsed French 2018–2021 corpus. It contains 1,000 interventions and 227,069 words. Years are balanced exactly at 250 records each; the three text-length bands contain 334, 333, and 333 records. Among identified speaker IDs, 471 distinct speakers appear and no speaker appears more than twice. The source uses speaker ID `0` for some collective/unattributed interventions; 215 sample records have that sentinel and the sampler treats them as distinct unknowns. Party coverage is incomplete: 775/1,000 sample records have no party metadata and are grouped as unknown; the other records span the available party labels. This sample therefore does not support a substantive party-comparison claim.

- Seed: `2026`
- Minimum length: 40 words
- Output: `data/controls/france_historical_control_2018_2021_seed2026.jsonl` (local and Git-ignored)
- SHA-256: `8f7c9e4dfcee087e86817cfbffb6360c341d0257706c209d872d217ba90ec36d`
- Preliminary Pangram 4 list-price estimate at the currently displayed $0.50/1,000-word rate: $113.53; no paid call was made.

The sample is a detector-calibration control, not ground truth about human authorship or a false-positive rate. The same sampling code can be applied to other languages only after those corpora and their metadata are acquired. No comparable historical sample exists yet for Germany, Netherlands, Italy, Spain, or Poland.
