# European Parliamentary AI-Writing Study

This repository is the engineering workspace for a comparative study of AI-classified text in six European lower chambers: the German Bundestag, French Assemblée nationale, Dutch Tweede Kamer, Italian Camera dei deputati, Spanish Congreso de los Diputados, and Polish Sejm.

Research question: How has the prevalence of AI-generated or AI-assisted text in parliamentary interventions changed since widespread generative AI, and how does it compare across major European legislatures?

The project is motivated by The Economist's September 2026 article, “AI-written speeches are taking over politics.” The article body was recovered on 2026-09-24 through a syndicated reprint, which confirms Pangram as the detector and a word-weighted UK headline metric; the Pangram model, thresholds, date range, speech definition, and any source note, code, or data release remain unavailable. This is therefore a comparative extension, not an exact replication. See [the reconstruction ledger](docs/economist_replication.md).

## Current status — be precise

```text
DATA COLLECTION:        IN PROGRESS — five corpora built locally; Polish downloader resumed from its verified partial corpus with pooled connections and 12 workers; post-archive German protocols not yet incorporated (newest protocol partial)
PARSING:                COMPLETE for Germany, France, Netherlands, Italy, Spain; Poland parser implemented, full build pending
NORMALIZATION:          COMPLETE for the five built corpora; common schema, source URLs, and source-language text retained
VALIDATION:             PARTIAL — automated full-file integrity QA passed for all five built corpora; corrected full-file 10-record screening found one Spanish automatic mismatch (inline-cue deletion, located in source); human sample reading still outstanding
PANGRAM INTEGRATION:    SOFTWARE-TESTED — client, cache, spend-capped sampling and guarded real-corpus API diagnostic implemented; no live paid task run
ANALYSIS PIPELINE:      COMPLETE — tables, figures, sensitivity and control analyses implemented and exercised on mocked detector output
FULL PANGRAM INFERENCE: NOT RUN — Polish acquisition and six-country validation are incomplete; German 2026 cutoff is documented but not a gate
```

- RESEARCH RECONNAISSANCE: substantially advanced 2026-09-24; the article body was recovered through a syndicated reprint, which confirms Pangram as the detector and a word-weighted UK headline metric; the Pangram model, thresholds, date range, speech definition, and any source note, code, or data release remain unavailable, so this stays a comparative extension, not a replication ([ledger](docs/economist_replication.md))
- FRANCE ARCHIVE COLLECTION: official 15th–17th legislature Syceron ZIPs were downloaded and checksum-verified locally; they are not in Git and must be downloaded in a fresh clone
- FRANCE PARSING/NORMALIZATION: current local rebuild emitted 1,243,606 intervention records / 75,392,623 words through 2026-07-21; disk-backed full-file audit passed, but found 389,687 repeated text hashes, mostly formulaic short turns. Automated source-boundary screening of 10 records passed; human reading of a larger sample remains outstanding.
- FRANCE QA: 0 duplicate speech IDs, 0 empty records, and 0 missing provenance fields in the streamed check; one official webpage sample was manually compared; full manual sampling, text-boundary audit, duplicate-text review, and review of an over-10,000-word record remain outstanding
- HISTORICAL CONTROL: deterministic 2018–2021 samples now exist locally for Germany, France, Italy, Spain, and the Netherlands. The Dutch sample contains 658 rather than 1,000 records because the strict speaker cap could not fill the quota. No Poland sample exists yet ([method and QA](docs/historical_controls.md))
- POLAND: official API enumeration and per-statement HTML downloader/parser implemented; one 2023-11-13 sitting sample yielded 43 interventions and 19,291 words; the full historical corpus and country QA have not been run
- NETHERLANDS: the corrected-pagination build emitted 344,220 records / 46,237,076 words from 903 reports; disk-backed integrity QA passed, and 10-record source-boundary screening against the live official XML found 0 mismatches. A live coverage audit exactly matches all 903 active corrected/rectified final reports. The other 16 OData rows are one verified 2020 duplicate plus 15 post-2026-06-25 provisional-only meetings, not missing historical transcripts ([build QA](docs/netherlands_corpus_qa.md); [sample QA](docs/netherlands_sample_qa.md)).
- ITALY: official XML adapter across terms 17–19; a local full-builder run emitted 262,716 records / 49,946,554 words from 1,457 sittings. Disk-backed integrity QA and 10-record source-boundary screening passed, but official enumeration, human reading of a sample, role/short-turn cleaning, and XML reuse terms have not been signed off ([build QA](docs/italy_corpus_qa.md); [sample QA](docs/italy_sample_qa.md)).
- GERMANY: verified CC0 CPP-BT 2026-09-19 baseline emitted 64,796 records / 32,514,063 words, including 5,607 records in 2026 through the 11 September sitting; disk-backed integrity QA passed. Official XML for the 23 and 24 September sittings is accessible, but not in the corpus; the latter is labeled partial. The researcher accepts this documented country-specific cutoff rather than requiring the same final day in every country. The gap report remains for transparency but no longer blocks submission. Automated source-boundary screening of 10 records against the CC0 archive passed; human reading remains outstanding ([build QA](docs/germany_corpus_qa.md); [sample QA](docs/germany_sample_qa.md)).
- SPAIN: official Diario build emitted 101,069 records / 28,139,144 words from 583 journals, including 252 and 148 turns recovered from two official PDF-only journals with the pypdf fallback; page-boundary regression and disk-backed integrity QA passed. Corrected 10-record source-boundary screening has one automatic mismatch, a 26-word chair turn located manually in the official source after an inline cue was removed. Speaker/party enrichment and human reading of a larger sample remain outstanding ([build QA](docs/spain_corpus_qa.md); [sample QA](docs/spain_sample_qa.md)).
- SIX-COUNTRY BUILD: acquisition adapters and a combined-corpus builder exist; the full 2018–2026 acquisition and random manual QA have **not** been completed. An earlier Dutch 90,706-record build was incomplete because the OData server omitted a pagination link; explicit skip pagination is implemented, but that file must not be used as complete. Spanish numbered-journal gaps are recorded and block paid submission.
- SOURCE-BOUNDARY SCREENING: a corrected full-file SHA-256 10-record sample per built country was checked against its official source (live URL for Italy, the Netherlands, and Spain; local archives for Germany and France): 38 verbatim, 8 after punctuation folding, 3 partial because cleaning removed inline cues/page markers, and **one Spanish automatic mismatch**, located manually in the source; 0 skipped. Method, correction, and limits: [docs/source_boundary_verification.md](docs/source_boundary_verification.md). This is a screening sample, not the human Phase 4 sign-off; review packets live under `data/interim/review_packets/` (Git-ignored).
- PANGRAM CLIENT: client for Pangram's asynchronous task API (synchronous POST plus polling), request fingerprint cache, resume state, opt-in paid-run guard, budgeted country-month sampling and guarded 1–3 short-speech corpus API diagnostic implemented; no live request made
- COST CONTROL: per-item rounded estimator implemented; local length-eligible estimates are **$42,397.05** for France, **$17,802.00** for Germany, **$26,924.80** for Italy, **$26,680.00** for the reconciled Dutch corpus, and **$14,862.70** for the Spanish corpus including PDF fallbacks. None is an account quote or a validated six-country total.
- POSITIVE CONTROLS: optional Phase 8 design implemented — per-language generation briefs, validation that keeps synthetic text out of real corpora, cached submission, and a per-language detection table. No passages generated yet ([method](docs/positive_controls.md))
- ANALYSIS: aggregation, tables, SVG figures, and report generation implemented; exercised on synthetic smoke data only
- FULL INFERENCE: NOT RUN; no paid API call was made

The full Polish acquisition and six-country coverage validation remain unfinished. Paid execution still requires an explicit confirmation, valid 2018–2025 country/year coverage, and empty required Spanish and Polish source-gap reports. The researcher confirmed readiness to handle source and Pangram processing terms; there is no approval-file gate. German September 2026 sessions remain recorded as an accepted country-specific cutoff, not a submission blocker. Human boundary review remains a research-quality task. Do not cite mock outputs as research findings. Detailed earlier French counts and anomalies are in [docs/corpus_qa.md](docs/corpus_qa.md).

## Run the verified smoke workflow

Python 3.11 or later. Runtime dependencies are `pypdf==6.1.1` for the two Spain PDF fallback journals and Rich for the read-only Polish acquisition monitor. The launcher uses the project environment through `uv` when available, then falls back to an explicit `.venv`.

```bash
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python -e .
./run_experiment.sh --dry-run
```

The default dry run is deterministic and never contacts Pangram. With no combined corpus present, it creates an explicitly synthetic six-country test fixture and exercises QA, cost estimation, aggregation, CSV tables, SVG figures, machine-readable mock results, and a report under `results/`. **This is a software smoke test, not an end-to-end run on six real corpora.** An explicitly supplied `--corpus` path must exist; a typo will not silently use a synthetic fixture. To acquire every official corpus before a real-corpus dry run, use `./run_experiment.sh --build-corpus --dry-run`. This can download many files and may take a long time. To acquire without analysis, use `uv run --python 3.12 python -m parliament_ai_study.sources.build` after installation. Individual adapters: `uv run --python 3.12 python -m parliament_ai_study.sources.cli Germany` (also France, Netherlands, Italy, Spain, Poland). After all acquisition processes stop, reconcile checksums and inferred source URLs with `uv run --python 3.12 python -m parliament_ai_study.provenance --resolve-germany`; unresolved URLs are reported rather than guessed.

To watch an existing Polish acquisition **without starting a second downloader**, run this in another terminal from the repository root (Ctrl+C closes the display):

```bash
uv run --python 3.12 python -m parliament_ai_study.sources.monitor_sejm
```

Add `--once` for a single snapshot or `--offline` to avoid fetching a missing sitting-day index from the public Sejm API. The Rich bars count cached **sitting-day metadata**, not completed speeches or validated coverage; the display separately shows flushed records, the latest record, and bodies cached for its day. The monitor does not change the partial corpus or provenance manifest. After a transient DNS failure, the old writer was restarted, stopped cleanly for a downloader change, and restarted again from the preserved prefix with `--resume-partial --through-date 2026-09-25 --workers 12`. Its log is `/tmp/opencode/poland-resume-pooled-12.log`. Only one writer may run at a time; do not reconcile the live provenance manifest while it runs.

Poland has an [official whole-day stenographic PDF archive](docs/poland_acquisition_options.md). The current corpus uses the separately numbered HTML statements for trustworthy speaker boundaries. The resumed Sejm downloader uses one plain HTTP GET per small file and reuses HTTPS connections; a small read-only timing comparison favored pooling, but no sustained 10× corpus-wide speedup has been established. Do not switch to PDF extraction or a third-party corpus without a new parser and source-boundary QA.

Run tests with:

```bash
uv run --python 3.12 python -m unittest discover -s tests -v
```

## Cost estimate and paid-run guard

The Pangram 4 developer page advertises $0.05 per **started 100-word block per item**, with a minimum one block per eligible speech. Two 101-word speeches cost four blocks, not 2.02 blocks. The default $0.50 / 1,000 words is configurable. Confirm current plan, model access, and billing terms before a paid run. The public page advertises bulk discounts; this task-based client does not assume them.[3]

After a normalized JSONL corpus exists, estimate cost without inference:

```bash
./run_experiment.sh --estimate-only --corpus data/processed/speeches.jsonl
./run_experiment.sh --estimate-only --corpus data/processed/speeches.jsonl --country Germany --year 2024
```

To configure access, copy `.env.example` to `.env` and set `PANGRAM_API_KEY`; `.env` is ignored by Git. The real pipeline refuses to submit without the explicit `--confirm-paid-run` flag:

```bash
./run_experiment.sh --corpus data/processed/speeches.jsonl --confirm-paid-run
```

If the combined corpus is missing, this command attempts to acquire and normalize all six chambers first. It rejects missing country/year coverage and missing/non-empty Spanish or Polish source-gap reports; the German post-archive interval is informational only. No approval record is required. Add `--max-cost N` (USD) after verifying the six-country estimate and current account quote; the run aborts before the first request if the corpus plus optional positive-control estimate exceeds N. The command then checks model access through Pangram's read-only `/models` endpoint. Completed responses are cached under a text-plus-configuration SHA-256 key. Ambiguous POST outcomes are marked and not automatically resubmitted; [docs/pangram_operations.md](docs/pangram_operations.md) documents resume, error logs, and the reset procedure. For a real corpus, the pipeline replays the JSONL file for QA, costing, analysis, and output instead of loading every record into memory; paid responses are reloaded from the cache for analysis.

### Two limited-spend options

**Tiny real-corpus API diagnostic (one started 100-word block, estimated $0.05 at the default rate):** first run `./run_experiment.sh --dry-run` for the free software test. Once the **combined corpus and Polish coverage report** are ready, use `./run_experiment.sh --test-api --corpus data/processed/speeches.jsonl --max-cost 1 --confirm-paid-run` after setting `PANGRAM_API_KEY` in ignored `.env`. It deterministically picks one 40–100-word speech from 2023 onward, sends its source-language text, and reports AI-only and AI-assisted shares. `--test-country Germany` can restrict the choice. Up to three speeches are supported with `--test-count N`; every selected speech costs one started block at the configured rate. No corpus is downloaded or built by this option. The full-corpus integrity and country/year checks, and Spanish/Polish gap checks still apply; German September sittings and a processing-approval file do not block it. The default `--max-cost` without an override is $0.05. A `$1` cap is a **local estimate**, not a provider-enforced bill limit. Source IDs, dates, hashes and diagnostic shares are recorded under ignored `results/api_test/`; a repeat with the same corpus and model uses the cache. Short-text classifications are not proof of authorship or study prevalence. Never commit `.env` or test results.

**Budgeted parliamentary inference (only after the remaining corpus guards pass):** `./run_experiment.sh --corpus data/processed/speeches.jsonl --results-dir results/budgeted-preview --dry-run --sample-budget 1000` first verifies sampling and figures with mocked responses. Once the six-country corpus passes integrity and coverage checks, use `./run_experiment.sh --corpus data/processed/speeches.jsonl --results-dir results/budgeted --sample-budget 1000 --max-cost 1000 --confirm-paid-run` for a billable run. The budget includes optional positive controls; use an isolated results directory for each budget/seed and separate mock from paid output. The sampled run validates the **full** corpus and the same Spanish/Polish gap guards before selecting speeches. It writes a source-hashed, fixed-seed country-month sample, weights, and per-month sample/population counts to `results/budgeted/reports/sampling_plan.json`. The monthly/quarterly/annual, historical and subgroup shares use those weights; the speaker breakdown is suppressed. If the budget cannot reserve one possible speech in each populated country-month, it fails *before* any paid call. This conservative rule can leave unused funds. A few speeches per month provide a **plot of exploratory estimates, not precise or guaranteed-correct population rates**; inspect `sampled_speeches` and the plan before reporting. Details: [budgeted inference method](docs/budgeted_inference.md).

## Method and data

The observation is intended to be an individually attributed substantive plenary intervention, preserving source-language text. Do not translate before detection. AI-generated and AI-assisted classifications are distinct; the primary word share uses Pangram segment word proportions where returned, scaled to the source Unicode word denominator to accommodate Pangram normalization. Historical texts (2018–2021) are calibration controls, not ground truth. A detector label does not establish that a named member personally used AI; staff may draft speeches. Method choices and uncertainties are recorded in [docs/methodology.md](docs/methodology.md), [docs/data_sources.md](docs/data_sources.md), and [docs/limitations.md](docs/limitations.md).

## Output and data policy

Source licenses and terms must be reviewed before redistribution or paid processing. Raw archives and derived JSONL are excluded from Git. The manifests document verified local French, German, Italian, Dutch, and Spanish builds; a new clone must reacquire them. Country-level historical corpus statistics are not six-country research results.

## Repository status

This is an active research-engineering project, not a completed empirical study. Five country-level corpora have local builds, but the combined corpus is not validated, Germany retains a post-cutoff source gap, Spain still needs source-boundary and rights review, and Poland is still acquiring. There is no detector-based evidence about AI adoption rates in any chamber. The research-credit status summary is in [docs/pangram_research_request.md](docs/pangram_research_request.md) and intentionally documents the unfinished corpus work rather than claiming the six-country study is ready.
