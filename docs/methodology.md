# Proposed study methodology (version 0.1)

This document is a transparent pre-analysis plan for the requested cross-country extension. It is not a claim that the choices reproduce *The Economist*'s undisclosed method. See [`economist_replication.md`](economist_replication.md) for the evidence ledger.

## Estimand and unit

The target population is substantive interventions entered into the plenary record of six national lower chambers from 2018 through the latest complete material that can be retrieved consistently. The observation is one speaker-attributed intervention. We will retain each source's original-language text and source type; translations are excluded from detection input.

Primary estimand, conditional on a configured minimum eligible length, is the fraction of all eligible words classified AI-generated:

`AI-only word share = sum(Pangram window word_count where label == AI-Generated) / sum(eligible source word_count)`

If a response lacks segment word counts, the current implementation estimates the numerator as source word_count × Pangram `fraction_ai`; report that as a fallback approximation, not an exact word count.

AI-assisted/mixed fraction is reported separately and also in a clearly labeled combined sensitivity estimate. Pangram's current official API documentation confirms an asynchronous task flow: POST `/task` returns a task ID; polling GET `/task/{task_id}` continues until `STAGE_SUCCESS` or `STAGE_FAILED`. The successful response includes `fraction_ai`, `fraction_ai_assisted`, `fraction_human`, and (on Pangram 4) windows with labels and `word_count` values. It also states Pangram 4 may normalize submitted text, so window offsets refer to the returned text.[2] The client submits one intervention per task and sends an explicit model selector. Our primary word estimate sums Pangram's `word_count` for `AI-Generated` windows; assisted words are tabulated separately. For older/alternate responses without windows, the pipeline uses the returned fractions times the source corpus word count, which is an approximation and is recorded as a limitation.

## Time periods and controls

Use 2018–2021 as pre-LLM historical controls, 2022 as a transition year, and 2023 onward as post-ChatGPT. Current endpoint availability, not a presumed complete 2026 year, sets the latest observed date. A deterministic seed and stratification by country, year, speaker, party (if reliable), and length band will govern any sampled control corpus. Complete historic corpora are retained when practical. Country-language baseline estimates are diagnostic/sensitivity adjustments, never ground truth.

## Cleaning and inclusion

An intervention must have non-empty text, a traceable source record, a plausible date, and a speaker boundary. The current implementation's default minimum eligible length is 40 words; shorter turns are retained in normalized source outputs but excluded from inference and the primary aggregate. The 40-word cutoff is a transparent project design choice, not a reconstructed Economist rule, and should be varied in sensitivity analyses. Deterministic cleaning may remove markup and explicit applause/stage annotations, but must preserve the raw source and record all excluded spans or reasons. Procedural formulas, chair boilerplate, brief interruptions, and voting text require source-specific rules documented and tested against samples; do not use an opaque global regex as a substitute for validation. Speaker roles and minister/chair status are retained so exclusions can be sensitivity analyses.

## Analysis plan

Aggregate by country and month, quarter, and year. Provide word-weighted and intervention-weighted shares, AI-only and AI-plus-mixed results, alternative minimum lengths, exclusions of ministers/chairs, pre/post comparisons, language-specific historical baselines, descriptive party/speaker/term/topic splits when provenance supports them, and uncertainty intervals appropriate to the sampling design. Do not make individual politician-use allegations from detector scores.

## Pangram use and cost

The current documented API is asynchronous (`POST /task`, then poll `GET /task/{task_id}`); current docs instruct new integrations to specify a model selector, and show `pangram-4` as an example.[2] Developer pricing currently lists Pangram 4 at $0.05 per 100 words and Pangram 3 at $0.05 per 1,000 words, with a Bulk API discount shown.[3] Pricing is mutable and estimates must be generated from the current configured model/rate, with a clear warning that the billing unit, text normalization, task billing, taxes, discounts, and account-specific terms must be reconfirmed before paid submission. No paid call is part of this work.

## Sources

[2] https://docs.pangram.com/api-reference/ai-detection — Pangram AI Detection API
[3] https://www.pangram.com/pricing?category=developers — Pangram developer pricing
