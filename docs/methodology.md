# Proposed study methodology (version 0.1)

This document is a transparent pre-analysis plan for the requested cross-country extension. It is not a claim that the choices reproduce *The Economist*'s undisclosed method. See [`economist_replication.md`](economist_replication.md) for the evidence ledger.

## Estimand and unit

The target population is substantive interventions entered into the plenary record of six national lower chambers from 2018 through the latest complete material that can be retrieved consistently. The observation is one speaker-attributed intervention. We will retain each source's original-language text and source type; translations are excluded from detection input.

Primary estimand, conditional on a configured minimum eligible length, is the fraction of all eligible words classified AI-generated:

`AI-only word share = sum(source words per speech × Pangram AI-window words / all Pangram window words) / sum(eligible source words)`

Pangram 4 may normalize submitted text. Therefore, the detector's window word total can differ from this repository's Unicode source-word total. The code scales window fractions to each speech's source denominator; these are *estimated* AI-classified source words, not exact matching word boundaries. If no usable window counts exist, the code uses source word_count × Pangram `fraction_ai` as a fallback approximation.

AI-assisted/mixed fraction is reported separately and also in a labeled combined sensitivity estimate. Pangram's API specifies an asynchronous task flow: POST `/task` returns a task ID; polling GET `/task/{task_id}` continues until `STAGE_SUCCESS` or `STAGE_FAILED`. The result includes `fraction_ai`, `fraction_ai_assisted`, `fraction_human`, and Pangram 4 windows with labels and `word_count`. Window offsets refer to Pangram's returned (possibly normalized) text.[2] The client submits one intervention per task, checks `/models` entitlement, and sends an explicit selector.

## Time periods and controls

Use 2018–2021 as pre-LLM historical controls, 2022 as a transition year, and 2023 onward as post-ChatGPT. Current endpoint availability, not a presumed complete 2026 year, sets the latest observed date. The reproducible sampler uses a fixed seed, round-robin quotas across years and party/length strata, and a maximum per identified speaker; unknown parties remain a visible stratum, and unknown speaker IDs fall back to speech-specific keys. Executed local controls and their metadata limitations are in [`historical_controls.md`](historical_controls.md). Complete historic corpora are retained when practical. Country-language baseline estimates are diagnostic/sensitivity adjustments, never ground truth.

## Cleaning and inclusion

An intervention must have non-empty text, a traceable source record, a plausible date, and a speaker boundary. The current implementation's default minimum eligible length is 40 words; shorter turns are retained in normalized source outputs but excluded from inference and the primary aggregate. The 40-word cutoff is a transparent project design choice, not a reconstructed Economist rule, and should be varied in sensitivity analyses. Deterministic cleaning may remove markup and explicit applause/stage annotations, but must preserve the raw source and record all excluded spans or reasons. Procedural formulas, chair boilerplate, brief interruptions, and voting text require source-specific rules documented and tested against samples; do not use an opaque global regex as a substitute for validation. Speaker roles and minister/chair status are retained so exclusions can be sensitivity analyses.

## Analysis plan

Aggregate by country and month, quarter, and year. Provide word-weighted and intervention-weighted shares, AI-only and AI-plus-mixed results, alternative minimum lengths, exclusions of ministers/chairs, pre/post comparisons, language-specific historical baselines, descriptive party/speaker/term/topic splits when provenance supports them, and uncertainty intervals appropriate to the sampling design. Do not make individual politician-use allegations from detector scores.

## Pangram use and cost

The documented API is asynchronous (`POST /task`, then poll `GET /task/{task_id}`); new integrations must specify a model selector, and `GET /models` reports key-specific access.[2] The payload contains only `speech_text`; speaker identity and source metadata remain local. Developer pricing lists Pangram 4 at $0.05 per **started 100-word block for each submitted item** and Pangram 3 at a different unit/rate. `estimate_cost` uses `ceil(speech_words/100)` for Pangram 4's default configuration; the task client does not claim a bulk discount.[3] Billing, account-specific terms, source rights, processor terms, retention, and international transfers must be reviewed and recorded before paid submission. The runtime rejects a missing processing-approval record. No paid call is part of this work.

## Sources

[2] https://docs.pangram.com/api-reference/ai-detection — Pangram AI Detection API
[3] https://www.pangram.com/pricing?category=developers — Pangram developer pricing
