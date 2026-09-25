# European Parliamentary AI-Writing Study

This repository is the engineering workspace for a comparative study of AI-classified text in six European lower chambers: the German Bundestag, French Assemblée nationale, Dutch Tweede Kamer, Italian Camera dei deputati, Spanish Congreso de los Diputados, and Polish Sejm.

Research question: How has the prevalence of AI-generated or AI-assisted text in parliamentary interventions changed since widespread generative AI, and how does it compare across major European legislatures?

The project is motivated by The Economist's September 2026 article, “AI-written speeches are taking over politics.” The article body was recovered on 2026-09-24 through a syndicated reprint, which confirms Pangram as the detector and a word-weighted UK headline metric; the Pangram model, thresholds, date range, speech definition, and any source note, code, or data release remain unavailable. This is therefore a comparative extension, not an exact replication. See [the reconstruction ledger](docs/economist_replication.md).

## Current status — be precise

```text
DATA COLLECTION:        SIX LOCAL CORPORA BUILT through country-specific cutoffs; Polish raw coverage complete through 2026-09-25; German post-archive sittings not incorporated
PARSING:                COMPLETE for the current local six-country corpus
NORMALIZATION:          COMPLETE — 2,113,920 source-language interventions, 264,461,445 words
VALIDATION:             PARTIAL — six-country disk-backed integrity QA passed; 2,458 cached Polish statement bodies lack manifest entries; human boundary review remains
PANGRAM INTEGRATION:    ONE REAL-CORPUS API DIAGNOSTIC completed on a 73-word Dutch speech; estimated $0.05; not a study result
ANALYSIS PIPELINE:      COMPLETE — tables, figures, sensitivity and control analyses implemented and exercised on mocked detector output
FULL PANGRAM INFERENCE: NOT RUN — only one short-text diagnostic submitted; full study is not funded or executed
```

- RESEARCH RECONNAISSANCE: substantially advanced 2026-09-24; the article body was recovered through a syndicated reprint, which confirms Pangram as the detector and a word-weighted UK headline metric; the Pangram model, thresholds, date range, speech definition, and any source note, code, or data release remain unavailable, so this stays a comparative extension, not a replication ([ledger](docs/economist_replication.md))
- FRANCE ARCHIVE COLLECTION: official 15th–17th legislature Syceron ZIPs were downloaded and checksum-verified locally; they are not in Git and must be downloaded in a fresh clone
- FRANCE PARSING/NORMALIZATION: current local rebuild emitted 1,243,606 intervention records / 75,392,623 words through 2026-07-21; disk-backed full-file audit passed, but found 389,687 repeated text hashes, mostly formulaic short turns. Automated source-boundary screening of 10 records passed; human reading of a larger sample remains outstanding.
- FRANCE QA: 0 duplicate speech IDs, 0 empty records, and 0 missing provenance fields in the streamed check; one official webpage sample was manually compared; full manual sampling, text-boundary audit, duplicate-text review, and review of an over-10,000-word record remain outstanding
- HISTORICAL CONTROL: deterministic 2018–2021 samples exist locally for all six countries. The Dutch sample contains 658 rather than 1,000 records because the strict speaker cap could not fill the quota; Poland has 1,000 records (250 per year) ([method and QA](docs/historical_controls.md)).
- POLAND: official per-statement API build yielded 97,513 interventions / 32,231,985 words through 2026-09-25. Raw-file coverage and disk-backed integrity audits passed; live proceedings indexes match all 480 cached target days. The source manifest lacks entries for 2,458 cached statement bodies and 16 day-metadata files; 10-record cached-source screening has nine exact and one partial match. Human boundary review remains open ([Poland QA](docs/poland_corpus_qa.md)).
- NETHERLANDS: the corrected-pagination build emitted 344,220 records / 46,237,076 words from 903 reports; disk-backed integrity QA passed, and 10-record source-boundary screening against the live official XML found 0 mismatches. A live coverage audit exactly matches all 903 active corrected/rectified final reports. The other 16 OData rows are one verified 2020 duplicate plus 15 post-2026-06-25 provisional-only meetings, not missing historical transcripts ([build QA](docs/netherlands_corpus_qa.md); [sample QA](docs/netherlands_sample_qa.md)).
- ITALY: official XML adapter across terms 17–19; a local full-builder run emitted 262,716 records / 49,946,554 words from 1,457 sittings. Disk-backed integrity QA and 10-record source-boundary screening passed, but official enumeration, human reading of a sample, role/short-turn cleaning, and XML reuse terms have not been signed off ([build QA](docs/italy_corpus_qa.md); [sample QA](docs/italy_sample_qa.md)).
- GERMANY: verified CC0 CPP-BT 2026-09-19 baseline emitted 64,796 records / 32,514,063 words, including 5,607 records in 2026 through the 11 September sitting; disk-backed integrity QA passed. Official XML for the 23 and 24 September sittings is accessible, but not in the corpus; the latter is labeled partial. The researcher accepts this documented country-specific cutoff rather than requiring the same final day in every country. The gap report remains for transparency but no longer blocks submission. Automated source-boundary screening of 10 records against the CC0 archive passed; human reading remains outstanding ([build QA](docs/germany_corpus_qa.md); [sample QA](docs/germany_sample_qa.md)).
- SPAIN: official Diario build emitted 101,069 records / 28,139,144 words from 583 journals, including 252 and 148 turns recovered from two official PDF-only journals with the pypdf fallback; page-boundary regression and disk-backed integrity QA passed. Corrected 10-record source-boundary screening has one automatic mismatch, a 26-word chair turn located manually in the official source after an inline cue was removed. Speaker/party enrichment and human reading of a larger sample remain outstanding ([build QA](docs/spain_corpus_qa.md); [sample QA](docs/spain_sample_qa.md)).
- SIX-COUNTRY BUILD: combined local file contains 2,113,920 records and passes disk-backed integrity QA; required 2018–2025 country/year cells are present and Spanish/Polish gap reports are empty. Country end dates differ; Germany's 2026 cutoff remains documented. Random human boundary review and full Polish file-level provenance reconciliation are **not** complete. [Build manifest](data/manifests/combined_corpus.json).
- SOURCE-BOUNDARY SCREENING: corrected 10-record SHA-256 screens for five countries found 38 exact, eight normalized, three partial, and one Spanish automatic mismatch located manually in the source. Poland's cached-source screen found nine exact and one partial, with all ten speaker/date values matching cached metadata. This is not human QA ([details](docs/source_boundary_verification.md)).
- PANGRAM CLIENT: task API, request cache and explicit paid-run guard implemented. One real-corpus diagnostic completed, with one submitted Dutch speech (73 words); Pangram 4 returned **0.0% AI-only** and **0.0% AI-assisted** for that short text. This is software evidence, not a population or authorship finding.
- COST CONTROL: per-item rounded estimator reports **918,354** length-eligible interventions / **2,944,254** started 100-word units / **$147,212.70** for all six countries at the configured public rate. Poland alone is **$18,546.15**; the tiny test estimated **$0.05**. These are not account quotes or provider-enforced caps.
- POSITIVE CONTROLS: optional Phase 8 design implemented — per-language generation briefs, validation that keeps synthetic text out of real corpora, cached submission, and a per-language detection table. No passages generated yet ([method](docs/positive_controls.md))
- ANALYSIS: aggregation, tables, SVG figures, and report generation implemented; exercised on synthetic smoke data only
- FULL INFERENCE: NOT RUN; only the one explicitly authorized, tiny paid diagnostic was run

The six-country build is locally complete through its documented country-specific cutoffs; full research inference is not run. Paid execution requires explicit confirmation, 2018–2025 country/year coverage, and empty required Spanish and Polish gap reports. There is no approval-file gate. Polish cached files without manifest entries, long-turn flags, and human source-boundary review remain research-quality limitations. Do not cite the one short-text diagnostic or mock outputs as study findings. Detailed earlier French counts and anomalies are in [docs/corpus_qa.md](docs/corpus_qa.md).

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

**Tiny real-corpus API diagnostic:** the first one ran on 2026-09-25 with `--test-country Netherlands --test-count 1 --model pangram-4 --price-per-1000-words 0.50 --max-cost 0.05 --confirm-paid-run` against the validated combined corpus. The 73-word Dutch intervention dated 2025-03-06 was verified against its cached official XML; the local charge estimate was **$0.05**, under the requested $1 ceiling. Pangram returned 0.0% AI-only and 0.0% AI-assisted for that one short text. The record is in ignored `results/corpus-api-test-2026-09-25/api_test/test_result.json`. An earlier *synthetic* output already occupied `results/api_test/`, so the real request used an isolated directory; the first attempt stopped before network access. Future runs require separate authorization; do not rerun to seek different classifications. `--max-cost` is a local estimate, **not** a provider-enforced bill limit. Never commit `.env`, corpus text, or test results.

**Budgeted parliamentary inference (only after the remaining corpus guards pass):** `./run_experiment.sh --corpus data/processed/speeches.jsonl --results-dir results/budgeted-preview --dry-run --sample-budget 1000` first verifies sampling and figures with mocked responses. Once the six-country corpus passes integrity and coverage checks, use `./run_experiment.sh --corpus data/processed/speeches.jsonl --results-dir results/budgeted --sample-budget 1000 --max-cost 1000 --confirm-paid-run` for a billable run. The budget includes optional positive controls; use an isolated results directory for each budget/seed and separate mock from paid output. The sampled run validates the **full** corpus and the same Spanish/Polish gap guards before selecting speeches. It writes a source-hashed, fixed-seed country-month sample, weights, and per-month sample/population counts to `results/budgeted/reports/sampling_plan.json`. The monthly/quarterly/annual, historical and subgroup shares use those weights; the speaker breakdown is suppressed. If the budget cannot reserve one possible speech in each populated country-month, it fails *before* any paid call. This conservative rule can leave unused funds. A few speeches per month provide a **plot of exploratory estimates, not precise or guaranteed-correct population rates**; inspect `sampled_speeches` and the plan before reporting. Details: [budgeted inference method](docs/budgeted_inference.md).

## Method and data

The observation is intended to be an individually attributed substantive plenary intervention, preserving source-language text. Do not translate before detection. AI-generated and AI-assisted classifications are distinct; the primary word share uses Pangram segment word proportions where returned, scaled to the source Unicode word denominator to accommodate Pangram normalization. Historical texts (2018–2021) are calibration controls, not ground truth. A detector label does not establish that a named member personally used AI; staff may draft speeches. Method choices and uncertainties are recorded in [docs/methodology.md](docs/methodology.md), [docs/data_sources.md](docs/data_sources.md), and [docs/limitations.md](docs/limitations.md).

## Output and data policy

Source licenses and terms must be reviewed before redistribution or paid processing. Raw archives and derived JSONL are excluded from Git. The manifests document verified local French, German, Italian, Dutch, and Spanish builds; a new clone must reacquire them. Country-level historical corpus statistics are not six-country research results.

## Repository status

This is an active research-engineering project, not a completed empirical study. Five country-level corpora have local builds, but the combined corpus is not validated, Germany retains a post-cutoff source gap, Spain still needs source-boundary and rights review, and Poland is still acquiring. There is no detector-based evidence about AI adoption rates in any chamber. The research-credit status summary is in [docs/pangram_research_request.md](docs/pangram_research_request.md) and intentionally documents the unfinished corpus work rather than claiming the six-country study is ready.
