# Historical control sampling

The reusable sampler is in `src/parliament_ai_study/sampling.py`. It restricts records to the 2018–2021 pre-LLM period and the configured minimum length; deterministically ranks candidates by SHA-256 of `seed|speech_id`; rotates across year, party (or `__UNKNOWN__`), and length buckets; caps reuse of identified speakers; and redistributes unavailable quotas when strata are sparse. It treats missing or sentinel speaker IDs such as `0` as record-specific unknowns instead of one shared person. The selection is reproducible and does not use Python's process-randomized hash.

Example:

```bash
PYTHONPATH=src python -m parliament_ai_study.sampling \
  --corpus data/processed/france_speeches.jsonl \
  --output data/controls/france_historical_sample.jsonl \
  --sample-size-per-country 1000 --seed 2026 --max-per-speaker 2
```

## Executed French sample

A current local control sample was generated from the rebuilt French 2018–2021 corpus. It contains **1,000 interventions / 227,358 words**. Years are balanced exactly at 250 records each; the three length bands contain 334, 333, and 333 records. Among identified speakers, no speaker appears more than twice. The current sample has **215 empty speaker IDs**, which the sampler treats as distinct unknowns by using speech IDs. Party coverage is incomplete: 775/1,000 records have no party metadata and are grouped as unknown. This sample does not support a substantive party-comparison claim.

- Seed: `2026`
- Minimum length: 40 words
- Output: `data/controls/france_historical_sample.jsonl` (local and Git-ignored)
- SHA-256: `dd727ce981a3439413f52d117e9ffae92fe82e51095a29c39c6a10fba98bb337`
- Pangram 4 sample list-price estimate: **2,742 started 100-word units × $0.05 = $137.10**; no paid call was made.

An Italian 2018–2021 sample was also produced from the local XML corpus: **1,000 records / 347,158 words**, exactly 250 records in each year. It is stored in ignored `data/controls/italy_historical_sample.jsonl` (SHA-256 `c5280ca2881b3263ce7161d48c9ce66069cde96922364f0fb968116e703ed30d`); 137 records lack party metadata. At the same Pangram 4 list rate the sample would cost **$196.10**. See [Italian corpus QA](italy_corpus_qa.md) and its tracked control manifest. Neither sample has been sent to Pangram.

A Dutch 2018–2021 sample yielded only **658 records / 216,665 words** (136, 148, 141, and 233 by year). The two-records-per-speaker limit prevents filling the requested 1,000 with the current source metadata; do not label this as a balanced 1,000-record sample. It is stored in ignored `data/controls/netherlands_historical_sample.jsonl` (SHA-256 `8d6f1af24f0009c2841180e304dee6381222bc230e3211d911a057a077bd2ede`); 149 records have no party, and the list-price estimate is **$123.70**. The [Dutch build QA](netherlands_corpus_qa.md) lists the remaining source-coverage gap.

A Spanish 2018–2021 sample contains **1,000 records / 372,565 words**, exactly 250 records in each year. It is stored in ignored `data/controls/spain_historical_sample.jsonl` (SHA-256 `a08bc475847c45d748d4777c47f422f31531494502acb45cbed066947c458ccf`) with an estimated list price of **$210.45**. The current Diario source supplies no party or stable speaker ID, so all 1,000 records have both fields missing; the sampler uses immutable speech IDs for the speaker cap. The two official PDF-only journals are now included through the separate PDF fallback parser, as documented in [Spanish corpus QA](spain_corpus_qa.md). No inference was performed.

A German 2018–2021 sample was generated from the verified CPP-BT baseline: **1,000 records / 300,909 words**, exactly 250 records in each year. It is stored in ignored `data/controls/germany_historical_sample.jsonl` (SHA-256 `29859353a2bc88b05545b091f432e7641b82bd39c43dd7d58391aeb5f722249d`); 114 records lack party metadata, no identified speaker appears more than twice, and the list-price estimate is **$172.80**. See [German corpus QA](germany_corpus_qa.md). No inference was performed.

A Polish 2018–2021 sample contains **1,000 records / 426,523 words**, exactly 250 per year. It is stored in ignored `data/controls/poland_historical_sample.jsonl` (SHA-256 `1eaaa3d8d3f2d4b017b8677ef1dab474e5ba6eea3aa711c7a1b4ad5421ec2e58`). Identified speakers appear at most twice; sentinel/unknown speaker IDs are treated as distinct records. All sampled records lack party metadata. The [tracked manifest](../data/manifests/poland_current_controls_manifest.json) records its hash. These samples are detector-calibration controls, not ground truth about human authorship or a measured false-positive rate; none has been submitted.
